# Reconciliation Agent Frontend

这是 `reconciliation-agent` 的前端工作台原型，使用 Vue 3、TypeScript 和 Vite 构建。

## 设计定位

首屏是“对账工作台”：用于快速查看今日对账状态、进入待处理差异队列，并为后续接入上传、匹配、复核、导出等业务能力预留结构。

视觉风格遵循 `docs/前端设计规范.md`：大量留白、低饱和浅背景、系统字体、轻材质、清晰层级、Lucide 图标，以及减少动效和减少透明度偏好支持。

## 安装

```bash
npm install
```

## 开发

```bash
npm run dev
```

## 类型检查

```bash
npm run type-check
```

## 构建

```bash
npm run build
```

## 预览生产构建

```bash
npm run preview
```

## 目录结构

```text
src/
  App.vue                         # 应用入口，只保留应用壳与页面选择
  main.ts                         # Vue 挂载与全局样式引入
  components/                     # 稳定通用组件
  data/                           # 首版静态数据，后续可替换为 API service
  pages/ReconciliationWorkbench.vue
  styles/                         # token、基础样式、页面样式
  types/                          # 工作台业务类型
```

## 后续扩展建议

- 接入真实后端前，先新增 service 层替换 `src/data/workbenchMock.ts`。
- 当页面数量超过一个时，再引入 `vue-router`。
- 当状态跨页面共享时，再引入 Pinia 或独立 composable。
- 上传、运行任务、下载结果应使用明确的加载、失败、成功和权限状态。
