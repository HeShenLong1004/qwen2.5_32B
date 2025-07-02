# 项目名称

## 简介

本项目是一个基于Python的IoT设备控制和意图识别系统。它包括一个主要的服务运行脚本 `llm_build_serving.py`，以及两个模块：`intent_recognition.py`（意图识别模块）和 `device_control.py`（IoT控制模块）。项目还包含一个配置文件 `config.py`。

## 功能

- **意图识别**：通过 `intent_recognition.py` 模块识别用户的意图。
- **IoT控制**：通过 `device_control.py` 模块控制IoT设备。
- **服务运行**：通过 `llm_build_serving.py` 提供一个Web服务，用于交互和控制。

## 快速开始

配置：
在 config.py 文件中配置必要的参数，如数据库连接、API密钥等。

安装依赖包：

```bash
pip install -r requirements.txt
```

运行服务：
在终端中运行以下命令来启动服务：

```bash
gunicorn -w 8 --bind 0.0.0.0:10000 llm_build_serving:app
```

服务将在本地的10000端口运行，你可以通过访问 http://localhost:10000 来使用服务。



### 运行

```text
docker build -t llm:0.3 .
docker run -d -p 10000:10000 --name llm3 llm:0.3
curl --location 'http://localhost:10000/llm_intent' \
--header 'Content-Type: application/json' \
--data '{
    "dn": "C411E1019879",
    "log_id": "sdlc-fffe25156e814933943f64038cd2dbe4",
    "seq_id": 2,
    "asr_text": "",
    "ip_address": "58.250.250.123",
    "city": "广东省深圳市南山区科技南五路"
}'
```


