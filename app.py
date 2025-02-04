from flask import Flask, request, jsonify,send_file,render_template,send_from_directory
from flask_cors import CORS
from pathlib import Path
import os,time,random,re,threading
from waitress import serve
import cfg


app = Flask(__name__, template_folder="templates")

@app.route("/static/<path:filename>")
def send_data_file(filename):
    return send_from_directory(cfg.ROOT+f'/static', filename)

@app.route("/temp/<path:filename>")
def send_data_file2(filename):
    return send_from_directory(cfg.ROOT+f'/temp', filename)


@app.route('/v1/audio/speech', methods=['POST'])
def audio_speech():
    """
    兼容 OpenAI /v1/audio/speech API 的接口
    """
    if not request.is_json:
        return jsonify({"error": "请求必须是 JSON 格式"}), 400

    data = request.get_json()

    # 检查请求中是否包含必要的参数
    if 'input' not in data or 'voice' not in data:
        return jsonify({"error": "请求缺少必要的参数： input, voice"}), 400
    

    text = data.get('input')
    
    voice = data.get('voice','')
    
    
    speed = float(data.get('speed',1.0))
    
    try:
        filename=cfg.dubb.process_synthesize_task(
                    text,
                    voice,
                    speed,
                    False,
                    False)
        return send_file(filename, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({"error": {"message": f"{e}", "type": e.__class__.__name__, "param": f'speed={speed},voice={voice},input={text}', "code": 400}}), 500



# 语音合成
@app.route("/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json()
    text = data.get("text")
    voice = data.get("voice")
    speed = float(data.get("speed", 1.0))

    keep_spacing = bool(data.get("keep_spacing", False))
    auto_speed = bool(data.get("auto_speed", False))
    if re.match(
            r"^1\s*[\r\n]+\s*\d{1,2}:\d{1,2}:\d{1,2}(\,\d{1,3})?\s*-->\s*\d{1,2}:\d{1,2}:\d{1,2}(\,\d{1,3})?",
            text.strip(),
        ):
        text = cfg.get_subtitle_from_srt(text, is_file=False)
    try:
        filename=cfg.dubb.process_synthesize_task(
                    text,
                    voice,
                    speed,
                    keep_spacing,
                    auto_speed)
        return jsonify(
                {
                    "status": "ok",
                    "data": f"/temp/{Path(filename).name}",
                }
            )
    except Exception as e:
        return jsonify({"error": f"{e}"}), 500
   

# 首页
@app.route("/")
def index():
    return render_template("index.html")   
    

def openwebbrowser(port):
    time.sleep(5)
    try:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}")
    except:
        pass
    
PORT=5066
if __name__ == '__main__':
    try:
        threading.Thread(target=openwebbrowser,args=(PORT,)).start()
        serve(app, host='0.0.0.0', port=PORT,threads=8)
    except Exception as e:
        import traceback
        traceback.print_exc()