#!/usr/bin/env python3
# =============================================================================
# Ubuntu - シャットダウンリスナー (Ctrl+Alt+S 受信 → shutdown)
# -----------------------------------------------------------------------------
# Raspberry Pi Pico が USB キーボードとして送る Ctrl+Alt+S を検知し、
# キーボード入力なし・デスクトップ非依存で shutdown を実行します。
# root 権限の systemd サービスとして常駐させる前提です（sudo 不要）。
#
# 依存パッケージ:
#   sudo apt install python3-evdev
#   （または: pip install evdev）
# =============================================================================

import subprocess
import selectors
import evdev
from evdev import ecodes

# Ctrl / Alt は左右どちらでも可
CTRL_KEYS = {ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL}
ALT_KEYS = {ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT}
TRIGGER_KEY = ecodes.KEY_S

# 現在押されているキーの集合（全デバイス共通で管理）
pressed = set()


def find_keyboards():
    """Ctrl と S を入力できる（=キーボード相当の）デバイスを列挙"""
    devices = []
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except Exception:
            continue
        key_caps = dev.capabilities().get(ecodes.EV_KEY, [])
        has_ctrl = ecodes.KEY_LEFTCTRL in key_caps or ecodes.KEY_RIGHTCTRL in key_caps
        if TRIGGER_KEY in key_caps and has_ctrl:
            devices.append(dev)
    return devices


def trigger_shutdown():
    print("Ctrl+Alt+S detected -> shutting down now", flush=True)
    # root で動作するため sudo は不要。shutdown を実行
    subprocess.run(["/sbin/shutdown", "-h", "now"])


def main():
    selector = selectors.DefaultSelector()
    devices = find_keyboards()
    if not devices:
        print("No keyboard-like input devices found.", flush=True)
    for dev in devices:
        print(f"Listening on: {dev.path} ({dev.name})", flush=True)
        selector.register(dev, selectors.EVENT_READ)

    while True:
        for key, _ in selector.select():
            device = key.fileobj
            try:
                for event in device.read():
                    if event.type != ecodes.EV_KEY:
                        continue
                    if event.value == 1:  # キー押下
                        pressed.add(event.code)
                        if event.code == TRIGGER_KEY and (pressed & CTRL_KEYS) and (pressed & ALT_KEYS):
                            trigger_shutdown()
                            return
                    elif event.value == 0:  # キー解放
                        pressed.discard(event.code)
            except OSError:
                # デバイスが外れた場合などは無視
                pass


if __name__ == "__main__":
    main()
