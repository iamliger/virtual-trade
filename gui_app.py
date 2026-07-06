# gui_app.py
import threading
import time
from datetime import datetime

import customtkinter as ctk

from db_manager import create_tables, get_statistics, sqlite3, update_cash
from kis_api import get_access_token
from main_logic import SCAN_POOL, predict_best_stock, run_trading_cycle

ctk.set_appearance_mode("dark")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 실전 단타 시뮬레이터 v2.7 (Heartbeat & Vitality)")
        self.geometry("1100x800")
        create_tables()

        # [1] 상단 상태바 (시계 및 생존 신호)
        self.header = ctk.CTkFrame(self, height=40, fg_color="#1a1a1a")
        self.header.pack(fill="x", padx=10, pady=5)
        self.clock_label = ctk.CTkLabel(
            self.header, text="--:--:--", font=("Consolas", 14), text_color="#00FF00"
        )
        self.clock_label.pack(side="left", padx=20)
        self.status_signal = ctk.CTkLabel(
            self.header,
            text="● SYSTEM LIVE",
            font=("Malgun Gothic", 12),
            text_color="green",
        )
        self.status_signal.pack(side="right", padx=20)

        # [2] AI 예측 배너
        self.predict_box = ctk.CTkTextbox(
            self, height=80, font=("Malgun Gothic", 12), text_color="#FFD700"
        )
        self.predict_box.pack(fill="x", padx=15, pady=5)
        self.predict_box.insert(
            "0.0", "🚀 AI 시장 예측 리포트 대기 중... 아래 버튼을 눌러 시작하세요."
        )

        # [3] 중앙 레이아웃
        self.mid_frame = ctk.CTkFrame(self)
        self.mid_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self.ai_report_text = ctk.CTkTextbox(self.mid_frame, font=("Malgun Gothic", 14))
        self.ai_report_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.stat_panel = ctk.CTkFrame(self.mid_frame, width=320, fg_color="#212121")
        self.stat_panel.pack(side="right", fill="both", expand=False, padx=5, pady=5)

        # 설정 섹션
        ctk.CTkLabel(
            self.stat_panel, text="💰 시드머니", font=("Malgun Gothic", 11)
        ).pack(pady=(5, 0))
        self.seed_input = ctk.CTkEntry(
            self.stat_panel, width=120, height=22, justify="center"
        )
        self.seed_input.insert(0, "1000000")
        self.seed_input.pack()
        self.btn_set_seed = ctk.CTkButton(
            self.stat_panel, text="업데이트", width=80, height=20, command=self.set_seed
        ).pack(pady=2)

        ctk.CTkLabel(
            self.stat_panel, text="🎯 목표 수익", font=("Malgun Gothic", 11)
        ).pack(pady=(5, 0))
        self.goal_input = ctk.CTkEntry(
            self.stat_panel, width=120, height=22, justify="center", fg_color="#1a3a1a"
        )
        self.goal_input.insert(0, "5000")
        self.goal_input.pack()

        # 전광판 섹션
        self.price_label = ctk.CTkLabel(
            self.stat_panel, text="--원", font=("Consolas", 35, "bold")
        )
        self.price_label.pack(pady=15)
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
        self.db_balance_label.pack(pady=10)

        self.ticker_menu = ctk.CTkOptionMenu(
            self.stat_panel,
            values=[f"{k} ({v})" for k, v in SCAN_POOL.items()],
            width=200,
        )
        self.ticker_menu.pack(pady=10)

        self.prog_bar = ctk.CTkProgressBar(self.stat_panel, width=250)
        self.prog_bar.set(0)
        self.prog_bar.pack(pady=15)

        # [4] 하단 시스템 로그 (탭 제거하고 통합하여 가시성 확보)
        self.log_box = ctk.CTkTextbox(
            self, height=150, font=("Consolas", 10), fg_color="#000000"
        )
        self.log_box.pack(fill="x", padx=15, pady=5)

        self.btn_start = ctk.CTkButton(
            self,
            text="AI 전략 가동 및 자동 매매 시작",
            command=self.start_engine,
            fg_color="green",
            height=40,
            font=("Malgun Gothic", 14, "bold"),
        )
        self.btn_start.pack(pady=10)

        # 초기 구동
        self.update_clock()

    def update_clock(self):
        """매초 시계와 생존 신호를 업데이트 (죽지 않는 스레드)"""
        now = datetime.now().strftime("%H:%M:%S")
        self.clock_label.configure(text=f"현재시간: {now}")
        # 깜빡이는 효과로 생동감 부여
        current_color = self.status_signal.cget("text_color")
        next_color = "green" if current_color == "#004d00" else "#00FF00"
        self.status_signal.configure(text_color=next_color)
        self.after(1000, self.update_clock)

    def add_log(self, msg):
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see("end")

    def set_seed(self):
        try:
            amt = int(self.seed_input.get())
            update_cash(amt)
            self.add_log(f"💰 예수금 {amt:,}원으로 재설정 완료")
        except:
            self.add_log("❌ 숫자만 입력하세요")

    def update_ui(self, data):
        # 통계 레이블은 항상 업데이트
        self.today_profit_label.configure(
            text=f"오늘 수익: {data.get('today_profit', 0):,}원"
        )
        self.stats_label.configure(
            text=f"주간: {data.get('weekly_profit', 0):,}원 | 월간: {data.get('monthly_profit', 0):,}원"
        )

        if data["status"] == "GOAL_REACHED":
            self.today_profit_label.configure(text_color="yellow")
            self.add_log("🎊 알림: 오늘 목표 수익을 달성하여 매매를 종료합니다.")
            self.predict_box.delete("1.0", "end")
            self.predict_box.insert(
                "1.0", "🏆 목표 달성! 오늘의 매매가 성공적으로 종료되었습니다."
            )
            return

        if data["status"] == "ACTIVE":
            self.price_label.configure(text=f"{data['price']:,}원")
            self.db_balance_label.configure(
                text=f"보유 예수금: {data['db_balance']:,}원"
            )
            self.ai_report_text.configure(state="normal")
            self.ai_report_text.delete("1.0", "end")
            self.ai_report_text.insert(
                "1.0",
                f"🎯 분석: {data['ticker']} | 결정: {data['decision']}\n{'-'*30}\n💡 근거: {data['reason']}\n\n📰 뉴스: {data['news']}",
            )
            self.ai_report_text.configure(state="disabled")
            self.add_log(f"📊 스캔 완료: {data['ticker']} ({data['trade_status']})")

    def start_engine(self):
        self.btn_start.configure(state="disabled", text="엔진 가동 중...")
        self.add_log("🚀 시스템 가동: AI 분석 및 루프를 시작합니다.")
        threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        pred = predict_best_stock()
        self.after(
            0,
            lambda: (
                self.predict_box.delete("1.0", "end"),
                self.predict_box.insert("1.0", f"🚀 AI 오늘의 분석: {pred}"),
            ),
        )
        token = get_access_token()
        while True:
            ticker = self.ticker_menu.get().split("(")[1].replace(")", "")
            try:
                goal = int(self.goal_input.get())
            except:
                goal = 5000

            res = run_trading_cycle(token, ticker, goal)
            self.after(0, lambda r=res: self.update_ui(r))

            # 60초 프로그래스 바 (부드럽게 업데이트)
            for i in range(61):
                self.after(0, lambda v=i: self.prog_bar.set(v / 60))
                time.sleep(1)
            if res.get("status") == "GOAL_REACHED":
                break


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
