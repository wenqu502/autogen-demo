# 使用多阶段构建
# 第一阶段：构建前端
FROM node:18-alpine as frontend_builder
WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/package.json frontend/package-lock.json* ./
# 安装依赖 (使用淘宝源以加快速度，可选)
RUN npm config set registry https://registry.npmmirror.com
RUN npm install

# 复制前端代码并构建
COPY frontend/ .
RUN npm run build

# 第二阶段：构建后端并运行
FROM python:3.9-slim
WORKDIR /app

# 安装后端依赖
COPY backend/requirements.txt backend/
# 使用清华源加速
RUN pip install --no-cache-dir -r backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制后端代码
COPY backend/ backend/

# 将前端构建产物复制到 Flask 的静态文件目录
# 1. 静态资源 (js, css) 放入 static
COPY --from=frontend_builder /app/frontend/dist/assets backend/static/assets
# 2. HTML 文件放入 templates (覆盖原有的 Fallback UI)
COPY --from=frontend_builder /app/frontend/dist/index.html backend/templates/index.html

# 设置环境变量
ENV FLASK_APP=backend/app.py
ENV PORT=8080
# 生产环境使用 SQLite (注意：重启容器数据会重置，生产建议连外部 PostgreSQL)
ENV DATABASE_URL=sqlite:///autogen.db

# 暴露端口
EXPOSE 8080

# 启动命令 (使用 gunicorn)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "backend.app:app"]
