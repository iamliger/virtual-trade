# gui_app.py
import threading
import time
from datetime import datetime

import customtkinter as ctk

from kis_api import get_access_token
from main_logic import (
    get_db_history,
    get_dynamic_stocks,
    predict_best_stock,
    run_trading_cycle,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 로컬 가상 매매 시스템 v1.9 (Heartbeat Engine)")
        self.geometry("1200x1000")

        self.status_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", height=40)
        self.status_frame.pack(fill="x", padx=20, pady=5)
        self.clock_label = ctk.CTkLabel(
            self.status_frame, text="", font=("Consolas", 14), text_color="#00FF00"
        )
        self.clock_label.pack(side="left", padx=20)
        self.system_status = ctk.CTkLabel(
            self.status_frame, text="상태: 대기 중", font=("Malgun Gothic", 12)
        )
        self.system_status.pack(side="right", padx=20)

        self.predict_box = ctk.CTkTextbox(
            self,
            height=120,
            font=("Malgun Gothic", 13),
            text_color="#FFD700",
            border_width=1,
        )
        self.predict_box.pack(fill="x", padx=20, pady=5)
        self.predict_box.insert(
            "0.0", "🚀 분석 엔진을 기동하면 AI 시장 예측 리포트가 표시됩니다."
        )

        self.progress_bar = ctk.CTkProgressBar(self, width=900)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=5)

        self.left_panel = ctk.CTkFrame(self.main_container)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.ai_report = ctk.CTkTextbox(
            self.left_panel, font=("Malgun Gothic", 15), border_width=1
        )
        self.ai_report.pack(fill="both", expand=True, padx=10, pady=10)

        self.right_panel = ctk.CTkFrame(self.main_container, width=380)
        self.right_panel.pack(side="right", fill="both", expand=False, padx=10, pady=10)

        ctk.CTkLabel(
            self.right_panel, text="🎯 목표 수익(원)", font=("Malgun Gothic", 13)
        ).pack(pady=5)
        self.goal_input = ctk.CTkEntry(self.right_panel, justify="center")
        self.goal_input.insert(0, "5000")
        self.goal_input.pack(pady=5)

        ctk.CTkLabel(
            self.right_panel, text="📡 분석 대상 종목", font=("Malgun Gothic", 13)
        ).pack(pady=5)
        self.ticker_selector = ctk.CTkOptionMenu(
            self.right_panel, values=get_dynamic_stocks()
        )
        self.ticker_selector.pack(pady=10)

        self.price_display = ctk.CTkLabel(
            self.right_panel,
            text="현재가: 조회 중...",
            font=("Malgun Gothic", 32, "bold"),
        )
        self.price_display.pack(pady=30)

        self.balance_display = ctk.CTkLabel(
            self.right_panel, text="예수금: 조회 중...", font=("Malgun Gothic", 16)
        )
        self.balance_display.pack(pady=10)

        ctk.CTkLabel(
            self,
            text="📜 실시간 DB 매매 내역 및 시스템 로그",
            font=("Malgun Gothic", 14, "bold"),
        ).pack()
        self.log_box = ctk.CTkTextbox(
            self,
            height=220,
            font=("Consolas", 11),
            fg_color="#000000",
            text_color="#FFFFFF",
        )
        self.log_box.pack(fill="x", padx=20, pady=10)

        self.btn_start = ctk.CTkButton(
            self,
            text="AI 분석 엔진 기동 및 자동 매매 시작",
            command=self.start_engine,
            fg_color="green",
            height=50,
            font=("Malgun Gothic", 16, "bold"),
        )
        self.btn_start.pack(pady=15)

        self.update_clock()

    def update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.configure(text=f"현재시간: {now}")
        self.after(1000, self.update_clock)

    def add_log(self, msg):
        self.log_box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see("end")

    def refresh_db_view(self):
        history = get_db_history()
        self.log_box.delete("1.0", "end")
        self.add_log("--- [실시간 DB 매매 기록 최신화] ---")
        for row in history:
            self.add_log(
                f"📅 {row[0]} | {row[1]} | {row[2]} | 가격:{row[3]:,} | 손익:{row[4]:,}"
            )
        self.add_log("----------------------------------")

    def update_display(self, data):
        if data["status"] == "WAITING":
            self.system_status.configure(text="상태: 데이터 동기화 중")
            self.ai_report.configure(state="normal")
            self.ai_report.delete("1.0", "end")
            self.ai_report.insert("1.0", f"🔄 {data['msg']}")
            self.ai_report.configure(state="disabled")
            return

        if data["status"] == "ACTIVE":
            self.system_status.configure(text=f"상태: {data['ticker']} 분석 중")
            self.ai_report.configure(state="normal")
            self.ai_report.delete("1.0", "end")
            report_txt = f"대상: {data['ticker']}\n결정: {data['decision']}\n"
            report_txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            report_txt += f"💡 분석근거: {data['reason']}\n\n"
            report_txt += f"📰 최신뉴스: {data['news']}"
            self.ai_report.insert("1.0", report_txt)
            self.ai_report.configure(state="disabled")

            self.price_display.configure(text=f"{data['price']:,}원")
            self.balance_display.configure(text=f"예수금: {data['balance']:,}원")

            if "성공" in data["trade_status"]:
                self.add_log(
                    f"✅ DB 기록: {data['trade_status']} | 가격: {data['price']:,}"
                )
                self.refresh_db_view()

    def start_engine(self):
        self.btn_start.configure(state="disabled", text="AI 엔진 구동 중...")
        threading.Thread(target=self.run_initial_analysis, daemon=True).start()

    def run_initial_analysis(self):
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
            ticker = self.ticker_selector.get().split("(")[1].replace(")", "")
            goal = int(self.goal_input.get())
            result = run_trading_cycle(token, ticker, goal)
            self.after(0, lambda r=result: self.update_display(r))
            for i in range(61):
                self.after(0, lambda v=i: self.progress_bar.set(v / 60))
                time.sleep(1)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
