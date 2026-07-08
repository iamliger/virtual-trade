# gui_app.py
import logging
import sys
import threading
import time
from datetime import datetime

import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import config
from db_manager import (
    create_tables,
    get_statistics,
    reset_db_completely,
    sqlite3,
    update_cash,
)
from kis_api import get_access_token
from main_logic import (
    check_ollama_status,
    get_db_history,
    get_db_holdings_with_names,
    get_market_indices,
    predict_market_view,
    refresh_stock_pool_by_capital,
    run_trading_cycle,
)

ctk.set_appearance_mode("dark")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 실전 트레이딩 스테이션 v12.5 (Fixed News Engine)")
        self.geometry("1100x850")
        create_tables()
        self.is_running = False
        self.after_ids = []
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        if not check_ollama_status():
            from tkinter import messagebox

            messagebox.showerror(
                "엔진 에러",
                "Ollama 서버가 꺼져 있습니다.\n'ollama run llama3'를 먼저 실행해 주세요.",
            )
            self.destroy()
            sys.exit()

        self.header = ctk.CTkFrame(self, height=35, fg_color="#1a1a1a")
        self.header.pack(fill="x", padx=10, pady=2)
        self.clock_label = ctk.CTkLabel(
            self.header, text="--:--:--", font=("Consolas", 14), text_color="#00FF00"
        )
        self.clock_label.pack(side="left", padx=20)
        self.index_label = ctk.CTkLabel(
            self.header,
            text="지수 동기화 중...",
            font=("Malgun Gothic", 12),
            text_color="#FFB2D9",
        )
        self.index_label.pack(side="left", padx=50)
        ctk.CTkButton(
            self.header,
            text="DB 초기화",
            width=90,
            height=20,
            fg_color="#660000",
            command=self.confirm_reset,
        ).pack(side="right", padx=10)
        self.status_signal = ctk.CTkLabel(
            self.header,
            text="● ENGINE STOPPED",
            font=("Malgun Gothic", 12),
            text_color="red",
        )
        self.status_signal.pack(side="right", padx=20)

        self.predict_box = ctk.CTkTextbox(
            self, height=100, font=("Malgun Gothic", 12), text_color="#FFD700"
        )
        self.predict_box.pack(fill="x", padx=15, pady=5)
        self.predict_box.insert(
            "0.0", "🚀 고성능 뉴스 크롤러 엔진(v12.5) 활성화 완료\n"
        )

        self.mid_frame = ctk.CTkFrame(self)
        self.mid_frame.pack(fill="both", expand=True, padx=15, pady=5)
        self.ai_report_text = ctk.CTkTextbox(self.mid_frame, font=("Malgun Gothic", 14))
        self.ai_report_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.stat_panel = ctk.CTkFrame(self.mid_frame, width=320, fg_color="#212121")
        self.stat_panel.pack(side="right", fill="both", expand=False, padx=5, pady=5)

        ctk.CTkLabel(
            self.stat_panel, text="💰 시드머니", font=("Malgun Gothic", 11)
        ).pack()
        self.seed_input = ctk.CTkEntry(
            self.stat_panel, width=120, height=22, justify="center"
        )
        self.seed_input.insert(0, str(config.DEFAULT_SEED_MONEY))
        self.seed_input.pack()
        ctk.CTkButton(
            self.stat_panel,
            text="잔고/종목 갱신",
            width=100,
            height=22,
            command=self.set_seed,
        ).pack(pady=2)

        ctk.CTkLabel(
            self.stat_panel, text="🎯 목표 수익(오늘)", font=("Malgun Gothic", 11)
        ).pack()
        self.goal_input = ctk.CTkEntry(
            self.stat_panel, width=120, height=22, justify="center", fg_color="#1a3a1a"
        )
        self.goal_input.insert(0, str(config.DEFAULT_GOAL_PROFIT))
        self.goal_input.pack()

        self.price_label = ctk.CTkLabel(
            self.stat_panel,
            text="--원",
            font=("Consolas", 40, "bold"),
            text_color="#FFFFFF",
        )
        self.price_label.pack(pady=10)
        self.today_profit_label = ctk.CTkLabel(
            self.stat_panel,
            text="오늘 수익: 0원",
            font=("Malgun Gothic", 18, "bold"),
            text_color="#00FF00",
        )
        self.today_profit_label.pack()
        self.db_balance_label = ctk.CTkLabel(
            self.stat_panel, text="보유 예수금: --원", font=("Malgun Gothic", 13)
        )
        self.db_balance_label.pack(pady=5)
        self.ticker_menu = ctk.CTkOptionMenu(
            self.stat_panel, values=["먼저 갱신을 누르세요"], width=220
        )
        self.ticker_menu.pack(pady=5)
        self.progress_bar = ctk.CTkProgressBar(self.stat_panel, width=250)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.fig, self.ax = plt.subplots(figsize=(4, 2), dpi=80)
        self.fig.set_facecolor("#212121")
        self.ax.set_facecolor("#000000")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.stat_panel)
        self.canvas.get_tk_widget().pack(pady=5)

        self.tab_view = ctk.CTkTabview(self, height=250)
        self.tab_view.pack(fill="x", padx=15, pady=5)
        self.history_box = ctk.CTkTextbox(
            self.tab_view.add("거래상세 히스토리"),
            font=("Consolas", 10),
            fg_color="#000000",
        )
        self.history_box.pack(fill="both", expand=True)
        self.holdings_box = ctk.CTkTextbox(
            self.tab_view.add("실시간 보유현황"),
            font=("Consolas", 10),
            fg_color="#000000",
        )
        self.holdings_box.pack(fill="both", expand=True)

        self.btn_control = ctk.CTkButton(
            self,
            text="▶ 엔진 가동 시작",
            command=self.toggle_engine,
            fg_color="green",
            height=40,
        )
        self.btn_control.pack(pady=5)

        self.update_clock()
        self.refresh_ui_from_db()

    def on_closing(self):
        self.is_running = False
        for aid in self.after_ids:
            try:
                self.after_cancel(aid)
            except:
                pass
        plt.close(self.fig)
        self.quit()
        self.destroy()

    def update_clock(self):
        if not self.winfo_exists():
            return
        now = datetime.now().strftime("%H:%M:%S")
        self.clock_label.configure(text=f"현재시간: {now}")
        if int(now.split(":")[-1]) % 15 == 0:
            threading.Thread(target=self.safe_index_update, daemon=True).start()
        aid = self.after(1000, self.update_clock)
        self.after_ids.append(aid)

    def safe_index_update(self):
        idx = get_market_indices()
        if self.winfo_exists():
            self.after(0, lambda: self.index_label.configure(text=idx))

    def add_predict_log(self, text):
        if self.winfo_exists():
            self.predict_box.insert(
                "end", f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n"
            )
            self.predict_box.see("end")

    def toggle_engine(self):
        if not self.is_running:
            self.is_running = True
            self.btn_control.configure(text="■ 엔진 일시 정지", fg_color="#990000")
            self.status_signal.configure(text="● ENGINE RUNNING", text_color="#00FF00")
            threading.Thread(target=self.run_process, daemon=True).start()
        else:
            self.is_running = False
            self.btn_control.configure(text="▶ 엔진 가동 재개", fg_color="green")
            self.status_signal.configure(text="● ENGINE STOPPED", text_color="red")

    def set_seed(self):
        def work():
            try:
                amt = int(self.seed_input.get())
                update_cash(amt)
                new_list = refresh_stock_pool_by_capital()
                if self.winfo_exists():
                    self.after(
                        0,
                        lambda: (
                            self.ticker_menu.configure(values=new_list),
                            self.ticker_menu.set(new_list[0]),
                            self.refresh_ui_from_db(),
                            self.add_predict_log(f"💰 {amt:,}원 맞춤형 종목 발굴 완료"),
                        ),
                    )
            except:
                pass

        threading.Thread(target=work, daemon=True).start()

    def confirm_reset(self):
        reset_db_completely()
        self.refresh_ui_from_db()
        self.add_predict_log("☢️ 전체 리셋 완료")

    def refresh_ui_from_db(self):
        if not self.winfo_exists():
            return
        h_data = get_db_history()
        self.history_box.delete("1.0", "end")
        header = f"{'거래시간':<18} | {'종목명':<12} | {'구분':<4} | {'가격':>10} | {'수량':>4} | {'실현손익':>10}\n"
        self.history_box.insert("end", header + "-" * 80 + "\n")
        for h in h_data:
            name = h[1] if h[1] else "알수없음"
            self.history_box.insert(
                "end",
                f"{h[0]:<18} | {name:<12} | {h[2]:<4} | {int(h[3]):>10,} | {h[4]:>4} | {int(h[5]):>10,}\n",
            )

        hold_data = get_db_holdings_with_names()
        self.holdings_box.delete("1.0", "end")
        p_header = f"{'종목명':<12} | {'코드':<10} | {'수량':>4} | {'평단가':>10} | {'현재가':>10} | {'평가손익':>10} | {'수익률':>7}\n"
        self.holdings_box.insert("end", p_header + "-" * 85 + "\n")
        for hold in hold_data:
            self.holdings_box.insert(
                "end",
                f"{hold[0]:<12} | {hold[1]:<10} | {int(hold[2]):>4} | {int(hold[3]):>10,} | {int(hold[4]):>10,} | {int(hold[5]):>10,} | {hold[6]:>7.2f}%\n",
            )

        t, _, _ = get_statistics()
        self.today_profit_label.configure(text=f"오늘 수익: {int(t):,}원")
        conn = sqlite3.connect("virtual_trade.db")
        cash = conn.execute("SELECT cash FROM account").fetchone()[0]
        conn.close()
        self.db_balance_label.configure(text=f"보유 예수금: {int(cash):,}원")

    def draw_chart(self, prices):
        if self.winfo_exists():
            self.ax.clear()
            self.ax.plot(prices, color="#00FF00", linewidth=2)
            self.ax.axis("off")
            self.canvas.draw()

    def update_ui(self, data):
        if not self.winfo_exists():
            return
        if data["status"] == "GOAL_REACHED":
            self.is_running = False
            self.add_predict_log(
                f"🏆 금일 목표 수익 달성! ({int(data['today_profit']):,}원) 안전 종료."
            )
            return
        if data["status"] == "ACTIVE":
            self.price_label.configure(text=f"{int(data['price']):,}원")
            self.ai_report_text.configure(state="normal")
            self.ai_report_text.delete("1.0", "end")
            self.ai_report_text.insert(
                "1.0",
                f"🎯 분석: {data['ticker']} | 결정: {data['decision']}\n상태: {data['trade_status']}\n{'-'*30}\n💡 근거: {data['reason']}\n\n{data['news']}",
            )
            self.ai_report_text.configure(state="disabled")
            self.refresh_ui_from_db()
            self.ai_report_text.see("end")
            if "chart" in data:
                self.draw_chart(data["chart"])
            if "성공" in data["trade_status"]:
                self.add_predict_log(f"📢 {data['ticker']} {data['trade_status']}")

    def run_process(self):
        view = predict_market_view()
        self.after(0, lambda: self.add_predict_log(f"🚀 AI 리포트: {view}"))
        token = get_access_token()
        while self.is_running:
            if not self.winfo_exists():
                break
            selection = self.ticker_menu.get()

            # 💡 [IndexError 방어] 종목 미선택 시 대기
            if "(" not in selection:
                self.after(
                    0, lambda: self.add_predict_log("⚠️ 분석할 종목을 먼저 선택하세요.")
                )
                time.sleep(5)
                continue

            ticker = selection.split("(")[1].replace(")", "")
            try:
                goal = int(self.goal_input.get())
            except:
                goal = config.DEFAULT_GOAL_PROFIT
            res = run_trading_cycle(token, ticker, goal)
            if "error" not in res:
                if self.winfo_exists():
                    self.after(0, lambda r=res: self.update_ui(r))
                if res.get("status") == "GOAL_REACHED":
                    break
            for i in range(61):
                if not self.is_running or not self.winfo_exists():
                    break
                aid = self.after(
                    0,
                    lambda v=i: (
                        self.progress_bar.set(v / 60) if self.winfo_exists() else None
                    ),
                )
                self.after_ids.append(aid)
                time.sleep(1)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
