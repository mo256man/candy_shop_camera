type InputItem = {
  datetime: string;
  duration: number;
  gender: string;
};

type CameraRecord = {
  datetime: string;
  duration: number;
  filename: string;
  gender: string;
  age: number;
};

export function genderRatioChart(
  records: CameraRecord[],
  analysisMode: "time" | "count"
): React.ReactNode {
  const categoryMap = {
    "M": { key: "M", label: "男性", color: "#3b82f6" },
    "NA": { key: "NA", label: "不明", color: "#9ca3af" },
    "F": { key: "F", label: "女性", color: "#f97316" },
  };

  // 性別ごとにデータを集約
  const genderStats = {
    M: { count: 0, totalDuration: 0 },
    NA: { count: 0, totalDuration: 0 },
    F: { count: 0, totalDuration: 0 },
  };

  for (const record of records) {
    const sex = (record.gender === "M" || record.gender === "F" || record.gender === "NA") ? record.gender : "NA";
    genderStats[sex].count += 1;
    genderStats[sex].totalDuration += record.duration;
  }

  console.log("genderStats:", genderStats);

  // 順番: 女性・不明・男性
  const keys = ["F", "NA", "M"] as const;

  if (analysisMode === "count") {
    const data = keys.map((k) => ({ key: k, value: genderStats[k].count }));
    return createPieChart(categoryMap, data, (v) => String(Math.round(v)));
  } else {
    const data = keys.map((k) => ({ key: k, value: genderStats[k].totalDuration }));
    return createPieChart(categoryMap, data, (v) => (Math.round(v * 10) / 10).toFixed(1));
  }
}

function createPieChart(
  categoryMap: { [key: string]: { key: string; label: string; color: string } },
  data: { key: string; value: number }[],
  formatValue: (v: number) => string = (v) => String(v)
): React.ReactNode {
  const width = 260;
  const height = 260;
  const cx = 130;
  const cy = 130;
  const r = 105;

  const total = data.reduce((sum, d) => sum + d.value, 0);

  if (total === 0) {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="gender-ratio-chart">
        <rect width={width} height={height} fill="#ffffff" />
        <circle cx={cx} cy={cy} r={r} fill="#e5e7eb" />
        <text x={cx} y={cy + 5} fontSize="13" textAnchor="middle" fill="#9ca3af">データなし</text>
      </svg>
    );
  }

  const sectors: React.ReactNode[] = [];
  const labels: React.ReactNode[] = [];
  let startAngle = -Math.PI / 2;

  for (const d of data) {
    const category = categoryMap[d.key];
    const percentage = total > 0 ? d.value / total : 0;
    if (percentage <= 0) {
      continue;
    }
    const angle = percentage * 2 * Math.PI;
    const endAngle = startAngle + angle;

    // 100%の場合: arcは始点=終点になり描画不能なのでcircleで描く
    if (percentage >= 1) {
      sectors.push(
        <circle key={`sector-${d.key}`} cx={cx} cy={cy} r={r} fill={category.color} stroke="#fff" strokeWidth="2" />
      );
      labels.push(
        <g key={`label-${d.key}`}>
          <text x={cx} y={cy - 6} fontSize="12" fontWeight="bold" textAnchor="middle" fill="#fff">
            {formatValue(d.value)}
          </text>
          <text x={cx} y={cy + 10} fontSize="11" textAnchor="middle" fill="#fff">
            100%
          </text>
        </g>
      );
      startAngle = endAngle;
      continue;
    }

    const x1 = cx + r * Math.cos(startAngle);
    const y1 = cy + r * Math.sin(startAngle);
    const x2 = cx + r * Math.cos(endAngle);
    const y2 = cy + r * Math.sin(endAngle);
    const largeArc = angle > Math.PI ? 1 : 0;

    sectors.push(
      <path
        key={`sector-${d.key}`}
        d={`M ${cx} ${cy} L ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${largeArc} 1 ${x2.toFixed(2)} ${y2.toFixed(2)} Z`}
        fill={category.color}
        stroke="#fff"
        strokeWidth="2"
      />
    );

    if (percentage >= 0.05) {
      const midAngle = startAngle + angle / 2;
      const labelR = r * 0.65;
      const lx = cx + labelR * Math.cos(midAngle);
      const ly = cy + labelR * Math.sin(midAngle);
      labels.push(
        <g key={`label-${d.key}`}>
          <text x={lx.toFixed(2)} y={(ly - 6).toFixed(2)} fontSize="12" fontWeight="bold" textAnchor="middle" fill="#fff">
            {formatValue(d.value)}
          </text>
          <text x={lx.toFixed(2)} y={(ly + 10).toFixed(2)} fontSize="11" textAnchor="middle" fill="#fff">
            {(percentage * 100).toFixed(1)}%
          </text>
        </g>
      );
    }

    startAngle = endAngle;
  }

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="gender-ratio-chart"
    >
      <rect width={width} height={height} fill="#ffffff" />
      {sectors}
      {labels}
    </svg>
  );
}


export function buildSexRatioSvg(
  data: InputItem[],
  width = 900,
  height = 180
): string {
  const categories = [
    { key: "M", label: "男性", color: "lightblue" },
    { key: "NA", label: "不明", color: "gray" },
    { key: "F", label: "女性", color: "pink" },
  ] as const;

  const countMap: { [key: string]: number } = { M: 0, NA: 0, F: 0 };
  const durationMap: { [key: string]: number } = { M: 0, NA: 0, F: 0 };

  for (const item of data) {
    const key = item.gender === "M" || item.gender === "F" || item.gender === "NA" ? item.gender : "NA";
    countMap[key] += 1;
    durationMap[key] += item.duration;
  }

  const totalCount = countMap.M + countMap.NA + countMap.F;
  const totalDuration = durationMap.M + durationMap.NA + durationMap.F;

  const countPct = categories.map(c =>
    totalCount > 0 ? (countMap[c.key] / totalCount) * 100 : 0
  );
  const durationPct = categories.map(c =>
    totalDuration > 0 ? (durationMap[c.key] / totalDuration) * 100 : 0
  );

  const margin = { top: 20, right: 20, bottom: 20, left: 80 };
  const labelW = 90;
  const barX = margin.left + labelW;
  const barW = width - barX - margin.right;
  const barH = 36;
  const gap = 36;

  const row1Y = margin.top;
  const row2Y = row1Y + barH + gap;

  const esc = (s: string) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const buildRow = (y: number, title: string, pcts: number[]) => {
    let x = barX;
    let out = "";

    out += `<text x="${margin.left + labelW - 10}" y="${y + barH / 2 + 5}" font-size="16" text-anchor="end" fill="#111">${esc(title)}</text>`;
    out += `<rect x="${barX}" y="${y}" width="${barW}" height="${barH}" fill="none" stroke="#333" stroke-width="1"/>`;

    for (let i = 0; i < categories.length; i++) {
      const pct = pcts[i];
      const segW = (pct / 100) * barW;
      const cx = x + segW / 2;
      const label = `${categories[i].label} ${Math.round(pct)}%`;

      if (segW > 0) {
        out += `<rect x="${x}" y="${y}" width="${segW}" height="${barH}" fill="${categories[i].color}"/>`;
        out += `<text x="${cx}" y="${y + barH / 2 + 5}" font-size="14" text-anchor="middle" fill="#111">${esc(label)}</text>`;
      }

      x += segW;
    }

    return out;
  };

  let svg = "";
  svg += `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;
  svg += `<rect width="${width}" height="${height}" fill="white"/>`;

  svg += buildRow(row1Y, "件数比", countPct);
  svg += buildRow(row2Y, "時間比", durationPct);

  svg += `<text x="${barX}" y="${height - 6}" font-size="12" text-anchor="start" fill="#333">0%</text>`;
  svg += `<text x="${barX + barW}" y="${height - 6}" font-size="12" text-anchor="end" fill="#333">100%</text>`;

  svg += `</svg>`;
  return svg;
}

