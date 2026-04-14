import numpy as np
import pandas as pd

np.random.seed(42)
N = 50000
FRAUD_RATE = 0.08

n_fraud = int(N * FRAUD_RATE)
n_safe = N - n_fraud

device_types = ["mobile", "desktop", "tablet"]
locations = ["urban", "semi-urban", "rural"]
payment_methods = ["UPI", "Debit Card", "Credit Card", "Net Banking", "Paytm Wallet"]
merchant_cats = [
    "electronics", "fashion", "groceries", "food", "travel",
    "gaming", "entertainment", "health", "education", "recharge"
]

def gen_safe(n):
    rows = []
    for _ in range(n):
        amount = np.random.lognormal(mean=6.5, sigma=0.8)
        amount = min(amount, 25000)
        hour = int(np.random.choice(range(24), p=_time_dist_safe()))
        device = np.random.choice(device_types, p=[0.55, 0.35, 0.10])
        loc = np.random.choice(locations, p=[0.50, 0.35, 0.15])
        method = np.random.choice(payment_methods, p=[0.35, 0.25, 0.20, 0.12, 0.08])
        cat = np.random.choice(merchant_cats)
        freq = max(1, int(np.random.normal(15, 8)))
        age = max(30, int(np.random.normal(600, 400)))
        avg_amt = amount * np.random.uniform(0.6, 1.5)
        failed = np.random.choice([0, 0, 0, 0, 0, 0, 0, 0, 1, 1], p=None)
        intl = 0 if np.random.random() < 0.92 else 1
        dev_change = 0 if np.random.random() < 0.88 else 1

        rows.append([
            round(amount, 2), hour, device, loc, method, cat,
            freq, age, round(avg_amt, 2), failed, intl, dev_change, 0
        ])
    return rows

def gen_fraud(n):
    rows = []
    for _ in range(n):
        pattern = np.random.choice(["high_amount", "night_new_device", "rapid_fire", "intl_high", "mixed"])

        if pattern == "high_amount":
            amount = np.random.uniform(8000, 30000)
            hour = np.random.choice(range(24))
            dev_change = np.random.choice([0, 1], p=[0.3, 0.7])
            failed = np.random.choice([2, 3, 4, 5, 6])
            freq = max(1, int(np.random.normal(35, 10)))
            age = max(5, int(np.random.exponential(90)))
            intl = np.random.choice([0, 1], p=[0.5, 0.5])

        elif pattern == "night_new_device":
            amount = np.random.uniform(2000, 15000)
            hour = np.random.choice([22, 23, 0, 1, 2, 3, 4])
            dev_change = 1
            failed = np.random.choice([1, 2, 3, 4])
            freq = max(1, int(np.random.normal(28, 12)))
            age = max(5, int(np.random.exponential(150)))
            intl = np.random.choice([0, 1], p=[0.65, 0.35])

        elif pattern == "rapid_fire":
            amount = np.random.uniform(500, 8000)
            hour = np.random.choice(range(24))
            dev_change = np.random.choice([0, 1], p=[0.4, 0.6])
            failed = np.random.choice([3, 4, 5, 6, 7, 8])
            freq = max(30, int(np.random.normal(45, 10)))
            age = max(5, int(np.random.exponential(60)))
            intl = np.random.choice([0, 1], p=[0.6, 0.4])

        elif pattern == "intl_high":
            amount = np.random.uniform(5000, 25000)
            hour = np.random.choice(range(24))
            dev_change = np.random.choice([0, 1], p=[0.35, 0.65])
            failed = np.random.choice([1, 2, 3, 4])
            freq = max(1, int(np.random.normal(20, 10)))
            age = max(10, int(np.random.exponential(200)))
            intl = 1

        else:
            amount = np.random.uniform(3000, 20000)
            hour = np.random.choice([21, 22, 23, 0, 1, 2, 3, 4, 5])
            dev_change = np.random.choice([0, 1], p=[0.25, 0.75])
            failed = np.random.choice([2, 3, 4, 5])
            freq = max(20, int(np.random.normal(35, 12)))
            age = max(5, int(np.random.exponential(120)))
            intl = np.random.choice([0, 1], p=[0.45, 0.55])

        device = np.random.choice(device_types, p=[0.35, 0.45, 0.20])
        loc = np.random.choice(locations, p=[0.30, 0.30, 0.40])
        method = np.random.choice(payment_methods, p=[0.20, 0.20, 0.30, 0.20, 0.10])
        cat = np.random.choice(merchant_cats, p=[0.25, 0.15, 0.05, 0.05, 0.15, 0.15, 0.05, 0.05, 0.02, 0.08])
        avg_amt = amount * np.random.uniform(0.1, 0.5)

        rows.append([
            round(amount, 2), hour, device, loc, method, cat,
            freq, age, round(avg_amt, 2), failed, intl, dev_change, 1
        ])
    return rows

def _time_dist_safe():
    p = np.zeros(24)
    for h in range(6, 22):
        p[h] = 4.0
    for h in [22, 23, 0, 1, 2, 3, 4, 5]:
        p[h] = 1.0
    return p / p.sum()

safe_rows = gen_safe(n_safe)
fraud_rows = gen_fraud(n_fraud)
all_rows = safe_rows + fraud_rows

cols = [
    "amount", "transaction_time", "device_type", "location",
    "payment_method", "merchant_category", "transaction_frequency",
    "account_age_days", "avg_transaction_amount", "failed_transactions_24h",
    "is_international", "device_change", "is_fraud"
]

df = pd.DataFrame(all_rows, columns=cols)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)
df.insert(0, "transaction_id", range(1, len(df) + 1))

df.to_csv("data/fraud_data.csv", index=False)

print(f"Generated {len(df)} rows")
print(f"Fraud: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.1f}%)")
print(f"\nCorrelations with is_fraud:")
print(df.select_dtypes(include="number").corrwith(df["is_fraud"]).sort_values(ascending=False))
print("\nSaved to data/fraud_data.csv")
