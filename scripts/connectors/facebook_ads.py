"""
Facebook広告（Meta広告）コネクター（ダッシュボード用）
認証：長期アクセストークン（システムユーザー発行）
"""

import json
import os
import requests


class FacebookAdsConnector:
    BASE_URL = "https://graph.facebook.com/v20.0"

    def __init__(self):
        self.access_token  = os.environ["FB_ACCESS_TOKEN"]
        self.ad_account_id = os.environ["FB_AD_ACCOUNT_ID"]  # 例: act_123456789

    def get_summary(self, start_date: str, end_date: str) -> dict:
        """
        指定期間のFacebook広告サマリーを返す
        戻り値: {"spend": int, "clicks": int, "conversions": int, "cpa": int}
        """
        url = f"{self.BASE_URL}/{self.ad_account_id}/insights"
        params = {
            "access_token": self.access_token,
            "fields": "spend,clicks,actions",
            "time_range": json.dumps({"since": start_date, "until": end_date}),
            "level": "account",
        }
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if "data" not in data or not data["data"]:
            return {"spend": 0, "clicks": 0, "conversions": 0, "cpa": 0}

        row = data["data"][0]
        spend  = float(row.get("spend", 0))
        clicks = int(row.get("clicks", 0))

        # コンバージョン（リード・ピクセルリード）を集計
        actions = row.get("actions", [])
        conversions = sum(
            int(a.get("value", 0)) for a in actions
            if a.get("action_type") in (
                "lead",
                "offsite_conversion.fb_pixel_lead",
                "offsite_conversion.fb_pixel_custom",
            )
        )
        cpa = int(spend / conversions) if conversions > 0 else 0

        return {
            "spend":       int(spend),
            "clicks":      clicks,
            "conversions": conversions,
            "cpa":         cpa,
        }
