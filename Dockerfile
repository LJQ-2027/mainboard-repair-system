# 智能主板维修系统 - Docker 镜像
# 构建: docker build -t mainboard-repair .
# 运行: docker run -p 8899:8899 -v ./data:/app/data mainboard-repair

FROM python:3.11-slim

WORKDIR /app

# 安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 复制前端构建产物
COPY frontend/dist/ ./frontend/dist/

# 创建数据目录（挂载点）
RUN mkdir -p /app/data

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PORT=8899

EXPOSE 8899

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8899/health')"

CMD ["python", "backend/run.py", "--host", "0.0.0.0"]
