# gui_app.py
import threading
import time

import customtkinter as ctk
from main_logic import WATCH_LIST, run_trading_cycle

from kis_api import get_access_token

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 로컬 가상 매매 시스템 v1.2")
        self.geometry("1000x800")

        # [상단 헤더]
        self.header_label = ctk.CTkLabel(
            self,
            text="🤖 로컬 AI 종목 추천 및 자동 매매 대시보드",
            font=("Malgun Gothic", 24, "bold"),
        )
        self.header_label.pack(pady=20)

        # [메인 프레임]
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # 1. 왼쪽 - AI 분석 및 뉴스 리포트
        self.ai_frame = ctk.CTkFrame(self.main_frame)
        self.ai_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.ai_title = ctk.CTkLabel(
            self.ai_frame,
            text="🧠 실시간 종목 분석 & 뉴스",
            font=("Malgun Gothic", 18, "bold"),
        )
        self.ai_title.pack(pady=10)

        self.ai_text = ctk.CTkTextbox(
            self.ai_frame, font=("Malgun Gothic", 14), width=500
        )
        self.ai_text.pack(fill="both", expand=True, padx=15, pady=15)
        self.ai_text.insert("0.0", "분석 시작 버튼을 눌러주세요.\n")

        # 2. 오른쪽 - 종목 선택 및 상태 정보
        self.info_frame = ctk.CTkFrame(self.main_frame, width=350)
        self.info_frame.pack(side="right", fill="both", expand=False, padx=10, pady=10)

        # [종목 선택 메뉴]
        self.ticker_title = ctk.CTkLabel(
            self.info_frame,
            text="📡 분석 종목 선택",
            font=("Malgun Gothic", 14, "bold"),
        )
        self.ticker_title.pack(pady=(20, 5))

        self.ticker_options = [f"{name} ({code})" for name, code in WATCH_LIST.items()]
        self.selected_ticker = ctk.StringVar(value=self.ticker_options[0])
        self.ticker_menu = ctk.CTkOptionMenu(
            self.info_frame, values=self.ticker_options, variable=self.selected_ticker
        )
        self.ticker_menu.pack(pady=10)

        self.price_label = ctk.CTkLabel(
            self.info_frame, text="현재가: --원", font=("Malgun Gothic", 22, "bold")
        )
        self.price_label.pack(pady=30)

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="가상 예수금: 조회 중...", font=("Malgun Gothic", 16)
        )
        self.balance_label.pack(pady=10)

        # [하단 로그 콘솔]
        self.log_text = ctk.CTkTextbox(self, height=120, font=("Consolas", 11))
        self.log_text.pack(fill="x", padx=20, pady=10)

        # [시작 버튼]
        self.start_button = ctk.CTkButton(
            self,
            text="자동 매매 및 분석 시작",
            command=self.start_trading_thread,
            fg_color="green",
            height=45,
        )
        self.start_button.pack(pady=15)

    def write_log(self, message):
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")

    def update_ui(self, data):
        """백엔드 데이터를 받아 화면을 실시간 갱신"""
        self.ai_text.configure(state="normal")
        self.ai_text.delete("1.0", "end")

        content = f"대상 종목: {data['ticker']}\n"
        content += f"결정: [{data['decision']}]\n"
        content += f"------------------------------------------\n"
        content += f"💡 AI 판단 근거:\n{data['reason']}\n\n"
        content += f"------------------------------------------\n"
        content += f"📰 최신 관련 뉴스:\n{data['news']}"

        self.ai_text.insert("1.0", content)
        self.ai_text.configure(state="disabled")

        self.price_label.configure(text=f"현재가: {data['price']:,}원")
        self.balance_label.configure(text=f"가상 예수금: {data['balance']:,}원")

    def start_trading_thread(self):
        self.start_button.configure(state="disabled", text="실시간 분석 중...")
        self.write_log("시스템 가동 시작...")
        threading.Thread(target=self.trading_loop, daemon=True).start()

    def trading_loop(self):
        token = get_access_token()
        while True:
            # 사용자가 선택한 종목 코드 추출 (예: 005930.KS)
            current_selection = self.selected_ticker.get()
            ticker_code = current_selection.split("(")[1].replace(")", "")

            result = run_trading_cycle(token, ticker_code)

            if "error" not in result:
                self.after(0, lambda r=result: self.update_ui(r))
                self.write_log(f"분석 완료: {result['ticker']} - {result['decision']}")
            else:
                self.after(0, lambda e=result["error"]: self.write_log(f"❌ 에러: {e}"))

            time.sleep(60)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
