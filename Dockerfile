# 使用官方 Python 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000

# 安装系统依赖 (编译某些 Python 包可能需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制后端依赖文件
COPY backend/requirements.txt .

# 安装 Python 依赖
# 升级 pip 并安装依赖，添加 --no-cache-dir 减小镜像体积
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制整个项目代码
COPY backend/ backend/

# 创建非 root 用户运行 (安全最佳实践)
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 暴露端口
EXPOSE 10000

# 启动命令
# 注意：CMD 列表格式更安全
CMD ["gunicorn", "--chdir", "backend", "--bind", "0.0.0.0:10000", "app:app"]
