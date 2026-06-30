import { useState, useEffect, useRef } from 'react'
import CommonDatePicker from './CommonDatePicker.tsx'
import "./Record.css"

type RecordProps = {
  cameraId: number;
  showTitle: () => void;
  showViewer: () => void;
  showAnalysis: () => void;
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
};

export default function Record({ cameraId, showTitle, showViewer, showAnalysis, isAdmin, isRecording, handleIsRecording, readyRecord, handleReadyRecord, isManualRecording, handleIsManualRecording, records, date, handleDateChange, handleDeleteRecord, isRunning, isAscending, setIsAscending }: RecordProps) {
  const [selectedRecord, setSelectedRecord] = useState<{ id: number; filename: string; datetime: string } | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
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
    a.href = `/output/${videoName}`
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

  const headerPanel = (
    <div className="header">
      <div className="header-left">
        <div className="header-icon" onClick={() => showTitle()}>🔙</div>
      </div>
      <div className="header-center">
        <div className="header-title">お菓子屋さんカメラ データ確認画面</div>
      </div>
      <div className="header-right">
        <div className="cameraControlPanel">
          {isRecording && <div className="recordingIcon">録画中 ●</div>}
          {isRunning ?
            <>
            {/* <div className="pictureInPicture">
              <img src={`${flaskBase}/api/video_feed`} ref={imgRef} alt="video_feed"
                onError={() => { setTimeout(reloadFeed, 2000) }}/>
            </div> */}
            <div className="header-icon" onClick={() => showViewer()}>📷</div>
          </>
          :
            <div className="header-icon-disabled">📷</div>
          }
          <div className="header-icon-selected" >👀</div>
          <div className="header-icon" onClick={() => showAnalysis()}>📊</div>
        </div>
      </div>
    </div>
  );




  const recordViewer = () => {
    return (
      <div className="recordViewer">
        <div>recordViewer</div>
      </div>
    );
  }

  const recordHeader = (
    <div className="recordHeader">
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
      <div>選択された日付：{date.toLocaleDateString("ja-JP")}</div>
      <div>データ件数：{records.length}件</div>
      <div onClick={() => setIsAscending(!isAscending)} className="sortBtn">
        {isAscending ? "▲ 昇順" : "▼ 降順"}
      </div>
    </div>
  );


  const recordList = () => {
    return (
      <div className="recordList">
        {sortByDateString(records, "datetime", isAscending).map((record, idx) => {
          const filename: string = record.filename;
          const thumnailImg: string = `/output/${filename}.jpg`;
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
              <div className="recordDeleteBtn" onClick={() => deleteRecord(record)}>❌</div>
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
              src={`/output/${selectedRecord.filename}.mp4`}
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