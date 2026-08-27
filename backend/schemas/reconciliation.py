from __future__ import annotations

from tools import ExcelSheetPreview


def preview_to_response(preview: ExcelSheetPreview) -> dict[str, object]:
    """Convert an Excel preview into the JSON shape consumed by the frontend."""

    return {
        "sheet_name": preview.sheet_name,
        "max_row": preview.max_row,
        "max_column": preview.max_column,
        "rows": [
            {
                "row_number": row.row_number,
                "cells": [
                    {
                        "coordinate": cell.coordinate,
                        "column": cell.column,
                        "value": cell.display_text,
                        "python_type": cell.python_type,
                        "excel_data_type": cell.excel_data_type,
                        "number_format": cell.number_format,
                        "is_date": cell.is_date,
                    }
                    for cell in row.cells
                ],
            }
            for row in preview.rows
        ],
    }
