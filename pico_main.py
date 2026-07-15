# =============================================================================
# Raspberry Pi Pico - メインプログラム
# =============================================================================

import time
import json
import usb.device
from usb.device.cdc import CDCInterface
from pico_class import DHT11PIO, DisplayPIO, Button, Color

# ---- 設定 ----
BUTTON_POLL_MS = 20
HOLD_TIME_SHORT = 1.0
HOLD_TIME_LONG = 3.0
RESPONSE_TIMEOUT = 5.0
MAX_RETRIES = 3
DHT_PIN = 10
NUM_DISPLAY_MODES = 3  # mode=0, 1, 2

# ---- インスタンス化 ----
dht_sensor = DHT11PIO(DHT_PIN)
display = DisplayPIO(cs_pin=22, reset_pin=21, a0_pin=20, clk_pin=18, mosi_pin=19, led_pin=15)
btn_a = Button(2)
btn_b = Button(4)
btn_c = Button(7)

print("Waiting 2 seconds... Press Ctrl+C to skip main loop")
for i in range(20):
    time.sleep_ms(100)

# ---- シリアル通信 ----
cdc = CDCInterface()
cdc.init(timeout=0)
usb.device.get().init(cdc, builtin_driver=True)

while not cdc.is_open():
    time.sleep_ms(100)

# ---- 状態変数 ----
disp_mode = 0
rx_buffer = bytearray()
last_temp = None
last_humi = None
send_state = None  # None, "sending", "ok", "ng"
x2 = 0

# ---- 通信関数 ----
def send_to_pc(data_dict):
    """JSONでPCに送信"""
    json_str = json.dumps(data_dict)
    cdc.write((json_str + "\n").encode())

def send_and_wait_ack(data_dict, timeout=RESPONSE_TIMEOUT):
    """PCにデータを送信し、RESP応答を待つ"""
    send_to_pc(data_dict)
    
    start_time = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start_time) < timeout * 1000:
        response_data = cdc.read(64)
        if response_data:
            rx_buffer.extend(response_data)
            if b"\n" in rx_buffer:
                idx = rx_buffer.index(b"\n")
                line = bytes(rx_buffer[:idx])
                del rx_buffer[:idx+1]
                
                try:
                    resp_dict = json.loads(line.decode())
                    if "RESP" in resp_dict:
                        return True
                except ValueError:
                    pass
        time.sleep_ms(50)
    
    return False

def display_temperature(temp, humi, state=None):
    """温度・湿度表示（mode=0用）"""
    if disp_mode != 0:
        return
    
    # 画面クリア（全白）
    display.fill(Color.WHITE)
    
    # テキスト表示
    display.text("Enviroment", 0, 0, Color.BLACK, scale=2)
    display.text(f"TEMP:{temp:>4.1f}C", 16, 16, Color.BLACK, scale=2)
    display.text(f"HUMI:{humi:>2.0f}  %", 16, 32, Color.BLACK, scale=2)
    
    # 送信状態表示
    if state == "sending":
        display.text("sending...", 16, 96, Color.BLUE, scale=2)
    elif state == "ok":
        display.fill(Color.WHITE)  # 送信状態を消すため画面再クリア
        display.text("Enviroment", 0, 0, Color.BLACK, scale=2)
        display.text(f"TEMP:{temp:>4.1f}C", 16, 16, Color.BLACK, scale=2)
        display.text(f"HUMI:{humi:>2.0f}  %", 16, 32, Color.BLACK, scale=2)
    elif state == "ng":
        display.text("send ng", 16, 96, Color.RED, scale=2)

def display_data():
    """データ表示（mode=1用）"""
    if disp_mode != 1:
        return
    
    # 画面クリア（全白）
    display.fill(Color.WHITE)
    
    # テキスト表示
    display.text("Data", 0, 0, Color.BLACK, scale=2)

def display_test(x2):
    """テスト表示（mode=2用）"""
    if disp_mode != 2:
        return
    
    # 画面クリア（全白）
    display.fill(Color.WHITE)
    
    # 3つの黒い四角形を描く
    for i in [0, 1, 2]:
        x = 10 + 40 * i
        y = 30
        display.rect(x, y, 40, 40, Color.BLACK)
    
    # 選択された四角形を赤で塗りつぶす
    x = 10 + 40 * x2
    y = 30
    display.fill_rect(x, y, 40, 40, Color.RED)

def send_dht_with_retry():
    """DHT11データ送信（最大3回再試行）"""
    global last_temp, last_humi, send_state
    
    for attempt in range(MAX_RETRIES):
        result = dht_sensor.measure()
        if result is None:
            continue
        
        temp, humi = result
        last_temp = temp
        last_humi = humi
        
        data = {"temp": temp, "humi": humi}
        send_to_pc(data)
        
        # 送信中表示
        send_state = "sending"
        display_temperature(temp, humi, state="sending")
        
        # PCからの応答を待つ
        start_time = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start_time) < RESPONSE_TIMEOUT * 1000:
            response_data = cdc.read(64)
            if response_data:
                rx_buffer.extend(response_data)
                if b"\n" in rx_buffer:
                    idx = rx_buffer.index(b"\n")
                    line = bytes(rx_buffer[:idx])
                    del rx_buffer[:idx+1]
                    
                    try:
                        resp_dict = json.loads(line.decode())
                        if resp_dict.get("RESP") == "ok":
                            send_state = "ok"
                            display_temperature(temp, humi, state="ok")
                            return True
                    except ValueError:
                        pass
            time.sleep_ms(50)
        
        # タイムアウト＝NG
        send_state = "ng"
        display_temperature(temp, humi, state="ng")
        time.sleep_ms(500)
    
    return False

def handle_command(cmd_dict):
    """PCからのコマンド処理"""
    command = cmd_dict.get("command")
    if command == "COPY":
        send_dht_with_retry()
    elif command == "READ":
        send_dht_with_retry()

def poll_serial():
    """シリアル受信処理"""
    data = cdc.read(64)
    if not data:
        return
    
    rx_buffer.extend(data)
    while b"\n" in rx_buffer:
        idx = rx_buffer.index(b"\n")
        line = bytes(rx_buffer[:idx])
        del rx_buffer[:idx+1]
        
        try:
            cmd_dict = json.loads(line.decode())
            handle_command(cmd_dict)
        except ValueError:
            pass

# ---- メインループ ----
while True:
    poll_serial()
    
    btn_a.update()
    btn_b.update()
    btn_c.update()
    
    # btnC: disp_mode切り替え
    if btn_c.held_for(0.1):
        disp_mode = (disp_mode + 1) % NUM_DISPLAY_MODES
        btn_c.sent = True
        # mode=0に切り替わったとき、初期表示
        if disp_mode == 0 and last_temp is not None:
            display_temperature(last_temp, last_humi, state=None)
    
    if disp_mode == 1:
        both_pressed = btn_a.is_pressed() and btn_b.is_pressed()
        
        # btnA単独 1秒以上（btnBが同時に押されていない場合のみ）
        if not both_pressed and btn_a.held_for(HOLD_TIME_SHORT) and not btn_a.sent:
            send_and_wait_ack({"command": "COPY"})
            btn_a.sent = True
        
        # btnB単独 1秒以上（btnAが同時に押されていない場合のみ）
        if not both_pressed and btn_b.held_for(HOLD_TIME_SHORT) and not btn_b.sent:
            send_and_wait_ack({"command": "DELETE"})
            btn_b.sent = True
        
        # btnA + btnB 3秒以上
        if both_pressed:
            if btn_a.pressed_time is not None and btn_b.pressed_time is not None:
                min_press_time = min(btn_a.pressed_time, btn_b.pressed_time)
                elapsed = time.ticks_diff(time.ticks_ms(), min_press_time)
                if elapsed >= HOLD_TIME_LONG * 1000 and not btn_a.sent and not btn_b.sent:
                    send_and_wait_ack({"command": "SHUTDOWN"})
                    btn_a.sent = True
                    btn_b.sent = True
    
    elif disp_mode == 2:
        global x2
        # btnA: x2を-1してmod 3
        if btn_a.held_for(HOLD_TIME_SHORT) and not btn_a.sent:
            x2 = (x2 - 1) % 3
            display_test(x2)
            btn_a.sent = True
        
        # btnB: x2を+1してmod 3
        if btn_b.held_for(HOLD_TIME_SHORT) and not btn_b.sent:
            x2 = (x2 + 1) % 3
            display_test(x2)
            btn_b.sent = True
        
        # 初期表示
        display_test(x2)
    
    time.sleep_ms(BUTTON_POLL_MS)
