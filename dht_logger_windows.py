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


def resolve_ports():
    """Pico らしき COM ポートの候補を列挙して返す。

    SERIAL_PORT が "auto" 以外なら、そのポートのみを返す。

    Pico は HID キーボード + CDC シリアルの複合デバイスとして動作するため、
    COM ポートが 2 つ生成される（片方は MicroPython の REPL、もう片方が
    DHT データ用）。どちらの COM 番号になるかは接続状況で入れ替わりうるので、
    番号を固定せず候補をすべて返し、呼び出し側で実際に READ に応答した
    ポートを採用する。
    """
    if SERIAL_PORT.lower() != "auto":
        return [SERIAL_PORT]

    candidates = [
        p.device for p in list_ports.comports()
        # Raspberry Pi Pico の VID は 0x2E8A
        if (p.vid == 0x2E8A) or ("Pico" in (p.description or ""))
    ]
    if candidates:
        return candidates

    # 見つからなければ全 COM ポートを候補にする
    return [p.device for p in list_ports.comports()]


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


def _read_from_port(port):
    """指定ポートに READ を送り (temperature, humidity) を返す。

    DHT データ用ポートなら "T=..,H=.." を返すので解析して数値を返す。
    REPL 側など想定外のポート・応答の場合は None を返し、呼び出し側で
    次の候補ポートを試せるようにする。
    """
    try:
        with serial.Serial(port, 115200, timeout=READ_TIMEOUT) as ser:
            ser.reset_input_buffer()
            ser.write(b"READ\n")
            line = ser.readline().decode(errors="ignore").strip()
    except serial.SerialException as e:
        print(f"[dht_logger] Serial error on {port}: {e}", flush=True)
        return None

    if line.startswith("T=") and "H=" in line:
        try:
            parts = dict(p.split("=") for p in line.split(","))
            t = round(float(parts["T"]), 1)
            h = round(float(parts["H"]), 1)
            return t, h
        except (ValueError, KeyError):
            print(f"[dht_logger] Parse error on {port}: {line!r}", flush=True)
    else:
        # REPL ポートや未応答（空行）の場合はここに来る
        print(f"[dht_logger] No valid DHT response on {port}: {line!r}", flush=True)

    return None


def read_sensor(ports):
    """候補ポートを順に試し、READ に応答したポートの測定値を返す。

    COM 番号が入れ替わっても、実際に READ へ正しく応答したポートを DHT
    データ用として採用するため、番号に依存しない。すべて失敗時は None。
    """
    for attempt in range(RETRIES):
        for port in ports:
            result = _read_from_port(port)
            if result is not None:
                print(f"[dht_logger] Using port: {port}", flush=True)
                return result
        time.sleep(1)

    return None


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    ports = resolve_ports()
    print(f"[dht_logger] Candidate ports: {ports}", flush=True)

    result = read_sensor(ports)
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
