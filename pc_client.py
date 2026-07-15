# =============================================================================
# PC Client - Raspberry Pi Pico との通信
# =============================================================================

import serial
import serial.tools.list_ports
import json
import time
import keyboard

# ---- 設定 ----
BAUDRATE = 115200
TIMEOUT = 1.0

def find_pico_port():
    """
    ラズピコのシリアルポートを自動検出
    Windows: COM* (usbserialなど)
    Linux: /dev/ttyACM* または /dev/ttyUSB*
    """
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("[ERROR] No serial ports found")
        return None
    
    # 最初のポートを使用（複数あればusbserialやusbが含まれているものを優先）
    pico_port = None
    for port in ports:
        if 'usb' in port.description.lower() or 'pico' in port.description.lower():
            pico_port = port.device
            break
    
    if pico_port is None:
        pico_port = ports[0].device
    
    print(f"[INFO] Using port: {pico_port}")
    return pico_port

def main():
    """メインループ"""
    # ポート接続
    port = find_pico_port()
    if port is None:
        return
    
    try:
        ser = serial.Serial(port, BAUDRATE, timeout=TIMEOUT)
        print(f"[INFO] Connected to {port} at {BAUDRATE} baud")
    except serial.SerialException as e:
        print(f"[ERROR] Failed to connect: {e}")
        return
    
    rx_buffer = bytearray()
    
    print("[INFO] Commands: r=READ, q=quit")
    print("[INFO] Waiting for input...")
    
    try:
        while True:
            # キーボード入力チェック
            if keyboard.is_pressed('r'):
                print("[DEBUG] 'r' pressed")
                # READ コマンド送信
                cmd = {"command": "READ"}
                ser.write((json.dumps(cmd) + "\n").encode())
                print(f"[SEND] {cmd}")
                time.sleep(0.2)  # キーバウンス対策
            
            if keyboard.is_pressed('q'):
                print("[DEBUG] 'q' pressed")
                break
            
            # シリアル受信
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                rx_buffer.extend(data)
                
                # 改行区切りでJSON解析
                while b"\n" in rx_buffer:
                    idx = rx_buffer.index(b"\n")
                    line = bytes(rx_buffer[:idx])
                    del rx_buffer[:idx+1]
                    
                    try:
                        msg = json.loads(line.decode())
                        
                        # センサーデータ受信
                        if "temp" in msg and "humi" in msg:
                            print(f"[RECV] temp={msg['temp']}, humi={msg['humi']}")
                            # OK応答
                            resp = {"RESP": "ok"}
                            ser.write((json.dumps(resp) + "\n").encode())
                            print(f"[SEND] {resp}")
                        
                        # COPYコマンド受信
                        elif msg.get("command") == "COPY":
                            print("command received: COPY")
                            resp = {"RESP": "ok"}
                            ser.write((json.dumps(resp) + "\n").encode())
                            print(f"[SEND] {resp}")
                        
                        # DELETEコマンド受信
                        elif msg.get("command") == "DELETE":
                            print("command received: DELETE")
                            resp = {"RESP": "ok"}
                            ser.write((json.dumps(resp) + "\n").encode())
                            print(f"[SEND] {resp}")
                        
                        # SHUTDOWNコマンド受信
                        elif msg.get("command") == "SHUTDOWN":
                            print("command received: SHUTDOWN")
                            resp = {"RESP": "OK"}
                            ser.write((json.dumps(resp) + "\n").encode())
                            print(f"[SEND] {resp}")
                        
                        else:
                            print(f"[RECV] {msg}")
                    
                    except json.JSONDecodeError:
                        print(f"[ERROR] Invalid JSON: {line.decode()}")
                    except Exception as e:
                        print(f"[ERROR] {e}")
            
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted")
    finally:
        ser.close()
        print("[INFO] Connection closed")

if __name__ == "__main__":
    main()
