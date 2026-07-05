# gui_app.py
import threading
import time

import customtkinter as ctk
from main_logic import get_dynamic_stocks, run_trading_cycle

from kis_api import get_access_token

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 로컬 가상 매매 시스템 v1.6")
        self.geometry("1100x950")

        # 상단 헤더
        self.header_label = ctk.CTkLabel(
            self,
            text="🛰️ 실시간 AI 분석 및 일일 정산 시스템",
            font=("Malgun Gothic", 24, "bold"),
        )
        self.header_label.pack(pady=10)

        # 💡 프로그래스 바 (지루함 해소용)
        self.prog_label = ctk.CTkLabel(
            self, text="다음 분석까지 남은 시간", font=("Malgun Gothic", 12)
        )
        self.prog_label.pack()
        self.progress_bar = ctk.CTkProgressBar(self, width=800)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=5)

        # 메인 프레임
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # 왼쪽 - AI 리포트
        self.ai_frame = ctk.CTkFrame(self.main_frame)
        self.ai_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.ai_text = ctk.CTkTextbox(
            self.ai_frame, font=("Malgun Gothic", 15), width=500
        )
        self.ai_text.pack(fill="both", expand=True, padx=15, pady=15)

        # 오른쪽 - 설정
        self.info_frame = ctk.CTkFrame(self.main_frame, width=350)
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
            self.info_frame, text="현재가: --원", font=("Malgun Gothic", 26, "bold")
        )
        self.price_label.pack(pady=20)

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="가상 예수금: 0원", font=("Malgun Gothic", 15)
        )
        self.balance_label.pack(pady=10)

        # 하단 - 매매 히스토리 (수익 정산 내역)
        ctk.CTkLabel(
            self, text="📜 실시간 매매 히스토리", font=("Malgun Gothic", 14, "bold")
        ).pack()
        self.history_text = ctk.CTkTextbox(
            self, height=180, font=("Consolas", 11), fg_color="#1a1a1a"
        )
        self.history_text.pack(fill="x", padx=20, pady=10)

        self.start_button = ctk.CTkButton(
            self,
            text="실전 시뮬레이션 시작",
            command=self.start_trading_thread,
            fg_color="green",
            height=40,
        )
        self.start_button.pack(pady=10)

    def write_history(self, message):
        self.history_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.history_text.see("end")

    def update_ui(self, data):
        self.price_label.configure(text=f"{data['price']:,}원")
        self.balance_label.configure(text=f"가상 예수금: {data['balance']:,}원")

        self.ai_text.configure(state="normal")
        self.ai_text.delete("1.0", "end")
        content = f"🎯 분석 종목: {self.selected_ticker.get()}\n"
        content += f"📡 AI 판단: [{data['decision']}]\n"
        content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        content += f"📰 실시간 뉴스 분석:\n{data['news']}\n\n"
        content += f"💡 AI 판단 근거:\n{data['reason']}\n"
        self.ai_text.insert("1.0", content)
        self.ai_text.configure(state="disabled")

        if data["trade_status"] != "IDLE":
            self.write_history(
                f"▶ {data['trade_status']} | {data['ticker']} @ {data['price']:,}원"
            )

    def start_trading_thread(self):
        self.start_button.configure(state="disabled", text="구동 중...")
        threading.Thread(target=self.trading_loop, daemon=True).start()

    def trading_loop(self):
        token = get_access_token()
        while True:
            ticker_code = self.selected_ticker.get().split("(")[1].replace(")", "")
            goal = int(self.goal_entry.get())
            result = run_trading_cycle(token, ticker_code, goal)

            if "error" not in result:
                self.after(0, lambda r=result: self.update_ui(r))

            # 💡 60초 동안 프로그래스 바 업데이트
            for i in range(61):
                self.after(0, lambda v=i: self.progress_bar.set(v / 60))
                time.sleep(1)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
