import pandas as pd
import json
import requests
import sys
import re
import numpy as np

# 动作列表
ACTION = ["打开", "关闭"]

# 灯光控制指令      
base_light_actions = ["亮度调低", "亮度调高", "色温调低", "色温调高"]
color_temp_actions = [f"色温调到{i}k" for i in range(2700, 5701, 100)]
brightness_actions = [f"亮度调到{i}%" for i in range(10, 101, 10)]
LIGHT_ACTION = color_temp_actions + brightness_actions + base_light_actions

# 设备类型列表                  
DEVICE_TYPES = ['筒灯', '射灯', '灯带', '格栅灯', '吊线灯', '线条灯', '轨道.*?灯', '智能.*?灯', '开关']

API_KEY = '5b2f20903b9-04ce29bd5d-5b9e6ae78e8f'

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)


# def user_info_no_cache(dn):
#     """获取用户信息（仅带 api-key 鉴权）"""
#     url = f"https://api-prod.gn-gpt.com/gateway/api/v1/device/list?dn={dn}"
#     headers = {
#         'Content-Type': 'application/json',
#         'api-key': API_KEY
#     }
#     try:
#         resp = requests.get(url, headers=headers)
#         resp.raise_for_status()
#         data_json = resp.json()

#         # 确保 data 是列表      
#         if 'data' not in data_json or not isinstance(data_json['data'], list):
#             print("错误: API 返回格式不正确，缺少 data 列表")
#             return None, None, None
#         items = data_json['data']
#         if len(items) == 0:
#             return pd.DataFrame(), "未知家庭", "未知房间"

#         user_df = pd.DataFrame(items)
    
#         # 解析房间和家庭
#         if 'deviceName' in user_df.columns:
#             sel = user_df[user_df['deviceName'] == dn]
#             if not sel.empty:
#                 local = sel['roomName'].iloc[0] if 'roomName' in sel.columns else "未知房间"
#                 user_home = sel['familyName'].iloc[0] if 'familyName' in sel.columns else "未知家庭"
#             else:
#                 local, user_home = "未知房间", "未知家庭"
#         else:
#             local, user_home = "未知房间", "未知家庭"

#         return user_df, user_home, local

#     except requests.exceptions.RequestException as e:
#         print(f"获取用户信息时发生请求错误: {e}")
#         return None, None, None
#     except ValueError as e:
#         print(f"解析 JSON 时发生错误: {e}")
#         return None, None, None
token_url = "https://dev-auth.iotbull.com/auth/oauth2/token"
device_list_url = "https://test-skill.iotbull.com/skill/ai/voice/device/list"



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
    # logger.info(f'request token_url: {token_url}')
    response = requests.post(token_url, headers=headers, data=data)

    # 打印响应内容
    access_token = response.json()['access_token']
    return access_token


def user_info_no_cache(dn):
    # 1) 获取访问令牌
    try:
        access_token = get_access_token()  
    except Exception as e:
        print(f"获取 access_token 失败: {e}")
        return None, None, None

    # 2) 构造带 Bearer Token 的请求
    url = f"{device_list_url}?deviceName={dn}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        data_json = resp.json()

        if "data" not in data_json or not isinstance(data_json["data"], list):
            print("错误: API 返回格式不正确，缺少 data 列表")
            return None, None, None

        items = data_json["data"]
        if len(items) == 0:
            return pd.DataFrame(), "未知家庭", "未知房间"

        user_df = pd.DataFrame(items)

        if "deviceName" in user_df.columns:
            sel = user_df[user_df["deviceName"] == dn]
            if not sel.empty:
                local = sel["roomName"].iloc[0] if "roomName" in sel.columns else "未知房间"
                user_home = sel["familyName"].iloc[0] if "familyName" in sel.columns else "未知家庭"
            else:
                local, user_home = "未知房间", "未知家庭"
        else:
            local, user_home = "未知房间", "未知家庭"

        return user_df, user_home, local

    except requests.exceptions.RequestException as e:
        print(f"获取用户信息时发生请求错误: {e}")
        return None, None, None
    except ValueError as e:
        print(f"解析 JSON 时发生错误: {e}")
        return None, None, None


def extraction_text(input_text, keywords):
    escaped = [re.escape(k) for k in keywords]
    pat = re.compile('|'.join(escaped))
    return pat.findall(input_text)


def information_extraction(input_text, user_data, local, mode='room'):
    rooms = sorted(set(user_data.get('roomName', [])), key=len, reverse=True)
    found_rooms = extraction_text(input_text, rooms)
    result = {}
    if mode == 'room':
        result['local'] = found_rooms[0] if found_rooms else local
        device_keys = sorted(set(user_data[user_data['roomName'] == result['local']]['nickName']), key=len, reverse=True)
    else:
        result['local'] = found_rooms
        device_keys = sorted(set(user_data['nickName']), key=len, reverse=True)

    if '所有灯带' not in input_text:
        device_keys += ['所有灯']
    devices = extraction_text(input_text, device_keys)

    if not devices:
        types = ['灯', '窗帘', '空调', '电视', '风扇', '插座']
        found = extraction_text(input_text, types)
        devs = []
        for t in found:
            for dk in device_keys:
                if t in dk:
                    devs.append(dk)
        result['device'] = devs or []
    else:
        result['device'] = devices

    return result


def generate_from_devices(dev_df, commands, cmd_map):
    for _, row in dev_df.iterrows():
        nick = row['nickName']
        dn = row['deviceName']
        pid = row['productId']
        iot = row['iotId']
        elem = row.get('element', '')
        x = elem.split('_')[-1] if elem and '_' in elem else ''

        # 开关
        for act in ACTION:
            key = f"{act}{nick}"
            en = "turn_on" if act == "打开" else "turn_off"
            commands.append(key)
            cmd_map[key] = {'custom_name': nick, 'control_dn': dn,
                             'control_pid': pid, 'control_iotid': iot,
                             'x': x, 'action': en}

        # 灯光操作
        for la in LIGHT_ACTION:
            key = f"{nick}{la}"
            base = {'custom_name': nick, 'control_dn': dn,
                    'control_pid': pid, 'control_iotid': iot, 'x': x}
            data = base.copy()

            m_b = re.match(r'亮度调到(\d+)%', la)
            if m_b:
                data.update({'action': 'light_value', 'value': int(m_b.group(1)), 'percentage': True})
            elif la == "亮度调高":
                data['action'] = 'light_up'
            elif la == "亮度调低":
                data['action'] = 'light_down'
            elif la == "色温调高":
                data['action'] = 'color_temperature_up'
            elif la == "色温调低":
                data['action'] = 'color_temperature_down'
            else:
                m_t = re.match(r'色温调到(\d+)k', la, re.IGNORECASE)
                if m_t:
                    data.update({'action': 'color_temperature_value', 'value': int(m_t.group(1)), 'percentage': False})

            commands.append(key)
            cmd_map[key] = data


def generate_commands(info, user_data):
    cmds, cmap = [], {}
    loc = info.get('local')
    if not loc:
        return cmds, cmap

    filt = user_data[user_data['roomName'] == loc] if not isinstance(loc, list) else \
           user_data[user_data['roomName'].isin(loc)]
    if filt.empty:
        return cmds, cmap

    devs = info.get('device', [])
    if devs:
        matched = pd.DataFrame()
        for k in devs:
            matched = pd.concat([matched, filt[filt['nickName'].str.contains(k, case=False, na=False)]])
        matched = matched.drop_duplicates()
        generate_from_devices(matched if not matched.empty else filt, cmds, cmap)
    else:
        generate_from_devices(filt, cmds, cmap)

    return cmds, cmap


def get_control_type(action, is_group):
    if is_group:
        # 组控逻辑：打开是1，关闭是2
        return 1 if action == 'turn_on' else 2
    else:
        # 单控逻辑：所有操作都是99  
        return 99


def format_command_to_structure(cmd_text: str, info: dict, user_data: pd.DataFrame, *, is_group: bool = False):
    """将单条命令映射为目标结构体"""
    dn = info["control_dn"]
    row = user_data[user_data["deviceName"] == dn]
    home = row["familyName"].iloc[0] if not row.empty else "未知家庭"
    local = row["roomName"].iloc[0] if not row.empty else "未知房间"
    room_id = row["roomId"].iloc[0] if not row.empty else -1

    ctrl = get_control_type(info.get("action", ""), is_group)

    if ctrl == 99:
        reply_text = f"已操作{local}区域相关设备"
    elif ctrl == 1:
        reply_text = f"已打开{local}区域相关设备"
    else:  # ctrl == 2
        reply_text = f"已关闭{local}区域相关设备"

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "type": "iot",
            "query": cmd_text,
            "ability_pool": {},
            "iot_detail": {
                "home": home,
                "device_info": [info],
                "controlType": ctrl,
                "reply": reply_text,
                "roomIds": [room_id],
            },
        },
    }


def is_all_lights_command(input_text):
    """
    检查是否为"打开/关闭所有灯"命令
    """
    input_text = input_text.strip()
    patterns = [
        r'^(打开|关闭)所有灯$',
        r'^(打开|关闭)全部灯$',
        r'^(打开|关闭)所有的灯$',
        r'^(打开|关闭)全部的灯$'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, input_text)
        if match:
            return match.group(1)  # 返回动作（打开/关闭）
    
    return None


def process_all_lights_command(input_text, user_data):
    """
    处理"打开/关闭所有灯"命令
    对整个data列表中所有设备进行操作，但只将前10个设备放到iot_detail中
    将所有roomId放到roomIds中并去重
    """
    action = is_all_lights_command(input_text)
    if not action:
        return None
    
    if user_data.empty:
        return None
    
    # 生成所有设备的信息
    all_device_infos = []
    for _, row in user_data.iterrows():
        nick = row['nickName']
        dn = row['deviceName']
        pid = row['productId']
        iot = row['iotId']
        elem = row.get('element', '')
        x = elem.split('_')[-1] if elem and '_' in elem else ''
        
        device_info = {
            'custom_name': nick,
            'control_dn': dn,
            'control_pid': pid,
            'control_iotid': iot,
            'x': x,
            'action': "turn_on" if action == "打开" else "turn_off"
        }
        all_device_infos.append(device_info)
    
    if not all_device_infos:
        return None
    
    # 只取前10个设备放到iot_detail中
    limited_device_infos = all_device_infos[:10]
    
    # 获取所有roomId并去重
    all_room_ids = list(set(user_data['roomId'].dropna().astype(int)))
    
    # 获取第一个设备的家庭信息
    first_device = user_data.iloc[0]
    home = first_device.get('familyName', "未知家庭")
    
    # 构造回复文本
    reply = f"已{action}所有设备"
    
    ctrl_type = get_control_type("turn_on" if action == "打开" else "turn_off", is_group=True)
    
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "type": "iot",
            "query": input_text,
            "ability_pool": {},
            "iot_detail": {
                "home": home,
                "device_info": limited_device_infos,  # 只包含前10个设备
                "controlType": ctrl_type,
                "reply": reply,
                "roomIds": all_room_ids  # 包含所有房间ID并去重
            }
        }
    }


def is_group_light_command(input_text):
    input_text = input_text.strip()
    pats = [
        r'^(打开|关闭)灯$',
        r'^(打开|关闭)(所有|全部)灯$',
        r'^(打开|关闭)(.+?)(所有|全部)灯$'
    ]
    for p in pats:
        m = re.match(p, input_text)
        if m:
            grp = m.groups()
            act = grp[0]
            if len(grp) == 1:
                return act, None
            elif len(grp) == 2:
                return act, None if grp[1] in ['所有', '全部'] else grp[1]
            else:
                return act, grp[1]
    return None, None


def generate_group_command(user_data, action, room_name, explicit):
    """
    生成“打开/关闭 [房间]灯（全部灯）”的组控指令
    """
    # 仅处理“打开 / 关闭”
    if action not in ["打开", "关闭"]:
        return None

    # 解析得到 user_data 中真正存在的房间名
    matched_room = resolve_room_name(room_name, user_data)
    if not matched_room:          # 找不到就直接返回
        return None

    # 取出该房间的所有设备
    df = user_data[user_data['roomName'] == matched_room]
    if df.empty:
        return None

    # 组装每个设备的控制信息（只做开关）
    cmds, cmap = [], {}
    for _, row in df.iterrows():
        nick = row['nickName']
        dn = row['deviceName']
        pid = row['productId']
        iot = row['iotId']
        elem = row.get('element', '')
        x = elem.split('_')[-1] if elem and '_' in elem else ''

        key = f"{action}{nick}"
        en = "turn_on" if action == "打开" else "turn_off"

        cmds.append(key)
        cmap[key] = {
            'custom_name': nick,
            'control_dn': dn,
            'control_pid': pid,
            'control_iotid': iot,
            'x': x,
            'action': en
        }

    infos = [cmap[c] for c in cmds]
    if not infos:
        return None

    # ——— 组装返回结构 ———
    query = f"{action}{matched_room}灯"
    reply = (
        f"已{action}{matched_room}区域相关设备"
        if explicit
        else f"已{action}默认区域相关设备"
    )

    first = infos[0]
    row0 = user_data[user_data['deviceName'] == first['control_dn']].iloc[0]
    home = row0.get('familyName', "未知家庭")
    room_ids = list(set(df['roomId']))

    ctrl = get_control_type("turn_on" if action == "打开" else "turn_off", is_group=True)

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "type": "iot",
            "query": query,
            "ability_pool": {},
            "iot_detail": {
                "home": home,
                "device_info": infos,
                "controlType": ctrl,
                "reply": reply,
                "roomIds": room_ids,
            },
        },
    }


def generate_device_type_group_command(
        user_data, action, device_type, room_name=None,
        default_room=None, *, orig_query: str | None = None):
    """
    生成“打开/关闭 [房间][设备类型]”的组控指令
    """
    if action not in ["打开", "关闭"]:
        return None

    # 解析最终房间
    target_room = resolve_room_name(room_name or default_room, user_data)
    if not target_room:
        return None

    # 找到该房间中与设备类型匹配的设备
    matched_devices = find_devices_by_type(user_data, device_type, target_room)
    if matched_devices.empty:
        print(f"在 {target_room} 中未找到匹配的 {device_type} 设备")
        return None

    # ★ 仅保留 nickName == device_type  或 nickName 以 device_type 结尾 的行
    matched_devices = matched_devices[
        (matched_devices['nickName'] == device_type) |
        (matched_devices['nickName'].str.endswith(device_type))
    ]
    if matched_devices.empty:
        print(f"在 {target_room} 中未找到精确匹配的 {device_type} 设备")
        return None

    device_infos = []
    for _, row in matched_devices.iterrows():
        nick = row['nickName']
        dn = row['deviceName']
        pid = row['productId']
        iot = row['iotId']
        elem = row.get('element', '')
        x = elem.split('_')[-1] if elem and '_' in elem else ''

        device_infos.append({
            'custom_name': nick,
            'control_dn': dn,
            'control_pid': pid,
            'control_iotid': iot,
            'x': x,
            'action': "turn_on" if action == "打开" else "turn_off"
        })

    if not device_infos:
        return None

    query = orig_query if orig_query else f"{action}{target_room}{device_type}"
    reply = f"已{action}{target_room}区域的所有{device_type}"

    first_device = matched_devices.iloc[0]
    home = first_device.get('familyName', "未知家庭")
    room_ids = list(set(matched_devices['roomId'].dropna()))

    ctrl_type = get_control_type(
        "turn_on" if action == "打开" else "turn_off",
        is_group=True
    )

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "type": "iot",
            "query": query,
            "ability_pool": {},
            "iot_detail": {
                "home": home,
                "device_info": device_infos,
                "controlType": ctrl_type,
                "reply": reply,
                "roomIds": room_ids,
            },
        },
    }



def process_group_command(input_text, user_data, default_room):
    # 匹配"打开/关闭 XX 灯"，返回 (action, room or None)
    action, room = is_group_light_command(input_text)
    if not action:
        return None

    # 区分用户是否明确说了区域
    explicit = bool(room)
    target_room = room or default_room
    return generate_group_command(user_data, action, target_room, explicit)


def is_device_type_command(input_text):
    """
    检查指令是否为设备类型组控命令
    匹配模式: (打开|关闭) [房间名] (设备类型)
    例如: "打开射灯", "关闭客厅筒灯", "打开卧室射灯"
    """
    input_text = input_text.strip()
    
    # 构建设备类型的正则模式
    device_patterns = []
    for device_type in DEVICE_TYPES:
        # 处理带.*?的正则类型（如轨道.*?灯）
        if '.*?' in device_type:
            device_patterns.append(device_type)
        else:
            # 普通设备类型直接转义
            device_patterns.append(re.escape(device_type))
    
    device_pattern = '|'.join(device_patterns)
    
    # 匹配模式: (打开|关闭) [房间名] (设备类型)
    patterns = [
        rf'^(打开|关闭)({device_pattern})$',  # 打开射灯
        rf'^(打开|关闭)(.+?)({device_pattern})$'  
    ]
    
    for pattern in patterns:
        match = re.match(pattern, input_text)
        if match:
            groups = match.groups()
            action = groups[0]
            if len(groups) == 2:
                # 没有指定房间
                return action, None, groups[1]
            else:
                # 指定了房间
                return action, groups[1].strip(), groups[2]
    
    return None, None, None


def find_devices_by_type(user_data, device_type, room_name=None):
    """
    根据设备类型和房间名查找匹配的设备
    """
    # 如果指定了房间，先筛选房间
    if room_name:
        filtered_data = user_data[user_data['roomName'] == room_name]
    else:
        filtered_data = user_data
    
    if filtered_data.empty:
        return pd.DataFrame()
    
    # 根据设备类型筛选设备
    # 处理带.*?的正则类型
    if '.*?' in device_type:
        pattern = device_type
    else:
        pattern = re.escape(device_type)
    
    # 在nickName中查找匹配的设备
    matched_devices = filtered_data[
        filtered_data['nickName'].str.contains(pattern, case=False, na=False, regex=True)
    ]
    
    return matched_devices



def process_device_type_command(input_text, user_data, default_room):
    action, room_name, device_type = is_device_type_command(input_text)
    if not action or not device_type:
        return None

    return generate_device_type_group_command(
        user_data, action, device_type,
        room_name, default_room, orig_query=input_text
    )



def resolve_room_name(room_name: str, user_data: pd.DataFrame) -> str | None:
    """
    根据用户说的房间名称，在 user_data['roomName'] 里找到最合适的实际房间名。
    """
    if not room_name or user_data is None or user_data.empty:
        return None
    rooms = list(set(user_data['roomName'].dropna()))
    if room_name in rooms:
        return room_name
    for r in rooms:
        if room_name in r or r in room_name:
            return r
    return None



def generate_global_commands(user_data):
    """
    生成全局命令表，格式为: 房间名+设备名+动作
    例如: "打开茶室RGB灯带", "关闭客厅吊灯", "茶室RGB灯带亮度调高"
    """
    global_commands = []
    global_cmd_map = {}
    
    for _, row in user_data.iterrows():
        room_name = row['roomName']
        nick = row['nickName']
        dn = row['deviceName']
        pid = row['productId']
        iot = row['iotId']
        elem = row.get('element', '')
        x = elem.split('_')[-1] if elem and '_' in elem else ''
        
        # 开关操作
        for act in ACTION:
            key = f"{act}{room_name}{nick}"
            en = "turn_on" if act == "打开" else "turn_off"
            global_commands.append(key)
            global_cmd_map[key] = {
                'custom_name': nick,
                'control_dn': dn,
                'control_pid': pid,
                'control_iotid': iot,
                'x': x,
                'action': en,
                'room_name': room_name  # 添加房间名信息
            }
        
        # 灯光操作
        for la in LIGHT_ACTION:
            key = f"{room_name}{nick}{la}"
            base = {
                'custom_name': nick,
                'control_dn': dn,
                'control_pid': pid,
                'control_iotid': iot,
                'x': x,
                'room_name': room_name  # 添加房间名信息
            }
            data = base.copy()
            
            m_b = re.match(r'亮度调到(\d+)%', la)
            if m_b:
                data.update({'action': 'light_value', 'value': int(m_b.group(1)), 'percentage': True})
            elif la == "亮度调高":
                data['action'] = 'light_up'
            elif la == "亮度调低":
                data['action'] = 'light_down'
            elif la == "色温调高":
                data['action'] = 'color_temperature_up'
            elif la == "色温调低":
                data['action'] = 'color_temperature_down'
            else:
                m_t = re.match(r'色温调到(\d+)k', la, re.IGNORECASE)
                if m_t:
                    data.update({'action': 'color_temperature_value', 'value': int(m_t.group(1)), 'percentage': False})
            
            global_commands.append(key)
            global_cmd_map[key] = data
    
    return global_commands, global_cmd_map


def try_regex_rules(dn, input_text):
    """
    尝试使用正则规则处理智能家居控制指令
    
    Args:
        dn: 设备名称
        input_text: 语音指令文本
        
    Returns:
        dict: 结构化的控制指令，如果无法处理则返回None
    """
    print("正在获取用户信息...")
    user_data, user_home, local = user_info_no_cache(dn)
    if user_data is None:
        print("获取用户信息失败")
        return None
    print(f"用户信息获取成功！家庭：{user_home}，默认房间：{local}")

    # 首先检查是否为"打开/关闭所有灯"命令
    all_lights_result = process_all_lights_command(input_text, user_data)
    if all_lights_result:
        print(json.dumps(all_lights_result, ensure_ascii=False, indent=4, cls=NumpyEncoder))
        return all_lights_result

    # 再尝试其他组控：设备类型组控 > 灯组控
    device_type_result = process_device_type_command(input_text, user_data, local)
    if device_type_result:
        print(json.dumps(device_type_result, ensure_ascii=False, indent=4, cls=NumpyEncoder))
        return device_type_result

    grp = process_group_command(input_text, user_data, local)
    if grp:
        print(json.dumps(grp, ensure_ascii=False, indent=4, cls=NumpyEncoder))
        return grp

    # 单控流程：先尝试generate_commands生成的命令表
    info = information_extraction(input_text, user_data, local)
    cmds, cmap = generate_commands(info, user_data)
    
    # 检查generate_commands生成的命令表是否有完全匹配
    if cmds:
        for c in cmds:
            structured = format_command_to_structure(c, cmap[c], user_data, is_group=False)
            if structured.get("data", {}).get("query", "") == input_text:
                print(json.dumps(structured, ensure_ascii=False, indent=4, cls=NumpyEncoder))
                return structured

    # 全屋控制指令匹配
    global_cmds, global_cmap = generate_global_commands(user_data)
    
    # 检查全局命令表是否有完全匹配
    if global_cmds:
        for c in global_cmds:
            if c == input_text:  # 完全匹配
                structured = format_command_to_structure(c, global_cmap[c], user_data, is_group=False)
                # 更新query为原始输入文本
                structured["data"]["query"] = input_text
                print(json.dumps(structured, ensure_ascii=False, indent=4, cls=NumpyEncoder))
                return structured

    print("无法生成任何有效指令，请检查输入。")
    return None


def main(dn=None, input_text=None):
    """
    主函数，用于命令行调用
    """
    if dn is None:
        dn = sys.argv[1] if len(sys.argv) > 1 else input("请输入设备名称(dn): ")

    # 获取语音指令
    if input_text is None:
        input_text = input("请输入语音指令（例如：打开客厅的主灯 或 打开射灯 或 打开所有灯）：")

    return try_regex_rules(dn, input_text)