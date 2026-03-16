"""
Salesforce コネクター（ダッシュボード用）
秘密鍵パスは環境変数 SF_PRIVATE_KEY_PATH から取得する
"""

import time
import jwt
import requests
from simple_salesforce import Salesforce
import config

EXCLUDE_SOURCES = ("アライアンス", "外注ベンダー", "アウトバウンド")


def _get_private_key():
    with open(config.SF_PRIVATE_KEY_PATH, "r") as f:
        return f.read()


def _get_jwt_access_token():
    private_key = _get_private_key()
    payload = {
        "iss": config.SF_CONSUMER_KEY,
        "sub": config.SF_USERNAME,
        "aud": "https://login.salesforce.com",
        "exp": int(time.time()) + 300,
    }
    signed_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    response = requests.post(
        "https://login.salesforce.com/services/oauth2/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
              "assertion": signed_jwt},
    )
    result = response.json()
    if "access_token" not in result:
        raise Exception(f"JWTトークン取得失敗: {result.get('error_description', result.get('error'))}")
    return result["access_token"], result["instance_url"]


def connect_salesforce():
    try:
        access_token, instance_url = _get_jwt_access_token()
        sf = Salesforce(instance_url=instance_url, session_id=access_token)
        print("[OK] Salesforce接続成功")
        return sf
    except Exception as e:
        print(f"[ERROR] Salesforce接続エラー: {e}")
        return None


def _dt_str(dt):
    return dt.strftime("%Y-%m-%dT00:00:00Z"), dt.strftime("%Y-%m-%dT23:59:59Z")


def _date_str(dt):
    return dt.strftime("%Y-%m-%d")


def _exclude_clause():
    values = "', '".join(EXCLUDE_SOURCES)
    return f"Leadtriger__c NOT IN ('{values}')"


def get_new_mql_summary(sf, start_date, end_date):
    """当期間の新規リード・MQL数をリード獲得元別に集計"""
    start_str = _dt_str(start_date)[0]
    end_str   = _dt_str(end_date)[1]
    try:
        result = sf.query_all(f"""
            SELECT Leadtriger__c, Field17__c, Field181__c FROM Lead
            WHERE CreatedDate >= {start_str} AND CreatedDate <= {end_str}
              AND Leadtriger__c != null AND {_exclude_clause()}
        """)
        has_sub = True
    except Exception:
        result = sf.query_all(f"""
            SELECT Leadtriger__c, Field17__c FROM Lead
            WHERE CreatedDate >= {start_str} AND CreatedDate <= {end_str}
              AND Leadtriger__c != null AND {_exclude_clause()}
        """)
        has_sub = False

    source_data = {}
    for r in result["records"]:
        source  = r.get("Leadtriger__c") or "不明"
        field17 = r.get("Field17__c") or ""
        sub     = r.get("Field181__c") or "" if has_sub else ""
        key = f"BOXIL（{sub}）" if source == "BOXIL" and sub else source
        if key not in source_data:
            source_data[key] = {"source": key, "info_count": 0, "mql_count": 0}
        if field17 == "情報収集段階":
            source_data[key]["info_count"] += 1
        elif field17 == "企画段階":
            source_data[key]["mql_count"] += 1

    by_source = sorted(source_data.values(),
                       key=lambda x: x["mql_count"] + x["info_count"], reverse=True)
    return {
        "by_source":  by_source,
        "total_info": sum(x["info_count"] for x in by_source),
        "total_mql":  sum(x["mql_count"]  for x in by_source),
    }


def get_opportunity_summary(sf, start_date, end_date):
    """当期間の新規商談数（製品別・獲得元別）"""
    start_str = _dt_str(start_date)[0]
    end_str   = _dt_str(end_date)[1]
    where = f"""
        CreatedDate >= {start_str} AND CreatedDate <= {end_str}
        AND Field70__c = '新規' AND RecordType.Name = 'FS商談（20期～）'
    """
    r_prod = sf.query(f"""
        SELECT Service__c, COUNT(Id) total FROM Opportunity
        WHERE {where} GROUP BY Service__c ORDER BY COUNT(Id) DESC
    """)
    by_product = [{"source": r.get("Service__c") or "不明", "total": r.get("total", 0)}
                  for r in r_prod["records"]]

    r_src = sf.query(f"""
        SELECT Field50__c, COUNT(Id) total FROM Opportunity
        WHERE {where} GROUP BY Field50__c ORDER BY COUNT(Id) DESC
    """)
    by_source = [{"source": r.get("Field50__c") or "不明", "total": r.get("total", 0)}
                 for r in r_src["records"]]

    return {
        "by_product": by_product,
        "by_source":  by_source,
        "total":      sum(r["total"] for r in by_product),
    }


def get_additional_mql_summary(sf, start_date, end_date):
    """有望リード転換日が当期間のリードを集計"""
    start_str = _date_str(start_date)
    end_str   = _date_str(end_date)
    result = sf.query(f"""
        SELECT Field26__c, COUNT(Id) total FROM Lead
        WHERE Field27__c >= {start_str} AND Field27__c <= {end_str}
        GROUP BY Field26__c ORDER BY COUNT(Id) DESC
    """)
    by_source = [{"source": r.get("Field26__c") or "不明", "total": r.get("total", 0)}
                 for r in result["records"]]
    return {"by_source": by_source, "total": sum(r["total"] for r in by_source)}


def get_all_salesforce_data(start_date, end_date):
    """全Salesforceデータをまとめて取得"""
    sf = connect_salesforce()
    if sf is None:
        return None
    return {
        "new_mql":        get_new_mql_summary(sf, start_date, end_date),
        "opportunities":  get_opportunity_summary(sf, start_date, end_date),
        "additional_mql": get_additional_mql_summary(sf, start_date, end_date),
    }
