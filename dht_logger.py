#!/usr/bin/env python3
# =============================================================================
# DHT 温湿度ロガー (PC/Ubuntu 側)
# -----------------------------------------------------------------------------
# USB シリアル経由で Raspberry Pi Pico に "READ" を送り、温湿度を受け取って
# SQLite に 1 行記録します。1 回実行で 1 測定の「ワンショット」型です。
# 実行タイミング（毎時 :00 :10 :20 ...）は systemd timer で制御します。
#
# テーブル sensor:
#   datetime    TEXT  "YYYY-MM-DD HH:MM:SS"
#   temperature REAL  温度（小数第1位）
#   humidity    REAL  湿度（小数第1位）
#
# 依存: pip install pyserial  （または sudo apt install python3-serial）
# =============================================================================

import os
import sqlite3
import time
from datetime import datetime

import serial

# ---- 設定（環境変数で上書き可能）----
SERIAL_PORT = os.environ.get("DHT_SERIAL_PORT", "/dev/ttyACM0")
DB_PATH = os.environ.get(
    "DHT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "sensor.db"),
)
READ_TIMEOUT = 5.0   # 1 回の応答待ち秒数（DHT 測定に数秒かかる）
RETRIES = 3          # 取得失敗時のリトライ回数
# -------------------------------------


def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sensor (
            datetime    TEXT,
            temperature REAL,
            humidity    REAL
        )
        """
    )
    conn.commit()


def read_sensor():
    """Pico に READ を送り (temperature, humidity) を返す。失敗時は None。"""
    for attempt in range(RETRIES):
        try:
            with serial.Serial(SERIAL_PORT, 115200, timeout=READ_TIMEOUT) as ser:
                ser.reset_input_buffer()
                ser.write(b"READ\n")
                line = ser.readline().decode(errors="ignore").strip()
        except serial.SerialException as e:
            print(f"[dht_logger] Serial error: {e}", flush=True)
            time.sleep(1)
            continue

        if line.startswith("T=") and "H=" in line:
            try:
                parts = dict(p.split("=") for p in line.split(","))
                t = round(float(parts["T"]), 1)
                h = round(float(parts["H"]), 1)
                return t, h
            except (ValueError, KeyError):
                print(f"[dht_logger] Parse error: {line!r}", flush=True)
        else:
            print(f"[dht_logger] Unexpected response: {line!r}", flush=True)

        time.sleep(1)

    return None


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    result = read_sensor()
    if result is None:
        print("[dht_logger] Failed to read sensor. Nothing recorded.", flush=True)
        return 1

    temperature, humidity = result
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        conn.execute(
            "INSERT INTO sensor (datetime, temperature, humidity) VALUES (?, ?, ?)",
            (now, temperature, humidity),
        )
        conn.commit()
    finally:
        conn.close()

    print(f"[dht_logger] Recorded: {now} T={temperature} H={humidity}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
