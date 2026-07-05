# gui_app.py (전체 교체)
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
        self.title("AI 로컬 가상 매매 시스템 v1.4")
        self.geometry("1100x900")

        # 헤더
        self.header_label = ctk.CTkLabel(
            self,
            text="🛰️ 실시간 뉴스 기반 종목 추천 및 소액 단타 대시보드",
            font=("Malgun Gothic", 24, "bold"),
        )
        self.header_label.pack(pady=20)

        # 메인 프레임
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 왼쪽 - AI 분석
        self.ai_frame = ctk.CTkFrame(self.main_frame)
        self.ai_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.ai_text = ctk.CTkTextbox(
            self.ai_frame, font=("Malgun Gothic", 15), width=500
        )
        self.ai_text.pack(fill="both", expand=True, padx=15, pady=15)

        # 오른쪽 - 설정 및 시세
        self.info_frame = ctk.CTkFrame(self.main_frame, width=380)
        self.info_frame.pack(side="right", fill="both", expand=False, padx=10, pady=10)

        # [목표 수익 설정 칸]
        self.goal_label = ctk.CTkLabel(
            self.info_frame,
            text="🎯 오늘의 목표 수익 (원)",
            font=("Malgun Gothic", 14, "bold"),
        )
        self.goal_label.pack(pady=(20, 5))
        self.goal_entry = ctk.CTkEntry(self.info_frame, placeholder_text="5000")
        self.goal_entry.insert(0, "5000")  # 기본값 5,000원
        self.goal_entry.pack(pady=5)

        # 종목 선택
        self.ticker_label = ctk.CTkLabel(
            self.info_frame,
            text="📡 뉴스 호재 분석 종목",
            font=("Malgun Gothic", 14, "bold"),
        )
        self.ticker_label.pack(pady=(20, 5))
        self.dynamic_list = get_dynamic_stocks()
        self.selected_ticker = ctk.StringVar(value=self.dynamic_list[0])
        self.ticker_menu = ctk.CTkOptionMenu(
            self.info_frame, values=self.dynamic_list, variable=self.selected_ticker
        )
        self.ticker_menu.pack(pady=10)

        # 시세 표시
        self.price_label = ctk.CTkLabel(
            self.info_frame, text="현재가: --", font=("Malgun Gothic", 30, "bold")
        )
        self.price_label.pack(pady=30)
        self.change_label = ctk.CTkLabel(
            self.info_frame, text="변동률: --", font=("Malgun Gothic", 18)
        )
        self.change_label.pack(pady=5)

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="가상 예수금: 0원", font=("Malgun Gothic", 16)
        )
        self.balance_label.pack(pady=20)

        # 하단 로그
        self.log_text = ctk.CTkTextbox(self, height=120, font=("Consolas", 11))
        self.log_text.pack(fill="x", padx=20, pady=10)

        self.start_button = ctk.CTkButton(
            self,
            text="실시간 분석 및 소액 단타 시작",
            command=self.start_trading_thread,
            fg_color="green",
            height=45,
        )
        self.start_button.pack(pady=20)

    def update_ui(self, data):
        color = (
            "#FF4444"
            if data["arrow"] == "▲"
            else "#4444FF" if data["arrow"] == "▼" else "#FFFFFF"
        )
        self.price_label.configure(
            text=f"{data['price']:,}원 {data['arrow']}", text_color=color
        )
        self.change_label.configure(
            text=f"변동: {data['change_pct']:+.2f}%", text_color=color
        )

        self.ai_text.configure(state="normal")
        self.ai_text.delete("1.0", "end")
        report = f"🎯 분석 종목: {self.selected_ticker.get()}\n"
        report += f"📡 AI 판단: [{data['decision']}]\n"
        report += f"💰 설정 목표 수익: {self.goal_entry.get()}원\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += f"📰 실시간 수집 뉴스:\n{data['news']}\n\n"
        report += f"🧠 AI 단타 수익 전망:\n{data['reason']}\n"
        self.ai_text.insert("1.0", report)
        self.ai_text.configure(state="disabled")

        self.balance_label.configure(text=f"가상 예수금: {data['balance']:,}원")

    def start_trading_thread(self):
        self.start_button.configure(state="disabled", text="실시간 분석 중...")
        threading.Thread(target=self.trading_loop, daemon=True).start()

    def trading_loop(self):
        token = get_access_token()
        while True:
            ticker_code = self.selected_ticker.get().split("(")[1].replace(")", "")
            goal = int(self.goal_entry.get())  # 사용자가 입력한 목표 수익값 읽기
            result = run_trading_cycle(token, ticker_code, goal)
            if "error" not in result:
                self.after(0, lambda: self.update_ui(result))
            time.sleep(60)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
