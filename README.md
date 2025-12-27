# AutoGen Multi-Agent Collaboration Platform

这是一个基于 Vite + React 和 Python + AutoGen 的多智能体协作平台。

## 项目结构

- `frontend/`: 前端项目 (React + Vite)
- `backend/`: 后端项目 (Flask + AutoGen + PostgreSQL)

## 前置要求

请确保本地已安装以下软件：
1. **Node.js** (v18+): 用于运行前端。
2. **Python** (v3.10+): 用于运行后端。
3. **PostgreSQL**: 数据库。

## 快速开始

### 1. 配置后端

进入 `backend` 目录：
```bash
cd backend
```

创建并激活虚拟环境（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
```

安装依赖：
```bash
pip install -r requirements.txt
```

配置环境变量：
编辑 `backend/.env` 文件，填入你的 DeepSeek API Key 和数据库连接信息：
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/autogen_db
DEEPSEEK_API_KEY=sk-your-key-here
```
*注意：请确保 PostgreSQL 服务已启动，且 `autogen_db` 数据库已创建。*

运行后端：
```bash
python app.py
```
后端将在 `http://localhost:5000` 启动。

### 2. 配置前端

进入 `frontend` 目录：
```bash
cd frontend
```

安装依赖：
```bash
npm install
```

运行前端开发服务器：
```bash
npm run dev
```
前端将在 `http://localhost:5173` 启动。

## 使用说明

1. 打开浏览器访问前端地址 (通常是 http://localhost:5173)。
2. 进入 **智能体设置** 页面，创建几个智能体 (例如 "Product_Manager", "Coder", "Reviewer")。
3. 进入 **对话界面**，选择刚才创建的智能体，输入你的任务，点击发送。
4. 观察智能体之间的自动协作过程。

## 注意事项

- AutoGen 的运行可能需要较长时间，请耐心等待后端返回结果。
- 请确保 DeepSeek API Key 有足够的额度。
