# gui_app.py
import threading
import time
from datetime import datetime

import customtkinter as ctk

from db_manager import (
    create_tables,
    get_statistics,
    reset_db_completely,
    sqlite3,
    update_cash,
)
from kis_api import get_access_token
from main_logic import (
    get_db_holdings,
    predict_market_view,
    refresh_stock_pool_by_capital,
    run_trading_cycle,
)

ctk.set_appearance_mode("dark")


class TradingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 실전 지능형 단타 스테이션 v4.5")
        self.geometry("1100x850")
        create_tables()
        self.is_running = False

        self.header = ctk.CTkFrame(self, height=35, fg_color="#1a1a1a")
        self.header.pack(fill="x", padx=10, pady=2)
        self.clock_label = ctk.CTkLabel(
            self.header, text="--:--:--", font=("Consolas", 14), text_color="#00FF00"
        )
        self.clock_label.pack(side="left", padx=20)
        self.btn_reset = ctk.CTkButton(
            self.header,
            text="전체 리셋",
            width=80,
            height=20,
            fg_color="#660000",
            command=self.confirm_reset,
        )
        self.btn_reset.pack(side="right", padx=10)
        self.status_signal = ctk.CTkLabel(
            self.header,
            text="● ENGINE STOPPED",
            font=("Malgun Gothic", 12),
            text_color="red",
        )
        self.status_signal.pack(side="right", padx=20)

        self.predict_box = ctk.CTkTextbox(
            self, height=80, font=("Malgun Gothic", 12), text_color="#FFD700"
        )
        self.predict_box.pack(fill="x", padx=15, pady=5)
        self.predict_box.insert(
            "0.0", "🚀 자본금을 설정하고 가동하세요. 저가주 위주로 세팅됩니다."
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
        self.seed_input.insert(0, "100000")
        self.seed_input.pack()
        ctk.CTkButton(
            self.stat_panel,
            text="잔고설정",
            width=100,
            height=22,
            command=self.set_seed,
        ).pack(pady=2)

        ctk.CTkLabel(
            self.stat_panel, text="🎯 목표 수익", font=("Malgun Gothic", 11)
        ).pack()
        self.goal_input = ctk.CTkEntry(
            self.stat_panel, width=120, height=22, justify="center", fg_color="#1a3a1a"
        )
        self.goal_input.insert(0, "5000")
        self.goal_input.pack()

        self.price_label = ctk.CTkLabel(
            self.stat_panel, text="--원", font=("Consolas", 35, "bold")
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
            self.stat_panel, values=["잔고설정을 먼저 하세요"], width=200
        )
        self.ticker_menu.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.stat_panel, width=250)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.tab_view = ctk.CTkTabview(self, height=220)
        self.tab_view.pack(fill="x", padx=15, pady=5)
        self.tab_history = self.tab_view.add("거래내역")
        self.tab_holdings = self.tab_view.add("보유현황")
        self.history_box = ctk.CTkTextbox(
            self.tab_history, font=("Consolas", 10), fg_color="#000000"
        )
        self.history_box.pack(fill="both", expand=True)
        self.holdings_box = ctk.CTkTextbox(
            self.tab_holdings, font=("Consolas", 10), fg_color="#000000"
        )
        self.holdings_box.pack(fill="both", expand=True)

        self.log_box = ctk.CTkTextbox(
            self, height=60, font=("Consolas", 10), fg_color="#1a1a1a"
        )
        self.log_box.pack(fill="x", padx=15, pady=5)

        self.btn_control = ctk.CTkButton(
            self,
            text="▶ 엔진 가동 시작",
            command=self.toggle_engine,
            fg_color="green",
            height=45,
        )
        self.btn_control.pack(pady=5)

        self.update_clock()
        self.refresh_ui_from_db()

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

    def update_clock(self):
        self.clock_label.configure(
            text=f"현재시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.after(1000, self.update_clock)

    def set_seed(self):
        def work():
            try:
                amt = int(self.seed_input.get())
                update_cash(amt)
                new_list = refresh_stock_pool_by_capital()
                self.after(0, lambda: self.ticker_menu.configure(values=new_list))
                self.after(0, lambda: self.ticker_menu.set(new_list[0]))
                self.after(0, self.refresh_ui_from_db)
            except Exception as e:
                print(e)

        threading.Thread(target=work, daemon=True).start()

    def confirm_reset(self):
        reset_db_completely()
        self.refresh_ui_from_db()

    def refresh_ui_from_db(self):
        conn = sqlite3.connect("virtual_trade.db")
        h_data = conn.execute(
            "SELECT trade_date, ticker, type, price, quantity, profit FROM trade_history ORDER BY id DESC LIMIT 15"
        ).fetchall()
        self.history_box.delete("1.0", "end")
        for h in h_data:
            self.history_box.insert(
                "end",
                f"{h[0]} | {h[1]} | {h[2]} | {int(h[3]):,}원 | {h[4]}주 | {int(h[5]):,}원\n",
            )

        hold_data = get_db_holdings()
        self.holdings_box.delete("1.0", "end")
        for hold in hold_data:
            # 💡 [핵심 해결] h[2], h[3], h[4]를 강제로 int() 변환하여 ValueError 방지
            self.holdings_box.insert(
                "end",
                f"{hold[0]} | {hold[1]}주 | 평단:{int(hold[2]):,} | 현재:{int(hold[3]):,} | 손익:{int(hold[4]):,} ({hold[5]:.2f}%)\n",
            )

        t, w, m = get_statistics()
        self.today_profit_label.configure(text=f"오늘 수익: {int(t):,}원")
        cash = conn.execute("SELECT cash FROM account").fetchone()[0]
        conn.close()
        self.db_balance_label.configure(text=f"보유 예수금: {int(cash):,}원")

    def update_ui(self, data):
        if data["status"] == "GOAL_REACHED":
            self.is_running = False
            self.btn_control.configure(text="🏆 목표 달성 완료", state="disabled")
            return
        if data["status"] == "ACTIVE":
            self.price_label.configure(text=f"{int(data['price']):,}원")
            self.ai_report_text.configure(state="normal")
            self.ai_report_text.delete("1.0", "end")
            self.ai_report_text.insert(
                "1.0",
                f"🎯 분석: {data['ticker']} | 결정: {data['decision']}\n상태: {data['trade_status']}\n{'-'*30}\n💡 근거: {data['reason']}\n",
            )
            self.ai_report_text.configure(state="disabled")
            self.refresh_ui_from_db()

    def run_process(self):
        view = predict_market_view()
        self.after(
            0,
            lambda: (
                self.predict_box.delete("1.0", "end"),
                self.predict_box.insert("1.0", f"🚀 AI 리포트: {view}"),
            ),
        )
        token = get_access_token()
        while self.is_running:
            ticker = self.ticker_menu.get().split("(")[1].replace(")", "")
            try:
                goal = int(self.goal_input.get())
            except:
                goal = 5000
            res = run_trading_cycle(token, ticker, goal)
            if "error" not in res:
                self.after(0, lambda r=res: self.update_ui(r))
                if res.get("status") == "GOAL_REACHED":
                    break
            for i in range(61):
                if not self.is_running:
                    break
                self.after(0, lambda v=i: self.progress_bar.set(v / 60))
                time.sleep(1)


if __name__ == "__main__":
    app = TradingApp()
    app.mainloop()
