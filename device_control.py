import re
import openai
from openai import OpenAI
import json
import random
import time
from http import HTTPStatus
# 建议dashscope SDK 的版本 >= 1.14.0
import pandas as pd
import numpy as np
from typing import Generator, List
from music_function_call import parse_music_intent
from config import api_key, reply_prompt, device_type, skill_name, command_name, dashscope_url
# 如果环境变量配置无效请启用以下代码
client = OpenAI(api_key=api_key, base_url=dashscope_url)

def music_control(input_text):
    #暂时音乐功能开发
    if re.findall('上一首|返回上一首|上一首歌|上一曲',input_text):
        return {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": 'Media.Player.Previous',
                                "param": {}
                            },
                            "binary_len": 0
                        }
                    }
    elif re.findall('下一首|切歌|下一首歌|换一首歌|下一曲|跳过这首歌',input_text):
        return {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": 'Media.Player.Next',
                                "param": {}
                            },
                            "binary_len": 0
                        }
                    }
    elif re.findall('别放音乐了|别放了|别唱了|退出音乐|停止播放|退出播放|关闭音乐|结束音乐',input_text):
        return {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": 'Media.Player.Stop',
                                "param": {}
                            },
                            "binary_len": 0
                        }
                    }
    elif re.findall('停止播放|暂停播放|音乐暂停|暂停音乐|音乐暂停一下',input_text):
        return {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": 'Media.Player.Pause',
                                "param": {}
                            },
                            "binary_len": 0
                        }
                    }
    elif re.findall('“恢复音乐|恢复播放|继续听歌|继续播放|继续音乐|音乐继续|继续放',input_text):
        return {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": 'Media.Player.Resume',
                                "param": {}
                            },
                            "binary_len": 0
                        }
                    }
    elif re.findall('列表循环|列表播放|顺序播放',input_text):
        return {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": 'Media.Loop.List',
                                "param": {}
                            },
                            "binary_len": 0
                        }
                    }
    elif re.findall('随机循环|随机播放|随机播放我的歌单|按顺序播放',input_text):
        return {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": 'Media.Loop.Random',
                                "param": {}
                            },
                            "binary_len": 0
                        }
                    }
    elif re.findall('单曲循环|单曲播放|重复这首歌',input_text):
        return {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": 'Media.Loop.Single',
                                "param": {}
                            },
                            "binary_len": 0
                        }
                    }
    else:
        return {}

def extract_trailing_number(element):
    #提取element中结尾的数字位置
    # 定义正则表达式模式，匹配以数字结尾的字符串
    pattern = r'PowerSwitch_(\d+)$'
    # 使用re.search查找匹配项
    match = re.search(pattern, element)
    
    # 如果找到匹配项，返回数字部分；否则返回空字符串
    if match:
        return str(match.group(1))
    else:
        return ''

def air_control(input_text,user_data,user_home,local,unique_id,seq_id,logger):
    """空调指令控制"""
    # function = information_extraction(text=input_text, user_data=user_data, local=local, mode='all')
    room_dict = user_data[['roomName', 'roomId']].set_index('roomName')['roomId'].to_dict()
    device_kv = {}
    for item in user_data.to_dict('records'):
        if device_kv.get(item['nickName']):
            device_kv[item['nickName']].append(item['deviceName']+'_'+str(item['productId'])+'_'+item['iotId']+'_'+item['element'].split('_')[-1])
        else:
            device_kv[item['nickName']] = [item['deviceName']+'_'+str(item['productId'])+'_'+item['iotId']+'_'+item['element'].split('_')[-1]]
    function = information_extraction(text=input_text, user_data=user_data, local=local, mode='room')
    # if not function.get('local'):
    #     function['local'] = list(room_dict.keys())
    # else:
    #     function = information_extraction(text=input_text, user_data=user_data, local=local, mode='room')
    logger.info(f'log id:{unique_id},seq id:{seq_id}。信息抽取结果：{function}')
    result = {}
    result['controlType'] = 99
    result['device_info'] = []
    if re.findall('空调',input_text) and function['device'] != []:
        if re.findall('开空调|打开|开',input_text):
            result['action'] = 'air_turn_on'
            result['reply'] = '已打开空调'
        elif re.findall('关空调|关闭|关',input_text):
            result['action'] = 'air_turn_off'
            result['reply'] = '已关闭空调'
        elif re.findall('温度|度|°',input_text):
            #温度值调节
            # 正则表达式模式，匹配整数
            pattern = r'\d+'
            # search 方法会找出字符串中第一个匹配的数字
            match = re.search(pattern, input_text)
            if match:
                temperature_value = match.group()  # 获取匹配的字符串
                temperature_value = int(temperature_value)    # 将提取的数字字符串转换为整数
                if temperature_value > 30:
                    temperature_value = 30
                elif temperature_value < 16:
                    temperature_value = 16
                result['action'] = 'temperature_value'
                result['value'] = temperature_value
                result['reply'] = '已调整温度'
            elif '最高' in input_text:
                result['action'] = 'temperature_value'
                result['value'] = 30
                result['reply'] = '已调整温度'
            elif '最低' in input_text:
                result['action'] = 'temperature_value'
                result['value'] = 16
                result['reply'] = '已调整温度'
            else:
                result['reply'] = '似乎在您的问题中没有找到想要操控的温度数值。'
        elif re.findall('模式|制冷|制热|送风|除湿',input_text):
            matches = re.findall('制冷|制热|送风|除湿',input_text)
            if matches:
                air_mode = matches[-1]
                mode_dict = {'制冷':1,'制热':8,'送风':4,'除湿':2}
                result['action'] = 'mode'
                result['value'] = mode_dict.get(air_mode)
                result['reply'] =  f'已调整至{air_mode}模式'
            else:
                result['reply'] = '不好意思，空调模式只有制冷、制热和送风以及除湿。'
        elif re.findall('风速|风',input_text):
            matches = re.findall('自动|高|中|低', input_text)
            if matches:
                value = matches[-1]
                ws_dict = {'高':1,'中':2,'低':4,'自动':0}
                ws_value = ws_dict.get(value,0)
                result['action'] = 'windspeed_value'
                result['value'] = ws_value
                result['reply'] = '已调整空调风速啦'
            else:
                result['reply'] = '不好意思，空调风速只有高档、中档和低档以及自动挡。'
        else:
            result['reply'] = '小主不好意思，我暂时只能调节空调具体温度值，风速，模式，剩下的需要我提上书包去学习了。'
        for device in function['device']:
            id_info = device_kv.get(device,[])
            for id_device in id_info:
                info_list = id_device.split('_')
                if result.get('action'):
                    if result.get('value') is not None:
                        result['device_info'].append({'custom_name':device,'action': result['action'],'value':result['value'],"percentage":False,'control_dn':info_list[0],'control_pid':info_list[1],'control_iotid':info_list[2],'x':extract_trailing_number(info_list[3])})
                    else:
                        result['device_info'].append({'custom_name':device,'action': result['action'],'control_dn':info_list[0],'control_pid':info_list[1],'control_iotid':info_list[2],'x':extract_trailing_number(info_list[3])})
        result.pop('action', None)
        result.pop('value', None)
    elif re.findall('地暖',input_text):
        floor_heating = []
        for nickName in user_data['nickName']:
            if re.findall('地暖',nickName):
                floor_heating.append(nickName)
        if floor_heating:
            if re.findall('开地暖|打开',input_text):
                result['action'] = 'antifreeze_switch'
                result['value'] = 1
                result['reply'] = '已打开地暖'   
            elif re.findall('关地暖|关闭',input_text):
                result['action'] = 'antifreeze_switch'
                result['value'] = 0
                result['reply'] = '已关闭地暖'
            else:
                result['reply'] = '小主不好意思，我暂时只能操作地暖开和关，剩下的需要我提上书包去学习了。'
            for device in floor_heating:
                id_info = device_kv.get(device,[])
                for id_device in id_info:
                    info_list = id_device.split('_')
                    if result.get('action'):
                        result['device_info'].append({'custom_name':device,'action': result['action'],'value':result['value'],"percentage":False,'control_dn':info_list[0],'control_pid':info_list[1],'control_iotid':info_list[2],'x':extract_trailing_number(info_list[3])})
        else:
            result['reply'] = '小主我没有找到地暖设备'
        result.pop('action', None)
        result.pop('value', None)
    elif re.findall('风管机',input_text) and function['device'] != []:
        if re.findall('开空调风管机|开风管机|打开|开',input_text):
            result['action'] = 'air_turn_on'
            result['reply'] = '已打开空调风管机'
        elif re.findall('关空调风管机|关风管机|关闭|关',input_text):
            result['action'] = 'air_turn_off'
            result['reply'] = '已关闭空调风管机'
        elif re.findall('温度|度|°',input_text):
            #温度值调节
            # 正则表达式模式，匹配整数
            pattern = r'\d+'
            # search 方法会找出字符串中第一个匹配的数字
            match = re.search(pattern, input_text)
            if match:
                temperature_value = match.group()  # 获取匹配的字符串
                temperature_value = int(temperature_value)    # 将提取的数字字符串转换为整数
                if temperature_value > 30:
                    temperature_value = 30
                elif temperature_value < 16:
                    temperature_value = 16
                result['action'] = 'temperature_value'
                result['value'] = temperature_value
                result['reply'] = '已调整温度'
            elif '最高' in input_text:
                result['action'] = 'temperature_value'
                result['value'] = 30
                result['reply'] = '已调整温度'
            elif '最低' in input_text:
                result['action'] = 'temperature_value'
                result['value'] = 16
                result['reply'] = '已调整温度'
            else:
                result['reply'] = '似乎在您的问题中没有找到想要操控的温度数值。'
        elif re.findall('模式|制冷|制热|送风|除湿',input_text):
            matches = re.findall('制冷|制热|送风|除湿',input_text)
            if matches:
                air_mode = matches[-1]
                mode_dict = {'制冷':1,'制热':8,'送风':4,'除湿':2}
                result['action'] = 'mode'
                result['value'] = mode_dict.get(air_mode)
                result['reply'] = f'已调整至{air_mode}模式'
            else:
                result['reply'] = '不好意思，空调风管机模式只有制冷、制热和送风以及除湿。'
        elif re.findall('风速|风',input_text):
            matches = re.findall('自动|高|中|低', input_text)
            if matches:
                value = matches[-1]
                ws_dict = {'高':1,'中':2,'低':4,'自动':0}
                ws_value = ws_dict.get(value,0)
                result['action'] = 'windspeed_value'
                result['value'] = ws_value
                result['reply'] = '已调整风速'
            else:
                result['reply'] = '不好意思，空调风管机风速只有高档、中档和低档以及自动挡。'
        else:
            result['reply'] = '小主不好意思，我暂时只能调节空调风管机具体温度值，风速，模式，剩下的需要我提上书包去学习了。'
        for device in function['device']:
            id_info = device_kv.get(device,[])
            for id_device in id_info:
                info_list = id_device.split('_')
                if result.get('action'):
                    if result.get('value') is not None:
                        result['device_info'].append({'custom_name':device,'action': result['action'],'value':result['value'],"percentage":False,'control_dn':info_list[0],'control_pid':info_list[1],'control_iotid':info_list[2],'x':extract_trailing_number(info_list[3])})
                    else:
                        result['device_info'].append({'custom_name':device,'action': result['action'],'control_dn':info_list[0],'control_pid':info_list[1],'control_iotid':info_list[2],'x':extract_trailing_number(info_list[3])})
        result.pop('action', None)
        result.pop('value', None)      
    else:
        result['device_info'] = []
        result['reply'] = '未找到小主要操控的相关设备'
    if type(function['local']) is list:
        result['roomIds'] = [room_dict.get(local) for local in function['local']]
    else:
        result['roomIds'] = [room_dict.get(function['local'])]
    return result

def lighting_control_command_synthesis(input_text,user_data,user_home,local,ip_address,city,open_migu,date,content,model,unique_id,seq_id,logger):
    """控制指令合成"""
    if content['l1']=='家电控制' and content['l2'] in {'灯','开关','插座','窗帘'}:
        function = information_extraction(text=input_text, user_data=user_data, local=local)
        if not function['local']:
            function['local'] = local
        logger.info(f'log id:{unique_id},seq id:{seq_id}。信息抽取结果：{function}')
        room_dict = user_data[['roomName', 'roomId']].set_index('roomName')['roomId'].to_dict()
        recall_data = recall_user_data(user_data,user_home,function)
        if function['device'] == ['所有灯'] and re.findall('打开',input_text):
            result = {}
            device_info = []
            result['home'] = user_home
            for item in recall_data.to_dict('records'):
                if re.findall('灯',item['nickName']):
                    device_info.append({'custom_name':item['nickName'],'action': 'turn_on','control_dn':item['deviceName'],'control_pid':item['productId'],'control_iotid': item['iotId'],'x':extract_trailing_number(item['element'])})
            result['device_info'] = device_info
            result['controlType'] = 1
            if not result['device_info']:
                result['reply'] = f'{function["local"]}区域未找到相关设备'
            else:
                result['reply'] = f"已打开{function['local']}区域所有灯"
        elif function['device'] == ['所有灯'] and re.findall('关闭',input_text):
            result = {}
            device_info = []
            result['home'] = user_home
            result['controlType'] = 2
            for item in recall_data.to_dict('records'):
                if re.findall('灯',item['nickName']):
                    device_info.append({'custom_name':item['nickName'],'action': 'turn_off','control_dn':item['deviceName'],'control_pid':item['productId'],'control_iotid': item['iotId'],'x':extract_trailing_number(item['element'])})
            result['device_info'] = device_info
            if not result['device_info']:
                result['reply'] = f'{function["local"]}区域未找到相关设备'
            else:
                result['reply'] = f"已关闭{function['local']}区域所有灯"
        elif type(function['device']) is list and len(function['device'])>0 and re.findall('打开',input_text) and content['l2']!='窗帘':
            result = {}
            device_info = []
            result['home'] = user_home
            for item in recall_data.to_dict('records'):
                if item['nickName'] in function['device']:
                    device_info.append({'custom_name':item['nickName'],'action': 'turn_on','control_dn':item['deviceName'],'control_pid':item['productId'],'control_iotid': item['iotId'],'x':extract_trailing_number(item['element'])})
            result['device_info'] = device_info
            result['controlType'] = 99
            if not result['device_info']:
                result['reply'] = f'{function["local"]}区域未找到相关设备'
            else:
                result['reply'] = f"已打开{function['local']}区域相关设备"
        elif type(function['device']) is list and len(function['device'])>0 and re.findall('关闭',input_text) and content['l2']!='窗帘':
            result = {}
            device_info = []
            result['home'] = user_home
            for item in recall_data.to_dict('records'):
                if item['nickName'] in function['device']:
                    device_info.append({'custom_name':item['nickName'],'action': 'turn_off','control_dn':item['deviceName'],'control_pid':item['productId'],'control_iotid': item['iotId'],'x':extract_trailing_number(item['element'])})
            result['device_info'] = device_info
            result['controlType'] = 99
            if not result['device_info']:
                result['reply'] = f'{function["local"]}区域未找到相关设备'
            else:
                result['reply'] = f"已关闭{function['local']}区域相关设备" 
        else:
            result = control_instruction(input_text,content,recall_data,function['local'],user_home,unique_id,seq_id,logger,model=model)
        result['roomIds'] = [room_dict[function['local']]]
        #进行control_dn和iot id联合去重
        unique_devices = {}
        for device in result["device_info"]:
            key = (device["control_dn"], device["control_iotid"], device["x"])
            if key not in unique_devices:
                unique_devices[key] = device
        # 将去重后的设备信息转换回列表
        result["device_info"] = list(unique_devices.values())
        output = {
                "code": 200,
                "msg": "success",
                "data": {
                    "type": "iot",
                    "query":input_text,
                    "ability_pool": {},
                    "iot_detail": result}
                }
    elif content['l1']=='家电控制' and content['l2'] in {'空调','地暖'}:
        result = air_control(input_text,user_data,user_home,local,unique_id,seq_id,logger)
        output = {
                "code": 200,
                "msg": "success",
                "data": {
                    "type": "iot",
                    "query":input_text,
                    "ability_pool": {},
                    "iot_detail": result}
                }
    elif content['l1']=='通用技能' and content['l2'] in skill_name:
        if content['l2'] == '音乐' and open_migu:
            music_info = parse_music_intent(input_text,unique_id,seq_id,logger)
            output = {
                "code": 200,
                "msg": "success",
                "data": {
                    "type": "skill",
                    "query":input_text,
                    "ability_pool": {"type":skill_name.get(content['l2']),"param":{},"migu":music_info},
                    "iot_detail": {}}
                }
        else:
            output = {
            "code": 200,
            "msg": "success",
            "data": {
                "type": "skill",
                "query":input_text,
                "ability_pool": {"type":skill_name.get(content['l2']),"param":{}},
                "iot_detail": {}}
            }

    elif content['l1']=='中控' and content['l2'] in command_name:
        if content['l2'] == '设置音量':
            # 正则表达式匹配1到100的数字
            pattern = r'(0|100|[1-9][0-9]?)'
            # 使用re.search提取第一个匹配的数值
            match = re.search(pattern, input_text)
            if match:
                output = {
                    "code": 200,
                    "msg": "success",
                    "data": {
                            "type": "command",
                            "value": {
                                "method": command_name.get(content['l2']),
                                "param": {'volume':int(match.group())}
                            },
                            "binary_len": 0
                        }
                    }
            else:
                output = {
                    "code": 200,
                    "msg": "success",
                    "data": {
                        "type": "chat",
                        "query":f'你根据下面信息如果有用到这些信息则结合回答，没有请忽略。用户当前位置信息：{city}和当前时间：{date}。用户问题：{input_text}',
                        "ability_pool": {},
                        "iot_detail": {}}
                }

        else:
            output = {
                "code": 200,
                "msg": "success",
                "data": {
                        "type": "command",
                        "value": {
                            "method": command_name.get(content['l2']),
                            "param": ""
                        },
                        "binary_len": 0
                    }
                }
    elif content['l1']=='通用技能' and content['l2'] in '搜索':
        output = {
                    "code": 200,
                    "msg": "success",
                    "data": {
                        "type": "search",
                        "query":f'你根据下面信息如果有用到这些信息则结合回答，没有请忽略。用户当前位置信息：{city}和当前时间：{date}。用户问题：{input_text}',
                        "ability_pool": {},
                        "iot_detail": {}}
                }
    elif content['l1']=='中控' and content['l2']=='无意义':
        output = {
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
            }
    else:
        output = {
                    "code": 200,
                    "msg": "success",
                    "data": {
                        "type": "chat",
                        "query":f'你根据下面信息如果有用到这些信息则结合回答，没有请忽略。用户当前位置信息：{city}和当前时间：{date}。用户问题：{input_text}',
                        "ability_pool": {},
                        "iot_detail": {}}
                }

    return output

def extraction_text(text, keywords):
    # 对每个关键词进行转义处理，避免特殊字符影响正则匹配
    escaped_keywords = [re.escape(keyword) for keyword in keywords]
    # 构建一个正则表达式，匹配关键词整体
    pattern = re.compile('|'.join(escaped_keywords))
    # 使用 findall() 函数提取关键词
    matched_keywords = pattern.findall(text)
    return matched_keywords

def information_extraction(text, user_data, local, mode='room'):
    local_keyworks = list(set(user_data['roomName']))
    local_keyworks.sort(key=len, reverse=True)
    local_list = extraction_text(text,local_keyworks)
    result = {}
    if mode=='room':
        if not local_list:
            result['local'] = local
        else:
            result['local'] = local_list[0]
        device_keyworks = list(set(user_data[user_data['roomName']==result['local']]['nickName']))
    elif mode=='all':
        if local_list:
            result['local'] = local_list
        device_keyworks = list(set(user_data['nickName']))
    if not re.findall('所有灯带',text):
        device_keyworks += ['所有灯']
    device_keyworks.sort(key=len, reverse=True)
    device_list = extraction_text(text,device_keyworks)
    if not device_list:
        device_type.sort(key=len)
        type_list = extraction_text(text,device_type)
        device_result = []
        for type_name in type_list:
            for device_name in device_keyworks:
                if re.findall(type_name,device_name):
                    device_result.append(device_name)
        if device_result:
            result['device'] = device_result
        else:
            result['device'] = []
    else:
        result['device'] = device_list
    return result

def recall_user_data(user_data,user_home,function):
    select_data = user_data[(user_data['roomName']==function.get('local')) & (user_data['nickName'].isin(function.get('device')))]
    if len(select_data)==0:
        select_data = user_data[user_data['roomName']==function.get('local')]
    return select_data

def unique_list(seq):
    return list(dict.fromkeys(seq))

def control_instruction(input_text,content,recall_data,local,user_home,unique_id,seq_id,logger,model):
    device_list = []
    recall_data = recall_data.drop_duplicates(subset=['nickName','deviceName'])
    device_kv = {}
    for item in recall_data.to_dict('records'):
        if device_kv.get(item['nickName']):
            device_kv[item['nickName']].append(item['deviceName']+'_'+str(item['productId'])+'_'+item['iotId']+'_'+extract_trailing_number(item['element']))
        else:
            device_kv[item['nickName']] = [item['deviceName']+'_'+str(item['productId'])+'_'+item['iotId']+'_'+extract_trailing_number(item['element'])]
        device_list.append(item['nickName'])
    logger.info(f'房间设备列表归类：{device_kv}')
    if content['l2']=='窗帘':
        system_prompt = """ 
                        # 角色
                        你是一位智能家居系统智能控制指令解析专家,严格遵守下面条例和格式要求，不得违背，请你仔细学习下面用户的例子，来更好的完成任务，一步步思考，请保证每次输出是一样的。

                        ## 需要严格遵守条例
                        - id输出的数字在当前用户设备信息里面选择，不要从例子信息里面选择，请牢记。
                        - 梦幻窗帘电机、智能窗帘电机、Mini开合帘电机、卷帘管状电机是四个不同窗帘设备，需要区分好，用户如果提到具体设备名,则仅操作用户提到的设备名。
                        - 请认真对应列表中数字，而且要看清楚用户操作的设备在设备信息中选择编号，不要输出错误数字，导致任务错误，请模型根据用户语义选择设备对应的id，不要输出错误，这对我非常重要。
                        - 如果在设备列表中没有找到相关设备，id就输出[]，请注意看清用户列表的设备名字以及用户问题中想要超控的设备名字，不要假设和瞎猜，不要操控错误，请严格遵循条件。
                        - 窗帘不支持组播，"domain"值必须为"0"。
                        - 根据下面例子一样，能够精准理解用户意图，精准控制到每一个设备，不会多输出和少输出，千万注意不能漏掉控制。

                        ## 参考用例（这下面只是例子，用来参考，控制指令输出并不是从下面选择）
                            - 房间：客厅
                            - 用户设备信息: 0:梦幻窗帘电机，1:智能窗帘，2:情景调光开关
                            用户问题：打开客厅窗帘到50% 
                            模型回答：{{"domain": 0,"id": ["0","1"],"action": "curtain_position","value": 50,"percentage": true}}

                            - 房间：客厅
                            - 用户设备信息: 0:梦幻窗帘电机，1:智能窗帘，2:情景调光开关
                            用户问题：调整客厅窗帘角度到90° 
                            模型回答：{{"domain": 0,"id": ["0","1"],"action": "flip_angle","value":90}}

                            - 房间：卧室
                            - 用户设备信息: 0:梦幻窗帘电机，1:智能窗帘，2:情景调光开关
                            用户问题：关闭卧室智能窗帘 
                            模型回答：{{"domain": 0,"id": ["0","1"],"action": "curtain_position","value":0,"percentage":true}}
                            用户问题：打开卧室智能窗帘 
                            模型回答：{{"domain": 0,"id": ["0","1"],"action": "curtain_position","value":100,"percentage":true}}

                            - 房间：客厅
                            - 用户设备信息: 0:梦幻窗帘电机，1:智能窗帘，2:情景调光开关，3:Mini开合帘电机
                            用户问题：暂停窗帘 
                            模型回答：{{"domain": 0,"id": ["0","1","2"],"action": "curtain_control","value":2}}

                            - 房间：客厅
                            - 用户设备信息: 0:梦幻窗帘电机，1:智能窗帘，2:情景调光开关，3:Mini开合帘电机 4:卷帘管状电机
                            用户问题：打开卷帘
                            模型回答：{{"domain": 0,"id": ["4"],"action": "curtain_position","value":100,"percentage":true}}

                        ## 请严格按照下面的格式输出信息,一定要保证输出是json格式,不需要输出json这个字符串，请不要多做解释，请一定要记住:
                        {{"domain":0,#此操作默认为0
                        "id":["0","1"],#id是操控设备的编号，例如:1,4,9等，只输出设备编号，不要输出设备名，严格只从用户设备信息中选取设备编号，请勿幻觉生成。
                        "action":"
                                // curtain_position（窗帘位置和开关设定，取值范围：[0-100]: 代表窗帘的位置，0表示完全关闭，100表示完全打开）
                                // flip_angle（窗帘翻转角度设定，[0-180]: 代表窗帘的翻转角度，0表示没有翻转，180表示完全翻转)
                                // curtain_control (窗帘控制属性，2代表为窗帘暂停)
                        ,
                        "value":"不要创造只从用户话语中提取，是int型",#如果用户意图没有具体值或百分比，则不用输出value和percentage字段
                        "percentage":"用户是否想调节百分比数值，输出true和false布尔值，不要输出字符串"}}

                        ## 当前用户的设备信息:
                        - 当前房间(如果输入是默认就是默认房间，这是一个缺省值请忽略房间信息)：
                        {local}
                        - 当前用户输入设备信息:
                        {device_list}
                        """
    else: 
        system_prompt = """ 
                        # 角色
                        你是一位智能家居系统智能控制指令解析专家,严格遵守下面条例和格式要求，不得违背，请你仔细学习下面用户的例子，来更好的完成任务，一步步思考，请保证每次输出是一样的。

                        ## 需要严格遵守条例
                        - id输出的数字在当前用户设备信息里面选择，不要从例子信息里面选择，请牢记。
                        - 请认真对应列表中数字，不要输出错误数字，导致任务错误。
                        - 请模型根据用户语义选择设备对应的id，不要输出错误，这对我非常重要。
                        - 如果在设备列表中没有找到相关设备，id就输出[]，请注意看清用户列表的设备名字以及用户问题中想要超控的设备名字，不要假设和瞎猜，不要操控错误，请严格遵循条件。
                        - 其中筒灯,射灯,灯带,格栅灯,吊线灯,线条灯,智能射灯，是不同的灯，灯组是单设备，不是区域控制。
                        - 根据下面例子一样，能够精准理解用户意图，精准控制到每一个设备，不会多输出和少输出，千万注意不能漏掉控制。
                        - 其中只有是灯的设备就能调色温和亮度，比如灯带、筒灯、射灯等，无需考虑是否能操控，并且开关、传感器、窗帘等设备是不支持调色温和亮度。
                        - 其中黄光代表色温2700k、白光代表色温5700k，灯色温调节范围不受限制，有些灯色温能调节到12000k以上。
                        - 如果操作色温百分比的话，例如调到色温百分之八十，color_temperature_value为80，percentage为true，色温冷一点是color_temperature_up，色温暖一点是color_temperature_down。
                        - 如果user说随便颜色或者只说了颜色，但是没有指名是什么颜色的话，则rgb_value需要从'216,163,106'、'255,139,0'、'2,167,240'、'18,135,62'中选择一种。

                        ## 参考用例（这下面只是例子，用来参考，控制指令输出并不是从下面选择）
                            - 房间：客厅
                            - 用户设备信息：0:摄像头，1:嵌入式射灯B，2:布帘，3:客厅纱帘，4:轨道线条灯
                            用户问题：打开客厅灯带
                            模型回答：{{"domain":0,"id":[],"action":"turn_on"}}
                            用户问题：关闭客厅筒灯
                            模型回答：{{"domain":0,"id":[],"action":"turn_off"}}
                            用户问题：打开客厅射灯
                            模型回答：{{"domain":0,"id":["1"],"action":"turn_on"}}
                            用户问题：将灯带亮度调到30%
                            模型回答：{{"domain": 0, "id": [], "action": "light_value", "value": 30, "percentage": true}}   

                            - 房间：主卧
                            - 用户设备信息：0:语音四位开关左下键，1:语音四位开关左上键，2:二位零火开关右键，3:轨道线条灯，4:语音四位开关右下键，5:空调2，6:二位零火开关左键，7:轨道智能灯，8:语音四位开关右上键，9:射灯，10:语音情景开关，11:格栅灯，12:吊线灯
                            用户问题：主卧灯带调到紫色
                            模型回答：{{"domain":0,"id":[],"action":"rgb_value","rgb_value":"128,0,128"}}

                            - 房间：客厅
                            - 用户设备信息：0:轨道单头射灯，1:低压灯带222，2:智慧屏网关上键，3:智慧屏网关下键
                            用户问题：打开客厅灯
                            模型回答：{{"domain":1,"id":[],"action":"turn_on"}}

                            - 房间：客厅
                            - 用户设备信息：0:智慧屏网关中键，1:轨道射灯1，2:智慧屏网关上键，3:智慧屏网关下键，4:电视墙射灯1，5:电视墙射灯2，6:157-轨道射灯2
                            用户问题：客厅灯色温调到100%
                            模型回答：{{"domain":1,"id":[],"action":"color_temperature_value","value":100,"percentage":true}}

                            - 房间：主卧
                            - 用户设备信息:0:低压灯带，1:换尿布
                            用户问题：主卧白光
                            模型回答：{{"domain": 1, "id": [], "action": "color_temperature_value", "value": 5700, "percentage": false}}
                            用户问题：主卧灯亮度调到50%
                            模型回答：{{'domain': 1, 'id': [], 'action': 'light_value', 'value': 50, 'percentage': true}}

                            - 房间：车库
                            - 用户设备信息:0:低压灯带，1:一位零火开关
                            用户问题：将车库调亮一点
                            模型回答：{{"domain":1,"id":[],"action":"light_up"}}
                            用户问题：车库白光
                            模型回答：{{"domain":1,"id":[],"action":"color_temperature_value","value":5700,"percentage":false}}

                            - 房间：客厅
                            - 用户设备信息:0:273轨道单头射灯，1:189-低压灯带222，2:智慧屏网关上键，3:智慧屏网关下键
                            用户问题：客厅射灯亮度调低
                            模型回答：{{"domain":0,"id":["0"],"action":"light_down"}}

                            - 房间：客厅
                            - 用户设备信息:0:轨道单头射灯，1:智慧屏网关上键，2:智慧屏网关下键，3:轨道格栅灯，4:低压灯带
                            用户问题：将客厅灯带色温调到5000k
                            模型回答：{{"domain":0,"id":["4"],"action":"color_temperature_value","value":5000,"percentage":false}}

                            - 房间：客厅
                            - 用户设备信息:0:电视墙天花灯带，1:客厅天花灯带
                            用户问题：将灯带亮度调到15%
                            模型回答：{{"domain": 0, "id": ["0","1"], "action": "light_value", "value": 15, "percentage":true}}   

                            - 房间：客厅
                            - 用户设备信息:0:小白，1:灯带，2:语音四位开关左上键，3:吸顶灯，4:无线四位情景开关，5:摄像头，6:11时39分新建灯组，7:地板黑，8:过道射灯组，9:无线情景调光开关，10:纱帘，11:智能吊灯，12:景航1#，13:轨道智能灯，14:布帘，15:轨道线条灯，16:空调，17:嵌入式射灯，18:二位情景开关
                            用户问题：喊客厅灯调到最暗
                            模型回答：{{"domain": 1, "id": [], "action": "light_value", "value": 1, "percentage": true}}
                            用户问题：喊客厅灯调到最亮
                            模型回答：{{"domain": 1, "id": [], "action": "light_value", "value": 100, "percentage": true}}
                            用户问题：喊客厅灯调到最暖
                            模型回答：{{"domain": 1, "id": [], "action": "color_temperature_value", "value": 1, "percentage": true}}
                            用户问题：喊客厅灯调到最冷
                            模型回答：{{"domain": 1, "id": [], "action": "color_temperature_value", "value": 100, "percentage": true}}             

                        ## 请严格按照下面的格式输出信息,一定要保证输出是json格式,不需要输出json这个字符串，请不要多做解释，请一定要记住:
                        {{"domain":1,#0-单设备操作，1-区域全局操作，如果是对当前房间区域灯或者开关全局操作，操作时填1且id输出为空，如果只是对于房间内某一类型设备操作则填0（例如操作射灯、筒灯这种单一类型设备），且输出具体id设备编号列表
                        "id":["0","1"],#id是操控设备的编号，例如:1,4,9等，只输出设备编号，不要输出设备名，严格只从用户设备信息中选取设备编号，请勿幻觉生成。
                        "action":"// 开关 turn_on（打开）, turn_off（关闭）, 
                                // 调亮暗 light_up（亮度上升）, light_down（亮度下降）, light_value（亮度值）
                                // color_temperature_up（色温上升）, color_temperature_down（色温下降）, color_temperature_value（色温值），灯色温，请注意色温高为冷色，色温低为暖色。
                                // rgb_value（RGB颜色字段）
                        ,
                        “rgb_value”://RGB的数值，例如红色则填入'255,0,0'字符串
                        "value":"色温或者亮度具体值，不要创造只从用户话语中提取，是int型",#如果用户意图没有具体值或百分比，则不用输出value和percentage字段
                        "percentage":"用户是否想调节百分比数值，输出true和false布尔值，不要输出字符串"}}

                        ## 当前用户的设备信息:
                        - 当前房间(如果输入是默认就是默认房间，这是一个缺省值请忽略房间信息)：
                        {local}
                        - 当前用户输入设备信息:
                        {device_list}
                        """
    device_list = list(set(device_list))
    device_id = {}
    new_device_list = []
    for i in range(len(device_list)):
        device_id[str(i)] = device_list[i]
        new_device_list.append(f'{i}:{device_list[i]}')
    logger.info(f"log id:{unique_id},seq id:{seq_id}。model_input_device_list：{'，'.join(new_device_list)}")
    system_prompt = system_prompt.format(local=local,device_list='，'.join(new_device_list))
    messages = [{'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': input_text}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.01
    )
    if response:
        try:
            content = json.loads(response.choices[0].message.content)
            logger.info(f'log id:{unique_id},seq id:{seq_id}。iot大模型输出：{content}')
        except:
            logger.info(f'log id:{unique_id},seq id:{seq_id}。model response json error')␊
            logger.info(f'log id:{unique_id},seq id:{seq_id}。iot大模型输出：{response.choices[0].message.content}')
            content = {'device_info':[]}
        content['device_info'] = []
        for device in content.get('id',[]):
            if not device_id.get(device):
                continue
            if content.get("value") is not None:
                content['device_info'].append({"custom_name":device_id.get(device),"action":content["action"],"value":content["value"],"percentage":content.get("percentage",False)})
            elif content.get("rgb_value"):
                content['device_info'].append({"custom_name":device_id.get(device),"action":content["action"],"rgb_value":content["rgb_value"]})
            else:
                content['device_info'].append({"custom_name":device_id.get(device),"action":content["action"]})
        logger.info(f'log id:{unique_id},seq id:{seq_id}。content的输出：{content}')
        content['home'] = user_home
        if content.get('domain') == 1:
            if content['action'] == 'turn_on':
                content['controlType'] = 1
                content['reply'] = f"{local}区域设备{reply_prompt.get(content['action'])}"
            elif content['action'] == 'turn_off':
                content['controlType'] = 2
                content['reply'] = f"{local}区域设备{reply_prompt.get(content['action'])}"
            elif content['action'] in {'color_temperature_up','color_temperature_down','light_up','light_down'}:
                content['controlType'] = 3
                content['reply'] = f"{local}区域设备{reply_prompt.get(content['action'])}"
                if content['action'] == 'light_up':
                    content['identifier'] = 'BrightValue'
                    content['step'] = 'up'
                elif content['action'] == 'light_down':
                    content['identifier'] = 'BrightValue'
                    content['step'] = 'down'
                elif content['action'] == 'color_temperature_up':
                    content['identifier'] = 'ColorTemperature'
                    content['step'] = 'up'
                elif content['action'] == 'color_temperature_down':
                    content['identifier'] = 'ColorTemperature'
                    content['step'] = 'down'
            else:
                content['controlType'] = 3
                if content['action'] == 'color_temperature_value' and not content.get('percentage',False):
                    content['identifier'] = 'ColorTemperature'
                    content['reply'] =  f"{local}区域设备{reply_prompt.get(content['action']) + str(content['value']) + 'k'}"
                elif content['action'] == 'color_temperature_value' and content.get('percentage',False):
                    content['identifier'] = 'ColorTemperature'
                    content['reply'] =  f"{local}区域设备{reply_prompt.get(content['action']) + str(content['value']) + '%'}"
                elif content['action'] == 'light_value' and not content.get('percentage',False):
                    content['identifier'] = 'BrightValue'
                    content['reply'] =  f"{local}区域设备{reply_prompt.get(content['action']) + str(content['value'])}"
                elif content['action'] == 'light_value' and content.get('percentage',False):
                    content['identifier'] = 'BrightValue'
                    content['reply'] =  f"{local}区域设备{reply_prompt.get(content['action']) + str(content['value']) + '%'}"
                elif content['action'] == 'rgb_value':
                    content['identifier'] = 'ColorHSV'
                    content['reply'] =  f"已为您执行{local}区域设备颜色操作"
            #设备列表指令转化
            if content.get('value') is not None:
                content['device_info'] = [{'custom_name': k, 'action': content['action'], 'value': content['value'], 'percentage': content.get('percentage', False), 'control_dn': data.split('_')[0], 'control_pid': int(data.split('_')[1]), 'control_iotid': data.split('_')[2], 'x': data.split('_')[3]} for k in device_kv.keys() for data in device_kv[k]]
            elif content.get('rgb_value'):
                content['device_info'] = [{'custom_name': k, 'action': content['action'], 'rgb_value': content.get('rgb_value', ''), 'control_dn': data.split('_')[0], 'control_pid': int(data.split('_')[1]), 'control_iotid': data.split('_')[2], 'x': data.split('_')[3]} for k in device_kv.keys() for data in device_kv[k]]
            else:
                content['device_info'] = [{'custom_name': k, 'action': content['action'], 'control_dn': data.split('_')[0], 'control_pid': int(data.split('_')[1]), 'control_iotid': data.split('_')[2], 'x': data.split('_')[3]} for k in device_kv.keys() for data in device_kv[k]]
        else:
            device_info = []
            reply = [f'{local}区域']
            for item in content['device_info']:
                if item['action'] in {'turn_on','turn_off','light_up','light_down','light_value','color_temperature_up','color_temperature_down','color_temperature_value','rgb_value','curtain_position','flip_angle','curtain_control','temperature_value','mode','windspeed_value','antifreeze_switch'} and item['custom_name']:
                    control_dn_list = device_kv.get(item['custom_name'])
                    if not control_dn_list:
                        break
                    if item['action'] not in {'color_temperature_value','light_value','rgb_value','curtain_position','flip_angle','curtain_control','temperature_value','mode','windspeed_value','antifreeze_switch'}:
                        reply.append(item['custom_name'] + reply_prompt.get(item['action']))
                    else:
                        if item['action'] == 'color_temperature_value' and not item['percentage']:
                            reply.append(item['custom_name'] + reply_prompt.get(item['action']) + str(item['value']) + 'k')
                        elif item['action'] == 'color_temperature_value' and item['percentage']:
                            reply.append(item['custom_name'] + reply_prompt.get(item['action']) + str(item['value']) + '%')
                        elif item['action'] == 'light_value' and not item['percentage']:
                            reply.append(item['custom_name'] + reply_prompt.get(item['action']) + str(item['value']))
                        elif item['action'] == 'light_value' and item['percentage']:
                            reply.append(item['custom_name'] + reply_prompt.get(item['action']) + str(item['value']) + '%')
                        elif item['action'] == 'rgb_value':
                            reply.append('已执行'+item['custom_name']+'颜色调节')
                        elif item['action'] == 'curtain_position':
                            reply.append(f"已执行窗帘操作")  
                        elif item['action'] == 'flip_angle':
                            reply.append(f"已执行窗帘角度调整")
                        elif item['action'] == 'curtain_control':
                            reply.append(f"已暂停窗帘")

                    for control_id in control_dn_list:
                        if item.get('value') is not None:
                            device_info.append({'custom_name':item['custom_name'],'action':item['action'],'value':item['value'],'percentage':item.get('percentage',False),'control_dn':control_id.split('_')[0],'control_pid':int(control_id.split('_')[1]),'control_iotid':control_id.split('_')[2],'x':control_id.split('_')[3]})
                        elif item.get('rgb_value'):
                            device_info.append({'custom_name':item['custom_name'],'action':item['action'],'rgb_value':item['rgb_value'],'control_dn':control_id.split('_')[0],'control_pid':int(control_id.split('_')[1]),'control_iotid':control_id.split('_')[2],'x':control_id.split('_')[3]})
                        else:
                            device_info.append({'custom_name':item['custom_name'],'action':item['action'],'control_dn':control_id.split('_')[0],'control_pid':int(control_id.split('_')[1]),'control_iotid':control_id.split('_')[2],'x':control_id.split('_')[3]})
            reply = unique_list(reply)
            if len(reply)>3:
                reply = f'已为您执行{local}区域相关设备操作'
            else:
                reply = '，'.join(reply)
            content['controlType'] = 99
            content['reply'] = reply
            content['device_info'] = device_info
            if not content.get('device_info'):
                content['reply'] = f'{local}区域没有找到相关设备'
                content['device_info'] = []
        #清除不必要的key值 
        content.pop('id', None)
        content.pop('action', None)
        content.pop('domain', None)
        return content
    else:
        logger.error(f'log id:{unique_id},seq id:{seq_id}。Request id: %s, Status code: %s, error code: %s, error message: %s' % (
            response.request_id, response.status_code,
            response.code, response.message
        ))
