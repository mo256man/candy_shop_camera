import { useState, useEffect } from "react"
import io, { Socket } from "socket.io-client"
import "./App.css"
import Title from "./Title.tsx"
import Viewer from "./Viewer.tsx"
import Record from "./Record.tsx"
import Analysis from "./Analysis.tsx"

export default function App() {
  // flaskに送り全クライアントで共有する状態
  const [cameraId, setCameraId] = useState<number>(0)
  const [view, setView] = useState<"title" | "viewer" | "record" | "analysis">("title")
  const [isAdmin, setIsAdmin] = useState<boolean>(false)
  const [isRunning, setIsRunning] = useState<boolean>(false)
  const [readyRecord, setReadyRecord] = useState<boolean>(false)
  const [isRecording, setIsRecording] = useState<boolean>(false)
  const [isManualRecording, setIsManualRecording] = useState(false);
  const [isAscending, setIsAscending] = useState<boolean>(true);

  const showTitle = () => setView("title")
  const showViewer = () => setView("viewer")
  const showRecord = () => {
    getCameraRecords(date);
    setView("record");
  }
  const showAnalysis = () => setView("analysis")
  const loginAdmin = () => setIsAdmin(true)
  const logoutAdmin = () => setIsAdmin(false)

  const fetchStatus = async () => {
    try {
      const res = await fetch(`http://${window.location.hostname}:5000/api/get_status?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        if (data.camera_id !== undefined) setCameraId(data.camera_id);
        if (data.is_running !== undefined) setIsRunning(data.is_running);
        if (data.is_recording !== undefined) setIsRecording(data.is_recording);
        if (data.ready_record !== undefined) setReadyRecord(data.ready_record);
      }
    } catch (e) {
      console.error("get_status error:", e);
    }
  };

  // 初回取得
  useEffect(() => {
    fetchStatus();
  }, []);

  // 3秒ごとにポーリング（socket.ioが届かない端末でも同期できる）
  useEffect(() => {
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const socket: Socket = io(`http://${window.location.hostname}:5000`, {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity
    });

    socket.on("connect", () => {
      console.log("Socket.IO connected");
      fetchStatus();
    });

    socket.on("status_update", (data: { camera_id?: number; is_running?: boolean; is_recording?: boolean; ready_record?: boolean }) => {
      console.log("Received status_update:", data);
      if (data.camera_id !== undefined) {
        setCameraId(data.camera_id);
      }
      if (data.is_running !== undefined) {
        setIsRunning(data.is_running);
      }
      if (data.is_recording !== undefined) {
        setIsRecording(data.is_recording);
      }
      if (data.ready_record !== undefined) {
        setReadyRecord(data.ready_record);
      }
    });

    socket.on("disconnect", () => {
      console.log("Socket.IO disconnected");
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const handleCameraId = async (id: number) => {
    try {
      const res = await fetch("/api/set_camera", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ camera_id: id }),
      });
      if (res.ok) {
        setCameraId(id);
        if (id === 0) {
          handleRunning(false);
        } else {
          handleRunning(true);
        }
      } else {
        console.error("set_camera failed:", res.status);
      }
    } catch (e) {
      console.error("set_camera error:", e);
    }
  }

  const handleReadyRecord = (ready: boolean) => {
    setReadyRecord(ready);
  }

  const handleIsRecording = (recording: boolean) => {
    setIsRecording(recording);
  }

  const handleIsManualRecording = (manualRecording: boolean) => {
    setIsManualRecording(manualRecording);
  }

  const sendConfig = async (data: Record<string, unknown>) => {
    try {
      const response = await fetch('/api/set_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      if (!response.ok) {
        console.error('Failed to set config:', response.statusText);
      }
    } catch (error) {
      console.error('Error sending config to server:', error);
    }
  };

  const [date, setDate] = useState(new Date());
  const [records, setRecords] = useState<Array<{ id: number; filename: string; datetime: string; age: number; gender: string; duration: number }>>([]);

  const getCameraRecords = async (d: Date) => {
    const strDate = d.toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
    try {
      const res = await fetch("/api/get_records", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: strDate })
      });
      const data = await res.json();
      setRecords(data.records);
      console.log("Fetched records:", data.records);
    } catch (error) {
      console.error("Error fetching camera records:", error);
    }
  };

  const handleRunning = (running: boolean) => {
    try {
      const res = fetch("/api/set_running", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ running: running }),
      });
      setIsRunning(running);
    } catch (e) {
      console.error("set_running error:", e);
    }
  }

  const handleDateChange = (d: Date) => {
    setDate(d);
    getCameraRecords(d);
  };

  const handleDeleteRecord = async (filename: string) => {
    try {
      const res = await fetch("/api/delete_record", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: filename }),
      });
      const data = await res.json();
      console.log("Delete record:", data);
    } catch (error) {
      console.error("Failed to delete record:", error);
    }
  }
  
  return (
    <>
      {view === "title" && (
        <Title cameraId={cameraId} handleCameraId={handleCameraId} showViewer={showViewer} showRecord={showRecord} showAnalysis={showAnalysis} isAdmin={isAdmin} loginAdmin={loginAdmin} logoutAdmin={logoutAdmin} isRunning={isRunning} handleRunning={handleRunning} />
      )}
      {view === "viewer" && (
        <Viewer cameraId={cameraId} showTitle={showTitle} showRecord={showRecord} showAnalysis={showAnalysis} isAdmin={isAdmin} isRecording={isRecording} handleIsRecording={handleIsRecording} readyRecord={readyRecord} setReadyRecord={setReadyRecord} isManualRecording={isManualRecording} handleIsManualRecording={handleIsManualRecording} isRunning={isRunning} sendConfig={sendConfig} />
      )}
      {view === "record" && (
        <Record cameraId={cameraId} showTitle={showTitle} showViewer={showViewer} showAnalysis={showAnalysis} isAdmin={isAdmin} isRecording={isRecording} handleIsRecording={handleIsRecording} readyRecord={readyRecord} handleReadyRecord={handleReadyRecord} isManualRecording={isManualRecording} handleIsManualRecording={handleIsManualRecording} records={records} date={date} handleDateChange={handleDateChange} handleDeleteRecord={handleDeleteRecord} isRunning={isRunning} isAscending={isAscending} setIsAscending={setIsAscending} />
      )}
      {view === "analysis" && (
        <Analysis
          isAdmin={isAdmin}
          cameraId={cameraId}
          isRecording={isRecording}
          showTitle={showTitle}
          showViewer={showViewer}
          showRecord={showRecord}
          handleDateChange={handleDateChange}
          records={records}
          date={date}
          isRunning={isRunning}
        />
      )}
    </>
  );
}
