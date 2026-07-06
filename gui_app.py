# gui_app.py
import threading
import time
from datetime import datetime

import customtkinter as ctk

from db_manager import create_tables
from kis_api import get_access_token
from main_logic import (
    SCAN_POOL,
    get_db_history,
    get_holdings,
    predict_best_stock,
    run_trading_cycle,
)

ctk.set_appearance_mode("dark")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 로컬 가상 매매 스테이션 v2.0")
        self.geometry("1300x1000")
        create_tables()  # 시작 시 DB 점검

        # [1] 상단: AI 시장 심층 리포트
        self.top_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.top_frame.pack(fill="x", padx=20, pady=10)
        self.predict_box = ctk.CTkTextbox(
            self.top_frame, height=120, font=("Malgun Gothic", 13), text_color="#FFD700"
        )
        self.predict_box.pack(fill="x", padx=10, pady=10)
        self.predict_box.insert("0.0", "🚀 AI 시장 예측 엔진 대기 중...")

        # [2] 중앙: 분석 리포트 및 자산 전광판
        self.mid_frame = ctk.CTkFrame(self)
        self.mid_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # 왼쪽: AI 실시간 분석
        self.ai_panel = ctk.CTkFrame(self.mid_frame)
        self.ai_panel.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.ai_report_text = ctk.CTkTextbox(self.ai_panel, font=("Malgun Gothic", 15))
        self.ai_report_text.pack(fill="both", expand=True, padx=10, pady=10)

        # 오른쪽: 자산 현황 (전광판 스타일)
        self.asset_panel = ctk.CTkFrame(self.mid_frame, width=400, fg_color="#212121")
        self.asset_panel.pack(side="right", fill="both", expand=False, padx=5, pady=5)

        self.ticker_menu = ctk.CTkOptionMenu(
            self.asset_panel,
            values=[f"{k} ({v})" for k, v in SCAN_POOL.items()],
            width=250,
        )
        self.ticker_menu.pack(pady=20)

        self.price_label = ctk.CTkLabel(
            self.asset_panel,
            text="--원",
            font=("Consolas", 40, "bold"),
            text_color="#FFFFFF",
        )
        self.price_label.pack(pady=10)

        self.db_balance_label = ctk.CTkLabel(
            self.asset_panel, text="로컬 자산: --원", font=("Malgun Gothic", 18)
        )
        self.db_balance_label.pack(pady=5)

        self.mock_balance_label = ctk.CTkLabel(
            self.asset_panel,
            text="증권사 잔고: --원",
            font=("Malgun Gothic", 14),
            text_color="gray",
        )
        self.mock_balance_label.pack(pady=5)

        self.prog_bar = ctk.CTkProgressBar(self.asset_panel, width=300)
        self.prog_bar.set(0)
        self.prog_bar.pack(pady=20)

        # [3] 하단: 탭 메뉴 (히스토리 / 보유현황)
        self.tab_view = ctk.CTkTabview(self, height=300)
        self.tab_view.pack(fill="x", padx=20, pady=10)
        self.tab_history = self.tab_view.add("매매 히스토리")
        self.tab_holdings = self.tab_view.add("현재 보유 종목")

        self.history_box = ctk.CTkTextbox(
            self.tab_history, font=("Consolas", 11), fg_color="#000000"
        )
        self.history_box.pack(fill="both", expand=True)

        self.holdings_box = ctk.CTkTextbox(
            self.tab_holdings, font=("Consolas", 11), fg_color="#000000"
        )
        self.holdings_box.pack(fill="both", expand=True)

        # [4] 시작 버튼
        self.btn_start = ctk.CTkButton(
            self,
            text="AI 트레이딩 시스템 풀 가동",
            command=self.start_engine,
            fg_color="green",
            height=50,
            font=("Malgun Gothic", 16, "bold"),
        )
        self.btn_start.pack(pady=10)

        # 시계 업데이트
        self.update_clock()

    def update_clock(self):
        self.after(1000, self.update_clock)

    def update_ui(self, data):
        if data["status"] == "ACTIVE":
            # 1. 가격 및 잔고 업데이트
            self.price_label.configure(text=f"{data['price']:,}원")
            self.db_balance_label.configure(
                text=f"로컬 가상자산: {data['db_balance']:,}원", text_color="#00FF00"
            )
            self.mock_balance_label.configure(
                text=f"증권사 모의예수금: {data['mock_balance']:,}원"
            )

            # 2. AI 리포트
            self.ai_report_text.configure(state="normal")
            self.ai_report_text.delete("1.0", "end")
            report = f"🎯 분석 대상: {data['ticker']}\n결정: [{data['decision']}]\n상태: {data['trade_status']}\n"
            report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            report += f"💡 분석근거: {data['reason']}\n\n📰 관련 뉴스:\n{data['news']}"
            self.ai_report_text.insert("1.0", report)
            self.ai_report_text.configure(state="disabled")

            # 3. DB 데이터 실시간 새로고침
            self.refresh_db_tabs()

    def refresh_db_tabs(self):
        # 히스토리 탭
        history = get_db_history()
        self.history_box.delete("1.0", "end")
        for h in history:
            self.history_box.insert(
                "end", f"📅 {h[0]} | {h[1]} | {h[2]} | 가격:{h[3]:,} | 손익:{h[4]:,}\n"
            )

        # 보유현황 탭
        holdings = get_holdings()
        self.holdings_box.delete("1.0", "end")
        self.holdings_box.insert(
            "end", "Ticker | 수량 | 평단가 | 현재가치\n" + "-" * 40 + "\n"
        )
        for h in holdings:
            self.holdings_box.insert("end", f"📦 {h[0]} | {h[1]}주 | 평단:{h[2]:,}원\n")

    def start_engine(self):
        self.btn_start.configure(state="disabled", text="엔진 가동 중...")
        threading.Thread(target=self.initial_analysis, daemon=True).start()

    def initial_analysis(self):
        pred = predict_best_stock()
        self.after(
            0,
            lambda: (
                self.predict_box.delete("1.0", "end"),
                self.predict_box.insert("1.0", f"🚀 AI 오늘의 시장 분석:\n{pred}"),
            ),
        )
        self.trading_main_loop()

    def trading_main_loop(self):
        token = get_access_token()
        while True:
            ticker = self.ticker_menu.get().split("(")[1].replace(")", "")
            result = run_trading_cycle(token, ticker)
            if "error" not in result:
                self.after(0, lambda r=result: self.update_ui(r))

            # 60초 프로그래스 바
            for i in range(61):
                self.after(0, lambda v=i: self.prog_bar.set(v / 60))
                time.sleep(1)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
