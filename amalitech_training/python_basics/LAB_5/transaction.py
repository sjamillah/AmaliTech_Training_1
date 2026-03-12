from abc import ABC
from datetime import datetime


ALLOWED_KINDS = {"income", "expense", "saving"}


class Transaction(ABC):
    def __init__(self, amount, category, kind, description="", created_at=None):
        self.amount = float(amount)
        self.category = category
        self.kind = kind
        self.description = description
        if created_at is None:
            self.created_at = datetime.now().isoformat(timespec="seconds")
        else:
            self.created_at = created_at

        if self.amount <= 0:
            raise ValueError("Transaction amount must be positive")
        if self.kind not in ALLOWED_KINDS:
            raise ValueError(f"Transaction kind must be one of {ALLOWED_KINDS}")

    def to_dict(self):
        return {
            "amount": self.amount,
            "category": self.category,
            "kind": self.kind,
            "description": self.description,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(payload):
        kind = payload.get("kind")
        amount = payload.get("amount")
        category = payload.get("category", "general")
        description = payload.get("description", "")
        created_at = payload.get("created_at")

        if kind == "income":
            tx = IncomeTransaction(amount=amount, category=category, description=description)
        elif kind == "expense":
            tx = ExpenseTransaction(amount=amount, category=category, description=description)
        elif kind == "saving":
            tx = SavingsTransaction(amount=amount, category=category, description=description)
        else:
            raise ValueError(f"Unsupported transaction kind in JSON: {kind}")

        if created_at:
            tx.created_at = created_at
        return tx

    def __str__(self):
        return f"{self.kind.title()}({self.category}): {self.amount:.2f}"

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(amount={self.amount!r}, category={self.category!r}, "
            f"description={self.description!r}, created_at={self.created_at!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, Transaction):
            return False
        return (
            self.amount == other.amount
            and self.category == other.category
            and self.kind == other.kind
            and self.description == other.description
        )

    def __add__(self, other):
        if isinstance(other, Transaction):
            return self.amount + other.amount
        if isinstance(other, (int, float)):
            return self.amount + float(other)
        return NotImplemented


class IncomeTransaction(Transaction):
    def __init__(self, amount, category="income", description=""):
        super().__init__(amount=amount, category=category, kind="income", description=description)


class ExpenseTransaction(Transaction):
    def __init__(self, amount, category="expense", description=""):
        super().__init__(amount=amount, category=category, kind="expense", description=description)


class SavingsTransaction(Transaction):
    def __init__(self, amount, category="savings", description=""):
        super().__init__(amount=amount, category=category, kind="saving", description=description)

