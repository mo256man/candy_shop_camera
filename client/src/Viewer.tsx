import { useState, useRef, useEffect } from 'react'
import "./Viewer.css"

type ViewerProps = {
  cameraId: number;
  showTitle: () => void;
  showRecord: () => void;
  showAnalysis: () => void;
  isAdmin: boolean;
  isRecording: boolean;
  handleIsRecording: (recording: boolean) => void;
  readyRecord: boolean;
  setReadyRecord: (ready: boolean) => void;
  isManualRecording: boolean;
  handleIsManualRecording: (manualRecording: boolean) => void;
  isRunning: boolean;
  sendConfig: (data: Record<string, unknown>) => void;
};

export default function Viewer({ cameraId, showTitle, showRecord, showAnalysis, isAdmin, isRecording, handleIsRecording, readyRecord, setReadyRecord, isManualRecording, handleIsManualRecording, isRunning, sendConfig }: ViewerProps) {
  const [showPanel, setShowPanel] = useState(false);
  const [feedKey, setFeedKey] = useState(0);
  const previousCameraIdRef = useRef<number | null>(null);

  // カメラIDが変わったらサーバーに通知してビデオフィードを再ロード
  useEffect(() => {
    // 同じカメラIDなら初期化をスキップ
    if (cameraId === null || cameraId === previousCameraIdRef.current) {
      setFeedKey(prev => prev + 1);
      return;
    }
    
    const setCameraOnServer = async () => {
      try {
        const response = await fetch('/api/set_camera', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ camera_id: cameraId })
        });
        
        if (!response.ok) {
          console.error('Failed to set camera on server:', response.statusText);
        } else {
          previousCameraIdRef.current = cameraId;
        }
      } catch (error) {
        console.error('Error setting camera on server:', error);
      }
    };
    
    setCameraOnServer();
    setFeedKey(prev => prev + 1);
  }, [cameraId]);

  const imgRef = useRef<HTMLImageElement>(null)
  const flaskBase = `http://${window.location.hostname}:5000`

  const reloadFeed = () => {
    if (imgRef.current) {
      const src = `${flaskBase}/api/video_feed?t=${Date.now()}`
      imgRef.current.src = src
    }
  }

  const handleReadyRecordToggle = () => {
    const newstate = !readyRecord;
    setReadyRecord(newstate);
    sendConfig({ ready_record: newstate });
  };


  const handleIsRecordingToggle = () => {
    // readyRecord = true のときのみ手動録画状態を切り替え可能
    if (!readyRecord) return;
    const newstate = !isManualRecording;
    handleIsRecording(newstate);
    sendConfig({ is_manual_recording: newstate });
  };

  const adminArea = () => {
    return (
      <div className="adminBtnArea">
        <div className="adminBtn">
          <div className="adminBtnTitle">AI連動録画</div>
          {isAdmin && <button className={`recordBtn ${readyRecord ? "isRecording" : ""}`}
            onClick={handleReadyRecordToggle}>
              {readyRecord ? "オン" : "オフ"}
          </button>}
        </div>
        <div className="adminBtn">
        <div className="adminBtnTitle">手動録画</div>
        {isAdmin && <button className={`recordBtn ${isManualRecording ? "isRecording" : ""}`}
          onClick={handleIsRecordingToggle}>
            {isManualRecording ? "録画中" : "停止中"}
        </button>}
      </div>
      </div>
    );
  }


  const headerPanel = (
    <div className="header">
      <div className="header-left">
        <div className="header-icon" onClick={() => showTitle()}>🔙</div>
        {isAdmin && adminArea()}
      </div>
      <div className="header-center">
        <div className="header-title">お菓子屋さんカメラ</div>
      </div>
      <div className="header-right">
        <div className="cameraControlPanel">
          {isRecording && <div className="recordingIcon">録画中 ●</div>}
          {readyRecord && <div className="readyIcon">【監視中】</div>}
          {isRunning ?
            <div className="header-icon-selected">📷</div>
          :
            <div className="header-icon-disabled">📷</div>
          }
          <div className="header-icon" onClick={() => showRecord()}>👀</div>
          <div className="header-icon" onClick={() => showAnalysis()}>📊</div>
        </div>
      </div>
    </div>
    );


  return (
    <>
    {headerPanel}
    <div className="video-wrap">
      <img key={feedKey} src={`${flaskBase}/api/video_feed`} ref={imgRef} alt="Video feed"
        onError={() => { setTimeout(reloadFeed, 2000) }}/>
    </div>
    </>
  );
}
