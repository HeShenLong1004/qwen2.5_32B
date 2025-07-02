# 使用 Python 3.12.8 作为基础镜像
FROM python:3.12.8-slim

# 安装必要的系统依赖（ARMS 探针可能需要一些系统工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    curl \
    telnet \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制 requirements.txt 文件到容器中
COPY requirements.txt .

# 安装 Python 依赖
# 使用阿里云镜像源加速 pip 安装
RUN pip install -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt

##########################################################################

# 复制当前目录的所有文件到工作目录
COPY . .

# 暴露端口
EXPOSE 10000

# 使用 gunicorn 启动应用，配置参数 -w 8 (8个工作进程) 和 --bind 0.0.0.0:10000 (绑定到0.0.0.0的10000端口)
CMD ["gunicorn", "-w", "8", "--bind", "0.0.0.0:10000", "llm_build_serving:app"]