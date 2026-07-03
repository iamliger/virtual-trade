import os
import requests
from dotenv import load_dotenv

# 1. .env 파일에 저장된 가상 키값들을 안정적으로 불러옵니다.
load_dotenv()

APP_KEY = os.getenv("HM_APPKEY")
APP_SECRET = os.getenv("HM_APPSECRET")
ACCOUNT_NO = os.getenv("HM_ACCOUNT_NO")

# 🔧 [공식 문서 규격] 한국투자증권 모의투자 전용 도메인 및 포트 지정
# BASE_URL = "https://koreainvestment.com"

BASE_URL = "https://openapivts.koreainvestment.com:29443"
def get_access_token():
    """증권사 모의투자 서버로부터 6시간 동안 유효한 공식 가상 출입증(토큰)을 발급받는 함수"""
    # 공식 토큰 발급 엔드포인트 주소
    url = f"{BASE_URL}/oauth2/tokenP"
    
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    
    try:
        # 공식 규격에 맞춰 POST 통신 요청
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            token = response.json().get("access_token")
            return token
        else:
            print(f"❌ [증권사 전산 거절] 에러 코드: {response.status_code}")
            print(f"📄 거절 이유 반환: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 증권사 서버 연결 네트워크 오류 발생: {e}")
        return None

def get_mock_cash_balance(token):
    """발급받은 출입증(토큰)을 지참하고 내 모의계좌의 진짜 가상 예수금을 조회하는 함수"""
    # 공식 국내주식 모의투자 잔고조회 API 주소
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"
    
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "VTTC8434R"  # 국내주식 모의투자 잔고조회 전용 거래 ID (VT 고정값)
    }
    
    # 공식 필수 파라미터 조건 배열 설정 (8자리 계좌번호 + 2자리 상품코드 분리 매칭)
    # 우리 계좌번호는 4483078002(10자리)이므로 앞 8자리와 뒤 2자리로 슬라이싱 처리합니다.
    cano_8 = ACCOUNT_NO[:8]
    prdt_2 = ACCOUNT_NO[8:]
    
    params = {
        "CANO": cano_8,              # 계좌번호 앞 8자리 (예: 44830780)
        "ACNT_PRDT_CD": prdt_2,      # 계좌번호 뒤 2자리 상품코드 (예: 02)
        "AFHR_FLPR_YN": "N",         # 시간외단일가 여부 (N 고정)
        "OFR_CTX_AREA_RUNG_LEN": "",
        "OFR_CTX_AREA_NK": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            res_json = response.json()
            output2 = res_json.get("output2", [{}])
            
            # 공식 데이터 규격 명세서상 총예수금 필드명인 'dnca_tot_amt' 추출
            cash_balance = output2[0].get("dnca_tot_amt", "0") if output2 else "0"
            return int(cash_balance)
        else:
            print(f"❌ 잔고 조회 실패! 에러 코드: {response.status_code}")
            print(f"📄 응답 내용: {response.text}")
            return 0
    except Exception as e:
        print(f"❌ 잔고 조회 중 오류 발생: {e}")
        return 0
