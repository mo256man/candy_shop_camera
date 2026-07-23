type CommonFilterConditionProps = {
  className?: string;
  showFilter: boolean;
  onToggleFilter: () => void;
  onCloseFilter: () => void;
  filterUnknown: boolean;
  setFilterUnknown: (v: boolean) => void;
  filterShort: boolean;
  setFilterShort: (v: boolean) => void;
  hourOption: string;
  setHourOption: (v: string) => void;
};

export default function CommonFilterCondition({
  className,
  showFilter,
  onToggleFilter,
  onCloseFilter,
  filterUnknown,
  setFilterUnknown,
  filterShort,
  setFilterShort,
  hourOption,
  setHourOption,
}: CommonFilterConditionProps) {
  const resetCondition = () => {
    setFilterUnknown(true);
    setFilterShort(true);
  }

  const resetHourOption = () => {
    setHourOption("");
  }

  const filterOptions = () => {
    const options = [
      { value: "filterUnknown", label: "不詳を除く", checked: filterUnknown, onChange: (e: React.ChangeEvent<HTMLInputElement>) => setFilterUnknown(e.target.checked) },
      { value: "filterShort", label: "短時間を除く", checked: filterShort, onChange: (e: React.ChangeEvent<HTMLInputElement>) => setFilterShort(e.target.checked) },
    ];
    return (
      <div className="options">
        {options.map((option) => (
          <span key={option.value}>
            <input
              type="checkbox"
              id={option.value}
              name={option.value}
              checked={option.checked}
              onChange={option.onChange}
            />
            <label htmlFor={option.value}>{option.label}</label>
          </span>
        ))}
      </div>
    );
  }

  const hourOptions = () => {
    const options = [
      { value: "<7", label: "7時以前" },
      { value: "7", label: "7時" },
      { value: "8", label: "8時" },
      { value: "9", label: "9時" },
      { value: "10", label: "10時" },
      { value: "11", label: "11時" },
      { value: "12", label: "12時" },
      { value: "13", label: "13時" },
      { value: "14", label: "14時" },
      { value: "15", label: "15時" },
      { value: "16", label: "16時" },
      { value: "17", label: "17時" },
      { value: "18", label: "18時" },
      { value: "19", label: "19時" },
      { value: "20", label: "20時" },
      { value: ">21", label: "21時以降" },
    ];

    return (
      <div className="options">
        {options.map((option) => (
          <span key={option.value}>
            <input
              value={option.value}
              type="radio"
              id={`filterHour${option.value}`}
              name="filterHour"
              checked={hourOption === option.value}
              onChange={() => setHourOption(option.value)}
            />
            <label htmlFor={`filterHour${option.value}`}>{option.label}</label>
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className={`filter-container ${className ?? ""}`}>
      <div className="filter-icon" onClick={onToggleFilter}>🔍</div>
      {showFilter && (
        <div className="filterWrapper">
          <div className="filter-close-btn" onClick={onCloseFilter}>x</div>
          <div><b>検索条件</b></div>
          <button className="filter-reset-btn" onClick={resetCondition}>初期状態にリセット</button>
          {filterOptions()}
          <br />
          <div><b>時間帯</b></div>
          <button className="filter-reset-btn" onClick={resetHourOption}>全時間帯にリセット</button>
          {hourOptions()}
        </div>
      )}
    </div>
  );
}
