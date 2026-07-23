type DiskUsageBarChartProps = {
  totalGb: number;
  freeGb: number;
  usedGb: number;
  folderGb: number;
  width?: number;
  height?: number;
};

export default function DiskUsageBarChart({
  totalGb,
  freeGb,
  usedGb,
  folderGb,
  width = 900,
  height = 70,
}: DiskUsageBarChartProps) {
  const topMargin = 18;
  const svgHeight = height + topMargin;

  if (totalGb <= 0) {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width={width} height={svgHeight} viewBox={`0 0 ${width} ${svgHeight}`} className="disk-usage-bar-chart">
        <text x={2} y={topMargin - 4} fontSize="12" textAnchor="start" fill="#6b7280">0%</text>
        <text x={width - 2} y={topMargin - 4} fontSize="12" textAnchor="end" fill="#6b7280">100%</text>
        <rect y={topMargin} width={width} height={height} fill="#e5e7eb" />
        <text x={width / 2} y={topMargin + height / 2 + 5} fontSize="13" textAnchor="middle" fill="#9ca3af">データなし</text>
      </svg>
    );
  }

  const otherUsedGb = Math.max(usedGb - folderGb, 0);
  const clampedFreeGb = Math.max(freeGb, 0);

  const labelPadding = 8;

  const segments = [
    { key: "folder", label: "録画データ", value: folderGb, color: "#B22222", anchor: "start" as const },
    { key: "otherUsed", label: "その他使用領域", value: otherUsedGb, color: "#FF8C00", anchor: "middle" as const },
    { key: "free", label: "空き容量", value: clampedFreeGb, color: "#191970", anchor: "end" as const },
  ];

  let x = 0;
  const bars: React.ReactNode[] = [];
  const labels: React.ReactNode[] = [];

  for (const seg of segments) {
    const ratio = seg.value / totalGb;
    const segWidth = ratio * width;

    if (segWidth > 0) {
      bars.push(
        <rect
          key={`bar-${seg.key}`}
          x={x}
          y={topMargin}
          width={segWidth}
          height={height}
          fill={seg.color}
          stroke="#fff"
          strokeWidth="1"
        />
      );

      // ラベル表示：folderはグラフ全体の左寄せ、freeは右寄せ、otherUsedは自セグメント中央
      let labelX: number;
      if (seg.anchor === "start") {
        labelX = labelPadding;
      } else if (seg.anchor === "end") {
        labelX = width - labelPadding;
      } else {
        labelX = x + segWidth / 2;
      }
      labels.push(
        <g key={`label-${seg.key}`}>
          <text x={labelX} y={topMargin + 20} fontSize="16" textAnchor={seg.anchor} fill="#fff">
            {seg.label}
          </text>
          <text x={labelX} y={topMargin + 40} fontSize="18" fontWeight="bold" textAnchor={seg.anchor} fill="#fff">
            {seg.value.toFixed(1)} GB
          </text>
          <text x={labelX} y={topMargin + 60} fontSize="18" textAnchor={seg.anchor} fill="#fff">
            {(ratio * 100).toFixed(1)}%
          </text>
        </g>
      );
    }

    x += segWidth;
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={width}
      height={svgHeight}
      viewBox={`0 0 ${width} ${svgHeight}`}
      className="disk-usage-bar-chart"
    >
      <text x={2} y={topMargin - 4} fontSize="12" textAnchor="start" fill="#6b7280">0%</text>
      <text x={width - 2} y={topMargin - 4} fontSize="12" textAnchor="end" fill="#6b7280">100%</text>
      <rect y={topMargin} width={width} height={height} fill="#ffffff" />
      {bars}
      {labels}
    </svg>
  );
}
