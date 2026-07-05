# gui_app.py
import threading
import time

import customtkinter as ctk
from main_logic import get_dynamic_stocks, predict_best_stock, run_trading_cycle

from kis_api import get_access_token

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 로컬 가상 매매 대시보드 v1.7")
        self.geometry("1100x950")

        # 상단 AI 오늘의 예측 배너
        self.predict_frame = ctk.CTkFrame(self, fg_color="#1e1e1e")
        self.predict_frame.pack(fill="x", padx=20, pady=10)
        self.predict_label = ctk.CTkLabel(
            self.predict_frame,
            text="🛰️ AI 시장 분석 대기 중...",
            font=("Malgun Gothic", 13, "bold"),
            text_color="#FFD700",
        )
        self.predict_label.pack(pady=10)

        # 프로그래스 바
        self.progress_bar = ctk.CTkProgressBar(self, width=800)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=5)

        # 메인 프레임
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # 왼쪽 - AI 리포트 창
        self.ai_frame = ctk.CTkFrame(self.main_frame)
        self.ai_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.ai_text = ctk.CTkTextbox(
            self.ai_frame, font=("Malgun Gothic", 15), width=550
        )
        self.ai_text.pack(fill="both", expand=True, padx=15, pady=15)

        # 오른쪽 - 정보 및 설정
        self.info_frame = ctk.CTkFrame(self.main_frame, width=380)
        self.info_frame.pack(side="right", fill="both", expand=False, padx=10, pady=10)

        ctk.CTkLabel(
            self.info_frame, text="🎯 목표 수익(원)", font=("Malgun Gothic", 14)
        ).pack(pady=5)
        self.goal_entry = ctk.CTkEntry(self.info_frame)
        self.goal_entry.insert(0, "5000")
        self.goal_entry.pack(pady=5)

        ctk.CTkLabel(
            self.info_frame, text="📡 분석 종목", font=("Malgun Gothic", 14)
        ).pack(pady=5)
        self.dynamic_list = get_dynamic_stocks()
        self.selected_ticker = ctk.StringVar(value=self.dynamic_list[0])
        self.ticker_menu = ctk.CTkOptionMenu(
            self.info_frame, values=self.dynamic_list, variable=self.selected_ticker
        )
        self.ticker_menu.pack(pady=5)

        self.price_label = ctk.CTkLabel(
            self.info_frame, text="현재가: --원", font=("Malgun Gothic", 30, "bold")
        )
        self.price_label.pack(pady=20)

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="가상 예수금: 0원", font=("Malgun Gothic", 16)
        )
        self.balance_label.pack(pady=10)

        # 하단 - 매매 히스토리
        ctk.CTkLabel(
            self, text="📜 매매 히스토리 및 정산", font=("Malgun Gothic", 14, "bold")
        ).pack()
        self.history_text = ctk.CTkTextbox(
            self, height=180, font=("Consolas", 11), fg_color="#111111"
        )
        self.history_text.pack(fill="x", padx=20, pady=10)

        self.start_button = ctk.CTkButton(
            self,
            text="AI 시장 예측 및 시뮬레이션 시작",
            command=self.start_trading_thread,
            fg_color="green",
            height=45,
        )
        self.start_button.pack(pady=10)

    def write_history(self, message):
        self.history_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.history_text.see("end")

    def update_ui(self, data):
        color = (
            "#FF4444"
            if data["arrow"] == "▲"
            else "#4444FF" if data["arrow"] == "▼" else "#FFFFFF"
        )
        self.price_label.configure(
            text=f"{data['price']:,}원 {data['arrow']}", text_color=color
        )

        self.ai_text.configure(state="normal")
        self.ai_text.delete("1.0", "end")
        content = f"🎯 분석 대상: {self.selected_ticker.get()}\n"
        content += f"📡 AI 판단: [{data['decision']}]\n"
        content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        content += f"📰 실시간 수집 뉴스:\n{data['news']}\n\n"
        content += f"🧠 AI 단타 수익 전망:\n{data['reason']}\n"
        self.ai_text.insert("1.0", content)
        self.ai_text.configure(state="disabled")

        self.balance_label.configure(text=f"가상 예수금: {data['balance']:,}원")
        if data["trade_status"] != "IDLE":
            self.write_history(
                f"▶ {data['trade_status']} | {data['ticker']} @ {data['price']:,}원"
            )

    def start_trading_thread(self):
        self.start_button.configure(state="disabled", text="AI 분석 및 스캐닝 중...")
        threading.Thread(target=self.initial_prediction_phase, daemon=True).start()

    def initial_prediction_phase(self):
        """프로그램 시작 시 한 번만 수행하는 시장 예측 단계"""
        prediction = predict_best_stock()
        self.after(
            0,
            lambda: self.predict_label.configure(text=f"🚀 오늘의 AI 픽: {prediction}"),
        )
        self.write_history("✅ 오늘의 시장 뉴스 분석 및 예측 완료")
        self.trading_loop()

    def trading_loop(self):
        token = get_access_token()
        while True:
            ticker_code = self.selected_ticker.get().split("(")[1].replace(")", "")
            goal = int(self.goal_entry.get())
            result = run_trading_cycle(token, ticker_code, goal)

            if "error" not in result:
                self.after(0, lambda r=result: self.update_ui(r))

            # 60초 프로그래스 바 대기
            for i in range(61):
                self.after(0, lambda v=i: self.progress_bar.set(v / 60))
                time.sleep(1)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
