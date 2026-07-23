import { useState, useRef } from 'react'
import { registerLocale } from "react-datepicker";
import ja from "date-fns/locale/ja";
import CommonDatePicker from "./CommonDatePicker"
import HeaderPanel from "./HeaderPanel.tsx"
import PasswordPad from "./PasswordPad.tsx"
import DiskUsageBarChart from "./DiskUsageBarChart.tsx"
import "react-datepicker/dist/react-datepicker.css"
import "./Setting.css"

registerLocale("ja", ja);

type SettingProps = {
  isAdmin: boolean;
  cameraId: number | null;
  isRecording: boolean;
  showTitle: () => void;
  showViewer: () => void;
  showRecord: () => void;
  showAnalysis: () => void;
  showSetting: () => void;
  handleDateChange: (d: Date) => void;
  records: Array<{ id: number; filename: string; datetime: string; age: number; gender: string; duration: number }>;
  date: Date;
  isRunning: boolean;
  onAdminChange: (isAdmin: boolean) => void;
  handleCameraId: (id: number) => void;
  handleRunning: (running: boolean) => void;
  allRecords: Array<{ id: number; filename: string; datetime: string; age: number; gender: string; duration: number }>;
  handleDeleteRecordsRange: (dateFrom: Date, dateTo: Date) => void;
  diskUsage: { os: string; drive: string; total_gb: number; free_gb: number; used_gb: number; folder: string; folder_gb: number } | null;
};

// "YYYY-MM-DD" のキー文字列をタイムゾーンに依存せずDateへ変換
function parseDateKey(dateKey: string): Date {
  const [year, month, day] = dateKey.split("-").map(Number);
  return new Date(year, month - 1, day);
}

// DateをJST基準の"YYYY-MM-DD"キー文字列に変換
function toDateKey(d: Date): string {
  return d.toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
}

// "YYYY-MM-DD" のキー文字列を表示用の"M/D"形式に変換
function formatMonthDay(dateKey: string): string {
  const [, month, day] = dateKey.split("-").map(Number);
  return `${month}/${day}`;
}

// Dateを表示用の"M/D"形式に変換
function formatMonthDayFromDate(d: Date): string {
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function Setting({ isAdmin, cameraId, isRecording, showTitle, showViewer, showRecord, showAnalysis, showSetting, handleDateChange, records, date, isRunning, onAdminChange, handleCameraId, handleRunning, allRecords, handleDeleteRecordsRange, diskUsage }: SettingProps) {
  const [activePicker, setActivePicker] = useState<"header" | "extractFrom" | "extractTo" | "deleteFrom" | "deleteTo" | null>(null);
  const [extractOption, setExtractOption] = useState<"today" | "pastWeek" | "custom" | null>(null);
  const [extractStatus, setExtractStatus] = useState<null | "loading" | { success: true; count: number; usbPath: string } | { success: false; message: string }>(null);
  const [deleteOption, setDeleteOption] = useState<"oldest" | "oldestWeek" | "custom" | null>(null);
  const [deleteStatus, setDeleteStatus] = useState<null | "loading" | { success: true; deleted_count: number } | { success: false; message: string }>(null);
  const [extractDateFrom, setExtractDateFrom] = useState<Date | null>(null);
  const [extractDateTo, setExtractDateTo] = useState<Date | null>(null);
  const [deleteDateFrom, setDeleteDateFrom] = useState<Date | null>(null);
  const [deleteDateTo, setDeleteDateTo] = useState<Date | null>(null);
  const [dataTab, setDataTab] = useState<"extract" | "delete">("extract");

  const now = new Date();
  const todayKey = toDateKey(now);
  const pastWeekStartKey = toDateKey(new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000));

  const today = formatMonthDay(todayKey);
  const pastWeek = formatMonthDay(pastWeekStartKey);

  const recordDateKeys = allRecords.map(r => r.datetime.substring(0, 10)).sort();
  const oldestDateKey = recordDateKeys.length > 0 ? recordDateKeys[0] : null;
  const oldestWeekEndKey = oldestDateKey
    ? toDateKey(new Date(parseDateKey(oldestDateKey).getTime() + 6 * 24 * 60 * 60 * 1000))
    : null;

  const oldestDate = oldestDateKey ? formatMonthDay(oldestDateKey) : "データなし";
  const oldestWeek = oldestWeekEndKey ? formatMonthDay(oldestWeekEndKey) : "データなし";

  const todayCount = allRecords.filter(r => r.datetime.substring(0, 10) === todayKey).length;
  const pastWeekCount = allRecords.filter(r => {
    const key = r.datetime.substring(0, 10);
    return key >= pastWeekStartKey && key <= todayKey;
  }).length;
  const oldestDateCount = oldestDateKey
    ? allRecords.filter(r => r.datetime.substring(0, 10) === oldestDateKey).length
    : 0;
  const oldestWeekCount = (oldestDateKey && oldestWeekEndKey)
    ? allRecords.filter(r => {
        const key = r.datetime.substring(0, 10);
        return key >= oldestDateKey && key <= oldestWeekEndKey;
      }).length
    : 0;

  // データ取り出し：選択中のextractDateFrom, extractDateToを元にUSBへエクスポートを実行する
  const extractRecords = async () => {
    if (!extractDateFrom || !extractDateTo) return;
    setExtractStatus("loading");
    try {
      const res = await fetch("/api/export_to_usb", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date_from: toDateKey(extractDateFrom),
          date_to: toDateKey(extractDateTo),
        }),
      });
      const json = await res.json();
      if (json.status === "success") {
        setExtractStatus({ success: true, count: json.count, usbPath: json.usb_path });
        setExtractDateFrom(null);
        setExtractDateTo(null);
        setExtractOption(null);
      } else {
        setExtractStatus({ success: false, message: json.message ?? "エクスポートに失敗しました" });
      }
    } catch (error) {
      console.error("Failed to export records:", error);
      setExtractStatus({ success: false, message: "サーバーへの接続に失敗しました" });
    }
  };

  // データ削除：選択中のdeleteDateFrom, deleteDateToを元に削除を実行する
  const deleteRecords = async () => {
    if (!deleteDateFrom || !deleteDateTo) return;
    setDeleteStatus("loading");
    const strFrom = deleteDateFrom.toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
    const strTo = deleteDateTo.toLocaleDateString("sv-SE", { timeZone: "Asia/Tokyo" });
    try {
      const res = await fetch("/api/delete_records_range", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date_from: strFrom, date_to: strTo }),
      });
      const json = await res.json();
      if (json.status === "success") {
        setDeleteStatus({ success: true, deleted_count: json.deleted_count });
        setDeleteDateFrom(null);
        setDeleteDateTo(null);
        setDeleteOption(null);
        // 親コンポーネントのデータを更新
        await handleDeleteRecordsRange(deleteDateFrom, deleteDateTo);
      } else {
        setDeleteStatus({ success: false, message: json.message ?? "削除に失敗しました" });
      }
    } catch (error) {
      console.error("Failed to delete records:", error);
      setDeleteStatus({ success: false, message: "サーバーへの接続に失敗しました" });
    }
  };

  const headerPanel = (
    <HeaderPanel
      title="設定画面"
      currentPage="setting"
      showTitle={showTitle}
      showViewer={showViewer}
      showRecord={showRecord}
      showAnalysis={showAnalysis}
      showSetting={showSetting}
      isRunning={isRunning}
      isRecording={isRecording}
    />
  );

  const showDiskUsage = () => {
    return (
      <div>
        <div className="settingSectionTitle">💻 ディスク使用状況（全容量：{diskUsage?.total_gb.toFixed(1) ?? 0}GB）</div>
        {diskUsage ? (
          <DiskUsageBarChart
            totalGb={diskUsage.total_gb}
            freeGb={diskUsage.free_gb}
            usedGb={diskUsage.used_gb}
            folderGb={diskUsage.folder_gb}
          />
        ) : (
          <div className="diskUsageInfo">取得中...</div>
        )}
      </div>
    );
  }

  const showCameraSelection = () => {
    const btns =  [
      {label1: "PC内蔵カメラ", label2: "（トライ）", id: 1},
      {label1: "AXISカメラ", label2: "（本番）", id: 2},
      {label1: "カメラ", label2: "接続断", id: 0},
    ];

    return (
      <div>
        <div className="settingSectionTitle">📷 カメラ選択</div>
        <div className="btnCameraContainer">
          {btns.map(btn => (
            <div key={btn.id} className={`btnCamera ${cameraId === btn.id ? "active" : ""}`} onClick={() => { handleCameraId(btn.id); if (btn.id === 0) { handleRunning(false); } else { handleRunning(true); } }}>
              <div>{btn.label1}</div>
              <div>{btn.label2}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const showDatePicker = (dateValue: Date | null, onDateChange: (date: Date) => void, pickerKey: "extractFrom" | "extractTo" | "deleteFrom" | "deleteTo") => {
    return (
      <div className="datepicker-container" onClick={(e) => e.stopPropagation()}>
        {dateValue ? (
          <span>{formatMonthDayFromDate(dateValue)}</span>
        ) : (
          <button onClick={() => setActivePicker(activePicker === pickerKey ? null : pickerKey)}>click me</button>
        )}
        {activePicker === pickerKey && (
          <div className="calendarWrapper">
            <CommonDatePicker
              date={dateValue ?? new Date()}
              onChange={(d) => {
                onDateChange(d);
                setActivePicker(null);
              }}
            />
          </div>
        )}
      </div>
    );
  }

  const showExtractTab = () => {
    let infoText = "";
    if (extractStatus === "loading") {
      infoText = "⏳ USBへコピー中...";
    } else if (extractStatus) {
      if (extractStatus.success) {
        infoText = `✅ USB（${extractStatus.usbPath}）に ${extractStatus.count} 件をコピーしました`;
      } else {
        infoText = `❌ ${extractStatus.message}`;
      }
    }

    return (
      <div className="dateManagementArea extract">
        <div className="btnDateContainer">
          <div className={`btnDate ${extractOption === "today" ? "active" : ""}`} 
            onClick={() => { setExtractOption("today"); setExtractDateFrom(parseDateKey(todayKey)); setExtractDateTo(parseDateKey(todayKey)); }}>
            <div className="column">
              <div><b>今日の分</b></div>
              <div>（{today}）</div>
              <div>{todayCount}件</div>
            </div>
          </div>
          <div className={`btnDate ${extractOption === "pastWeek" ? "active" : ""}`} 
            onClick={() => { setExtractOption("pastWeek"); setExtractDateFrom(parseDateKey(pastWeekStartKey)); setExtractDateTo(parseDateKey(todayKey)); }}>
            <div className="column">
              <div><b>1週間分</b></div>
              <div>（{pastWeek}～）</div>
              <div>{pastWeekCount}件</div>
            </div>
          </div>
          <div className={`btnDate ${extractOption === "custom" ? "active" : ""}`} 
            onClick={() => { setExtractOption("custom"); setExtractDateFrom(null); setExtractDateTo(null); }}>
            <div className="column">
              <div><b>期日指定</b></div>
              <div className="row">
                {showDatePicker(extractDateFrom, setExtractDateFrom, "extractFrom")}
                <div>～</div>
                {showDatePicker(extractDateTo, setExtractDateTo, "extractTo")}
              </div>
            </div>
          </div>
          <div className={`btnExtract ${(!extractDateFrom || !extractDateTo || extractStatus === "loading") ? "disabled" : ""}`} 
            onClick={() => { if (extractDateFrom && extractDateTo && extractStatus !== "loading") { setExtractStatus(null); extractRecords(); } }}>
            {extractStatus === "loading" ? "抽出中..." : "抽出実行"}
          </div>
        </div>
        <div className="infoText">
          {infoText}
        </div>
      </div>
    );
  }

  const showDeleteTab = () => {
    let infoText = "";
    if (deleteStatus === "loading") {
      infoText = "⏳ 削除中...";
    } else if (deleteStatus) {
      if (deleteStatus.success) {
        infoText = `✅ ${deleteStatus.deleted_count} 件を削除しました`;
      } else {
        infoText = `❌ ${deleteStatus.message}`;
      }
    }

    return (
      <div className="dateManagementArea delete">
        <div className="btnDateContainer">
          <div className={`btnDate ${deleteOption === "oldest" ? "active" : ""}`} 
            onClick={() => {
              setDeleteOption("oldest");
              if (oldestDateKey) {
                setDeleteDateFrom(parseDateKey(oldestDateKey));
                setDeleteDateTo(parseDateKey(oldestDateKey));
              }
            }}>
            <div><b>もっとも古い1日分</b></div>
            <div>（{oldestDate}）</div>
            <div>{oldestDateCount}件</div>
          </div>
          <div className={`btnDate ${deleteOption === "oldestWeek" ? "active" : ""}`} 
            onClick={() => {
              setDeleteOption("oldestWeek");
              if (oldestDateKey && oldestWeekEndKey) {
                setDeleteDateFrom(parseDateKey(oldestDateKey));
                setDeleteDateTo(parseDateKey(oldestWeekEndKey));
              }
            }}>
            <div><b>もっとも古い1週間分</b></div>
            <div>（～{oldestWeek}）</div>
            <div>{oldestWeekCount}件</div>
          </div>
          <div className={`btnDate ${deleteOption === "custom" ? "active" : ""}`} 
            onClick={() => { setDeleteOption("custom"); setDeleteDateFrom(null); setDeleteDateTo(null); }}>
            <div><b>期日指定</b></div>
            <div className="row">
              {showDatePicker(deleteDateFrom, setDeleteDateFrom, "deleteFrom")}
              <div>～</div>
              {showDatePicker(deleteDateTo, setDeleteDateTo, "deleteTo")}
            </div>
          </div>
          <div className={`btnDelete ${(!deleteDateFrom || !deleteDateTo || deleteStatus === "loading") ? "disabled" : ""}`} onClick={() => { if (deleteDateFrom && deleteDateTo && deleteStatus !== "loading") { setDeleteStatus(null); deleteRecords(); } }}>
            {deleteStatus === "loading" ? "削除中..." : "削除実行"}
          </div>
        </div>
        <div className="infoText">
          {infoText}
        </div>
      </div>
    );
  }

  const showDataManagement = () => {
    return (
      <div className="dataManagementArea">
        <div className="settingTabContainer">
          <div className={`settingTab ${dataTab === "extract" ? "activeExtract" : ""}`} 
            onClick={() => setDataTab("extract")}>
            💾 データ取り出し
          </div>
          <div className={`settingTab ${dataTab === "delete" ? "activeDelete" : ""}`} 
            onClick={() => setDataTab("delete")}>
            🗑️ データ削除
          </div>
        </div>
        {dataTab === "extract" && showExtractTab()}
        {dataTab === "delete" && showDeleteTab()}
      </div>
    );
  }

  const settingContent = () => {
    return (
      <div>
        {showDataManagement()}
        {showDiskUsage()}
        {showCameraSelection()}
      </div>
    );
  }

  return (
    <>
      {headerPanel}
      <div className="settingMain">
        {!isAdmin && <PasswordPad isAdmin={isAdmin} onAdminChange={onAdminChange} />}
        {isAdmin && settingContent()}
      </div>
    </>
  );

}
