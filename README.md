# 🛡️ PayShield AI — Online Payment Fraud Detection

An intelligent, production-grade web application for detecting fraudulent online payment transactions using Machine Learning. Built with FastAPI, scikit-learn Random Forest, and a premium glassmorphism UI.

## 🌟 Features

- **AI-Powered Fraud Detection** — Random Forest classifier trained on 50,000+ transaction records
- **12-Feature Analysis** — Uses realistic behavioral features (amount, device, location, frequency, account age, etc.)
- **Real-Time Prediction** — Instant fraud risk assessment with confidence scores
- **Interactive Dashboard** — KPIs, charts, alerts, and transaction analytics
- **Prediction History** — Track all past fraud checks with statistics
- **User Authentication** — Secure login/register with session management and remember-me
- **Admin Panel** — User management with role-based access control
- **Responsive Design** — Works on desktop, tablet, and mobile
- **Premium UI** — Dark theme with glassmorphism, Inter font, micro-animations

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Jinja2 templates, Vanilla CSS, Chart.js |
| **Backend** | FastAPI (Python), Uvicorn |
| **ML Model** | scikit-learn Random Forest (200 trees) |
| **Database** | SQLite (users + predictions) |
| **Auth** | Session-based + HMAC remember-me tokens |

## 📁 Project Structure

```
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── routes/
│   │   ├── auth.py              # Login, register, logout, admin routes
│   │   └── pages.py             # Dashboard, check, predict, history routes
│   ├── services/
│   │   ├── auth_db.py           # SQLite user & prediction DB
│   │   ├── auth_guard.py        # Auth middleware helpers
│   │   ├── auth_tokens.py       # Remember-me token signing
│   │   └── inference.py         # ML model inference
│   ├── static/
│   │   └── style.css            # Premium design system
│   ├── templates/
│   │   ├── base.html            # Shared layout (sidebar + nav)
│   │   ├── login.html           # Login page
│   │   ├── register.html        # Registration page
│   │   ├── dashboard.html       # Analytics dashboard
│   │   ├── index.html           # Transaction check form
│   │   ├── result.html          # Prediction result
│   │   ├── history.html         # Prediction history
│   │   ├── profile.html         # User profile
│   │   └── admin.html           # Admin panel
│   └── data/
│       └── users.db             # SQLite database (auto-created)
├── data/
│   ├── fraud_data.csv           # Model dataset
│   └── fraud dataset.csv        # Unprocessed dataset
├── docs/
│   └── Online Payment Fraud Detection SRS.docx
├── ml/
│   ├── train.py                 # Model training script
│   └── artifacts/
│       ├── pipeline.pkl         # Trained model pipeline
│       ├── threshold.json       # Classification threshold
│       └── model_metrics.json   # Model evaluation metrics
├── requirements.txt
└── README.md
```

## 🚀 Setup & Run

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Step 1: Create Virtual Environment

```bash
python -m venv venv
```

### Step 2: Activate Virtual Environment

**Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**

```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**

```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Train the ML Model

```bash
python ml/train.py
```

This will:

- Load the 50,000-row dataset
- Train a Random Forest classifier (200 trees)
- Save the trained pipeline to `ml/artifacts/pipeline.pkl`
- Print accuracy, precision, recall, and F1 score

### Step 5: Run the Application

```bash
python -m uvicorn app.main:app --reload
```

The app will be available at: **<http://127.0.0.1:8000>**

### Step 6: First-Time Setup

1. Visit `http://127.0.0.1:8000` — you'll be redirected to login
2. Click **"Create an account"** to register
3. The **first registered user** automatically becomes **admin**
4. You're now ready to use the system!

## 🤖 ML Model Details

| Property | Value |
|----------|-------|
| **Algorithm** | Random Forest Classifier |
| **Trees** | 200 estimators |
| **Max Depth** | 18 |
| **Class Weight** | Balanced |
| **Dataset** | 50,000 transactions |
| **Features** | 12 (6 numeric + 6 categorical) |

### Features Used for Prediction

| Feature | Type | Description |
|---------|------|-------------|
| `amount` | Numeric | Transaction amount in INR |
| `transaction_time` | Numeric | Hour of day (0-23) |
| `transaction_frequency` | Numeric | Monthly transaction count |
| `account_age_days` | Numeric | Days since account creation |
| `avg_transaction_amount` | Numeric | User's average spending |
| `failed_transactions_24h` | Numeric | Failed attempts in 24 hours |
| `device_type` | Categorical | mobile / desktop / tablet |
| `location` | Categorical | urban / semi-urban / rural |
| `payment_method` | Categorical | UPI / Debit Card / Credit Card / Net Banking / Paytm Wallet |
| `merchant_category` | Categorical | electronics / fashion / groceries / etc. |
| `is_international` | Binary | Domestic or international |
| `device_change` | Binary | Same or different device |

## 📊 Dataset Details

The system uses a comprehensive dataset with 50,000 transaction records containing:

- Realistic transaction amounts and patterns
- Multiple payment methods (UPI, Debit Card, Credit Card, Net Banking, Paytm Wallet)
- Various merchant categories
- Device and location behavioral data
- Account age and transaction frequency metrics
- Balanced fraud/safe labels

## 🔄 Key Changes from Previous Version

| Area | Before | After |
|------|--------|-------|
| **Dataset** | 10,000 rows, 6 features | 50,000 rows, 14 features |
| **Model** | Logistic Regression | Random Forest (200 trees) |
| **Auth** | Broken — hardcoded Guest user | Fully integrated session auth |
| **Input** | Required Transaction ID / UPI ID | Uses behavioral features only |
| **Pages** | Dashboard not auth-protected | All pages require login |
| **History** | Not available | Full prediction history |
| **DB** | Users only | Users + Predictions |
| **UI** | Inline styles, inconsistent | Design system, base template |
| **Admin** | Duplicate route conflicts | Single consolidated router |
| **Frontend** | No shared layout | Base template (DRY) |
| **Responsive** | Partial | Full mobile/tablet/desktop |

## 🛡️ Security

- Passwords hashed with PBKDF2-SHA256
- Session-based authentication
- HMAC-signed remember-me tokens
- CSRF protection via session middleware
- Input validation on all forms
- SQL parameterized queries (no injection)

## 📝 License

This project is for educational and demonstration purposes.

THIS PROJECT IS DONE BY THE TEAM MEMBERS:

1. GEMINI AI (<https://gemini.google.com/app/05ce25f6a681239d?hl=en-IN> ,, <https://gemini.google.com/app/059cfbe517802db9?hl=en-IN>)
2. CHATGPT AI (<https://chatgpt.com/g/g-p-698602d8abb08191accdb41b3f802c1e-homework/project> ,, <https://chatgpt.com/c/69dd41f3-58d8-83e8-b339-c6aefcb25a30>)
3. CLAUDE AI (<https://claude.ai/chat/d5e553d2-af2f-4f75-a45d-674970e9a716> ,, <https://claude.ai/chat/4f68253c-c8db-4448-aab4-91efeaa9b46e>)
4. CHAITANYA PAMARTHI (THE DESSION MAKER) ( Email : <pamarthichaitanya1@gmail.com>
LinkedinURL : <https://www.linkedin.com/in/chaitanya-pamarthi-24b198309?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app>

Github : <https://github.com/chaitu-2303>)
