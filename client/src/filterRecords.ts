export type RecordItem = {
  id: number;
  filename: string;
  datetime: string;
  age: number;
  gender: string;
  duration: number;
};

// filename は "YYYYMMDD_HHMMSS_..." 形式のため、時刻部分の先頭2桁から時間を取得する
function getRecordHour(record: RecordItem): number {
  const timePart = record.filename.split("_")[1];
  return parseInt(timePart.substring(0, 2), 10);
}

function matchesHourOption(hour: number, hourOption: string): boolean {
  if (!hourOption) return true;
  if (hourOption === "<7") return hour < 7;
  if (hourOption === ">21") return hour >= 21;
  return hour === parseInt(hourOption, 10);
}

export function filterRecords<T extends RecordItem>(
  records: T[],
  filterUnknown: boolean,
  filterShort: boolean,
  hourOption: string
): T[] {
  return records.filter((record) => {
    if (filterUnknown && record.gender === "NA") return false;
    if (filterShort && record.duration < 5) return false;
    if (!matchesHourOption(getRecordHour(record), hourOption)) return false;
    return true;
  });
}
