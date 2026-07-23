import { useState, useEffect, useRef } from 'react'
import "./Title.css"

type TitleProps = {
  cameraId: number;
  handleCameraId: (id: number) => void;
  showViewer: () => void;
  showRecord: () => void;
  showAnalysis: () => void;
  showSetting: () => void;
  isAdmin: boolean;
  loginAdmin: () => void;
  logoutAdmin: () => void;
  isRunning: boolean;
  handleRunning: (running: boolean) => void;
};

export default function Title({ cameraId, handleCameraId, showViewer, showRecord, showAnalysis, showSetting, isAdmin, loginAdmin, logoutAdmin, isRunning, handleRunning }: TitleProps) {

  const title = (
    <div className="kanban">
      <img className="kanbanImage" src="kanban.png" alt="Kanban" />
      <div className="kanbanTitle">お菓子屋さんの防犯＋分析カメラ</div>
    </div>
  );

  const menu = (
    <div className="titleMenu">
      {isRunning ?
        <button className="btnMenu colorView" onClick={showViewer}>📷 ライブ映像（cameraId={cameraId}）</button>
      :
        <button className="btnMenu colorNoCamera">✖ カメラ未設定</button>
      }
      <button className="btnMenu colorRecord" onClick={showRecord}>👀 録画確認</button>
      <button className="btnMenu colorAnalysis" onClick={showAnalysis}>📊 分析結果</button>
      <button className="btnMenu colorEnvironment" onClick={showSetting}>⚙️ 設定画面</button>
    </div>
  );

  return (
    <div className="titleMain">
      <div className="backgroundImage"></div>
      {title}
      {menu}
    </div>
  );

}