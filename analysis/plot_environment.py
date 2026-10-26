import sqlite3
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_environment.sqlite")

# 日本語フォントを自動選択（見つかったものを使用）
_candidates = ["Yu Gothic", "Meiryo", "MS Gothic", "IPAexGothic", "Noto Sans CJK JP", "Noto Sans JP"]
_available = {f.name for f in fm.fontManager.ttflist}
for _name in _candidates:
    if _name in _available:
        plt.rcParams["font.family"] = _name
        break
plt.rcParams["axes.unicode_minus"] = False

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT datetime, temperature, humidity, pressure FROM environment ORDER BY datetime")
rows = cur.fetchall()
conn.close()

dates = [datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") for row in rows]
print(f"取得件数: {len(rows)}")
if dates:
    print(f"datetime 最小値: {min(dates)}")
    print(f"datetime 最大値: {max(dates)}")

# NULL（None）は NaN に変換し、欠測として線を途切れさせる
temperature = np.array([r[1] if r[1] is not None else np.nan for r in rows], dtype=float)
humidity = np.array([r[2] if r[2] is not None else np.nan for r in rows], dtype=float)
pressure = np.array([r[3] if r[3] is not None else np.nan for r in rows], dtype=float)


def set_ylim_from_data(ax, data, margin_ratio=0.05):
    valid = data[~np.isnan(data)]
    if valid.size == 0:
        return
    vmin, vmax = valid.min(), valid.max()
    if vmin == vmax:
        vmin -= 1
        vmax += 1
    margin = (vmax - vmin) * margin_ratio
    ax.set_ylim(vmin - margin, vmax + margin)


fig, axes = plt.subplots(3, 1, figsize=(6, 6), sharex=True)

axes[0].plot(dates, temperature, color="tab:red")
axes[0].set_ylabel("温度 (℃)")
axes[0].grid(True)
set_ylim_from_data(axes[0], temperature)

axes[1].plot(dates, humidity, color="tab:blue")
axes[1].set_ylabel("湿度 (%)")
axes[1].grid(True)
set_ylim_from_data(axes[1], humidity)

axes[2].plot(dates, pressure, color="tab:green")
axes[2].set_ylabel("気圧 (hPa)")
axes[2].grid(True)
set_ylim_from_data(axes[2], pressure)

# X軸範囲は、いずれかの列がNaNであっても全datetimeの実データ範囲に固定する
# (matplotlibはY値がNaNの点を自動スケール計算から除外するため、明示的に設定する)
if dates:
    x_min = mdates.date2num(dates[0])
    x_max = mdates.date2num(dates[-1])
    margin = (x_max - x_min) * 0.02 if x_max > x_min else 0.5
    axes[0].set_xlim(x_min - margin, x_max + margin)

axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
fig.autofmt_xdate()

plt.tight_layout()
plt.savefig("environment_plot.png", dpi=150)
plt.show()
