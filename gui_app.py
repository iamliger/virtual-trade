# gui_app.py (전체 교체)
import threading
import time

import customtkinter as ctk
from main_logic import run_trading_cycle

from kis_api import get_access_token

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 로컬 가상 매매 시스템 v1.1")
        self.geometry("950x750")

        # 상단 헤더
        self.header_label = ctk.CTkLabel(
            self,
            text="🤖 로컬 AI 실시간 매매 대시보드",
            font=("Malgun Gothic", 24, "bold"),
        )
        self.header_label.pack(pady=20)

        # 메인 프레임
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # [왼쪽 AI 리포트 창]
        self.ai_frame = ctk.CTkFrame(self.main_frame)
        self.ai_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.ai_title = ctk.CTkLabel(
            self.ai_frame,
            text="🧠 AI 분석 리포트 & 뉴스",
            font=("Malgun Gothic", 16, "bold"),
        )
        self.ai_title.pack(pady=5)

        self.ai_text = ctk.CTkTextbox(
            self.ai_frame, font=("Malgun Gothic", 14), width=450
        )
        self.ai_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.ai_text.insert("0.0", "대기 중...\n")

        # [오른쪽 정보 창]
        self.info_frame = ctk.CTkFrame(self.main_frame, width=300)
        self.info_frame.pack(side="right", fill="both", expand=False, padx=10, pady=10)

        self.price_label = ctk.CTkLabel(
            self.info_frame,
            text="현재가: 조회 중...",
            font=("Malgun Gothic", 22, "bold"),
        )
        self.price_label.pack(pady=30)

        self.balance_label = ctk.CTkLabel(
            self.info_frame, text="가상 예수금: 0원", font=("Malgun Gothic", 16)
        )
        self.balance_label.pack(pady=10)

        # 하단 로그 창
        self.log_text = ctk.CTkTextbox(self, height=150, font=("Consolas", 11))
        self.log_text.pack(fill="x", padx=20, pady=10)

        # 시작 버튼
        self.start_button = ctk.CTkButton(
            self,
            text="자동 매매 시작",
            command=self.start_trading_thread,
            fg_color="green",
            height=40,
        )
        self.start_button.pack(pady=20)

    def write_log(self, message):
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")

    # 💡 [핵심] Pylance 에러 해결: result라는 매개변수를 확실히 받도록 정의함
    def update_ui(self, result_data):
        """데이터를 받아 화면의 모든 요소를 갱신합니다."""
        # 1. AI 리포트 및 뉴스 업데이트
        self.ai_text.delete("1.0", "end")
        content = f"결정: [{result_data.get('decision', 'HOLD')}]\n"
        content += f"----------------------------------\n"
        content += (
            f"💡 AI 분석 근거:\n{result_data.get('reason', '분석 중입니다...')}\n\n"
        )
        content += f"----------------------------------\n"
        content += f"📰 최신 뉴스:\n{result_data.get('news', '뉴스가 없습니다.')}"
        self.ai_text.insert("1.0", content)

        # 2. 가격 및 잔고 업데이트
        self.price_label.configure(text=f"현재가: {result_data.get('price', 0):,}원")
        self.balance_label.configure(
            text=f"가상 예수금: {result_data.get('balance', 0):,}원"
        )

    def start_trading_thread(self):
        self.start_button.configure(state="disabled", text="자동 매매 구동 중...")
        t = threading.Thread(target=self.trading_loop, daemon=True)
        t.start()

    def trading_loop(self):
        token = get_access_token()
        while True:
            # main_logic에서 한 사이클을 돌리고 결과(result)를 받아옵니다.
            result = run_trading_cycle(token)

            # 받아온 결과가 에러가 아니라면 화면 업데이트 함수로 전달합니다.
            if "error" not in result:
                # 💡 [핵심] 윈도우 스레드 안전을 위해 호출
                self.after(0, lambda: self.update_ui(result))
                self.write_log(
                    f"분석 완료: {result['decision']} - {result['price']:,}원"
                )
            else:
                self.after(0, lambda: self.write_log(f"❌ 에러: {result['error']}"))

            time.sleep(60)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
