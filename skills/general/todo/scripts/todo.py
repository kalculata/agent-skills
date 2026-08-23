#!/usr/bin/env python3
"""Local task list backed by SQLite. Run `todo.py -h` for commands."""

import argparse
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta

DB_PATH = os.environ.get("TODO_DB", os.path.expanduser("~/.todo/todo.db"))
STATUSES = ("backlog", "in_progress", "done")
DEFAULT_PROJECT = "Personal"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS projects_name_ci ON projects (lower(name));
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'backlog'
        CHECK (status IN ('backlog', 'in_progress', 'done')),
    due_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def now():
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    db.execute(
        "INSERT INTO projects (name, created_at) SELECT ?, ? "
        "WHERE NOT EXISTS (SELECT 1 FROM projects WHERE lower(name) = lower(?))",
        (DEFAULT_PROJECT, now(), DEFAULT_PROJECT),
    )
    db.commit()
    return db


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


# ---------- dates ----------

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def parse_date(text):
    """Accept YYYY-MM-DD, today, tomorrow, yesterday, a weekday name (next occurrence),
    'next <weekday>' (the occurrence in next week), or 'none' to clear."""
    if text is None:
        return None
    t = text.strip().lower()
    if t in ("", "none", "clear"):
        return ""
    today = date.today()
    if t == "today":
        return today.isoformat()
    if t == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    if t == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    m = re.fullmatch(r"(?:(next|this)\s+)?([a-z]{3,})", t)
    if m:
        matches = [i for i, d in enumerate(WEEKDAYS) if d.startswith(m.group(2))]
        if matches:
            target = matches[0]
            if m.group(1) == "next":
                next_monday = today + timedelta(days=7 - today.weekday())
                return (next_monday + timedelta(days=target)).isoformat()
            ahead = (target - today.weekday()) % 7 or 7
            return (today + timedelta(days=ahead)).isoformat()
    try:
        return datetime.strptime(t, "%Y-%m-%d").date().isoformat()
    except ValueError:
        die(f"cannot parse date '{text}' (use YYYY-MM-DD, today, tomorrow, or a weekday)")


def week_bounds():
    today = date.today()
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


# ---------- projects ----------

def get_project(db, name):
    return db.execute(
        "SELECT * FROM projects WHERE lower(name) = lower(?)", (name.strip(),)
    ).fetchone()


def get_or_create_project(db, name):
    row = get_project(db, name)
    if row:
        return row
    db.execute(
        "INSERT INTO projects (name, created_at) VALUES (?, ?)", (name.strip(), now())
    )
    db.commit()
    print(f"created project '{name.strip()}'")
    return get_project(db, name)


# ---------- output ----------

def fmt_task(t, with_project=False):
    parts = [f"#{t['id']:<4}", f"[{t['status']}]".ljust(13), t["title"]]
    if t["due_date"]:
        tag = "due"
        if t["status"] != "done" and t["due_date"] < date.today().isoformat():
            tag = "OVERDUE"
        parts.append(f"({tag} {t['due_date']})")
    if with_project:
        parts.append(f"· {t['project']}")
    return " ".join(parts)


def print_tasks(rows, group=True, empty="no tasks"):
    rows = list(rows)
    if not rows:
        print(empty)
        return
    if not group:
        for t in rows:
            print(fmt_task(t, with_project=True))
        return
    current = None
    for t in rows:
        if t["project"] != current:
            current = t["project"]
            print(f"\n{current}")
        print("  " + fmt_task(t))


def query_tasks(db, where="1=1", params=(), order="t.due_date IS NULL, t.due_date, t.id"):
    return db.execute(
        f"""SELECT t.*, p.name AS project FROM tasks t
            JOIN projects p ON p.id = t.project_id
            WHERE {where} ORDER BY p.name COLLATE NOCASE, {order}""",
        params,
    ).fetchall()


def get_task(db, task_id):
    row = query_tasks(db, "t.id = ?", (task_id,))
    if not row:
        die(f"no task with id {task_id}")
    return row[0]


# ---------- commands ----------

def cmd_add(db, a):
    project = get_or_create_project(db, a.project)
    due = parse_date(a.due) or None
    ts = now()
    cur = db.execute(
        "INSERT INTO tasks (project_id, title, status, due_date, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (project["id"], a.title.strip(), a.status, due, ts, ts),
    )
    db.commit()
    print("added " + fmt_task(get_task(db, cur.lastrowid), with_project=True))


def cmd_list(db, a):
    clauses, params = [], []
    if a.project:
        p = get_project(db, a.project)
        if not p:
            die(f"no project named '{a.project}'")
        clauses.append("t.project_id = ?")
        params.append(p["id"])
    if a.status:
        clauses.append("t.status = ?")
        params.append(a.status)
    elif not a.all:
        clauses.append("t.status != 'done'")
    if a.search:
        clauses.append("t.title LIKE ?")
        params.append(f"%{a.search}%")
    print_tasks(query_tasks(db, " AND ".join(clauses) or "1=1", params))


def cmd_today(db, a):
    today = date.today().isoformat()
    print_tasks(
        query_tasks(db, "t.status != 'done' AND t.due_date <= ?", (today,)),
        empty="nothing due today",
    )


def cmd_week(db, a):
    start, end = week_bounds()
    print(f"week {start} to {end} (plus overdue)")
    print_tasks(
        query_tasks(db, "t.status != 'done' AND t.due_date <= ?", (end.isoformat(),)),
        empty="nothing due this week",
    )


def cmd_overdue(db, a):
    today = date.today().isoformat()
    print_tasks(
        query_tasks(db, "t.status != 'done' AND t.due_date < ?", (today,)),
        empty="nothing overdue",
    )


def cmd_completed(db, a):
    """Tasks marked done this week (updated_at is the completion time)."""
    start, _ = week_bounds()
    print_tasks(
        query_tasks(db, "t.status = 'done' AND t.updated_at >= ?", (start.isoformat(),),
                    order="t.updated_at DESC"),
        empty="nothing completed this week",
    )


def cmd_find(db, a):
    print_tasks(
        query_tasks(db, "t.title LIKE ?", (f"%{a.text}%",)), group=False,
        empty=f"no tasks matching '{a.text}'",
    )


def set_status(db, task_id, status):
    get_task(db, task_id)
    db.execute(
        "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, now(), task_id)
    )
    db.commit()
    print(fmt_task(get_task(db, task_id), with_project=True))


def cmd_done(db, a):
    for tid in a.ids:
        set_status(db, tid, "done")


def cmd_start(db, a):
    for tid in a.ids:
        set_status(db, tid, "in_progress")


def cmd_update(db, a):
    get_task(db, a.id)
    sets, params = [], []
    if a.title is not None:
        sets.append("title = ?"); params.append(a.title.strip())
    if a.status is not None:
        sets.append("status = ?"); params.append(a.status)
    if a.due is not None:
        sets.append("due_date = ?"); params.append(parse_date(a.due) or None)
    if a.project is not None:
        sets.append("project_id = ?"); params.append(get_or_create_project(db, a.project)["id"])
    if not sets:
        die("nothing to update (use --title, --status, --due, --project)")
    sets.append("updated_at = ?"); params.append(now())
    params.append(a.id)
    db.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", params)
    db.commit()
    print(fmt_task(get_task(db, a.id), with_project=True))


def cmd_delete(db, a):
    t = get_task(db, a.id)
    db.execute("DELETE FROM tasks WHERE id = ?", (a.id,))
    db.commit()
    print("deleted " + fmt_task(t, with_project=True))


def cmd_projects(db, a):
    rows = db.execute(
        """SELECT p.name,
                  SUM(t.status = 'backlog') AS backlog,
                  SUM(t.status = 'in_progress') AS in_progress,
                  SUM(t.status = 'done') AS done
           FROM projects p LEFT JOIN tasks t ON t.project_id = p.id
           GROUP BY p.id ORDER BY p.name COLLATE NOCASE"""
    ).fetchall()
    for r in rows:
        print(f"{r['name']:<24} backlog {r['backlog'] or 0:>3}  "
              f"in_progress {r['in_progress'] or 0:>3}  done {r['done'] or 0:>3}")


def cmd_add_project(db, a):
    if get_project(db, a.name):
        die(f"project '{a.name}' already exists")
    get_or_create_project(db, a.name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("add", help="add a task")
    s.add_argument("title")
    s.add_argument("--project", "-p", default=DEFAULT_PROJECT)
    s.add_argument("--due", "-d", help="YYYY-MM-DD, today, tomorrow, friday, 'next monday'")
    s.add_argument("--status", "-s", choices=STATUSES, default="backlog")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("list", help="list open tasks (grouped by project)")
    s.add_argument("--project", "-p")
    s.add_argument("--status", "-s", choices=STATUSES)
    s.add_argument("--search", help="substring match on title")
    s.add_argument("--all", "-a", action="store_true", help="include done tasks")
    s.set_defaults(fn=cmd_list)

    sub.add_parser("today", help="open tasks due today or overdue").set_defaults(fn=cmd_today)
    sub.add_parser("week", help="open tasks due this week or overdue").set_defaults(fn=cmd_week)
    sub.add_parser("overdue", help="open tasks past their due date").set_defaults(fn=cmd_overdue)
    sub.add_parser("completed", help="tasks marked done this week").set_defaults(fn=cmd_completed)

    s = sub.add_parser("find", help="search tasks by title (any status)")
    s.add_argument("text")
    s.set_defaults(fn=cmd_find)

    s = sub.add_parser("done", help="mark task(s) done")
    s.add_argument("ids", type=int, nargs="+")
    s.set_defaults(fn=cmd_done)

    s = sub.add_parser("start", help="move task(s) to in_progress")
    s.add_argument("ids", type=int, nargs="+")
    s.set_defaults(fn=cmd_start)

    s = sub.add_parser("update", help="change title, status, due date or project")
    s.add_argument("id", type=int)
    s.add_argument("--title", "-t")
    s.add_argument("--status", "-s", choices=STATUSES)
    s.add_argument("--due", "-d", help="date, or 'none' to clear")
    s.add_argument("--project", "-p")
    s.set_defaults(fn=cmd_update)

    s = sub.add_parser("delete", help="delete a task permanently")
    s.add_argument("id", type=int)
    s.set_defaults(fn=cmd_delete)

    sub.add_parser("projects", help="list projects with task counts").set_defaults(fn=cmd_projects)

    s = sub.add_parser("add-project", help="create an empty project")
    s.add_argument("name")
    s.set_defaults(fn=cmd_add_project)

    a = p.parse_args()
    a.fn(connect(), a)


if __name__ == "__main__":
    main()
