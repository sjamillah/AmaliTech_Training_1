import json
from pathlib import Path

from .account import SavingsAccount, StandardAccount
from .transaction import ExpenseTransaction, IncomeTransaction, SavingsTransaction


class PersonalFinanceTracker:
    def __init__(self):
        self.accounts = {}

    def add_account(self, account):
        if account.bank_id in self.accounts:
            raise ValueError(f"Account {account.bank_id} already exists")
        self.accounts[account.bank_id] = account

    def record_transaction(self, account_id, transaction):
        if account_id not in self.accounts:
            raise ValueError(f"No account found for id {account_id}")
        return self.accounts[account_id].apply_transaction(transaction)

    def total_balance(self):
        return sum(account.balance for account in self.accounts.values())

    def account_summaries(self):
        summaries = {}
        for account_id, account in self.accounts.items():
            totals = account.transaction_totals()
            summaries[account_id] = {
                "owner": account.owner,
                "balance": account.balance,
                "income": totals["income"],
                "expense": totals["expense"],
                "saving": totals["saving"],
            }
        return summaries


def save_transactions_to_json(tracker, file_path):
    data = []
    for account_id, account in tracker.accounts.items():
        data.append(
            {
                "account_id": account_id,
                "transactions": [tx.to_dict() for tx in account.transactions],
            }
        )

    try:
        Path(file_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Could not save file: {exc}") from exc


def build_finance_report(tracker):
    summaries = tracker.account_summaries()

    total_income = sum(item["income"] for item in summaries.values())
    total_expense = sum(item["expense"] for item in summaries.values())
    total_saving = sum(item["saving"] for item in summaries.values())

    return {
        "accounts": len(summaries),
        "total_balance": tracker.total_balance(),
        "total_income": total_income,
        "total_expense": total_expense,
        "total_saving": total_saving,
        "net": total_income - total_expense - total_saving,
        "details": summaries,
    }


def format_finance_report(report):
    lines = [
        "=== Personal Finance Report ===",
        f"Accounts: {report['accounts']}",
        f"Total balance: {report['total_balance']:.2f}",
        f"Income: {report['total_income']:.2f}",
        f"Expense: {report['total_expense']:.2f}",
        f"Saving: {report['total_saving']:.2f}",
        f"Net cashflow: {report['net']:.2f}",
    ]

    for account_id, info in report["details"].items():
        lines.append(
            f"- {account_id} ({info['owner']}): balance={info['balance']:.2f}, "
            f"income={info['income']:.2f}, expense={info['expense']:.2f}, saving={info['saving']:.2f}"
        )

    return "\n".join(lines)


def process_actions(tracker, actions):
    for action in actions:
        action_type = action["type"]
        amount = action["amount"]
        account_id = action["account_id"]

        if action_type == "income":
            tx = IncomeTransaction(amount, category=action.get("category", "salary"))
        elif action_type == "expense":
            tx = ExpenseTransaction(amount, category=action.get("category", "misc"))
        elif action_type == "saving":
            tx = SavingsTransaction(amount, category=action.get("category", "goal"))
        else:
            raise ValueError(f"Unsupported action type: {action_type}")

        tracker.record_transaction(account_id, tx)


def run_demo():
    tracker = PersonalFinanceTracker()

    standard = StandardAccount("A-100", "Ama", "001122", "1234", 1000)
    savings = SavingsAccount("A-200", "Kojo", "001133", "5678", 500, 100)

    tracker.add_account(standard)
    tracker.add_account(savings)

    actions = [
        {"account_id": "A-100", "type": "income", "amount": 500, "category": "salary"},
        {"account_id": "A-100", "type": "expense", "amount": 120, "category": "food"},
        {"account_id": "A-200", "type": "saving", "amount": 100, "category": "vacation"},
        {"account_id": "A-200", "type": "income", "amount": 250, "category": "freelance"},
    ]

    process_actions(tracker, actions)

    for account in tracker.accounts.values():
        account.monthly_update()

    report = build_finance_report(tracker)
    print(format_finance_report(report))

    output_path = Path(__file__).with_name("transactions.json")
    save_transactions_to_json(tracker, output_path)
    print(f"\nSaved transaction history to: {output_path}")


if __name__ == "__main__":
    try:
        run_demo()
    except (ValueError, RuntimeError) as exc:
        print(f"Application error: {exc}")
