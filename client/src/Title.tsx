import { useState, useEffect, useRef } from 'react'
import "./Title.css"

type TitleProps = {
  cameraId: number;
  handleCameraId: (id: number) => void;
  showViewer: () => void;
  showRecord: () => void;
  showAnalysis: () => void;
  isAdmin: boolean;
  loginAdmin: () => void;
  logoutAdmin: () => void;
  isRunning: boolean;
  handleRunning: (running: boolean) => void;
};

export default function Title({ cameraId, handleCameraId, showViewer, showRecord, showAnalysis, isAdmin, loginAdmin, logoutAdmin, isRunning, handleRunning }: TitleProps) {
  const [showAdminMenu, setShowAdminMenu] = useState<"settingBtn" | "loginArea" | "controlPanel">("settingBtn");
  const [password, setPassword] = useState<string>("");

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
    </div>
  );

  const handleSettingBtnClick = () => {
    if (isAdmin) {
      setShowAdminMenu("controlPanel");
    } else {
      setShowAdminMenu("loginArea");
    }
  }

  const handleLogin = () => {
    const correctPassword = "TY34433";
    if (password === correctPassword) {
      loginAdmin();
      setShowAdminMenu("controlPanel");
    }
  }

  const handleLogout = () => {
    logoutAdmin();
    setShowAdminMenu("settingBtn");
  }

  const settingBtn = (
    <div className="settingBtn" onClick={handleSettingBtnClick}>⚙</div>
  );

  const loginArea = (
    <div className={`loginArea ${isAdmin ? "bgAdmin" : "bgNotAdmin"}`}>
      <div className="controlPanel-title">管理者ログイン</div>
      <input
        className="loginInput"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="パスワード"
      />
      <div className="loginBtns">
        <button onClick={handleLogin}>ログイン</button>
        <button onClick={() => setShowAdminMenu("settingBtn")}>キャンセル</button>
      </div>
    </div>
  );

  const controlPanel = () => {
    const btns =  [
      {label1: "PC内蔵カメラ", label2: "（トライ）", id: 1},
      {label1: "AXISカメラ", label2: "（本番）", id: 2},
      {label1: "カメラ", label2: "接続断", id: 0},
    ];
    return (
      <div className={"controlPanel"}>
        <div className="loginBtns">
          <button onClick={() => setShowAdminMenu("settingBtn")}>閉じる</button>
          <button onClick={handleLogout}>ログアウト</button>
        </div>
        <div className="controlPanel-title">カメラ選択</div>
        <div className="cameraList">
          {btns.map((btn) => (
            <div key={btn.id} className={`cameraItem ${cameraId === btn.id ? "active" : ""}`} 
              onClick={() => handleCameraId(btn.id)}>
              <div>{btn.label1}</div>
              <div>{btn.label2}</div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const adminArea = (
    <div className="adminArea"> 
      {showAdminMenu === "settingBtn" && settingBtn}
      {showAdminMenu === "loginArea" && loginArea}
      {showAdminMenu === "controlPanel" && controlPanel()}
    </div>
  );

  return (
    <div className="titleMain">
      {adminArea}
      <div className="backgroundImage"></div>
      {title}
      {menu}
    </div>
  );

}