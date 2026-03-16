"""
Ahrefs キーワードランキング × Google Sheets コネクター

スプレッドシートの構造（スクリーンショットより）:
  上部セクション（行1〜5）:
    F列: "順位割合" / "1〜5位" / "6〜10位" / "11〜20位" / "20位〜"
    J〜N列: 各週の割合（%）
  キーワードテーブル（行6〜）:
    ヘッダー行:  B=キーワード, C=記事URL, D=注力KW, E=CV貢献数, F=検索Vol,
                 J〜N=週別順位（YYYY/MM/DD形式）, 順位変動列, 記事URL
    データ行: 上記に従うデータ
"""

import os
import re
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _build_service():
    credentials = service_account.Credentials.from_service_account_file(
        config.GCP_CREDENTIALS_PATH, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=credentials)


def _parse_date(s: str):
    """'2026/03/11' や '2026-03-11' 形式の文字列を date オブジェクトに変換。失敗したら None。"""
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except ValueError:
            pass
    return None


def get_ahrefs_data() -> dict:
    """
    Ahrefsスプレッドシートから順位分布と注力KWの最新順位を取得する。

    戻り値:
    {
        "sheet_updated": "2026/03/11",   # 最新データの週
        "ranking_distribution": {         # 順位分布（最新週）
            "1_5":   77.71,
            "6_10":  6.86,
            "11_20": 8.00,
            "20plus": 7.43,
        },
        "focus_keywords": [               # 注力KWのみ
            {
                "keyword":      "ecサイト運営",
                "current_rank": 6,
                "rank_change":  -13,
                "cv_contribution": 9,
                "search_vol":   1600,
            },
            ...
        ],
    }
    """
    service = _build_service()
    sheet_id   = config.AHREFS_SHEET_ID
    sheet_name = config.AHREFS_SHEET_NAME

    # シート全体を取得
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=sheet_name,
    ).execute()
    rows = result.get("values", [])

    if not rows:
        return {"sheet_updated": None, "ranking_distribution": {}, "focus_keywords": []}

    # ------------------------------------------------------------------ #
    # ① 順位分布（上部セクション）を解析
    #    F列（index 5）に "1〜5位" などのラベル、J列以降（index 9〜）に%値
    # ------------------------------------------------------------------ #
    dist_labels = {"1〜5位": "1_5", "6〜10位": "6_10", "11〜20位": "11_20", "20位〜": "20plus"}
    dist_data   = {}       # label_key -> list of (date, value)
    dist_col_dates = []    # 分布セクションの日付ヘッダー（行0か行1から取得）

    # 行0の J〜 から日付を探す
    if len(rows) > 0:
        header_row = rows[0]
        for i, cell in enumerate(header_row):
            d = _parse_date(cell)
            if d:
                dist_col_dates.append((i, d))

    for row in rows[:6]:  # 上部6行以内を探索
        if len(row) <= 5:
            continue
        label = str(row[5]).strip()   # F列（index 5）
        if label in dist_labels:
            key = dist_labels[label]
            values = []
            for col_idx, date in dist_col_dates:
                if col_idx < len(row):
                    raw = str(row[col_idx]).strip().replace("%", "").replace(",", ".")
                    try:
                        values.append((date, float(raw)))
                    except ValueError:
                        pass
            dist_data[key] = values

    # 最新の日付を特定
    latest_date = None
    for values_list in dist_data.values():
        for d, _ in values_list:
            if latest_date is None or d > latest_date:
                latest_date = d

    ranking_distribution = {}
    for key, values_list in dist_data.items():
        if not values_list:
            continue
        # 最新日付に最も近い値を使用
        if latest_date:
            closest = min(values_list, key=lambda x: abs((x[0] - latest_date).days))
            ranking_distribution[key] = closest[1]
        else:
            ranking_distribution[key] = values_list[-1][1]

    # ------------------------------------------------------------------ #
    # ② キーワードテーブルを解析
    #    ヘッダー行を探す（"キーワード" を含む行）
    # ------------------------------------------------------------------ #
    kw_header_idx = None
    for i, row in enumerate(rows):
        if any("キーワード" in str(cell) for cell in row):
            kw_header_idx = i
            break

    focus_keywords = []
    if kw_header_idx is not None:
        header = rows[kw_header_idx]

        # 日付列のインデックスを特定
        date_cols = []
        for i, cell in enumerate(header):
            d = _parse_date(cell)
            if d:
                date_cols.append((i, d))

        # 順位変動列（"順位変動" を含む列）
        rank_change_col = None
        for i, cell in enumerate(header):
            if "順位変動" in str(cell):
                rank_change_col = i
                break

        # 最新日付列
        latest_rank_col = None
        if date_cols:
            latest_entry = max(date_cols, key=lambda x: x[1])
            latest_rank_col = latest_entry[0]
            if latest_date is None:
                latest_date = latest_entry[1]

        # データ行を走査
        for row in rows[kw_header_idx + 1:]:
            if len(row) < 4:
                continue

            # B列（index 1）: キーワード
            keyword = str(row[1]).strip() if len(row) > 1 else ""
            if not keyword:
                continue

            # D列（index 3）: 注力KW（チェックボックス = TRUE/FALSE）
            focus_raw = str(row[3]).strip().upper() if len(row) > 3 else ""
            if focus_raw not in ("TRUE", "1", "☑", "✓", "✔"):
                continue  # 注力KWのみ

            # E列（index 4）: CV貢献数
            cv_raw = str(row[4]).strip() if len(row) > 4 else "0"
            try:
                cv = int(cv_raw.replace(",", ""))
            except ValueError:
                cv = 0

            # F列（index 5）: 検索Vol
            vol_raw = str(row[5]).strip() if len(row) > 5 else "0"
            try:
                search_vol = int(vol_raw.replace(",", ""))
            except ValueError:
                search_vol = 0

            # 最新順位
            current_rank = None
            if latest_rank_col is not None and latest_rank_col < len(row):
                rank_raw = str(row[latest_rank_col]).strip()
                try:
                    current_rank = int(rank_raw)
                except ValueError:
                    current_rank = None

            # 順位変動
            rank_change = None
            if rank_change_col is not None and rank_change_col < len(row):
                change_raw = str(row[rank_change_col]).strip()
                try:
                    rank_change = int(change_raw)
                except ValueError:
                    rank_change = None

            focus_keywords.append({
                "keyword":         keyword,
                "current_rank":    current_rank,
                "rank_change":     rank_change,
                "cv_contribution": cv,
                "search_vol":      search_vol,
            })

    return {
        "sheet_updated":       str(latest_date) if latest_date else None,
        "ranking_distribution": ranking_distribution,
        "focus_keywords":       focus_keywords,
    }
