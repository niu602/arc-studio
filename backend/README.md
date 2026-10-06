# ARC Studio Backend

包装 ARC (Agentic Requirement Compiler) 的 FastAPI 后端，提供 REST 接口：
自然语言 → 需求树 YAML → 异步编译 → 实时状态/日志 → 结果预览与下载。

ARC 编译器已**内置在本仓库 `../compiler` 目录**（`arc-compiler` 1.2.0），
因此整个项目是自包含的：把 `arc-studio/` 整体拷贝到任何一台 Windows
机器，按下方「评审环境准备」一键配置即可运行。

## 目录结构

```
arc-studio/
├── setup.ps1                # 一键创建 backend + compiler 两个虚拟环境
├── compiler/                # 内置的 ARC 编译器（pip install -e 安装）
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口（顶部加载 .env + sys.path 修复）
│   │   ├── config.py          # 配置（路径/端口/CORS/默认 LLM）
│   │   ├── models.py          # Pydantic 请求/响应模型
│   │   ├── routers/
│   │   │   ├── tree.py        # POST /api/generate-tree
│   │   │   ├── compile.py     # compile/status/result/cancel/download/history
│   │   │   └── demo.py        # GET /api/demo-download（演示模式代码包）
│   │   ├── services/
│   │   │   ├── task_manager.py    # 任务管理器（单例，含磁盘持久化）
│   │   │   ├── compiler.py        # subprocess 包装 + 日志解析
│   │   │   └── tree_generator.py  # 自然语言 → 需求树（LLM / 模板兜底）
│   │   └── utils/
│   │       └── yaml_helper.py     # 需求树 → 编译器 YAML
│   ├── demo_resources/
│   │   └── voice-calendar/    # 演示模式代码包源（语音日历项目源码）
│   ├── tasks/                 # 运行时生成：每个任务一个目录 + index.json
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
└── frontend/                  # React + TypeScript + Vite 前端
```

## 评审环境准备（Windows，一键）

前置条件：安装 **Python 3.11+**（已加入 PATH）。

```powershell
# 1. 项目根目录执行（arc-studio/）
powershell -ExecutionPolicy Bypass .\setup.ps1

# 2. 启动后端（backend/ 目录）
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# 3. 另开终端启动前端（frontend/ 目录）
cd frontend
npm install
npm run dev
```

- Swagger UI：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/health>（返回 `compiler_available`）
- 前端（Vite）运行在 <http://localhost:5173>，已配置 CORS。

> 注意：真实编译需要 OpenAI 兼容 API Key（`api_key`/`base_url`）。
> 没有 Key 时前端自动进入**演示模式**——内置「语音日历」需求树与
> 模拟编译动画，完整走通 生成 → 编译 → 结果预览 → 下载 全流程，
> 适合无预算现场演示。

## 环境变量（backend/.env，可全部省略）

复制 `.env.example` 为 `.env` 后按需修改；`main.py` 启动时自动加载。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `COMPILER_PYTHON` | `../compiler/.venv/Scripts/python.exe` | 编译器解释器（相对项目自动定位） |
| `COMPILER_MAIN` | `../compiler/src/main.py` | 编译器入口 |
| `VOICE_CALENDAR_SOURCE_DIR` | `backend/demo_resources/voice-calendar` | 演示代码包源目录（可指向外部副本） |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 允许的前端来源 |
| `ARC_WEB_PORT_START` | `3301` | 首个编译产物的预览端口 |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | 空 | 需求树生成的默认 LLM（空则用内置模板） |

## API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/generate-tree` | 自然语言 → 结构化需求树 JSON（含编译器 YAML） |
| POST | `/api/compile` | 创建编译任务，返回 `task_id` |
| GET | `/api/status/{task_id}?since=N` | 查询进度/节点状态/日志/估算成本（增量） |
| GET | `/api/result/{task_id}` | 预览 URL、测试结果、汇总（含成本） |
| POST | `/api/cancel/{task_id}` | 取消正在运行的编译 |
| GET | `/api/download/{task_id}` | 下载输出目录 zip |
| GET | `/api/history` | 编译历史（重启后仍保留，磁盘持久化） |
| GET | `/api/demo-download` | 演示模式代码包 zip（永不 404） |

### 示例：生成需求树

```powershell
curl -X POST http://localhost:8000/api/generate-tree `
  -H "Content-Type: application/json" `
  -d '{"requirement":"我要一个待办清单应用，能添加任务、打勾完成、删除任务","app_type":"web"}'
```

未配置 `OPENAI_API_KEY` 时自动使用内置模板（响应 `source: "mock"`）。

### 示例：启动编译

```powershell
curl -X POST http://localhost:8000/api/compile `
  -H "Content-Type: application/json" `
  -d '{
        "requirement_text":"待办清单应用：添加、完成、删除任务",
        "app_type":"web",
        "api_key":"sk-xxx",
        "base_url":"https://api.deepseek.com/v1"
      }'
```

> 真正跑通编译需要有效的 `api_key` / `base_url`；接口逻辑与日志捕获在无
> key 时也能走通（任务会快速失败并记录日志）。

## 工作原理

- **任务管理**：`TaskManager` 单例在内存中维护所有任务；状态机
  `PENDING → RUNNING → COMPLETED / FAILED / CANCELLED`；日志为环形缓冲
  （默认保留最近 1000 条）。
- **持久化**：任务元数据（不含 API Key、不含运行进程）在创建与终态时
  写入 `tasks/index.json`；服务重启后 `/api/history` 保留记录，中途任务
  标记为 FAILED（进程已随服务终止）。
- **成本估算**：每个节点首次进入终态（PASSED/FAILED）时按阶段单价累加
  （DESIGN ¥0.010 / IMPLEMENT ¥0.015 / TEST ¥0.006），与演示模式量级一致。
- **异步执行**：每个编译任务在一个 daemon 线程中通过 `subprocess.Popen`
  调用编译器 CLI，逐行读取 stdout/stderr 写入日志，并启发式解析节点 ID
  （`REQ-x-y`）与状态（PASSED/FAILED/RUNNING）。
- **端口分配**：首个 web 预览端口从 `3301` 开始递增，避免多任务冲突。
- **需求树 → YAML**：LLM（OpenAI 兼容 `chat/completions`）优先，失败时
  回退到按关键词选择的内置模板；再由 `yaml_helper.tree_to_compiler_yaml`
  转成编译器接受的递归 YAML（根节点 `ROOT` / `FOLDER`，叶子 `ATOMIC` +
  `scenarios`）。
