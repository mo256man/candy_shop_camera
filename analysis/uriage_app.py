import csv
import json
import os
import re
import sqlite3
import sys
import tkinter.ttk as ttk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog

import TkEasyGUI as eg
import pandas as pd
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


def get_base_dir():
    """実行ファイル（exe）またはスクリプトのあるフォルダを返す。
    PyInstaller の onefile では sys.executable が exe 本体を指すため、
    その親フォルダを基準にする。通常の .py 実行では __file__ を使う。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
DB_PATH = os.path.join(BASE_DIR, "uriage.sqlite")
EXCEL_PATH = os.path.join(BASE_DIR, "uriage.xlsx")
STORE_PATH = os.path.join(BASE_DIR, "stores.ini")

HISTORY_HEADER = [
    "操作ID", "商品ID", "商品名", "商品コード",
    "在庫操作タイプ", "在庫変更数", "操作後在庫", "理論賞味期限", "日時",
]

STATS_HEADER = [
    "商品ID", "商品名（日本語）", "売上高（円）", "売上数", "注文件数",
]


def load_stores():
    """店舗定義ファイル(stores.ini)を読み込む。
    中身は JSON の配列で、各要素は {"name": 店舗名, "id": 店舗ID}。
    拡張子は ini だが内容は JSON として解釈する。
    末尾のコンマを許容する。読み込めない場合は空リストを返す。
    """
    if not os.path.exists(STORE_PATH):
        return []
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
            content = f.read()
        # 末尾のコンマを削除（,] と ,} のパターン）
        content = re.sub(r',(\s*[\]}])', r'\1', content)
        data = json.loads(content)
    except (ValueError, OSError):
        return []
    stores = []
    for item in data if isinstance(data, list) else []:
        try:
            stores.append({"id": int(item["id"]), "name": str(item["name"])})
        except (KeyError, TypeError, ValueError):
            continue
    return stores


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def parse_dt(s):
    s = (s or "").strip()
    fmts = [
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
        "%Y-%m-%d", "%Y/%m/%d",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except ValueError:
            continue
    return None


def normalize_month(s):
    """入力文字列を yyyy-mm 形式に正規化する。不正なら None を返す。
    yyyy-mm / yyyy/mm / yyyymm を受け付ける。
    """
    s = (s or "").strip()
    m = re.fullmatch(r"(\d{4})[-/]?(\d{1,2})", s)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2))
    if not 1 <= month <= 12:
        return None
    return f"{year:04d}-{month:02d}"


def get_name_digits(path):
    """ファイル名の種別名（histories / statisctics）の直後にある
    数字列を取り出す。
    oneqr_stock_histories_2026071395236-utf8-bom.csv のように
    時刻部分がゼロ埋めされず桁数が一定しないため、桁数は限定せず
    連続する数字をそのまま返す。見つからなければ空文字を返す。
    """
    base = os.path.basename(path or "")
    m = re.search(r"(histories|statisctics)_(\d+)", base)
    if not m:
        return ""
    return m.group(2)


def guess_month_from_name(path):
    """ファイル名から締め単位の年月(yyyy-mm)を推定する。
    数字列の先頭8文字が yyyymmdd なので、そこからスライスで取り出す。
    推定できなければ空文字を返す。
    """
    digits = get_name_digits(path)
    if len(digits) < 6:
        return ""
    return f"{digits[0:4]}-{digits[4:6]}"


def shorten_csv_name(name):
    """元データタブに表示するファイル名を短縮する。
    oneqr_stock_histories_yyyymmdd... を histories_yyyymmdd に、
    oneqr_products_statisctics_yyyymmdd... を statisctics_yyyymmdd
    に変換する。数字列の先頭8文字を日付として使う。
    想定外の形式のときは元のファイル名をそのまま返す。
    """
    base = os.path.basename(name or "")
    m = re.search(r"(histories|statisctics)_(\d+)", base)
    if not m:
        return base
    digits = m.group(2)
    if len(digits) < 8:
        return base
    return f"{m.group(1)}_{digits[0:8]}"


# ------------------------------------------------------ モーダルダイアログ

def _tk_parent(window):
    """TkEasyGUI の Window から tk のウィンドウオブジェクトを取り出す。
    ダイアログの parent に渡すことでモーダル化する。
    取り出せない場合は None を返し、その場合は非モーダルになる。
    """
    for attr in ("window", "root", "widget", "tk_window", "_window"):
        obj = getattr(window, attr, None)
        if obj is not None and hasattr(obj, "winfo_exists"):
            return obj
    return None


def ask_open_file(window, title, patterns):
    """モーダルなファイル選択ダイアログを開く。
    選択されなければ空文字を返す。
    """
    parent = _tk_parent(window)
    kwargs = {
        "title": title,
        "initialdir": BASE_DIR,
        "filetypes": list(patterns) + [("すべてのファイル", "*.*")],
    }
    if parent is not None:
        kwargs["parent"] = parent
    return filedialog.askopenfilename(**kwargs) or ""


def ask_text(window, title, prompt, initial=""):
    """モーダルな文字列入力ダイアログを開く。
    キャンセル時は None を返す。
    """
    parent = _tk_parent(window)
    kwargs = {"initialvalue": initial}
    if parent is not None:
        kwargs["parent"] = parent
    return simpledialog.askstring(title, prompt, **kwargs)


def ask_yes_no(window, title, message):
    """モーダルな確認ダイアログを開く。はいなら True を返す。"""
    parent = _tk_parent(window)
    kwargs = {}
    if parent is not None:
        kwargs["parent"] = parent
    return bool(messagebox.askyesno(title, message, **kwargs))


def show_message(window, title, message):
    """モーダルな通知ダイアログを開く。"""
    parent = _tk_parent(window)
    kwargs = {}
    if parent is not None:
        kwargs["parent"] = parent
    messagebox.showinfo(title, message, **kwargs)


# ---------------------------------------------------------------- 取込管理

def get_pending_import(conn, store_id):
    """指定店舗の未完了の取込行を返す。無ければ None。
    未完了とは history / stats のどちらかが未取込の行を指す。
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 取込ID, 年月, historyファイル名, statsファイル名
        FROM imports
        WHERE 店舗ID = ?
          AND (historyファイル名 IS NULL OR statsファイル名 IS NULL)
        """,
        (store_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {
        "取込ID": row[0],
        "年月": row[1],
        "history": row[2],
        "stats": row[3],
    }


def create_import(conn, store_id, month):
    """新しい取込行を作成し、取込IDを返す。"""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO imports (店舗ID, 年月, 取込日時)
        VALUES (?, ?, ?)
        """,
        (store_id, month, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    return cur.lastrowid


def delete_import(conn, import_id):
    """取込IDに紐づく history / stats と取込行をまとめて削除する。"""
    cur = conn.cursor()
    cur.execute("DELETE FROM history WHERE 取込ID = ?", (import_id,))
    h = cur.rowcount
    cur.execute("DELETE FROM stats WHERE 取込ID = ?", (import_id,))
    s = cur.rowcount
    cur.execute("DELETE FROM imports WHERE 取込ID = ?", (import_id,))
    conn.commit()
    return h, s


def get_import_rows(conn, store_map):
    """元データタブに表示する取込一覧を返す。
    戻り値は (rows, ids)。ids は行と同じ並びの取込IDのリスト。
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 取込ID, 店舗ID, 年月, historyファイル名, statsファイル名,
               history件数, stats件数
        FROM imports
        ORDER BY 取込ID DESC
        """
    )
    rows = []
    ids = []
    for iid, sid, month, hname, sname, hcnt, scnt in cur.fetchall():
        ids.append(iid)
        rows.append([
            store_map.get(sid, str(sid)),
            month or "",
            "－" if not hname else shorten_csv_name(hname),
            "－" if not sname else shorten_csv_name(sname),
            "－" if hcnt is None else f"{hcnt}",
            "－" if scnt is None else f"{scnt}",
        ])
    return rows, ids


# ---------------------------------------------------------------- 集計

def get_summary(conn, store_id):
    """選択店舗の history 件数と期間を表す文字列を返す。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*), MIN(日時), MAX(日時) FROM history WHERE 店舗ID = ?",
        (store_id,),
    )
    cnt, dmin, dmax = cur.fetchone()
    cnt = cnt or 0
    if cnt == 0:
        return "全0件"
    dt_min = parse_dt(dmin)
    dt_max = parse_dt(dmax)
    if dt_min and dt_max:
        span = f"{dt_min.month}/{dt_min.day} ～ {dt_max.month}/{dt_max.day}"
    else:
        span = f"{dmin} ～ {dmax}"
    return f"全{cnt}件（{span}）"


def get_stocktake_dates(conn, store_id):
    """在庫操作タイプ='棚卸し' の 日時 からユニークな日付(yyyy-mm-dd)を返す。"""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT substr(日時, 1, 10) AS d
        FROM history
        WHERE 在庫操作タイプ = '棚卸し' AND 店舗ID = ?
        ORDER BY d DESC
        """,
        (store_id,),
    )
    return [r[0] for r in cur.fetchall() if r[0]]


def get_stocktake_rows(conn, store_id, date_str):
    """選択日付の棚卸し差異を返す。戻り値は (rows, total)。
    rows の列は 商品名, 差異(在庫変更数), 単価, 差異金額。
    単価は取込時に指定した年月と店舗で stats を結合して求める。
    棚卸し日が月をまたぐ週に含まれても、締め単位である年月列で紐づく。
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            h.商品名,
            h.在庫変更数,
            s.単価,
            CAST(h.在庫変更数 AS REAL) * COALESCE(s.単価, 0) AS 差異金額
        FROM history h
        LEFT JOIN stats s
          ON h.商品ID = s.商品ID
         AND h.年月 = s.年月
         AND h.店舗ID = s.店舗ID
        WHERE h.在庫操作タイプ = '棚卸し'
          AND h.店舗ID = ?
          AND substr(h.日時, 1, 10) = ?
          AND CAST(h.在庫変更数 AS REAL) <> 0
        ORDER BY h.商品名
        """,
        (store_id, date_str),
    )
    result = []
    total = 0.0
    for name, henka, tanka, kingaku in cur.fetchall():
        total += kingaku
        result.append([
            name,
            henka,
            "－" if tanka is None else f"{tanka:g}",
            f"{kingaku:g}円",
        ])
    return result, total


def get_sales_months(conn, store_id):
    """選択店舗の注文データが存在する年月を新しい順に返す。
    カレンダー上の日付ではなく、取込時に指定した締め単位の年月を使う。
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT 年月
        FROM history
        WHERE 在庫操作タイプ = '注文' AND 店舗ID = ?
        ORDER BY 年月 DESC
        """,
        (store_id,),
    )
    return [r[0] for r in cur.fetchall() if r[0]]


def get_sales_rows(conn, store_id, month_str):
    """選択年月・選択店舗の月別売上を返す。戻り値は (records, total)。
    records の各要素は (商品名, 単価, 売上数, 売上金額) で、
    単価が未登録の場合の単価は None。
    注文の在庫変更数はマイナスのため -1 倍して売上数とする。
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            MAX(h.商品名) AS 商品名,
            MAX(s.単価) AS 単価,
            SUM(-CAST(h.在庫変更数 AS REAL)) AS 売上数
        FROM history h
        LEFT JOIN stats s
          ON h.商品ID = s.商品ID
         AND h.年月 = s.年月
         AND h.店舗ID = s.店舗ID
        WHERE h.在庫操作タイプ = '注文'
          AND h.店舗ID = ?
          AND h.年月 = ?
        GROUP BY h.商品コード
        """,
        (store_id, month_str),
    )
    records = []
    total = 0.0
    for name, tanka, urisuu in cur.fetchall():
        kingaku = 0.0 if tanka is None else urisuu * tanka
        total += kingaku
        records.append((name, tanka, urisuu, kingaku))
    return records, total


# 月別売上テーブルの列定義（見出しと並び替えに使用）
SALES_COLUMNS = ["商品名", "単価", "売上数", "売上金額"]
# 初期並び替え列（売上数）と方向（降順）
SALES_DEFAULT_SORT_COL = 2
SALES_DEFAULT_SORT_DESC = True


def format_sales_rows(records):
    """数値付きレコードを表示用の文字列行に整形する。"""
    rows = []
    for name, tanka, urisuu, kingaku in records:
        rows.append([
            name,
            "－" if tanka is None else f"{tanka:g}",
            f"{urisuu:g}",
            f"{kingaku:g}円",
        ])
    return rows


def sort_sales_records(records, col_index, descending):
    """レコードを指定列で並び替える。
    商品名(0)は文字列比較、単価・売上数・売上金額(1-3)は数値比較。
    単価が None の行は数値比較で最小値として扱う。
    """
    def key(r):
        v = r[col_index]
        return -float("inf") if v is None else v

    return sorted(records, key=key, reverse=descending)


# ---------------------------------------------------------------- 取り込み

def read_csv(path):
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            with open(path, newline="", encoding=enc) as f:
                rows = list(csv.reader(f))
            return rows
        except UnicodeDecodeError:
            continue
    raise ValueError("文字コードを判別できません")


def import_history(conn, path, store_id, month, import_id):
    """history CSV を指定店舗・指定年月の取込として登録する。
    同一店舗内で操作IDが重複する行はスキップする。
    """
    rows = read_csv(path)
    if not rows:
        return "ファイルが空です", 0
    header = [c.strip() for c in rows[0]]
    if header != HISTORY_HEADER:
        return "ヘッダーが history 形式と一致しません", 0

    cur = conn.cursor()
    added = 0
    skipped = 0
    for row in rows[1:]:
        if len(row) < len(HISTORY_HEADER):
            continue
        row = row[:len(HISTORY_HEADER)]
        cur.execute(
            """
            INSERT OR IGNORE INTO history (
                操作ID, 商品ID, 商品名, 商品コード, 在庫操作タイプ,
                在庫変更数, 操作後在庫, 理論賞味期限, 日時,
                店舗ID, 年月, 取込ID
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            row + [store_id, month, import_id],
        )
        if cur.rowcount:
            added += 1
        else:
            skipped += 1
    cur.execute(
        """
        UPDATE imports
        SET historyファイル名 = ?, history件数 = ?
        WHERE 取込ID = ?
        """,
        (os.path.basename(path), added, import_id),
    )
    conn.commit()
    return f"追加 {added} 件 / 重複スキップ {skipped} 件", added


def import_stats(conn, path, store_id, month, import_id):
    """stats CSV を指定店舗・指定年月の単価として登録する。
    同一 (店舗ID, 商品ID, 年月) は常に上書きする。
    戻り値は (メッセージ, 登録件数, conflicts)。
    conflicts は既存と単価が異なっていた商品の一覧。
    """
    rows = read_csv(path)
    if not rows:
        return "ファイルが空です", 0, []
    header = [c.strip() for c in rows[0]]
    if header != STATS_HEADER:
        return "ヘッダーが stats 形式と一致しません", 0, []

    cur = conn.cursor()
    added = 0
    updated = 0
    invalid = 0
    conflicts = []
    for row in rows[1:]:
        if len(row) < len(STATS_HEADER):
            continue
        pid = row[0].strip()
        name = row[1].strip()
        try:
            uriage = float(row[2])
            urisuu = float(row[3])
        except ValueError:
            invalid += 1
            continue
        if urisuu == 0:
            invalid += 1
            continue
        tanka = uriage / urisuu

        cur.execute(
            """
            SELECT 単価 FROM stats
            WHERE 店舗ID = ? AND 商品ID = ? AND 年月 = ?
            """,
            (store_id, pid, month),
        )
        existing = cur.fetchone()
        if existing is None:
            added += 1
        else:
            updated += 1
            if existing[0] != tanka:
                conflicts.append(
                    f"商品ID {pid} {name}: "
                    f"既存 {existing[0]:g} → 新規 {tanka:g}"
                )
        cur.execute(
            """
            INSERT INTO stats (店舗ID, 商品ID, 年月, 商品名, 単価, 取込ID)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(店舗ID, 商品ID, 年月) DO UPDATE SET
                商品名 = excluded.商品名,
                単価 = excluded.単価,
                取込ID = excluded.取込ID
            """,
            (store_id, pid, month, name, tanka, import_id),
        )
    cur.execute(
        """
        UPDATE imports
        SET statsファイル名 = ?, stats件数 = ?
        WHERE 取込ID = ?
        """,
        (os.path.basename(path), added + updated, import_id),
    )
    conn.commit()
    return (
        f"{month} 分: 新規 {added} 件 / 上書き {updated} 件 / "
        f"不正データ {invalid} 件",
        added + updated,
        conflicts,
    )


def export_sales_data(conn, store_id, store_name):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            h.操作ID,
            h.商品ID,
            h.商品名,
            COALESCE(s.単価, 0) AS 単価,
            -CAST(h.在庫変更数 AS REAL) AS 売上数,
            h.日時
        FROM history h
        LEFT JOIN stats s
          ON h.商品ID = s.商品ID
         AND h.年月 = s.年月
         AND h.店舗ID = s.店舗ID
        WHERE h.在庫操作タイプ = '注文'
          AND h.店舗ID = ?
        ORDER BY h.日時
        """,
        (store_id,),
    )

    rows = cur.fetchall()
    if not rows:
        return "エクスポート対象がありません"

    columns = ['操作ID', '商品ID', '商品名', '単価', '売上数', '日時']
    df = pd.DataFrame(rows, columns=columns)
    # 日時を文字列から datetime 型へ変換する
    df['日時'] = pd.to_datetime(df['日時'], errors='coerce')

    try:
        with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
            sheet_name = '売上'
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]

            n_rows, n_cols = df.shape
            ref = f"A1:{get_column_letter(n_cols)}{n_rows + 1}"
            table = Table(displayName="売上テーブル", ref=ref)
            table.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2",
                showRowStripes=True,
            )
            ws.add_table(table)

            # ヘッダー行のフォントを白・太字にする
            header_font = Font(color="FFFFFF", bold=True)
            for cell in ws[1]:
                cell.font = header_font

            # 日時列に datetime 書式を設定する
            dt_col_idx = columns.index('日時') + 1
            dt_letter = get_column_letter(dt_col_idx)
            for r in range(2, n_rows + 2):
                ws[f"{dt_letter}{r}"].number_format = "yyyy-mm-dd hh:mm:ss"

            narrow_cols = {'商品ID', '操作ID'}
            for i, col in enumerate(columns, start=1):
                letter = get_column_letter(i)
                if col in narrow_cols:
                    ws.column_dimensions[letter].width = 2.00
                    continue
                if col == '日時':
                    ws.column_dimensions[letter].width = 21
                    continue
                max_len = max(
                    [len(str(col))]
                    + [len(str(v)) for v in df[col].tolist()]
                )
                ws.column_dimensions[letter].width = max_len + 4
        return f"{store_name}: エクスポート完了 {len(rows)} 件"
    except Exception as e:
        return f"エクスポートエラー: {str(e)}"


# ---------------------------------------------------------------- 画面

TABLE_FONT_SIZE = 12
TAB_FONT_SIZE = TABLE_FONT_SIZE

STORE_BTN_KEY = "-STORE-{}-"
STORE_BTN_WIDTH = 12

# Windows 標準のグレー系画面に馴染むよう、彩度を抑えて明度差で
# 選択状態を示す配色にする。店舗ボタンを濃く、タブをやや淡くして
# 切り替えの階層が視覚的に伝わるようにする。
COLOR_IDLE_BG = "#e1e1e1"
COLOR_IDLE_FG = "#5a5a5a"
COLOR_HOVER_BG = "#cdcdcd"
COLOR_BORDER = "#b0b0b0"
COLOR_STORE_ON_BG = "#37474f"
COLOR_TAB_ON_BG = "#546e7a"
COLOR_ON_FG = "#ffffff"

TAB_STYLE = "Main.TNotebook"

SOURCE_COLUMNS = ["店舗", "年月", "historyファイル", "statsファイル",
                  "history件数", "stats件数"]


def format_total(total):
    """差異合計の表示文字列を返す。値が正のときは + を付ける。"""
    sign = "+" if total > 0 else ""
    return f"差異合計　{sign}{total:g}円"


def format_sales_total(total):
    """月度売上金額の表示文字列を返す。プラス記号は付けない。"""
    return f"月度売上金額　{total:g}円"


def build_store_row(stores):
    """店舗定義から店舗切り替えボタンの行を組み立てる。
    ボタンは stores.ini の内容に応じて動的に生成する。
    後処理で等分割になるように調整される。
    """
    row = []
    for st in stores:
        row.append(
            eg.Button(
                st["name"],
                key=STORE_BTN_KEY.format(st["id"]),
                size=(1, 1),  # 最小サイズのみ指定、後で動的調整
            )
        )
    return row


def build_import_tab():
    """データ取り込みタブのレイアウトを返す。"""
    return [
        [eg.Text("", key="-SUMMARY-", font=("", 16))],
        [
            eg.Button("history 取込", key="-HISTORY-", size=(18, 1)),
            eg.Button("stats 取込", key="-STATS-", size=(18, 1)),
        ],
        [eg.Text("", key="-MSG-IMPORT-", size=(50, 2))],
        [
            eg.Push(),
            eg.Button("Excel出力", key="-EXPORT-ALLTIME-"),
        ],
    ]


def build_sales_tab():
    """月別売上タブのレイアウトを返す。"""
    return [
        [
            eg.Text("年月", font=("", 14)),
            eg.Combo([], key="-SALES-MONTH-", readonly=True),
            eg.Button("表示", key="-SALES-SHOW-"),
        ],
        [
            eg.Push(),
            eg.Text(
                format_sales_total(0.0),
                key="-SALES-TOTAL-", font=("", 14),
            ),
        ],
        [
            eg.Table(
                [],
                headings=SALES_COLUMNS,
                key="-SALES-TABLE-",
                auto_size_columns=False,
                col_widths=[33, 4, 4, 8],
                expand_x=True,
                expand_y=True,
            )
        ],
    ]


def build_stock_tab():
    """棚卸し差異確認タブのレイアウトを返す。"""
    return [
        [
            eg.Text("棚卸し日付", font=("", 14)),
            eg.Combo([], key="-STOCK-DATE-", readonly=True),
            eg.Button("表示", key="-STOCK-SHOW-"),
        ],
        [
            eg.Push(),
            eg.Text(
                format_total(0.0),
                key="-STOCK-TOTAL-", font=("", 14),
            ),
        ],
        [
            eg.Table(
                [],
                headings=["商品名", "差異", "単価", "差異金額"],
                key="-STOCK-TABLE-",
                auto_size_columns=False,
                col_widths=[33, 4, 5, 7],
                expand_x=True,
                expand_y=True,
            )
        ],
    ]


def build_source_tab():
    """元データタブのレイアウトを返す。
    取込単位の一覧を表示し、選択した取込をまとめて削除できる。
    """
    return [
        [
            eg.Text("取り込み履歴（全店舗）", font=("", 14)),
            eg.Push(),
            eg.Button("選択した取込を削除", key="-SRC-DELETE-"),
        ],
        [
            eg.Table(
                [],
                headings=SOURCE_COLUMNS,
                key="-SRC-TABLE-",
                auto_size_columns=False,
                col_widths=[8, 8, 18, 18, 6, 6],
                expand_x=True,
                expand_y=True,
            )
        ],
    ]


def build_window(stores):
    """タブ構成のウィンドウを生成して返す。
    店舗切り替えボタンはタブの上に置き、全タブが選択店舗に従う。
    """
    layout = [
        [eg.Text("お菓子屋さん売上データ集約くん", font=("", 18))],
        [eg.Text("", font=("", 10))],
        build_store_row(stores),
        [
            eg.TabGroup(
                [[
                    eg.Tab("データ取り込み", build_import_tab(),
                           key="-TAB-IMPORT-"),
                    eg.Tab("月別売上", build_sales_tab(), key="-TAB-SALES-"),
                    eg.Tab("棚卸し差異確認", build_stock_tab(),
                           key="-TAB-STOCK-"),
                    eg.Tab("元データ", build_source_tab(), key="-TAB-SRC-"),
                ]],
                key="-TABGROUP-",
                expand_x=True,
                expand_y=True,
            )
        ],
        [eg.Push(), eg.Button("終了", key="-EXIT-")],
    ]

    window = eg.Window(
        "お菓子屋さん売上データ集約くん", layout,
        font=("", 14), size=(640, 560),
    )
    _init_styles()
    _apply_tab_style(window)
    _apply_store_button_style(window, stores)
    _adjust_store_button_width(window, stores)
    _apply_table_style(window, "-SALES-TABLE-", "Sales")
    _apply_table_style(window, "-STOCK-TABLE-", "Stock")
    _apply_table_style(window, "-SRC-TABLE-", "Source")
    _apply_align(window, "-SALES-TABLE-", ["w", "e", "e", "e"])
    _apply_align(window, "-STOCK-TABLE-", ["w", "e", "e", "e"])
    _apply_align(window, "-SRC-TABLE-", ["w", "w", "w", "w", "e", "e"])
    return window


def _init_styles():
    """タブの ttk.Style を定義する。
    店舗ボタンの実体は tkinter.Button（ttk ではない）ため、
    そちらは Style ではなくウィジェットのオプションで配色する。
    """
    style = ttk.Style()
    # clam テーマは背景色指定が確実に反映される
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # タブ見出し
    style.configure(
        TAB_STYLE,
        background=COLOR_BORDER,
        borderwidth=0,
        tabmargins=(4, 4, 4, 0),
    )
    style.configure(
        TAB_STYLE + ".Tab",
        font=("", TAB_FONT_SIZE),
        padding=(14, 8),
        background=COLOR_IDLE_BG,
        foreground=COLOR_IDLE_FG,
        bordercolor=COLOR_BORDER,
        borderwidth=1,
    )
    style.map(
        TAB_STYLE + ".Tab",
        background=[("selected", COLOR_TAB_ON_BG),
                    ("active", COLOR_HOVER_BG)],
        foreground=[("selected", COLOR_ON_FG)],
        expand=[("selected", (1, 1, 1, 0))],
    )


def _apply_tab_style(window):
    """TabGroup 内部の ttk.Notebook に専用スタイルを割り当てる。
    TkEasyGUI の Tab/TabGroup はタブ見出しの font 指定に対応しない。
    """
    try:
        window["-TABGROUP-"].widget.configure(style=TAB_STYLE)
    except Exception:
        pass


def _adjust_store_button_width(window, stores):
    """店舗ボタンをウィンドウ幅に応じて等分割に調整する。
    ウィンドウ表示後に呼び出す必要がある。
    """
    import tkinter as tk
    
    try:
        # ウィンドウのジオメトリを確定させる
        window.window.update_idletasks()
        
        # 最初のボタンを取得
        first_btn = _store_button_widget(window, stores[0]["id"])
        if first_btn is None:
            return
        
        # ボタンの親フレームを取得
        parent = first_btn.master
        if parent is None:
            return
        
        # 親フレームのジオメトリを更新して幅を取得
        parent.update_idletasks()
        parent_width = parent.winfo_width()
        
        # ボタン数で等分割
        num_buttons = len(stores)
        button_width_rel = 1.0 / num_buttons
        
        # 各ボタンを place() で相対位置・相対幅で配置（等分割）
        for i, st in enumerate(stores):
            btn = _store_button_widget(window, st["id"])
            if btn is not None:
                btn.place(
                    relx=i * button_width_rel,
                    rely=0,
                    relwidth=button_width_rel,
                    relheight=1,
                )
    except Exception as e:
        # エラーが発生しても処理を続ける
        pass


def _store_button_widget(window, store_id):
    """店舗ボタンの tk ウィジェットを返す。取得できなければ None。"""
    try:
        return window[STORE_BTN_KEY.format(store_id)].widget
    except Exception:
        return None


def _apply_store_button_style(window, stores):
    """店舗ボタンの共通の見た目を設定する。
    実体は tkinter.Button なので、ttk の style ではなく
    ウィジェット自身のオプションで指定する。
    ボタンはウィンドウ幅に応じて等分割される（expand_x=True）。
    """
    for st in stores:
        w = _store_button_widget(window, st["id"])
        if w is None:
            continue
        try:
            w.configure(
                padx=6,
                pady=4,
                borderwidth=2,
                highlightthickness=0,
                takefocus=0,
            )
        except Exception:
            # ttk 実装の場合は何もしない
            pass


def _apply_table_style(window, key, style_prefix):
    """テーブルのセル・見出しフォントを ttk.Style で設定する。
    Treeview の行フォントはウィジェットの font 引数では反映されないため、
    専用スタイルを割り当ててフォントと行高を設定する。
    """
    try:
        tree = window[key].widget
        style = ttk.Style()
        style_name = f"{style_prefix}.Treeview"
        style.configure(
            style_name,
            font=("", TABLE_FONT_SIZE),
            rowheight=int(TABLE_FONT_SIZE * 2.0),
        )
        style.configure(style_name + ".Heading", font=("", TABLE_FONT_SIZE))
        tree.configure(style=style_name)
    except Exception:
        pass


def _apply_align(window, key, anchors):
    """テーブルの各列の文字揃えを設定する。
    anchors は列数ぶんの "w"（左揃え）/"e"（右揃え）のリスト。
    """
    try:
        tree = window[key].widget
        for i, anchor in enumerate(anchors, start=1):
            tree.column(i, anchor=anchor)
    except Exception:
        pass


def _set_button_text(window, key, text):
    """ボタンのラベルを動的に変更する。
    TkEasyGUI のバージョン差を吸収するため、update が効かない場合は
    内部の tk ウィジェットを直接書き換える。
    """
    try:
        window[key].update(text=text)
        return
    except Exception:
        pass
    try:
        window[key].widget.configure(text=text)
    except Exception:
        pass


def _set_store_button_state(window, store_id, selected):
    """店舗ボタンの選択状態を配色と立体表現で示す。
    実体が tkinter.Button のため、bg / fg に加えて
    マウスが乗ったときの activebackground / activeforeground も
    指定する。これを省くとホバーで既定のグレーに戻る。
    選択中は relief を sunken にして押し込まれた見た目にする。
    """
    w = _store_button_widget(window, store_id)
    if w is None:
        return
    if selected:
        opts = {
            "bg": COLOR_STORE_ON_BG,
            "fg": COLOR_ON_FG,
            "activebackground": COLOR_STORE_ON_BG,
            "activeforeground": COLOR_ON_FG,
            "relief": "sunken",
            "font": ("", TAB_FONT_SIZE, "bold"),
        }
    else:
        opts = {
            "bg": COLOR_IDLE_BG,
            "fg": COLOR_IDLE_FG,
            "activebackground": COLOR_HOVER_BG,
            "activeforeground": COLOR_IDLE_FG,
            "relief": "raised",
            "font": ("", TAB_FONT_SIZE),
        }
    try:
        w.configure(**opts)
        return
    except Exception:
        pass
    # 環境によっては Button が ttk 実装のことがある。その場合は
    # 上の tk 用オプションが効かないため、Style 経由で配色する。
    try:
        style_name = f"Store{store_id}.TButton"
        style = ttk.Style()
        bg = opts["bg"]
        fg = opts["fg"]
        style.configure(
            style_name, background=bg, foreground=fg,
            font=opts["font"], relief=opts["relief"],
            lightcolor=bg, darkcolor=bg, bordercolor=bg,
        )
        style.map(
            style_name,
            background=[("active", opts["activebackground"]),
                        ("pressed", opts["activebackground"]),
                        ("!active", bg)],
            foreground=[("active", opts["activeforeground"]),
                        ("pressed", opts["activeforeground"]),
                        ("!active", fg)],
        )
        w.configure(style=style_name)
    except Exception:
        pass


def _refresh_combo(window, key, items):
    """Combo の選択肢を最新化する。現在の選択値が残っていれば維持する。"""
    try:
        cb = window[key].widget
    except Exception:
        return
    try:
        current = cb.get()
    except Exception:
        current = ""
    try:
        cb.configure(values=items)
    except Exception:
        return
    if current in items:
        try:
            cb.set(current)
        except Exception:
            pass
    else:
        try:
            cb.set("")
        except Exception:
            pass


def _get_selected_row_index(window, key):
    """テーブルで選択されている行の位置を返す。未選択なら None。"""
    try:
        tree = window[key].widget
        sel = tree.selection()
        if not sel:
            return None
        return tree.index(sel[0])
    except Exception:
        return None


def _update_sales_headings(window, state):
    """月別売上テーブルの見出しに現在のソート方向(▲/▼)を表示する。"""
    try:
        tree = window["-SALES-TABLE-"].widget
        for i, name in enumerate(SALES_COLUMNS):
            arrow = ""
            if state["sort_col"] == i:
                arrow = " ▼" if state["sort_desc"] else " ▲"
            tree.heading(i + 1, text=name + arrow)
    except Exception:
        pass


def _setup_sales_sort(window, state):
    """月別売上テーブルの見出しクリックで並び替えできるようにする。
    表示値には '円' が付くため、並び替えは数値付きレコード(state["records"])
    に対して行い、整形し直してテーブルを更新する。
    """
    try:
        tree = window["-SALES-TABLE-"].widget
    except Exception:
        return

    def make_command(col_index):
        def command():
            if state["sort_col"] == col_index:
                state["sort_desc"] = not state["sort_desc"]
            else:
                state["sort_col"] = col_index
                # 数値列は降順、文字列(商品名)は昇順を初期方向にする
                state["sort_desc"] = col_index != 0
            state["records"] = sort_sales_records(
                state["records"], col_index, state["sort_desc"]
            )
            window["-SALES-TABLE-"].update(
                format_sales_rows(state["records"])
            )
            _update_sales_headings(window, state)
        return command

    for i in range(len(SALES_COLUMNS)):
        try:
            tree.heading(i + 1, command=make_command(i))
        except Exception:
            pass


def _setup_tab_refresh(window, state):
    """タブ切り替え時に選択肢と一覧を最新化する。
    ttk.Notebook の <<NotebookTabChanged>> を捕捉し、タブへ移った
    タイミングでデータベースを読み直す。
    """
    try:
        nb = window["-TABGROUP-"].widget
    except Exception:
        return

    def on_tab_changed(_event=None):
        refresh_selectors(window, state)
        refresh_source_table(window, state)

    try:
        nb.bind("<<NotebookTabChanged>>", on_tab_changed, add="+")
    except Exception:
        pass


# ---------------------------------------------------------------- 状態反映

def refresh_selectors(window, state):
    """選択店舗に応じて年月・棚卸し日付の選択肢を読み直す。"""
    conn = state["conn"]
    sid = state["store_id"]
    if conn is None or sid is None:
        return
    _refresh_combo(window, "-SALES-MONTH-", get_sales_months(conn, sid))
    _refresh_combo(window, "-STOCK-DATE-", get_stocktake_dates(conn, sid))


def refresh_source_table(window, state):
    """元データタブの取込一覧を読み直す。"""
    conn = state["conn"]
    if conn is None:
        return
    rows, ids = get_import_rows(conn, state["store_map"])
    state["import_ids"] = ids
    window["-SRC-TABLE-"].update(rows)


def refresh_import_buttons(window, state):
    """取込状態に応じて取込ボタンのラベルを切り替える。
    未完了の取込がある店舗では、残っている側のボタンに継続表示を出す。
    """
    conn = state["conn"]
    sid = state["store_id"]
    if conn is None or sid is None:
        return
    pending = get_pending_import(conn, sid)
    state["pending"] = pending
    if pending is None:
        _set_button_text(window, "-HISTORY-", "history 取込")
        _set_button_text(window, "-STATS-", "stats 取込")
        return
    month = pending["年月"] or ""
    if pending["history"] is None:
        _set_button_text(window, "-HISTORY-", f"history 取込（{month}）")
    else:
        _set_button_text(window, "-HISTORY-", "history 取込")
    if pending["stats"] is None:
        _set_button_text(window, "-STATS-", f"stats 取込（{month}）")
    else:
        _set_button_text(window, "-STATS-", "stats 取込")


def select_store(window, state, store_id):
    """店舗を切り替え、画面全体を選択店舗の内容に更新する。"""
    state["store_id"] = store_id
    state["store_name"] = state["store_map"].get(store_id, "")
    for sid in state["store_map"]:
        _set_store_button_state(window, sid, sid == store_id)

    window["-SUMMARY-"].update(get_summary(state["conn"], store_id))
    window["-MSG-IMPORT-"].update("")
    window["-SALES-TABLE-"].update([])
    window["-SALES-TOTAL-"].update(format_sales_total(0.0))
    window["-STOCK-TABLE-"].update([])
    window["-STOCK-TOTAL-"].update(format_total(0.0))
    state["sales"]["records"] = []
    refresh_selectors(window, state)
    refresh_import_buttons(window, state)


def resolve_import_target(window, state, path):
    """取り込み先の (取込ID, 年月) を決める。
    未完了の取込があればその取込IDと年月を使い、無ければ年月を
    確認したうえで新しい取込IDを発番する。中止した場合は None を返す。
    """
    conn = state["conn"]
    sid = state["store_id"]
    pending = get_pending_import(conn, sid)
    if pending is not None:
        return pending["取込ID"], pending["年月"]

    text = ask_text(
        window,
        "対象年月",
        f"{state['store_name']}\n{os.path.basename(path)}\n"
        "対象年月を yyyy-mm で入力してください",
        guess_month_from_name(path),
    )
    if text is None:
        return None
    month = normalize_month(text)
    if month is None:
        return None
    return create_import(conn, sid, month), month


def main():
    stores = load_stores()
    if not stores:
        messagebox.showerror("エラー", "stores.ini を読み込めません")
        return
    if not os.path.exists(DB_PATH):
        messagebox.showerror("エラー", "データベースが見つかりません")
        return

    conn = init_db()
    state = {
        "conn": conn,
        "stores": stores,
        "store_map": {st["id"]: st["name"] for st in stores},
        "store_id": None,
        "store_name": "",
        "pending": None,
        "import_ids": [],
        "sales": {
            "records": [],
            "sort_col": SALES_DEFAULT_SORT_COL,
            "sort_desc": SALES_DEFAULT_SORT_DESC,
        },
    }

    window = build_window(stores)
    _setup_sales_sort(window, state["sales"])
    _setup_tab_refresh(window, state)
    select_store(window, state, stores[0]["id"])
    refresh_source_table(window, state)

    while True:
        event, values = window.read()
        if event in (eg.WIN_CLOSED, None, "-EXIT-"):
            break

        if isinstance(event, str) and event.startswith("-STORE-"):
            try:
                sid = int(event.strip("-").split("-")[1])
            except (IndexError, ValueError):
                continue
            select_store(window, state, sid)
            continue

        if event == "-STOCK-SHOW-":
            sel = values.get("-STOCK-DATE-", "")
            if sel:
                rows, total = get_stocktake_rows(
                    conn, state["store_id"], sel
                )
                window["-STOCK-TABLE-"].update(rows)
                window["-STOCK-TOTAL-"].update(format_total(total))
            continue

        if event == "-SALES-SHOW-":
            sel = values.get("-SALES-MONTH-", "")
            if sel:
                records, total = get_sales_rows(conn, state["store_id"], sel)
                sales = state["sales"]
                # 初期表示は売上数の多い順（降順）
                sales["sort_col"] = SALES_DEFAULT_SORT_COL
                sales["sort_desc"] = SALES_DEFAULT_SORT_DESC
                sales["records"] = sort_sales_records(
                    records, SALES_DEFAULT_SORT_COL, SALES_DEFAULT_SORT_DESC
                )
                window["-SALES-TABLE-"].update(
                    format_sales_rows(sales["records"])
                )
                window["-SALES-TOTAL-"].update(format_sales_total(total))
                _update_sales_headings(window, sales)
            continue

        if event == "-HISTORY-":
            path = ask_open_file(
                window,
                f"{state['store_name']} の history CSV を選択",
                [("CSV", "*histories*.csv")],
            )
            if path:
                target = resolve_import_target(window, state, path)
                if target is None:
                    window["-MSG-IMPORT-"].update("取り込みを中止しました")
                else:
                    import_id, month = target
                    msg, _ = import_history(
                        conn, path, state["store_id"], month, import_id
                    )
                    window["-MSG-IMPORT-"].update(f"{month} 分: {msg}")
                    window["-SUMMARY-"].update(
                        get_summary(conn, state["store_id"])
                    )
                    refresh_selectors(window, state)
                    refresh_import_buttons(window, state)
                    refresh_source_table(window, state)

        elif event == "-STATS-":
            path = ask_open_file(
                window,
                f"{state['store_name']} の stats CSV を選択",
                [("CSV", "*statisctics*.csv")],
            )
            if path:
                target = resolve_import_target(window, state, path)
                if target is None:
                    window["-MSG-IMPORT-"].update("取り込みを中止しました")
                else:
                    import_id, month = target
                    msg, _, conflicts = import_stats(
                        conn, path, state["store_id"], month, import_id
                    )
                    window["-MSG-IMPORT-"].update(msg)
                    refresh_import_buttons(window, state)
                    refresh_source_table(window, state)
                    if conflicts:
                        show_message(
                            window,
                            "単価の上書き",
                            "同じ年月で単価が異なるデータを上書きしました：\n\n"
                            + "\n".join(conflicts),
                        )

        elif event == "-SRC-DELETE-":
            idx = _get_selected_row_index(window, "-SRC-TABLE-")
            if idx is None or idx >= len(state["import_ids"]):
                show_message(window, "削除", "削除する行を選択してください")
                continue
            import_id = state["import_ids"][idx]
            rows, _ = get_import_rows(conn, state["store_map"])
            info = rows[idx]
            ok = ask_yes_no(
                window,
                "取込の削除",
                f"取込ID {import_id} を削除します。\n\n"
                f"店舗: {info[0]}　年月: {info[1]}\n"
                f"history: {info[2]}（{info[4]} 件）\n"
                f"stats: {info[3]}（{info[5]} 件）\n\n"
                "この取込で登録したデータをすべて削除します。",
            )
            if ok:
                delete_import(conn, import_id)
                refresh_source_table(window, state)
                refresh_selectors(window, state)
                refresh_import_buttons(window, state)
                window["-SUMMARY-"].update(
                    get_summary(conn, state["store_id"])
                )

        elif event == "-EXPORT-ALLTIME-":
            window["-MSG-IMPORT-"].update(
                export_sales_data(
                    conn, state["store_id"], state["store_name"]
                )
            )

    window.close()
    conn.close()


if __name__ == "__main__":
    main()
