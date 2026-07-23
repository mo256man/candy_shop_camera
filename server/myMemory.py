import shutil
import os
from pathlib import Path

def _check_writable(mount_point):
  """
  指定したマウントポイントに実際に書き込み可能かどうかをテストする。
  os.access() は root 権限下や一部のファイルシステムで不正確になる場合があるため、
  一時ファイルの作成・削除を試みて実際の書き込み可否を判定する。

  Args:
    mount_point: チェック対象のマウントポイント（例: /media/usb0）

  Returns:
    (bool, str) : (書き込み可能なら True, エラーがあればそのメッセージ)
  """
  import tempfile

  if not os.path.isdir(mount_point):
    return False, "マウントポイントが存在しません"

  try:
    with tempfile.NamedTemporaryFile(dir=mount_point, prefix='.write_test_', delete=True):
      pass
    return True, ""
  except (OSError, PermissionError) as e:
    return False, str(e)


def export_data_to_usb(date_from, date_to):
  """
  指定期間のデータをUSBメモリ・メモリーカードにエクスポート（Ubuntu専用）
  
  USB メモリまたはメモリーカードリーダー経由のメディアをサポート。
  複数マウント時は最初に見つかったものを使用します。
  
  Args:
    date_from: 開始日付 (YYYY-MM-DD)
    date_to: 終了日付 (YYYY-MM-DD)
    
  Returns:
    辞書 {"status": "success" or "error", "message": str, "count": int, "usb_path": str}
  """
  from myDatabase import DB_PATH, VIDEO_DIR, THUMB_DIR, get_camera_records
  
  # USBドライブのマウントポイントを探す（/proc/mounts から /dev/sd* を検索）
  usb_mounts = []
  try:
    with open('/proc/mounts', 'r') as f:
      for line in f:
        parts = line.split()
        if len(parts) < 2:
          continue
        device, mount_point = parts[0], parts[1]
        
        # USB デバイス（USB メモリ、メモリーカードリーダー等）の判定
        # /dev/sdX または /dev/sdXN（パーティション）形式のデバイス
        # マウント先が /media/ または /run/media/ 以下
        if device.startswith('/dev/sd') and (
          mount_point.startswith('/media/') or mount_point.startswith('/run/media/')
        ):
          # パーティション情報をスキップ（例：/dev/sdb1p2）し、
          # 最初のパーティション（/dev/sdb1）のマウント先のみ使用
          # これによってメモリーカードリーダー内の複数スロットに対応
          is_partition = any(c.isdigit() for c in device.split('/')[-1])
          if is_partition:
            usb_mounts.append({
              'device': device,
              'mount_point': mount_point
            })
  except Exception as e:
    return {"status": "error", "message": f"マウント情報の読み取りに失敗しました: {str(e)}"}

  if not usb_mounts:
    return {"status": "error", "message": "USBメモリが見つかりません。USBまたはメモリーカードを挿入してください。"}

  # 複数見つかった場合は最初のものを使用
  selected = usb_mounts[0]
  usb_path = selected['mount_point']
  device_name = selected['device']

  # 書き込み可能かどうかをチェック（読み取り専用マウントやロック付きSDカード対策）
  # os.access() は root 権限下では不正確な場合があるため、実際に書き込みテストを行う
  write_ok, write_err = _check_writable(usb_path)
  if not write_ok:
    return {"status": "error", "message": f"メディアへの書き込みができません（{device_name}）: {write_err}"}

  # USB上にフォルダを作成
  usb_output_dir = os.path.join(usb_path, 'output')
  usb_thumb_dir = os.path.join(usb_output_dir, 'thumbnail')
  usb_video_dir = os.path.join(usb_output_dir, 'video')
  try:
    os.makedirs(usb_thumb_dir, exist_ok=True)
    os.makedirs(usb_video_dir, exist_ok=True)
  except Exception as e:
    return {"status": "error", "message": f"USBへのフォルダ作成に失敗しました: {str(e)}"}

  # camera.sqlite をコピー（期間に関わらず全件）
  try:
    shutil.copy2(DB_PATH, os.path.join(usb_output_dir, 'camera.sqlite'))
  except Exception as e:
    return {"status": "error", "message": f"DBのコピーに失敗しました: {str(e)}"}

  # 指定期間のレコードを取得してファイルをコピー
  all_records = get_camera_records()
  target_records = [
    r for r in all_records
    if date_from <= r['datetime'][:10] <= date_to
  ]

  for record in target_records:
    filename_base = record['filename']

    thumb_src = os.path.join(THUMB_DIR, f"{filename_base}.jpg")
    if os.path.exists(thumb_src):
      try:
        shutil.copy2(thumb_src, os.path.join(usb_thumb_dir, f"{filename_base}.jpg"))
      except Exception:
        pass

    video_src = os.path.join(VIDEO_DIR, f"{filename_base}.mp4")
    if os.path.exists(video_src):
      try:
        shutil.copy2(video_src, os.path.join(usb_video_dir, f"{filename_base}.mp4"))
      except Exception:
        pass

  return {
    "status": "success",
    "count": len(target_records),
    "usb_path": usb_path,
    "device": device_name,
  }


def get_disk_and_folder_usage(os_name):
    def get_folder_size(path):
        total = 0
        for p in Path(path).rglob('*'):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except (OSError, PermissionError):
                    pass
        return total

    def to_gb(n):
        return n / (1024 ** 3)

    script_dir  = Path(__file__).resolve().parent
    project_dir = script_dir.parent
    output_dir  = project_dir

    if os_name == 'Windows':
        drive = Path(project_dir.drive + '\\')
    elif os_name == 'Linux':
        drive = Path('/')
    else:
        raise RuntimeError(f'unsupported OS: {os_name}')

    usage = shutil.disk_usage(drive)
    used = usage.total - usage.free
    folder_used = get_folder_size(output_dir)

    return {
        'os'          : os_name,
        'drive'       : str(drive),
        'total_gb'    : to_gb(usage.total),
        'free_gb'     : to_gb(usage.free),
        'used_gb'     : to_gb(used),
        'folder'      : str(output_dir),
        'folder_gb'   : to_gb(folder_used),
    }


if __name__ == '__main__':
    import platform
    os_name = platform.system()
    info = get_disk_and_folder_usage(os_name)
    print(f'OS            : {info["os"]}')
    print(f'対象ドライブ  : {info["drive"]}')
    print(f'全体容量      : {info["total_gb"]:.2f} GB')
    print(f'残容量        : {info["free_gb"]:.2f} GB')
    print(f'使用容量      : {info["used_gb"]:.2f} GB')
    print(f'対象フォルダ  : {info["folder"]}')
    print(f'フォルダ使用量: {info["folder_gb"]:.2f} GB')