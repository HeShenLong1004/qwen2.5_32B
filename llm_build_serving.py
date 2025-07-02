import os
import pandas as pd
import json
import time
from device_control import *
from intent_recognition import intent_recognition
from flask import Flask, request, jsonify
import uuid
from datetime import datetime
from config import skill_name, command_name, setup_logger, llm_model_name, question_scene
import requests
import redis
import random
import concurrent.futures
from qqwry import QQwry
import logging
import numpy as np
from tqdm import tqdm
# from embedding_model import embed_with_list_of_str

def get_location_by_ip(ip):
    response = requests.get(f'http://ipinfo.io/{ip}/json')
    if response.status_code == 200:
        data = response.json()
        return data.get('city','深圳')
    else:
        return 

app = Flask(__name__)

# 获取 Werkzeug 的日志记录器
werkzeug_logger = logging.getLogger("werkzeug")

@app.before_request
def disable_logging_for_health_check():
    # 动态禁用特定路径的日志
    if request.path == "/intent/healthCheck":
        werkzeug_logger.disabled = True
    else:
        werkzeug_logger.disabled = False

logger = setup_logger('llm serving','serving.log')

q = QQwry()
q.load_file('qqwry.dat')

r = None
embedding_url = None
token_url = None
device_list_url = None
scene_list_url = None

env = "testk8s"#os.getenv("APP_ENV", "test")
if env == "prod": # 此redis是: gnailab_redis_2024
    embedding_url = "http://localhost:6666/embedding"
    token_url = "https://prod-auth.iotbull.com/auth/oauth2/token"
    device_list_url = "https://skill.iotbull.com/skill/ai/voice/device/list"
    scene_list_url = "https://skill.iotbull.com/skill/ai/voice/scene/list"
    r = redis.Redis(
        host='r-uf6lg8sdnxfeyu3n4k.redis.rds.aliyuncs.com',  # 阿里云 Redis 实例地址
        port=6379,  # Redis 端口
        password='Gnailab2024aaa333',  # Redis 密码
        db=0,  # 使用的数据库编号
        decode_responses=False  # 如果需要返回字符串而不是字节，可以设置这个选项为 True
    )
    logger.info("current env is prod")
elif env == "prodk8s":
    embedding_url = "http://embedding-service-svc-prod:8080/embedding"
    token_url = "https://prod-auth.iotbull.com/auth/oauth2/token"
    device_list_url = "http://prod-iothub.gn-gpt.com:8006/skill/ai/voice/device/list"
    scene_list_url = "http://prod-iothub.gn-gpt.com:8006/skill/ai/voice/scene/list"
    r = redis.Redis(
        host='r-uf6lg8sdnxfeyu3n4k.redis.rds.aliyuncs.com',  # 阿里云 Redis 实例地址
        port=6379,  # Redis 端口
        password='Gnailab2024aaa333',  # Redis 密码
        db=0,  # 使用的数据库编号
        decode_responses=False  # 如果需要返回字符串而不是字节，可以设置这个选项为 True
    )
    logger.info("current env is prodk8s")
elif env == "testk8s":
    embedding_url = "http://172.16.100.215:8080/embedding"
    token_url = "https://prod-auth.iotbull.com/auth/oauth2/token"
    device_list_url = "http://prod-iothub.gn-gpt.com:8006/skill/ai/voice/device/list"
    scene_list_url = "http://prod-iothub.gn-gpt.com:8006/skill/ai/voice/scene/list"
    # token_url = "https://dev-auth.iotbull.com/auth/oauth2/token"
    # device_list_url = "http://dev-iothub.gn-gpt.com:8006/skill/ai/voice/device/list"
    # scene_list_url = "http://dev-iothub.gn-gpt.com:8006/skill/ai/voice/scene/list"
    r = redis.Redis(
        host='r-uf6z3kih12q9xdk3r4.redis.rds.aliyuncs.com',  # 阿里云 Redis 专有网络 实例地址
        port=6379,  # Redis 端口
        password='Gnailab2024aaa333',  # Redis 密码
        db=0,  # 使用的数据库编号
        decode_responses=False  # 如果需要返回字符串而不是字节，可以设置这个选项为 True
    )
    logger.info("current env is testk8s")
else: # test
    embedding_url = "http://localhost:6666/embedding"
    token_url = "https://dev-auth.iotbull.com/auth/oauth2/token"
    device_list_url = "https://test-skill.iotbull.com/skill/ai/voice/device/list"
    scene_list_url = "https://test-skill.iotbull.com/skill/ai/voice/scene/list"
    r = redis.Redis(
        host='r-uf6z3kih12q9xdk3r4.redis.rds.aliyuncs.com',  # 阿里云 Redis 专有网络 实例地址
        port=6379,  # Redis 端口
        password='Gnailab2024aaa333',  # Redis 密码
        db=0,  # 使用的数据库编号
        decode_responses=False  # 如果需要返回字符串而不是字节，可以设置这个选项为 True
    )
    logger.info("current env is test")


class CustomError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

def get_access_token():
    # 定义请求头
    headers = {
        'Authorization': 'Basic cGFhc2Nsb3VkY2xpZW50dWljYWlsYWI6JDJhJDEwJDZmU0VQN2VXRUd1RVovei8yaC45bE9ndFNOc2FVcnF0VU9ISjlOSTJMTHpncmVyL1JBb1Fh',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    # 定义请求数据
    data = {
        'scope': 'server',
        'grant_type': 'client_credentials'
    }

    # 发送POST请求
    logger.info(f'request token_url: {token_url}')
    response = requests.post(token_url, headers=headers, data=data)

    # 打印响应内容
    access_token = response.json()['access_token']
    return access_token

def cosine_similarity(vector_a, vector_b):
    dot_product = np.dot(vector_a, vector_b)
    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)
    if norm_a == 0 or norm_b == 0:
        return 0  # 避免除以零的情况
    return dot_product / (norm_a * norm_b)

def user_info(dn,unique_id,seq_id):
    value = r.get(f'deviceList_{dn}_{unique_id}')
    cache = False
    if value:
        redis_json = json.loads(value)
        user_data = pd.DataFrame(redis_json['result'])
        select_data = user_data[(user_data['deviceName'] == dn) & (user_data['element'] == 'PowerSwitch')]
        local = select_data['roomName'].values[0]
        user_home = select_data['familyName'].values[0]
        cache = True
    else:
        user_data_url = f"{device_list_url}?deviceName={dn}&logId={unique_id}&seqId={seq_id}"
        # 定义请求头
        headers = {
            'Content-Type': 'application/json'
        }
        # 发送GET请求
        response = requests.get(user_data_url, headers=headers)
        response_json = response.json()
        user_data = pd.DataFrame(response_json['result'])
        print(response_json)
        select_data = user_data[(user_data['deviceName'] == dn) & ((user_data['element'] == 'PowerSwitch') | (user_data['element'] == 'PowerSwitch_1'))]
        local = select_data['roomName'].values[0]
        user_home = select_data['familyName'].values[0]
    return user_data,user_home,local,cache

def lighting_scene(dn,unique_id,seq_id):
    value = r.get(f'sceneList_{dn}_{unique_id}')
    cache = False
    if value:
        redis_json = json.loads(value)
        scene_list = redis_json['result']
        cache = True
    else:
        # 定义Mock地址
        url = f"{scene_list_url}?deviceName={dn}&logId={unique_id}&seqId={seq_id}"

        # 定义请求头
        headers = {
            'Content-Type': 'application/json'
        }
        # 发送GET请求
        logger.info(f'request scene_list_url: {url}')
        response = requests.get(url, headers=headers)
        scene_list = response.json()['result']

    if cache:
        logger.info(f'log id:{unique_id},seq id:{seq_id}。命中用户家庭的场景模式缓存')
    else:
        logger.info(f'log id:{unique_id},seq id:{seq_id}。未命中用户家庭的场景模式缓存，继续调用接口查询')
    logger.info(f'log id:{unique_id},seq id:{seq_id}。用户家庭的场景模式：{scene_list}')

    return scene_list

def get_embedding_from_redis(key):
    # Build the full Redis key
    redis_key = 'embedding_v1:' + key
    # Fetch embedding from Redis; returns None if the key does not exist
    embedding = r.get(redis_key)
    if embedding:
        # Refresh expiration to one week (604800 seconds)
        r.expire(redis_key, 604800)
        return np.frombuffer(embedding, dtype=np.float32)
    return None

def batch_get_embeddings_from_redis(keys):
    pipe = r.pipeline()
    for key in keys:
        pipe.get('embedding_v1:' + key)
    embeddings = pipe.execute()
    
    scene_embed_dict = {}
    missing_keys = []
    existing_keys = []  # To collect keys that were found

    # Process the results and refresh TTL for each found key
    for embedding, key in zip(embeddings, keys):
        if embedding is None:
            missing_keys.append(key)
        else:
            scene_embed_dict[key]=np.frombuffer(embedding, dtype=np.float32)
            existing_keys.append(key)
    
    # Refresh expiration on all keys that exist using another pipeline
    if existing_keys:
        expire_pipe = r.pipeline()
        for key in existing_keys:
            expire_pipe.expire('embedding_v1:' + key, 604800)
        expire_pipe.execute()
    
    return scene_embed_dict, missing_keys

def save_embedding_to_redis(key, embedding):
    # Save embedding to Redis as bytes and set expiration to one week (604800 seconds)
    # Using the 'ex' parameter to set expiry time directly
    r.set('embedding_v1:' + key, embedding.tobytes(), ex=604800)

def embed_with_list_of_str(text_list):
    headers = {"Content-Type": "application/json","Authorization":"Bearer 3jK8Lm#9qX2p@Vf7GhT5yN1bR4sW6eD!QzXcVbNmGhJkL"}
    data = {
        "texts": text_list
    }
    try:
        logger.info(f'request embedding_url: {embedding_url}')
        response = requests.post(embedding_url, json=data, headers=headers)
        if response.status_code == 200:
            return  response.json()
        else:
            logger.error(f"请求失败:{response.text}")
            return None
    except Exception as e:
        logger.error("embedding服务请求异常: %s", str(e))
        return None

def is_opposite_meaning(text1, text2):
    open_words = ['开', '打开']
    close_words = ['关', '关闭']

    is_text1_open = any(w in text1 for w in open_words)
    is_text2_close = any(w in text2 for w in close_words)

    is_text2_open = any(w in text2 for w in open_words)
    is_text1_close = any(w in text1 for w in close_words)

    return (is_text1_open and is_text2_close) or (is_text2_open and is_text1_close)

def scene_instruct(input_text, scene_list, local, unique_id, seq_id, threshold=0.6):
    # state 可以保存重复 key
    state = {}
    scene_type_mapping = {}
    answer_scene_map = {}
    scene_id_to_info = {}

    # 构建映射
    for scene_info in scene_list:
        sid = str(scene_info['sceneId'])
        scene_type_mapping[sid] = scene_info.get('sceneType', 1)
        scene_id_to_info[sid] = scene_info

        sceneName = scene_info['sceneName'].replace('场景','').replace('模式','')
        customName = scene_info.get('customLightEffectName', scene_info['sceneName'])\
                        .replace('场景','').replace('模式','')
        room = scene_info.get('roomName', '')
        if sceneName!=customName:
            names = (sceneName, customName)
        else:
            names = [sceneName]
        # 基础描述与动词 + 后缀组合
        for name in names:
            for suffix in ['场景','模式','']:
                if '开' in name or '关' in name:
                    key = f'{name}{suffix}'
                    state.setdefault(key, []).append(f'{sid}:1')
                    answer_scene_map.setdefault(key, []).append(scene_info['sceneName'])
                else:
                    for verb in ['','打开','执行']:
                        key = f'{verb}{name}{suffix}'
                        state.setdefault(key, []).append(f'{sid}:1')
                        answer_scene_map.setdefault(key, []).append(scene_info['sceneName'])

        # roomName 前缀方式
        if room:
            for name in names:
                for suffix in ['场景','模式','']:
                    if '开' in name or '关' in name:
                        if room not in name:
                            key = f'{room}{name}{suffix}'
                            state.setdefault(key, []).append(f'{sid}:1')
                            answer_scene_map.setdefault(key, []).append(scene_info['sceneName'])    
                    else:
                        for verb in ['','打开','执行']:
                            if room not in name:
                                key = f'{verb}{room}{name}{suffix}'
                                state.setdefault(key, []).append(f'{sid}:1')
                                answer_scene_map.setdefault(key, []).append(scene_info['sceneName'])

        # 自定义问法
        for key_scene in (scene_info['sceneName'], scene_info.get('customLightEffectName','')):
            for q in question_scene.get(key_scene, []):
                state.setdefault(q, []).append(f'{sid}:1')
                answer_scene_map.setdefault(q, []).append(key_scene)

    # 展平键与值
    keys_list = []
    vals_list = []
    for key, vals in state.items():
        for v in vals:
            keys_list.append(key)
            vals_list.append(v)

    # 获取 Redis embeddings
    get_redis_start = time.time()
    scene_embed_dict, missing_keys = batch_get_embeddings_from_redis(keys_list)
    get_redis_end = time.time()
    logger.info(f'log id:{unique_id},seq id:{seq_id}。查询redis耗时：{get_redis_end-get_redis_start}s')

    missing_keys.append(input_text)
    miss_start = time.time()
    if missing_keys:
        logger.info(f'log id:{unique_id},seq id:{seq_id}。没在redis里面的数据需要调用 embedding：{missing_keys}')
        emb_result = embed_with_list_of_str(missing_keys)
        if emb_result is None:
            logger.error(f'log id:{unique_id},seq id:{seq_id}。查询 embedding 模型结果为空')
            return {"code":500, "error":"Embedding 请求失败"}
        if 'output' not in emb_result or 'embeddings' not in emb_result['output']:
            logger.error(f'log id:{unique_id},seq id:{seq_id}。embedding 模型响应格式错误')
            return {"code":500, "error":"响应格式错误"}
        new_embs = [np.array(e['embedding'], dtype=np.float32) for e in emb_result['output']['embeddings']]
        for i, key in enumerate(missing_keys[:-1]):
            #save_embedding_to_redis(key, new_embs[i])
            scene_embed_dict[key] = new_embs[i]
        input_emb = new_embs[-1]
    else:
        logger.info(f'log id:{unique_id},seq id:{seq_id}。当前用户问题 embedding 表征：{input_text}')
        input_emb = embed_with_list_of_str([input_text])['output']['embeddings'][0]['embedding']
    miss_end = time.time()
    logger.info(f'log id:{unique_id},seq id:{seq_id}。所有文本 embedding 表征耗时：{miss_end-miss_start}s')

    # 构造场景 embeddings
    scene_embs = np.array([scene_embed_dict.get(k) for k in keys_list])
    start_cos = time.time()
    cosine_scores = np.array([cosine_similarity(input_emb, v) for v in scene_embs])
    max_val = np.max(cosine_scores)
    max_idxs = np.where(cosine_scores == max_val)[0]
    end_cos = time.time()
    logger.info(f'log id:{unique_id},seq id:{seq_id}。余弦相似度最大的索引：{max_idxs}')
    logger.info(f'log id:{unique_id},seq id:{seq_id}。余弦相似度计算耗时：{end_cos-start_cos}s')

    # 优先匹配本地 room
    best_idx = None
    for idx in max_idxs:
        sid, _ = vals_list[idx].split(':')
        if scene_id_to_info[sid].get('roomName','') == local:
            best_idx = idx
            logger.info(f'log id:{unique_id},seq id:{seq_id}。语音设备房间{local}，命中场景房间：{best_idx}')
            break
    if best_idx is None:
        best_idx = int(max_idxs[0]) if max_idxs.size else -1
        logger.info(f'log id:{unique_id},seq id:{seq_id}。语音设备房间{local}，未命中场景房间：{best_idx}')

    # 判断阈值并返回
    if best_idx != -1 and cosine_scores[best_idx] >= threshold and not is_opposite_meaning(input_text,keys_list[best_idx]):
        key = keys_list[best_idx]
        sid, val = vals_list[best_idx].split(':')
        scene_type = scene_type_mapping.get(sid,1)
        matched = answer_scene_map.get(key, ['未知'])[0]
        replies = [f'已为你找到{matched}', f'正在跑步前去帮您执行{matched}']
        reply = random.choice(replies)
        logger.info(f'log id:{unique_id},seq id:{seq_id}。最匹配场景：{key}，相似度分数：{cosine_scores[best_idx]}')
        return {
            "code":200,
            "msg":"success",
            "data":{
                "type":"scene",
                "query":input_text,
                "ability_pool":{},
                "iot_detail":{
                    "scene_id":sid,
                    "value":int(val),
                    "sceneType":scene_type,
                    "reply":reply
                }
            }
        }
    else:
        return {}
    
def pre_emb_question_scene(question_scene):
    logger.info('正在进行场景文本预表征......')
    miss_question_list = []
    for k,v in question_scene.items():
        for question in v:
            embedding = get_embedding_from_redis(question)
            if not np.any(embedding):
                miss_question_list.append(question)
    if miss_question_list:
        emb_result = embed_with_list_of_str(miss_question_list)
        new_embeddings = [np.array(emb['embedding'], dtype=np.float32) for emb in emb_result['output']['embeddings']]
        for i in tqdm(range(len(new_embeddings))):
            save_embedding_to_redis(miss_question_list[i], new_embeddings[i])
    logger.info('表征结束......')

def main(dn, input_text, ip_address, city, open_migu, history, unique_id, seq_id):
    # Start music control check
    instruct = music_control(input_text)
    if instruct:
        return instruct
    # Retrieve user data
    start4 = time.time()
    try:
        user_data, user_home, local, cache = user_info(dn, unique_id, seq_id)
    except Exception as e:
        logger.error(f'log id:{unique_id},seq id:{seq_id}。iot get user device list error：{str(e)}')
        return {"code":400,"msg":f'log id:{unique_id},seq id:{seq_id}。iot get user device list error：{str(e)}',"data":{}}

    end4 = time.time()
    if cache:
        logger.info(f'log id:{unique_id},seq id:{seq_id}。用户dn：{dn}，用户数据命中缓存。用户数据查询耗时：{end4 - start4}s')
    else:
        logger.info(f'log id:{unique_id},seq id:{seq_id}。用户dn：{dn}，缓存没命中，请求用户数据接口。用户数据查询耗时：{end4 - start4}s')
    logger.info(f'log id:{unique_id},seq id:{seq_id}。用户设备信息：{json.dumps(user_data.to_dict("records"), ensure_ascii=False)}')

    # Start scene list retrieval for scene_instruct
    scene_start = time.time()
    try:
        scene_list = lighting_scene(dn, unique_id, seq_id)
    except Exception as e:
        logger.error(f'log id:{unique_id},seq id:{seq_id}。iot get scene error：{str(e)}')
        return {"code":400,"msg":f'log id:{unique_id},seq id:{seq_id}。iot get scene error：{str(e)}',"data":{}}
    
    scene_end = time.time()
    logger.info(f'log id:{unique_id},seq id:{seq_id}。用户场景接口查询耗时：{scene_end-scene_start}s')
    # Prepare data for intent_recognition call
    now = datetime.now()
    date = f"今天的日期是：{now.year}年{now.month}月{now.day}日"
    # Initialize logger timings
    scene_start = time.time()
    if not scene_list:  # If scene_list is empty, skip parallel execution
        # Directly call intent_recognition
        start_intent = time.time()
        content,intent_cache = intent_recognition(input_text, ip_address, date, history, r, unique_id, seq_id, logger, model=llm_model_name)
        end_intent = time.time()
        logger.info(f'log id:{unique_id},seq id:{seq_id}。意图识别耗时：{end_intent - start_intent}s')
        logger.info(f'log id:{unique_id},seq id:{seq_id}。意图识别结果：{content}')
    else:
        scene_output = scene_instruct(input_text, scene_list, local, unique_id, seq_id, 0.92)
        scene_end = time.time()
        if scene_output:
            logger.info(f'log id:{unique_id},seq id:{seq_id}。场景指令结果：{scene_output}')
            logger.info(f'log id:{unique_id},seq id:{seq_id}。场景匹配成功,耗时：{scene_end - scene_start}s')
            return scene_output  # Return immediately if scene_output has a result
        else:
            logger.info(f'log id:{unique_id},seq id:{seq_id}。场景匹配耗时：{scene_end - scene_start}s')
            logger.info(f'log id:{unique_id},seq id:{seq_id}。场景未命中，进行大模型意图识别模块')
            start1 = time.time()
            content,intent_cache = intent_recognition(input_text, ip_address, date, history, r, unique_id, seq_id, logger, model=llm_model_name)
            end1 = time.time()
            logger.info(f'log id:{unique_id},seq id:{seq_id}。意图识别耗时：{end1 - start1}s')
            logger.info(f'log id:{unique_id},seq id:{seq_id}。意图识别结果：{content}')
    
    # Continue with the rest of the logic if no scene_output
    start2 = time.time()
    input_text = content['text']
    # Generate lighting control command
    output = lighting_control_command_synthesis(input_text, user_data, user_home, local, ip_address, city, open_migu, date, content, llm_model_name, unique_id, seq_id, logger)
    end2 = time.time()
    if intent_cache and end2-start2<=0.05:
        output['data']['fast'] = True
    else:
        output['data']['fast'] = False
    logger.info(f'log id:{unique_id},seq id:{seq_id}。指令解析链路耗时：{end2 - start2}s')
    logger.info(f'log id:{unique_id},seq id:{seq_id}。指令结果：{output}')
    
    return output

@app.route('/llm_intent', methods=['POST'])
def llm_intent():
    start = time.time()
    # 获取 JSON 数据
    data = request.get_json()
    
    # 获取参数
    asr_text = data.get('asr_text')
    dn = data.get('dn')
    ip_address = data.get('ip_address','110.96.0.0')
    history = data.get('history',[])
    city = data.get('city','')
    open_migu = data.get('open_migu',False)
    try:
        ip_address = q.lookup(ip_address)[0]
    except:
        ip_address = get_location_by_ip(ip_address)    
        
    # 串联上游业务的logID
    unique_id = request.headers.get('x-log-id')
    if not unique_id:
        # 生成一个随机的UUID
        unique_id = str(uuid.uuid4())

    seq_id = data.get('seq_id',1)
    logger.info('*'*100)
    logger.info(f'当前logid的标识为：{unique_id},seq id:{seq_id}')

    if not dn :
        logger.info(json.dumps({"code": 400,"msg": "error",'error_info': 'Missing parameters dn','logid_id':unique_id,'seq_id':seq_id}))
        return json.dumps({"code": 400,"msg": "error",'error_info': 'Missing parameters dn','logid_id':unique_id,'seq_id':seq_id}), 400

    logger.info(f'log id:{unique_id},seq id:{seq_id}。用户输入信息：{data}')
    if not asr_text:
        logger.info(f'log id:{unique_id},seq id:{seq_id}。因为asr识别文本为空触发无效语音指令！')
        return json.dumps({
            "code": 200,
            "msg": "success",
            "data": {
                    "type": "command",
                    "value": {
                        "method": command_name.get('无效语音'),
                        "param": ""
                    },
                    "binary_len": 0
                }
            }, ensure_ascii=False)
    main_start = time.time()
    result = main(dn, asr_text, ip_address, city, open_migu, history, unique_id, seq_id)
    main_end = time.time()
    logger.info(f'log id:{unique_id},seq id:{seq_id}。意图大模型主函数耗时：{main_end-main_start}s')
    end = time.time()
    logger.info(f'log id:{unique_id},seq id:{seq_id}。整个链路耗时：{end-start}s')
    result['logid'] = unique_id
    result['data']['city'] = city
    response = json.dumps(result, ensure_ascii=False)
    return response

@app.route('/healthCheck', methods=['GET'])
def health_check():
    """Health check endpoint."""
    log_id = str(int(time.time() * 1000))
    response = {
        "code": 200,
        "msg": "success",
        "data": None,
        "log_id": log_id
    }
    return jsonify(response)

if __name__ == '__main__':
    #场景预设问题提前表征
    pre_emb_question_scene(question_scene)
    app.run(host='0.0.0.0', port=6000, debug=False)


    
    






















































