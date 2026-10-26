import json
import time
import serial
import serial.tools.list_ports

BAUDRATE = 115200
TIMEOUT = 2.0


def find_pico_port():
    print("=== 検出されたシリアルポート一覧 ===")
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("  (ポートが1つも見つかりません)")
    for p in ports:
        print(f"  device={p.device}  description={p.description}  hwid={p.hwid}")
    print("=" * 40)

    for p in ports:
        if "pico" in (p.description or "").lower():
            print(f"[検出] description に 'pico' を含むポート: {p.device}")
            return p.device

    # 'pico' で見つからない場合、ttyACM* をフォールバック候補として提示
    for p in ports:
        if "ttyACM" in p.device:
            print(f"[フォールバック] ttyACM ポートを候補にします: {p.device}")
            print("  （description に 'pico' が無いため、本番コードでは検出漏れの可能性あり）")
            return p.device

    return None


def main():
    port = find_pico_port()
    if port is None:
        print("[NG] Picoのポートが見つかりませんでした。")
        return

    try:
        ser = serial.Serial(port, BAUDRATE, timeout=TIMEOUT)
    except serial.SerialException as e:
        print(f"[NG] ポートを開けませんでした: {e}")
        print("  → 権限（dialoutグループ）や他プロセスによる占有を確認してください。")
        return

    print(f"[OK] 接続しました: {port}")

    # Pico起動直後の安定待ち
    time.sleep(1.0)
    ser.reset_input_buffer()

    ser.write(b"GET_TEMPERATURE\n")
    print("[送信] GET_TEMPERATURE")

    line = ser.readline()
    if not line:
        print("[NG] 応答がありません（タイムアウト）。")
        ser.close()
        return

    raw = line.decode(errors="replace").strip()
    print(f"[受信] {raw}")

    try:
        data = json.loads(raw)
        print("[OK] JSONとして解釈できました:")
        print(f"    temperature = {data.get('temperature')}")
        print(f"    humidity    = {data.get('humidity')}")
        print(f"    pressure    = {data.get('pressure')}")
    except ValueError:
        print("[NG] JSONとして解釈できませんでした。")

    ser.close()


if __name__ == "__main__":
    main()
