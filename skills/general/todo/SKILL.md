---
name: todo
description: Manage a local task list (projects + tasks in SQLite) from natural language. Use when the user wants to add, list, start, finish, update or delete a task, asks what they need to do today or this week, what is overdue, what is in progress, what they completed this week, or asks to see tasks for a project. Phrases like "add X to Y", "I started X", "I finished X", "mark 12 as done", "what am I working on", "show my Music Bible tasks" trigger it. Always goes through scripts/todo.py, never touches the database directly.
---

# Todo

Translate what the user says about their tasks into calls to `scripts/todo.py`, then summarize the result. Commands below are shown as `todo.py ...`; always prefix them with the venv interpreter (see Setup).

Resolve paths relative to this SKILL.md. The database lives at `~/.todo/todo.db` (override with `TODO_DB`) and is created on first run with a default `Personal` project.

## Setup and check

The script must run inside its own venv at `scripts/.venv`, never the global interpreter. Before the first command of a session:

1. Check the venv exists: `test -x scripts/.venv/bin/python`.
2. If it does not, run `bash scripts/setup.sh`. It creates the venv, installs `scripts/requirements.txt` into it, and prints `ok: python X, sqlite Y`. Tell the user it was created.
3. Run every command as `scripts/.venv/bin/python scripts/todo.py ...`. Do not use `python3 scripts/todo.py`.

If `setup.sh` fails, show the error and stop. Common cause is `python3` missing from PATH.

## CLI

```bash
todo.py add "Title" [--project NAME] [--due DATE] [--status S] [--desc TEXT]   # project defaults to Personal, created if missing
todo.py list [--project NAME] [--status S] [--search TEXT] [--all] # open tasks grouped by project; --all includes done
todo.py today                      # open tasks due today, plus overdue
todo.py week                       # open tasks due this week (Mon-Sun), plus overdue
todo.py overdue
todo.py completed                  # tasks marked done this week
todo.py find TEXT                  # title search across all statuses, one line per task with project
todo.py start ID [ID...]           # -> in_progress
todo.py done ID [ID...]            # -> done
todo.py show ID                    # one task with its description and timestamps
todo.py update ID [--title T] [--status S] [--due DATE|none] [--project NAME] [--desc TEXT|""]
todo.py delete ID                  # permanent
todo.py projects                   # projects with counts per status
todo.py add-project NAME [--desc TEXT]
todo.py update-project NAME [--rename NEW] [--desc TEXT|""]
```

Statuses are `backlog`, `in_progress`, `done`. `DATE` accepts `YYYY-MM-DD`, `today`, `tomorrow`, `yesterday`, a weekday name (next occurrence, e.g. `friday`), or `next <weekday>` (that day of next week). `--desc` is an optional short description (max 255 chars) on both tasks and projects; pass `--desc ""` to clear one. Project names match case-insensitively, so "music bible" and "Music Bible" are the same project.

## Mapping requests to commands

| User says | Run |
| --- | --- |
| "Add fix login bug to Music Bible" | `add "Fix login bug" --project "Music Bible"` |
| "Add buy groceries" (no project, personal-sounding) | `add "Buy groceries"` |
| "... by Friday" / "due tomorrow" | append `--due friday` / `--due tomorrow` |
| "What do I need to do this week?" | `week` |
| "What's on today?" | `today` |
| "What's overdue?" | `overdue` |
| "What am I working on?" / "What's in progress?" | `list --status in_progress` |
| "Show me my Music Bible tasks" | `list --project "Music Bible"` |
| "Show everything" / "all tasks" | `list --all` |
| "What have I completed this week?" | `completed` |
| "Mark task 12 as done" | `done 12` |
| "Move task 5 to in progress" | `start 5` |
| "I started X" / "I finished X" | `find X`, then `start ID` / `done ID` (see matching rules) |
| "Rename 7 to ..." / "push 7 to Monday" / "move 7 to Work" | `update 7 --title ...` / `--due monday` / `--project Work` |
| "Add X to Y, it's about Z" / "describe 7 as ..." | `add "X" --project "Y" --desc "Z"` / `update 7 --desc "..."` |
| "Tell me more about task 7" | `show 7` |
| "Create project Work for client stuff" | `add-project Work --desc "client stuff"` |
| "Delete task 9" | `delete 9` |
| "What projects do I have?" | `projects` |

"Add X to Y" means title X in project Y. Unknown projects are created automatically by the CLI; say so when it happens. If the user names no project, use `Personal` (the CLI default).

## Matching tasks by name

When the user refers to a task by words rather than ID, run `find` with a distinctive fragment of the name.

- Exactly one open match: act on it and confirm with the ID.
- Several matches: show them and ask which one. Do not guess.
- No match: say so and offer to add it.

## Rules

- Always modify data through the CLI. Never open or edit the SQLite file directly.
- Never delete unless the user explicitly asks to delete. "Done" and "finished" mean `done`, not `delete`.
- Fix spelling, capitalization and grammar in titles and descriptions before saving ("fix login bugg on mobil" becomes "Fix login bug on mobile"). Keep the user's wording and sentence structure; do not rephrase, reorder, shorten or expand.
- Do not invent due dates or descriptions. Pass `--due` / `--desc` only when the user gave them. Descriptions are for extra context the user states; the title stays short.
- Keep answers short. Relay the CLI's output, which already shows IDs, status and due dates grouped by project. Add at most a sentence of summary.
- Show IDs so the user can refer to tasks later.
- The `week` and `today` views already include overdue tasks; do not re-query for them.
- Quote titles and project names with double quotes in the shell call.

## Out of scope for v1

No tags, subtasks, priorities, reminders, recurring tasks, sync, server or UI. If the user asks for one of these, say it is not supported rather than faking it with the title field.
