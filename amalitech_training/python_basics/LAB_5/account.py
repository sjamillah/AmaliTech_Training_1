from abc import ABC, abstractmethod

class Account(ABC):
    def __init__(self, bank_id, owner, bank_number, password, total_amount):
        self._bank_id = bank_id
        self.owner = owner
        self.bank_number = bank_number
        self._password = password

        self.validate_amount(total_amount)
        self._total_amount = total_amount
        self._transactions = []

    @property
    def bank_id(self):
        return self._bank_id
    
    @property
    def total_amount(self):
        return self._total_amount

    @property
    def balance(self):
        return self._total_amount

    @property
    def transactions(self):
        return list(self._transactions)
    
    def validate_amount(self, total_amount):
        if total_amount < 0:
            raise ValueError("Amount must be greater than or equal to 0")
        
    def check_password(self, password):
        return password == self._password

    def apply_transaction(self, transaction):
        if transaction.kind == "income":
            self._total_amount += transaction.amount
        elif transaction.kind == "expense" or transaction.kind == "saving":
            if transaction.amount > self._total_amount:
                raise ValueError("Insufficient funds")
            self._total_amount -= transaction.amount
        else:
            raise ValueError(f"Unsupported transaction type: {transaction.kind}")

        self._transactions.append(transaction)
        return self._total_amount

    def transaction_totals(self):
        income = 0
        expense = 0
        saving = 0

        for tx in self._transactions:
            if tx.kind == "income":
                income += tx.amount
            elif tx.kind == "expense":
                expense += tx.amount
            elif tx.kind == "saving":
                saving += tx.amount

        return {"income": income, "expense": expense, "saving": saving}
            
    @abstractmethod
    def calculate_total_amount(self):
        pass

    def monthly_update(self):
        return self.calculate_total_amount()

    def __str__(self):
        return f"Account({self.owner}, balance={self.total_amount})"

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(bank_id={self.bank_id!r}, owner={self.owner!r}, "
            f"bank_number={self.bank_number!r}, total_amount={self.total_amount!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, Account):
            return False
        return self.bank_id == other.bank_id

    def __add__(self, other):
        if isinstance(other, Account):
            return self.total_amount + other.total_amount
        if isinstance(other, (int, float)):
            return self.total_amount + float(other)
        return NotImplemented


class StandardAccount(Account):
    def calculate_total_amount(self):
        return self.total_amount

class SavingsAccount(Account):
    def __init__(self, bank_id, owner, bank_number, password, total_amount, savings):
        super().__init__(bank_id, owner, bank_number, password, total_amount)

        if savings < 0:
            raise ValueError("Savings must be non-negative")
        
        self.savings = savings

    def calculate_total_amount(self):
        return self.total_amount + self.savings
