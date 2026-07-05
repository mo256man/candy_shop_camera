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
import time
import evdev
from evdev import ecodes

# Ctrl / Alt は左右どちらでも可
CTRL_KEYS = {ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL}
ALT_KEYS = {ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT}
TRIGGER_KEY = ecodes.KEY_S

# 新しいキーボード（後から接続したラズピコ等）を検出する間隔（秒）
RESCAN_INTERVAL = 3.0

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
    registered = {}  # path -> InputDevice

    def refresh_devices():
        """未登録のキーボード相当デバイスを検出して監視対象に追加する"""
        for dev in find_keyboards():
            if dev.path in registered:
                continue
            try:
                selector.register(dev, selectors.EVENT_READ)
                registered[dev.path] = dev
                print(f"Listening on: {dev.path} ({dev.name})", flush=True)
            except Exception:
                pass

    refresh_devices()
    if not registered:
        print("No keyboard-like input devices found yet. Waiting for connection...", flush=True)

    last_scan = time.monotonic()
    while True:
        for key, _ in selector.select(timeout=1.0):
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
                # デバイスが外れた → 登録解除して再検出対象に戻す
                try:
                    selector.unregister(device)
                except Exception:
                    pass
                registered.pop(device.path, None)

        # 定期的に新しいデバイス（後から接続したラズピコ等）を検出する
        now = time.monotonic()
        if now - last_scan >= RESCAN_INTERVAL:
            refresh_devices()
            last_scan = now


if __name__ == "__main__":
    main()
