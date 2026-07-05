import subprocess
import cv2
import os

# 定数
VIDEO_FPS_DEFAULT = 15


def get_video_duration_seconds(path, fallback_fps):
    """動画の長さを秒単位で取得"""
    # ffprobe で duration を取得
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            s = (r.stdout or "").strip()
            if s:
                return float(s)
    except Exception:
        pass

    # フォールバック：OpenCVで概算
    cap2 = cv2.VideoCapture(path)
    try:
        fps = cap2.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = fallback_fps if fallback_fps and fallback_fps > 0 else VIDEO_FPS_DEFAULT
        frame_count = cap2.get(cv2.CAP_PROP_FRAME_COUNT)
        if frame_count and frame_count > 0 and fps and fps > 0:
            return float(frame_count) / float(fps)
    finally:
        cap2.release()

    return 0.0


def generate_thumbnail(video_path, output_path, thumb_scale, cam_w, cam_h):
    """動画の中央フレームからサムネイル生成"""
    thumb_cap = cv2.VideoCapture(video_path)
    try:
        total = int(thumb_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            return False
        thumb_cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
        ret, frame = thumb_cap.read()
        if not ret or frame is None:
            return False
    finally:
        thumb_cap.release()
    
    # リサイズして保存
    tw = int(cam_w * thumb_scale)
    th = int(cam_h * thumb_scale)
    thumb = cv2.resize(frame, (tw, th))
    cv2.imwrite(output_path, thumb)
    return True


def save_thumbnail_from_frame(frame, output_path, thumb_scale, cam_w, cam_h):
    """既に取得済みのフレーム（カメラサイズ）をサムネイル用サイズに縮小して保存"""
    if frame is None:
        return False
    tw = int(cam_w * thumb_scale)
    th = int(cam_h * thumb_scale)
    thumb = cv2.resize(frame, (tw, th))
    cv2.imwrite(output_path, thumb)
    return True
