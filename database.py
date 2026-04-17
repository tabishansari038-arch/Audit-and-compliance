"""
database.py — SQLite database setup, schema, and seed data
University Audit & Compliance Portal — Greenfield University
"""

import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "audit.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # ── USERS ──────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        email       TEXT UNIQUE NOT NULL,
        role        TEXT NOT NULL DEFAULT 'auditor',
        department  TEXT,
        initials    TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    )""")

    # ── AUDITS ─────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS audits (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_code  TEXT UNIQUE NOT NULL,
        name        TEXT NOT NULL,
        type        TEXT NOT NULL,
        department  TEXT NOT NULL,
        lead_auditor TEXT NOT NULL,
        start_date  TEXT,
        due_date    TEXT,
        status      TEXT NOT NULL DEFAULT 'Pending',
        score       REAL,
        priority    TEXT DEFAULT 'Medium',
        scope       TEXT,
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )""")

    # ── FINDINGS ───────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS findings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        finding_code TEXT UNIQUE NOT NULL,
        title       TEXT NOT NULL,
        audit_id    INTEGER REFERENCES audits(id),
        audit_name  TEXT,
        severity    TEXT NOT NULL,
        description TEXT,
        recommendation TEXT,
        owner       TEXT NOT NULL,
        due_date    TEXT,
        status      TEXT NOT NULL DEFAULT 'Open',
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )""")

    # ── RISKS ──────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS risks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        risk_code   TEXT UNIQUE NOT NULL,
        description TEXT NOT NULL,
        category    TEXT NOT NULL,
        owner       TEXT NOT NULL,
        likelihood  INTEGER NOT NULL CHECK(likelihood BETWEEN 1 AND 5),
        impact      INTEGER NOT NULL CHECK(impact BETWEEN 1 AND 5),
        score       INTEGER GENERATED ALWAYS AS (likelihood * impact) STORED,
        mitigations TEXT,
        status      TEXT DEFAULT 'Open',
        created_at  TEXT DEFAULT (datetime('now')),
        updated_at  TEXT DEFAULT (datetime('now'))
    )""")

    # ── POLICIES ───────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        category        TEXT NOT NULL,
        version         TEXT NOT NULL DEFAULT '1.0',
        owner           TEXT NOT NULL,
        review_frequency TEXT DEFAULT 'Annual',
        last_review     TEXT,
        next_review     TEXT,
        effective_date  TEXT,
        status          TEXT NOT NULL DEFAULT 'Current',
        summary         TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        updated_at      TEXT DEFAULT (datetime('now'))
    )""")

    # ── COMPLIANCE CHECKLIST ───────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS checklist_items (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        reference   TEXT,
        is_checked  INTEGER NOT NULL DEFAULT 0,
        checked_by  TEXT,
        checked_at  TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    )""")

    # ── NOTIFICATIONS ──────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        message     TEXT NOT NULL,
        type        TEXT DEFAULT 'info',
        is_read     INTEGER DEFAULT 0,
        created_at  TEXT DEFAULT (datetime('now'))
    )""")

    conn.commit()
    conn.close()
    print("[DB] Schema created.")


def seed_db():
    conn = get_db()
    c = conn.cursor()

    # Skip if already seeded
    c.execute("SELECT COUNT(*) FROM audits")
    if c.fetchone()[0] > 0:
        print("[DB] Already seeded.")
        conn.close()
        return

    # ── USERS ──────────────────────────────────────────────────────────────
    users = [
        ("Dr. J. Mitchell",   "j.mitchell@greenfield.ac.uk",   "Chief Auditor",   "Internal Audit", "JM"),
        ("A. Brown",          "a.brown@greenfield.ac.uk",      "Auditor",         "Finance",        "AB"),
        ("K. Patel",          "k.patel@greenfield.ac.uk",      "Auditor",         "IT Services",    "KP"),
        ("M. Singh",          "m.singh@greenfield.ac.uk",      "Auditor",         "HR",             "MS"),
        ("Dr. Chen",          "d.chen@greenfield.ac.uk",       "Auditor",         "Research Office","DC"),
        ("P. Okoye",          "p.okoye@greenfield.ac.uk",      "Auditor",         "Library",        "PO"),
        ("S. Ahmed",          "s.ahmed@greenfield.ac.uk",      "Auditor",         "Registry",       "SA"),
        ("R. Thomas",         "r.thomas@greenfield.ac.uk",     "Auditor",         "Estates",        "RT"),
        ("L. Park",           "l.park@greenfield.ac.uk",       "Auditor",         "Finance",        "LP"),
    ]
    c.executemany("INSERT OR IGNORE INTO users (name,email,role,department,initials) VALUES (?,?,?,?,?)", users)

    # ── AUDITS ─────────────────────────────────────────────────────────────
    audits = [
        ("AUD-001","Financial Audit 2024",          "Financial",   "Finance",         "A. Brown",  "2026-01-15","2026-04-22","In Progress",  None, "High",   "Full review of financial controls and expenditure for FY 2024-25"),
        ("AUD-002","IT Security Review",            "IT Security", "IT Services",     "K. Patel",  "2026-04-15","2026-05-01","In Progress",  None, "High",   "Assessment of cybersecurity posture, access controls and patch management"),
        ("AUD-003","HR Compliance Audit",           "HR",          "Human Resources", "M. Singh",  "2026-03-01","2026-04-08","Completed",    91.0, "Medium", "Review of HR policies, training records and contractual compliance"),
        ("AUD-004","Research Ethics Review",        "Academic",    "Research Office", "Dr. Chen",  "2026-02-10","2026-03-28","Completed",    88.0, "Medium", "Compliance review against UKRI ethics requirements"),
        ("AUD-005","Library Systems Audit",         "IT Security", "Library",         "P. Okoye",  "2026-01-20","2026-03-10","Completed",    76.0, "Low",    "Audit of library management systems and data retention"),
        ("AUD-006","Student Data Compliance",       "HR",          "Registry",        "S. Ahmed",  "2026-03-20","2026-05-15","In Progress",  None, "High",   "Review of student data handling against GDPR requirements"),
        ("AUD-007","Estates Safety Audit",          "Financial",   "Estates",         "R. Thomas", "2026-02-28","2026-04-30","In Progress",  None, "Medium", "Health and safety compliance audit across all campus buildings"),
        ("AUD-008","Procurement Governance Audit",  "Financial",   "Finance",         "L. Park",   "2026-02-01","2026-03-31","Overdue",      None, "High",   "Review of procurement processes and supplier due diligence"),
        ("AUD-009","Payroll Compliance 2024",       "Financial",   "Finance",         "A. Brown",  "2025-11-01","2026-02-20","Completed",    94.0, "Medium", "Annual payroll compliance and HMRC obligations audit"),
        ("AUD-010","International Student Compliance","Academic",  "Registry",        "S. Ahmed",  "2025-10-15","2026-01-15","Completed",    89.0, "Medium", "Home Office compliance for international student monitoring"),
        ("AUD-011","Annual Risk Assessment",        "Academic",    "All",             "J. Mitchell","2026-05-01","2026-06-01","Pending",      None, "High",   "University-wide annual risk assessment and register update"),
        ("AUD-012","Research Grants Audit",         "Financial",   "Research Office", "Dr. Chen",  "2026-05-15","2026-06-30","Pending",      None, "Medium", "Audit of grant expenditure and compliance with funder requirements"),
    ]
    c.executemany("""INSERT OR IGNORE INTO audits
        (audit_code,name,type,department,lead_auditor,start_date,due_date,status,score,priority,scope)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", audits)

    # ── FINDINGS ───────────────────────────────────────────────────────────
    findings = [
        ("FND-001","Inadequate procurement approval controls",    1,"Financial Audit 2024",          "Critical","Purchases above £10k are being authorised by a single signatory contrary to the dual-authorisation policy.","Implement mandatory dual-authorisation workflow in the finance system for all transactions above £10,000.","Finance Director","2026-04-25","Open"),
        ("FND-002","Student data stored unencrypted on shared drive",2,"IT Security Review",         "Critical","Sensitive student personal data including medical records found unencrypted on a shared network drive accessible to 47 staff.","Immediately encrypt the shared drive, restrict access to authorised staff only, and review all data storage locations.","IT Manager","2026-04-20","In Progress"),
        ("FND-003","Outdated access control lists on servers",    2,"IT Security Review",            "High",    "Seven production servers still carry access permissions for 14 former employees who left 3-18 months ago.","Implement automated offboarding process that revokes all system access within 24 hours of employment termination.","Systems Team","2026-05-01","Open"),
        ("FND-004","Missing training records for 12 staff members",3,"HR Compliance Audit",          "High",    "Mandatory data protection training records are missing for 12 members of staff across Finance and Registry departments.","Conduct emergency training sessions and establish a centralised training management system with automatic reminders.","HR Manager","2026-04-30","In Progress"),
        ("FND-005","Research consent forms non-compliant with GDPR",4,"Research Ethics Review",      "High",    "Consent forms for two active research projects do not include the mandatory data retention and subject rights information required by GDPR Article 13.","Update all consent forms immediately and obtain fresh consent from affected participants where legally required.","Research Office","2026-04-15","Open"),
        ("FND-006","Library CCTV data retention period exceeded", 5,"Library Systems Audit",         "Medium",  "CCTV footage in the main library is being retained for 42 days, exceeding the university policy maximum of 31 days.","Configure CCTV system to auto-delete footage after 31 days and document the configuration change.","Library Director","2026-05-10","Resolved"),
        ("FND-007","Absence management reporting gap identified", 3,"HR Compliance Audit",           "Medium",  "Absence data for agency staff is not being captured in the central HR system, creating a gap in statutory absence reporting.","Extend absence management system to include agency staff and update contract templates with reporting requirements.","HR Team","2026-05-15","Resolved"),
        ("FND-008","Password policy not enforced for all systems",2,"IT Security Review",            "Medium",  "The university password policy (12 chars, complexity, 90-day rotation) is not enforced on 3 legacy administrative systems.","Upgrade or replace legacy systems to enforce the password policy, or implement a password manager integration.","IT Manager","2026-05-05","Open"),
        ("FND-009","Budget variance reporting delayed by 15 days",1,"Financial Audit 2024",          "Medium",  "Monthly budget variance reports are being submitted to the Finance Committee an average of 15 working days after month-end, against a 5-day SLA.","Automate variance report generation from the finance system to eliminate manual compilation delays.","Finance Team","2026-04-28","In Progress"),
        ("FND-010","Staff handbook not updated in 18 months",     3,"HR Compliance Audit",           "Low",     "The staff handbook has not been updated since October 2024 and contains outdated references to superseded policies.","Assign a policy owner for the handbook with an annual review obligation and update immediately.","HR Manager","2026-06-01","Open"),
    ]
    c.executemany("""INSERT OR IGNORE INTO findings
        (finding_code,title,audit_id,audit_name,severity,description,recommendation,owner,due_date,status)
        VALUES (?,?,?,?,?,?,?,?,?,?)""", findings)

    # ── RISKS ──────────────────────────────────────────────────────────────
    risks = [
        ("RSK-001","Cybersecurity breach / ransomware attack on university systems","IT",          "IT Services",   4,5,"Enterprise firewall, endpoint protection (CrowdStrike), staff phishing training, penetration testing annually"),
        ("RSK-002","GDPR violation — student personal data exposure",               "Data",        "Registry",      3,5,"DPIAs conducted for new systems, encryption policy, DPO oversight, quarterly audits"),
        ("RSK-003","Financial fraud in research grants",                            "Finance",     "Finance",       3,4,"Dual authorisation controls, annual grant audits, UKRI compliance checks"),
        ("RSK-004","Health & Safety incident — campus safety failure",              "Safety",      "Estates",       2,5,"H&S Committee, annual inspections, PAT testing, fire risk assessments quarterly"),
        ("RSK-005","Academic misconduct — large-scale undetected plagiarism",       "Academic",    "Registry",      4,3,"Turnitin integration, academic integrity training, viva requirements for suspect submissions"),
        ("RSK-006","Reputational damage from adverse media coverage",               "Reputational","Communications",2,4,"Media policy, crisis communications plan, social media monitoring"),
        ("RSK-007","Supplier non-compliance with procurement policy",               "Procurement", "Finance",       3,3,"Supplier due diligence checks, contract compliance clauses, annual supplier audits"),
        ("RSK-008","Loss of key academic or senior staff",                          "HR",          "HR",            2,3,"Succession planning, retention programme, competitive benchmarking"),
        ("RSK-009","Failure to meet Office for Students registration conditions",   "Academic",    "Registry",      1,5,"OfS condition monitoring schedule, compliance reviews, legal counsel oversight"),
    ]
    c.executemany("""INSERT OR IGNORE INTO risks
        (risk_code,description,category,owner,likelihood,impact,mitigations)
        VALUES (?,?,?,?,?,?,?)""", risks)

    # ── POLICIES ───────────────────────────────────────────────────────────
    policies = [
        ("Data Protection & Privacy Policy","Data & Privacy","3.2","DPO",           "Annual",  "2025-04-01","2026-04-01","2023-09-01","Due Review","Governs the collection, processing, storage and disposal of personal data across the university"),
        ("GDPR Compliance Policy",          "Data & Privacy","2.1","DPO",           "Annual",  "2025-03-01","2026-04-04","2023-05-25","Overdue",   "Details obligations under UK GDPR and the Data Protection Act 2018 for all staff handling personal data"),
        ("Information Security Policy",     "IT Security",   "4.0","IT Director",   "Annual",  "2025-10-01","2026-10-01","2022-10-01","Current",   "Defines requirements for protecting university information assets from unauthorised access or disclosure"),
        ("Financial Regulations",           "Finance",       "5.1","CFO",           "Annual",  "2026-01-01","2027-01-01","2019-08-01","Current",   "Sets out financial management framework including delegated authorities, procurement thresholds and reporting"),
        ("Anti-Bribery & Corruption Policy","Finance",       "2.0","Finance",       "Annual",  "2025-06-01","2026-06-01","2021-06-01","Current",   "Prohibits bribery and corruption in all university activities and sets out reporting procedures"),
        ("Procurement Policy",              "Finance",       "3.0","Procurement",   "Annual",  "2026-02-01","2027-02-01","2020-09-01","Current",   "Governs the procurement of goods and services including supplier selection and contract management"),
        ("Equality, Diversity & Inclusion Policy","HR",      "4.2","HR Director",   "Annual",  "2024-09-01","2025-09-01","2017-10-01","Due Review","Sets out the university's commitment to equality and the elimination of unlawful discrimination"),
        ("Health & Safety Policy",          "Health & Safety","6.0","H&S Manager",  "Annual",  "2026-01-01","2027-01-01","2018-01-01","Current",   "Defines responsibilities for health and safety across all university premises and activities"),
        ("Academic Integrity Policy",       "Academic",      "3.1","Registry",      "Annual",  "2025-08-01","2026-08-01","2019-09-01","Current",   "Defines academic misconduct including plagiarism and sets out investigation and penalty procedures"),
        ("Research Ethics Policy",          "Academic",      "2.3","Research Office","Annual", "2025-11-01","2026-11-01","2020-01-01","Current",   "Governs the ethical conduct of research involving human participants, animals and sensitive data"),
        ("Whistleblowing Policy",           "HR",            "1.5","HR Director",   "Annual",  "2025-07-01","2026-07-01","2020-04-01","Current",   "Provides a confidential mechanism for staff to report suspected wrongdoing without fear of retaliation"),
        ("IT Acceptable Use Policy",        "IT Security",   "3.0","IT Director",   "Annual",  "2025-12-01","2026-12-01","2021-09-01","Under Review","Defines acceptable use of university IT systems, networks and data for all staff and students"),
        ("Records Management Policy",       "Data & Privacy","2.0","DPO",           "Annual",  "2025-05-01","2026-05-01","2022-05-01","Current",   "Governs the creation, maintenance, retention and disposal of university records in all formats"),
        ("Safeguarding Policy",             "HR",            "4.1","Safeguarding Lead","Annual","2025-09-01","2026-09-01","2018-09-01","Current",   "Sets out the university's duty of care for vulnerable individuals and reporting obligations"),
    ]
    c.executemany("""INSERT OR IGNORE INTO policies
        (name,category,version,owner,review_frequency,last_review,next_review,effective_date,status,summary)
        VALUES (?,?,?,?,?,?,?,?,?,?)""", policies)

    # ── CHECKLIST ──────────────────────────────────────────────────────────
    checklist = [
        ("Data subject access request (DSAR) process documented and tested",         "GDPR Art. 15"),
        ("Annual staff data protection training completed for all departments",       "All Departments"),
        ("Data Protection Impact Assessments (DPIAs) conducted for new systems",     "GDPR Art. 35"),
        ("Privacy notices updated and publicly accessible on website",               "GDPR Art. 13 & 14"),
        ("Information security risk assessment completed and documented",             "ISO 27001"),
        ("Business continuity plan reviewed and tested this year",                   "Estates & IT"),
        ("Student records retention schedule reviewed and adhered to",               "Registry"),
        ("Equality monitoring data collected, analysed and reported",                "Equality Act 2010"),
        ("Safeguarding training completed for all designated staff",                 "Mandatory"),
        ("Financial controls self-assessment submitted to audit committee",           "Financial Regulations"),
    ]
    c.executemany("INSERT OR IGNORE INTO checklist_items (title,reference) VALUES (?,?)", checklist)

    # ── NOTIFICATIONS ──────────────────────────────────────────────────────
    notifs = [
        ("Financial Audit 2024 — 3 new findings added",           "warning"),
        ("GDPR Policy review overdue — action required",           "danger"),
        ("Risk assessment for IT Security completed",              "success"),
        ("Compliance score updated: 81% → 84%",                    "info"),
    ]
    c.executemany("INSERT OR IGNORE INTO notifications (message,type) VALUES (?,?)", notifs)

    conn.commit()
    conn.close()
    print("[DB] Seed data inserted.")


if __name__ == "__main__":
    init_db()
    seed_db()
    print("[DB] Database ready at:", DB_PATH)
