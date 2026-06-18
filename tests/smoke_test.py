from pathlib import Path
from tempfile import TemporaryDirectory

from billiards_manager.database import Database, receipt_text


def main() -> None:
    with TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.db")
        customer_id = db.add_customer("Test Customer", "000-0000")
        service_id = db.add_service("Coffee", 12000)
        session_id = db.start_session(table_id=1, num_players=2, customer_id=customer_id)
        db.add_service_to_session(session_id, service_id, 2)
        bill = db.finish_session(session_id, discount=5000, payment_method="cash")
        text = receipt_text("Demo Billiards", bill)
        assert bill.final_total >= 0
        assert "Coffee" in text
        assert "TOTAL" in text
        db.close()
    print("Smoke test passed")


if __name__ == "__main__":
    main()
