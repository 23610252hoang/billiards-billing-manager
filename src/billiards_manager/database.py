from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
REPORT_DIR = PROJECT_ROOT / "reports"
DB_PATH = DATA_DIR / "billiards_app.db"


@dataclass(frozen=True)
class Bill:
    session_id: int
    table_id: int
    started_at: str
    ended_at: str
    duration_seconds: float
    base_fee: float
    service_fee: float
    discount: float
    prepaid: float
    final_total: float
    payment_method: str
    customer_name: str | None
    services: list[dict[str, Any]]


def money(value: float) -> str:
    return f"{value:,.0f} VND"


class Database:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.initialize()

    def close(self) -> None:
        self.conn.close()

    def initialize(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE,
                points INTEGER DEFAULT 0,
                join_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 0,
                supplier TEXT
            );

            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                res_time TEXT NOT NULL,
                table_id INTEGER,
                notes TEXT,
                status TEXT DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                item TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_seconds REAL,
                rate_per_hour REAL NOT NULL,
                num_players INTEGER DEFAULT 1,
                base_fee REAL,
                services TEXT DEFAULT '[]',
                service_fee REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                prepaid REAL DEFAULT 0,
                final_total REAL,
                payment_method TEXT,
                customer_id INTEGER,
                customer_name TEXT,
                notes TEXT
            );
            """
        )
        defaults = {
            "club_name": "ビリヤードクラブ",
            "table_count": "8",
            "rate_per_hour": "60000",
            "point_rate": "10000",
        }
        for key, value in defaults.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                (key, value),
            )
        if not self.list_services():
            self.add_service("ミネラルウォーター", 10000)
            self.add_service("ソフトドリンク", 15000)
            self.add_service("キュー貸出", 20000)
        self.conn.commit()

    def setting(self, key: str) -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return str(row["value"])

    def update_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        self.conn.commit()

    def active_sessions(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM sessions WHERE end_time IS NULL ORDER BY table_id"
        ).fetchall()

    def recent_sessions(self, limit: int = 20) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM sessions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def start_session(
        self,
        table_id: int,
        num_players: int,
        customer_id: int | None = None,
        prepaid: float = 0,
        notes: str = "",
    ) -> int:
        existing = self.conn.execute(
            "SELECT id FROM sessions WHERE table_id = ? AND end_time IS NULL",
            (table_id,),
        ).fetchone()
        if existing:
            raise ValueError(f"台番号 {table_id} はすでに利用中です。")

        customer_name = None
        if customer_id:
            customer = self.get_customer(customer_id)
            customer_name = customer["name"] if customer else None

        cur = self.conn.execute(
            """
            INSERT INTO sessions(
                table_id, start_time, rate_per_hour, num_players,
                customer_id, customer_name, prepaid, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                table_id,
                datetime.now().isoformat(timespec="seconds"),
                float(self.setting("rate_per_hour")),
                num_players,
                customer_id,
                customer_name,
                prepaid,
                notes,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_service_to_session(self, session_id: int, service_id: int, quantity: int) -> None:
        session = self.get_session(session_id)
        service = self.conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()
        if session is None or service is None:
            raise ValueError("セッションまたはサービスが正しくありません。")
        services = json.loads(session["services"] or "[]")
        services.append(
            {
                "name": service["name"],
                "unit_price": float(service["price"]),
                "quantity": quantity,
                "total": float(service["price"]) * quantity,
            }
        )
        service_fee = sum(item["total"] for item in services)
        self.conn.execute(
            "UPDATE sessions SET services = ?, service_fee = ? WHERE id = ?",
            (json.dumps(services), service_fee, session_id),
        )
        self.conn.commit()

    def finish_session(
        self,
        session_id: int,
        discount: float = 0,
        payment_method: str = "現金",
    ) -> Bill:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("セッションが見つかりません。")
        if session["end_time"] is not None:
            raise ValueError("このセッションはすでに会計済みです。")

        end_time = datetime.now()
        start_time = datetime.fromisoformat(session["start_time"])
        duration_seconds = max((end_time - start_time).total_seconds(), 60)
        base_fee = duration_seconds / 3600 * float(session["rate_per_hour"])
        service_fee = float(session["service_fee"] or 0)
        prepaid = float(session["prepaid"] or 0)
        final_total = max(base_fee + service_fee - discount - prepaid, 0)

        self.conn.execute(
            """
            UPDATE sessions
            SET end_time = ?, duration_seconds = ?, base_fee = ?, discount = ?,
                final_total = ?, payment_method = ?
            WHERE id = ?
            """,
            (
                end_time.isoformat(timespec="seconds"),
                duration_seconds,
                base_fee,
                discount,
                final_total,
                payment_method,
                session_id,
            ),
        )
        if session["customer_id"]:
            earned = int(final_total // float(self.setting("point_rate")))
            self.conn.execute(
                "UPDATE customers SET points = points + ? WHERE id = ?",
                (earned, session["customer_id"]),
            )
        self.conn.commit()
        return self.bill_for_session(session_id)

    def bill_for_session(self, session_id: int) -> Bill:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError("セッションが見つかりません。")
        return Bill(
            session_id=int(session["id"]),
            table_id=int(session["table_id"]),
            started_at=str(session["start_time"]),
            ended_at=str(session["end_time"] or ""),
            duration_seconds=float(session["duration_seconds"] or 0),
            base_fee=float(session["base_fee"] or 0),
            service_fee=float(session["service_fee"] or 0),
            discount=float(session["discount"] or 0),
            prepaid=float(session["prepaid"] or 0),
            final_total=float(session["final_total"] or 0),
            payment_method=str(session["payment_method"] or ""),
            customer_name=session["customer_name"],
            services=json.loads(session["services"] or "[]"),
        )

    def get_session(self, session_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()

    def add_customer(self, name: str, phone: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO customers(name, phone, join_date) VALUES (?, ?, ?)",
            (name, phone or None, datetime.now().date().isoformat()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_customers(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM customers ORDER BY name").fetchall()

    def get_customer(self, customer_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()

    def add_service(self, name: str, price: float) -> int:
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO services(name, price) VALUES (?, ?)",
            (name, price),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_services(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM services ORDER BY name").fetchall()

    def seed_demo_data(self) -> None:
        """Populate a fresh temporary database with fictional portfolio data."""
        existing = self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        if existing:
            return

        customer_ids = [
            self.add_customer("デモ顧客A"),
            self.add_customer("デモ顧客B"),
            self.add_customer("デモ顧客C"),
        ]
        services = {row["name"]: row for row in self.list_services()}
        now = datetime.now().replace(microsecond=0)

        def service_item(name: str, quantity: int) -> dict[str, Any]:
            price = float(services[name]["price"])
            return {
                "name": name,
                "unit_price": price,
                "quantity": quantity,
                "total": price * quantity,
            }

        active_rows = [
            (2, now - timedelta(hours=2), 2, customer_ids[0], "デモ顧客A", [service_item("ミネラルウォーター", 1)]),
            (4, now - timedelta(hours=1, minutes=30), 3, customer_ids[1], "デモ顧客B", [service_item("ソフトドリンク", 1), service_item("キュー貸出", 1)]),
        ]
        for table_id, started_at, players, customer_id, customer_name, items in active_rows:
            self.conn.execute(
                """
                INSERT INTO sessions(
                    table_id, start_time, rate_per_hour, num_players,
                    services, service_fee, customer_id, customer_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    table_id,
                    started_at.isoformat(timespec="seconds"),
                    float(self.setting("rate_per_hour")),
                    players,
                    json.dumps(items, ensure_ascii=False),
                    sum(item["total"] for item in items),
                    customer_id,
                    customer_name,
                    "架空のデモデータ",
                ),
            )

        completed_rows = [
            (1, now - timedelta(hours=2), now, customer_ids[2], "デモ顧客C", [service_item("ソフトドリンク", 1)], 0, "現金"),
            (3, now - timedelta(hours=1, minutes=30), now, None, None, [service_item("キュー貸出", 1)], 10000, "カード"),
            (5, now - timedelta(days=1, hours=3), now - timedelta(days=1, hours=1), None, None, [], 0, "QR決済"),
        ]
        rate = float(self.setting("rate_per_hour"))
        for table_id, started_at, ended_at, customer_id, customer_name, items, discount, payment in completed_rows:
            duration = (ended_at - started_at).total_seconds()
            base_fee = duration / 3600 * rate
            service_fee = sum(item["total"] for item in items)
            final_total = max(base_fee + service_fee - discount, 0)
            self.conn.execute(
                """
                INSERT INTO sessions(
                    table_id, start_time, end_time, duration_seconds,
                    rate_per_hour, num_players, base_fee, services,
                    service_fee, discount, final_total, payment_method,
                    customer_id, customer_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    table_id,
                    started_at.isoformat(timespec="seconds"),
                    ended_at.isoformat(timespec="seconds"),
                    duration,
                    rate,
                    2,
                    base_fee,
                    json.dumps(items, ensure_ascii=False),
                    service_fee,
                    discount,
                    final_total,
                    payment,
                    customer_id,
                    customer_name,
                    "架空のデモデータ",
                ),
            )
        self.conn.commit()

    def daily_report(self, date_prefix: str | None = None) -> dict[str, float]:
        date_prefix = date_prefix or datetime.now().date().isoformat()
        row = self.conn.execute(
            """
            SELECT
                COUNT(*) AS session_count,
                COALESCE(SUM(base_fee), 0) AS table_revenue,
                COALESCE(SUM(service_fee), 0) AS service_revenue,
                COALESCE(SUM(discount), 0) AS discounts,
                COALESCE(SUM(final_total), 0) AS final_revenue
            FROM sessions
            WHERE end_time LIKE ?
            """,
            (f"{date_prefix}%",),
        ).fetchone()
        return dict(row)


def receipt_text(club_name: str, bill: Bill) -> str:
    minutes = int(bill.duration_seconds // 60)
    lines = [
        club_name,
        "=" * 34,
        f"領収書 #{bill.session_id} - 台番号 {bill.table_id}",
        f"顧客: {bill.customer_name or '一般顧客'}",
        f"開始: {bill.started_at}",
        f"終了: {bill.ended_at}",
        f"時間: {minutes // 60}時間 {minutes % 60}分",
        "-" * 34,
        f"台利用料金:   {money(bill.base_fee)}",
    ]
    if bill.services:
        lines.append("サービス:")
        for item in bill.services:
            lines.append(
                f"  {item['name']} x{item['quantity']}: {money(float(item['total']))}"
            )
    else:
        lines.append("サービス: なし")
    lines.extend(
        [
            f"サービス料金: {money(bill.service_fee)}",
            f"割引:         {money(bill.discount)}",
            f"前払い:       {money(bill.prepaid)}",
            "=" * 34,
            f"合計:         {money(bill.final_total)}",
            f"支払方法:     {bill.payment_method}",
            "ご利用ありがとうございました。",
        ]
    )
    return "\n".join(lines)

