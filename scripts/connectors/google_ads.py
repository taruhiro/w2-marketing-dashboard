"""
Google Ads API コネクター（ダッシュボード用）
認証情報はすべて環境変数から読み込む
"""

import os
from google.ads.googleads.client import GoogleAdsClient


def _get_client():
    credentials = {
        "developer_token":   os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
        "refresh_token":     os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "client_id":         os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret":     os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "login_customer_id": os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"],
        "use_proto_plus":    True,
    }
    return GoogleAdsClient.load_from_dict(credentials)


class GoogleAdsConnector:
    def __init__(self):
        self.client = _get_client()
        self.customer_id = os.environ["GOOGLE_ADS_CUSTOMER_ID"]

    def _run_query(self, query):
        service = self.client.get_service("GoogleAdsService")
        return service.search(customer_id=self.customer_id, query=query)

    def get_summary(self, start, end):
        """費用・クリック・CV・CPA サマリー"""
        query = f"""
            SELECT
                metrics.cost_micros,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.cost_per_conversion
            FROM customer
            WHERE segments.date BETWEEN '{start}' AND '{end}'
        """
        cost = clicks = impressions = conversions = 0
        ctr = cpa = 0.0
        for row in self._run_query(query):
            m = row.metrics
            cost        += m.cost_micros
            clicks      += m.clicks
            impressions += m.impressions
            ctr          = m.ctr * 100
            conversions += m.conversions
            cpa          = m.cost_per_conversion / 1_000_000
        return {
            "cost":        int(cost / 1_000_000),
            "clicks":      int(clicks),
            "impressions": int(impressions),
            "ctr":         round(ctr, 2),
            "conversions": round(conversions, 1),
            "cpa":         int(cpa),
        }

    def get_summary_by_campaigns(self, start, end, campaign_names):
        """キャンペーン名リストに絞った集計（リスティング/P-MAX別）"""
        if not campaign_names:
            return {"cost": 0, "clicks": 0, "impressions": 0,
                    "ctr": 0.0, "conversions": 0.0, "cpa": 0}
        names_sql = ", ".join([f"'{n}'" for n in campaign_names])
        query = f"""
            SELECT metrics.cost_micros, metrics.clicks,
                   metrics.impressions, metrics.conversions
            FROM campaign
            WHERE segments.date BETWEEN '{start}' AND '{end}'
              AND campaign.name IN ({names_sql})
              AND campaign.status != 'REMOVED'
        """
        cost = clicks = impressions = conversions = 0
        for row in self._run_query(query):
            m = row.metrics
            cost += m.cost_micros; clicks += m.clicks
            impressions += m.impressions; conversions += m.conversions
        ctr     = round(clicks / impressions * 100, 2) if impressions > 0 else 0.0
        avg_cpc = int(cost / clicks / 1_000_000)       if clicks > 0       else 0
        cpa     = int(cost / conversions / 1_000_000)  if conversions > 0  else 0
        return {
            "cost":        int(cost / 1_000_000),
            "clicks":      int(clicks),
            "impressions": int(impressions),
            "ctr":         ctr,
            "conversions": round(conversions, 1),
            "cpa":         cpa,
        }
