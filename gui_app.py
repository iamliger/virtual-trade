# gui_app.py
import threading
import time
from datetime import datetime

import customtkinter as ctk

from db_manager import create_tables, get_statistics, update_cash
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
        self.title("AI 실전 단타 시뮬레이터 v2.5 (목표 달성 시스템)")
        self.geometry("1400x1050")
        create_tables()

        # [1] 상단: AI 시장 분석
        self.top_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        self.top_frame.pack(fill="x", padx=20, pady=10)
        self.predict_box = ctk.CTkTextbox(
            self.top_frame, height=120, font=("Malgun Gothic", 13), text_color="#FFD700"
        )
        self.predict_box.pack(fill="x", padx=10, pady=10)
        self.predict_box.insert("0.0", "🚀 AI 시장 분석 및 예측 리포트 대기 중...")

        # [2] 중앙 레이아웃
        self.mid_frame = ctk.CTkFrame(self)
        self.mid_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # 왼쪽: AI 실시간 리포트
        self.ai_panel = ctk.CTkFrame(self.mid_frame)
        self.ai_panel.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.ai_report_text = ctk.CTkTextbox(self.ai_panel, font=("Malgun Gothic", 15))
        self.ai_report_text.pack(fill="both", expand=True, padx=10, pady=10)

        # 오른쪽: 통계 전광판 및 설정
        self.stat_panel = ctk.CTkFrame(self.mid_frame, width=450, fg_color="#212121")
        self.stat_panel.pack(side="right", fill="both", expand=False, padx=5, pady=5)

        # 시드머니 설정 (width, height 속성 사용으로 수정됨)
        ctk.CTkLabel(
            self.stat_panel, text="💰 시드머니 설정 (원)", font=("Malgun Gothic", 12)
        ).pack(pady=(10, 0))
        self.seed_input = ctk.CTkEntry(self.stat_panel, width=150, justify="center")
        self.seed_input.insert(0, "1000000")
        self.seed_input.pack(pady=5)
        self.btn_set_seed = ctk.CTkButton(
            self.stat_panel,
            text="잔고 업데이트",
            width=100,
            height=25,
            command=self.set_seed,
        )
        self.btn_set_seed.pack(pady=5)

        # 오늘의 목표 수익 설정
        ctk.CTkLabel(
            self.stat_panel, text="🎯 일일 목표 수익 (원)", font=("Malgun Gothic", 12)
        ).pack(pady=(10, 0))
        self.goal_input = ctk.CTkEntry(
            self.stat_panel, width=150, justify="center", fg_color="#1a3a1a"
        )
        self.goal_input.insert(0, "5000")
        self.goal_input.pack(pady=5)

        self.price_label = ctk.CTkLabel(
            self.stat_panel,
            text="--원",
            font=("Consolas", 45, "bold"),
            text_color="#FFFFFF",
        )
        self.price_label.pack(pady=20)

        self.today_profit_label = ctk.CTkLabel(
            self.stat_panel,
            text="금일 수익: 0원",
            font=("Malgun Gothic", 20, "bold"),
            text_color="#00FF00",
        )
        self.today_profit_label.pack(pady=5)

        self.stats_label = ctk.CTkLabel(
            self.stat_panel,
            text="주간: 0원 | 월간: 0원",
            font=("Malgun Gothic", 14),
            text_color="gray",
        )
        self.stats_label.pack(pady=5)

        self.db_balance_label = ctk.CTkLabel(
            self.stat_panel, text="보유 예수금: --원", font=("Malgun Gothic", 16)
        )
        self.db_balance_label.pack(pady=20)

        self.ticker_menu = ctk.CTkOptionMenu(
            self.stat_panel,
            values=[f"{k} ({v})" for k, v in SCAN_POOL.items()],
            width=250,
        )
        self.ticker_menu.pack(pady=10)

        self.prog_bar = ctk.CTkProgressBar(self.stat_panel, width=300)
        self.prog_bar.set(0)
        self.prog_bar.pack(pady=20)

        # [3] 하단 탭
        self.tab_view = ctk.CTkTabview(self, height=350)
        self.tab_view.pack(fill="x", padx=20, pady=10)
        self.tab_history = self.tab_view.add("매매 히스토리")
        self.tab_holdings = self.tab_view.add("현재 보유 종목 현황")

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
            text="전략 가동 및 자동 매매 시작",
            command=self.start_engine,
            fg_color="green",
            height=50,
            font=("Malgun Gothic", 16, "bold"),
        )
        self.btn_start.pack(pady=10)

    def set_seed(self):
        try:
            amount = int(self.seed_input.get())
            update_cash(amount)
            self.db_balance_label.configure(text=f"보유 예수금: {amount:,}원")
            self.predict_box.insert(
                "end", f"\n💰 시드머니가 {amount:,}원으로 재설정되었습니다."
            )
        except:
            pass

    def update_ui(self, data):
        if data["status"] == "GOAL_REACHED":
            self.today_profit_label.configure(
                text=f"🎯 목표 달성: {data['today_profit']:,}원", text_color="yellow"
            )
            self.predict_box.insert(
                "end", "\n🎊 오늘의 목표 수익을 달성했습니다. 시스템을 종료합니다."
            )
            return

        if data["status"] == "ACTIVE":
            self.price_label.configure(text=f"{data['price']:,}원")
            self.db_balance_label.configure(
                text=f"보유 예수금: {data['db_balance']:,}원"
            )
            self.today_profit_label.configure(
                text=f"금일 수익: {data['today_profit']:,}원"
            )
            self.stats_label.configure(
                text=f"주간: {data['weekly_profit']:,}원 | 월간: {data['monthly_profit']:,}원"
            )

            self.ai_report_text.configure(state="normal")
            self.ai_report_text.delete("1.0", "end")
            report = f"🎯 분석 대상: {self.ticker_menu.get()}\n결정: [{data['decision']}]\n상태: {data['trade_status']}\n"
            report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            report += f"💡 분석근거: {data['reason']}\n\n📰 관련 뉴스:\n{data['news']}"
            self.ai_report_text.insert("1.0", report)
            self.ai_report_text.configure(state="disabled")

            self.refresh_db_tabs()

    def refresh_db_tabs(self):
        history = get_db_history()
        self.history_box.delete("1.0", "end")
        for h in history:
            self.history_box.insert(
                "end", f"📅 {h[0]} | {h[1]} | {h[2]} | 가격:{h[3]:,} | 손익:{h[4]:,}\n"
            )

        holdings = get_holdings()
        self.holdings_box.delete("1.0", "end")
        self.holdings_box.insert("end", "Ticker | 수량 | 평단가\n" + "-" * 40 + "\n")
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
                self.predict_box.insert("1.0", f"🚀 AI 오늘의 분석:\n{pred}"),
            ),
        )
        self.trading_main_loop()

    def trading_main_loop(self):
        token = get_access_token()
        while True:
            ticker = self.ticker_menu.get().split("(")[1].replace(")", "")
            try:
                goal = int(self.goal_input.get())
            except:
                goal = 5000

            result = run_trading_cycle(token, ticker, goal)
            if "error" not in result:
                self.after(0, lambda r=result: self.update_ui(r))
                if result.get("status") == "GOAL_REACHED":
                    break

            for i in range(61):
                self.after(0, lambda v=i: self.prog_bar.set(v / 60))
                time.sleep(1)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
