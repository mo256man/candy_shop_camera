from machine import Pin, I2C
from neopixel import NeoPixel
from ssd1306 import SSD1306_I2C
from ahtx0 import AHT20
from bmp280 import BMP280
from framebuf import FrameBuffer, MONO_HLSB
from myLED import PicoWS2812
from led_effects import LEDEffects
import time
import sys
import json
import uselect

# ボタン
btnA = Pin(2, Pin.IN, Pin.PULL_UP)
btnB = Pin(1, Pin.IN, Pin.PULL_UP)

# 単色LED (R=GPIO17, G=GPIO16, B=GPIO25)
mono_led_r = Pin(17, Pin.OUT)
mono_led_g = Pin(16, Pin.OUT)
mono_led_b = Pin(25, Pin.OUT)

# 外付けのNeoPixel LED (GPIO4)
external_led = NeoPixel(Pin(4), 1)

# True: LOWで点灯(active-low), False: HIGHで点灯(active-high)
MONO_LED_ACTIVE_LOW = True


def set_mono_led(r_on, g_on, b_on):
    if MONO_LED_ACTIVE_LOW:
        mono_led_r.value(0 if r_on else 1)
        mono_led_g.value(0 if g_on else 1)
        mono_led_b.value(0 if b_on else 1)
    else:
        mono_led_r.value(1 if r_on else 0)
        mono_led_g.value(1 if g_on else 0)
        mono_led_b.value(1 if b_on else 0)


def clear_mono_led():
    set_mono_led(False, False, False)


# 起動直後に単色LEDを消灯
clear_mono_led()

# 内蔵フルカラーLED (XIAO RP2040: 電源=GPIO11, データ=GPIO12)
led_power = Pin(11, Pin.OUT)
onboard_led = NeoPixel(Pin(12), 1)
led_power.on()
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# 0.0 ～ 1.0 で内蔵LEDの明るさを一括調整
LED_BRIGHTNESS = 0.005


def with_brightness(color, brightness):
    return tuple(int(c * brightness) for c in color)

LED_RED = with_brightness(RED, LED_BRIGHTNESS)
LED_GREEN = with_brightness(GREEN, LED_BRIGHTNESS)
LED_BLUE = with_brightness(BLUE, LED_BRIGHTNESS)
LED_YELLOW = with_brightness(YELLOW, LED_BRIGHTNESS)
LED_OFF = (0, 0, 0)

# ボタン応答設定
BUTTON_DEBOUNCE_MS = 80
MODE_OVERLAY_MS = 500
MAIN_LOOP_SLEEP_MS = 5

def set_onboard_led(color):
    onboard_led[0] = color
    onboard_led.write()

# コード開始直後: 赤
set_onboard_led(LED_RED)

# モード
mode = "SENSOR"

# 内蔵LED点滅状態
led_state = True

# I2C (XIAO RP2040: SDA=6, SCL=7)
sensor_i2c = I2C(1, sda=Pin(6, Pin.PULL_UP), scl=Pin(7, Pin.PULL_UP), freq=100000, timeout=200000)
time.sleep_ms(100)

oled = None
aht = None
bmp = None

# OLED
try:
    oled = SSD1306_I2C(128, 32, sensor_i2c)
except Exception:
    oled = None

# AHT20
try:
    aht = AHT20(sensor_i2c)
except Exception:
    aht = None

# BMP280
for bmp_addr in (0x77, 0x76):
    try:
        bmp = BMP280(sensor_i2c, addr=bmp_addr)
        break
    except Exception:
        bmp = None


# センサー前回正常取得値
last_temperature = None
last_humidity = None
last_pressure = None

# NeoPixel
NUM_LED = 60
led_strip = PicoWS2812(10, NUM_LED, brightness=0.1)

# LED演出
led_effect_controller = LEDEffects(led_strip, NUM_LED)
led_effects = led_effect_controller.get_effects()
led_effect = 0

def text_scale(oled, text, x, y, scale):
    width = 8 * len(text)
    buffer = bytearray(width)
    framebuffer = FrameBuffer(buffer, width, 8, MONO_HLSB)

    framebuffer.fill(0)
    framebuffer.text(text, 0, 0)

    for yy in range(8):
        for xx in range(width):
            if framebuffer.pixel(xx, yy):
                oled.fill_rect(x + xx * scale, y + yy * scale, scale, scale, 1)

def read_aht():
    global last_temperature
    global last_humidity

    if aht is None:
        return False

    try:
        last_temperature = aht.temperature
        last_humidity = aht.relative_humidity
        return True
    except Exception:
        return False

def read_pressure():
    global last_pressure

    if bmp is None:
        return False

    try:
        last_pressure = bmp.pressure / 100
        return True
    except Exception:
        return False

def read_sensors():
    aht_success = read_aht()
    pressure_success = read_pressure()

    # シリアルの応答は JSON のみを返すようにし、ホスト側の line-by-line 読み取りで
    # 余計なデバッグ文字列が混ざらないようにする
    return aht_success, pressure_success


def get_status_color():
    sensor_ok = (
        aht is not None
        and bmp is not None
        and last_temperature is not None
        and last_humidity is not None
        and last_pressure is not None
    )
    display_ok = oled is not None

    if sensor_ok and display_ok:
        return LED_GREEN
    if sensor_ok:
        return LED_BLUE
    if display_ok:
        return LED_YELLOW
    return LED_RED


# センサー表示モード
# 0: 温度、湿度、気圧
# 1: 温度、湿度を2倍表示
# 2: 温度を4倍表示
sensor_display_mode = 1


def show_sensor(read_now=True):
    if read_now:
        read_sensors()

    if oled is None:
        return

    oled.fill(0)

    colon = ":" if (time.ticks_ms() // 1000) % 2 == 0 else " "

    if sensor_display_mode == 0:
        if last_temperature is None:
            temperature_text = "ERR"
        else:
            temperature_text = "{:.1f}C".format(last_temperature)

        if last_humidity is None:
            humidity_text = "ERR"
        else:
            humidity_text = "{:.1f}%".format(last_humidity)

        if last_pressure is None:
            pressure_text = "ERR"
        else:
            pressure_text = "{:.1f}".format(last_pressure)

        oled.text("Temp" + colon + temperature_text, 0, 0)
        oled.text("Hum " + colon + humidity_text, 0, 11)
        oled.text("Pres" + colon + pressure_text, 0, 22)

    elif sensor_display_mode == 1:
        if last_temperature is None:
            temperature_text = "ERR"
        else:
            temperature_text = "T{colon}{:4.1f}C".format(last_temperature, colon=colon)

        if last_humidity is None:
            humidity_text = "ERR"
        else:
            humidity_text = "H{colon}{:4.1f}%".format(last_humidity, colon=colon)

        text_scale(oled, temperature_text, 0, 0, 2)
        text_scale(oled, humidity_text, 0, 16, 2)

    else:
        if last_temperature is None:
            temperature_text = "ERR"
        else:
            temperature_value = int(round(last_temperature * 10))
            temperature_text = "{:03d}C".format(temperature_value)

        text_scale(oled, temperature_text, 0, 0, 4)

        if last_temperature is not None:
            dot_x = 62
            dot_y = 24
            oled.fill_rect(dot_x - 1, dot_y - 1, 6, 6, 0)
            oled.fill_rect(dot_x, dot_y, 4, 4, 1)

    oled.show()


def show_mode():
    if oled is None:
        return

    oled.fill(0)
    text_scale(oled, mode, 0, 0, 2)
    oled.show()


def show_led_effect():
    if oled is None:
        return

    oled.fill(0)
    text_scale(oled, led_effects[led_effect]["label"], 0, 0, 2)
    oled.show()


def update_led():
    led_effects[led_effect]["func"]()
    led_strip.show()


def set_led_effect(effect_index):
    global led_effect

    led_effect = effect_index
    effect_label = led_effects[led_effect]["label"]
    led_effect_controller.prepare_effect(effect_label)
    update_led()


def send_json(data):
    print(json.dumps(data))


def process_serial_command(command):
    command = command.strip()

    if command == "":
        return

    if command == "GET_TEMPERATURE":
        read_sensors()

        send_json({
            "temperature": (
                round(last_temperature, 1)
                if last_temperature is not None
                else None
            ),
            "humidity": (
                round(last_humidity, 1)
                if last_humidity is not None
                else None
            ),
            "pressure": (
                round(last_pressure, 1)
                if last_pressure is not None
                else None
            )
        })
        return

    if command.startswith("LED_"):
        function_name = command[4:]

        for index, effect in enumerate(led_effects):
            if effect["label"] == function_name:
                set_led_effect(index)
                show_led_effect()
                send_json({"result": "done"})
                return

        send_json({
            "result": "error",
            "message": "unknown LED function"
        })
        return

    send_json({
        "result": "error",
        "message": "unknown command"
    })


# シリアル入力監視
serial_poll = uselect.poll()
serial_poll.register(sys.stdin, uselect.POLLIN)


# 起動表示
show_sensor()

# ボタン管理
lastA = 1
lastB = 1
debounceA = 0
debounceB = 0

last_led_time = time.ticks_ms()
last_effect_time = time.ticks_ms()
last_sensor_time = time.ticks_ms()
mode_overlay_until = 0

# メインループ
try:
    # 無限ループ開始: 認識状態に応じた色
    set_onboard_led(get_status_color())

    while True:
        now = time.ticks_ms()

        # シリアル命令受信
        if serial_poll.poll(0):
            command = sys.stdin.readline()
            process_serial_command(command)

        # 内蔵LED点滅 (認識状態に応じた色)
        if time.ticks_diff(now, last_led_time) >= 1000:
            led_state = not led_state
            set_onboard_led(get_status_color() if led_state else LED_OFF)
            last_led_time = now

        # LED演出を常時更新
        if time.ticks_diff(now, last_effect_time) >= 100:
            update_led()
            last_effect_time = now

        # センサー値とディスプレイを定期更新
        if time.ticks_diff(now, last_sensor_time) >= 1000:
            if time.ticks_diff(mode_overlay_until, now) <= 0:
                if mode == "SENSOR":
                    show_sensor()
                elif mode == "LED":
                    show_led_effect()

            last_sensor_time = now

        # ボタンA: モード切替
        a = btnA.value()

        if lastA == 1 and a == 0:
            if time.ticks_diff(now, debounceA) > BUTTON_DEBOUNCE_MS:
                if mode == "SENSOR":
                    mode = "LED"
                else:
                    mode = "SENSOR"

                show_mode()
                mode_overlay_until = time.ticks_add(now, MODE_OVERLAY_MS)
                debounceA = now

        lastA = a

        # ボタンB: 各モード内の設定変更
        b = btnB.value()

        if lastB == 1 and b == 0:
            if time.ticks_diff(now, debounceB) > BUTTON_DEBOUNCE_MS:
                if mode == "SENSOR":
                    sensor_display_mode += 1

                    if sensor_display_mode >= 3:
                        sensor_display_mode = 0

                    show_sensor(read_now=False)
                else:
                    next_effect = led_effect + 1

                    if next_effect >= len(led_effects):
                        next_effect = 0

                    set_led_effect(next_effect)
                    show_led_effect()

                debounceB = now

        lastB = b
        time.sleep_ms(MAIN_LOOP_SLEEP_MS)

finally:
    led_strip.clear()
    led_strip.show()
    clear_mono_led()
    set_onboard_led(LED_OFF)
    led_power.off()
    print("LED cleared")

