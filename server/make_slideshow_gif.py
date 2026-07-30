import os
import glob
from datetime import datetime, timedelta
from PIL import Image
import numpy as np
import cv2

BASE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(BASE, "..", "snapshot")
PATTERN = "*.jpg"
INTERVAL = timedelta(hours=1)
OUTPUT = "output.gif"
DURATION_MS = 200

is_trim = False
TRIM_X0, TRIM_Y0 = 490, 520
TRIM_W, TRIM_H = 400, 200
SCALE = 0.5

TEXT_ORG = (10, 30)
TEXT_FONT = cv2.FONT_HERSHEY_SIMPLEX
TEXT_SCALE = 0.6
TEXT_COLOR = (255, 255, 255)
TEXT_THICKNESS = 1

files = {}
for path in glob.glob(os.path.join(FOLDER, PATTERN)):
    name = os.path.splitext(os.path.basename(path))[0]
    try:
        dt = datetime.strptime(name, "%Y%m%d_%H%M%S")
    except ValueError:
        continue
    files[dt] = path

if not files:
    raise SystemExit("対象の画像がありません")

first = min(files)
last = max(files)

size = Image.open(files[first]).size

def put_timestamp(img, t):
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    cv2.putText(arr, t.strftime("%Y-%m-%d %H:%M:%S"),
                TEXT_ORG, TEXT_FONT, TEXT_SCALE,
                TEXT_COLOR, TEXT_THICKNESS, cv2.LINE_AA)
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

def process(img, t):
    if is_trim:
        cropped = img.crop((TRIM_X0, TRIM_Y0, TRIM_X0 + TRIM_W, TRIM_Y0 + TRIM_H))
        return put_timestamp(cropped, t)
    else:
        return img.resize((int(img.width * SCALE), int(img.height * SCALE)))

if is_trim:
    black_size = (TRIM_W, TRIM_H)
else:
    black_size = (int(size[0] * SCALE), int(size[1] * SCALE))

frames = []
t = first
while t <= last:
    if t in files:
        frames.append(process(Image.open(files[t]).convert("RGB"), t))
    else:
        black = Image.new("RGB", black_size, (0, 0, 0))
        if is_trim:
            black = put_timestamp(black, t)
        frames.append(black)
    t += INTERVAL

frames[0].save(
    OUTPUT,
    save_all=True,
    append_images=frames[1:],
    duration=DURATION_MS,
    optimize=True,
    # loop=0,
)

print("done.")