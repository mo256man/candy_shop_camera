# =============================================================================
# Raspberry Pi Pico - シャットダウンボタン + DHT温湿度センサー
#   (MicroPython / USB 複合デバイス: HID Keyboard + CDC Serial)
# -----------------------------------------------------------------------------
# 機能1) シャットダウンボタン（スイッチのみ / LED なし）
#   - ボタンが 1 秒以上オンになったら USB キーボードとして Ctrl+Alt+S を送信
#
# 機能2) DHT 温湿度センサー（PC からの要求で測定して返す）
#   - PC が USB シリアルに "READ\n" を送ると、DHT を測定して
#     "T=23.0,H=45.0\n" の 1 行で返す（失敗時は "ERR\n"）
#   - 測定タイミングは PC 側の時計で管理する想定（毎時 :00 :10 :20 ...）
#
# 必要環境:
#   - MicroPython v1.23 以降（usb.device モジュールを含むビルド）
#   - パッケージ:
#       mpremote mip install usb-device-keyboard
#       mpremote mip install usb-device-cdc
#   - dht モジュールは MicroPython 同梱
#   - このファイルを Pico に main.py として保存すると、通電で自動実行されます。
#
# 配線（スイッチと DHT をケースの小穴から外に出す想定 / 4線）:
#   Pico 左下の物理ピン 17〜20 を使用する。
#
#   物理ピン17 (GP13) ── 常時 HIGH ── DHT VCC（3V3 代わりに GPIO 出力）
#   物理ピン18 (GND)  ── DHT GND と スイッチの片側（共通）
#   物理ピン19 (GP14) ── スイッチ接点（押すと GND に落ちる）
#   物理ピン20 (GP15) ── DHT DATA（4.7〜10kΩ で VCC へプルアップ。モジュール版は実装済み）
#
#   外に出る線は 4 本: VCC(GP13) / GND / BUTTON(GP14) / DHT DATA(GP15)
#   ※ スイッチは GND に落とす配線なので ACTIVE_HIGH = False
#   ※ DATA のプルアップは GP13(VCC) に対して入れる
# =============================================================================

import time
from machine import Pin
import dht
import usb.device
from usb.device.keyboard import KeyboardInterface, KeyCode
from usb.device.cdc import CDCInterface

# ---- 設定（環境に合わせて変更）----
DHT_PWR_PIN = 13         # 物理ピン17 / GP13。常時 HIGH にして DHT の VCC として使う
BUTTON_PIN = 14          # 物理ピン19 / GP14。スイッチ接点
DHT_PIN = 15             # 物理ピン20 / GP15。DHT DATA
ACTIVE_HIGH = False      # スイッチを GND に落とす配線なので False
HOLD_SECONDS = 1.0       # この秒数以上オンが続いたら送信
POLL_MS = 20             # メインループ周期(ms)
DHT_TYPE = "DHT11"       # "DHT11" または "DHT22"（精度を上げるなら DHT22 推奨）
# ----------------------------------

# DHT の電源ピン（GP13 を常時 HIGH 出力 = 3.3V 供給）
dht_pwr = Pin(DHT_PWR_PIN, Pin.OUT)
dht_pwr.on()
time.sleep_ms(1000)  # センサー電源投入後の安定待ち

# 入力ピン設定（ACTIVE_HIGH なら PULL_DOWN、ACTIVE_LOW なら PULL_UP）
if ACTIVE_HIGH:
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)
else:
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# DHT センサー
if DHT_TYPE == "DHT22":
    sensor = dht.DHT22(Pin(DHT_PIN))
else:
    sensor = dht.DHT11(Pin(DHT_PIN))


def is_pressed():
    return button.value() == 1 if ACTIVE_HIGH else button.value() == 0


# ---- USB 複合デバイス初期化（HID キーボード + CDC シリアル）----
keyboard = KeyboardInterface()
cdc = CDCInterface()
cdc.init(timeout=0)  # 非ブロッキング読み取り
usb.device.get().init(keyboard, cdc, builtin_driver=True)

# ホスト(PC)が両インターフェースを認識するまで待つ
while not (keyboard.is_open() and cdc.is_open()):
    time.sleep_ms(100)


def send_ctrl_alt_s():
    # 修飾キー + S を同時押し → すべて離す
    keyboard.send_keys([KeyCode.LEFT_CTRL, KeyCode.LEFT_ALT, KeyCode.S])
    time.sleep_ms(50)
    keyboard.send_keys([])


def read_dht():
    """DHT を測定して (temp, humi) を返す。失敗時は None。1 回リトライする。"""
    for attempt in range(2):
        try:
            sensor.measure()
            return sensor.temperature(), sensor.humidity()
        except OSError:
            time.sleep_ms(500)
    return None


def handle_command(line):
    """PC からの 1 行コマンドを処理する。"""
    cmd = line.strip().upper()
    if cmd == b"READ":
        result = read_dht()
        if result is None:
            cdc.write(b"ERR\n")
        else:
            t, h = result
            cdc.write("T={:.1f},H={:.1f}\n".format(t, h).encode())


# シリアル受信バッファ
rx = bytearray()


def poll_serial():
    """CDC シリアルを非ブロッキングで読み、改行ごとにコマンド処理する。"""
    data = cdc.read(64)
    if not data:
        return
    rx.extend(data)
    while b"\n" in rx:
        idx = rx.index(b"\n")
        line = bytes(rx[:idx])
        del rx[: idx + 1]
        handle_command(line)


press_start = None   # 押され始めた時刻(ms)
sent = False         # この押下中にすでに送信済みか

while True:
    # --- PC からの測定要求を処理 ---
    poll_serial()

    # --- シャットダウンボタン ---
    if is_pressed():
        if press_start is None:
            press_start = time.ticks_ms()
        elif not sent and time.ticks_diff(time.ticks_ms(), press_start) >= int(HOLD_SECONDS * 1000):
            send_ctrl_alt_s()
            sent = True   # 離すまで再送しない
    else:
        # 非押下: 状態リセット
        press_start = None
        sent = False

    time.sleep_ms(POLL_MS)
