import json
import os

# 가상 계좌 파일 경로 설정 (내 컴퓨터 안의 가상 통장 장부)
ACCOUNT_FILE = "account.json"

# 📖 초보자를 위한 주식 용어 친절 사전 (프로그램 내부 툴팁 기능)
# 로그가 출력될 때 이 사전을 참고하여 한글 설명을 주석처럼 달아줍니다.
STOCK_DICTIONARY = {
    "예수금": "주식을 사기 위해 내 계좌에 넣어둔 '상태 좋은 현금'",
    "익절": "내가 샀던 가격보다 '비싸게 팔아서' 기분 좋게 이익을 남기고 나오는 것",
    "손절": "내가 샀던 가격보다 '싸게 팔아서' 더 큰 손실을 막기 위해 눈물을 머금고 탈출하는 것",
    "매수": "주식 시장에서 주식을 '사서 내 장부에 담는 행위'",
    "매도": "가지고 있던 주식을 시장에 '팔아서 현금으로 바꾸는 행위'",
    "평단가": "내가 이 주식을 여러 번 나누어 샀을 때, 주당 평균적으로 얼마에 샀는지 계산한 원가",
    "거래세": "주식을 '팔 때(매도)' 국가에 무조건 내야 하는 합법적인 세금 (단타의 가장 큰 적)",
}


def load_account():
    """내 컴퓨터의 가상 계좌 파일(JSON)을 읽어오는 함수"""
    if not os.path.exists(ACCOUNT_FILE):
        # 파일이 없으면 가상 자산 1,000만 원으로 장부를 초기화하여 생성
        initial_data = {"cash": 10000000, "stocks": {}}
        with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=4)
        return initial_data

    with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_account(account_data):
    """계좌 변경 사항을 파일에 다시 저장하는 함수"""
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(account_data, f, indent=4, ensure_ascii=False)


def execute_scalping_buy(ticker, current_price, quantity):
    """
    [단타 전용 매수 함수]
    - ticker: 주식 종목 코드 (예: '005930.KS')
    - current_price: 현재가 (단타는 현재가로 즉시 체결)
    - quantity: 살 수량
    """
    account = load_account()
    total_cost = current_price * quantity

    # 단타 필수 반영: 증증권사 가상 수수료 (약 0.015% 가정)
    brokerage_fee = int(total_cost * 0.00015)
    final_deduction = total_cost + brokerage_fee

    print(
        f"\n⚡ [단타 매수 시도] {ticker} | 가격: {current_price:,}원 | 수량: {quantity}주"
    )
    print(
        f"💰 필요 금액(수수료 포함): {final_deduction:,}원 (수수료: {brokerage_fee:,}원)"
    )

    # 잔고 검증 (예수금이 부족하면 거절하고 친절한 용어 툴팁을 보여줍니다)
    if account["cash"] < final_deduction:
        print(f"❌ [매수 실패] 가상 예수금이 부족합니다!")
        print(f"   💡 [용어 설명] 예수금이란? {STOCK_DICTIONARY['예수금']}\n")
        return False

    # 예수금 차감
    account["cash"] -= final_deduction

    # 보유 주식 목록 갱신
    if ticker in account["stocks"]:
        # 이미 가지고 있는 종목이면 평단가 재계산 및 수량 추가
        prev_qty = account["stocks"][ticker]["quantity"]
        prev_price = account["stocks"][ticker]["avg_price"]

        # 새로운 평균 매입가(평단가) 계산
        new_qty = prev_qty + quantity
        new_avg_price = int(
            ((prev_price * prev_qty) + (current_price * quantity)) / new_qty
        )

        account["stocks"][ticker]["quantity"] = new_qty
        account["stocks"][ticker]["avg_price"] = new_avg_price
    else:
        # 처음 사는 종목이면 새로 등록
        account["stocks"][ticker] = {"quantity": quantity, "avg_price": current_price}

    save_account(account)
    print(f"✅ [매수 완료] 현재 남은 가상 예수금: {account['cash']:,}원")
    print(f"   💡 [용어 설명] 매수란? {STOCK_DICTIONARY['매수']}")
    print(f"   💡 [용어 설명] 평단가란? {STOCK_DICTIONARY['평단가']}")
    return True


def execute_scalping_sell(ticker, current_price, quantity):
    """
    [단타 전용 매도 함수]
    - ticker: 주식 종목 코드 (예: '005930.KS')
    - current_price: 현재가 (단타는 현재가로 즉시 매도 체결)
    - quantity: 팔 수량
    """
    account = load_account()

    # 1. 내가 이 주식을 진짜 가지고 있는지 검증
    if (
        ticker not in account["stocks"]
        or account["stocks"][ticker]["quantity"] < quantity
    ):
        print(f"❌ [매도 실패] 보유한 {ticker} 주식이 부족하거나 없습니다!")
        print(f"   💡 [용어 설명] 매도란? {STOCK_DICTIONARY['매도']}\n")
        return False

    avg_buy_price = account["stocks"][ticker]["avg_price"]  # 내가 샀던 평균 가격
    total_sales = current_price * quantity  # 판 총금액

    # 2. 단타의 핵심: 매도 수수료 및 국가 세금 계산
    brokerage_fee = int(total_sales * 0.00015)  # 증권사 수수료 (0.015%)
    tax = int(total_sales * 0.0018)  # 국가 거래세 (약 0.18% 가정)
    final_income = total_sales - (
        brokerage_fee + tax
    )  # 수수료/세금 떼고 내 통장에 들어올 돈

    # 3. 수익률 및 손익 금액 계산
    total_buy_cost = avg_buy_price * quantity  # 살 때 들었던 원금
    net_profit = final_income - total_buy_cost  # 순수익 (마이너스면 손실)
    profit_rate = (net_profit / total_buy_cost) * 100  # 수익률(%)

    print(
        f"\n⚡ [단타 매도 시도] {ticker} | 가격: {current_price:,}원 | 수량: {quantity}주"
    )
    print(
        f"📊 [매도 정산] 원금: {total_buy_cost:,}원 ──> 정산금: {final_income:,}원 (세금/수수료: {tax+brokerage_fee:,}원)"
    )

    if net_profit >= 0:
        print(f"📈 [익절 성공] 순수익: +{net_profit:,}원 (수익률: +{profit_rate:.2f}%)")
        print(f"   💡 [용어 설명] 익절이란? {STOCK_DICTIONARY['익절']}")
    else:
        print(f"📉 [손절 탈출] 순손실: {net_profit:,}원 (수익률: {profit_rate:.2f}%)")
        print(f"   💡 [용어 설명] 손절이란? {STOCK_DICTIONARY['손절']}")
        print(f"   💡 [용어 설명] 거래세란? {STOCK_DICTIONARY['거래세']}")

    # 4. 가상 계좌 장부 업데이트
    account["cash"] += final_income  # 예수금 늘려주기
    account["stocks"][ticker]["quantity"] -= quantity  # 보유 수량 차감

    # 만약 주식을 전량 매도해서 0주가 되었다면 목록에서 삭제
    if account["stocks"][ticker]["quantity"] == 0:
        del account["stocks"][ticker]

    save_account(account)
    print(f"✅ [매도 완료] 현재 남은 가상 예수금: {account['cash']:,}원")
    return True
