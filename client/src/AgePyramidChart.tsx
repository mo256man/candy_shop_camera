type Record = {
  datetime: string;
  duration: number;
  filename: string;
  gender: string;
  age: number;
};

interface AgeGroupStats {
  count: number;
  totalDuration: number;
}

export function agePyramidChart(
  records: Record[],
  analysisMode: "time" | "count"
): React.ReactNode {
  // 年齢層の定義（下が若い、上が年配）
  const ageGroups = [
    { key: "50plus", label: "50台以上", min: 50, max: 999 },
    { key: "40s", label: "40台", min: 40, max: 49 },
    { key: "30s", label: "30台", min: 30, max: 39 },
    { key: "20below", label: "20台以下", min: 0, max: 29 },
  ];

  // データ集約：男性と女性で分ける
  const maleStats: Record<string, AgeGroupStats> = {};
  const femaleStats: Record<string, AgeGroupStats> = {};

  ageGroups.forEach((group) => {
    maleStats[group.key] = { count: 0, totalDuration: 0 };
    femaleStats[group.key] = { count: 0, totalDuration: 0 };
  });

  for (const record of records) {
    if (record.gender === "NA" || !record.age || record.age === 0) {
      continue; // NA と年齢0を無視
    }

    const age = record.age;
    if (isNaN(age)) continue;

    const group = ageGroups.find((g) => age >= g.min && age <= g.max);
    if (!group) continue;

    if (record.gender === "M") {
      maleStats[group.key].count += 1;
      maleStats[group.key].totalDuration += record.duration;
    } else if (record.gender === "F") {
      femaleStats[group.key].count += 1;
      femaleStats[group.key].totalDuration += record.duration;
    }
  }

  const values = analysisMode === "count"
    ? { male: maleStats, female: femaleStats }
    : { male: maleStats, female: femaleStats };

  console.log("agePyramidChart", { maleStats, femaleStats });

  return createPyramidChart(ageGroups, values, analysisMode);
}

function createPyramidChart(
  ageGroups: { key: string; label: string }[],
  stats: {
    male: Record<string, AgeGroupStats>;
    female: Record<string, AgeGroupStats>;
  },
  analysisMode: "time" | "count"
): React.ReactNode {
  const width = 500;
  const height = 200;
  const centerX = width / 2;
  const margin = { top: 20, bottom: 20, left: 20, right: 20 };
  const chartHeight = height - margin.top - margin.bottom;
  const rowHeight = chartHeight / ageGroups.length;
  const labelWidth = 50;
  const halfLabelWidth = labelWidth / 2;
  const maxBarWidth = (width - margin.left - margin.right) / 2 - halfLabelWidth; // 年齢層ラベル用スペース  

  // 最大値を計算
  let maxValue = 0;
  ageGroups.forEach((group) => {
    const maleVal =
      analysisMode === "count"
        ? stats.male[group.key].count
        : stats.male[group.key].totalDuration;
    const femaleVal =
      analysisMode === "count"
        ? stats.female[group.key].count
        : stats.female[group.key].totalDuration;
    maxValue = Math.max(maxValue, maleVal, femaleVal);
  });
  
  const maleTotal = ageGroups.reduce((sum, g) => {
    return sum + (analysisMode === "count"
      ? stats.male[g.key].count
      : stats.male[g.key].totalDuration);
  }, 0);
  const femaleTotal = ageGroups.reduce((sum, g) => {
    return sum + (analysisMode === "count"
      ? stats.female[g.key].count
      : stats.female[g.key].totalDuration);
  }, 0);

  const rows = ageGroups.map((group, index) => {
    const maleVal =
      analysisMode === "count"
        ? stats.male[group.key].count
        : stats.male[group.key].totalDuration;
    const femaleVal =
      analysisMode === "count"
        ? stats.female[group.key].count
        : stats.female[group.key].totalDuration;

    const maleWidth = (maleVal / maxValue) * maxBarWidth;
    const femaleWidth = (femaleVal / maxValue) * maxBarWidth;

    const maleRatio = maleTotal > 0 ? (maleVal / maleTotal) * 100 : 0;
    const femaleRatio = femaleTotal > 0 ? (femaleVal / femaleTotal) * 100 : 0;

    const maleDisplay = `${analysisMode === "count" ? maleVal : Math.round(maleVal)}  (${maleRatio.toFixed(1)}%)`;
    const femaleDisplay = `${analysisMode === "count" ? femaleVal : Math.round(femaleVal)}  (${femaleRatio.toFixed(1)}%)`;

    const y = margin.top + index * rowHeight + rowHeight / 2;
    const maleX = centerX - halfLabelWidth - maleWidth; // 右寄り（中央から左）
    const femaleX = centerX + halfLabelWidth; // 左寄り（中央から右）
    const maleBarWidth = maleWidth;
    const femaleBarWidth = femaleWidth;

    return (
      <g key={`row-${group.key}`}>
        {/* 男性バー（左、右から左へ） */}
        <rect
          x={maleX}
          y={y - rowHeight / 4}
          width={maleBarWidth}
          height={rowHeight / 2}
          fill="#3b82f6"
        />
        <text
          x={maleX + maleBarWidth - 5}
          y={y + 4}
          fontSize="11"
          textAnchor="end"
          fill="#fff"
          fontWeight="bold"
        >
          {maleDisplay}
        </text>
        {/* 年齢層ラベル（中央） */}
        <text
          x={centerX}
          y={y + 4}
          fontSize="12"
          textAnchor="middle"
          fill="#374151"
          fontWeight="bold"
        >
          {group.label}
        </text>

        {/* 女性バー（右、左から右へ） */}
        <rect
          x={femaleX}
          y={y - rowHeight / 4}
          width={femaleBarWidth}
          height={rowHeight / 2}
          fill="#f97316"
        />
        <text
          x={femaleX + 5}
          y={y + 4}
          fontSize="11"
          fill="#fff"
          fontWeight="bold"
        >
          {femaleDisplay}
        </text>
      </g>
    );
  });

return (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={width}
    height={height}
    viewBox={`0 0 ${width} ${height}`}
    style={{ border: "1px solid #e5e7eb", marginBottom: "20px" }}
  >
    <rect width={width} height={height} fill="#ffffff" />
    {rows}
    {/* ラベル左右の縦線（グラフの0基準線） */}
    <line
      x1={centerX - halfLabelWidth}
      y1={margin.top}
      x2={centerX - halfLabelWidth}
      y2={height - margin.bottom}
      stroke="#374151"
      strokeWidth={1}
    />
    <line
      x1={centerX + halfLabelWidth}
      y1={margin.top}
      x2={centerX + halfLabelWidth}
      y2={height - margin.bottom}
      stroke="#374151"
      strokeWidth={1}
    />
  </svg>
);
}
