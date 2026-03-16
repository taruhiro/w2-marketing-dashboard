"""
Google Search Console API コネクター（ダッシュボード用）
認証ファイルパスは環境変数 GCP_CREDENTIALS_PATH から取得する
"""

from googleapiclient.discovery import build
from google.oauth2 import service_account
import config

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

BASE_FILTERS = [
    {"filters": [{"dimension": "country", "operator": "equals", "expression": "jpn"}]},
    {"filters": [{"dimension": "page", "operator": "notContains", "expression": "/tech"}]},
]


class GSCConnector:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            config.GCP_CREDENTIALS_PATH,
            scopes=SCOPES,
        )
        self.service = build("searchconsole", "v1", credentials=credentials)
        self.site_url = config.GSC_SITE_URL

    def _query(self, body):
        body.setdefault("dimensionFilterGroups", BASE_FILTERS)
        return (
            self.service.searchanalytics()
            .query(siteUrl=self.site_url, body=body)
            .execute()
        )

    def get_summary(self, start, end):
        """クリック・表示・CTR・平均順位（日本・/tech 除外）"""
        response = self._query({"startDate": start, "endDate": end, "dimensions": []})
        row = response.get("rows", [{}])[0]
        return {
            "clicks":      int(row.get("clicks", 0)),
            "impressions": int(row.get("impressions", 0)),
            "ctr":         round(row.get("ctr", 0) * 100, 2),
            "position":    round(row.get("position", 0), 1),
        }

    def get_top_queries(self, start, end, limit=10):
        """クリック数上位クエリ"""
        response = self._query({
            "startDate": start, "endDate": end,
            "dimensions": ["query"],
            "rowLimit": limit,
            "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
        })
        return [
            {"query": r["keys"][0], "clicks": int(r["clicks"]),
             "impressions": int(r["impressions"]),
             "ctr": round(r["ctr"] * 100, 2), "position": round(r["position"], 1)}
            for r in response.get("rows", [])
        ]
