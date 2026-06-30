import numpy as np
import cv2
import time
import os
import logging
import warnings
import sys

# ライブラリの標準出力を強制的に抑制
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '4'
os.environ['GLOG_minloglevel'] = '3'
os.environ['GLOG_logtostderr'] = '0'
warnings.filterwarnings('ignore')

import mediapipe as mp
from mediapipe.tasks.python import vision
import tensorflow as tf
from absl import logging as absl_logging

# abslロガーを寻默化
absl_logging.set_verbosity(absl_logging.ERROR)
absl_logging.get_absl_handler().python_handler.stream = open(os.devnull, 'w')

# TensorFlow の全てのロガーを ERROR 以上に設定
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('tensorflow.python').setLevel(logging.ERROR)
logging.getLogger('tensorflow.python.util').setLevel(logging.ERROR)
logging.getLogger('mediapipe').setLevel(logging.ERROR)
tf.get_logger().setLevel(logging.ERROR)

try:
  import tensorflow.compat.v1 as tf_v1
  tf_v1.logging.set_verbosity(tf_v1.logging.ERROR)
except:
  pass


class PoseEstimator:
  def __init__(self):
    # スクリプトのディレクトリを基準にモデルパスを設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_asset_path = os.path.join(script_dir, "models", "pose_landmarker_lite.task")
    baseoptions = mp.tasks.BaseOptions(model_asset_path=model_asset_path)
    running_mode = vision.RunningMode.LIVE_STREAM
    options = vision.PoseLandmarkerOptions(
      base_options = baseoptions,
      output_segmentation_masks = False,        # セグメンテーションマスクの出力を無効化
      num_poses = 1,                            # 検出人数
      running_mode = running_mode,
      result_callback = self.on_result_callback
    )
    # モデルロード中のC++レベル警告をOSレベルで抑制
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    stderr_fd = os.dup(2)
    os.dup2(devnull_fd, 2)
    os.close(devnull_fd)
    try:
      self.landmarker = vision.PoseLandmarker.create_from_options(options)
    finally:
      os.dup2(stderr_fd, 2)
      os.close(stderr_fd)
    
    #LIVE_STREAMモードに必要な、最新の検出結果
    self.latest_result = None
    self.result_available = False
    
    # 骨格描画用接続情報
    self.pose_parts = {
      "left_arm":  [11,13,15,17,19,15,21],
      "right_arm":  [12,14,16,18,20,16,22],
      "upper_body":  [11,12,24,23,11],
      # "left_leg": [23,25,27,29,31],
      # "right_leg": [24,26,28,30,32]
    }
    
    self.face_max_aspect_ratio = 3.0  # 顔の最大アスペクト比（高さ/幅）
    self.face_min_aspect_ratio = 0.5  # 顔の最小アスペクト比（高さ/幅）
    
  # LIVE_STREAMモードで必要なコールバック関数（非同期）
  def on_result_callback(self, result, output_image, timestamp_ms):
    self.latest_result = result
    self.result_available = True

  # メインから毎フレーム呼ばれる関数
  def process_frame(self, image):
    rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int(time.time() * 1000)
    self.landmarker.detect_async(mp_image, timestamp_ms)

  # 終了
  def close(self):
    self.landmarker.close()

  # 顔のROIを骨格推定から算出する
  def get_face_roi(self, pose_landmarks):
    lm_nose = pose_landmarks[0]         # 鼻
    lm_l_shoulder = pose_landmarks[11]  # 左肩
    lm_r_shoulder = pose_landmarks[12]  # 右肩
    if (lm_nose.visibility > 0.5 and 
        lm_l_shoulder.visibility > 0.5 and 
        lm_r_shoulder.visibility > 0.5):
      x_min = min(lm_l_shoulder.x, lm_r_shoulder.x)
      x_max = max(lm_l_shoulder.x, lm_r_shoulder.x)
      y_max = max(lm_l_shoulder.y, lm_r_shoulder.y)
      y_min = 2 * lm_nose.y - y_max
      return (x_min, y_min, x_max, y_max)
    else:
      return None

  # 骨格描画関数
  def draw_landmarks(self, image):
    """ 骨格ランドマークを描画し、顔のROIを返す
    Args:
      image: OpenCVのBGR画像
    Returns:
      annotated_image: 骨格と顔のROIが描画された画像
      face_roi: 顔のROI (x1, y1, x2, y2) または None
    """ 
    
    # 検出準備ができていない場合はそのまま返す
    if self.latest_result is None or not self.result_available:
      return image, None

    # 検出結果が0人の場合はそのまま返す
    if len(self.latest_result.pose_landmarks) == 0:
      return image, None

    annotated_image = image.copy()
    h, w, _ = annotated_image.shape

    pose_landmarks = self.latest_result.pose_landmarks[0]

    # 人物サイズフィルタ: 胴体の高さが閾値未満なら無視する
    threshold_height = 0.1  # 画面高さに対する比率
    lm_l_shoulder = pose_landmarks[11]
    lm_r_shoulder = pose_landmarks[12]
    lm_l_hip      = pose_landmarks[23]
    lm_r_hip      = pose_landmarks[24]
    torso_height = (lm_l_hip.y + lm_r_hip.y - lm_l_shoulder.y - lm_r_shoulder.y) / 2
    # print(f"torsoheight: {torso_height:.3f}, threshold: {threshold_height:.3f}, {torso_height < threshold_height}")
    if torso_height < threshold_height:
      return image, None

    coords = np.array([[lm.x, lm.y] for lm in pose_landmarks])
    pixel_points = (coords * np.array([w, h])).astype(int)

    # 部位ごとに線を描画
    for idx_list in self.pose_parts.values():
      for i in range(len(idx_list) - 1):
        pt1 = tuple(pixel_points[idx_list[i]])
        pt2 = tuple(pixel_points[idx_list[i + 1]])
        cv2.line(annotated_image, pt1, pt2, (255, 0, 0), 2)

    # 顔の範囲を取得
    face_roi = self.get_face_roi(pose_landmarks)
    if face_roi is None:
      return annotated_image, face_roi
    
    x_min, y_min, x_max, y_max = face_roi
    if (x_max - x_min) < 0.05:                            # 肩幅が小さすぎる場合は顔とみなさない:
      face_roi = None
      return annotated_image, face_roi

    aspect_ratio = (y_max - y_min) / (x_max - x_min)      # 顔のアスペクト比
    if aspect_ratio < self.face_min_aspect_ratio or aspect_ratio > self.face_max_aspect_ratio:
      face_roi = None
      return annotated_image, face_roi

    x1, y1, x2, y2 = int(x_min * w), int(y_min * h), int(x_max * w), int(y_max * h)
    cv2.rectangle(annotated_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
    face_roi = (x1, y1, x2, y2)
    return annotated_image, face_roi


class FaceMosaic:
  """フレーム全体から複数の顔を検出し、各顔にモザイクをかける。
  軽量なBlazeFace(short-range)を同期(IMAGEモード)で使用する。
  """
  def __init__(self, min_confidence=0.5, detect_scale=0.5, padding=0.15, mosaic_scale=0.08):
    """
    Args:
      min_confidence: 顔検出の最小信頼度
      detect_scale:   検出時の縮小率(小さいほど軽い)。検出後に元座標へ戻す
      padding:        顔ボックスの拡張率(プライバシー保護のため少し広めに隠す)
      mosaic_scale:   モザイクの粗さ(小さいほど粗い)
    """
    self.detect_scale = detect_scale
    self.padding = padding
    self.mosaic_scale = mosaic_scale

    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_asset_path = os.path.join(script_dir, "models", "blaze_face_short_range.tflite")
    base_options = mp.tasks.BaseOptions(model_asset_path=model_asset_path)
    options = vision.FaceDetectorOptions(
      base_options = base_options,
      running_mode = vision.RunningMode.IMAGE,    # 同期検出(その場で結果取得)
      min_detection_confidence = min_confidence,
    )
    # モデルロード中のC++レベル警告をOSレベルで抑制
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    stderr_fd = os.dup(2)
    os.dup2(devnull_fd, 2)
    os.close(devnull_fd)
    try:
      self.detector = vision.FaceDetector.create_from_options(options)
    finally:
      os.dup2(stderr_fd, 2)
      os.close(stderr_fd)

  def detect(self, image):
    """フレーム全体から顔のバウンディングボックス一覧を返す
    Returns:
      list[(x1, y1, x2, y2)] 元画像座標系の顔ボックス
    """
    h, w, _ = image.shape

    # 検出は縮小フレームで行い負荷を下げる
    if self.detect_scale != 1.0:
      proc = cv2.resize(image, (0, 0), fx=self.detect_scale, fy=self.detect_scale)
    else:
      proc = image
    inv = 1.0 / self.detect_scale

    rgb = cv2.cvtColor(proc, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = self.detector.detect(mp_image)

    boxes = []
    for det in result.detections:
      bbox = det.bounding_box
      # 縮小座標 → 元座標へ戻す
      bx = bbox.origin_x * inv
      by = bbox.origin_y * inv
      bw = bbox.width * inv
      bh = bbox.height * inv
      # プライバシー保護のためボックスを少し拡張
      pad_x = bw * self.padding
      pad_y = bh * self.padding
      x1 = max(0, int(bx - pad_x))
      y1 = max(0, int(by - pad_y))
      x2 = min(w, int(bx + bw + pad_x))
      y2 = min(h, int(by + bh + pad_y))
      if x2 > x1 and y2 > y1:
        boxes.append((x1, y1, x2, y2))
    return boxes

  def apply(self, image, boxes=None):
    """検出した各顔にモザイクをかける(画像を破壊的に変更)
    Args:
      image: OpenCVのBGR画像
      boxes: 事前に検出済みのボックス一覧。Noneなら内部で検出する
    Returns:
      モザイク適用後の画像(同一オブジェクト)
    """
    if boxes is None:
      boxes = self.detect(image)
    for (x1, y1, x2, y2) in boxes:
      roi = image[y1:y2, x1:x2]
      fh, fw = roi.shape[:2]
      if fh == 0 or fw == 0:
        continue
      small_w = max(1, int(fw * self.mosaic_scale))
      small_h = max(1, int(fh * self.mosaic_scale))
      small = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
      image[y1:y2, x1:x2] = cv2.resize(small, (fw, fh), interpolation=cv2.INTER_NEAREST)
    return image

  def close(self):
    self.detector.close()


def main():
  cap = cv2.VideoCapture(0)
  cap.set(cv2.CAP_PROP_FPS, 30)  # フレームレートを30FPSに設定
  estimator = PoseEstimator()
  
  while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
      break

    estimator.process_frame(frame)
    frame, face_roi = estimator.draw_landmarks(frame)

    cv2.imshow('Camera', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
      break
    
  cap.release()
  cv2.destroyAllWindows()

if __name__ == "__main__":
  main()

