import csv
import os
import sqlite3
from datetime import datetime, timedelta

import TkEasyGUI as eg
import pandas as pd

DB_PATH = "inventory.db"

HISTORY_HEADER = [
    "操作ID", "商品ID", "商品名", "商品コード",
    "在庫操作タイプ", "在庫変更数", "操作後在庫", "理論賞味期限", "日時",
]

STATS_HEADER = [
    "商品ID", "商品名（日本語）", "売上高（円）", "売上数", "注文件数",
]

SALES_HEADINGS = ["商品名", "単価", "売上数", "売上"]


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            操作ID TEXT PRIMARY KEY,
            商品ID TEXT,
            商品名 TEXT,
            商品コード TEXT,
            在庫操作タイプ TEXT,
            在庫変更数 TEXT,
            操作後在庫 TEXT,
            理論賞味期限 TEXT,
            日時 TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stats (
            商品ID TEXT PRIMARY KEY,
            商品名 TEXT,
            単価 REAL
        )
        """
    )
    conn.commit()
    _migrate_stats_table(conn)
    return conn


def _migrate_stats_table(conn):
    """旧スキーマ（商品IDの重複を許すstatsテーブル）を
    PRIMARY KEY付きのテーブルに移行し、重複行を排除する。
    重複がある場合は最後に取り込まれた行（rowidが最大のもの）を残す。
    """
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(stats)")
    has_pk = any(col[1] == "商品ID" and col[5] for col in cur.fetchall())
    if has_pk:
        return

    cur.execute(
        """
        CREATE TABLE stats_new (
            商品ID TEXT PRIMARY KEY,
            商品名 TEXT,
            単価 REAL
        )
        """
    )
    cur.execute(
        """
        INSERT INTO stats_new (商品ID, 商品名, 単価)
        SELECT 商品ID, 商品名, 単価 FROM stats
        WHERE rowid IN (SELECT MAX(rowid) FROM stats GROUP BY 商品ID)
        """
    )
    cur.execute("DROP TABLE stats")
    cur.execute("ALTER TABLE stats_new RENAME TO stats")
    conn.commit()


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


def get_summary(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), MIN(日時), MAX(日時) FROM history")
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


def read_csv(path):
    for enc in ("utf-8-sig", "cp932", "utf-8"):
        try:
            with open(path, newline="", encoding=enc) as f:
                rows = list(csv.reader(f))
            return rows
        except UnicodeDecodeError:
            continue
    raise ValueError("文字コードを判別できません")


def import_history(conn, path):
    rows = read_csv(path)
    if not rows:
        return "ファイルが空です"
    header = [c.strip() for c in rows[0]]
    if header != HISTORY_HEADER:
        return "ヘッダーが history 形式と一致しません"

    cur = conn.cursor()
    added = 0
    skipped = 0
    for row in rows[1:]:
        if len(row) < len(HISTORY_HEADER):
            continue
        row = row[:len(HISTORY_HEADER)]
        try:
            cur.execute(
                "INSERT INTO history VALUES (?,?,?,?,?,?,?,?,?)", row
            )
            added += 1
        except sqlite3.IntegrityError:
            skipped += 1
    conn.commit()
    return f"追加 {added} 件 / 重複スキップ {skipped} 件"


def import_stats(conn, path):
    rows = read_csv(path)
    if not rows:
        return "ファイルが空です", []
    header = [c.strip() for c in rows[0]]
    if header != STATS_HEADER:
        return "ヘッダーが stats 形式と一致しません", []

    cur = conn.cursor()
    added = 0
    skipped = 0
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
            skipped += 1
            continue
        if urisuu == 0:
            skipped += 1
            continue
        tanka = uriage / urisuu

        cur.execute(
            "SELECT 商品名, 単価 FROM stats WHERE 商品ID = ?", (pid,)
        )
        existing = cur.fetchone()
        if existing is not None:
            ex_name, ex_tanka = existing
            if ex_name != name or ex_tanka != tanka:
                conflicts.append(
                    f"商品ID {pid}: 既存({ex_name}, {ex_tanka:g}) / "
                    f"新規({name}, {tanka:g})"
                )

        cur.execute(
            """
            INSERT INTO stats (商品ID, 商品名, 単価) VALUES (?,?,?)
            ON CONFLICT(商品ID) DO UPDATE SET
                商品名 = excluded.商品名,
                単価 = excluded.単価
            """,
            (pid, name, tanka),
        )
        added += 1
    conn.commit()
    return f"追加 {added} 件 / スキップ {skipped} 件", conflicts


def calc_weekly_sales(conn, start_date):
    end_date = start_date + timedelta(days=7)
    start_s = start_date.strftime("%Y-%m-%d")
    end_s = end_date.strftime("%Y-%m-%d")

    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            h.商品ID,
            COALESCE(s.商品名, h.商品名) AS 商品名,
            COALESCE(s.単価, 0) AS 単価,
            -SUM(CAST(h.在庫変更数 AS REAL)) AS 売上数
        FROM history h
        LEFT JOIN stats s ON h.商品ID = s.商品ID
        WHERE h.在庫操作タイプ = '注文'
          AND substr(h.日時, 1, 10) >= ?
          AND substr(h.日時, 1, 10) < ?
        GROUP BY h.商品ID
        ORDER BY 売上数 DESC
        """,
        (start_s, end_s),
    )

    rows = []
    total = 0.0
    for pid, name, tanka, urisuu in cur.fetchall():
        urisuu = urisuu or 0
        uriage = urisuu * (tanka or 0)
        total += uriage
        rows.append([
            name,
            f"{tanka:g}",
            f"{urisuu:g}",
            f"{uriage:g}",
        ])
    return rows, total


def calc_monthly_sales(conn, year, month):
    # 次の月の初日を計算
    if month == 12:
        next_month_start = datetime(year + 1, 1, 1)
    else:
        next_month_start = datetime(year, month + 1, 1)

    start_s = f"{year:04d}-{month:02d}-01"
    end_s = next_month_start.strftime("%Y-%m-%d")

    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            h.商品ID,
            COALESCE(s.商品名, h.商品名) AS 商品名,
            COALESCE(s.単価, 0) AS 単価,
            -SUM(CAST(h.在庫変更数 AS REAL)) AS 売上数
        FROM history h
        LEFT JOIN stats s ON h.商品ID = s.商品ID
        WHERE h.在庫操作タイプ = '注文'
          AND substr(h.日時, 1, 10) >= ?
          AND substr(h.日時, 1, 10) < ?
        GROUP BY h.商品ID
        ORDER BY 売上数 DESC
        """,
        (start_s, end_s),
    )

    rows = []
    total = 0.0
    for pid, name, tanka, urisuu in cur.fetchall():
        urisuu = urisuu or 0
        uriage = urisuu * (tanka or 0)
        total += uriage
        rows.append([
            name,
            f"{tanka:g}",
            f"{urisuu:g}",
            f"{uriage:g}",
        ])
    return rows, total


def export_sales_data(conn, year=None, month=None):
    cur = conn.cursor()
    if year is not None and month is not None:
        if month == 12:
            next_month_start = datetime(year + 1, 1, 1)
        else:
            next_month_start = datetime(year, month + 1, 1)
        start_s = f"{year:04d}-{month:02d}-01"
        end_s = next_month_start.strftime("%Y-%m-%d")
        cur.execute(
            """
            SELECT
                h.操作ID,
                h.商品名,
                -CAST(h.在庫変更数 AS REAL) AS 売上数,
                COALESCE(s.単価, 0) AS 単価,
                h.日時
            FROM history h
            LEFT JOIN stats s ON h.商品ID = s.商品ID
            WHERE h.在庫操作タイプ = '注文'
              AND substr(h.日時, 1, 10) >= ?
              AND substr(h.日時, 1, 10) < ?
            ORDER BY h.日時
            """,
            (start_s, end_s),
        )
    else:
        cur.execute(
            """
            SELECT
                h.操作ID,
                h.商品名,
                -CAST(h.在庫変更数 AS REAL) AS 売上数,
                COALESCE(s.単価, 0) AS 単価,
                h.日時
            FROM history h
            LEFT JOIN stats s ON h.商品ID = s.商品ID
            WHERE h.在庫操作タイプ = '注文'
            ORDER BY h.日時
            """
        )

    rows = cur.fetchall()
    if not rows:
        return "エクスポート対象がありません"

    df = pd.DataFrame(rows, columns=['操作ID', '商品名', '売上数', '単価', '日時'])

    try:
        df.to_excel('okashiyasan.xlsx', index=False, engine='openpyxl')
        return f"エクスポート完了: {len(rows)} 件"
    except Exception as e:
        return f"エクスポートエラー: {str(e)}"


def main():
    # カレントディレクトリをこのスクリプトがある場所に設定
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    conn = init_db()

    import_tab = [
        [
            eg.Button("history 取込", key="-HISTORY-"),
            eg.Button("stats 取込", key="-STATS-"),
            eg.Button("Monthly Export", key="-EXPORT-"),
            eg.Button("AllTime Export", key="-EXPORT-ALLTIME-"),
        ],
        [eg.Text("", key="-MSG-IMPORT-", size=(50, 2))],
    ]

    stats_tab = [
        [
            eg.Text("開始日:"),
            eg.Input("", key="-DATE-", size=(12, 1)),
            eg.Button("選択", key="-PICK-"),
            eg.Button("週間売上を計算", key="-CALC-"),
            eg.Button("月間売上を計算", key="-CALC-MONTHLY-"),
        ],
        [eg.Table(
            values=[],
            headings=SALES_HEADINGS,
            key="-TABLE-",
            justification="left",
            auto_size_columns=False,
            vertical_scroll_only=True,
            height=10,
            col_widths=[20, 5, 5, 10],
            size=(None, 10),
        )],
        [eg.Text("売上合計: -", key="-TOTAL-", font=("", 14))],
        [eg.Text("", key="-MSG-STATS-", size=(50, 1))],
    ]

    layout = [
        [eg.Text(get_summary(conn), key="-SUMMARY-", font=("", 14))],
        [eg.TabGroup([
            [eg.Tab("データ取込", import_tab)],
            [eg.Tab("集計", stats_tab)],
        ], key="-TABGROUP-")],
    ]

    window = eg.Window("売上管理", layout)

    while True:
        event, values = window.read()
        if event in (eg.WIN_CLOSED, None):
            break

        if event == "-HISTORY-":
            path = eg.popup_get_file(
                "history CSV を選択", file_types=(("CSV", "*histories*.csv"),)
            )
            if path:
                msg = import_history(conn, path)
                window["-MSG-IMPORT-"].update(msg)
                window["-SUMMARY-"].update(get_summary(conn))

        elif event == "-STATS-":
            path = eg.popup_get_file(
                "stats CSV を選択", file_types=(("CSV", "*statisctics*.csv"),)
            )
            if path:
                msg, conflicts = import_stats(conn, path)
                window["-MSG-IMPORT-"].update(msg)
                if conflicts:
                    eg.popup(
                        "商品名または単価が異なる重複がありました：\n\n"
                        + "\n".join(conflicts)
                    )

        elif event == "-EXPORT-":
            now = datetime.now()
            msg = export_sales_data(conn, now.year, now.month)
            window["-MSG-IMPORT-"].update(msg)

        elif event == "-EXPORT-ALLTIME-":
            msg = export_sales_data(conn)
            window["-MSG-IMPORT-"].update(msg)

        elif event == "-PICK-":
            d = eg.popup_get_date()
            if d:
                if isinstance(d, (tuple, list)):
                    y, m, day = d[2], d[0], d[1]
                    d = datetime(int(y), int(m), int(day))
                if isinstance(d, datetime):
                    window["-DATE-"].update(d.strftime("%Y-%m-%d"))
                else:
                    window["-DATE-"].update(str(d))

        elif event == "-CALC-":
            start = parse_dt(values.get("-DATE-", ""))
            if start is None:
                window["-MSG-STATS-"].update("開始日を正しく指定してください")
                continue
            rows, total = calc_weekly_sales(conn, start)
            window["-TABLE-"].update(values=rows)
            window["-TOTAL-"].update(f"売上合計: {total:,.0f} 円")
            window["-MSG-STATS-"].update(
                f"{start.strftime('%Y-%m-%d')} から1週間分を集計しました"
            )

        elif event == "-CALC-MONTHLY-":
            start = parse_dt(values.get("-DATE-", ""))
            if start is None:
                window["-MSG-STATS-"].update("開始日を正しく指定してください")
                continue
            rows, total = calc_monthly_sales(conn, start.year, start.month)
            window["-TABLE-"].update(values=rows)
            window["-TOTAL-"].update(f"売上合計: {total:,.0f} 円")
            window["-MSG-STATS-"].update(
                f"{start.year}年{start.month}月分を集計しました"
            )

    window.close()
    conn.close()


if __name__ == "__main__":
    main()
