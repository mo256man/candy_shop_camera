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

# Python 実行コマンド（venv があれば優先して使う）
if [ -x "${SERVER_DIR}/.venv/bin/python" ]; then
  PYTHON="${SERVER_DIR}/.venv/bin/python"
elif [ -x "${PROJECT_DIR}/.venv/bin/python" ]; then
  PYTHON="${PROJECT_DIR}/.venv/bin/python"
else
  PYTHON="python3"
fi

# 終了時に子プロセス（Flask / Vite）をまとめて停止する
cleanup() {
  echo "[start_camera] Shutting down child processes..."
  # 再帰呼び出しを防ぐためトラップをリセット
  trap - EXIT INT TERM
  kill "${FLASK_PID:-}" "${VITE_PID:-}" 2>/dev/null || true
  wait "${FLASK_PID:-}" "${VITE_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[start_camera] PROJECT_DIR = ${PROJECT_DIR}"
echo "[start_camera] CAMERA_ID   = ${CAMERA_ID}"
echo "[start_camera] PYTHON      = ${PYTHON}"

# --- Flask サーバー起動（カメラ自動初期化 + AI連動録画オン）---
echo "[start_camera] Starting Flask server..."
cd "${SERVER_DIR}"
"${PYTHON}" app.py --camera_id="${CAMERA_ID}" &
FLASK_PID=$!

# --- Vite クライアント起動 ---
echo "[start_camera] Starting Vite client..."
cd "${CLIENT_DIR}"
npm run dev &
VITE_PID=$!

echo "[start_camera] Flask PID=${FLASK_PID}, Vite PID=${VITE_PID}"
echo "[start_camera] Running. Press Ctrl+C to stop."

# どちらかのプロセスが終了したらスクリプトも終了する
wait -n "${FLASK_PID}" "${VITE_PID}"
