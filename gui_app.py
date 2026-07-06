# gui_app.py
import threading
import time
from datetime import datetime

import customtkinter as ctk

from db_manager import create_tables, get_statistics, reset_db_completely, update_cash
from kis_api import get_access_token
from main_logic import (
    SCAN_POOL,
    get_db_history,
    get_holdings_with_valuation,
    predict_best_stock,
    run_trading_cycle,
)

ctk.set_appearance_mode("dark")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 실전 단타 스테이션 v3.0 (Professional Analysis)")
        self.geometry("1100x850")
        create_tables()

        # [1] 상단 상태바
        self.header = ctk.CTkFrame(self, height=35, fg_color="#1a1a1a")
        self.header.pack(fill="x", padx=10, pady=2)
        self.clock_label = ctk.CTkLabel(
            self.header, text="--:--:--", font=("Consolas", 14), text_color="#00FF00"
        )
        self.clock_label.pack(side="left", padx=20)

        self.btn_reset = ctk.CTkButton(
            self.header,
            text="DB 데이터 리셋",
            width=100,
            height=20,
            fg_color="#660000",
            hover_color="#990000",
            command=self.confirm_reset,
        )
        self.btn_reset.pack(side="right", padx=10)
        self.status_signal = ctk.CTkLabel(
            self.header,
            text="● SYSTEM LIVE",
            font=("Malgun Gothic", 12),
            text_color="green",
        )
        self.status_signal.pack(side="right", padx=20)

        # [2] AI 시장 예측 보고서
        self.predict_box = ctk.CTkTextbox(
            self, height=80, font=("Malgun Gothic", 12), text_color="#FFD700"
        )
        self.predict_box.pack(fill="x", padx=15, pady=5)
        self.predict_box.insert(
            "0.0", "🚀 시스템을 가동하면 AI가 오늘 시장의 거시적 흐름을 분석합니다."
        )

        # [3] 중앙 메인 프레임
        self.mid_frame = ctk.CTkFrame(self)
        self.mid_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self.ai_report_text = ctk.CTkTextbox(self.mid_frame, font=("Malgun Gothic", 14))
        self.ai_report_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.stat_panel = ctk.CTkFrame(self.mid_frame, width=320, fg_color="#212121")
        self.stat_panel.pack(side="right", fill="both", expand=False, padx=5, pady=5)

        # 시드/목표 설정
        ctk.CTkLabel(
            self.stat_panel, text="💰 시드머니", font=("Malgun Gothic", 11)
        ).pack()
        self.seed_input = ctk.CTkEntry(
            self.stat_panel, width=120, height=22, justify="center"
        )
        self.seed_input.insert(0, "1000000")
        self.seed_input.pack()
        ctk.CTkButton(
            self.stat_panel, text="업데이트", width=80, height=20, command=self.set_seed
        ).pack(pady=2)

        ctk.CTkLabel(
            self.stat_panel, text="🎯 목표 수익", font=("Malgun Gothic", 11)
        ).pack()
        self.goal_input = ctk.CTkEntry(
            self.stat_panel, width=120, height=22, justify="center", fg_color="#1a3a1a"
        )
        self.goal_input.insert(0, "50000")  # 목표 수익을 넉넉히 상향
        self.goal_input.pack()

        self.price_label = ctk.CTkLabel(
            self.stat_panel, text="--원", font=("Consolas", 35, "bold")
        )
        self.price_label.pack(pady=10)
        self.today_profit_label = ctk.CTkLabel(
            self.stat_panel,
            text="오늘: 0원",
            font=("Malgun Gothic", 18, "bold"),
            text_color="#00FF00",
        )
        self.today_profit_label.pack()
        self.stats_label = ctk.CTkLabel(
            self.stat_panel,
            text="주간: 0원 | 월간: 0원",
            font=("Malgun Gothic", 12),
            text_color="gray",
        )
        self.stats_label.pack()
        self.db_balance_label = ctk.CTkLabel(
            self.stat_panel, text="보유 예수금: --원", font=("Malgun Gothic", 13)
        )
        self.db_balance_label.pack(pady=5)

        self.ticker_menu = ctk.CTkOptionMenu(
            self.stat_panel,
            values=[f"{k} ({v})" for k, v in SCAN_POOL.items()],
            width=200,
        )
        self.ticker_menu.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.stat_panel, width=250)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        # [4] 하단 정밀 탭 메뉴 (데이터 시각화 강화)
        self.tab_view = ctk.CTkTabview(self, height=250)
        self.tab_view.pack(fill="x", padx=15, pady=5)
        self.tab_history = self.tab_view.add("거래상세 히스토리")
        self.tab_holdings = self.tab_view.add("실시간 평가 잔고")

        self.history_box = ctk.CTkTextbox(
            self.tab_history, font=("Consolas", 10), fg_color="#000000"
        )
        self.history_box.pack(fill="both", expand=True)
        self.holdings_box = ctk.CTkTextbox(
            self.tab_holdings, font=("Consolas", 10), fg_color="#000000"
        )
        self.holdings_box.pack(fill="both", expand=True)

        # [5] 시스템 로그 및 가동 버튼
        self.log_box = ctk.CTkTextbox(
            self, height=60, font=("Consolas", 10), fg_color="#1a1a1a"
        )
        self.log_box.pack(fill="x", padx=15, pady=5)

        self.btn_start = ctk.CTkButton(
            self,
            text="AI 트레이딩 엔진 풀 가동",
            command=self.start_engine,
            fg_color="green",
            height=45,
            font=("Malgun Gothic", 14, "bold"),
        )
        self.btn_start.pack(pady=5)

        self.update_clock()
        self.refresh_ui_from_db()

    def confirm_reset(self):
        """DB 리셋 확인 절차"""
        reset_db_completely()
        self.add_log("☢️ DB 초기화 완료. 시드머니 100만원으로 재시작합니다.")
        self.refresh_ui_from_db()

    def update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.configure(text=f"현재시간: {now}")
        curr = self.status_signal.cget("text_color")
        self.status_signal.configure(
            text_color="green" if curr != "green" else "#00FF00"
        )
        self.after(1000, self.update_clock)

    def add_log(self, msg):
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see("end")

    def set_seed(self):
        try:
            amt = int(self.seed_input.get())
            update_cash(amt)
            self.db_balance_label.configure(text=f"보유 예수금: {amt:,}원")
            self.add_log(f"💰 예수금 {amt:,}원 재설정 완료")
        except:
            self.add_log("❌ 숫자만 입력하세요")

    def refresh_ui_from_db(self):
        """DB에서 데이터를 가져와 탭 메뉴와 기본 정보 갱신"""
        # 히스토리 탭 (상세)
        h_data = get_db_history()
        self.history_box.delete("1.0", "end")
        self.history_box.insert(
            "end",
            f"{'거래시간':^20} | {'종목':^10} | {'구분':^4} | {'체결가':^10} | {'수량':^4} | {'손익':^10}\n"
            + "=" * 75
            + "\n",
        )
        for h in h_data:
            self.history_box.insert(
                "end",
                f"{h[0]} | {h[1]:<10} | {h[2]:^4} | {h[3]:>10,} | {h[4]:>4} | {h[5]:>10,}\n",
            )

        # 보유현황 탭 (실시간 평가)
        hold_data = get_holdings_with_valuation()
        self.holdings_box.delete("1.0", "end")
        self.holdings_box.insert(
            "end",
            f"{'종목':^10} | {'수량':^4} | {'평단가':^10} | {'현재가':^10} | {'평가손익':^10} | {'수익률':^6}\n"
            + "=" * 75
            + "\n",
        )
        for hold in hold_data:
            color_tag = "red" if hold[4] > 0 else "blue"
            self.holdings_box.insert(
                "end",
                f"{hold[0]:<10} | {hold[1]:>4}주 | {hold[2]:>10,} | {hold[3]:>10,} | {hold[4]:>10,} | {hold[5]:>6.2f}%\n",
            )

        # 통계 갱신
        t, w, m = get_statistics()
        self.today_profit_label.configure(text=f"오늘 수익: {t:,}원")
        self.stats_label.configure(text=f"주간: {w:,}원 | 월간: {m:,}원")

    def update_ui(self, data):
        self.db_balance_label.configure(
            text=f"보유 예수금: {data.get('db_balance', 0):,}원"
        )

        if data["status"] == "GOAL_REACHED":
            self.add_log("🎊 목표 달성! 안전을 위해 거래를 종료합니다.")
            self.predict_box.delete("1.0", "end")
            self.predict_box.insert(
                "1.0", f"🏆 목표 달성 완료! 금일 누적 수익: {data['today_profit']:,}원"
            )
            self.refresh_ui_from_db()
            return

        if data["status"] == "ACTIVE":
            self.price_label.configure(text=f"{data['price']:,}원")
            self.ai_report_text.configure(state="normal")
            self.ai_report_text.delete("1.0", "end")
            self.ai_report_text.insert(
                "1.0",
                f"🎯 분석: {data['ticker']} | 결정: {data['decision']}\n상태: {data['trade_status']}\n{'-'*30}\n💡 근거: {data['reason']}\n\n📰 뉴스: {data['news']}",
            )
            self.ai_report_text.configure(state="disabled")
            self.add_log(f"📊 스캔: {data['ticker']} ({data['trade_status']})")
            self.refresh_ui_from_db()

    def start_engine(self):
        self.btn_start.configure(state="disabled", text="엔진 가동 중...")
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        pred = predict_best_stock()
        self.after(
            0,
            lambda: (
                self.predict_box.delete("1.0", "end"),
                self.predict_box.insert("1.0", f"🚀 AI 시장 예측: {pred}"),
            ),
        )
        token = get_access_token()
        while True:
            ticker = self.ticker_menu.get().split("(")[1].replace(")", "")
            try:
                goal = int(self.goal_input.get())
            except:
                goal = 50000

            res = run_trading_cycle(token, ticker, goal)
            self.after(0, lambda r=res: self.update_ui(r))

            for i in range(61):
                self.after(0, lambda v=i: self.progress_bar.set(v / 60))
                time.sleep(1)
            if res.get("status") == "GOAL_REACHED":
                break


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
