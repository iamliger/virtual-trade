# db_manager.py
import json
import os
import sqlite3
from datetime import datetime

DB_FILE = "virtual_trade.db"
JSON_FILE = "account.json"


def get_db_connection():
    return sqlite3.connect(DB_FILE)


def create_tables():
    """DB 테이블 초기 설계(스키마) 생성"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 계좌 테이블
    cursor.execute("""CREATE TABLE IF NOT EXISTS account 
                      (cash INTEGER, updated_at TEXT)""")

    # 2. 보유 종목 테이블
    cursor.execute("""CREATE TABLE IF NOT EXISTS holdings 
                      (ticker TEXT PRIMARY KEY, quantity INTEGER, avg_price INTEGER)""")

    # 3. 매매 기록 테이블
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS trade_history 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT, 
                       ticker TEXT, type TEXT, price INTEGER, quantity INTEGER, profit INTEGER)"""
    )

    # 4. AI 판단 로그 테이블
    cursor.execute("""CREATE TABLE IF NOT EXISTS ai_log 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, log_date TEXT, 
                       ticker TEXT, decision TEXT, reason TEXT)""")

    conn.commit()
    conn.close()
    print("✅ [DB] 테이블 설계 및 생성 완료")


def migrate_from_json():
    """기존 account.json 데이터를 DB로 이사(마이그레이션)하기"""
    if not os.path.exists(JSON_FILE):
        print("⚠️ [마이그레이션] 기존 JSON 파일이 없어 건너뜁니다.")
        return

    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        conn = get_db_connection()
        cursor = conn.cursor()

        # 현금 데이터 이전
        cursor.execute(
            "INSERT INTO account (cash, updated_at) VALUES (?, ?)",
            (data["cash"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

        # 보유 종목 데이터 이전
        for ticker, info in data["stocks"].items():
            cursor.execute(
                "INSERT OR REPLACE INTO holdings (ticker, quantity, avg_price) VALUES (?, ?, ?)",
                (ticker, info["quantity"], info["avg_price"]),
            )

        conn.commit()
        conn.close()

        # 이사 완료 후 기존 파일 이름 변경 (백업용)
        os.rename(JSON_FILE, f"backup_{JSON_FILE}")
        print("🎊 [마이그레이션] JSON 데이터를 DB로 안전하게 이전했습니다!")

    except Exception as e:
        print(f"❌ [마이그레이션 에러] {e}")


if __name__ == "__main__":
    create_tables()
    migrate_from_json()
