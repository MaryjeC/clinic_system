# School Clinic Health Monitoring System

A Flask web app that reads `clinic_visits.csv` and shows clinic KPIs and charts.

## How to run (Windows)

```bash
cd "C:\Users\Maryje Clasin\clinic_system"
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser. The first time, click **Register here** to create an account, then log in.
Accounts are saved in `users.db` (created automatically). Passwords are stored as secure hashes, not plain text. Press `Ctrl + C` in the terminal to stop the server.
You need internet the first time a page loads, because Bootstrap and Chart.js are loaded from a CDN.

## Project structure

```
clinic_system/
├── app.py               # Flask app: accounts, data, analysis and routes
├── users.db             # User accounts (created automatically on first run)
├── generate_data.py     # Makes sample clinic_visits.csv (run once if you need fresh data)
├── clinic_visits.csv    # The data
├── requirements.txt
├── static/
│   └── style.css
└── templates/
    ├── base.html        # Navbar + layout shared by all pages
    ├── _auth_base.html  # Shared layout for login/register
    ├── login.html
    ├── register.html
    ├── _flash.html, _macros.html, _toggle_pw.html   # small reusable pieces
    ├── dashboard.html   # KPIs + 4 charts
    ├── visits.html      # Table of all visits with search
    └── add_visit.html   # Form to add a new visit
```

## CSV columns

`visit_id, student_id, age, gender, course, complaint, date`

`course` was added to the teacher's columns because the "Visits by Course" chart needs it.

## Features

| Requirement | Where |
|---|---|
| Total Clinic Visits | Dashboard KPI card |
| Most Common Illness | Dashboard KPI card |
| Male/Female Visits | Dashboard KPI card with split bar |
| Monthly Cases | Dashboard KPI card (latest month + monthly average) |
| Illness Distribution | Horizontal bar chart |
| Visits per Month | Line chart |
| Visits by Course | Bar chart |
| Age Group Analysis | Bar chart (17-18, 19-20, 21-22, 23-24, 25+) |
| Extra | Register / login / logout, dashboard filters (course, gender, month), visit search, add-visit form, recent visits |

## Run it online with GitHub Codespaces (no install needed)

1. On this repository's GitHub page, click the green **Code** button → **Codespaces** tab → **Create codespace on main**.
2. Wait for it to finish setting up (Flask installs automatically).
3. In the terminal at the bottom, type: `python app.py`
4. Click **Open in Browser** when the pop-up appears, then register an account and log in.
