# Stage 1: Build Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
# 复制 package.json 和 lock 文件
COPY frontend/package.json frontend/package-lock.json* ./
# 安装依赖
RUN npm install
# 复制源代码
COPY frontend/ ./
# 构建生产环境代码
RUN npm run build

# Stage 2: Setup Backend with Python
FROM python:3.11-slim
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制后端依赖
COPY backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ backend/

# 关键步骤：从第一阶段复制构建好的前端静态文件到后端的 static 和 templates 目录
# 假设 Vite 构建输出在 frontend/dist
# 我们将 dist/index.html 放到 backend/templates/
# 将 dist/assets (或其他静态资源) 放到 backend/static/
COPY --from=frontend-builder /app/frontend/dist/index.html /app/backend/templates/index.html
COPY --from=frontend-builder /app/frontend/dist/assets /app/backend/static/assets
# 如果 dist 根目录还有其他文件（如 favicon.ico），也需要复制
COPY --from=frontend-builder /app/frontend/dist/ /app/backend/static/

# 创建非 root 用户
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 暴露端口
EXPOSE 10000

# 启动命令
CMD ["gunicorn", "--chdir", "backend", "--bind", "0.0.0.0:10000", "app:app"]
