// components/CommonDatePicker.tsx
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

export default function CommonDatePicker({
  date,
  onChange,
  className,
}: CommonDatePickerProps) {
  return (
    <div className={className}>
      <DatePicker
        inline
        dateFormat="yyyy/MM/dd"
        locale="ja"
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