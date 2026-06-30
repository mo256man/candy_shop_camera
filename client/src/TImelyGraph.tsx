type InputItem = {
  datetime: string;
  length: number;
};

export function TimelyGraph({
  data,
  width = 1200,
  height = 600,
  analysisMode = "time",
}: {
  data: InputItem[];
  width?: number;
  height?: number;
  analysisMode?: "time" | "count";
}) {
  // バケット定義：0-7時(1), 7-21時の10分単位(84), 21-24時(1)
  const cols = 86;
  const buckets = new Array<number>(cols).fill(0);

  // 時刻からバケットインデックスと容量を計算
  const getBucketInfo = (hours: number, minutes: number, seconds: number) => {
    if (hours < 7) {
      // 0-7時：1つのバケット、容量は7時間
      const timeInBucket = hours * 3600 + minutes * 60 + seconds;
      const writable = 7 * 3600 - timeInBucket;
      return { bucketIndex: 0, bucketCapacity: 7 * 3600, writable };
    } else if (hours < 21) {
      // 7-21時：10分ごと、容量は600秒
      const bucketIndex = 1 + (hours - 7) * 6 + Math.floor(minutes / 10);
      const timeInBucket = (minutes % 10) * 60 + seconds;
      const writable = 600 - timeInBucket;
      return { bucketIndex, bucketCapacity: 600, writable };
    } else {
      // 21-24時：1つのバケット、容量は3時間
      const timeInBucket = (hours - 21) * 3600 + minutes * 60 + seconds;
      const writable = 3 * 3600 - timeInBucket;
      return { bucketIndex: 85, bucketCapacity: 3 * 3600, writable };
    }
  };

  for (const item of data) {
    if (analysisMode === "time") {
      // 利用時間別：時間を集約
      let remain = item.duration;
      let t = new Date(item.datetime).getTime() / 1000;

      while (remain > 0) {
        const d = new Date(t * 1000);
        const h = d.getHours();
        const m = d.getMinutes();
        const s = d.getSeconds();

        const { bucketIndex, writable } = getBucketInfo(h, m, s);
        const used = Math.min(remain, writable);

        if (bucketIndex >= 0 && bucketIndex < cols) {
          buckets[bucketIndex] += used;
        }

        t += used;
        remain -= used;
      }
    } else {
      // 利用回数別：回数を集約
      const d = new Date(item.datetime);
      const h = d.getHours();
      const m = d.getMinutes();
      const s = d.getSeconds();

      const { bucketIndex } = getBucketInfo(h, m, s);
      if (bucketIndex >= 0 && bucketIndex < cols) {
        buckets[bucketIndex] += 1;
      }
    }
  }

  const margin = { top: 20, right: 20, bottom: 40, left: 50 };
  const plotX = margin.left;
  const plotY = margin.top;
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const colW = plotW / cols;
  
  // 最大値を計算
  const rawMaxValue = Math.max(...buckets, 1);
  
  // 切りのいい数字に丸める関数
  const roundUpNicely = (value: number): number => {
    if (value === 0) return 0;
    const digits = Math.floor(Math.log10(value)) + 1;
    const divisor = Math.pow(10, Math.max(digits - 1, 1));
    return Math.ceil(value / divisor) * divisor;
  };
  
  const maxValue = roundUpNicely(rawMaxValue);

  // X軸ラベル位置の計算
  const getXAxisLabel = (bucketIndex: number) => {
    if (bucketIndex === 0) return "0";
    if (bucketIndex === 85) return "21";
    const hourOffset = Math.floor((bucketIndex - 1) / 6);
    const hour = 7 + hourOffset;
    return String(hour);
  };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
    >
      <rect width={width} height={height} fill="#ffffff" />

      {/* Background grid */}
      {Array.from({ length: cols }).map((_, i) => {
        const x = plotX + i * colW;
        // 0-7時と21-24時がグレー
        const bg = i === 0 || i === 85 ? "#e5e7eb" : "#ffffff";
        return (
          <rect
            key={`bg-${i}`}
            x={x}
            y={plotY}
            width={colW}
            height={plotH}
            fill={bg}
          />
        );
      })}

      {/* Y-axis gridlines and labels */}
      {Array.from({ length: Math.floor(maxValue / 120) + 1 }).map((_, i) => {
        const sec = i * 120;
        const y = plotY + plotH - (sec / maxValue) * plotH;
        return (
          <g key={`y-grid-${i}`}>
            <line
              x1={plotX}
              y1={y}
              x2={plotX + plotW}
              y2={y}
              stroke="#d1d5db"
              strokeWidth="1"
            />
            <text
              x={plotX - 6}
              y={y + 4}
              fontSize="10"
              textAnchor="end"
              fill="#374151"
            >
              {sec}
            </text>
          </g>
        );
      })}

      {/* X-axis gridlines and labels */}
      {Array.from({ length: cols }).map((_, i) => {
        // 0-7時、各時刻、21-24時でグリッド線を引く
        let drawGrid = i === 0 || i === 85;
        let showLabel = i === 0 || i === 85;
        
        if (i > 0 && i < 85) {
          // 7-21時の各時間の境界
          if ((i - 1) % 6 === 0) {
            drawGrid = true;
            showLabel = true;
          }
        }

        if (!drawGrid) return null;

        const x = plotX + i * colW;
        return (
          <g key={`x-grid-${i}`}>
            <line
              x1={x}
              y1={plotY}
              x2={x}
              y2={plotY + plotH}
              stroke="#9ca3af"
              strokeWidth="1"
            />
            {showLabel && (
              <text
                x={x + colW / 2}
                y={plotY + plotH + 14}
                fontSize="10"
                textAnchor="middle"
                fill="#374151"
              >
                {getXAxisLabel(i)}
              </text>
            )}
          </g>
        );
      })}

      {/* Data bars */}
      {Array.from({ length: cols }).map((_, i) => {
        const v = buckets[i];
        const hPx = (v / maxValue) * plotH;
        const x = plotX + i * colW + 0.5;
        const y = plotY + plotH - hPx;
        const w = Math.max(colW - 1, 0);
        
        return (
          <g key={`bar-${i}`}>
            <rect
              x={x}
              y={y}
              width={w}
              height={hPx}
              fill="#3b82f6"
            />
            {v > 0 && (
              <text
                x={x + w / 2}
                y={y - 5}
                fontSize="10"
                textAnchor="middle"
                fill="#374151"
                fontWeight="bold"
              >
                {Math.round(v)}
              </text>
            )}
          </g>
        );
      })}

      {/* Border */}
      <rect
        x={plotX}
        y={plotY}
        width={plotW}
        height={plotH}
        fill="none"
        stroke="#374151"
        strokeWidth="1"
      />
    </svg>
  );
}