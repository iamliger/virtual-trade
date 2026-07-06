import os

import requests
from dotenv import load_dotenv

load_dotenv()
APP_KEY = os.getenv("HM_APPKEY", "")
APP_SECRET = os.getenv("HM_APPSECRET", "")
ACCOUNT_NO = os.getenv("HM_ACCOUNT_NO", "")
BASE_URL = "https://openapivts.koreainvestment.com:29443"


def get_access_token():
    """증권사 모의투자 서버 토큰 발급"""
    if not APP_KEY or not APP_SECRET:
        return None
    url = f"{BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
    }
    try:
        res = requests.post(url, json=body)
        return res.json().get("access_token") if res.status_code == 200 else None
    except:
        return None


def get_mock_cash_balance(token):
    """실제 증권사 서버 가상 예수금 조회"""
    if len(ACCOUNT_NO) < 10:
        return 0
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "VTTC8434R",
        "content-type": "application/json",
    }
    params = {
        "CANO": ACCOUNT_NO[:8],
        "ACNT_PRDT_CD": ACCOUNT_NO[8:],
        "AFHR_FLPR_YN": "N",
        "OFR_CTX_AREA_RUNG_LEN": "",
        "OFR_CTX_AREA_NK": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            return int(res.json().get("output2", [{}])[0].get("dnca_tot_amt", 0))
        return 0
    except:
        return 0
