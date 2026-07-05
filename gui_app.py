import threading
import time

import customtkinter as ctk
from main_logic import (
    get_db_history,
    get_dynamic_stocks,
    predict_best_stock,
    run_trading_cycle,
)

from kis_api import get_access_token

ctk.set_appearance_mode("dark")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 로컬 가상 매매 시스템 v1.8")
        self.geometry("1100x950")

        # 1. 상단 예측 배너
        self.predict_text = ctk.CTkTextbox(
            self, height=120, font=("Malgun Gothic", 12), text_color="#FFD700"
        )
        self.predict_text.pack(fill="x", padx=20, pady=10)
        self.predict_text.insert("0.0", "🛰️ 버튼을 누르면 AI 시장 예측이 시작됩니다...")

        # 2. 진행 바
        self.progress_bar = ctk.CTkProgressBar(self, width=800)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=5)

        # 3. 메인 영역
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.ai_text = ctk.CTkTextbox(
            self.main_frame, font=("Malgun Gothic", 15), width=600
        )
        self.ai_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.info_frame = ctk.CTkFrame(self.main_frame, width=400)
        self.info_frame.pack(side="right", fill="both", expand=False, padx=10, pady=10)

        self.ticker_menu = ctk.CTkOptionMenu(
            self.info_frame, values=get_dynamic_stocks()
        )
        self.ticker_menu.pack(pady=20)

        self.price_label = ctk.CTkLabel(
            self.info_frame, text="현재가: --원", font=("Malgun Gothic", 30, "bold")
        )
        self.price_label.pack(pady=20)

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="예수금: 조회 중...", font=("Malgun Gothic", 16)
        )
        self.balance_label.pack(pady=10)

        # 4. 하단 DB 히스토리
        ctk.CTkLabel(
            self,
            text="📜 실시간 DB 매매 내역 및 로그",
            font=("Malgun Gothic", 14, "bold"),
        ).pack()
        self.history_text = ctk.CTkTextbox(
            self, height=200, font=("Consolas", 11), fg_color="#000000"
        )
        self.history_text.pack(fill="x", padx=20, pady=10)

        self.start_button = ctk.CTkButton(
            self,
            text="AI 전략 가동 및 DB 동기화",
            command=self.start_trading_thread,
            fg_color="green",
            height=50,
        )
        self.start_button.pack(pady=10)

    def update_ui(self, data):
        self.ai_text.configure(state="normal")
        self.ai_text.delete("1.0", "end")
        content = (
            f"🎯 분석 대상: {self.ticker_menu.get()}\n결정: [{data['decision']}]\n"
        )
        content += (
            f"━━━━━━━━━━━━━━━━━━\n💡 이유: {data['reason']}\n\n📰 뉴스:\n{data['news']}"
        )
        self.ai_text.insert("1.0", content)
        self.ai_text.configure(state="disabled")

        self.price_label.configure(text=f"{data['price']:,}원")
        self.balance_label.configure(text=f"예수금: {data['balance']:,}원")

        # DB 히스토리 갱신
        history = get_db_history()
        self.history_text.delete("1.0", "end")
        for h in history:
            self.history_text.insert(
                "end", f"[{h[0]}] {h[1]} | {h[2]} | 가격:{h[3]:,} | 손익:{h[4]:,}\n"
            )

    def start_trading_thread(self):
        self.start_button.configure(state="disabled")
        threading.Thread(target=self.initial_work, daemon=True).start()

    def initial_work(self):
        pred = predict_best_stock()
        self.after(
            0,
            lambda: (
                self.predict_text.delete("1.0", "end"),
                self.predict_text.insert("1.0", f"🚀 예측: {pred}"),
            ),
        )
        self.trading_loop()

    def trading_loop(self):
        token = get_access_token()
        while True:
            ticker = self.ticker_menu.get().split("(")[1].replace(")", "")
            res = run_trading_cycle(token, ticker)
            if "error" not in res:
                self.after(0, lambda: self.update_ui(res))

            for i in range(61):
                self.after(0, lambda v=i: self.progress_bar.set(v / 60))
                time.sleep(1)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
