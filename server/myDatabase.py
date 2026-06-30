import os
import sqlite3

# 定数

base_dir = os.path.dirname(__file__)
output_path = os.path.join(base_dir, '..', 'output')
OUTPUT_DIR = os.path.abspath(output_path)
TEMP_PATH = os.path.join(OUTPUT_DIR, '_recording_temp.mp4')
DB_PATH = os.path.join(OUTPUT_DIR, 'dagashi_camera.sqlite')
THUMB_SCALE = 0.5


def insert_camera_row(dt_str, filename_base, duration_sec, gender, age):
    """DBに録画記録を登録"""
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.cursor()
        sql = "INSERT INTO camera(datetime, filename, duration, gender, age) VALUES (?, ?, ?, ?, ?)"
        cur.execute(sql, (dt_str, filename_base, duration_sec, gender, age))
        con.commit()
    finally:
        con.close()

def get_camera_records(dt_str = ""):
    """DBから録画記録を取得"""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row  # レコードを辞書のように扱う
    try:
        cur = con.cursor()
        if dt_str:
          sql = "select * from camera where datetime LIKE ?"
          cur.execute(sql, (f'{dt_str}%',))
        else:
          sql = "select * from camera"
          cur.execute(sql)
        records = cur.fetchall()
        return [dict(row) for row in records]  # 辞書のリストに変換
    finally:
        con.close()

def delete_record(filename):
  """DBから録画記録を削除"""
  con = sqlite3.connect(DB_PATH)
  try:
    cur = con.cursor()
    sql = "DELETE FROM camera WHERE filename = ?"
    cur.execute(sql, (filename,))
    con.commit()
  finally:
    con.close()
  # さらに、動画ファイルとサムネイルも削除
  video_path = os.path.join(OUTPUT_DIR, f"{filename}.mp4")
  thumb_path = os.path.join(OUTPUT_DIR, f"{filename}.jpg")
  if os.path.exists(video_path):
    os.remove(video_path)
  else:
    print(f"Warning: Video file {video_path} not found for deletion.")
  if os.path.exists(thumb_path):
    os.remove(thumb_path)
  else:
    print(f"Warning: Thumbnail file {thumb_path} not found for deletion.")
