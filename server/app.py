isMediaPipeAvailable = True

import os
import threading
import platform
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import cv2
import time
from myCamera import Camera
from myDatabase import insert_camera_row, get_camera_records, delete_record, delete_records_by_date_range, get_record_dates, VIDEO_DIR, THUMB_DIR
from myMemory import get_disk_and_folder_usage, export_data_to_usb

# グローバル終了フラグ
stop_flag = threading.Event()

# OS情報を起動時に一度だけ取得
SYSTEM_OS = platform.system()

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
  """指定期間のデータをUSBメモリにエクスポート（この機能はUbuntu専用）"""
  data = request.get_json()
  date_from = data.get("date_from")  # "YYYY-MM-DD"
  date_to = data.get("date_to")      # "YYYY-MM-DD"
  if not date_from or not date_to:
    return jsonify({"status": "error", "message": "date_from と date_to は必須です"}), 400

  # myMemory の関数を呼び出してエクスポート処理を実行
  result = export_data_to_usb(date_from, date_to)
  
  if result.get("status") == "error":
    return jsonify(result), 500
  
  return jsonify(result)


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


if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser(description="Vendor camera server")
  parser.add_argument("--camera_id", type=int, default=None,
                      help="起動時に使用するカメラID。指定するとカメラを自動初期化し、ready_record=true（AI連動録画オン）にします。")
  args = parser.parse_args()

  # カメラIDが引数で指定されている場合は自動でカメラを初期化し、AI連動録画を有効化する
  if args.camera_id is not None:
    try:
      camera.initialize(args.camera_id)
      config.is_running = True
      config.ready_record = True
      print(f"[APP] Auto-start with camera_id={args.camera_id}, is_running=True, ready_record=True")
    except Exception as e:
      print(f"[APP] Failed to auto-initialize camera {args.camera_id}: {e}", flush=True)

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