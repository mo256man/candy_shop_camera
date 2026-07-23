import { useState, useEffect, useRef } from 'react'
import CommonDatePicker from './CommonDatePicker.tsx'
import CommonFilterCondition from './CommonFilterCondition.tsx'
import HeaderPanel from './HeaderPanel.tsx'
import { filterRecords } from './filterRecords.ts'
import "./Record.css"

type RecordProps = {
  cameraId: number;
  showTitle: () => void;
  showViewer: () => void;
  showAnalysis: () => void;
  showSetting: () => void;
  isAdmin: boolean;
  isRecording: boolean;
  handleIsRecording: (recording: boolean) => void;
  readyRecord: boolean;
  handleReadyRecord: (ready: boolean) => void;
  isManualRecording: boolean;
  handleIsManualRecording: (manualRecording: boolean) => void;
  handleDeleteRecord: (filename: string) => Promise<void>;
  records: Array<{ id: number; filename: string; datetime: string; age: number; gender: string; duration: number }>;
  date: Date;
  handleDateChange: (date: Date) => void;
  isRunning: boolean;
  isAscending: boolean;
  setIsAscending: (v: boolean) => void;
  filterUnknown: boolean;
  setFilterUnknown: (v: boolean) => void;
  filterShort: boolean;
  setFilterShort: (v: boolean) => void;
  hourOption: string;
  setHourOption: (v: string) => void;
};

export default function Record({ cameraId, showTitle, showViewer, showAnalysis, showSetting, isAdmin, isRecording, handleIsRecording, readyRecord, handleReadyRecord, isManualRecording, handleIsManualRecording, records, date, handleDateChange, handleDeleteRecord, isRunning, isAscending, setIsAscending, filterUnknown, setFilterUnknown, filterShort, setFilterShort, hourOption, setHourOption }: RecordProps) {
  const [selectedRecord, setSelectedRecord] = useState<{ id: number; filename: string; datetime: string } | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showFilter, setShowFilter] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null)
  const flaskBase = `http://${window.location.hostname}:5000`

  const reloadFeed = () => {
    if (imgRef.current) {
      imgRef.current.src = `${flaskBase}/api/video_feed?t=${Date.now()}`
    }
  }

  const deleteRecord = async (record: { filename: string; datetime: string }) => {
    await handleDeleteRecord(record.filename);
    handleDateChange(date);
    setSelectedRecord(null);
  }

  const downloadRecord = async (record: { filename: string }) => {
    const videoName = `${record.filename}.mp4`
    const a = document.createElement('a')
    a.href = `/output/video/${videoName}`
    a.download = videoName
    a.click()
  }

  const sortByDateString = (arr, key:string, isAscending: boolean) => {
    return [...arr].sort((a, b) =>
      isAscending
        ? a[key].localeCompare(b[key])
        : b[key].localeCompare(a[key])
    );
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
      title="データ確認画面"
      currentPage="record"
      showTitle={showTitle}
      showViewer={showViewer}
      showAnalysis={showAnalysis}
      showSetting={showSetting}
      isRunning={isRunning}
      isRecording={isRecording}
    />
  );


  const recordHeader = (
    <div className="recordHeader">
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
      <div className="recordDate">{date.toLocaleDateString("ja-JP")}</div>
      <div className="recordCount">{filteredRecords.length}件</div>
      <div onClick={() => setIsAscending(!isAscending)} className="sortBtn">
        {isAscending ? "▲ 昇順" : "▼ 降順"}
      </div>
    </div>
  );


  const recordList = () => {
    return (
      <div className="recordList">
        {sortByDateString(filteredRecords, "datetime", isAscending).map((record, idx) => {
          const filename: string = record.filename;
          const thumnailImg: string = `/output/thumbnail/${filename}.jpg`;
          const strTime: string = filename.split("_")[1].replace(/(..)(..)(..)/, "$1:$2:$3");
          const age: number = record.age;
          const gender: string = record.gender === "M" ? "男性" : record.gender === "F" ? "女性" : "不明";
          const duration: number = record.duration;
          return (
          <div key={idx}
            className={`recordItem ${selectedRecord?.filename === record.filename ? 'selected' : ''}`}
            onClick={() => setSelectedRecord(record)}>
            <div className="thumbnail">
              <img src={thumnailImg} />
            </div>
            <div>{strTime}</div>
            <div><span>{gender}</span> <span>{age}歳</span></div>
            <div>{duration} 秒</div>
            <div className="thumbnailBtnArea">
              <div className="recordSaveBtn" onClick={() => downloadRecord(record)}>💾</div>
              {isAdmin && <div className="recordDeleteBtn" onClick={() => deleteRecord(record)}>❌</div>}
            </div>
          </div>
        )})} 
      </div>
    );
  }

  const videoInfo = (
    <table className="videoInfo">
      <tbody>
        <tr>
          <td>日時</td>
          <td>{selectedRecord?.datetime}</td>
        </tr>
        <tr>
          <td>滞在時間</td>
          <td>{selectedRecord?.duration} 秒</td>
        </tr>
        <tr>
          <td>検出人物</td>
          <td>推定 {selectedRecord?.age} 歳（性別：{selectedRecord?.gender}）</td>
        </tr>
      </tbody>
    </table>
  );


  const videoViewer = () => {
    return (
      <div className="videoViewer">
        {selectedRecord && (
          <video
            key={selectedRecord.filename}
            className="viewer-video"
            controls
            autoPlay
            playsInline
          >
            <source
              src={`/output/video/${selectedRecord.filename}.mp4`}
              type="video/mp4"
            />
          </video>
        )}
      </div>
    );
  }


  const viewerArea = (
    <div className="viewerArea">
      {selectedRecord && videoInfo}
      {videoViewer()}
    </div>
  );

  const recordListArea = (
    <div className="recordListArea">
      {recordHeader}
      {recordList()}
    </div>
  );


  return (
    <>
      {headerPanel}
      <div className="recordMain">
        {viewerArea}
        {recordListArea}
      </div>
    </>
  );
}