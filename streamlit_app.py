from __future__ import annotations

import sys
import tempfile
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from billiards_manager.database import Database, money, receipt_text


st.set_page_config(
    page_title="ビリヤード会計管理デモ",
    page_icon="🎱",
    layout="wide",
)


@st.cache_resource
def get_database(session_key: str) -> Database:
    db_path = Path(tempfile.gettempdir()) / f"billiards_portfolio_{session_key}.db"
    return Database(db_path)


def get_session_key() -> str:
    if "demo_session_key" not in st.session_state:
        st.session_state.demo_session_key = uuid.uuid4().hex
    return st.session_state.demo_session_key


def rows_to_frame(rows, columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame([{column: row[column] for column in columns} for row in rows])


def format_session_frame(rows) -> pd.DataFrame:
    data = []
    for row in rows:
        data.append(
            {
                "ID": row["id"],
                "台番号": row["table_id"],
                "開始時刻": row["start_time"],
                "終了時刻": row["end_time"] or "利用中",
                "人数": row["num_players"],
                "顧客": row["customer_name"] or "一般顧客",
                "合計": money(float(row["final_total"] or 0)),
                "支払方法": row["payment_method"] or "",
            }
        )
    return pd.DataFrame(data)


db = get_database(get_session_key())

st.title("ビリヤード店舗向け会計管理アプリ")
st.caption("Python・Streamlit・SQLiteで構築した採用選考向けWebデモ")
st.info(
    "このデモのデータは一時領域に保存されます。実店舗名、電話番号、顧客データは含まれていません。",
    icon="ℹ️",
)

active_sessions = db.active_sessions()
today = db.daily_report()

metric_1, metric_2, metric_3 = st.columns(3)
metric_1.metric("利用中の台数", len(active_sessions))
metric_2.metric("本日の会計数", int(today["session_count"]))
metric_3.metric("本日の売上", money(float(today["final_revenue"])))

dashboard_tab, session_tab, master_tab, report_tab = st.tabs(
    ["ダッシュボード", "利用・会計", "顧客・サービス", "売上レポート"]
)

with dashboard_tab:
    st.subheader("利用中セッション")
    if active_sessions:
        st.dataframe(format_session_frame(active_sessions), use_container_width=True, hide_index=True)
    else:
        st.info("現在利用中の台はありません。")

    st.subheader("最近の利用履歴")
    recent_sessions = db.recent_sessions(limit=10)
    if recent_sessions:
        st.dataframe(format_session_frame(recent_sessions), use_container_width=True, hide_index=True)
    else:
        st.info("利用履歴はまだありません。")

with session_tab:
    start_col, action_col = st.columns(2)

    with start_col:
        st.subheader("利用開始")
        customers = db.list_customers()
        customer_options = {"一般顧客": None}
        customer_options.update({f"#{row['id']} {row['name']}": row["id"] for row in customers})

        with st.form("start_session_form", clear_on_submit=True):
            table_id = st.number_input("台番号", min_value=1, max_value=50, value=1, step=1)
            num_players = st.number_input("利用人数", min_value=1, max_value=20, value=2, step=1)
            customer_label = st.selectbox("顧客", list(customer_options))
            prepaid = st.number_input("前払い金額（VND）", min_value=0, value=0, step=10000)
            notes = st.text_input("メモ")
            start_submitted = st.form_submit_button("利用を開始", type="primary")

        if start_submitted:
            try:
                session_id = db.start_session(
                    table_id=int(table_id),
                    num_players=int(num_players),
                    customer_id=customer_options[customer_label],
                    prepaid=float(prepaid),
                    notes=notes,
                )
                st.success(f"セッション #{session_id} を開始しました。")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    with action_col:
        st.subheader("サービス追加・会計")
        active_sessions = db.active_sessions()
        if not active_sessions:
            st.info("先に利用セッションを開始してください。")
        else:
            session_options = {
                f"#{row['id']} / 台{row['table_id']} / {row['customer_name'] or '一般顧客'}": row["id"]
                for row in active_sessions
            }
            selected_session_label = st.selectbox("対象セッション", list(session_options))
            selected_session_id = session_options[selected_session_label]

            services = db.list_services()
            service_options = {
                f"#{row['id']} {row['name']} ({money(float(row['price']))})": row["id"]
                for row in services
            }

            with st.form("add_service_form"):
                service_label = st.selectbox("追加サービス", list(service_options))
                quantity = st.number_input("数量", min_value=1, max_value=20, value=1, step=1)
                service_submitted = st.form_submit_button("サービスを追加")

            if service_submitted:
                try:
                    db.add_service_to_session(
                        selected_session_id,
                        service_options[service_label],
                        int(quantity),
                    )
                    st.success("サービスを追加しました。")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

            with st.form("finish_session_form"):
                discount = st.number_input("割引金額（VND）", min_value=0, value=0, step=5000)
                payment_method = st.selectbox("支払方法", ["現金", "カード", "QR決済"])
                finish_submitted = st.form_submit_button("会計を完了", type="primary")

            if finish_submitted:
                try:
                    bill = db.finish_session(
                        selected_session_id,
                        discount=float(discount),
                        payment_method=payment_method,
                    )
                    st.session_state.last_receipt = receipt_text(db.setting("club_name"), bill)
                    st.success(f"会計が完了しました。合計: {money(bill.final_total)}")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    if "last_receipt" in st.session_state:
        st.divider()
        st.subheader("最新の領収書")
        st.code(st.session_state.last_receipt, language="text")
        st.download_button(
            "領収書をダウンロード",
            data=st.session_state.last_receipt.encode("utf-8"),
            file_name="billiards_receipt.txt",
            mime="text/plain",
        )

with master_tab:
    customer_col, service_col = st.columns(2)

    with customer_col:
        st.subheader("顧客登録")
        with st.form("customer_form", clear_on_submit=True):
            customer_name = st.text_input("氏名")
            customer_phone = st.text_input("電話番号（デモ用・任意）")
            customer_submitted = st.form_submit_button("顧客を追加")
        if customer_submitted:
            try:
                if not customer_name.strip():
                    raise ValueError("氏名を入力してください。")
                db.add_customer(customer_name.strip(), customer_phone.strip())
                st.success("顧客を追加しました。")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        customers = db.list_customers()
        if customers:
            customer_frame = rows_to_frame(customers, ["id", "name", "phone", "points", "join_date"])
            customer_frame.columns = ["ID", "氏名", "電話番号", "ポイント", "登録日"]
            st.dataframe(customer_frame, use_container_width=True, hide_index=True)

    with service_col:
        st.subheader("サービス登録")
        with st.form("service_form", clear_on_submit=True):
            service_name = st.text_input("サービス名")
            service_price = st.number_input("料金（VND）", min_value=0, value=10000, step=5000)
            service_master_submitted = st.form_submit_button("サービスを追加")
        if service_master_submitted:
            try:
                if not service_name.strip():
                    raise ValueError("サービス名を入力してください。")
                db.add_service(service_name.strip(), float(service_price))
                st.success("サービスを追加しました。")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        services = db.list_services()
        service_frame = rows_to_frame(services, ["id", "name", "price"])
        service_frame.columns = ["ID", "サービス名", "料金"]
        service_frame["料金"] = service_frame["料金"].map(money)
        st.dataframe(service_frame, use_container_width=True, hide_index=True)

with report_tab:
    st.subheader("本日の売上")
    report = db.daily_report()
    report_frame = pd.DataFrame(
        [
            {"項目": "会計数", "値": int(report["session_count"])},
            {"項目": "台利用売上", "値": money(float(report["table_revenue"]))},
            {"項目": "サービス売上", "値": money(float(report["service_revenue"]))},
            {"項目": "割引合計", "値": money(float(report["discounts"]))},
            {"項目": "最終売上", "値": money(float(report["final_revenue"]))},
        ]
    )
    st.dataframe(report_frame, use_container_width=True, hide_index=True)

    completed = [row for row in db.recent_sessions(limit=50) if row["end_time"]]
    if completed:
        chart_frame = pd.DataFrame(
            {
                "セッション": [f"#{row['id']} 台{row['table_id']}" for row in completed],
                "売上": [float(row["final_total"] or 0) for row in completed],
            }
        ).set_index("セッション")
        st.bar_chart(chart_frame)
    else:
        st.info("会計完了後に売上グラフが表示されます。")

st.divider()
st.caption("Portfolio demo by Nguyen Kim Hoang | 実データは使用していません")
