import type { ReactNode } from 'react'
import "./HeaderPanel.css"

type PageName = "viewer" | "record" | "analysis" | "setting";

type HeaderPanelProps = {
  title: string;
  currentPage: PageName;
  showTitle: () => void;
  showViewer?: () => void;
  showRecord?: () => void;
  showAnalysis?: () => void;
  showSetting?: () => void;
  isRunning: boolean;
  isRecording: boolean;
  readyRecord?: boolean;
  leftExtra?: ReactNode;
};

export default function HeaderPanel({
  title,
  currentPage,
  showTitle,
  showViewer,
  showRecord,
  showAnalysis,
  showSetting,
  isRunning,
  isRecording,
  readyRecord = false,
  leftExtra,
}: HeaderPanelProps) {

  const titleIcon = (
    <div className="header-icon" onClick={() => showTitle()}>🔙</div>
  );

  const cameraIcon = currentPage === "viewer"
    ? (isRunning
        ? <div className="header-icon-selected">📷</div>
        : <div className="header-icon-disabled">📷</div>)
    : (isRunning
        ? <div className="header-icon" onClick={() => showViewer?.()}>📷</div>
        : <div className="header-icon-disabled">📷</div>);

  const recordIcon = currentPage === "record"
    ? <div className="header-icon-selected">👀</div>
    : <div className="header-icon" onClick={() => showRecord?.()}>👀</div>;

  const analysisIcon = currentPage === "analysis"
    ? <div className="header-icon-selected">📊</div>
    : <div className="header-icon" onClick={() => showAnalysis?.()}>📊</div>;

  const settingIcon = currentPage === "setting"
    ? <div className="header-icon-selected">⚙️</div>
    : <div className="header-icon" onClick={() => showSetting?.()}>⚙️</div>;

  return (
    <div className="header">
      <div className="header-left">
        <div className="header-title">{title}</div>
        {leftExtra}
      </div>
      <div className="header-center">
        {isRecording && <div className="recordingIcon">録画中 ●</div>}
        {currentPage === "viewer" && readyRecord && <div className="readyIcon">【監視中】</div>}
      </div>
      <div className="header-right">
        {/* <div className="cameraControlPanel"> */}
          {titleIcon}
          {cameraIcon}
          {recordIcon}
          {analysisIcon}
          {settingIcon}
        {/* </div> */}
      </div>
    </div>
  );
}
