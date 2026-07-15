type EnvItem = {
  datetime: string;
  temperature: number;
  humidity: number;
};

// 縦軸の固定範囲
const VALUE_RANGE: Record<"temperature" | "humidity", { min: number; max: number }> = {
  temperature: { min: 10, max: 40 },
  humidity: { min: 0, max: 100 },
};

const getMinutesOfDay = (dtStr: string): number => {
  const d = new Date(dtStr.replace(" ", "T"));
  return d.getHours() * 60 + d.getMinutes() + d.getSeconds() / 60;
};

function renderLineGraph(
  data: EnvItem[],
  valueKey: "temperature" | "humidity",
  width: number,
  height: number,
  color: string,
  unit: string
) {
  const margin = { top: 20, right: 20, bottom: 40, left: 50 };
  const plotX = margin.left;
  const plotY = margin.top;
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  // 0時から24時まで（分単位）
  const totalMinutes = 24 * 60;

  const points = data
    .map((item) => ({ x: getMinutesOfDay(item.datetime), y: item[valueKey] }))
    .sort((a, b) => a.x - b.x);

  const { min: minValue, max: maxValue } = VALUE_RANGE[valueKey];
  const valueRange = maxValue - minValue;

  const xScale = (minutes: number) => plotX + (minutes / totalMinutes) * plotW;
  const yScale = (value: number) => plotY + plotH - ((value - minValue) / valueRange) * plotH;

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xScale(p.x).toFixed(1)} ${yScale(p.y).toFixed(1)}`)
    .join(" ");

  // Y軸目盛（5分割）
  const yTicks = 5;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
    >
      <rect width={width} height={height} fill="#ffffff" />

      {/* X軸：1時間ごとの主目盛、10分ごとの副目盛 */}
      {Array.from({ length: 25 }).map((_, hour) => {
        const x = xScale(hour * 60);
        return (
          <g key={`hour-${hour}`}>
            <line x1={x} y1={plotY} x2={x} y2={plotY + plotH} stroke="#9ca3af" strokeWidth="1" />
            <text x={x} y={plotY + plotH + 14} fontSize="16" textAnchor="middle" fill="#374151">
              {hour}
            </text>
            {hour < 24 &&
              Array.from({ length: 5 }).map((_, sub) => {
                const minorX = xScale(hour * 60 + (sub + 1) * 10);
                return (
                  <line
                    key={`minor-${hour}-${sub}`}
                    x1={minorX}
                    y1={plotY}
                    x2={minorX}
                    y2={plotY + plotH}
                    stroke="#e5e7eb"
                    strokeWidth="1"
                  />
                );
              })}
          </g>
        );
      })}

      {/* Y軸目盛 */}
      {Array.from({ length: yTicks + 1 }).map((_, i) => {
        const value = minValue + (valueRange / yTicks) * i;
        const y = yScale(value);
        return (
          <g key={`y-grid-${i}`}>
            <line x1={plotX} y1={y} x2={plotX + plotW} y2={y} stroke="#d1d5db" strokeWidth="1" />
            <text x={plotX - 6} y={y + 4} fontSize="16" textAnchor="end" fill="#374151">
              {value.toFixed(1)}
            </text>
          </g>
        );
      })}

      {/* 折れ線 */}
      {points.length > 0 && <path d={linePath} fill="none" stroke={color} strokeWidth="2" />}

      {/* データ点 */}
      {points.map((p, i) => (
        <circle key={`pt-${i}`} cx={xScale(p.x)} cy={yScale(p.y)} r="2" fill={color} />
      ))}

      <text x={plotX} y={14} fontSize="16" fill="#374151">
        単位: {unit}
      </text>
    </svg>
  );
}

// 温度・湿度の折れ線グラフを1回の呼び出しでまとめて生成する
export function createEnvironmentGraphs(
  data: EnvItem[],
  width = 1000,
  height = 300
): { temperatureGraph: React.ReactNode; humidityGraph: React.ReactNode } {
  return {
    temperatureGraph: renderLineGraph(data, "temperature", width, height, "#ef4444", "℃"),
    humidityGraph: renderLineGraph(data, "humidity", width, height, "#3b82f6", "%"),
  };
}
