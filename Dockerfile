FROM pytorch/torchserve:0.12.0-gpu as builder

USER root

RUN apt-get update && apt-get install -y ffmpeg


# 设置工作目录
WORKDIR /app

# 将应用代码复制到工作目录
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV FLASK_APP app.py
# 设置 Flask 监听地址，因为容器内不使用0.0.0.0
ENV FLASK_RUN_HOST 0.0.0.0
ENV FLASK_RUN_PORT 5066

# 暴露端口
EXPOSE 5066

# 启动应用
CMD ["python","app.py"]


# 临时文件目录 -v temp:/app/temp 
# 模型目录 -v models:/app/models
# 日志目录 -v logs:/app/logs