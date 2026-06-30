#!/usr/bin/env python3
# =============================================================================
# DHT 温湿度ロガー (Windows 版)
# -----------------------------------------------------------------------------
# COM ポート経由で Raspberry Pi Pico に "READ" を送り、温湿度を受け取って
# SQLite に 1 行記録します。1 回実行で 1 測定の「ワンショット」型です。
# 実行タイミング（毎時 :00 :10 :20 ...）は Windows タスクスケジューラで制御します。
#
# テーブル sensor:
#   datetime    TEXT  "YYYY-MM-DD HH:MM:SS"
#   temperature REAL  温度（小数第1位）
#   humidity    REAL  湿度（小数第1位）
#
# 依存: pip install pyserial
# =============================================================================

import os
import sqlite3
import time
from datetime import datetime

import serial
from serial.tools import list_ports

# ---- 設定（環境変数で上書き可能）----
# ポートは "auto" で Pico を自動検出、もしくは "COM3" のように明示指定
SERIAL_PORT = os.environ.get("DHT_SERIAL_PORT", "auto")
DB_PATH = os.environ.get(
    "DHT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "sensor.db"),
)
READ_TIMEOUT = 5.0   # 1 回の応答待ち秒数（DHT 測定に数秒かかる）
RETRIES = 3          # 取得失敗時のリトライ回数
# -------------------------------------


def resolve_port():
    """SERIAL_PORT が "auto" なら Pico らしき COM ポートを探して返す。"""
    if SERIAL_PORT.lower() != "auto":
        return SERIAL_PORT
    for p in list_ports.comports():
        # Raspberry Pi Pico の VID は 0x2E8A
        if (p.vid == 0x2E8A) or ("Pico" in (p.description or "")):
            return p.device
    # 見つからなければ最初の COM ポート
    ports = list(list_ports.comports())
    return ports[0].device if ports else "COM3"


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


def read_sensor(port):
    """Pico に READ を送り (temperature, humidity) を返す。失敗時は None。"""
    for attempt in range(RETRIES):
        try:
            with serial.Serial(port, 115200, timeout=READ_TIMEOUT) as ser:
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

    port = resolve_port()
    print(f"[dht_logger] Using port: {port}", flush=True)

    result = read_sensor(port)
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
