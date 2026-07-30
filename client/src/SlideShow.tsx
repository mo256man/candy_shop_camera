import { useState, useRef, useEffect } from 'react'
import HeaderPanel from './HeaderPanel.tsx'
import CommonDatePicker from './CommonDatePicker.tsx'
import "./SlideShow.css"

type SlideShowProps = {
  showTitle: () => void;
  showViewer: () => void;
  showRecord: () => void;
  showAnalysis: () => void;
  showSetting: () => void;
  isRunning: boolean;
  isRecording: boolean;
  readyRecord: boolean;
};

// 再生中、1コマ（1時間分）を切り替える間隔のデフォルト値
const DEFAULT_PLAY_INTERVAL_MS = 800;

// Dateから "yyyymmdd_hhmmss"（分・秒は常に00）を生成
function toSnapshotKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  return `${y}${m}${day}_${h}0000`;
}

function toMidnight(d: Date): Date {
  const next = new Date(d);
  next.setHours(0, 0, 0, 0);
  return next;
}

export default function SlideShow({ showTitle, showViewer, showRecord, showAnalysis, showSetting, isRunning, isRecording, readyRecord }: SlideShowProps) {
  // デートピッカーで選択中の日付（0時基準）
  const [pickedDate, setPickedDate] = useState<Date>(() => toMidnight(new Date()));
  // 現在表示中の日時（1時間刻みで進む）
  const [current, setCurrent] = useState<Date>(() => toMidnight(new Date()));
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  // 再生間隔（ミリ秒）。スライダーで 0～1000ms（0～1秒）の範囲で調整する
  const [intervalMs, setIntervalMs] = useState(DEFAULT_PLAY_INTERVAL_MS);

  const objectUrlRef = useRef<string | null>(null);
  // 同時に1件だけフェッチし、実行中に current が進んだ場合は
  // 完了後すぐに最新の日時を追いかけて取得する（取りこぼしを防ぐ）
  const fetchingRef = useRef(false);
  const pendingRef = useRef<Date | null>(null);
  const unmountedRef = useRef(false);
  const flaskBase = `http://${window.location.hostname}:5000`;

  // 表示中の日時が変わるたびに、Flaskへ日時を送りスナップショットを取得する
  useEffect(() => {
    if (fetchingRef.current) {
      // フェッチ中なら、完了後に追いかける最新の日時だけ覚えておく
      pendingRef.current = current;
      return;
    }

    fetchingRef.current = true;

    const loadSnapshot = async (target: Date) => {
      try {
        const res = await fetch(`${flaskBase}/api/get_snapshot`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ datetime: toSnapshotKey(target) }),
        });
        if (unmountedRef.current) return;
        if (res.ok) {
          const blob = await res.blob();
          if (unmountedRef.current) return;
          const url = URL.createObjectURL(blob);
          if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
          objectUrlRef.current = url;
          setImageUrl(url);
        } else {
          if (objectUrlRef.current) {
            URL.revokeObjectURL(objectUrlRef.current);
            objectUrlRef.current = null;
          }
          setImageUrl(null); // 画像が無い場合は黒画面
        }
      } catch (e) {
        console.error("get_snapshot error:", e);
        if (!unmountedRef.current) setImageUrl(null);
      }

      if (unmountedRef.current) return;

      // 待っている間に current が進んでいたら、続けて最新分を取得する
      const next = pendingRef.current;
      pendingRef.current = null;
      if (next && next.getTime() !== target.getTime()) {
        await loadSnapshot(next);
      } else {
        fetchingRef.current = false;
      }
    };

    loadSnapshot(current);
  }, [current, flaskBase]);

  // 再生中は一定間隔で1時間ずつ進める（日をまたいでそのまま進み続ける）
  useEffect(() => {
    if (!isPlaying) return;
    const id = setInterval(() => {
      setCurrent(prev => {
        const next = new Date(prev);
        next.setHours(next.getHours() + 1);
        return next;
      });
    }, intervalMs);
    return () => clearInterval(id);
  }, [isPlaying, intervalMs]);

  // アンマウント時にオブジェクトURLを解放
  useEffect(() => {
    return () => {
      unmountedRef.current = true;
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    };
  }, []);

  const handlePlay = () => setIsPlaying(true);
  const handleStop = () => setIsPlaying(false);

  const handleNextDay = () => {
    setIsPlaying(false);
    setCurrent(prev => {
      const next = new Date(prev);
      next.setDate(next.getDate() + 1);
      return toMidnight(next);
    });
  };

  const handlePrevDay = () => {
    setIsPlaying(false);
    setCurrent(prev => {
      const next = new Date(prev);
      next.setDate(next.getDate() - 1);
      return toMidnight(next);
    });
  };

  const handleDateChange = (d: Date) => {
    const midnight = toMidnight(d);
    setIsPlaying(false);
    setPickedDate(midnight);
    setCurrent(midnight);
    setShowDatePicker(false);
  };

  const toggleDatePicker = () => setShowDatePicker(prev => !prev);

  const currentLabel = `${current.getFullYear()}/${String(current.getMonth() + 1).padStart(2, "0")}/${String(current.getDate()).padStart(2, "0")} ${String(current.getHours()).padStart(2, "0")}:00`;

  const renderHeaderPanel = () => (
    <HeaderPanel
      title="スライドショー"
      currentPage="slideshow"
      showTitle={showTitle}
      showViewer={showViewer}
      showRecord={showRecord}
      showAnalysis={showAnalysis}
      showSetting={showSetting}
      isRunning={isRunning}
      isRecording={isRecording}
      readyRecord={readyRecord}
    />
  );

  const renderSlideShowControls = () => (
    <div className="slideShowControls">
      <div className="slideShowButtons">
        <button className="slideShowBtn" onClick={handlePrevDay} title="前日0時へ">⏮</button>
        {isPlaying ? (
          <button className="slideShowBtn" onClick={handleStop} title="停止">■</button>
        ) : (
          <button className="slideShowBtn" onClick={handlePlay} title="再生">▶</button>
        )}
        <button className="slideShowBtn" onClick={handleNextDay} title="翌日0時へ">⏭</button>
      </div>
      <div className="slideShowIntervalSlider">
        <label htmlFor="intervalSlider">切替間隔: {(intervalMs / 1000).toFixed(2)}秒</label>
        <input
          id="intervalSlider"
          type="range"
          min={0}
          max={1000}
          step={50}
          value={intervalMs}
          onChange={(e) => setIntervalMs(Number(e.target.value))}
        />
      </div>
      <div className="datepicker-container">
        <div className="datepicker-icon" onClick={toggleDatePicker}>📅</div>
        {showDatePicker && (
          <div className="calendarWrapper">
            <div className="calendar-close-row">
              <div className="calendar-close-btn" onClick={() => setShowDatePicker(false)}>x</div>
            </div>
            <CommonDatePicker date={pickedDate} onChange={handleDateChange} />
          </div>
        )}
      </div>
    </div>
  );

  const renderSlideShowImageArea = () => (
    <div className="slideShowImageArea">
      <div className="slideShowImageWrap">
        {imageUrl ? (
          <img className="slideShowImage" src={imageUrl} alt="Snapshot" />
        ) : (
          <div className="slideShowBlack">画像なし</div>
        )}
      </div>
      <div className="slideShowDateTime">{currentLabel}</div>
    </div>
  );

  return (
    <div className="slideShowMain">
      {renderHeaderPanel()}
      <div className="slideShowBody">
        {renderSlideShowControls()}
        {renderSlideShowImageArea()}
      </div>
    </div>
  );
}
