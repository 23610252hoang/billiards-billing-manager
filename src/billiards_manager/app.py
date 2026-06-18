from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .database import REPORT_DIR, Database, money, receipt_text


class BilliardsApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Billiards Billing Manager")
        self.geometry("1080x680")
        self.minsize(960, 600)
        self.db = Database()

        self.table_count = tk.IntVar(value=int(self.db.setting("table_count")))
        self.rate_per_hour = tk.StringVar(value=self.db.setting("rate_per_hour"))
        self.status_text = tk.StringVar(value="Ready")

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
        ttk.Label(header, text="Billiards Billing Manager", style="Title.TLabel").pack(side="left")
        ttk.Label(header, textvariable=self.status_text).pack(side="right")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=8)

        self.dashboard_tab = ttk.Frame(self.tabs, padding=12)
        self.sessions_tab = ttk.Frame(self.tabs, padding=12)
        self.services_tab = ttk.Frame(self.tabs, padding=12)
        self.customers_tab = ttk.Frame(self.tabs, padding=12)
        self.reports_tab = ttk.Frame(self.tabs, padding=12)

        self.tabs.add(self.dashboard_tab, text="Dashboard")
        self.tabs.add(self.sessions_tab, text="Sessions")
        self.tabs.add(self.services_tab, text="Services")
        self.tabs.add(self.customers_tab, text="Customers")
        self.tabs.add(self.reports_tab, text="Reports")

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
            ("Active tables", self.active_metric),
            ("Sessions today", self.today_metric),
            ("Revenue today", self.revenue_metric),
        ]:
            card = ttk.LabelFrame(metrics, text=label, padding=12)
            card.pack(side="left", fill="x", expand=True, padx=(0, 12))
            ttk.Label(card, textvariable=var, style="Metric.TLabel").pack(anchor="w")

        settings = ttk.LabelFrame(self.dashboard_tab, text="Settings", padding=12)
        settings.pack(fill="x", pady=16)
        ttk.Label(settings, text="Table count").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Spinbox(settings, from_=1, to=50, textvariable=self.table_count, width=8).grid(row=0, column=1)
        ttk.Label(settings, text="Rate per hour").grid(row=0, column=2, sticky="w", padx=(18, 8))
        ttk.Entry(settings, textvariable=self.rate_per_hour, width=14).grid(row=0, column=3)
        ttk.Button(settings, text="Save settings", command=self.save_settings).grid(row=0, column=4, padx=16)

        active_box = ttk.LabelFrame(self.dashboard_tab, text="Active Sessions", padding=8)
        active_box.pack(fill="both", expand=True)
        self.active_tree = self._tree(
            active_box,
            ("id", "table", "start", "players", "customer", "prepaid"),
            ("ID", "Table", "Start", "Players", "Customer", "Prepaid"),
        )

    def _build_sessions(self) -> None:
        form = ttk.LabelFrame(self.sessions_tab, text="Start Session", padding=12)
        form.pack(fill="x")
        self.start_table = tk.IntVar(value=1)
        self.start_players = tk.IntVar(value=1)
        self.start_customer = tk.StringVar()
        self.start_prepaid = tk.StringVar(value="0")
        self.start_notes = tk.StringVar()
        labels = ["Table", "Players", "Customer ID", "Prepaid", "Notes"]
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
        ttk.Button(form, text="Start", command=self.start_session).grid(row=0, column=10)

        actions = ttk.LabelFrame(self.sessions_tab, text="Close Session / Add Service", padding=12)
        actions.pack(fill="x", pady=12)
        self.selected_session = tk.StringVar()
        self.service_id = tk.StringVar()
        self.service_quantity = tk.IntVar(value=1)
        self.discount = tk.StringVar(value="0")
        self.payment_method = tk.StringVar(value="cash")
        for index, (label, var) in enumerate(
            [
                ("Session ID", self.selected_session),
                ("Service ID", self.service_id),
                ("Qty", self.service_quantity),
                ("Discount", self.discount),
                ("Payment", self.payment_method),
            ]
        ):
            ttk.Label(actions, text=label).grid(row=0, column=index * 2, padx=(0, 6))
            ttk.Entry(actions, textvariable=var, width=12).grid(row=0, column=index * 2 + 1, padx=(0, 12))
        ttk.Button(actions, text="Add service", command=self.add_service_to_session).grid(row=0, column=10, padx=4)
        ttk.Button(actions, text="Finish", command=self.finish_session).grid(row=0, column=11, padx=4)

        history = ttk.LabelFrame(self.sessions_tab, text="Recent Sessions", padding=8)
        history.pack(fill="both", expand=True)
        self.sessions_tree = self._tree(
            history,
            ("id", "table", "start", "end", "fee", "customer", "payment"),
            ("ID", "Table", "Start", "End", "Total", "Customer", "Payment"),
        )

    def _build_services(self) -> None:
        form = ttk.LabelFrame(self.services_tab, text="Add Service", padding=12)
        form.pack(fill="x")
        self.new_service_name = tk.StringVar()
        self.new_service_price = tk.StringVar()
        ttk.Label(form, text="Name").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(form, textvariable=self.new_service_name, width=24).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(form, text="Price").grid(row=0, column=2, padx=(0, 6))
        ttk.Entry(form, textvariable=self.new_service_price, width=16).grid(row=0, column=3, padx=(0, 12))
        ttk.Button(form, text="Add", command=self.add_service).grid(row=0, column=4)
        table = ttk.LabelFrame(self.services_tab, text="Services", padding=8)
        table.pack(fill="both", expand=True, pady=12)
        self.services_tree = self._tree(table, ("id", "name", "price"), ("ID", "Name", "Price"))

    def _build_customers(self) -> None:
        form = ttk.LabelFrame(self.customers_tab, text="Add Customer", padding=12)
        form.pack(fill="x")
        self.customer_name = tk.StringVar()
        self.customer_phone = tk.StringVar()
        ttk.Label(form, text="Name").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(form, textvariable=self.customer_name, width=24).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(form, text="Phone").grid(row=0, column=2, padx=(0, 6))
        ttk.Entry(form, textvariable=self.customer_phone, width=18).grid(row=0, column=3, padx=(0, 12))
        ttk.Button(form, text="Add", command=self.add_customer).grid(row=0, column=4)
        table = ttk.LabelFrame(self.customers_tab, text="Customers", padding=8)
        table.pack(fill="both", expand=True, pady=12)
        self.customers_tree = self._tree(
            table,
            ("id", "name", "phone", "points", "join_date"),
            ("ID", "Name", "Phone", "Points", "Join date"),
        )

    def _build_reports(self) -> None:
        controls = ttk.Frame(self.reports_tab)
        controls.pack(fill="x")
        self.report_date = tk.StringVar(value=datetime.now().date().isoformat())
        ttk.Label(controls, text="Date").pack(side="left")
        ttk.Entry(controls, textvariable=self.report_date, width=16).pack(side="left", padx=8)
        ttk.Button(controls, text="Refresh", command=self.refresh_reports).pack(side="left")
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
        self.status_text.set("Settings saved")
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
            self.status_text.set(f"Started session #{session_id}")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("Cannot start session", str(exc))

    def add_service_to_session(self) -> None:
        try:
            self.db.add_service_to_session(
                int(self.selected_session.get()),
                int(self.service_id.get()),
                self.service_quantity.get(),
            )
            self.status_text.set("Service added")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("Cannot add service", str(exc))

    def finish_session(self) -> None:
        try:
            bill = self.db.finish_session(
                int(self.selected_session.get()),
                discount=float(self.discount.get() or 0),
                payment_method=self.payment_method.get() or "cash",
            )
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            path = REPORT_DIR / f"receipt_{bill.session_id}_{datetime.now():%Y%m%d_%H%M%S}.txt"
            path.write_text(receipt_text(self.db.setting("club_name"), bill), encoding="utf-8")
            self.status_text.set(f"Finished session #{bill.session_id}; receipt saved")
            messagebox.showinfo("Receipt saved", str(path))
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("Cannot finish session", str(exc))

    def add_service(self) -> None:
        try:
            self.db.add_service(self.new_service_name.get().strip(), float(self.new_service_price.get()))
            self.new_service_name.set("")
            self.new_service_price.set("")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("Cannot add service", str(exc))

    def add_customer(self) -> None:
        try:
            self.db.add_customer(self.customer_name.get().strip(), self.customer_phone.get().strip())
            self.customer_name.set("")
            self.customer_phone.set("")
            self.refresh_all()
        except Exception as exc:
            messagebox.showerror("Cannot add customer", str(exc))

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
                    row["customer_name"] or "Walk-in",
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
                    row["end_time"] or "active",
                    money(float(row["final_total"] or 0)),
                    row["customer_name"] or "Walk-in",
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
            f"Daily report: {self.report_date.get()}",
            "=" * 32,
            f"Sessions:        {int(report['session_count'])}",
            f"Table revenue:   {money(float(report['table_revenue']))}",
            f"Service revenue: {money(float(report['service_revenue']))}",
            f"Discounts:       {money(float(report['discounts']))}",
            f"Final revenue:   {money(float(report['final_revenue']))}",
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
