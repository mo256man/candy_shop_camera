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
        combined = f"{p.description or ''} {p.device} {p.hwid or ''}".lower()
        if any(token in combined for token in ("pico", "rp2040", "xiao", "seeed", "usb serial", "arduino")):
            print(f"[検出] Pico互換デバイスを検出: {p.device}")
            return p.device

    # 'pico' で見つからない場合、類似デバイスの ttyACM/ttyUSB をフォールバック候補として提示
    for p in ports:
        device = p.device.lower()
        if "ttyacm" in device or "ttyusb" in device or "cu.usbmodem" in device:
            print(f"[フォールバック] シリアルポートを候補にします: {p.device}")
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

    data = None
    for _ in range(20):
        line = ser.readline()
        if not line:
            break

        raw = line.decode(errors="replace").strip()
        if not raw:
            continue

        print(f"[受信] {raw}")

        try:
            data = json.loads(raw)
            break
        except ValueError:
            print("[INFO] JSONでない行をスキップしました。")

    if data is None:
        print("[NG] JSON応答がありませんでした。")
        ser.close()
        return

    print("[OK] JSONとして解釈できました:")
    print(f"    temperature = {data.get('temperature')}")
    print(f"    humidity    = {data.get('humidity')}")
    print(f"    pressure    = {data.get('pressure')}")

    ser.close()


if __name__ == "__main__":
    main()
