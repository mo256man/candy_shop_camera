# =============================================================================
# Raspberry Pi Pico - シャットダウン信号送出 (MicroPython / USB HID Keyboard)
# -----------------------------------------------------------------------------
# 指定の GPIO が 1 秒以上オンになったら、USB キーボードとして
# Ctrl + Alt + S を 1 回送信します。
# Ubuntu(NUC) 側はこのキー入力を受け取り shutdown します。
#
# LED 表示:
#   - ボタンを押していない … 点灯（デバイスが生きていることを示す）
#   - ボタンを押している   … 点滅
#
# 配線（照光スイッチをケースの小穴から外に出す想定 / GND共通の3線）:
#   GPIO(BUTTON_PIN) ── スイッチ接点 ──┐
#   GPIO(LED_PIN) ─[抵抳]─ LED アノード(+)  │
#   GND ──────────────────────┼─ スイッチ接点(コモン)
#                                 └─ LED カソード(-)
#   ※ スイッチは GND に落とす配線なので ACTIVE_HIGH = False
#   ※ 照光スイッチの LED は 3V 品を選ぶか、適切な抵抳(例330Ω)を入れる。
#     LED 電流は GPIO 定格内(概ね8～12mA以下)に収めること。
#
# 必要環境:
#   - MicroPython v1.23 以降（usb.device モジュールを含むビルド）
#   - usb-device-keyboard パッケージ
#       Thonny の場合: Tools > Manage packages で "usb-device-keyboard" を検索
#       または mpremote: mpremote mip install usb-device-keyboard
#   - このファイルを Pico に main.py として保存すると、通電で自動実行されます。
# =============================================================================

import time
from machine import Pin
import usb.device
from usb.device.keyboard import KeyboardInterface, KeyCode

# ---- 設定（環境に合わせて変更）----
BUTTON_PIN = 15          # 照光スイッチのスイッチ接点をつなぐ GPIO 番号
ACTIVE_HIGH = False      # スイッチを GND に落とす配線なので False（3V3に入れる場合は True）
HOLD_SECONDS = 1.0       # この秒数以上オンが続いたら送信
POLL_MS = 20             # 入力ポーリング間隔(ms)
LED_PIN = 16             # 照光スイッチの LED をつなぐ GPIO 番号（外付けLED）
BLINK_MS = 200           # ボタン押下中の点滅間隔(ms)
# ----------------------------------

# 入力ピン設定（ACTIVE_HIGH なら PULL_DOWN、ACTIVE_LOW なら PULL_UP）
if ACTIVE_HIGH:
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)
else:
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# LED 出力ピン
led = Pin(LED_PIN, Pin.OUT)
led.on()  # 起動直後は点灯（生存表示）


def is_pressed():
    return button.value() == 1 if ACTIVE_HIGH else button.value() == 0


# USB HID キーボードとして自分を初期化
keyboard = KeyboardInterface()
usb.device.get().init(keyboard, builtin_driver=True)

# ホスト(PC)がインターフェースを認識するまで待つ
while not keyboard.is_open():
    time.sleep_ms(100)


def send_ctrl_alt_s():
    # 修飾キー + S を同時押し → すべて離す
    keyboard.send_keys([KeyCode.LEFT_CTRL, KeyCode.LEFT_ALT, KeyCode.S])
    time.sleep_ms(50)
    keyboard.send_keys([])


press_start = None   # 押され始めた時刻(ms)
sent = False         # この押下中にすでに送信済みか
blink_last = time.ticks_ms()  # 最後に点滅トグルした時刻(ms)

while True:
    if is_pressed():
        # --- 押下中: LED を点滅させる ---
        if time.ticks_diff(time.ticks_ms(), blink_last) >= BLINK_MS:
            led.toggle()
            blink_last = time.ticks_ms()

        if press_start is None:
            press_start = time.ticks_ms()
        elif not sent and time.ticks_diff(time.ticks_ms(), press_start) >= int(HOLD_SECONDS * 1000):
            send_ctrl_alt_s()
            sent = True   # 離すまで再送しない
    else:
        # --- 非押下: LED 点灯（生存表示）/ 状態リセット ---
        led.on()
        press_start = None
        sent = False

    time.sleep_ms(POLL_MS)
