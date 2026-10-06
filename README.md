# ARC Studio — AI 应用编译工作台

> **输入一句大白话需求，AI 自动输出可运行的全栈应用。** 三个专业 AI Agent 协作完成设计、测试和开发全流程。

**参赛信息**：天猫 AI 黑客松·高校挑战赛 ｜ 赛道：效率进化 ｜ 作者：niu602

---

## 核心功能

- **自然语言需求输入**：不用写代码，用大白话描述你想要的应用
- **AI 自动拆解需求树**：把需求拆成层级功能点，用户确认后开始编译
- **三 Agent 协作编译**：架构师（设计）→ 测试工程师（生成测试）→ 开发工程师（TDD 实现）
- **模型阶梯策略**：三个阶段自由搭配不同模型，实时成本对比，省 60%+
- **实时编译可视化**：节点逐个变色、实时日志滚动、进度条、统计面板
- **结果预览与下载**：编译完成后在线预览应用，可下载完整源码
- **演示模式**：无需 API Key，内置语音日历模板，零门槛体验完整流程

---

## 目录结构

```
arc-studio/
├── frontend/           # 前端（React 18 + TypeScript + Vite + Ant Design 5）
│   └── src/
│       ├── pages/      # 6 个页面：首页/创建项目/模型配置/编译运行/结果页/历史记录
│       ├── components/ # 组件：布局/需求树/日志控制台
│       ├── services/   # API 调用
│       ├── mock/       # 演示模式 mock 数据
│       └── context/    # 全局状态
├── backend/            # 后端（Python FastAPI）
│   └── app/
│       ├── routers/    # 路由：compile / tree / demo
│       ├── services/   # 服务：编译器管理 / 任务管理 / 需求树生成
│       ├── models.py   # 数据模型
│       ├── config.py   # 配置
│       └── main.py     # 入口
├── compiler/           # ARC 编译器（Python + LangGraph，三 Agent 协作核心）
│   └── src/            # 编译器源码
├── product-brief/      # 提交材料
│   ├── ARC Studio 产品说明书.pdf
│   ├── ARC Studio 演示视频-配音版.mp4
│   ├── ARC Studio 演示视频-干净版.mp4
│   └── 演示视频解说稿.md
├── setup.ps1           # 一键环境准备脚本（Windows）
├── 项目介绍.md          # 完整项目介绍（覆盖全部评分维度）
└── README.md           # 本文件
```

---

## 快速启动

### 环境要求

- Python 3.11+
- Node.js 18+（含 npm）
- Windows 10/11

### 1. 一键准备环境

在项目根目录打开 PowerShell，运行：

```powershell
powershell -ExecutionPolicy Bypass .\setup.ps1
```

脚本会自动：
- 为 backend 创建虚拟环境并安装依赖
- 为 compiler 创建虚拟环境并安装编译器

### 2. 启动后端

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

后端运行在 `http://localhost:8000`，API 文档：`http://localhost:8000/docs`

### 3. 启动前端（新开一个终端）

```powershell
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:5173`

---

## 演示模式（无需 API Key）

如果没有 API Key，可以使用演示模式体验完整流程：

1. 打开 `http://localhost:5173`
2. 进入「模型配置」页，开启「演示模式」开关
3. 进入「创建项目」页，点击「使用语音日历模板」
4. 点击「生成需求框架」→ 确认 → 「开始编译」
5. 观看 18 秒模拟编译过程（节点变色、日志滚动）
6. 编译完成后查看结果页（应用预览 + 代码下载）

演示模式下所有数据均为前端模拟，不调用任何 AI API，不产生任何费用。

---

## 真实编译模式（需要 API Key）

1. 在「模型配置」页关闭演示模式
2. 填写你的 API Key 和 Base URL（支持 DeepSeek / Qwen / GLM 等 OpenAI 兼容接口）
3. 三个阶段分别选择模型（设计/测试/开发）
4. 创建项目 → 生成需求树 → 开始编译
5. 后端会拉起真实的 ARC 编译器，调用 AI API 进行真实编译
6. 编译完成后自动启动预览服务器，可在线查看生成的真实应用

> API Key 仅存储在浏览器 localStorage 中，服务器不保存任何 Key。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端框架 | React 18 + TypeScript + Vite |
| UI 库 | Ant Design 5 |
| 需求树可视化 | cytoscape.js + dagre 布局 |
| 后端框架 | Python FastAPI |
| Agent 框架 | LangGraph |
| 模型网关 | OpenAI 兼容接口（多模型混用） |
| 编译器输出 | React + Express / FastAPI + SQLite |
| 测试 | Vitest + Playwright + pytest |
| 并发 | asyncio + 信号量 |
| 支持模型 | DeepSeek / Qwen / GLM 等 |

---

## AI 应用能力亮点

- **三 Agent 专业分工**：InterfaceDesigner（架构师）/ TestGenerator（测试工程师）/ TestDrivenDeveloper（开发工程师）
- **模型阶梯策略**：按阶段选最合适的模型，比全用顶级模型省 60%+ 成本
- **Fallback 自动升级**：便宜模型跑不动自动换强模型重试
- **上下文缓存复用**：缓存命中率 97.6%，大幅降低 token 消耗
- **熔断止损机制**：连续失败自动停止，分层预算控制成本
- **需求树增量编译**：按依赖关系逐个节点编译，失败只重跑失败节点

---

## 真实运行数据（ARC-Bench 实测）

| 指标 | 数值 |
|---|---|
| 总节点数 | 65（完整 GitHub 协作平台需求树） |
| 通过节点 | 25 个（~60% 通过率） |
| 编译时长 | ~2.5 小时 |
| 总成本 | ~¥140 |
| 缓存命中率 | 97.6% |

---

## 许可证

MIT License
