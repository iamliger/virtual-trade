# gui_app.py
import threading
import time

import customtkinter as ctk
from main_logic import (
    run_trading_cycle,
)  # 다음 단계에서 main.py를 main_logic.py로 이름을 바꿀 예정입니다.

# 윈도우의 테마를 '다크(어두운)' 모드로 설정하고, 파란색 포인트를 줍니다.
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. 기본 창 설정
        self.title("AI 로컬 가상 매매 시스템 v1.0")
        self.geometry("900x700")

        # 2. 화면 상단 - 제목 및 상태 영역
        self.header_label = ctk.CTkLabel(
            self,
            text="🤖 로컬 AI 실시간 매매 대시보드",
            font=("Malgun Gothic", 24, "bold"),
        )
        self.header_label.pack(pady=20)

        # 3. 중간 영역 - (왼쪽: AI 리포트 / 오른쪽: 내 계좌 잔고)
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # [왼쪽 AI 리포트 창]
        self.ai_frame = ctk.CTkFrame(self.main_frame)
        self.ai_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.ai_title = ctk.CTkLabel(
            self.ai_frame, text="🧠 AI 분석 리포트", font=("Malgun Gothic", 16, "bold")
        )
        self.ai_title.pack(pady=5)

        self.ai_text = ctk.CTkTextbox(
            self.ai_frame, font=("Malgun Gothic", 13), width=400
        )
        self.ai_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.ai_text.insert("0.0", "AI 분석 대기 중...\n")

        # [오른쪽 실시간 정보 창]
        self.info_frame = ctk.CTkFrame(self.main_frame, width=300)
        self.info_frame.pack(side="right", fill="both", expand=False, padx=10, pady=10)

        self.price_label = ctk.CTkLabel(
            self.info_frame, text="현재가: --원", font=("Malgun Gothic", 20)
        )
        self.price_label.pack(pady=20)

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="가상 예수금: --원", font=("Malgun Gothic", 15)
        )
        self.balance_label.pack(pady=10)

        # 4. 하단 영역 - 로그 기록 창
        self.log_text = ctk.CTkTextbox(self, height=150, font=("Consolas", 11))
        self.log_text.pack(fill="x", padx=20, pady=10)
        self.log_text.insert("0.0", "[시스템] 프로그램이 준비되었습니다.\n")

        # 5. 하단 버튼 - 시작/중단
        self.start_button = ctk.CTkButton(
            self,
            text="자동 매매 시작",
            command=self.start_trading_thread,
            fg_color="green",
        )
        self.start_button.pack(pady=10)

    def write_log(self, message):
        """하단 로그창에 메시지를 추가하는 함수"""
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")  # 스크롤을 맨 아래로

    def update_ai_report(self, report):
        """AI 리포트 창 내용을 업데이트하는 함수"""
        self.ai_text.delete("0.0", "end")
        self.ai_text.insert("0.0", report)

    def start_trading_thread(self):
        """버튼을 누르면 '일손(스레드)'을 하나 더 만들어 매매 로직을 실행합니다."""
        self.start_button.configure(
            state="disabled", text="자동 매매 구동 중...", fg_color="gray"
        )
        self.write_log("자동 매매 엔진을 기동합니다...")

        # 별도의 실을 뽑아내어 메인 로직을 돌립니다. (안 그러면 창이 멈춰요!)
        t = threading.Thread(target=self.trading_loop, daemon=True)
        t.start()

    def trading_loop(self):
        from kis_api import get_access_token

        token = get_access_token()

        while True:
            # main_logic.py의 함수를 호출하여 결과를 받습니다.
            result = run_trading_cycle(token)

            if "error" in result:
                self.write_log(f"❌ 에러: {result['error']}")
            else:
                # 화면 글자들을 업데이트합니다.
                self.price_label.configure(text=f"현재가: {result['price']:,}원")
                self.balance_label.configure(
                    text=f"가상 예수금: {result['balance']:,}원"
                )
                self.update_ai_report(
                    f"[{result['decision']}]\n\n{result['reason']}\n\n[최신 뉴스]\n{result['news']}"
                )
                self.write_log(
                    f"분석 완료: {result['decision']} - {result['price']:,}원"
                )

            time.sleep(60)  # 1분 대기


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
