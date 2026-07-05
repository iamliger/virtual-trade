# kis_api.py (전체 교체)
import os

import requests
from dotenv import load_dotenv

# 1. .env 파일 로드
load_dotenv()

# 2. 환경 변수 읽기 (없을 경우 빈 문자열로 초기화하여 'None' 에러 방지)
APP_KEY = os.getenv("HM_APPKEY", "")
APP_SECRET = os.getenv("HM_APPSECRET", "")
ACCOUNT_NO = os.getenv("HM_ACCOUNT_NO", "")

BASE_URL = "https://openapivts.koreainvestment.com:29443"


def get_access_token():
    """토큰 발급"""
    if not APP_KEY or not APP_SECRET:
        print("❌ [설정오류] .env 파일의 APP_KEY 또는 APP_SECRET을 확인하세요.")
        return None

    url = f"{BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
    }
    try:
        res = requests.post(url, json=body)
        if res.status_code == 200:
            return res.json().get("access_token")
        else:
            print(f"❌ [토큰 에러] 응답코드: {res.status_code}")
            return None
    except Exception as e:
        print(f"❌ [네트워크 에러] {e}")
        return None


def get_mock_cash_balance(token):
    """예수금 조회"""
    # 💡 Pylance 에러 해결: ACCOUNT_NO가 10자리인지 확인 후 슬라이싱
    if len(ACCOUNT_NO) < 10:
        print("❌ [계좌번호 오류] .env의 HM_ACCOUNT_NO가 10자리인지 확인하세요.")
        return 0

    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "VTTC8434R",
        "content-type": "application/json",
    }

    # 안전하게 8자리, 2자리 분리
    cano_8 = ACCOUNT_NO[:8]
    prdt_2 = ACCOUNT_NO[8:]

    params = {
        "CANO": cano_8,
        "ACNT_PRDT_CD": prdt_2,
        "AFHR_FLPR_YN": "N",
        "OFR_CTX_AREA_RUNG_LEN": "",
        "OFR_CTX_AREA_NK": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": "",
    }

    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            output2 = res.json().get("output2", [{}])
            cash = output2[0].get("dnca_tot_amt", "0")
            return int(cash)
        else:
            return 0
    except Exception as e:
        print(f"❌ [잔고조회 에러] {e}")
        return 0
