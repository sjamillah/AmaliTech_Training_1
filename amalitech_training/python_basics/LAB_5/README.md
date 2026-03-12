# LAB 5: Personal Finance Tracker

LAB 5 brings together multiple OOP ideas into a practical finance mini-app.
It tracks account activity, prints a readable report, and writes transaction history to JSON.

## What You Can Do

- Create accounts and store them in a tracker
- Record income, expense, and savings transactions
- Generate a summarized finance report
- Export transactions to `transactions.json`

## Run It

From the project root:

```powershell
poetry run python -m amalitech_training.python_basics.LAB_5.main
```

## Run The Tests

```powershell
poetry run pytest amalitech_training/python_basics/LAB_5/test_lab5.py -q
```

## Example Output

```text
=== Personal Finance Report ===
Accounts: 2
Total balance: 1525.00
Income: 750.00
Expense: 120.00
Saving: 100.00
Net cashflow: 530.00
- A-100 (Ama): balance=1380.00, income=500.00, expense=120.00, saving=0.00
- A-200 (Kojo): balance=145.00, income=250.00, expense=0.00, saving=100.00

Saved transaction history to: ...\LAB_5\transactions.json
```
