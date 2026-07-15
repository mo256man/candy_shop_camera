import { useState, useEffect, useRef } from 'react'
import { registerLocale } from "react-datepicker";
import ja from "date-fns/locale/ja";
import CommonDatePicker from "./CommonDatePicker"
import { createEnvironmentGraphs } from "./EnvironmentGraph"
import "react-datepicker/dist/react-datepicker.css"
import "./Analysis.css"

registerLocale("ja", ja);

type EnvironmentProps = {
  isAdmin: boolean;
  cameraId: number | null;
  isRecording: boolean;
  showTitle: () => void;
  showViewer: () => void;
  showRecord: () => void;
  showAnalysis: () => void;
  showEnvironment: () => void;
  handleDateChange: (d: Date) => void;
  records: Array<{ id: number; filename: string; datetime: string; age: number; gender: string; duration: number }>;
  date: Date;
  isRunning: boolean;
};

export default function Environment({ isAdmin, cameraId, isRecording, showTitle, showViewer, showRecord, showAnalysis, showEnvironment, handleDateChange, records, date, isRunning }: EnvironmentProps) {
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [envRecords, setEnvRecords] = useState<Array<{ datetime: string; temperature: number; humidity: number }>>([]);

  const getEnvironmentRecords = async (d: Date) => {
    const strDate = d.toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
    try {
      const res = await fetch("/api/get_environment_records", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: strDate })
      });
      const data = await res.json();
      setEnvRecords(data.records);
    } catch (error) {
      console.error("Error fetching environment records:", error);
    }
  };

  useEffect(() => {
    getEnvironmentRecords(date);
  }, [date]);

  const { temperatureGraph, humidityGraph } = createEnvironmentGraphs(envRecords, 1000, 200);

  const headerPanel = (
    <div className="header">
      <div className="header-left">
        <div className="header-icon" onClick={() => showTitle()}>🔙</div>
      </div>
      <div className="header-center">
        <div className="header-title">環境画面<span style={{ color: "red" }}>（データはウソ）</span></div>
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
          <div className="header-icon" onClick={() => showAnalysis()}>📊</div>
          <div className="header-icon-selected">🌿</div>
        </div>
      </div>
    </div>
  );

  const environmentHeader = (
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
        <div className="recordDate">{date.toLocaleDateString("ja-JP")}</div>
      </div>
    </div>
  );


  const graph1 = () => {
    return (
      <div className="graphContainer">
        <div className="graphTitle">気温</div>
        {temperatureGraph}
      </div>
    );   
  }

  const graph2 = () => {
    return (
      <div className="graphContainer">
        <div className="graphTitle">湿度</div>
        {humidityGraph}
      </div>
    );
  }


  const environmentContent = () => {
    return (
      <div className="analysisContent">
        {environmentHeader}
        <div className="graph">{graph1()}</div>
        <div className="graph">{graph2()}</div>
      </div>
    );
  }

  return (
    <div className="environmentMain">
      {headerPanel}
      {environmentContent()}
    </div>
  );

}
