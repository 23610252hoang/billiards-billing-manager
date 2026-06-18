from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .database import REPORT_DIR, Database, money, receipt_text


class BilliardsApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ビリヤード会計管理アプリ")
        self.geometry("1080x680")
        self.minsize(960, 600)
        self.db = Database()

        self.table_count = tk.IntVar(value=int(self.db.setting("table_count")))
        self.rate_per_hour = tk.StringVar(value=self.db.setting("rate_per_hour"))
        self.status_text = tk.StringVar(value="準備完了")

        self._configure_style()
        self._build_layout()
        self.refresh_all()

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Metric.TLabel", font=("Segoe UI", 15, "bold"))
        style.configure("Treeview", rowheight=28)

    def _build_layout(self) -> None:
        header = ttk.Frame(self, padding=(16, 14, 16, 8))
        header.pack(fill="x")
        ttk.Label(header, text="ビリヤード会計管理アプリ", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.status_text).pack(side="right")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=8)

        self.dashboard_tab = ttk.Frame(self.tabs, padding=12)
        self.sessions_tab = ttk.Frame(self.tabs, padding=12)
        self.services_tab = ttk.Frame(self.tabs, padding=12)
        self.customers_tab = ttk.Frame(self.tabs, padding=12)
        self.reports_tab = ttk.Frame(self.tabs, padding=12)

        self.tabs.add(self.dashboard_tab, text="ダッシュボード")
        self.tabs.add(self.sessions_tab, text="利用管理")
        self.tabs.add(self.services_tab, text="サービス")
        self.tabs.add(self.customers_tab, text="顧客")
        self.tabs.add(self.reports_tab, text="売上レポート")

        self._build_dashboard()
        self._build_sessions()
        self._build_services()
        self._build_customers()
        self._build_reports()

    def _build_dashboard(self) -> None:
        metrics = ttk.Frame(self.dashboard_tab)
        metrics.pack(fill="x")
        self.active_metric = tk.StringVar()
        self.today_metric = tk.StringVar()
        self.revenue_metric = tk.StringVar()
        for label, var in [
            ("利用中の台数", self.active_metric),
            ("本日の会計数", self.today_metric),
            ("本日の売上", self.revenue_metric),
        ]:
            card = ttk.LabelFrame(metrics, text=label, padding=12)
            card.pack(side="left", fill="x", expand=True, padx=(0, 12))
            ttk.Label(card, textvariable=var, style="Metric.TLabel").pack(anchor="w")

        settings = ttk.LabelFrame(self.dashboard_tab, text="基本設定", padding=12)
        settings.pack(fill="x", pady=16)
        ttk.Label(settings, text="台数").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Spinbox(settings, from_=1, to=50, textvariable=self.table_count, width=8).grid(row=0, column=1)
        ttk.Label(settings, text="1時間あたり料金").grid(row=0, column=2, sticky="w", padx=(18, 8))
        ttk.Entry(settings, textvariable=self.rate_per_hour, width=14).grid(row=0, column=3)
        ttk.Button(settings, text="設定を保存", command=self.save_settings).grid(row=0, column=4, padx=16)

        active_box = ttk.LabelFrame(self.dashboard_tab, text="利用中セッション", padding=8)
        active_box.pack(fill="both", expand=True)
        self.active_tree = self._tree(
            active_box,
            ("id", "table", "start", "players", "customer", "prepaid"),
            ("ID", "台番号", "開始時刻", "人数", "顧客", "前払い"),
        )

    def _build_sessions(self) -> None:
        form = ttk.LabelFrame(self.sessions_tab, text="利用開始", padding=12)
        form.pack(fill="x")
        self.start_table = tk.IntVar(value=1)
        self.start_players = tk.IntVar(value=1)
        self.start_customer = tk.StringVar()
        self.start_prepaid = tk.StringVar(value="0")
        self.start_notes = tk.StringVar()
        labels = ["台番号", "人数", "顧客ID", "前払い", "メモ"]
        variables = [
            self.start_table,
            self.start_players,
            self.start_customer,
            self.start_prepaid,
            self.start_notes,
        ]
        for index, (label, var) in enumerate(zip(labels, variables)):
            ttk.Label(form, text=label).grid(row=0, column=index * 2, sticky="w", padx=(0, 6))
            ttk.Entry(form, textvariable=var, width=14).grid(row=0, column=index * 2 + 1, padx=(0, 12))
        ttk.Button(form, text="開始", command=self.start_session).grid(row=0, column=10)

        actions = ttk.LabelFrame(self.sessions_tab, text="会計・サービス追加", padding=12)
        actions.pack(fill="x", pady=12)
        self.selected_session = tk.StringVar()
        self.service_id = tk.StringVar()
        self.service_quantity = tk.IntVar(value=1)
        self.discount = tk.StringVar(value="0")
        self.payment_method = tk.StringVar(value="現金")
        for index, (label, var) in enumerate(
            [
                ("セッションID", self.selected_session),
                ("サービスID", self.service_id),
                ("数量", self.service_quantity),
                ("割引", self.discount),
                ("支払方法", self.payment_method),
            ]
        ):
            ttk.Label(actions, text=label).grid(row=0, column=index * 2, padx=(0, 6))
            ttk.Entry(actions, textvariable=var, width=12).grid(row=0, column=index * 2 + 1, padx=(0, 12))
        ttk.Button(actions, text="サービス追加", command=self.add_service_to_session).grid(row=0, column=10, padx=4)
        ttk.Button(actions, text="会計完了", command=self.finish_session).grid(row=0, column=11, padx=4)

        history = ttk.LabelFrame(self.sessions_tab, text="最近の利用履歴", padding=8)
        history.pack(fill="both", expand=True)
        self.sessions_tree = self._tree(
            history,
            ("id", "table", "start", "end", "fee", "customer", "payment"),
            ("ID", "台番号", "開始", "終了", "合計", "顧客", "支払方法"),
        )

    def _build_services(self) -> None:
        form = ttk.LabelFrame(self.services_tab, text="サービス追加", padding=12)
        form.pack(fill="x")
        self.new_service_name = tk.StringVar()
        self.new_service_price = tk.StringVar()
        ttk.Label(form, text="名称").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(form, textvariable=self.new_service_name, width=24).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(form, text="料金").grid(row=0, column=2, padx=(0, 6))
        ttk.Entry(form, textvariable=self.new_service_price, width=16).grid(row=0, column=3, padx=(0, 12))
        ttk.Button(form, text="追加", command=self.add_service).grid(row=0, column=4)
        table = ttk.LabelFrame(self.services_tab, text="サービス一覧", padding=8)
        table.pack(fill="both", expand=True, pady=12)
        self.services_tree = self._tree(table, ("id", "name", "price"), ("ID", "名称", "料金"))

    def _build_customers(self) -> None:
        form = ttk.LabelFrame(self.customers_tab, text="顧客追加", padding=12)
        form.pack(fill="x")
        self.customer_name = tk.StringVar()
        self.customer_phone = tk.StringVar()
        ttk.Label(form, text="氏名").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(form, textvariable=self.customer_name, width=24).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(form, text="電話番号").grid(row=0, column=2, padx=(0, 6))
        ttk.Entry(form, textvariable=self.customer_phone, width=18).grid(row=0, column=3, padx=(0, 12))
        ttk.Button(form, text="追加", command=self.add_customer).grid(row=0, column=4)
        table = ttk.LabelFrame(self.customers_tab, text="顧客一覧", padding=8)
        table.pack(fill="both", expand=True, pady=12)
        self.customers_tree = self._tree(
            table,
            ("id", "name", "phone", "points", "join_date"),
            ("ID", "氏名", "電話番号", "ポイント", "登録日"),
        )

    def _build_reports(self) -> None:
        controls = ttk.Frame(self.reports_tab)
        controls.pack(fill="x")
        self.report_date = tk.StringVar(value=datetime.now().date().isoformat())
        ttk.Label(controls, text="日付").pack(side="left")
        ttk.Entry(controls, textvariable=self.report_date, width=16).pack(side="left", padx=8)
        ttk.Button(controls, text="更新", command=self.refresh_reports).pack(side="left")
        self.report_text = tk.Text(self.reports_tab, height=18, wrap="word")
        self.report_text.pack(fill="both", expand=True, pady=12)

    def _tree(self, parent: ttk.Frame, columns: tuple[str, ...], headings: tuple[str, ...]) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        for column, heading in zip(columns, headings):
            tree.heading(column, text=heading)
            tree.column(column, width=120, anchor="w")
        tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        tree.bind("<<TreeviewSelect>>", self._select_session_from_tree)
        return tree

    def save_settings(self) -> None:
        self.db.update_setting("table_count", str(self.table_count.get()))
        self.db.update_setting("rate_per_hour", self.rate_per_hour.get())
        self.status_text.set("設定を保存しました")
        self.refresh_all()

    def start_session(self) -> None:
        try:
            customer_id = int(self.start_customer.get()) if self.start_customer.get().strip() else None
            session_id = self.db.start_session(
                table_id=self.start_table.get(),
                num_players=self.start_players.get(),
                customer_id=customer_id,
                prepaid=float(self.start_prepaid.get() or 0),
                notes=self.start_notes.get(),
            )
            self.status_text.set(f"セッション #{session_id} を開始しました")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("開始できません", str(exc))

    def add_service_to_session(self) -> None:
        try:
            self.db.add_service_to_session(
                int(self.selected_session.get()),
                int(self.service_id.get()),
                self.service_quantity.get(),
            )
            self.status_text.set("サービスを追加しました")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("サービスを追加できません", str(exc))

    def finish_session(self) -> None:
        try:
            bill = self.db.finish_session(
                int(self.selected_session.get()),
                discount=float(self.discount.get() or 0),
                payment_method=self.payment_method.get() or "現金",
            )
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            path = REPORT_DIR / f"receipt_{bill.session_id}_{datetime.now():%Y%m%d_%H%M%S}.txt"
            path.write_text(receipt_text(self.db.setting("club_name"), bill), encoding="utf-8")
            self.status_text.set(f"セッション #{bill.session_id} を会計完了し、領収書を保存しました")
            messagebox.showinfo("領収書を保存しました", str(path))
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("会計完了できません", str(exc))

    def add_service(self) -> None:
        try:
            self.db.add_service(self.new_service_name.get().strip(), float(self.new_service_price.get()))
            self.new_service_name.set("")
            self.new_service_price.set("")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("サービスを追加できません", str(exc))

    def add_customer(self) -> None:
        try:
            self.db.add_customer(self.customer_name.get().strip(), self.customer_phone.get().strip())
            self.customer_name.set("")
            self.customer_phone.set("")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("顧客を追加できません", str(exc))

    def refresh_all(self) -> None:
        self.refresh_active()
        self.refresh_sessions()
        self.refresh_services()
        self.refresh_customers()
        self.refresh_reports()

    def refresh_active(self) -> None:
        self._clear(self.active_tree)
        active = self.db.active_sessions()
        for row in active:
            self.active_tree.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["table_id"],
                    row["start_time"],
                    row["num_players"],
                    row["customer_name"] or "一般顧客",
                    money(float(row["prepaid"] or 0)),
                ),
            )
        today = self.db.daily_report()
        self.active_metric.set(str(len(active)))
        self.today_metric.set(str(int(today["session_count"])))
        self.revenue_metric.set(money(float(today["final_revenue"])))

    def refresh_sessions(self) -> None:
        self._clear(self.sessions_tree)
        for row in self.db.recent_sessions():
            self.sessions_tree.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["table_id"],
                    row["start_time"],
                    row["end_time"] or "利用中",
                    money(float(row["final_total"] or 0)),
                    row["customer_name"] or "一般顧客",
                    row["payment_method"] or "",
                ),
            )

    def refresh_services(self) -> None:
        self._clear(self.services_tree)
        for row in self.db.list_services():
            self.services_tree.insert("", "end", values=(row["id"], row["name"], money(float(row["price"]))))

    def refresh_customers(self) -> None:
        self._clear(self.customers_tree)
        for row in self.db.list_customers():
            self.customers_tree.insert(
                "",
                "end",
                values=(row["id"], row["name"], row["phone"] or "", row["points"], row["join_date"]),
            )

    def refresh_reports(self) -> None:
        report = self.db.daily_report(self.report_date.get())
        lines = [
            f"日次売上レポート: {self.report_date.get()}",
            "=" * 32,
            f"会計数:          {int(report['session_count'])}",
            f"台利用売上:      {money(float(report['table_revenue']))}",
            f"サービス売上:    {money(float(report['service_revenue']))}",
            f"割引合計:        {money(float(report['discounts']))}",
            f"最終売上:        {money(float(report['final_revenue']))}",
        ]
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", "\n".join(lines))

    def _select_session_from_tree(self, event: tk.Event) -> None:
        tree = event.widget
        selected = tree.selection()
        if selected:
            values = tree.item(selected[0], "values")
            if values:
                self.selected_session.set(str(values[0]))

    @staticmethod
    def _clear(tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)


def main() -> None:
    app = BilliardsApp()
    app.mainloop()
