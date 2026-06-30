#!/usr/bin/env python3
# =============================================================================
# シャットダウンリスナー (Windows 版)
# -----------------------------------------------------------------------------
# Raspberry Pi Pico が USB キーボードとして送る Ctrl+Alt+S を検知し、
# Windows をシャットダウンします（キーボード入力なしで動作）。
# 常駐させて使います（タスクスケジューラでログオン時に起動推奨）。
#
# 依存: pip install keyboard
#   ※ keyboard ライブラリのグローバルフックは管理者権限で実行すると確実です。
# =============================================================================

import subprocess
import keyboard

HOTKEY = "ctrl+alt+s"


def shutdown():
    print("Ctrl+Alt+S detected -> shutting down now", flush=True)
    # 即時シャットダウン
    subprocess.run(["shutdown", "/s", "/t", "0"])


def main():
    print(f"Listening for {HOTKEY} ...", flush=True)
    keyboard.add_hotkey(HOTKEY, shutdown)
    # キー入力を待ち続ける（常駐）
    keyboard.wait()


if __name__ == "__main__":
    main()
