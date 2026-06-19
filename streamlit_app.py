Exit code: 0
Wall time: 1.7 seconds
Output:
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
    page_title="繝薙Μ繝､繝ｼ繝我ｼ夊ｨ育ｮ｡逅・ョ繝｢",
    page_icon="竺",
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
                "蜿ｰ逡ｪ蜿ｷ": row["table_id"],
                "髢句ｧ区凾蛻ｻ": row["start_time"],
                "邨ゆｺ・凾蛻ｻ": row["end_time"] or "蛻ｩ逕ｨ荳ｭ",
                "莠ｺ謨ｰ": row["num_players"],
                "鬘ｧ螳｢": row["customer_name"] or "荳闊ｬ鬘ｧ螳｢",
                "蜷郁ｨ・: money(float(row["final_total"] or 0)),
                "謾ｯ謇墓婿豕・: row["payment_method"] or "",
            }
        )
    return pd.DataFrame(data)


db = get_database(get_session_key())

st.title("繝薙Μ繝､繝ｼ繝牙ｺ苓・蜷代￠莨夊ｨ育ｮ｡逅・い繝励Μ")
st.caption("Python繝ｻStreamlit繝ｻSQLite縺ｧ讒狗ｯ峨＠縺滓治逕ｨ驕ｸ閠・髄縺糎eb繝・Δ")
st.info(
    "縺薙・繝・Δ縺ｮ繝・・繧ｿ縺ｯ荳譎る伜沺縺ｫ菫晏ｭ倥＆繧後∪縺吶ょｮ溷ｺ苓・蜷阪・崕隧ｱ逡ｪ蜿ｷ縲・｡ｧ螳｢繝・・繧ｿ縺ｯ蜷ｫ縺ｾ繧後※縺・∪縺帙ｓ縲・,
    icon="邃ｹ・・,
)

active_sessions = db.active_sessions()
today = db.daily_report()

metric_1, metric_2, metric_3 = st.columns(3)
metric_1.metric("蛻ｩ逕ｨ荳ｭ縺ｮ蜿ｰ謨ｰ", len(active_sessions))
metric_2.metric("譛ｬ譌･縺ｮ莨夊ｨ域焚", int(today["session_count"]))
metric_3.metric("譛ｬ譌･縺ｮ螢ｲ荳・, money(float(today["final_revenue"])))

dashboard_tab, session_tab, master_tab, report_tab = st.tabs(
    ["繝繝・す繝･繝懊・繝・, "蛻ｩ逕ｨ繝ｻ莨夊ｨ・, "鬘ｧ螳｢繝ｻ繧ｵ繝ｼ繝薙せ", "螢ｲ荳翫Ξ繝昴・繝・]
)

with dashboard_tab:
    st.subheader("蛻ｩ逕ｨ荳ｭ繧ｻ繝・す繝ｧ繝ｳ")
    if active_sessions:
        st.dataframe(format_session_frame(active_sessions), use_container_width=True, hide_index=True)
    else:
        st.info("迴ｾ蝨ｨ蛻ｩ逕ｨ荳ｭ縺ｮ蜿ｰ縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・)

    st.subheader("譛霑代・蛻ｩ逕ｨ螻･豁ｴ")
    recent_sessions = db.recent_sessions(limit=10)
    if recent_sessions:
        st.dataframe(format_session_frame(recent_sessions), use_container_width=True, hide_index=True)
    else:
        st.info("蛻ｩ逕ｨ螻･豁ｴ縺ｯ縺ｾ縺縺ゅｊ縺ｾ縺帙ｓ縲・)

with session_tab:
    start_col, action_col = st.columns(2)

    with start_col:
        st.subheader("蛻ｩ逕ｨ髢句ｧ・)
        customers = db.list_customers()
        customer_options = {"荳闊ｬ鬘ｧ螳｢": None}
        customer_options.update({f"#{row['id']} {row['name']}": row["id"] for row in customers})

        with st.form("start_session_form", clear_on_submit=True):
            table_id = st.number_input("蜿ｰ逡ｪ蜿ｷ", min_value=1, max_value=50, value=1, step=1)
            num_players = st.number_input("蛻ｩ逕ｨ莠ｺ謨ｰ", min_value=1, max_value=20, value=2, step=1)
            customer_label = st.selectbox("鬘ｧ螳｢", list(customer_options))
            prepaid = st.number_input("蜑肴鴛縺・≡鬘搾ｼ・ND・・, min_value=0, value=0, step=10000)
            notes = st.text_input("繝｡繝｢")
            start_submitted = st.form_submit_button("蛻ｩ逕ｨ繧帝幕蟋・, type="primary")

        if start_submitted:
            try:
                session_id = db.start_session(
                    table_id=int(table_id),
                    num_players=int(num_players),
                    customer_id=customer_options[customer_label],
                    prepaid=float(prepaid),
                    notes=notes,
                )
                st.success(f"繧ｻ繝・す繝ｧ繝ｳ #{session_id} 繧帝幕蟋九＠縺ｾ縺励◆縲・)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    with action_col:
        st.subheader("繧ｵ繝ｼ繝薙せ霑ｽ蜉繝ｻ莨夊ｨ・)
        active_sessions = db.active_sessions()
        if not active_sessions:
            st.info("蜈医↓蛻ｩ逕ｨ繧ｻ繝・す繝ｧ繝ｳ繧帝幕蟋九＠縺ｦ縺上□縺輔＞縲・)
        else:
            session_options = {
                f"#{row['id']} / 蜿ｰ{row['table_id']} / {row['customer_name'] or '荳闊ｬ鬘ｧ螳｢'}": row["id"]
                for row in active_sessions
            }
            selected_session_label = st.selectbox("蟇ｾ雎｡繧ｻ繝・す繝ｧ繝ｳ", list(session_options))
            selected_session_id = session_options[selected_session_label]

            services = db.list_services()
            service_options = {
                f"#{row['id']} {row['name']} ({money(float(row['price']))})": row["id"]
                for row in services
            }

            with st.form("add_service_form"):
                service_label = st.selectbox("霑ｽ蜉繧ｵ繝ｼ繝薙せ", list(service_options))
                quantity = st.number_input("謨ｰ驥・, min_value=1, max_value=20, value=1, step=1)
                service_submitted = st.form_submit_button("繧ｵ繝ｼ繝薙せ繧定ｿｽ蜉")

            if service_submitted:
                try:
                    db.add_service_to_session(
                        selected_session_id,
                        service_options[service_label],
                        int(quantity),
                    )
                    st.success("繧ｵ繝ｼ繝薙せ繧定ｿｽ蜉縺励∪縺励◆縲・)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

            with st.form("finish_session_form"):
                discount = st.number_input("蜑ｲ蠑暮≡鬘搾ｼ・ND・・, min_value=0, value=0, step=5000)
                payment_method = st.selectbox("謾ｯ謇墓婿豕・, ["迴ｾ驥・, "繧ｫ繝ｼ繝・, "QR豎ｺ貂・])
                finish_submitted = st.form_submit_button("莨夊ｨ医ｒ螳御ｺ・, type="primary")

            if finish_submitted:
                try:
                    bill = db.finish_session(
                        selected_session_id,
                        discount=float(discount),
                        payment_method=payment_method,
                    )
                    st.session_state.last_receipt = receipt_text(db.setting("club_name"), bill)
                    st.success(f"莨夊ｨ医′螳御ｺ・＠縺ｾ縺励◆縲ょ粋險・ {money(bill.final_total)}")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    if "last_receipt" in st.session_state:
        st.divider()
        st.subheader("譛譁ｰ縺ｮ鬆伜庶譖ｸ")
        st.code(st.session_state.last_receipt, language="text")
        st.download_button(
            "鬆伜庶譖ｸ繧偵ム繧ｦ繝ｳ繝ｭ繝ｼ繝・,
            data=st.session_state.last_receipt.encode("utf-8"),
            file_name="billiards_receipt.txt",
            mime="text/plain",
        )

with master_tab:
    customer_col, service_col = st.columns(2)

    with customer_col:
        st.subheader("鬘ｧ螳｢逋ｻ骭ｲ")
        with st.form("customer_form", clear_on_submit=True):
            customer_name = st.text_input("豌丞錐")
            customer_phone = st.text_input("髮ｻ隧ｱ逡ｪ蜿ｷ・医ョ繝｢逕ｨ繝ｻ莉ｻ諢擾ｼ・)
            customer_submitted = st.form_submit_button("鬘ｧ螳｢繧定ｿｽ蜉")
        if customer_submitted:
            try:
                if not customer_name.strip():
                    raise ValueError("豌丞錐繧貞・蜉帙＠縺ｦ縺上□縺輔＞縲・)
                db.add_customer(customer_name.strip(), customer_phone.strip())
                st.success("鬘ｧ螳｢繧定ｿｽ蜉縺励∪縺励◆縲・)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        customers = db.list_customers()
        if customers:
            customer_frame = rows_to_frame(customers, ["id", "name", "phone", "points", "join_date"])
            customer_frame.columns = ["ID", "豌丞錐", "髮ｻ隧ｱ逡ｪ蜿ｷ", "繝昴う繝ｳ繝・, "逋ｻ骭ｲ譌･"]
            st.dataframe(customer_frame, use_container_width=True, hide_index=True)

    with service_col:
        st.subheader("繧ｵ繝ｼ繝薙せ逋ｻ骭ｲ")
        with st.form("service_form", clear_on_submit=True):
            service_name = st.text_input("繧ｵ繝ｼ繝薙せ蜷・)
            service_price = st.number_input("譁咎≡・・ND・・, min_value=0, value=10000, step=5000)
            service_master_submitted = st.form_submit_button("繧ｵ繝ｼ繝薙せ繧定ｿｽ蜉")
        if service_master_submitted:
            try:
                if not service_name.strip():
                    raise ValueError("繧ｵ繝ｼ繝薙せ蜷阪ｒ蜈･蜉帙＠縺ｦ縺上□縺輔＞縲・)
                db.add_service(service_name.strip(), float(service_price))
                st.success("繧ｵ繝ｼ繝薙せ繧定ｿｽ蜉縺励∪縺励◆縲・)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        services = db.list_services()
        service_frame = rows_to_frame(services, ["id", "name", "price"])
        service_frame.columns = ["ID", "繧ｵ繝ｼ繝薙せ蜷・, "譁咎≡"]
        service_frame["譁咎≡"] = service_frame["譁咎≡"].map(money)
        st.dataframe(service_frame, use_container_width=True, hide_index=True)

with report_tab:
    st.subheader("譛ｬ譌･縺ｮ螢ｲ荳・)
    report = db.daily_report()
    report_frame = pd.DataFrame(
        [
            {"鬆・岼": "莨夊ｨ域焚", "蛟､": int(report["session_count"])},
            {"鬆・岼": "蜿ｰ蛻ｩ逕ｨ螢ｲ荳・, "蛟､": money(float(report["table_revenue"]))},
            {"鬆・岼": "繧ｵ繝ｼ繝薙せ螢ｲ荳・, "蛟､": money(float(report["service_revenue"]))},
            {"鬆・岼": "蜑ｲ蠑募粋險・, "蛟､": money(float(report["discounts"]))},
            {"鬆・岼": "譛邨ょ｣ｲ荳・, "蛟､": money(float(report["final_revenue"]))},
        ]
    )
    st.dataframe(report_frame, use_container_width=True, hide_index=True)

    completed = [row for row in db.recent_sessions(limit=50) if row["end_time"]]
    if completed:
        chart_frame = pd.DataFrame(
            {
                "繧ｻ繝・す繝ｧ繝ｳ": [f"#{row['id']} 蜿ｰ{row['table_id']}" for row in completed],
                "螢ｲ荳・: [float(row["final_total"] or 0) for row in completed],
            }
        ).set_index("繧ｻ繝・す繝ｧ繝ｳ")
        st.bar_chart(chart_frame)
    else:
        st.info("莨夊ｨ亥ｮ御ｺ・ｾ後↓螢ｲ荳翫げ繝ｩ繝輔′陦ｨ遉ｺ縺輔ｌ縺ｾ縺吶・)

st.divider()
st.caption("Portfolio demo by Nguyen Kim Hoang | 螳溘ョ繝ｼ繧ｿ縺ｯ菴ｿ逕ｨ縺励※縺・∪縺帙ｓ")

