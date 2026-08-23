from machine import Pin, I2C
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


# モード
mode = "SENSOR"


# 内蔵LED
led = Pin("LED", Pin.OUT)
led_state = True
led.on()


# ボタン
btnA = Pin(3, Pin.IN, Pin.PULL_UP)
btnB = Pin(7, Pin.IN, Pin.PULL_UP)


# OLED
oled_i2c = I2C(1, sda=Pin(18), scl=Pin(19), freq=400000)
oled = SSD1306_I2C(128, 32, oled_i2c)


# センサー
sensor_i2c = I2C(0, sda=Pin(12), scl=Pin(13), freq=400000)
aht = AHT20(sensor_i2c)
bmp = BMP280(sensor_i2c, addr=0x77)


# センサー前回正常取得値
last_temperature = None
last_humidity = None
last_pressure = None


# NeoPixel
NUM_LED = 60
np = PicoWS2812(10, NUM_LED, brightness=0.1)


# LED演出
led_effect_controller = LEDEffects(np, NUM_LED)
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

    try:
        last_temperature = aht.temperature
        last_humidity = aht.relative_humidity
        return True
    except Exception:
        return False


def read_pressure():
    global last_pressure

    try:
        last_pressure = bmp.pressure / 100
        return True
    except Exception:
        return False


def read_sensors():
    aht_success = read_aht()
    pressure_success = read_pressure()
    return aht_success, pressure_success


# センサー表示モード
# 0: 温度、湿度、気圧
# 1: 温度、湿度を2倍表示
# 2: 温度を4倍表示
sensor_display_mode = 1


def show_sensor():
    read_sensors()
    oled.fill(0)

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

        oled.text("Temp:" + temperature_text, 0, 0)
        oled.text("Hum :" + humidity_text, 0, 11)
        oled.text("Pres:" + pressure_text, 0, 22)

    elif sensor_display_mode == 1:
        if last_temperature is None:
            temperature_text = "ERR"
        else:
            temperature_text = "T:{:4.1f}C".format(last_temperature)

        if last_humidity is None:
            humidity_text = "ERR"
        else:
            humidity_text = "H:{:4.1f}%".format(last_humidity)

        text_scale(oled, temperature_text, 0, 0, 2)
        text_scale(oled, humidity_text, 0, 16, 2)

    else:
        if last_temperature is None:
            temperature_text = "ERR"
        else:
            temperature_text = "{:4.1f}C".format(last_temperature)

        text_scale(oled, temperature_text, 0, 0, 4)

    oled.show()


def show_mode():
    oled.fill(0)
    text_scale(oled, mode, 0, 0, 2)
    oled.show()
    time.sleep(0.5)


def show_led_effect():
    oled.fill(0)
    text_scale(oled, led_effects[led_effect]["label"], 0, 0, 2)
    oled.show()


def update_led():
    led_effects[led_effect]["func"]()
    np.show()


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


# メインループ
try:
    while True:
        now = time.ticks_ms()

        # シリアル命令受信
        if serial_poll.poll(0):
            command = sys.stdin.readline()
            process_serial_command(command)

        # 内蔵LED点滅
        if time.ticks_diff(now, last_led_time) >= 1000:
            led_state = not led_state
            led.value(led_state)
            last_led_time = now

        # LED演出を常時更新
        if time.ticks_diff(now, last_effect_time) >= 100:
            update_led()
            last_effect_time = now

        # センサー値とディスプレイを定期更新
        if time.ticks_diff(now, last_sensor_time) >= 1000:
            if mode == "SENSOR":
                show_sensor()
            elif mode == "LED":
                show_led_effect()

            last_sensor_time = now

        # ボタンA: モード切替
        a = btnA.value()

        if lastA == 1 and a == 0:
            if time.ticks_diff(now, debounceA) > 200:
                if mode == "SENSOR":
                    mode = "LED"
                else:
                    mode = "SENSOR"

                show_mode()
                debounceA = now

        lastA = a

        # ボタンB: 各モード内の設定変更
        b = btnB.value()

        if lastB == 1 and b == 0:
            if time.ticks_diff(now, debounceB) > 200:
                if mode == "SENSOR":
                    sensor_display_mode += 1

                    if sensor_display_mode >= 3:
                        sensor_display_mode = 0

                    show_sensor()
                else:
                    next_effect = led_effect + 1

                    if next_effect >= len(led_effects):
                        next_effect = 0

                    set_led_effect(next_effect)
                    show_led_effect()

                debounceB = now

        lastB = b
        time.sleep_ms(10)

except KeyboardInterrupt:
    np.clear()
    np.show()
    print("LED cleared")
