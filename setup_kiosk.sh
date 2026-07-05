#!/usr/bin/env bash
# =============================================================================
# Dagashiya Camera - キオスク設定スクリプト
# =============================================================================
# 起動時に Chrome でブラウザ全画面表示（localhost:5173）を有効にします

set -euo pipefail

echo "[setup_kiosk] Setting up Dagashiya Camera Kiosk autostart..."

# autostart ディレクトリを作成
mkdir -p ~/.config/autostart

# dagashiya-kiosk.desktop を作成
cat > ~/.config/autostart/dagashiya-kiosk.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Dagashiya Camera Kiosk
Exec=google-chrome --kiosk http://localhost:5173
X-GNOME-Autostart-enabled=true
EOF

echo "[setup_kiosk] Done! ~/.config/autostart/dagashiya-kiosk.desktop が作成されました。"
echo "[setup_kiosk] 次回起動時に Chrome がキオスク表示で localhost:5173 を開きます。"
echo ""
echo "※ Chromium を使う場合は以下で編集してください:"
echo "  nano ~/.config/autostart/dagashiya-kiosk.desktop"
echo "  Exec=google-chrome を Exec=chromium-browser に変更"
