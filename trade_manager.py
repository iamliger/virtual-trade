# trade_manager.py (전체 교체)
import sqlite3
from datetime import datetime

DB_FILE = "virtual_trade.db"


def get_db_connection():
    return sqlite3.connect(DB_FILE)


def execute_scalping_buy(ticker, current_price, quantity):
    """DB 기반 매수 실행"""
    conn = get_db_connection()
    cursor = conn.cursor()

    total_cost = current_price * quantity
    fee = int(total_cost * 0.00015)
    final_deduction = total_cost + fee

    # 1. 현금 잔고 확인
    cursor.execute("SELECT cash FROM account")
    cash = cursor.fetchone()[0]

    if cash < final_deduction:
        print("❌ [매수 실패] 가상 예수금이 부족합니다!")
        conn.close()
        return False

    # 2. 현금 차감 및 종목 수량/평단가 업데이트 (SQL의 힘!)
    cursor.execute("UPDATE account SET cash = cash - ?", (final_deduction,))

    # 이미 보유 중인지 확인
    cursor.execute(
        "SELECT quantity, avg_price FROM holdings WHERE ticker = ?", (ticker,)
    )
    row = cursor.fetchone()

    if row:
        prev_qty, prev_price = row
        new_qty = prev_qty + quantity
        new_avg_price = int(
            ((prev_price * prev_qty) + (current_price * quantity)) / new_qty
        )
        cursor.execute(
            "UPDATE holdings SET quantity = ?, avg_price = ? WHERE ticker = ?",
            (new_qty, new_avg_price, ticker),
        )
    else:
        cursor.execute(
            "INSERT INTO holdings (ticker, quantity, avg_price) VALUES (?, ?, ?)",
            (ticker, quantity, current_price),
        )

    # 3. 거래 히스토리 기록
    cursor.execute(
        "INSERT INTO trade_history (trade_date, ticker, type, price, quantity, profit) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ticker,
            "BUY",
            current_price,
            quantity,
            0,
        ),
    )

    conn.commit()
    conn.close()
    print(f"✅ [매수 완료] DB 기록 완료")
    return True


def execute_scalping_sell(ticker, current_price, quantity):
    """DB 기반 매도 실행"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 보유 확인
    cursor.execute(
        "SELECT quantity, avg_price FROM holdings WHERE ticker = ?", (ticker,)
    )
    row = cursor.fetchone()

    if not row or row[0] < quantity:
        print(f"❌ [매도 실패] 보유 주식이 부족합니다.")
        conn.close()
        return False

    prev_qty, avg_buy_price = row
    total_sales = current_price * quantity
    fee_tax = int(total_sales * (0.00015 + 0.0018))
    final_income = total_sales - fee_tax

    # 수익 계산
    profit = final_income - (avg_buy_price * quantity)

    # 2. 잔고 및 보유량 업데이트
    cursor.execute("UPDATE account SET cash = cash + ?", (final_income,))

    if prev_qty == quantity:
        cursor.execute("DELETE FROM holdings WHERE ticker = ?", (ticker,))
    else:
        cursor.execute(
            "UPDATE holdings SET quantity = quantity - ? WHERE ticker = ?",
            (quantity, ticker),
        )

    # 3. 거래 히스토리 기록
    cursor.execute(
        "INSERT INTO trade_history (trade_date, ticker, type, price, quantity, profit) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ticker,
            "SELL",
            current_price,
            quantity,
            profit,
        ),
    )

    conn.commit()
    conn.close()
    print(f"✅ [매도 완료] 수익: {profit:,}원 기록 완료")
    return True
