// components/CommonDatePicker.tsx
import { useState, useEffect } from "react";
import DatePicker from "react-datepicker";
import { registerLocale } from "react-datepicker";
import ja from "date-fns/locale/ja";
import "react-datepicker/dist/react-datepicker.css";


registerLocale("ja", ja);

type CommonDatePickerProps = {
  date: Date;
  onChange: (date: Date) => void;
  className?: string;
};

// Date を "YYYY-MM-DD"（ローカルタイム）に変換
function toDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export default function CommonDatePicker({
  date,
  onChange,
  className,
}: CommonDatePickerProps) {
  // データが存在する日付（"YYYY-MM-DD"）の集合
  const [markedDates, setMarkedDates] = useState<Set<string>>(new Set());

  // 指定した月（表示中の月）にデータがある日付を取得する
  const fetchMarkedDates = async (viewDate: Date) => {
    const monthStr = `${viewDate.getFullYear()}-${String(
      viewDate.getMonth() + 1
    ).padStart(2, "0")}`;
    try {
      const res = await fetch("/api/get_record_dates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ month: monthStr }),
      });
      const data = await res.json();
      setMarkedDates(new Set<string>(data.dates ?? []));
    } catch (error) {
      console.error("Error fetching record dates:", error);
    }
  };

  // カレンダー表示前（マウント時）に、選択中の月のデータ有り日付を取得
  useEffect(() => {
    fetchMarkedDates(date);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={className}>
      <DatePicker
        inline
        dateFormat="yyyy/MM/dd"
        locale="ja"
        onMonthChange={(d) => fetchMarkedDates(d)}
        dayClassName={(d) =>
          markedDates.has(toDateKey(d)) ? "datepicker-has-data" : ""
        }
        renderCustomHeader={({ date, decreaseMonth, increaseMonth }) => (
          <div className="datepicker-header">
            <button type="button" onClick={decreaseMonth}>◀</button>
            <span>{`${date.getFullYear()}年${date.getMonth() + 1}月`}</span>
            <button type="button" onClick={increaseMonth}>▶</button>
          </div>
        )}
        selected={date}
        onChange={(d) => {
          if (d) onChange(d);
        }}
      />
    </div>
  );
}