from pathlib import Path
from tempfile import TemporaryDirectory

from billiards_manager.database import Database, receipt_text


def main() -> None:
    with TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        customer_id = db.add_customer("テスト顧客", "000-0000")
        service_id = db.add_service("コーヒー", 12000)
        session_id = db.start_session(table_id=1, num_players=2, customer_id=customer_id)
        db.add_service_to_session(session_id, service_id, 2)
        bill = db.finish_session(session_id, discount=5000, payment_method="現金")
        text = receipt_text("デモビリヤード", bill)
        assert bill.final_total >= 0
        assert "コーヒー" in text
        assert "合計" in text
        db.close()

        demo_db = Database(Path(tmp) / "demo.db")
        demo_db.seed_demo_data()
        demo_db.seed_demo_data()
        assert len(demo_db.active_sessions()) == 2
        assert len(demo_db.recent_sessions()) == 5
        assert demo_db.daily_report()["session_count"] == 2
        demo_db.close()
    print("スモークテストに成功しました")


if __name__ == "__main__":
    main()

