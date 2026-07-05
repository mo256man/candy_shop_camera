#!/usr/bin/env bash
# =============================================================================
# 駄菓子屋さんカメラ - Ubuntu 自動起動スクリプト
# -----------------------------------------------------------------------------
# Flask (server) と Vite (client) をまとめて起動します。
# --camera_id を渡すと、サーバー側でカメラを自動初期化し、
# ready_record=true（AI連動録画オン）の状態で立ち上がります。
#
# 使い方:
#   ./start_camera.sh            # CAMERA_ID 環境変数（既定 2）を使用
#   CAMERA_ID=1 ./start_camera.sh
# =============================================================================

set -euo pipefail

# このスクリプトが置かれているディレクトリ（= プロジェクトルート）を基準にする
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="${PROJECT_DIR}/server"
CLIENT_DIR="${PROJECT_DIR}/client"

# 起動時に使用するカメラID（環境変数で上書き可能。既定は 2）
CAMERA_ID="${CAMERA_ID:-2}"

# Python 実行コマンド（pyenv の python 実体を直接指定する）
# systemd などの自動起動では PATH に pyenv シムが無く、システムの別 python3 が
# 使われて numpy 不一致などになるため、実体パスを直接指定する。
PYTHON="/home/ubuntu/.pyenv/versions/3.9.19/bin/python"

# node / npm の置き場所（fnm のインストール先の bin）
# systemd などの自動起動では PATH に node/npm が無く「command not found」や
# 「'node': そのようなファイルやディレクトリ」になるため、この bin を PATH に追加する。
NODE_DIR="/home/ubuntu/.local/share/fnm/node-versions/v24.18.0/installation/bin"
export PATH="${NODE_DIR}:${PATH}"
NPM="${NODE_DIR}/npm"

# 終了時に子プロセス（Flask / Vite / ブラウザ）をまとめて停止する
cleanup() {
  echo "[start_camera] Shutting down child processes..."
  # 再帰呼び出しを防ぐためトラップをリセット
  trap - EXIT INT TERM
  kill "${FLASK_PID:-}" "${VITE_PID:-}" "${BROWSER_PID:-}" 2>/dev/null || true
  wait "${FLASK_PID:-}" "${VITE_PID:-}" "${BROWSER_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ブラウザ起動関数
start_browser() {
  local browser_cmd=""
  if command -v google-chrome &> /dev/null; then
    browser_cmd="google-chrome"
  elif command -v chromium-browser &> /dev/null; then
    browser_cmd="chromium-browser"
  else
    echo "[start_camera] Warning: Chrome/Chromium not found. Skipping browser startup."
    return
  fi
  
  echo "[start_camera] Waiting for display to become available..."
  # DISPLAY が利用可能になるまで最大 30 秒待つ
  local timeout=30
  while [ $timeout -gt 0 ]; do
    if [ -n "$DISPLAY" ] 2>/dev/null; then
      break
    fi
    # X socket を確認（:0 または :1）
    if [ -S /tmp/.X11-unix/0 ] 2>/dev/null || [ -S /tmp/.X11-unix/1 ] 2>/dev/null; then
      export DISPLAY=":0"
      break
    fi
    timeout=$((timeout - 1))
    sleep 1
  done
  
  if [ -z "$DISPLAY" ]; then
    echo "[start_camera] Display still not available after waiting. Browser will run in background."
    export DISPLAY=":0"
  fi
  
  echo "[start_camera] Starting browser on display $DISPLAY..."
  "$browser_cmd" --kiosk http://localhost:5173 > /dev/null 2>&1 &
  BROWSER_PID=$!
  echo "[start_camera] Browser PID=${BROWSER_PID}"
}

echo "[start_camera] PROJECT_DIR = ${PROJECT_DIR}"
echo "[start_camera] CAMERA_ID   = ${CAMERA_ID}"
echo "[start_camera] PYTHON      = ${PYTHON}"
echo "[start_camera] NPM         = ${NPM}"

# --- Flask サーバー起動（カメラ自動初期化 + AI連動録画オン）---
echo "[start_camera] Starting Flask server..."
cd "${SERVER_DIR}"
"${PYTHON}" app.py --camera_id="${CAMERA_ID}" &
FLASK_PID=$!

# --- Vite クライアント起動 ---
echo "[start_camera] Starting Vite client..."
cd "${CLIENT_DIR}"
"${NPM}" run dev &
VITE_PID=$!

echo "[start_camera] Flask PID=${FLASK_PID}, Vite PID=${VITE_PID}"

# --- ブラウザ起動（Flask/Vite 起動後に DISPLAY 待機） ---
start_browser

echo "[start_camera] Running. Press Ctrl+C to stop."

# どれかのプロセスが終了したらスクリプトも終了する
wait -n "${FLASK_PID}" "${VITE_PID}" "${BROWSER_PID:-}"
