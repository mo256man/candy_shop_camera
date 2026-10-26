isMediaPipeAvailable = True

import os
import re
import threading
import platform
import subprocess
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import cv2
import time
import serial
import serial.tools.list_ports
from myCamera import Camera
from myDatabase import insert_camera_row, get_camera_records, delete_record, delete_records_by_date_range, get_record_dates, insert_environment_row, VIDEO_DIR, THUMB_DIR, SNAPSHOT_DIR
from myMemory import get_disk_and_folder_usage, export_data_to_usb

# グローバル終了フラグ
stop_flag = threading.Event()

# USBエクスポートの進捗状態（ポーリング用）
export_progress_lock = threading.Lock()
export_progress = {
  "status": "idle", "phase_no": 0, "phase_count": 4, "phase_label": "",
  "phase_done": 0, "phase_total": 0, "phase_percent": 0,
  "message": "", "count": 0, "snapshot_count": 0, "usb_path": "", "device": "",
}


def _run_export_job(date_from, date_to):
  """バックグラウンドスレッドでエクスポートを実行し、進捗状態を更新する"""
  def on_progress(phase_info):
    with export_progress_lock:
      export_progress.update(phase_info)

  result = export_data_to_usb(date_from, date_to, progress_callback=on_progress)

  with export_progress_lock:
    if result.get("status") == "success":
      export_progress["status"] = "success"
      export_progress["count"] = result.get("count", 0)
      export_progress["snapshot_count"] = result.get("snapshot_count", 0)
      export_progress["usb_path"] = result.get("usb_path", "")
      export_progress["device"] = result.get("device", "")
    else:
      export_progress["status"] = "error"
      export_progress["message"] = result.get("message", "エクスポートに失敗しました")

# OS情報を起動時に一度だけ取得
SYSTEM_OS = platform.system()

# ラズパイPico（センサー）とのシリアル通信設定
PICO_BAUDRATE = 115200
PICO_TIMEOUT = 2.0

_pico_serial = None
_pico_lock = threading.Lock()
_last_environment_hour = -1  # 最後に環境データを記録した時刻（hour）


def _find_pico_port():
  """ラズパイPicoのシリアルポートを自動検出"""
  ports = list(serial.tools.list_ports.comports())

  for port in ports:
    if "pico" in (port.description or "").lower():
      return port.device

  # descriptionに'pico'を含まない環境向けのフォールバック（check_pico.py参照）
  for port in ports:
    if "ttyACM" in port.device:
      return port.device

  return None


def _get_pico_serial():
  """Picoとのシリアル接続を取得（未接続または切断時は接続を試みる）"""
  global _pico_serial
  if _pico_serial is not None and _pico_serial.is_open:
    return _pico_serial

  port = _find_pico_port()
  if port is None:
    return None

  try:
    _pico_serial = serial.Serial(port, PICO_BAUDRATE, timeout=PICO_TIMEOUT)
    print(f"[Pico] Connected: {port}", flush=True)
  except serial.SerialException as e:
    print(f"[Pico] Connection failed: {e}", flush=True)
    _pico_serial = None

  return _pico_serial


def _send_pico_command(command):
  """Picoにコマンド文字列を送信し、応答（JSON）を取得する"""
  with _pico_lock:
    ser = _get_pico_serial()
    if ser is None:
      return None

    try:
      ser.reset_input_buffer()
      ser.write((command + "\n").encode())
      line = ser.readline()
      if not line:
        return None
      return json.loads(line.decode().strip())
    except (serial.SerialException, ValueError, UnicodeDecodeError) as e:
      print(f"[Pico] Command '{command}' failed: {e}", flush=True)
      return None


def _read_pico_environment():
  """PicoにGET_TEMPERATUREを送信し、気温・湿度・気圧を取得"""
  return _send_pico_command("GET_TEMPERATURE")


# サーバー側で把握しているPicoの現在のLED演出（起動直後はPico自体の初期値である"blank"と仮定）
_current_led_label = "blank"
_pre_recording_led_label = None  # 録画開始前の演出を復帰するためのバックアップ
_led_state_lock = threading.Lock()


def _set_led_effect(label):
  """PicoにLED_<label>を送信し、現在の演出として記録する"""
  global _current_led_label
  _send_pico_command(f"LED_{label}")
  with _led_state_lock:
    _current_led_label = label


def _on_recording_change(is_recording):
  """録画開始/終了に合わせてLED演出を切替える（開始時:half、終了時:元の演出に復帰）"""
  global _pre_recording_led_label

  if is_recording:
    with _led_state_lock:
      _pre_recording_led_label = _current_led_label
    _set_led_effect("half")
  else:
    with _led_state_lock:
      restore_label = _pre_recording_led_label or "blank"
      _pre_recording_led_label = None
    _set_led_effect(restore_label)


def _environment_logger_loop():
  """毎時0分にPicoから気温・湿度・気圧を取得し、_environment.sqliteに記録する"""
  global _last_environment_hour

  print("[Environment] Logger thread started", flush=True)

  while not stop_flag.is_set():
    try:
      now_dt = datetime.now()

      # 毎時0分に1回だけ記録（スナップショットと同様、秒は強制的に00とする）
      if now_dt.minute == 0 and now_dt.hour != _last_environment_hour:
        _last_environment_hour = now_dt.hour
        data = _read_pico_environment()

        if data is not None:
          record_dt = now_dt.replace(minute=0, second=0, microsecond=0)
          insert_environment_row(
            record_dt.strftime("%Y-%m-%d %H:%M:%S"),
            data.get("temperature"),
            data.get("humidity"),
            data.get("pressure"),
          )
          print(f"[Environment] Saved: {record_dt}", flush=True)
        else:
          print("[Environment] Failed to read from Pico", flush=True)
    except Exception as e:
      # 想定外の例外でスレッドが無言で停止しないよう、ログに残して継続する
      import traceback
      print(f"[Environment] Error in logger loop: {e}", flush=True)
      traceback.print_exc()

    time.sleep(5)


_last_led_schedule_hour = -1  # 最後にLED演出命令を送った時刻（hour）


def _led_night_schedule_loop():
  """時間帯に応じてPicoのLED演出を自動切替する

  20時: 消灯（LED_blank）
  21〜23時、0〜7時: 命令を送らない（消灯状態を維持）
  8〜19時: 毎時0分にランダム演出（LED_random）
  """
  global _last_led_schedule_hour

  while not stop_flag.is_set():
    now_dt = datetime.now()

    if now_dt.minute == 0 and now_dt.hour != _last_led_schedule_hour:
      _last_led_schedule_hour = now_dt.hour

      if now_dt.hour == 20:
        _set_led_effect("blank")
      elif 8 <= now_dt.hour <= 19:
        _set_led_effect("random")

    time.sleep(5)

app = Flask(__name__)
app.config["SECRET_KEY"] = "vendor_camera_secret"

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output'))

# CORSを設定：すべてのオリジンからのリクエスト、すべてのメソッド、すべてのヘッダーを許可
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

class Config:
  """アプリケーション設定管理"""
  def __init__(self):
    self.is_ai_available = isMediaPipeAvailable
    self.ready_record = False
    self._is_recording = False
    self.is_manual_recording = False
    self.is_running = False
    self.previous_recording = False
    self.on_recording_change = None
    self.clear_recording_state()

  @property
  def is_recording(self):
    return self._is_recording

  @is_recording.setter
  def is_recording(self, value):
    self._is_recording = value
  
  def clear_recording_state(self):
    self.record_start_dt = None
    self.record_fps = None
    self.record_writer = None
    self.next_write_time = None
    self.tick = None
    self.record_out_w = None
    self.record_out_h = None
    self.record_start_dt = None
    self.record_fps = None
    self.record_writer = None
    self.next_write_time = None
    self.tick = None
    self.record_out_w = None
    self.record_out_h = None

config = Config()
camera = Camera(config)
config.on_recording_change = _on_recording_change



def _generate_frames():
  """MJPEG フレームをジェネレータで垂れ流す"""
  target_fps = 15.0
  frame_interval = 1.0 / target_fps
  encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
  while not stop_flag.is_set():
    loop_start = time.perf_counter()
    frame = camera.get_frame()
    if frame is None:
      time.sleep(0.05)
      continue

    ret, buffer = cv2.imencode(".jpg", frame, encode_params)
    if not ret:
      time.sleep(0.01)
      continue

    yield (
      b"--frame\r\n"
      b"Content-Type: image/jpeg\r\n\r\n"
      + buffer.tobytes()
      + b"\r\n"
    )

    # 配信レートを制限し、ストリームがワーカースレッドを占有し続けないようにする
    sleep_time = frame_interval - (time.perf_counter() - loop_start)
    if sleep_time > 0:
      time.sleep(sleep_time)


@app.route("/api/video_feed")
def video_feed():
  """MJPEG ビデオフィード配信"""
  resp = Response(
    _generate_frames(),
    mimetype="multipart/x-mixed-replace; boundary=frame"
  )
  resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
  resp.headers["Pragma"] = "no-cache"
  resp.headers["Connection"] = "close"
  return resp


@app.route("/api/get_camera", methods=["GET"])
def get_camera():
  """現在のカメラIDを取得"""
  return jsonify({"camera_id": camera.camera_id})


@app.route("/api/get_temperature", methods=["GET"])
def get_temperature():
  """クライアントからの要求時にPicoから気温を取得（都度取得、DB登録はしない）"""
  data = _read_pico_environment()
  if data is None:
    return jsonify({"status": "error", "message": "Picoから取得できませんでした"}), 502
  return jsonify({"status": "success", "temperature": data.get("temperature")})


@app.route("/api/get_status", methods=["GET"])
def get_status():
  """現在のサーバー状態をまとめて取得"""
  return jsonify({
    "camera_id": camera.camera_id,
    "is_running": config.is_running,
    "is_recording": config.is_recording,
    "ready_record": config.ready_record,
  })


@app.route("/api/get_disk_usage", methods=["GET"])
def get_disk_usage():
  """ディスク使用状況を取得"""
  usage_info = get_disk_and_folder_usage(SYSTEM_OS)
  return jsonify(usage_info)


@app.route("/api/set_camera", methods=["POST"])
def set_camera():
  """カメラを切り替え"""
  data = request.get_json()
  camera_id = data.get("camera_id")
  print(f"[POST /api/set_camera] Setting camera_id to {camera_id}")
  
  # camera_id=0（停止）は常に実行してカメラを確実に解放する
  if camera_id == 0:
    camera.initialize(0)
    print(f"[POST /api/set_camera] Camera stopped and released.")
    return jsonify({"status": "success", "camera_id": 0})

  # 同じカメラIDなら再初期化をスキップ（ランプの点滅を防ぐ）
  if camera.camera_id == camera_id:
    print(f"[POST /api/set_camera] Camera {camera_id} is already initialized. Skipping.")
    return jsonify({"status": "success", "camera_id": camera_id, "already_initialized": True})
  
  try:
    camera.initialize(camera_id)
    print(f"[POST /api/set_camera] Success. camera.camera_id is now {camera.camera_id}")
    return jsonify({"status": "success", "camera_id": camera_id})
  except Exception as e:
    print(f"[POST /api/set_camera] Error: {e}")
    return jsonify({"status": "error", "message": str(e)}), 400
  

@app.route("/output/video/<path:filename>")
def serve_output_video(filename):
  """output/videoフォルダの静的ファイル（録画動画）を配信"""
  return send_from_directory(VIDEO_DIR, filename)


@app.route("/output/thumbnail/<path:filename>")
def serve_output_thumbnail(filename):
  """output/thumbnailフォルダの静的ファイル（サムネイル画像）を配信"""
  return send_from_directory(THUMB_DIR, filename)


@app.route("/api/get_snapshot", methods=["POST"])
def get_snapshot():
  """指定日時（yyyyMMdd_HHMMSS、分秒は00前提）のスナップショット画像を取得。存在しない場合は404"""
  data = request.get_json() or {}
  dt_str = data.get("datetime", "")
  # ディレクトリトラバーサル対策として、想定フォーマットのみ許可
  if not re.fullmatch(r"\d{8}_\d{6}", dt_str):
    return jsonify({"status": "error", "message": "invalid datetime format"}), 400
  filename = f"{dt_str}.jpg"
  filepath = os.path.join(SNAPSHOT_DIR, filename)
  if not os.path.isfile(filepath):
    return jsonify({"status": "error", "message": "not found"}), 404
  return send_from_directory(SNAPSHOT_DIR, filename)


@app.route("/api/get_snapshot_hours", methods=["POST"])
def get_snapshot_hours():
  """指定日（yyyyMMdd）に存在するスナップショットの時刻（0-23）一覧を返す"""
  data = request.get_json() or {}
  date_str = data.get("date", "")
  if not re.fullmatch(r"\d{8}", date_str):
    return jsonify({"status": "error", "message": "invalid date format"}), 400
  hours = [
    h for h in range(24)
    if os.path.isfile(os.path.join(SNAPSHOT_DIR, f"{date_str}_{h:02d}0000.jpg"))
  ]
  return jsonify({"status": "ok", "hours": hours})


@app.route("/api/get_records", methods=["POST"])
def get_records():
  """録画記録を取得"""
  data = request.get_json()
  dt_str = data.get("date", "")
  records = get_camera_records(dt_str)
  return jsonify({"records": records})


@app.route("/api/get_record_dates", methods=["POST"])
def get_record_dates_api():
  """データが存在する日付の一覧を取得"""
  data = request.get_json(silent=True) or {}
  month_str = data.get("month", "")
  dates = get_record_dates(month_str)
  return jsonify({"dates": dates})



@app.route("/api/delete_record", methods=["POST"])
def del_record():
  """録画記録を削除"""
  data = request.get_json()
  filename = data.get("filename")
  delete_record(filename)
  return jsonify({"status": "success"})


@app.route("/api/export_to_usb", methods=["POST"])
def export_to_usb():
  """指定期間のデータをUSBメモリにエクスポート（この機能はUbuntu専用）

  処理はバックグラウンドスレッドで実行し、即座にレスポンスを返す。
  進捗は /api/export_progress をポーリングして取得する。
  """
  data = request.get_json()
  date_from = data.get("date_from")  # "YYYY-MM-DD"
  date_to = data.get("date_to")      # "YYYY-MM-DD"
  if not date_from or not date_to:
    return jsonify({"status": "error", "message": "date_from と date_to は必須です"}), 400

  with export_progress_lock:
    if export_progress["status"] == "running":
      return jsonify({"status": "error", "message": "既にエクスポート処理が実行中です"}), 409
    export_progress.update({
      "status": "running", "phase_no": 0, "phase_label": "", "phase_done": 0, "phase_total": 0, "phase_percent": 0,
      "message": "", "count": 0, "snapshot_count": 0, "usb_path": "", "device": "",
    })

  thread = threading.Thread(target=_run_export_job, args=(date_from, date_to), daemon=True)
  thread.start()

  return jsonify({"status": "started"})


@app.route("/api/export_progress", methods=["GET"])
def get_export_progress():
  """USBエクスポートの進捗状態を返す（ポーリング用）"""
  with export_progress_lock:
    return jsonify(dict(export_progress))


@app.route("/api/delete_records_range", methods=["POST"])
def del_records_range():
  """指定期間の録画記録を一括削除"""
  data = request.get_json()
  date_from = data.get("date_from")
  date_to = data.get("date_to")
  if not date_from or not date_to:
    return jsonify({"status": "error", "message": "date_from, date_to is required"}), 400
  deleted_count = delete_records_by_date_range(date_from, date_to)
  return jsonify({"status": "success", "deleted_count": deleted_count})


@app.route("/api/set_running", methods=["POST"])
def set_running():
  """isRunningの状態を設定"""
  data = request.get_json()
  is_running = data.get("running")
  print(f"[POST /api/set_running] Setting is_running to {is_running}")
  config.is_running = is_running
  return jsonify({"status": "success", "is_running": is_running})


@app.route("/api/set_config", methods=["POST"])
def set_config():
  """Configの各属性を設定"""
  data = request.get_json()
  if "ready_record" in data:
    config.ready_record = data["ready_record"]
    print(f"[POST /api/set_config] ready_record = {config.ready_record}")
  if "is_manual_recording" in data:
    config.is_manual_recording = data["is_manual_recording"]
    print(f"[POST /api/set_config] is_manual_recording = {config.is_manual_recording}")
  return jsonify({"status": "success"})


@app.route("/api/shutdown", methods=["GET"])
def shutdown():
  """システムをシャットダウン（Ubuntu専用）"""
  if SYSTEM_OS != "Linux":
    return jsonify({"status": "error", "message": "Shutdown is only available on Linux/Ubuntu"}), 400

  try:
    # -n: パスワード入力を求めず、資格情報が無ければ即座にエラーにする
    # （systemdユーザーサービス等TTYが無い環境で無限にプロンプト待ちになるのを防ぐ）
    # NOPASSWD設定が無いとここで失敗するため、事前に sudoers 設定が必要
    # （setup/ubuntu 配下の手順、または ubuntu_autostart_setup.txt 参照）
    result = subprocess.run(
      ["sudo", "-n", "shutdown", "now"],
      check=True,
      capture_output=True,
      text=True,
    )
    print(f"[GET /api/shutdown] Shutdown command executed: {result.stdout}")
    return jsonify({"status": "success", "message": "Shutdown command executed"})
  except subprocess.CalledProcessError as e:
    message = (e.stderr or str(e)).strip()
    print(f"[GET /api/shutdown] Error: {message}")
    return jsonify({"status": "error", "message": message}), 500
  except Exception as e:
    print(f"[GET /api/shutdown] Unexpected error: {e}")
    return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser(description="Vendor camera server")
  parser.add_argument("--camera_id", type=int, default=None,
                      help="起動時に使用するカメラID。指定するとカメラを自動初期化し、ready_record=true（AI連動録画オン）にします。")
  args = parser.parse_args()

  # カメラIDが引数で指定されている場合は自動でカメラを初期化し、AI連動録画を有効化する
  # 起動直後はネットワークカメラ(AXIS)やUSBカメラがまだ準備できていないことがあるため、
  # 数回リトライしてから諦める（systemd自動起動時のレースコンディション対策）。
  if args.camera_id is not None:
    MAX_INIT_RETRIES = 10
    RETRY_INTERVAL_SEC = 3
    for attempt in range(1, MAX_INIT_RETRIES + 1):
      try:
        camera.initialize(args.camera_id)
        config.is_running = True
        config.ready_record = True
        print(f"[APP] Auto-start with camera_id={args.camera_id}, is_running=True, ready_record=True (attempt {attempt})")
        break
      except Exception as e:
        print(f"[APP] Failed to auto-initialize camera {args.camera_id} (attempt {attempt}/{MAX_INIT_RETRIES}): {e}", flush=True)
        if attempt < MAX_INIT_RETRIES:
          time.sleep(RETRY_INTERVAL_SEC)
        else:
          print(f"[APP] Giving up auto-initializing camera {args.camera_id} after {MAX_INIT_RETRIES} attempts.", flush=True)

  environment_thread = threading.Thread(target=_environment_logger_loop, daemon=True)
  environment_thread.start()

  led_schedule_thread = threading.Thread(target=_led_night_schedule_loop, daemon=True)
  led_schedule_thread.start()

  print(app.url_map)
  try:
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
  except (KeyboardInterrupt, SystemExit):
    pass
  except Exception as e:
    import traceback
    print(f"\n[APP] ERROR: {e}", flush=True)
    traceback.print_exc()
  finally:
    print("\n[APP] Shutting down...", flush=True)
    stop_flag.set()
    os._exit(0)