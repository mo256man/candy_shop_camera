import cv2
import os
import queue
import subprocess
import threading
import time
import platform
from urllib.parse import quote
from datetime import datetime
# from myDeepFace import analyze_face
from myInsightFace import analyze_face
from myVideo import get_video_duration_seconds, generate_thumbnail, save_thumbnail_from_frame
from myDatabase import insert_camera_row, OUTPUT_DIR, VIDEO_DIR, THUMB_DIR, TEMP_PATH, THUMB_SCALE

# スナップショット保存先（毎時0分に1枚保存）
SNAPSHOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'snapshot'))

# MediaPipe処理用スケール（小さいほど軽い）
MEDIAPIPE_SCALE = 0.5
# InsightFace呼び出し間隔（秒）
DEEPFACE_INTERVAL = 1.0

# AXISカメラのRTSP通信設定
username = "root"
password = "password"
pwd_enc = quote(password, safe="")

if platform.system() == "Windows":
  local_backend = cv2.CAP_DSHOW
else:
  local_backend = None

CAMERAS = [
  {
    "source": 0,
    "rotate": None,
    "backend": local_backend,
    "width": 1280,
    "height": 720,
  },
  {
    "source": f"rtsp://{username}:{pwd_enc}@192.168.4.245/axis-media/media.amp",
    "backend": cv2.CAP_FFMPEG,
    "rotate": None,
    "width": 1280,
    "height": 720,
  }
]


class Camera:
  def __init__(self, config):
    self.camera_id = None
    self.cap =None
    self.source = None
    self.backend = None
    self.rotate = None
    self.width = None
    self.height = None
    self.config = config
    # 録画中に検出した最大面積の顔と、その年齢・性別を保持する
    # （平均や多数決ではなく「最も大きく写った顔」を採用するため、録画タイミングに依存しない）
    self.max_face_area = 0
    self.result_age = None
    self.result_gender = None
    # 最大面積の顔が写ったフレーム（カメラサイズのまま保持し、録画終了時に縮小してサムネイル化）
    self.best_thumb_frame = None

    self.is_ai_available = config.is_ai_available
    if self.is_ai_available:
      from myMediaPipe import PoseEstimator
      self.estimator = PoseEstimator()
    else:
      self.estimator = None
    self.is_found = False
    self.last_found_time = None
    self.first_found_time = None  # 検知開始時刻
    self.min_detection_duration = 0.5  # 最小検知時間（秒）。これ未満なら幻として無視
    self.valid_detection = False  # 現在の検知セッションが有効か
    self.last_deepface_time = 0.0
    self.last_snapshot_hour = -1  # 最後にスナップショットを保存した時刻（hour）
    
    # 一定FPSで走らせるための設定
    self.target_fps = 15.0
    self.frame_duration = 1.0 / self.target_fps
    
    # スレッド管理
    self.capture_thread = None
    self.deepface_thread = None
    self.deepface_queue = queue.Queue(maxsize=1)  # 常に最新ROIだけ保持
    self.stop_event = threading.Event()
    self.frame_lock = threading.Lock()
    self.current_frame = None
  
  def initialize(self, camera_id):
    self.stop()                       # 既存スレッドを停止
    self.camera_id = camera_id
    
    # カメラ定義の前に確実に前の設定をクリアする
    if self.cap is not None:
      self.cap.release()
      self.cap = None

    # estimatorを再生成
    if self.is_ai_available:
      from myMediaPipe import PoseEstimator
      self.estimator = PoseEstimator()
    
    # 0番はカメラ無し
    if camera_id == 0:
      return
  
    # 1番以上はカメラを設定
    idx = camera_id - 1
    self.source = CAMERAS[idx]["source"]
    self.backend = CAMERAS[idx]["backend"]
    self.rotate = CAMERAS[idx]["rotate"]
    self.width = CAMERAS[idx]["width"]
    self.height = CAMERAS[idx]["height"]
    try:
      if self.backend is not None:
        self.cap = cv2.VideoCapture(self.source, self.backend)
      else:
        self.cap = cv2.VideoCapture(self.source)
      if not self.cap.isOpened():
        raise Exception("Failed to open camera")
      self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
      self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
      self.start()
    except Exception as e:
      print(f"Error initializing camera {camera_id}: {e}")
      self.cap = None
      raise

  def start(self):
    if self.cap is None or not self.cap.isOpened():
      return
    self.stop_event.clear()
    # キューをリセット
    while not self.deepface_queue.empty():
      try:
        self.deepface_queue.get_nowait()
      except queue.Empty:
        break
    self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
    self.capture_thread.start()
    if self.is_ai_available:
      self.deepface_thread = threading.Thread(target=self._deepface_loop, daemon=True)
      self.deepface_thread.start()

  def stop(self):
    # スレッド停止イベント
    self.stop_event.set()

    # スレッド停止を先に待つ（cap.read()が完了してからreleaseする）
    if self.capture_thread is not None:
      self.capture_thread.join(timeout=3.0)
      self.capture_thread = None
    # InsightFaceスレッドはブロッキング処理中の可能性があるため長めに待つ
    if self.deepface_thread is not None:
      self.deepface_thread.join(timeout=10.0)
      self.deepface_thread = None
    while self.frame_lock.locked():
      self.current_frame = None

    # AI処理リソースの解放
    if self.is_ai_available and self.estimator is not None:
      try:
        self.estimator.close()
      except Exception as e:
        print(f"[Camera] Error closing estimator: {e}", flush=True)

    # スレッド停止後にカメラを解放する
    if self.cap is not None:
      self.cap.release()
      self.cap = None

  def _capture_loop(self):
    while not self.stop_event.is_set():
      try:
        loop_start_time = time.perf_counter()

        # フレーム取得その他
        ret, frame = self._get_and_process_frame()
        if not ret:
          continue

        # AI処理
        if self.is_ai_available:
          # MediaPipeには縮小フレームを渡す（処理を軽くするため）
          small = cv2.resize(frame, (0, 0), fx=MEDIAPIPE_SCALE, fy=MEDIAPIPE_SCALE)
          self.estimator.process_frame(small)
          # draw_landmarksには元のframeを渡す（正規化座標なので元サイズのROIが得られる）
          frame, face_roi = self.estimator.draw_landmarks(frame)
          send_to_insightface = False
          if face_roi is not None:
            self.is_found = True
            x1, y1, x2, y2 = face_roi
            # InsightFace呼び出しは間隔制限付き。クリーンな顔ROIを切り出す
            now_t = time.perf_counter()
            if now_t - self.last_deepface_time >= DEEPFACE_INTERVAL:
              roi = frame[y1:y2, x1:x2].copy()
              area = (x2 - x1) * (y2 - y1)
              send_to_insightface = True

            # テキストは現在採用している（最大面積の）結果で描画
            cur_age = self.result_age
            cur_gender = self.result_gender
            if cur_age is not None and cur_gender is not None:
              cv2.putText(frame, f"Age: {round(cur_age, 1)},  Gender: {cur_gender}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
          else:
            self.is_found = False

          # InsightFaceスレッドへ渡す（間隔制限付き・ノンブロッキング）。
          # サムネイル候補としてフレームを同梱し、最大面積の顔が
          # 推論できたタイミングでサムネイルも更新する
          if send_to_insightface:
            try:
              self.deepface_queue.put_nowait((roi, area, frame.copy()))
              self.last_deepface_time = now_t
            except queue.Full:
              pass  # InsightFace処理中 → スキップ
        # print("人検知", self.is_found, flush=True)

        # 録画処理
        self._handle_recording(frame)

        # 次のフレーム取得まで待機
        next_frame_time = loop_start_time + self.frame_duration
        sleep_time = next_frame_time - time.perf_counter()
        if sleep_time > 0:
          time.sleep(sleep_time)

        # フレームをロック付きで保存
        with self.frame_lock:
          self.current_frame = frame.copy()
      except Exception as e:
        print(f"[Camera] Error in capture loop: {e}", flush=True)
        time.sleep(0.1)

  def _deepface_loop(self):
    """InsightFace専用スレッド：キューからROIを受け取り解析する"""
    while not self.stop_event.is_set():
      try:
        roi, area, frame = self.deepface_queue.get(timeout=0.5)
      except queue.Empty:
        continue
      ret, age, gender = analyze_face(roi)
      # これまでの最大面積より大きい顔が推論できたときだけ年齢・性別を更新する
      # 同じタイミングでサムネイル候補フレーム（カメラサイズのまま）も更新する
      if ret and area > self.max_face_area:
        self.max_face_area = area
        self.result_age = age
        self.result_gender = gender
        self.best_thumb_frame = frame

  def _get_and_process_frame(self):
    """フレーム取得、回転、時計追加"""
    if self.stop_event.is_set():
      return False, None
    if self.cap is None or not self.cap.isOpened():
      time.sleep(0.01)
      return False, None

    ret, frame = self.cap.read()
    if not ret:
      # 一時的な読み込み失敗。カメラ接続は維持したまま次のループで再試行する
      print("[Camera] cap.read() failed (ret=False)", flush=True)
      time.sleep(0.01)
      return False, None

    # 回転処理
    if self.rotate is not None:
      frame = cv2.rotate(frame, self.rotate)

    # 時計を追加
    now_dt = datetime.now()
    clock = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    cv2.rectangle(frame, (0, 0), (frame.shape[1]-1, 35), (0, 0, 0), -1)
    cv2.putText(frame, clock, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

    # 毎時0分に1枚スナップショットを保存（秒は強制的に00とする）
    if now_dt.minute == 0 and now_dt.hour != self.last_snapshot_hour:
      self.last_snapshot_hour = now_dt.hour
      snap_dt = now_dt.replace(minute=0, second=0, microsecond=0)
      snap_filename = snap_dt.strftime('%Y%m%d_%H%M%S') + '.jpg'
      snap_path = os.path.join(SNAPSHOT_DIR, snap_filename)
      os.makedirs(SNAPSHOT_DIR, exist_ok=True)
      cv2.imwrite(snap_path, frame)
      print(f"[Snapshot] Saved: {snap_path}", flush=True)

    return True, frame

  def get_frame(self):
    """現在のフレームを取得"""
    with self.frame_lock:
      if self.current_frame is not None:
        return self.current_frame.copy()
    return None

  def _handle_recording(self, frame):
    """録画状態チェックと録画フレーム書き込み"""
    now = time.perf_counter()

    # 人検知時は最終検知時刻を更新し、初回検知時刻も記録。録画中でなければ録画開始
    if self.config.ready_record and self.is_found:
      if self.first_found_time is None:
        self.first_found_time = now  # 検知開始時刻を記録
      self.last_found_time = now
      if not self.config.is_recording:
        self.config.is_recording = True

    # 人未検知が一定時間継続したら録画終了
    # さらに、検知セッション全体の長さが最小検知時間未満なら、その検知は無効（幻）と判定
    if self.config.is_recording and not self.is_found:
      if self.last_found_time is not None and now - self.last_found_time >= 2.0:
        # 検知セッション全体の長さを計算
        if self.first_found_time is not None:
          detection_duration = self.last_found_time - self.first_found_time
          self.valid_detection = detection_duration >= self.min_detection_duration
        else:
          self.valid_detection = False
        self.config.is_recording = False
        self.first_found_time = None

    # 録画状態の遷移をチェック
    current_recording = self.config.is_recording
    if current_recording and not self.config.previous_recording:
      # 録画開始
      self._start_recording()
      self.config.previous_recording = True
    elif not current_recording and self.config.previous_recording:
      # 録画終了
      self._stop_recording()
      self.config.previous_recording = False

    # 固定周期で録画フレームを書き込む
    if self.config.is_recording and self.config.record_writer and self.config.next_write_time is not None:
      while now >= self.config.next_write_time:
        out = cv2.resize(frame, (self.config.record_out_w, self.config.record_out_h))
        self.config.record_writer.write(out)
        self.config.next_write_time += self.config.tick

  def _start_recording(self):
    """録画開始"""
    if self.config.record_writer is not None:
        return
    
    # 最大面積の顔とその年齢・性別をリセットする
    # （録画ごとにリセットすることで、その録画中に最も大きく写った顔の結果だけを採用する）
    self.max_face_area = 0
    self.result_age = None
    self.result_gender = None
    self.best_thumb_frame = None
    
    # 検知セッションの有効性フラグをリセット
    self.valid_detection = False
    
    # ディレクトリ作成
    if not os.path.exists(OUTPUT_DIR):
      os.makedirs(OUTPUT_DIR)
    if not os.path.exists(VIDEO_DIR):
      os.makedirs(VIDEO_DIR)
    if not os.path.exists(THUMB_DIR):
      os.makedirs(THUMB_DIR)
    
    # 録画設定
    self.config.record_start_dt = datetime.now()
    self.config.record_fps = self.target_fps
    self.config.tick = 1.0 / self.target_fps
    
    # 回転を考慮したサイズ（90度回転の場合、幅と高さが入れ替わる）
    if self.rotate in [cv2.ROTATE_90_COUNTERCLOCKWISE, cv2.ROTATE_90_CLOCKWISE]:
      record_w = self.height
      record_h = self.width
    else:
      record_w = self.width
      record_h = self.height
    
    # VideoWriter作成用のサイズを保存
    self.config.record_out_w = int(record_w * 0.5)
    self.config.record_out_h = int(record_h * 0.5)
    
    if platform.system() == "Windows":
      fourcc = cv2.VideoWriter_fourcc(*'avc1')
    else:
      fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Linux: 後でffmpegでH.264に再エンコード
    self.config.record_writer = cv2.VideoWriter(TEMP_PATH, fourcc, self.config.record_fps, (self.config.record_out_w, self.config.record_out_h))
    
    if not self.config.record_writer.isOpened():
      print(f"[Recording] ERROR: VideoWriter failed to open. Check codec/path.", flush=True)
      self.config.record_writer = None
      return
    
    # 固定周期の基準時刻
    self.config.next_write_time = time.perf_counter()
    
    print(f"[Recording] Started at {self.config.record_start_dt.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

  def _stop_recording(self):
    """録画終了"""
    if self.config.record_writer is None:
      return
    
    # VideoWriter終了
    self.config.record_writer.release()
    self.config.record_writer = None
    
    # ファイル名
    timestamp = self.config.record_start_dt.strftime('%Y%m%d_%H%M%S')
    filename_base = timestamp
    target = os.path.join(VIDEO_DIR, f"{filename_base}.mp4")
    
    # 重複チェック
    if os.path.exists(target):
      name, ext = os.path.splitext(target)
      i = 1
      while os.path.exists(f"{name}_{i}{ext}"):
        i += 1
      filename_base = f"{filename_base}_{i}"
      target = f"{name}_{i}{ext}"
    
    # サムネイル生成（回転を考慮したサイズを使用）
    thumb_path = os.path.join(THUMB_DIR, filename_base + ".jpg")
    if self.rotate in [cv2.ROTATE_90_COUNTERCLOCKWISE, cv2.ROTATE_90_CLOCKWISE]:
      thumb_w = self.height
      thumb_h = self.width
    else:
      thumb_w = self.width
      thumb_h = self.height
    # 最大面積の顔が写ったフレーム（カメラサイズのまま保持）をサムネイル用に縮小して保存する。
    # 顔が一度も推論できなかった場合は従来どおり動画中央フレームから生成する
    if self.best_thumb_frame is not None:
      save_thumbnail_from_frame(self.best_thumb_frame, thumb_path, THUMB_SCALE, thumb_w, thumb_h)
    else:
      generate_thumbnail(TEMP_PATH, thumb_path, THUMB_SCALE, thumb_w, thumb_h)
    print(f"[Recording] Thumbnail saved: {thumb_path}", flush=True)
    
    # 動画を保存（Linuxはffmpegでmp4v→H.264に再エンコードしてブラウザ再生に対応）
    if platform.system() != "Windows":
      ret = subprocess.call(
        ["ffmpeg", "-y", "-i", TEMP_PATH, "-vcodec", "libx264", "-preset", "fast", "-movflags", "+faststart", target],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
      )
      if ret == 0:
        os.remove(TEMP_PATH)
      else:
        print(f"[Recording] WARNING: ffmpeg re-encoding failed, using mp4v.", flush=True)
        os.rename(TEMP_PATH, target)
    else:
      os.rename(TEMP_PATH, target)
    print(f"[Recording] Stopped. File saved: {target}", flush=True)
    
    # 動画の長さを取得
    duration = get_video_duration_seconds(target, self.target_fps)
    duration = round(duration, 1)
    
    # DB登録（検知セッションが有効な場合のみ）
    if self.valid_detection:
      dt_str = self.config.record_start_dt.strftime('%Y-%m-%d %H:%M:%S')
      gender = self.result_gender if self.result_gender is not None else "NA"  # 最大面積の顔の性別
      age = round(self.result_age, 1) if self.result_age is not None else 0.0  # 最大面積の顔の年齢（小数一位まで）
      insert_camera_row(dt_str, filename_base, duration, gender, age)
      print(f"[Recording] DB registered: {filename_base} ({gender}, {age})", flush=True)
    else:
      print(f"[Recording] Detection duration too short ({duration}s < {self.min_detection_duration}s). Skipped DB registration.", flush=True)
      # ファイルを削除
      if os.path.exists(target):
        os.remove(target)
      if os.path.exists(thumb_path):
        os.remove(thumb_path)
      print(f"[Recording] Files deleted (invalid detection session).", flush=True)
    
    self.config.clear_recording_state()