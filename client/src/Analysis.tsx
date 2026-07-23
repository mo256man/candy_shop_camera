import { useState, useEffect, useRef } from 'react'
import { registerLocale } from "react-datepicker";
import ja from "date-fns/locale/ja";
import CommonDatePicker from "./CommonDatePicker"
import CommonFilterCondition from "./CommonFilterCondition"
import HeaderPanel from "./HeaderPanel.tsx"
import { TimelyGraph } from "./TImelyGraph"
import { genderRatioChart } from "./GenderRatioChart"
import {agePyramidChart} from "./AgePyramidChart"
import { filterRecords } from "./filterRecords"
import "react-datepicker/dist/react-datepicker.css"
import "./Analysis.css"

registerLocale("ja", ja);

type AnalysisProps = {
  isAdmin: boolean;
  cameraId: number | null;
  isRecording: boolean;
  showTitle: () => void;
  showViewer: () => void;
  showRecord: () => void;
  showSetting: () => void;
  handleDateChange: (d: Date) => void;
  records: Array<{ id: number; filename: string; datetime: string; age: number; gender: string; duration: number }>;
  date: Date;
  isRunning: boolean;
  filterUnknown: boolean;
  setFilterUnknown: (v: boolean) => void;
  filterShort: boolean;
  setFilterShort: (v: boolean) => void;
  hourOption: string;
  setHourOption: (v: string) => void;
};

export default function Analysis({ isAdmin, cameraId, isRecording, showTitle, showViewer, showRecord, showSetting, handleDateChange, records, date, isRunning, filterUnknown, setFilterUnknown, filterShort, setFilterShort, hourOption, setHourOption }: AnalysisProps) {
  const [analysisMode, setAnalysisMode] = useState<"time" | "count">("count");
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showFilter, setShowFilter] = useState(false);

  const changeAnalysisMode = (mode: "time" | "count") => {
    setAnalysisMode(mode);
  }

  const filteredRecords = filterRecords(records, filterUnknown, filterShort, hourOption);

  const toggleDatePicker = () => {
    setShowFilter(false);
    setShowDatePicker(!showDatePicker);
  }

  const toggleFilter = () => {
    setShowDatePicker(false);
    setShowFilter(!showFilter);
  }

  const headerPanel = (
    <HeaderPanel
      title="分析画面"
      currentPage="analysis"
      showTitle={showTitle}
      showViewer={showViewer}
      showRecord={showRecord}
      showSetting={showSetting}
      isRunning={isRunning}
      isRecording={isRecording}
    />
  );

  const analysisHeader = (
    <div className="analysisHeader">
      <div className="analysisHeaderLeft">
      <div className="datepicker-container">
        <div className="datepicker-icon" onClick={toggleDatePicker}>📅</div>
        {showDatePicker && (
          <div className="calendarWrapper">
            <div className="calendar-close-row">
              <div className="calendar-close-btn" onClick={() => setShowDatePicker(false)}>x</div>
            </div>
            <CommonDatePicker
              date={date}
              onChange={(d) => {
                handleDateChange(d);
                setShowDatePicker(false);
              }}
            />
          </div>
        )}
      </div>
      <CommonFilterCondition
        showFilter={showFilter}
        onToggleFilter={toggleFilter}
        onCloseFilter={() => setShowFilter(false)}
        filterUnknown={filterUnknown}
        setFilterUnknown={setFilterUnknown}
        filterShort={filterShort}
        setFilterShort={setFilterShort}
        hourOption={hourOption}
        setHourOption={setHourOption}
      />
      </div>
      <div className="analysisHeaderRight">
        <div className="recordDate">{date.toLocaleDateString("ja-JP")}</div>
      </div>
    </div>
  );


  const graph1 = () => {
    return (
      <div className="graphContainer">
        <div className="graphTitle">{analysisMode=== "count" ? "時間別利用回数（回）" : "時間別利用時間（秒）"}</div>
          <TimelyGraph data={filteredRecords} width={1000} height={200} analysisMode={analysisMode} />
      </div>
    );   
  }

  const graph2 = () => {
    return (
      <div className="graphContainer">
        <div className="graphTitle">{analysisMode === "count" ? "性別利用回数（回）" : "性別利用時間（秒）"}</div>
        {genderRatioChart(filteredRecords, analysisMode)}
      </div>
    );
  }

  const graph3 = () => {
    return (
      <div className="graphContainer">
        <div className="graphTitle">{analysisMode === "count" ? "年齢層別利用回数（回）" : "年齢層別利用時間（秒）"}</div>
        {agePyramidChart(filteredRecords, analysisMode)}
      </div>
    );
  }

  const analysisContent = () => {
    return (
      <div className="analysisContent">
        {analysisHeader}
        <div className="analysisModeBtns">
          <div className={`analysisModeBtn ${analysisMode === "count" ? "analysisModeBtn-active" : ""}`} onClick={()=> changeAnalysisMode("count")}>利用回数別</div>
          <div className={`analysisModeBtn ${analysisMode === "time" ? "analysisModeBtn-active" : ""}`} onClick={()=> changeAnalysisMode("time")}>利用時間別</div>
        </div>
        <div className="graph">{graph1()}</div>
        <div style={{ display: "flex", flexDirection: "row" }}>
          <div className="graph">{graph2()}</div>
          <div className="graph">{graph3()}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="analysisMain">
      {headerPanel}
      {analysisContent()}
    </div>
  );

}
