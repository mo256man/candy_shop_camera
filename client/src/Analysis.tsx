import { useState, useEffect, useRef } from 'react'
import { registerLocale } from "react-datepicker";
import ja from "date-fns/locale/ja";
import CommonDatePicker from "./CommonDatePicker"
import { TimelyGraph } from "./TImelyGraph"
import { genderRatioChart } from "./GenderRatioChart"
import {agePyramidChart} from "./AgePyramidChart"
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
  handleDateChange: (d: Date) => void;
  records: Array<{ id: number; filename: string; datetime: string; age: number; gender: string; duration: number }>;
  date: Date;
  isRunning: boolean;
};

export default function Analysis({ isAdmin, cameraId, isRecording, showTitle, showViewer, showRecord, handleDateChange, records, date, isRunning }: AnalysisProps) {
  const [analysisMode, setAnalysisMode] = useState<"time" | "count">("time");
  const [showDatePicker, setShowDatePicker] = useState(false);

  const changeAnalysisMode = (mode: "time" | "count") => {
    setAnalysisMode(mode);
  }

  const headerPanel = (
    <div className="header">
      <div className="header-left">
        <div className="header-icon" onClick={() => showTitle()}>🔙</div>
      </div>
      <div className="header-center">
        <div className="header-title">お菓子屋さんカメラ 分析画面</div>
      </div>
      <div className="header-right">
        <div className="cameraControlPanel">
          {isRecording && <div className="recordingIcon">録画中 ●</div>}
          {isRunning ?
            <div className="header-icon" onClick={() => showViewer()}>📷</div>
          :
            <div className="header-icon-disabled">📷</div>
          }
          <div className="header-icon" onClick={() => showRecord()}>👀</div>
          <div className="header-icon-selected" >📊</div>
        </div>
      </div>
    </div>
  );

  const analysisHeader = (
    <div className="analysisHeader">
      <div className="analysisHeaderLeft">
      <div className="datepicker-container">
        <div className="datepicker-icon" onClick={() => setShowDatePicker(!showDatePicker)}>📅</div>
        {showDatePicker && (
          <div className="calendarWrapper">
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
      </div>
      <div className="analysisHeaderRight">
        <div>選択された日付：{date.toLocaleDateString("ja-JP")}</div>
      </div>
    </div>
  );


  const graph1 = () => {
    return (
      <div className="graphContainer">
        <div className="graphTitle">{analysisMode=== "count" ? "時間別利用回数（回）" : "時間別利用時間（秒）"}</div>
          <TimelyGraph data={records} width={1000} height={200} analysisMode={analysisMode} />
      </div>
    );   
  }

  const graph2 = () => {
    return (
      <div className="graphContainer">
        <div className="graphTitle">{analysisMode === "count" ? "性別利用回数（回）" : "性別利用時間（秒）"}</div>
        {genderRatioChart(records, analysisMode)}
      </div>
    );
  }

  const graph3 = () => {
    return (
      <div className="graphContainer">
        <div className="graphTitle">{analysisMode === "count" ? "年齢層別利用回数（回）" : "年齢層別利用時間（秒）"}</div>
        {agePyramidChart(records, analysisMode)}
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
