import re
import random
import time
from http import HTTPStatus
import pandas as pd
import requests
import json
from openai import OpenAI
from config import api_key, dashscope_url
# 如果环境变量配置无效请启用以下代码
client = OpenAI(api_key=api_key, base_url=dashscope_url)

#，冰箱，加湿器，取暖器，地暖，微波炉，扫地机器人，按摩椅，摄像头，新风，晾衣架，油烟机，洗碗机，洗衣机，浴霸，灶具，烤箱，热水器，电水壶，电热毯，电磁炉，电视，电饭煲，空气净化器，空调，窗帘，足浴盆，除湿器，面板，风扇，香薰机，马桶，其他
def intent_recognition(input_text, ip_address, date, history, r, unique_id, seq_id, logger, model):
    ttl = 7 * 24 * 3600
    intent_cache = False

        
    system_prompt = """作为公牛集团智能家居意图识别的专家，你的目标是从用户输入中准确判断并输出用户的意图。请仔细阅读用户的问题，并根据以下设定的l1级和l2级意图分类进行匹配，不要创造意图输入，严格按照要求执行。
                    下面是l1级对应的l2级子意图分类，严格按照对应的层级关系输出：

                    **l1：家电控制**
                    - l2：灯，开关，插座，窗帘，空调，地暖。

                    *l1：中控**
                    - l2：结束对话(只有明确要求结束意图时调用)，无意义（输入语义不完整，不理解什么意思时调用），音量上调，音量下调，设置音量(设置范围是0-100之间)，静音

                    **l1：通用技能**
                    - l2：搜索(实时信息查询或者新闻)，音乐，儿歌，交通限行，亲戚关系计算，单位换算，天气，日历，节假日查询，翻译，计算器，笑话，故障。

                    **l1：闲聊**
                    - l2：闲聊（仅当其他分类都不适用时选择该意图）

                    ##改写要求##
                    1、只做上下文改写、缩写扩展，还有错别字修正改写，但是不要多补充意思，如果完整语义就不改写，千万不要做解释，请不要直接回答问题，其中设备命名中的数字都是有意义的不要做修改。谨记、谨记、谨记。
                    ##意图识别要求##
                    1、用户意图中想要对光或者颜色操作，需要分类到家电控制和灯。
                    
                    ** 示例 **
                    当前样例说明：亮度最高是100%，最低是1%，其中色温最暖是1%，最冷是100%,如果是色温调到1000k，返回就是色温调节到1000k，暖光就是色温1%，冷光就是100%

                    输入：窗帘开到一半
                    输出：家电控制|窗帘|窗帘调整到50%

                    输入：窗帘关闭四分之一
                    输出：家电控制|窗帘|窗帘调整到75%

                    输入：开合帘停止
                    输出：家电控制|窗帘|停止开合帘

                    输入：开合帘开80%
                    输出：家电控制|窗帘|开合帘开80%

                    输入：声音调到最大
                    输出：中控|设置音量|声音调到100%

                    输入：7788999勾的单点01点  //如果输入语义不清楚，倾向选择无意义
                    输出：中控|无意义|无意义
                    
                    输入：将灯带亮度调到最低
                    输出：家电控制|灯|将灯带亮度调到1%

                    输入：智能吸顶灯暖一点
                    输出：家电控制|灯|将智能吸顶灯色温调低

                    输入：吸顶灯上出光亮一点
                    输出：家电控制|灯|吸顶灯上出光亮一点

                    输入：上文：今天深圳天气，当前问题：北京呢。
                    输出：通用技能|天气|今天北京天气

                    输入：上文：打开灯带，当前问题：不用开了。
                    输出：家电控制|灯|关闭灯带

                    输入：上文:user:将客厅灯带亮度调到100%, assistant:低压灯带222亮度已调节到100%, user: 再低一点,assistant: 低压灯带222亮度已调低。user(当前问题):'再低一点
                    输出： 家电控制|灯|将客厅灯带亮度调低

                    输入：上文:user:主卧调到深粉色, assistant:已为您执行主卧区域设备颜色操作, user: 打开阳台窗帘,assistant: 阳台区域，已执行窗帘操作。user(当前问题):'关闭阳台窗帘
                    输出： 家电控制|灯|关闭阳台窗帘

                    输入：打开风管机
                    输出：家电控制|空调|打开风管机

                    输入：把客厅的灯光亮度调低一点
                    输出：家电控制|灯|把客厅的灯光亮度调低一点

                    输入：滚或者退下以及没叫你
                    输出：中控|结束对话|遵命

                    输入：打开低压灯带左1
                    输出：家电控制|灯|打开低压灯带左1

                    输入：滚或者退下以及没叫你
                    输出：中控|结束对话|遵命

                    输入：房间太黑了
                    输出：家电控制|灯|打开所有灯

                    输入：开灯
                    输出：家电控制|灯|打开所有灯

                    输入：我走了或者我出门了。
                    输出：家电控制|灯|关闭所有灯

                    输入：灯光太黄了
                    输出：家电控制|灯|将灯色温调高
                    
                    输入：上文：(user:开灯,assistant:打开默认房间所有灯)，当前问题：退下。
                    输出：中控|结束对话|退下
                    
                    输入：我要上报故障、小木小木你是不是坏了、小沐你怎么没反应、小木小木你是不是傻了、这个是智障呀、这个东西傻逼等用户输入话术，但不要太发散了。
                    输出：通用技能|故障|故障上报
                    
                    输入：你能做什么
                    输出：闲聊|闲聊|你能做什么？

                    输入：我妻子的父亲是我什么人
                    输出：通用技能|亲戚关系计算|我妻子的父亲是我什么人

                    **要求**
                    严格按照(l1意图|l2意图|改写文本）格式输出，不需要解释，不要多生成。
                    """
    system_prompt = system_prompt.format(ip_address=ip_address, date=date)
    current_history = history[-2:] + [{'role': 'user', 'content': input_text}]

    messages = [{'role': 'system', 'content': system_prompt}] + current_history
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            top_p=1,
            timeout=1.2
        )
    except Exception as e:
        logger.error(f'log id:{unique_id},seq id:{seq_id}。OpenAI 调用错误，错误信息：{str(e)}')
        content = {
            "l1": "闲聊",
            "l2": "闲聊",
            "text": input_text
        }
        return content, intent_cache
    except Exception as e:
        logger.error(f'log id:{unique_id},seq id:{seq_id}。OpenAI API 错误，错误信息：{str(e)}')
        content = {
            "l1": "闲聊",
            "l2": "闲聊",
            "text": input_text
        }
        return content, intent_cache

    if response:
        try:
            model_result = response.choices[0].message.content.split('|')
            l1 = model_result[0]
            l2 = model_result[1]
            text = model_result[2]
            content = {
                "l1": l1,
                "l2": l2,
                "text": text
            }

    else:
        logger.error(f'log id:{unique_id},seq id:{seq_id}。OpenAI 返回空响应')
        content = {
            "l1": "闲聊",
            "l2": "闲聊",
            "text": input_text
        }
        return content,intent_cache