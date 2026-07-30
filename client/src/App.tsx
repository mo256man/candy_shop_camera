import { useState, useEffect } from "react"
import "./App.css"
import Title from "./Title.tsx"
import Viewer from "./Viewer.tsx"
import Record from "./Record.tsx"
import Analysis from "./Analysis.tsx"
import Setting from "./Setting.tsx"
import SlideShow from "./SlideShow.tsx"

export default function App() {
  // flaskに送り全クライアントで共有する状態
  const [cameraId, setCameraId] = useState<number>(0)
  const [view, setView] = useState<"title" | "viewer" | "record" | "analysis" | "setting" | "slideshow">("title")
  const [isAdmin, setIsAdmin] = useState<boolean>(false)
  const [isRunning, setIsRunning] = useState<boolean>(false)
  const [readyRecord, setReadyRecord] = useState<boolean>(true)
  const [isRecording, setIsRecording] = useState<boolean>(false)
  const [isManualRecording, setIsManualRecording] = useState(false);
  const [isAscending, setIsAscending] = useState<boolean>(false);
  const [filterUnknown, setFilterUnknown] = useState<boolean>(true);
  const [filterShort, setFilterShort] = useState<boolean>(true);
  const [hourOption, setHourOption] = useState<string>("");

  const showTitle = () => setView("title")
  const showViewer = () => setView("viewer")
  const showRecord = () => {
    getCameraRecords(date);
    setView("record");
  }
  const showAnalysis = () => setView("analysis")
  const showSetting = () => {
    getDiskUsage();
    setView("setting");
  }
  const showSlideShow = () => setView("slideshow")
  const loginAdmin = () => setIsAdmin(true)
  const logoutAdmin = () => setIsAdmin(false)

  const fetchStatus = async (): Promise<boolean> => {
    try {
      const res = await fetch(`http://${window.location.hostname}:5000/api/get_status?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        if (data.camera_id !== undefined) setCameraId(data.camera_id);
        if (data.is_running !== undefined) setIsRunning(data.is_running);
        if (data.is_recording !== undefined) setIsRecording(data.is_recording);
        if (data.ready_record !== undefined) setReadyRecord(data.ready_record);
        return !!data.is_running;
      }
    } catch (e) {
      console.error("get_status error:", e);
    }
    return false;
  };

  const [diskUsage, setDiskUsage] = useState<{ os: string; drive: string; total_gb: number; free_gb: number; used_gb: number; folder: string; folder_gb: number } | null>(null);

  const getDiskUsage = async () => {
    try {
      const res = await fetch(`http://${window.location.hostname}:5000/api/get_disk_usage?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        setDiskUsage(data);
      }
    } catch (e) {
      console.error("get_disk_usage error:", e);
    }
  };

  // 初回取得 + 一定時間だけポーリング
  // Flaskはカメラ初期化（特にネットワークカメラ）に起動後しばらく時間が
  // かかることがあり、Reactが先に起動して is_running=false のまま表示され続ける
  // ことがある。is_running=true の連絡が来た時点でポーリングを終了し、
  // また camera_id 無し起動（自動初期化しない運用）で連絡が来ない場合に備えて
  // 一定時間経過したら諦めてポーリングを打ち切る。
  useEffect(() => {
    let stopped = false;
    let timeoutId: ReturnType<typeof setTimeout>;
    const POLL_INTERVAL_MS = 3000;
    const POLL_TIMEOUT_MS = 40000; // サーバー側の最大リトライ時間より少し長め
    const startTime = Date.now();

    const poll = async () => {
      if (stopped) return;
      const running = await fetchStatus();
      if (stopped || running) return; // 連絡があったので終了
      if (Date.now() - startTime >= POLL_TIMEOUT_MS) return; // 時間切れで終了
      timeoutId = setTimeout(poll, POLL_INTERVAL_MS);
    };

    poll();

    return () => {
      stopped = true;
      clearTimeout(timeoutId);
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
  const [allRecords, setAllRecords] = useState<Array<{ id: number; filename: string; datetime: string; age: number; gender: string; duration: number }>>([]);

  const getAllRecords = async () => {
    try {
      const res = await fetch("/api/get_records", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: "" })
      });
      const data = await res.json();
      setAllRecords(data.records ?? []);
    } catch (error) {
      console.error("Error fetching all camera records:", error);
    }
  };

  useEffect(() => {
    if (!isAdmin) return;
    getAllRecords();
  }, [isAdmin]);

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

  const handleDeleteRecordsRange = async (rangeFrom: Date, rangeTo: Date) => {
    const strFrom = rangeFrom.toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
    const strTo = rangeTo.toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
    try {
      const res = await fetch("/api/delete_records_range", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date_from: strFrom, date_to: strTo }),
      });
      const data = await res.json();
      console.log("Delete records range:", data);
      await getAllRecords();
      await getCameraRecords(date);
    } catch (error) {
      console.error("Failed to delete records range:", error);
    }
  }

  const handleShutdown = async () => {
    try {
      const res = await fetch("/api/shutdown", {
        method: "GET",
      });
      const data = await res.json();
      if (data.status === "success") {
        console.log("Shutdown initiated");
      } else {
        console.error("Shutdown failed:", data.message);
      }
    } catch (error) {
      console.error("Shutdown error:", error);
    }
  }
  
  return (
    <>
      {view === "title" && (
        <Title cameraId={cameraId} handleCameraId={handleCameraId} showViewer={showViewer} showRecord={showRecord} showAnalysis={showAnalysis} showSetting={showSetting} showSlideShow={showSlideShow} isAdmin={isAdmin} loginAdmin={loginAdmin} logoutAdmin={logoutAdmin} isRunning={isRunning} handleRunning={handleRunning} />
      )}
      {view === "slideshow" && (
        <SlideShow showTitle={showTitle} showViewer={showViewer} showRecord={showRecord} showAnalysis={showAnalysis} showSetting={showSetting} isRunning={isRunning} isRecording={isRecording} readyRecord={readyRecord} />
      )}
      {view === "viewer" && (
        <Viewer cameraId={cameraId} showTitle={showTitle} showRecord={showRecord} showAnalysis={showAnalysis} showSetting={showSetting} showSlideShow={showSlideShow} isAdmin={isAdmin} isRecording={isRecording} handleIsRecording={handleIsRecording} readyRecord={readyRecord} setReadyRecord={setReadyRecord} isManualRecording={isManualRecording} handleIsManualRecording={handleIsManualRecording} isRunning={isRunning} sendConfig={sendConfig} />
      )}
      {view === "record" && (
        <Record cameraId={cameraId} showTitle={showTitle} showViewer={showViewer} showAnalysis={showAnalysis} showSetting={showSetting} showSlideShow={showSlideShow} isAdmin={isAdmin} isRecording={isRecording} handleIsRecording={handleIsRecording} readyRecord={readyRecord} handleReadyRecord={handleReadyRecord} isManualRecording={isManualRecording} handleIsManualRecording={handleIsManualRecording} records={records} date={date} handleDateChange={handleDateChange} handleDeleteRecord={handleDeleteRecord} isRunning={isRunning} isAscending={isAscending} setIsAscending={setIsAscending} filterUnknown={filterUnknown} setFilterUnknown={setFilterUnknown} filterShort={filterShort} setFilterShort={setFilterShort} hourOption={hourOption} setHourOption={setHourOption} />
      )}
      {view === "analysis" && (
        <Analysis
          isAdmin={isAdmin}
          cameraId={cameraId}
          isRecording={isRecording}
          showTitle={showTitle}
          showViewer={showViewer}
          showRecord={showRecord}
          showSetting={showSetting}
          showSlideShow={showSlideShow}
          handleDateChange={handleDateChange}
          records={records}
          date={date}
          isRunning={isRunning}
          filterUnknown={filterUnknown}
          setFilterUnknown={setFilterUnknown}
          filterShort={filterShort}
          setFilterShort={setFilterShort}
          hourOption={hourOption}
          setHourOption={setHourOption}
        />
      )}
      {view === "setting" && (
        <Setting
          isAdmin={isAdmin}
          cameraId={cameraId}
          isRecording={isRecording}
          showTitle={showTitle}
          showViewer={showViewer}
          showRecord={showRecord}
          showAnalysis={showAnalysis}
          showSetting={showSetting}
          showSlideShow={showSlideShow}
          isRunning={isRunning}
          onAdminChange={setIsAdmin}
          handleCameraId={handleCameraId}
          handleRunning={handleRunning}
          allRecords={allRecords}
          handleDeleteRecordsRange={handleDeleteRecordsRange}
          diskUsage={diskUsage}
          handleShutdown={handleShutdown}
        />
      )}
    </>
  );
}
