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
import serial.tools.list_ports

# ---- 設定（環境変数で上書き可能）----
# DHT_SERIAL_PORT が未設定の場合は Raspberry Pi Pico を自動検出する
_ENV_PORT = os.environ.get("DHT_SERIAL_PORT")
DB_PATH = os.environ.get(
    "DHT_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "sensor.sqlite"),
)
READ_TIMEOUT = 5.0   # 1 回の応答待ち秒数（DHT 測定に数秒かかる）
RETRIES = 3          # 取得失敗時のリトライ回数
# -------------------------------------

# Raspberry Pi Pico（ラズピコ）の USB Vendor ID
_PICO_VID = 0x2E8A


def find_pico_ports():
    """接続中のシリアルポートから Raspberry Pi Pico の候補をすべて列挙して返す。

    環境変数 DHT_SERIAL_PORT が設定されている場合はそのポートのみを返す。

    Pico は HID キーボード + CDC シリアルの複合デバイスとして動作するため、
    ttyACM0 / ttyACM1 のように複数のシリアルポートが生成される。片方は
    MicroPython の REPL、もう片方が DHT データ用だが、どちらの番号になるかは
    起動状況によって入れ替わりうる。そこでポート番号を固定せず、VID 0x2E8A
    （ラズピコ）に一致するポートをすべて返し、呼び出し側で実際に READ を
    送って正しく応答したポートを採用する。

    候補が見つからない場合は RuntimeError を送出する。
    """
    if _ENV_PORT:
        return [_ENV_PORT]

    candidates = [
        p.device for p in serial.tools.list_ports.comports()
        if p.vid == _PICO_VID
    ]

    if not candidates:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        raise RuntimeError(
            "Raspberry Pi Pico が見つかりません。"
            f" 検出されたポート: {ports or '(なし)'}"
        )

    if len(candidates) > 1:
        print(
            f"[dht_logger] Pico のポートを複数検出: {candidates}"
            " -> READ に応答するポートを探索します",
            flush=True,
        )

    return candidates


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


def read_sensor():
    """Pico の候補ポートを順に試し、READ に応答したポートの測定値を返す。

    ポート番号（ttyACM0 / ttyACM1）が入れ替わっても、実際に READ へ正しく
    応答したポートを DHT データ用として採用するため、番号に依存しない。
    すべて失敗した場合は None を返す。
    """
    try:
        ports = find_pico_ports()
    except RuntimeError as e:
        print(f"[dht_logger] Port detection error: {e}", flush=True)
        return None

    print(f"[dht_logger] Candidate ports: {ports}", flush=True)

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
