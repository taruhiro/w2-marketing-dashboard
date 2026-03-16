"""
ダッシュボード設定ファイル
認証情報はすべて環境変数または /tmp/ の一時ファイルから読み込む
"""
import os

# ------------------------------------------------------------------ #
# GA4 / GSC
# ------------------------------------------------------------------ #
GA4_PROPERTY_ID = "347437441"
GSC_SITE_URL = "https://www.w2solution.co.jp/"
# GitHub Actions が /tmp/gcp_credentials.json に書き出す
GCP_CREDENTIALS_PATH = os.environ.get("GCP_CREDENTIALS_PATH", "/tmp/gcp_credentials.json")

# ------------------------------------------------------------------ #
# Google広告
# ------------------------------------------------------------------ #
LISTING_CAMPAIGNS = ["一般CP", "指名CP", "08_BtoB一般", "九州一般"]
PMAX_CAMPAIGNS    = ["202502", "20251017"]
LISTING_MONTHLY_BUDGET    = 3_500_000
PMAX_MONTHLY_BUDGET       = 1_500_000
LISTING_MONTHLY_CV_TARGET = 38
PMAX_MONTHLY_CV_TARGET    = 50
LISTING_TARGET_CPA        = 70_200
PMAX_TARGET_CPA           = 30_000

# ------------------------------------------------------------------ #
# Salesforce
# ------------------------------------------------------------------ #
SF_USERNAME        = "h.taruzawa@w2solution.co.jp"
SF_PASSWORD        = os.environ.get("SF_PASSWORD")
SF_CONSUMER_KEY    = "3MVG9G9pzCUSkzZs7ze2kvcQTH1lB.vXbgIHrO7mvckUt_XXVV91fOqbSt_nwPHcaDLJW.iI1q7RcA3DRQ4RF"
SF_CONSUMER_SECRET = "B5DDE28B5D685F67983B62B889A149C2DAB123E0414EEBB1E2534C1F2BCE40E4"
SF_DOMAIN          = "login"
SF_ORG_ID          = "00D2v0000027Yzi"
# GitHub Actions が /tmp/sf_private_key.pem に書き出す
SF_PRIVATE_KEY_PATH = os.environ.get("SF_PRIVATE_KEY_PATH", "/tmp/sf_private_key.pem")

# ------------------------------------------------------------------ #
# Ahrefs × Google Sheets
# ------------------------------------------------------------------ #
AHREFS_SHEET_ID   = os.environ.get("AHREFS_SHEET_ID", "18CKHBygel_qADtAGeKiIOgrr7qBNBF_D6NukdtVSC-A")
AHREFS_SHEET_NAME = os.environ.get("AHREFS_SHEET_NAME", "シート1")  # 実際のシート名に合わせて変更
