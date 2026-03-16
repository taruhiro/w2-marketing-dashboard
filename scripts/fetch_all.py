"""
W2 マーケティングダッシュボード データ取得スクリプト
実行すると data/dashboard.json を更新する

取得する3つの期間:
  current_month : 今月1日〜昨日
  last_month    : 先月1日〜先月末日
  last_30days   : 昨日から30日前〜昨日
"""

import json
import sys
import os
from datetime import date, timedelta
from pathlib import Path

# connectors フォルダを import パスに追加
sys.path.insert(0, str(Path(__file__).parent))

from connectors.ga4          import GA4Connector
from connectors.gsc          import GSCConnector
from connectors.google_ads   import GoogleAdsConnector
from connectors.salesforce   import get_all_salesforce_data
from connectors.facebook_ads import FacebookAdsConnector
from connectors.ahrefs_sheets import get_ahrefs_data
import config


# ------------------------------------------------------------------ #
# 期間定義
# ------------------------------------------------------------------ #
def get_periods():
    today = date.today()
    yesterday = today - timedelta(days=1)

    # 当月
    cur_start = today.replace(day=1)
    cur_end   = yesterday

    # 先月
    last_end   = cur_start - timedelta(days=1)
    last_start = last_end.replace(day=1)

    # 直近30日
    d30_start = yesterday - timedelta(days=29)
    d30_end   = yesterday

    def label(s, e):
        return f"{s.strftime('%Y/%m/%d')} 〜 {e.strftime('%Y/%m/%d')}"

    return {
        "current_month": {
            "label":   f"当月（{cur_start.strftime('%m')}月）",
            "range":   label(cur_start, cur_end),
            "start":   str(cur_start),
            "end":     str(cur_end),
            "sf_start": cur_start,
            "sf_end":   cur_end,
        },
        "last_month": {
            "label":   f"先月（{last_start.strftime('%m')}月）",
            "range":   label(last_start, last_end),
            "start":   str(last_start),
            "end":     str(last_end),
            "sf_start": last_start,
            "sf_end":   last_end,
        },
        "last_30days": {
            "label":   "直近30日",
            "range":   label(d30_start, d30_end),
            "start":   str(d30_start),
            "end":     str(d30_end),
            "sf_start": d30_start,
            "sf_end":   d30_end,
        },
    }


# ------------------------------------------------------------------ #
# 各コネクターでデータを取得
# ------------------------------------------------------------------ #
def fetch_period_data(period_key, period_info,
                      ga4, gsc, gads, fb):
    start = period_info["start"]
    end   = period_info["end"]
    sf_start = period_info["sf_start"]
    sf_end   = period_info["sf_end"]

    result = {
        "label": period_info["label"],
        "range": period_info["range"],
        "ga4": {},
        "gsc": {},
        "google_ads": {},
        "facebook_ads": {},
        "salesforce": {},
    }

    # GA4
    try:
        result["ga4"] = {
            "summary":    ga4.get_summary(start, end),
            "key_events": ga4.get_key_events(start, end),
            "top_pages":  ga4.get_top_pages(start, end),
        }
        print(f"  [OK] GA4 ({period_key})")
    except Exception as e:
        print(f"  [ERROR] GA4 ({period_key}): {e}")

    # GSC
    try:
        result["gsc"] = {
            "summary":     gsc.get_summary(start, end),
            "top_queries": gsc.get_top_queries(start, end),
        }
        print(f"  [OK] GSC ({period_key})")
    except Exception as e:
        print(f"  [ERROR] GSC ({period_key}): {e}")

    # Google広告
    try:
        result["google_ads"] = {
            "summary": gads.get_summary(start, end),
            "listing": gads.get_summary_by_campaigns(start, end, config.LISTING_CAMPAIGNS),
            "pmax":    gads.get_summary_by_campaigns(start, end, config.PMAX_CAMPAIGNS),
        }
        print(f"  [OK] Google広告 ({period_key})")
    except Exception as e:
        print(f"  [ERROR] Google広告 ({period_key}): {e}")

    # Facebook広告
    try:
        result["facebook_ads"] = fb.get_summary(start, end)
        print(f"  [OK] Facebook広告 ({period_key})")
    except Exception as e:
        print(f"  [ERROR] Facebook広告 ({period_key}): {e}")

    # Salesforce
    try:
        sf_data = get_all_salesforce_data(sf_start, sf_end)
        result["salesforce"] = sf_data or {}
        print(f"  [OK] Salesforce ({period_key})")
    except Exception as e:
        print(f"  [ERROR] Salesforce ({period_key}): {e}")

    return result


# ------------------------------------------------------------------ #
# メイン
# ------------------------------------------------------------------ #
def main():
    today = date.today()
    periods = get_periods()

    print("=== コネクター初期化 ===")
    ga4  = GA4Connector()
    gsc  = GSCConnector()
    gads = GoogleAdsConnector()
    fb   = FacebookAdsConnector()

    output = {
        "updated_at": str(today),
        "periods": {},
        "ahrefs": {},
    }

    print("\n=== 期間別データ取得 ===")
    for key, info in periods.items():
        print(f"\n-- {info['label']} ({info['range']}) --")
        output["periods"][key] = fetch_period_data(key, info, ga4, gsc, gads, fb)

    print("\n=== Ahrefs (Google Sheets) ===")
    try:
        output["ahrefs"] = get_ahrefs_data()
        print(f"  [OK] Ahrefs Sheets（最終更新: {output['ahrefs'].get('sheet_updated')}）")
    except Exception as e:
        print(f"  [ERROR] Ahrefs Sheets: {e}")

    # JSON 保存
    output_path = Path(__file__).parent.parent / "data" / "dashboard.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n完了: {output_path} を更新しました")


if __name__ == "__main__":
    main()
