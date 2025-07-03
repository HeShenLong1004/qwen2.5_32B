import json
import logging

api_key = 'EMPTY'
llm_model_name = '/data/maxin/Qwen2.5-32B-Instruct'#qwen-plus-latest
dashscope_url = 'http://36.213.210.39:8000/v1'

skill_name = {'新闻':'news','天气':'weather','日历':'calendar','亲戚关系计算':'relation_computation','笑话':'joke','单位换算':'unit_conversion','节假日查询':'holiday_query','交通限行':'traffic_control','计算器':'calculator','翻译':'translate','音乐':'music','儿歌':'children_song','电台':'network_broadcasting_station','有声书':'talking_book','故障':'feedback'}

command_name = {'结束对话':'Assistant.Dialogue.Close','音量上调':'System.Volume.Loud','音量下调':'System.Volume.Down','设置音量':'System.Volume.Set','静音':'System.Volume.Mute','无效语音':'Assistant.Dialogue.Invalid'}

reply_prompt = {'turn_on':'已打开','turn_off':'已关闭','light_up':'亮度已调高','light_down':'亮度已调低','light_value':'亮度已调节到','color_temperature_up':'色温已调冷','color_temperature_down':'色温已调暖','color_temperature_value':'色温已调节到'}

device_type = ['筒灯','射灯','灯带','格栅灯','吊线灯','线条灯','轨道.*?灯','智能.*?灯','开关','轨道','空调','内机','风管机','AC','新风']

scene_reply = ['好的哟。','已为小主找到了你想要的场景。','正在跑步前去帮小主执行。']

filename = 'question_scene.json'

# 打开文件并加载JSON数据
with open(filename, 'r', encoding='utf-8') as f:
    question_scene = json.load(f)

# 使用字典推导式去掉值为空列表的键值对
question_scene = {k: v for k, v in question_scene.items() if v != []}

def setup_logger(name, log_file, level=logging.INFO):
    # 创建一个日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # 设置最低捕获级别

    # 创建一个处理器，用于将日志输出到控制台

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # 设置输出到控制台的日志级别

    # 创建一个处理器，用于将日志写入文件
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # 设置写入文件的日志级别

    # 定义日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 为控制台处理器设置格式
    console_handler.setFormatter(formatter)

    # 为文件处理器设置格式
    file_handler.setFormatter(formatter)

    # 给日志记录器添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
