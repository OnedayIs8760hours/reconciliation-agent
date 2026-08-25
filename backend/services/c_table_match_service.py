from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from backend.domain.match_result import MatchResult, MatchSummary
from backend.domain.reconciliation_record import ATableRecord, BTableRecord
from backend.domain.reconciliation_schema import SheetFieldSchema
from backend.services.c_table_base_service import C_TRACE_HEADERS, CTableBaseResult
from backend.services.product_mapping_service import ProductMappingLookup
from tools import excel_tool


class CTableMatchService:
    """用 C/A 表明细去匹配 B 表系统记录，并把追溯信息写回 C 表。"""

    def match_and_write(
        self,
        c_file_path: Path,
        a_schema: SheetFieldSchema,
        c_table_result: CTableBaseResult,
        b_records: list[BTableRecord],
        product_lookup: ProductMappingLookup,
    ) -> MatchSummary:
        """执行 C 表正向匹配，并把匹配状态和 B 表追溯字段写入 C 表。"""

        # load_workbook(...)：打开 C 表底稿，后续只在 C 表上写匹配结果。
        workbook = load_workbook(c_file_path)
        worksheet = excel_tool.get_sheet(workbook, a_schema.sheet_name or None)

        a_records = self.read_a_records(worksheet, a_schema)
        used_b_keys: set[str] = set()
        results: list[MatchResult] = []
        inserted_rows = 0

        for a_record in a_records:
            c_row = a_record.source_row + inserted_rows
            match_result = self.match_one_record(a_record, c_row, b_records, used_b_keys, product_lookup)
            results.append(match_result)

            if len(match_result.b_records) > 1:
                inserted_count = len(match_result.b_records) - 1
                # insert_rows(...)：在当前 A 行下面插入多行，用来承接一对多 B 表记录。
                worksheet.insert_rows(c_row + 1, amount=inserted_count)
                inserted_rows = inserted_rows + inserted_count
                self.clear_inserted_business_cells(
                    worksheet,
                    c_row + 1,
                    c_row + inserted_count,
                    c_table_result.original_max_column,
                )

            self.write_match_result(worksheet, c_table_result.trace_start_column, match_result)
            for b_record in match_result.b_records:
                used_b_keys.add(b_record.trace_key())

        excel_tool.reset_view(worksheet, header_row=a_schema.header_row)
        excel_tool.auto_fit_columns(worksheet)
        # save(...)：保存 C 表匹配结果。
        workbook.save(c_file_path)

        matched_a_records = 0
        matched_b_records = 0
        need_review_count = 0
        unmatched_count = 0
        for result in results:
            if result.b_records:
                matched_a_records = matched_a_records + 1
                matched_b_records = matched_b_records + len(result.b_records)
            if "复核" in result.status:
                need_review_count = need_review_count + 1
            if result.status == "未匹配" or result.status == "异常":
                unmatched_count = unmatched_count + 1

        return MatchSummary(
            total_a_records=len(a_records),
            matched_a_records=matched_a_records,
            matched_b_records=matched_b_records,
            need_review_count=need_review_count,
            unmatched_count=unmatched_count,
            inserted_rows=inserted_rows,
            results=results,
        )

    def read_a_records(self, worksheet: Worksheet, a_schema: SheetFieldSchema) -> list[ATableRecord]:
        """按照 LLM 识别出的 A 表字段读取明细记录。"""

        records: list[ATableRecord] = []
        for row_index in range(a_schema.detail_start_row, a_schema.detail_end_row + 1):
            product_value = excel_tool.clean_product_text(
                self.get_cell_value(worksheet, row_index, a_schema.product_field.column_index)
            )
            quantity = to_float(self.get_cell_value(worksheet, row_index, a_schema.quantity_field.column_index))
            unit_price = to_float(self.get_cell_value(worksheet, row_index, a_schema.unit_price_field.column_index))
            amount = to_float(self.get_cell_value(worksheet, row_index, a_schema.amount_field.column_index))
            date_value = self.get_cell_value(worksheet, row_index, a_schema.date_field.column_index)
            document_no = to_text(self.get_cell_value(worksheet, row_index, a_schema.document_no_field.column_index))

            if not product_value and quantity == 0 and amount == 0:
                continue

            record = ATableRecord(
                source_row=row_index,
                date_value=date_value,
                product_value=product_value,
                quantity=quantity,
                unit_price=unit_price,
                amount=amount,
                document_no=document_no,
            )
            records.append(record)

        return records

    def match_one_record(
        self,
        a_record: ATableRecord,
        c_row: int,
        b_records: list[BTableRecord],
        used_b_keys: set[str],
        product_lookup: ProductMappingLookup,
    ) -> MatchResult:
        """给一条 A/C 明细寻找最合适的 B 表匹配记录。"""

        direction = self.get_direction(a_record.quantity)
        if not direction:
            return MatchResult(
                a_row=a_record.source_row,
                c_row=c_row,
                status="异常",
                direction="",
                basis="数量为 0，不能判断入库或出库方向",
                review_type="零数量需复核",
                suggestion="请人工确认该行是否需要匹配 B 表系统记录",
            )

        available_records = self.filter_available_records(b_records, used_b_keys, direction)
        strict_match = self.find_single_match(a_record, available_records, product_lookup, require_same_date=True, require_product=True)
        if strict_match is not None:
            return MatchResult(
                a_row=a_record.source_row,
                c_row=c_row,
                status="已匹配",
                direction=direction,
                basis="同日期 + 同标准商品 + 数量一致 + 单价或金额一致",
                b_records=[strict_match],
            )

        date_review_match = self.find_single_match(
            a_record,
            available_records,
            product_lookup,
            require_same_date=False,
            require_product=True,
        )
        if date_review_match is not None:
            return MatchResult(
                a_row=a_record.source_row,
                c_row=c_row,
                status="已匹配/日期需复核",
                direction=direction,
                basis="同标准商品 + 数量一致 + 单价或金额一致，但日期不同",
                b_records=[date_review_match],
                review_type="日期需复核",
                suggestion="请人工确认 A 表日期和 B 表系统出入库时间差异是否合理",
            )

        spec_review_match = self.find_single_match(
            a_record,
            available_records,
            product_lookup,
            require_same_date=True,
            require_product=False,
        )
        if spec_review_match is not None:
            return MatchResult(
                a_row=a_record.source_row,
                c_row=c_row,
                status="已匹配/规格需复核",
                direction=direction,
                basis="同日期 + 数量一致 + 单价或金额一致，但商品规格未能严格确认",
                b_records=[spec_review_match],
                review_type="规格需复核",
                suggestion="请人工确认 A 表商品和 B 表规格是否属于同一商品",
            )

        date_spec_review_match = self.find_single_match(
            a_record,
            available_records,
            product_lookup,
            require_same_date=False,
            require_product=False,
        )
        if date_spec_review_match is not None:
            return MatchResult(
                a_row=a_record.source_row,
                c_row=c_row,
                status="已匹配/日期规格需复核",
                direction=direction,
                basis="数量一致 + 单价或金额一致，但日期和规格都需要人工确认",
                b_records=[date_spec_review_match],
                review_type="日期规格需复核",
                suggestion="请人工确认日期差异和商品规格差异是否合理",
            )

        multi_match = self.find_multi_match(a_record, available_records, product_lookup)
        if multi_match:
            return MatchResult(
                a_row=a_record.source_row,
                c_row=c_row,
                status="已匹配/多行需复核",
                direction=direction,
                basis="多条 B 表记录合计数量和金额匹配 A 表一行",
                b_records=multi_match,
                review_type="多行匹配需复核",
                suggestion="请人工确认这些 B 表明细是否共同对应同一条 A 表记录",
            )

        return MatchResult(
            a_row=a_record.source_row,
            c_row=c_row,
            status="未匹配",
            direction=direction,
            basis="未找到数量、金额、方向满足要求的 B 表记录",
            reason="核心字段无法匹配",
            suggestion="请检查 A 表商品、日期、数量、金额是否与 B 表系统记录一致",
        )

    def find_single_match(
        self,
        a_record: ATableRecord,
        candidates: list[BTableRecord],
        product_lookup: ProductMappingLookup,
        *,
        require_same_date: bool,
        require_product: bool,
    ) -> BTableRecord | None:
        """按单行条件查找一条 B 表记录。"""

        for b_record in candidates:
            if not self.hard_numbers_match(a_record, b_record):
                continue
            if require_same_date and not same_day(a_record.date_value, b_record.system_time):
                continue
            if require_product and not product_lookup.is_match(a_record.product_value, b_record.spec):
                continue
            return b_record
        return None

    def find_multi_match(
        self,
        a_record: ATableRecord,
        candidates: list[BTableRecord],
        product_lookup: ProductMappingLookup,
    ) -> list[BTableRecord]:
        """查找多条 B 表记录合计匹配一条 A 表记录的情况。"""

        product_candidates: list[BTableRecord] = []
        for b_record in candidates:
            if product_lookup.is_match(a_record.product_value, b_record.spec):
                product_candidates.append(b_record)

        same_date_records: list[BTableRecord] = []
        for b_record in product_candidates:
            if same_day(a_record.date_value, b_record.system_time):
                same_date_records.append(b_record)

        matched_records = self.find_total_match(a_record, same_date_records)
        if matched_records:
            return matched_records

        return self.find_total_match(a_record, product_candidates)

    def find_total_match(self, a_record: ATableRecord, candidates: list[BTableRecord]) -> list[BTableRecord]:
        """从候选 B 记录中寻找合计数量和金额匹配的一组记录。"""

        target_quantity = abs(a_record.quantity)
        target_amount = abs(a_record.amount)
        selected_records: list[BTableRecord] = []
        matched_records = self.search_total_match(
            candidates,
            selected_records,
            start_index=0,
            target_quantity=target_quantity,
            target_amount=target_amount,
            current_quantity=0.0,
            current_amount=0.0,
        )
        return matched_records

    def search_total_match(
        self,
        candidates: list[BTableRecord],
        selected_records: list[BTableRecord],
        start_index: int,
        target_quantity: float,
        target_amount: float,
        current_quantity: float,
        current_amount: float,
    ) -> list[BTableRecord]:
        """递归查找非连续 B 表组合，支持一条 A 记录对应多条 B 记录。"""

        if numbers_equal(current_quantity, target_quantity) and numbers_equal(current_amount, target_amount):
            if len(selected_records) > 1:
                return list(selected_records)
            return []

        if current_quantity > target_quantity + 0.01:
            return []
        if current_amount > target_amount + 0.01:
            return []

        for index in range(start_index, len(candidates)):
            b_record = candidates[index]
            # append(...)：先把当前候选放入组合，后面如果不合适再移除。
            selected_records.append(b_record)
            next_quantity = current_quantity + abs(b_record.quantity)
            next_amount = current_amount + abs(b_record.amount)
            matched_records = self.search_total_match(
                candidates,
                selected_records,
                index + 1,
                target_quantity,
                target_amount,
                next_quantity,
                next_amount,
            )
            if matched_records:
                return matched_records
            # pop(...)：回退当前选择，继续尝试后面的非连续组合。
            selected_records.pop()

        return []

    def hard_numbers_match(self, a_record: ATableRecord, b_record: BTableRecord) -> bool:
        """判断数量、金额、单价这些硬字段是否满足匹配要求。"""

        if not numbers_equal(abs(a_record.quantity), abs(b_record.quantity)):
            return False
        if numbers_equal(abs(a_record.amount), abs(b_record.amount)):
            return True
        if numbers_equal(abs(a_record.unit_price), abs(b_record.unit_price)):
            return True
        return False

    def filter_available_records(
        self,
        b_records: list[BTableRecord],
        used_b_keys: set[str],
        direction: str,
    ) -> list[BTableRecord]:
        """筛选还没有被 C 表承接、且方向一致的 B 表记录。"""

        result: list[BTableRecord] = []
        for record in b_records:
            if record.direction != direction:
                continue
            if record.trace_key() in used_b_keys:
                continue
            result.append(record)
        return result

    def write_match_result(self, worksheet: Worksheet, trace_start_column: int, match_result: MatchResult) -> None:
        """把匹配结果写入 C 表右侧追溯字段。"""

        if not match_result.b_records:
            self.write_one_trace_row(worksheet, match_result.c_row, trace_start_column, match_result, None)
            return

        for index, b_record in enumerate(match_result.b_records):
            row_index = match_result.c_row + index
            self.write_one_trace_row(worksheet, row_index, trace_start_column, match_result, b_record)

    def write_one_trace_row(
        self,
        worksheet: Worksheet,
        row_index: int,
        trace_start_column: int,
        match_result: MatchResult,
        b_record: BTableRecord | None,
    ) -> None:
        """写入一行 C 表追溯信息。"""

        values = self.build_trace_values(match_result, b_record)
        for index, value in enumerate(values):
            # cell(...)：按追溯字段位置逐列写入匹配结果。
            worksheet.cell(row=row_index, column=trace_start_column + index, value=value)

    def build_trace_values(self, match_result: MatchResult, b_record: BTableRecord | None) -> list[object]:
        """把匹配结果转换成 C 表追溯字段顺序的值列表。"""

        if b_record is None:
            return [
                match_result.status,
                match_result.basis,
                "",
                match_result.direction,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                match_result.review_type,
                match_result.suggestion,
            ]

        inbound_quantity: object = ""
        inbound_unit_price: object = ""
        inbound_amount: object = ""
        outbound_quantity: object = ""
        outbound_unit_price: object = ""
        outbound_amount: object = ""

        if b_record.direction == "入库":
            inbound_quantity = b_record.quantity
            inbound_unit_price = b_record.unit_price
            inbound_amount = b_record.amount
        else:
            outbound_quantity = b_record.quantity
            outbound_unit_price = b_record.unit_price
            outbound_amount = b_record.amount

        return [
            match_result.status,
            match_result.basis,
            b_record.source_row,
            b_record.direction,
            b_record.warehouse,
            b_record.system_time,
            b_record.document_no,
            b_record.sku,
            b_record.product_name,
            b_record.spec,
            inbound_quantity,
            inbound_unit_price,
            inbound_amount,
            outbound_quantity,
            outbound_unit_price,
            outbound_amount,
            match_result.review_type or b_record.risk_note,
            match_result.suggestion,
        ]

    def clear_inserted_business_cells(
        self,
        worksheet: Worksheet,
        start_row: int,
        end_row: int,
        original_max_column: int,
    ) -> None:
        """清空多行匹配插入行的 A 表原始业务列。"""

        for row_index in range(start_row, end_row + 1):
            for column_index in range(1, original_max_column + 1):
                # cell(...)：定位插入行中的 A 表原始列；value = None 表示清空内容。
                worksheet.cell(row=row_index, column=column_index).value = None

    def get_direction(self, quantity: float) -> str:
        """根据 A/C 表数量正负判断匹配方向。"""

        if quantity > 0:
            return "入库"
        if quantity < 0:
            return "出库"
        return ""

    def get_cell_value(self, worksheet: Worksheet, row_index: int, column_index: int) -> object:
        """安全读取 C 表单元格值。"""

        if column_index < 1:
            return None
        # cell(...)：用 LLM 返回的列号读取单元格。
        return worksheet.cell(row=row_index, column=column_index).value


def to_float(value: object) -> float:
    """把 Excel 单元格值安全转换成数字。"""

    if value is None or value == "":
        return 0.0
    try:
        # float(...)：把数字或数字字符串转成小数，便于数量金额比较。
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def to_text(value: object) -> str:
    """把 Excel 单元格值安全转换成文本。"""

    if value is None:
        return ""
    # str(...)：把单号数字等内容转成文本；strip(...)：去掉首尾空格。
    return str(value).strip()


def numbers_equal(left: float, right: float, tolerance: float = 0.01) -> bool:
    """按财务常用小误差判断两个数字是否一致。"""

    return abs(left - right) <= tolerance


def same_day(left: object, right: object) -> bool:
    """判断两个日期值是否是同一天。"""

    left_text = date_to_day_text(left)
    right_text = date_to_day_text(right)
    if not left_text or not right_text:
        return False
    return left_text == right_text


def date_to_day_text(value: object) -> str:
    """把日期值转换成 YYYY-MM-DD 文本，无法识别时返回空。"""

    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return text
