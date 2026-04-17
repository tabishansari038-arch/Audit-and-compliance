"""
app.py — Flask REST API Backend
University Audit & Compliance Portal — Greenfield University

Endpoints:
  GET/POST   /api/audits
  GET/PUT/DELETE /api/audits/<id>
  GET/POST   /api/findings
  GET/PUT/DELETE /api/findings/<id>
  GET/POST   /api/risks
  GET/PUT/DELETE /api/risks/<id>
  GET/POST   /api/policies
  GET/PUT/DELETE /api/policies/<id>
  GET        /api/checklist
  PUT        /api/checklist/<id>
  GET        /api/notifications
  PUT        /api/notifications/<id>/read
  PUT        /api/notifications/read-all
  GET        /api/dashboard/stats
  GET        /api/dashboard/compliance-trend
  GET        /api/dashboard/dept-scores
"""

import json
import os
import sqlite3
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template, send_from_directory

from database import init_db, seed_db, get_db

app = Flask(__name__, template_folder="templates", static_folder="static")


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def next_code(prefix, table, col):
    """Generate next sequential code e.g. AUD-013"""
    conn = get_db()
    c = conn.cursor()
    c.execute(f"SELECT MAX(CAST(SUBSTR({col}, {len(prefix)+2}) AS INTEGER)) FROM {table}")
    row = c.fetchone()[0]
    conn.close()
    num = (row or 0) + 1
    return f"{prefix}-{num:03d}"

def jsonify_rows(rows, **kwargs):
    return jsonify({"data": rows_to_list(rows), **kwargs})

def error(msg, code=400):
    return jsonify({"error": msg}), code

def ok(msg="Success", **kwargs):
    return jsonify({"message": msg, **kwargs})


# ═══════════════════════════════════════════════════════════════════
# FRONTEND ROUTE — serve the single-page app
# ═══════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/dashboard/stats")
def dashboard_stats():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM audits WHERE status IN ('In Progress','Pending')")
    active_audits = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM findings WHERE status != 'Resolved'")
    open_findings = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM findings WHERE status != 'Resolved' AND severity='Critical'")
    critical_findings = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM findings WHERE status != 'Resolved' AND severity='High'")
    high_findings = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM policies WHERE status IN ('Due Review','Overdue')")
    policies_due = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM policies WHERE status='Overdue'")
    policies_overdue = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM audits WHERE status='Overdue'")
    overdue_audits = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM audits WHERE status='Completed'")
    completed_audits = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM audits")
    total_audits = c.fetchone()[0]

    # Compliance score: average of completed audit scores
    c.execute("SELECT AVG(score) FROM audits WHERE status='Completed' AND score IS NOT NULL")
    avg_score = c.fetchone()[0]
    compliance_score = round(avg_score, 1) if avg_score else 84.0

    # Audit status distribution
    c.execute("""SELECT status, COUNT(*) as cnt FROM audits GROUP BY status""")
    audit_dist = {r["status"]: r["cnt"] for r in c.fetchall()}

    # Upcoming deadlines
    c.execute("""
        SELECT 'audit' as item_type, name as item, due_date, status 
        FROM audits WHERE status NOT IN ('Completed') AND due_date IS NOT NULL
        UNION ALL
        SELECT 'policy' as item_type, name as item, next_review as due_date, status
        FROM policies WHERE status IN ('Due Review','Overdue','Under Review')
        ORDER BY due_date ASC LIMIT 8
    """)
    deadlines = rows_to_list(c.fetchall())

    # Recent activity (findings + audit updates)
    c.execute("""
        SELECT 'finding' as type, title as text, status, severity, created_at as ts FROM findings
        UNION ALL
        SELECT 'audit' as type, name as text, status, priority as severity, updated_at as ts FROM audits
        ORDER BY ts DESC LIMIT 8
    """)
    activity = rows_to_list(c.fetchall())

    conn.close()

    return jsonify({
        "compliance_score": compliance_score,
        "active_audits": active_audits,
        "open_findings": open_findings,
        "critical_findings": critical_findings,
        "high_findings": high_findings,
        "policies_due": policies_due,
        "policies_overdue": policies_overdue,
        "overdue_audits": overdue_audits,
        "completed_audits": completed_audits,
        "total_audits": total_audits,
        "audit_distribution": audit_dist,
        "upcoming_deadlines": deadlines,
        "recent_activity": activity,
    })


@app.route("/api/dashboard/dept-scores")
def dept_scores():
    """Per-department compliance scores derived from completed audits"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT department, ROUND(AVG(score),1) as avg_score, COUNT(*) as audits
        FROM audits
        WHERE status='Completed' AND score IS NOT NULL
        GROUP BY department
        ORDER BY avg_score DESC
    """)
    rows = rows_to_list(c.fetchall())
    conn.close()
    # Fill in depts with no completed audits with default
    defaults = {"Finance":72,"IT Services":68,"Human Resources":91,
                "Research Office":88,"Registry":79,"Estates":85,"Library":76}
    result = []
    seen = {r["department"] for r in rows}
    for r in rows:
        result.append(r)
    for dept, score in defaults.items():
        if dept not in seen:
            result.append({"department": dept, "avg_score": score, "audits": 0})
    return jsonify({"data": result})


@app.route("/api/dashboard/compliance-trend")
def compliance_trend():
    """Monthly compliance trend — last 7 months"""
    trend = [
        {"month": "Oct 2025", "score": 73},
        {"month": "Nov 2025", "score": 78},
        {"month": "Dec 2025", "score": 76},
        {"month": "Jan 2026", "score": 80},
        {"month": "Feb 2026", "score": 81},
        {"month": "Mar 2026", "score": 82},
        {"month": "Apr 2026", "score": 84},
    ]
    return jsonify({"data": trend})


# ═══════════════════════════════════════════════════════════════════
# AUDITS API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/audits", methods=["GET"])
def get_audits():
    conn = get_db()
    c = conn.cursor()
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    audit_type = request.args.get("type", "")
    department = request.args.get("department", "")

    query = "SELECT * FROM audits WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR type LIKE ? OR department LIKE ? OR lead_auditor LIKE ?)"
        params += [f"%{search}%"] * 4
    if status:
        query += " AND status=?"
        params.append(status)
    if audit_type:
        query += " AND type=?"
        params.append(audit_type)
    if department:
        query += " AND department=?"
        params.append(department)
    query += " ORDER BY created_at DESC"

    c.execute(query, params)
    rows = rows_to_list(c.fetchall())

    # Summary counts
    c.execute("SELECT status, COUNT(*) as cnt FROM audits GROUP BY status")
    counts = {r["status"]: r["cnt"] for r in c.fetchall()}
    conn.close()
    return jsonify({"data": rows, "counts": counts})


@app.route("/api/audits/<int:audit_id>", methods=["GET"])
def get_audit(audit_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM audits WHERE id=?", (audit_id,))
    audit = row_to_dict(c.fetchone())
    if not audit:
        conn.close()
        return error("Audit not found", 404)
    # Also fetch findings for this audit
    c.execute("SELECT * FROM findings WHERE audit_id=? ORDER BY created_at DESC", (audit_id,))
    audit["findings"] = rows_to_list(c.fetchall())
    conn.close()
    return jsonify(audit)


@app.route("/api/audits", methods=["POST"])
def create_audit():
    data = request.get_json()
    required = ["name", "type", "department", "lead_auditor"]
    for f in required:
        if not data.get(f):
            return error(f"Field '{f}' is required")

    code = next_code("AUD", "audits", "audit_code")
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO audits
        (audit_code,name,type,department,lead_auditor,start_date,due_date,status,priority,scope,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        code, data["name"], data["type"], data["department"],
        data["lead_auditor"], data.get("start_date"), data.get("due_date"),
        data.get("status", "Pending"), data.get("priority", "Medium"),
        data.get("scope"), now()
    ))
    new_id = c.lastrowid
    # Create notification
    c.execute("INSERT INTO notifications (message,type) VALUES (?,?)",
              (f"New audit created: {data['name']}", "info"))
    conn.commit()
    c.execute("SELECT * FROM audits WHERE id=?", (new_id,))
    result = row_to_dict(c.fetchone())
    conn.close()
    return jsonify(result), 201


@app.route("/api/audits/<int:audit_id>", methods=["PUT"])
def update_audit(audit_id):
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM audits WHERE id=?", (audit_id,))
    if not c.fetchone():
        conn.close()
        return error("Audit not found", 404)

    fields = ["name","type","department","lead_auditor","start_date","due_date","status","score","priority","scope"]
    updates = [(data[f], f) for f in fields if f in data]
    if not updates:
        conn.close()
        return error("No fields to update")

    for val, field in updates:
        c.execute(f"UPDATE audits SET {field}=?, updated_at=? WHERE id=?", (val, now(), audit_id))
    conn.commit()
    c.execute("SELECT * FROM audits WHERE id=?", (audit_id,))
    result = row_to_dict(c.fetchone())
    conn.close()
    return jsonify(result)


@app.route("/api/audits/<int:audit_id>", methods=["DELETE"])
def delete_audit(audit_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM audits WHERE id=?", (audit_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return error("Audit not found", 404)
    c.execute("DELETE FROM audits WHERE id=?", (audit_id,))
    conn.commit()
    conn.close()
    return ok(f"Audit '{row['name']}' deleted")


# ═══════════════════════════════════════════════════════════════════
# FINDINGS API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/findings", methods=["GET"])
def get_findings():
    conn = get_db()
    c = conn.cursor()
    search   = request.args.get("search", "")
    severity = request.args.get("severity", "")
    status   = request.args.get("status", "")
    audit_id = request.args.get("audit_id", "")

    query = "SELECT * FROM findings WHERE 1=1"
    params = []
    if search:
        query += " AND (title LIKE ? OR audit_name LIKE ? OR owner LIKE ?)"
        params += [f"%{search}%"] * 3
    if severity:
        query += " AND severity=?"
        params.append(severity)
    if status:
        query += " AND status=?"
        params.append(status)
    if audit_id:
        query += " AND audit_id=?"
        params.append(audit_id)
    query += " ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 ELSE 5 END, created_at DESC"

    c.execute(query, params)
    rows = rows_to_list(c.fetchall())

    # Counts by severity
    c.execute("SELECT severity, COUNT(*) as cnt FROM findings WHERE status!='Resolved' GROUP BY severity")
    sev_counts = {r["severity"]: r["cnt"] for r in c.fetchall()}
    conn.close()
    return jsonify({"data": rows, "severity_counts": sev_counts})


@app.route("/api/findings/<int:fid>", methods=["GET"])
def get_finding(fid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM findings WHERE id=?", (fid,))
    row = row_to_dict(c.fetchone())
    conn.close()
    if not row:
        return error("Finding not found", 404)
    return jsonify(row)


@app.route("/api/findings", methods=["POST"])
def create_finding():
    data = request.get_json()
    required = ["title", "severity", "owner"]
    for f in required:
        if not data.get(f):
            return error(f"Field '{f}' is required")

    code = next_code("FND", "findings", "finding_code")
    conn = get_db()
    c = conn.cursor()

    # Resolve audit_name from audit_id
    audit_name = data.get("audit_name", "")
    if data.get("audit_id"):
        c.execute("SELECT name FROM audits WHERE id=?", (data["audit_id"],))
        row = c.fetchone()
        if row:
            audit_name = row["name"]

    c.execute("""INSERT INTO findings
        (finding_code,title,audit_id,audit_name,severity,description,recommendation,owner,due_date,status,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        code, data["title"], data.get("audit_id"), audit_name,
        data["severity"], data.get("description"), data.get("recommendation"),
        data["owner"], data.get("due_date"), data.get("status", "Open"), now()
    ))
    new_id = c.lastrowid
    c.execute("INSERT INTO notifications (message,type) VALUES (?,?)",
              (f"New {data['severity']} finding logged: {data['title']}", "warning" if data["severity"] in ("Critical","High") else "info"))
    conn.commit()
    c.execute("SELECT * FROM findings WHERE id=?", (new_id,))
    result = row_to_dict(c.fetchone())
    conn.close()
    return jsonify(result), 201


@app.route("/api/findings/<int:fid>", methods=["PUT"])
def update_finding(fid):
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM findings WHERE id=?", (fid,))
    if not c.fetchone():
        conn.close()
        return error("Finding not found", 404)

    fields = ["title","audit_id","audit_name","severity","description","recommendation","owner","due_date","status"]
    for field in fields:
        if field in data:
            c.execute(f"UPDATE findings SET {field}=?, updated_at=? WHERE id=?", (data[field], now(), fid))
    conn.commit()
    c.execute("SELECT * FROM findings WHERE id=?", (fid,))
    result = row_to_dict(c.fetchone())
    conn.close()
    return jsonify(result)


@app.route("/api/findings/<int:fid>", methods=["DELETE"])
def delete_finding(fid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT title FROM findings WHERE id=?", (fid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return error("Finding not found", 404)
    c.execute("DELETE FROM findings WHERE id=?", (fid,))
    conn.commit()
    conn.close()
    return ok(f"Finding '{row['title']}' deleted")


# ═══════════════════════════════════════════════════════════════════
# RISKS API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/risks", methods=["GET"])
def get_risks():
    conn = get_db()
    c = conn.cursor()
    search   = request.args.get("search", "")
    category = request.args.get("category", "")
    status   = request.args.get("status", "")

    query = "SELECT * FROM risks WHERE 1=1"
    params = []
    if search:
        query += " AND (description LIKE ? OR category LIKE ? OR owner LIKE ?)"
        params += [f"%{search}%"] * 3
    if category:
        query += " AND category=?"
        params.append(category)
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY score DESC, created_at DESC"

    c.execute(query, params)
    rows = rows_to_list(c.fetchall())

    # Rating labels
    for r in rows:
        s = r["score"]
        r["rating"] = "Critical" if s >= 15 else "High" if s >= 8 else "Medium" if s >= 4 else "Low"

    # Summary counts
    c.execute("""
        SELECT
            SUM(CASE WHEN score>=15 THEN 1 ELSE 0 END) as critical,
            SUM(CASE WHEN score>=8 AND score<15 THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN score>=4 AND score<8 THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN score<4 THEN 1 ELSE 0 END) as low
        FROM risks
    """)
    summary = row_to_dict(c.fetchone())
    conn.close()
    return jsonify({"data": rows, "summary": summary})


@app.route("/api/risks/<int:rid>", methods=["GET"])
def get_risk(rid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM risks WHERE id=?", (rid,))
    row = row_to_dict(c.fetchone())
    conn.close()
    if not row:
        return error("Risk not found", 404)
    s = row["score"]
    row["rating"] = "Critical" if s >= 15 else "High" if s >= 8 else "Medium" if s >= 4 else "Low"
    return jsonify(row)


@app.route("/api/risks", methods=["POST"])
def create_risk():
    data = request.get_json()
    required = ["description", "category", "owner", "likelihood", "impact"]
    for f in required:
        if data.get(f) is None:
            return error(f"Field '{f}' is required")

    like = int(data["likelihood"])
    imp  = int(data["impact"])
    if not (1 <= like <= 5) or not (1 <= imp <= 5):
        return error("Likelihood and impact must be between 1 and 5")

    code = next_code("RSK", "risks", "risk_code")
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO risks
        (risk_code,description,category,owner,likelihood,impact,mitigations,status,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)""", (
        code, data["description"], data["category"], data["owner"],
        like, imp, data.get("mitigations"), data.get("status","Open"), now()
    ))
    new_id = c.lastrowid
    c.execute("SELECT * FROM risks WHERE id=?", (new_id,))
    result = row_to_dict(c.fetchone())
    result["rating"] = "Critical" if result["score"]>=15 else "High" if result["score"]>=8 else "Medium" if result["score"]>=4 else "Low"
    conn.commit()
    conn.close()
    return jsonify(result), 201


@app.route("/api/risks/<int:rid>", methods=["PUT"])
def update_risk(rid):
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM risks WHERE id=?", (rid,))
    if not c.fetchone():
        conn.close()
        return error("Risk not found", 404)
    fields = ["description","category","owner","likelihood","impact","mitigations","status"]
    for field in fields:
        if field in data:
            c.execute(f"UPDATE risks SET {field}=?, updated_at=? WHERE id=?", (data[field], now(), rid))
    conn.commit()
    c.execute("SELECT * FROM risks WHERE id=?", (rid,))
    result = row_to_dict(c.fetchone())
    result["rating"] = "Critical" if result["score"]>=15 else "High" if result["score"]>=8 else "Medium" if result["score"]>=4 else "Low"
    conn.close()
    return jsonify(result)


@app.route("/api/risks/<int:rid>", methods=["DELETE"])
def delete_risk(rid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT description FROM risks WHERE id=?", (rid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return error("Risk not found", 404)
    c.execute("DELETE FROM risks WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return ok("Risk deleted")


# ═══════════════════════════════════════════════════════════════════
# POLICIES API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/policies", methods=["GET"])
def get_policies():
    conn = get_db()
    c = conn.cursor()
    search   = request.args.get("search", "")
    category = request.args.get("category", "")
    status   = request.args.get("status", "")

    query = "SELECT * FROM policies WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR owner LIKE ? OR category LIKE ?)"
        params += [f"%{search}%"] * 3
    if category:
        query += " AND category=?"
        params.append(category)
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY CASE status WHEN 'Overdue' THEN 1 WHEN 'Due Review' THEN 2 WHEN 'Under Review' THEN 3 ELSE 4 END, name"

    c.execute(query, params)
    rows = rows_to_list(c.fetchall())
    conn.close()
    return jsonify({"data": rows})


@app.route("/api/policies", methods=["POST"])
def create_policy():
    data = request.get_json()
    required = ["name", "category", "owner"]
    for f in required:
        if not data.get(f):
            return error(f"Field '{f}' is required")
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO policies
        (name,category,version,owner,review_frequency,last_review,next_review,effective_date,status,summary,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
        data["name"], data["category"], data.get("version","1.0"), data["owner"],
        data.get("review_frequency","Annual"), data.get("last_review"),
        data.get("next_review"), data.get("effective_date"),
        data.get("status","Current"), data.get("summary"), now()
    ))
    new_id = c.lastrowid
    conn.commit()
    c.execute("SELECT * FROM policies WHERE id=?", (new_id,))
    result = row_to_dict(c.fetchone())
    conn.close()
    return jsonify(result), 201


@app.route("/api/policies/<int:pid>", methods=["PUT"])
def update_policy(pid):
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM policies WHERE id=?", (pid,))
    if not c.fetchone():
        conn.close()
        return error("Policy not found", 404)
    fields = ["name","category","version","owner","review_frequency","last_review","next_review","effective_date","status","summary"]
    for field in fields:
        if field in data:
            c.execute(f"UPDATE policies SET {field}=?, updated_at=? WHERE id=?", (data[field], now(), pid))
    conn.commit()
    c.execute("SELECT * FROM policies WHERE id=?", (pid,))
    result = row_to_dict(c.fetchone())
    conn.close()
    return jsonify(result)


@app.route("/api/policies/<int:pid>", methods=["DELETE"])
def delete_policy(pid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT name FROM policies WHERE id=?", (pid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return error("Policy not found", 404)
    c.execute("DELETE FROM policies WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return ok(f"Policy '{row['name']}' deleted")


# ═══════════════════════════════════════════════════════════════════
# CHECKLIST API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/checklist", methods=["GET"])
def get_checklist():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM checklist_items ORDER BY id")
    rows = rows_to_list(c.fetchall())
    c.execute("SELECT COUNT(*) FROM checklist_items WHERE is_checked=1")
    checked = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM checklist_items")
    total = c.fetchone()[0]
    conn.close()
    return jsonify({"data": rows, "checked": checked, "total": total})


@app.route("/api/checklist/<int:cid>", methods=["PUT"])
def toggle_checklist(cid):
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM checklist_items WHERE id=?", (cid,))
    row = row_to_dict(c.fetchone())
    if not row:
        conn.close()
        return error("Checklist item not found", 404)
    is_checked = 1 if data.get("is_checked") else 0
    checked_by = data.get("checked_by", "Dr. J. Mitchell") if is_checked else None
    checked_at = now() if is_checked else None
    c.execute("UPDATE checklist_items SET is_checked=?, checked_by=?, checked_at=? WHERE id=?",
              (is_checked, checked_by, checked_at, cid))
    conn.commit()
    c.execute("SELECT * FROM checklist_items WHERE id=?", (cid,))
    result = row_to_dict(c.fetchone())
    conn.close()
    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════
# NOTIFICATIONS API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 20")
    rows = rows_to_list(c.fetchall())
    c.execute("SELECT COUNT(*) FROM notifications WHERE is_read=0")
    unread = c.fetchone()[0]
    conn.close()
    return jsonify({"data": rows, "unread": unread})


@app.route("/api/notifications/<int:nid>/read", methods=["PUT"])
def mark_notification_read(nid):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE notifications SET is_read=1 WHERE id=?", (nid,))
    conn.commit()
    conn.close()
    return ok("Marked as read")


@app.route("/api/notifications/read-all", methods=["PUT"])
def mark_all_read():
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE notifications SET is_read=1")
    conn.commit()
    conn.close()
    return ok("All notifications marked as read")


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE FRAMEWORKS API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/compliance/frameworks")
def get_frameworks():
    """Static framework compliance scores"""
    frameworks = [
        {"name": "GDPR / UK GDPR",           "score": 78,  "status": "Partial"},
        {"name": "ISO 27001",                  "score": 91,  "status": "Compliant"},
        {"name": "QAA Standards",              "score": 95,  "status": "Compliant"},
        {"name": "Office for Students",        "score": 88,  "status": "Compliant"},
        {"name": "Equality Act 2010",          "score": 72,  "status": "Partial"},
        {"name": "Health & Safety at Work Act","score": 87,  "status": "Compliant"},
    ]
    total = len(frameworks)
    compliant = sum(1 for f in frameworks if f["status"] == "Compliant")
    partial    = sum(1 for f in frameworks if f["status"] == "Partial")
    overall   = round(sum(f["score"] for f in frameworks) / total, 1)
    return jsonify({"data": frameworks, "overall": overall, "compliant": compliant, "partial": partial})


# ═══════════════════════════════════════════════════════════════════
# REPORTS API
# ═══════════════════════════════════════════════════════════════════

@app.route("/api/reports", methods=["GET"])
def get_reports():
    reports = [
        {"id":1,"name":"Q1 2026 Compliance Summary",         "type":"Compliance","generated":"Apr 1, 2026","period":"Jan–Mar 2026","formats":"PDF, Excel"},
        {"id":2,"name":"Financial Audit Interim Report",      "type":"Audit",     "generated":"Mar 15, 2026","period":"FY 2024–25","formats":"PDF"},
        {"id":3,"name":"Annual Risk Assessment 2025",          "type":"Risk",      "generated":"Feb 28, 2026","period":"AY 2025","formats":"PDF, Word"},
        {"id":4,"name":"HR Compliance Audit Report",          "type":"Completed", "generated":"Apr 10, 2026","period":"AY 2024–25","formats":"PDF"},
        {"id":5,"name":"Policy Register Summary",             "type":"Policy",    "generated":"Mar 31, 2026","period":"Mar 2026","formats":"PDF, Excel"},
        {"id":6,"name":"Research Ethics Audit Report",        "type":"Completed", "generated":"Mar 30, 2026","period":"AY 2024–25","formats":"PDF"},
    ]
    return jsonify({"data": reports})


@app.route("/api/reports/generate", methods=["POST"])
def generate_report():
    data = request.get_json()
    report_type = data.get("report_type", "Compliance Summary Report")
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO notifications (message,type) VALUES (?,?)",
              (f"Report '{report_type}' is being generated and will be ready shortly.", "info"))
    conn.commit()
    conn.close()
    return ok(f"Report generation started: {report_type}", report_type=report_type)


# ═══════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("[APP] Initialising database…")
    init_db()
    seed_db()
    print("[APP] Starting Flask server on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
