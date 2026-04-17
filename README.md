# GreenFields College — Finance & HR Management System

## How to Run

1. Install Flask:
   pip install flask

2. Run the app:
   python app.py

3. Open your browser at:
   http://127.0.0.1:5000

---

## Pages & Features

| Page             | URL              | What it does                                      |
|------------------|------------------|---------------------------------------------------|
| Dashboard        | /                | Charts — fee collected, dues, salary overview     |
| All Students     | /students        | View all students with fee progress bars          |
| Add Student      | /students/add    | Add a new student with fee details                |
| Edit Student     | /students/edit/  | Update fee paid, fine, course details             |
| Fee Tracker      | /fees            | Filter by Paid / Partial / Unpaid / Fined         |
| All Faculty      | /faculty         | View faculty with salary breakdown                |
| Add Faculty      | /faculty/add     | Add faculty with salary, allowance, deduction     |
| Edit Faculty     | /faculty/edit/   | Update months paid, salary components             |
| Salary Tracker   | /salary          | Progress bars for salary disbursement             |
| Notices          | /notices         | Post and view college notices                     |

---

## Data Storage

All data is stored in `college_data.json` (auto-created on first run).
To reset data, delete `college_data.json` and restart the app.

For production: replace the JSON file with SQLite using Flask-SQLAlchemy.

---

## Dashboard Charts (powered by Chart.js)

- Donut: Fee Collected vs Due
- Bar: Student payment status (Paid / Partial / Unpaid)
- Bar: Course-wise fee due breakdown
- Stacked Bar: Faculty salary paid vs pending


