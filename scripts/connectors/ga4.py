"""
GA4 Data API コネクター（ダッシュボード用）
認証ファイルパスは環境変数 GCP_CREDENTIALS_PATH から取得する
"""

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Filter, FilterExpression,
    FilterExpressionList, Metric, RunReportRequest,
)
from google.oauth2 import service_account
import config

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]

KEY_EVENTS = [
    "共通_CV", "W2RepeatCV", "W2RepeatFood_CV", "W2Unified_CV",
    "ヘッダー問い合わせCV", "ヘッダー資料請求CV", "セミナーCV",
    "W2_FB広告CV", "W2BtoB_CV", "AIインハウス_CV", "AIBuddy_CV",
    "Comedia_CV", "一括資料請求_CV", "W2Asia_CV",
]
NON_MQL_EVENTS = ["ヘッダー問い合わせCV"]


def _japan_filter():
    return FilterExpression(
        filter=Filter(
            field_name="country",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.EXACT,
                value="Japan",
            ),
        )
    )


class GA4Connector:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            config.GCP_CREDENTIALS_PATH,
            scopes=SCOPES,
        )
        self.client = BetaAnalyticsDataClient(credentials=credentials)
        self.property_id = f"properties/{config.GA4_PROPERTY_ID}"

    def _run_report(self, dimensions, metrics, date_ranges, dimension_filter=None):
        request = RunReportRequest(
            property=self.property_id,
            dimensions=dimensions,
            metrics=metrics,
            date_ranges=date_ranges,
            dimension_filter=dimension_filter,
        )
        return self.client.run_report(request)

    def _dr(self, start, end):
        return [DateRange(start_date=start, end_date=end)]

    def get_summary(self, start, end):
        """セッション・ユーザー・コンバージョン合計（日本のみ）"""
        response = self._run_report(
            dimensions=[],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="conversions"),
            ],
            date_ranges=self._dr(start, end),
            dimension_filter=_japan_filter(),
        )
        row = response.rows[0].metric_values if response.rows else None
        if not row:
            return {"sessions": 0, "users": 0, "conversions": 0}
        return {
            "sessions": int(row[0].value),
            "users": int(row[1].value),
            "conversions": int(row[2].value),
        }

    def get_key_events(self, start, end):
        """キーイベント別CV数"""
        response = self._run_report(
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="conversions")],
            date_ranges=self._dr(start, end),
            dimension_filter=_japan_filter(),
        )
        counts = {row.dimension_values[0].value: int(row.metric_values[0].value)
                  for row in response.rows}
        breakdown = []
        total = total_excl = 0
        for event in KEY_EVENTS:
            count = counts.get(event, 0)
            breakdown.append({"event": event, "count": count})
            total += count
            if event not in NON_MQL_EVENTS:
                total_excl += count
        return {"breakdown": breakdown, "total": total, "total_excl_non_mql": total_excl}

    def get_top_pages(self, start, end, limit=10):
        """アクセス上位ページ（/tech 除外）"""
        excl_tech = FilterExpression(
            and_group=FilterExpressionList(expressions=[
                _japan_filter(),
                FilterExpression(
                    not_expression=FilterExpression(
                        filter=Filter(
                            field_name="pagePath",
                            string_filter=Filter.StringFilter(
                                match_type=Filter.StringFilter.MatchType.CONTAINS,
                                value="/tech",
                            ),
                        )
                    )
                ),
            ])
        )
        response = self._run_report(
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
            date_ranges=self._dr(start, end),
            dimension_filter=excl_tech,
        )
        results = [
            {"page": r.dimension_values[0].value,
             "sessions": int(r.metric_values[0].value),
             "users": int(r.metric_values[1].value)}
            for r in response.rows
        ]
        results.sort(key=lambda x: x["sessions"], reverse=True)
        return results[:limit]
