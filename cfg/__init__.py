import copy
import datetime
import io
import time
from datetime import timedelta
import os
from pathlib import Path
ROOT=Path(os.getcwd()).as_posix()
os.environ['HF_HOME'] = ROOT + "/models"
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = 'true'
import re
import sys
import textwrap
import json,math
import random
import shutil,logging,hashlib
from filelock import FileLock, Timeout
from . import dubb
VOICE_LIST={
"en":[
"af_alloy",
"af_aoede",
"af_bella",
"af_jessica",
"af_kore",
"af_nicole",
"af_nova",
"af_river",
"af_sarah",
"af_sky",
"am_adam",
"am_echo",
"am_eric",
"am_fenrir",
"am_liam",
"am_michael",
"am_onyx",
"am_puck",
"am_santa",
"bf_alice",
"bf_emma",
"bf_isabella",
"bf_lily",
"bm_daniel",
"bm_fable",
"bm_george",
"bm_lewis"
],
"zh":["zf_xiaobei","zf_xiaoni","zf_xiaoxiao","zf_xiaoyi","zm_yunjian","zm_yunxi","zm_yunxia","zm_yunyang"],
"ja":["jf_alpha","jf_gongitsune","jf_nezumi","jf_tebukuro","jm_kumo"],
"fr":["ff_siwis"],
"it":["if_sara","im_nicola"],
"hi":["hf_alpha","hf_beta","hm_omega","hm_psi"],
"es":["ef_dora","em_alex","em_santa"],
"pt":["pf_dora","pm_alex","pm_santa"]
}





TEMP_FOLDER = f'{ROOT}/temp'
LOGS_FOLDER = f'{ROOT}/logs'





if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)
if not os.path.exists(LOGS_FOLDER):
    os.makedirs(LOGS_FOLDER)

if sys.platform == 'win32':
    os.environ['PATH'] = ROOT + f';{ROOT}/ffmpeg;' + os.environ['PATH']


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_file_handler = logging.FileHandler(f'{LOGS_FOLDER}/{datetime.datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
_file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_file_handler.setFormatter(formatter)
logger.addHandler(_file_handler)



# 将字符串做 md5 hash处理
def get_md5(input_string: str):
    md5 = hashlib.md5()
    md5.update(input_string.encode('utf-8'))
    return md5.hexdigest()


'''
格式化毫秒或秒为符合srt格式的 2位小时:2位分:2位秒,3位毫秒 形式
print(ms_to_time_string(ms=12030))
-> 00:00:12,030
'''
def ms_to_time_string(*, ms=0, seconds=None):
    # 计算小时、分钟、秒和毫秒
    if seconds is None:
        td = timedelta(milliseconds=ms)
    else:
        td = timedelta(seconds=seconds)
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = td.microseconds // 1000

    time_string = f"{hours}:{minutes}:{seconds},{milliseconds}"
    return format_time(time_string, ',')

# 将不规范的 时:分:秒,|.毫秒格式为  aa:bb:cc,ddd形式
# eg  001:01:2,4500  01:54,14 等做处理
def format_time(s_time="", separate=','):
    if not s_time.strip():
        return f'00:00:00{separate}000'
    hou, min, sec,ms = 0, 0, 0,0

    tmp = s_time.strip().split(':')
    if len(tmp) >= 3:
        hou,min,sec = tmp[-3].strip(),tmp[-2].strip(),tmp[-1].strip()
    elif len(tmp) == 2:
        min,sec = tmp[0].strip(),tmp[1].strip()
    elif len(tmp) == 1:
        sec = tmp[0].strip()
    
    if re.search(r',|\.', str(sec)):
        t = re.split(r',|\.', str(sec))
        sec = t[0].strip()
        ms=t[1].strip()
    else:
        ms = 0
    hou = f'{int(hou):02}'[-2:]
    min = f'{int(min):02}'[-2:]
    sec = f'{int(sec):02}'
    ms = f'{int(ms):03}'[-3:]
    return f"{hou}:{min}:{sec}{separate}{ms}"

# 将 datetime.timedelta 对象的秒和微妙转为毫秒整数值
def toms(td):
    return (td.seconds * 1000) + int(td.microseconds / 1000)

# 将 时:分:秒,毫秒 转为毫秒整数值
def get_ms_from_hmsm(time_str):
    h,m,sec2ms=0,0,'00,000'
    tmp0= time_str.split(":")
    if len(tmp0)==3:
        h,m,sec2ms=tmp0[0],tmp0[1],tmp0[2]
    elif len(tmp0)==2:
        m,sec2ms=tmp0[0],tmp0[1]
        
    tmp=sec2ms.split(',')
    ms=tmp[1] if len(tmp)==2 else 0
    sec=tmp[0]
    
    return int(int(h) * 3600000 + int(m) * 60000 +int(sec)*1000 + int(ms))


def srt_str_to_listdict(srt_string):
    """解析 SRT 字幕字符串，更精确地处理数字行和时间行之间的关系"""
    srt_list = []
    time_pattern = r'\s?(\d+):(\d+):(\d+)([,.]\d+)?\s*?-->\s*?(\d+):(\d+):(\d+)([,.]\d+)?\n?'
    lines = srt_string.splitlines()
    i = 0
    while i < len(lines):
        time_match = re.match(time_pattern, lines[i].strip())
        if time_match:
            # 解析时间戳
            start_time_groups = time_match.groups()[0:4]
            end_time_groups = time_match.groups()[4:8]

            def parse_time(time_groups):
                h, m, s, ms = time_groups
                ms = ms.replace(',', '').replace('.','') if ms else "0"
                try:
                    return int(h) * 3600000 + int(m) * 60000 + int(s)*1000 + int(ms)
                except (ValueError, TypeError):
                    return None

            start_time = parse_time(start_time_groups)
            end_time = parse_time(end_time_groups)

            if start_time is None or end_time is None:
                i += 1
                continue

            i += 1
            text_lines = []
            while i < len(lines):
                current_line = lines[i].strip()
                next_line = lines[i+1].strip() if i + 1 < len(lines) else "" # 获取下一行，如果没有则为空字符串

                if re.match(time_pattern, next_line): #判断下一行是否为时间行
                    if re.fullmatch(r'\d+', current_line): #如果当前行为纯数字，则跳过
                        i += 1
                        break
                    else:
                        text_lines.append(current_line)
                        i += 1
                        break

                if current_line:
                    text_lines.append(current_line)
                    i += 1
                else:
                    i += 1

            text = ('\n'.join(text_lines)).strip()
            text=re.sub(r'</?[a-zA-Z]+>','',text.replace("\r",'').strip())
            text=re.sub(r'\n{2,}','\n',text)
            it={
                "line": len(srt_list)+1,  #字幕索引，转换为整数
                "start_time": int(start_time), 
                "end_time":int(end_time),  #起始和结束时间
                "text": text, #字幕文本
            }
            it['startraw']=ms_to_time_string(ms=it['start_time'])
            it['endraw']=ms_to_time_string(ms=it['end_time'])
            it["time"]=f"{it['startraw']} --> {it['endraw']}"
            srt_list.append(it)


        else:
            i += 1 # 跳过非时间行
      

    return srt_list


# 将字符串或者字幕文件内容，格式化为有效字幕数组对象
# 格式化为有效的srt格式
def format_srt(content):
    result=[]
    try:
        result=srt_str_to_listdict(content)
    except Exception:
        pass
    return result




# 将srt文件或合法srt字符串转为字典对象
def get_subtitle_from_srt(srtfile, *, is_file=True):
    def _readfile(file):
        content=""
        try:
            with open(file,'r',encoding='utf-8') as f:
                content=f.read().strip()
        except Exception as e:
            try:
                with open(file,'r', encoding='gbk') as f:
                    content = f.read().strip()
            except Exception as e:
                logger.exception(e,exc_info=True)
        return content

    content=''
    if is_file:
        content=_readfile(srtfile)
    else:
        content = srtfile.strip()

    if len(content) < 1:
        raise Exception(f"srt is empty:{srtfile=},{content=}")

    result = format_srt(content)

    # txt 文件转为一条字幕
    if len(result) < 1:
        result = [
            {"line": 1, "time": "00:00:00,000 --> 00:00:02,000", "text": "\n".join(content)}
        ]
    return result


# 将字幕字典列表写入srt文件
def save_srt(srt_list, srt_file):
    txt = get_srt_from_list(srt_list)
    with open(srt_file,"w", encoding="utf-8") as f:
        f.write(txt)
    return True

def get_current_time_as_yymmddhhmmss(format='hms'):
  """将当前时间转换为 YYMMDDHHmmss 格式的字符串。"""
  now = datetime.datetime.now()
  return now.strftime("%y%m%d%H%M%S" if format!='hms' else "%H%M%S")

# 从 字幕 对象中获取 srt 字幕串
def get_srt_from_list(srt_list):
    txt = ""
    line = 0
    # it中可能含有完整时间戳 it['time']   00:00:01,123 --> 00:00:12,345
    # 开始和结束时间戳  it['startraw']=00:00:01,123  it['endraw']=00:00:12,345
    # 开始和结束毫秒数值  it['start_time']=126 it['end_time']=678
    for it in srt_list:
        line += 1
        if "startraw" not in it:
            # 存在完整开始和结束时间戳字符串 时:分:秒,毫秒 --> 时:分:秒,毫秒
            if 'time' in it:
                startraw, endraw = it['time'].strip().split(" --> ")
                startraw = format_time(startraw.strip().replace('.', ','), ',')
                endraw = format_time(endraw.strip().replace('.', ','), ',')
            elif 'start_time' in it and 'end_time' in it:
                # 存在开始结束毫秒数值
                startraw = ms_to_time_string(ms=it['start_time'])
                endraw = ms_to_time_string(ms=it['end_time'])
            else:
                raise Exception(
                    f'字幕中不存在 time/startraw/start_time 任何有效时间戳形式')
        else:
            # 存在单独开始和结束  时:分:秒,毫秒 字符串
            startraw = it['startraw']
            endraw = it['endraw']
        txt += f"{line}\n{startraw} --> {endraw}\n{it['text']}\n\n"
    return txt

