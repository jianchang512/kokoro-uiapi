import json
import cfg
import os,sys,time,asyncio,re,copy,base64,requests,shutil
from pydub import AudioSegment
from pathlib import Path
import concurrent.futures
from kokoro import KPipeline
import soundfile as sf
from . import cn_tn,en_tn
def merge_audio_segments(queue_tts,filename,keep_spacing=False,auto_speed=False):
    from pydub import AudioSegment
    merged_audio = AudioSegment.empty()
    err=0
    length = len(queue_tts)
    if length == 1:
        if queue_tts[0]['filename']!=filename:
            m=AudioSegment.from_file(queue_tts[0]['filename'], format=queue_tts[0]['filename'][-3:])
            m.export(filename, format="mp3")
            #shutil.copy2(queue_tts[0]['filename'],filename)
        return filename

    # start is not 0
    if keep_spacing and queue_tts[0]['start_time'] > 0:
        merged_audio += AudioSegment.silent(duration=queue_tts[0]['start_time'])

    # 开始时间

    for i, it in enumerate(queue_tts):

        # 存在有效配音文件则加入，否则配音时长大于0则加入静音
        segment = None
        the_ext = it['filename'][-3:]

        # 存在配音文件
        if Path(it['filename']).is_file():
            raw_time=it['end_time']-it['start_time']
            try:
                segment = AudioSegment.from_file(it['filename'], format=the_ext)
                dubb_time=len(segment)
                if raw_time and auto_speed:
                    if  raw_time<dubb_time:
                        segment=segment.speedup(playback_speed=min(3,dubb_time/raw_time))
                    elif raw_time>dubb_time:
                        segment+=AudioSegment.silent(duration=raw_time-dubb_time)   

                merged_audio+=segment
            except Exception as e:
                err+=1
                cfg.logger.exception(e, exc_info=True)
                merged_audio += AudioSegment.silent(duration=raw_time)
        else:
            # 不存在配音文件
            err+=1

        if i< length-1 and keep_spacing:
            silent_time=queue_tts[i+1]['start_time']-it['end_time']
            if silent_time>0:
                merged_audio += AudioSegment.silent(duration=silent_time)
    if err>length/2:
        raise Exception("Too many errors, please try again later.")
    merged_audio.export(filename, format="mp3")
    return filename


def process_synthesize_task(text, voice, speed=1.0, keep_spacing=False,auto_speed=False):
    try:
       return TTS(text, voice, speed,  keep_spacing,auto_speed).run()
    except Exception as e:
        cfg.logger.exception(f'配音失败 {e}',exc_info=True)
        raise



class TTS:

    def __init__(self, text,voice, speed,  keep_spacing,auto_speed):
        self.uuid=cfg.get_md5(f'{str(text)}-{voice}-{speed}-{keep_spacing}-{auto_speed}')
        self.end_mp3name=f'{cfg.TEMP_FOLDER}/dubbing-end-{self.uuid}.mp3'

        self.keep_spacing=keep_spacing
        self.auto_speed=auto_speed
        normalizer=None
        if voice[0] == 'z':
            normalizer = cn_tn.TextNorm(to_banjiao = True)
        elif voice[0] in ['a','b']:
            normalizer = en_tn.EnglishNormalizer()
        

        # 如果不是srt字幕
        if isinstance(text,str):
            self.queue_tts=[{
                "text":normalizer(text.strip()) if normalizer else text.strip(),
                "voice":voice,
                "speed":speed,
                "filename":self.end_mp3name+".wav",
                "break":0
            }]
        else:
            self.queue_tts=[]
            length=len(text)
            for i,it in enumerate(text):
                fname=cfg.TEMP_FOLDER+'/'+cfg.get_md5(f'{it["text"]}-{voice}-{speed}')+'.wav' 
                self.queue_tts.append({
                    "text": normalizer(it['text']) if normalizer else  it['text'],
                    "voice": voice,
                    "start_time": it['start_time'],
                    "end_time": it['end_time'],
                    "speed": speed,
                    "filename":  fname,
                    "break":text[i+1]['start_time']-it['end_time'] if self.keep_spacing and i<length-1 else 0
                })

    def run(self):
        return self._create()


    # 仅中文配音
    def _create(self):
        for it in self.queue_tts:
            speed = 1.0
            pipeline = KPipeline(lang_code=it['voice'][0]) # <= make sure lang_code matches voice


            if it['speed']:
                speed = float(it['speed'])
            print(f'{it["text"]=}')
            generator = pipeline(
                it['text'], voice=it['voice'], # <= change voice here
                speed=speed, split_pattern=r'\n+'
            )
            for i, (gs, ps, audio) in enumerate(generator):
                print(i)  # i => index
                print(gs) # gs => graphemes/text
                print(ps) # ps => phonemes
                sf.write(it['filename'], audio, 24000) # save each audio file

        return merge_audio_segments(self.queue_tts,self.end_mp3name,self.keep_spacing,self.auto_speed)


