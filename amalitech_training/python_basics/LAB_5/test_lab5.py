import json

from amalitech_training.python_basics.LAB_5.account import SavingsAccount, StandardAccount
from amalitech_training.python_basics.LAB_5.main import (
    PersonalFinanceTracker,
    build_finance_report,
    save_transactions_to_json,
)
from amalitech_training.python_basics.LAB_5.transaction import (
    ExpenseTransaction,
    IncomeTransaction,
    SavingsTransaction,
    Transaction,
)


def test_account_applies_transactions_and_updates_balance():
    account = StandardAccount("ACC-1", "Ama", "111", "1234", 100)

    account.apply_transaction(IncomeTransaction(50, "salary"))
    account.apply_transaction(ExpenseTransaction(20, "food"))
    account.apply_transaction(SavingsTransaction(10, "goal"))

    assert account.total_amount == 120


def test_insufficient_funds_raises_error():
    account = StandardAccount("ACC-2", "Kojo", "222", "1234", 30)

    try:
        account.apply_transaction(ExpenseTransaction(40, "shopping"))
        assert False, "Expected ValueError for insufficient funds"
    except ValueError as exc:
        assert "Insufficient funds" in str(exc)


def test_account_magic_methods_work():
    account_1 = StandardAccount("ACC-3", "A", "333", "1111", 100)
    account_2 = StandardAccount("ACC-4", "B", "444", "2222", 50)
    account_3 = StandardAccount("ACC-3", "A2", "555", "3333", 10)

    assert account_1 == account_3
    assert account_1 + account_2 == 150


def test_transaction_magic_methods_and_from_dict():
    tx1 = IncomeTransaction(100, "salary", "monthly salary")
    tx2 = IncomeTransaction(100, "salary", "monthly salary")
    tx3 = ExpenseTransaction(20, "food")

    assert tx1 == tx2
    assert tx1 + tx3 == 120

    tx_data = {
        "amount": 15,
        "category": "transport",
        "kind": "expense",
        "description": "bus fare",
    }
    tx = Transaction.from_dict(tx_data)
    assert isinstance(tx, ExpenseTransaction)
    assert tx.amount == 15


def test_report_uses_comprehension_totals():
    tracker = PersonalFinanceTracker()
    account = SavingsAccount("ACC-5", "Esi", "777", "1234", 200, 50)
    tracker.add_account(account)

    tracker.record_transaction("ACC-5", IncomeTransaction(100, "salary"))
    tracker.record_transaction("ACC-5", ExpenseTransaction(30, "food"))
    tracker.record_transaction("ACC-5", SavingsTransaction(20, "goal"))

    report = build_finance_report(tracker)

    assert report["total_income"] == 100
    assert report["total_expense"] == 30
    assert report["total_saving"] == 20
    assert report["net"] == 50


def test_save_transactions_to_json(tmp_path):
    tracker = PersonalFinanceTracker()
    account = StandardAccount("ACC-6", "Yaw", "888", "0000", 100)
    tracker.add_account(account)
    tracker.record_transaction("ACC-6", IncomeTransaction(25, "gift"))

    file_path = tmp_path / "transactions.json"
    save_transactions_to_json(tracker, file_path)

    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["account_id"] == "ACC-6"
    assert data[0]["transactions"][0]["kind"] == "income"
