---
name: create-linear-task
description: >-
  Create a Linear task from whatever the user hands over: a sentence, a pasted
  message, a screenshot, a link. Uses the Linear MCP server to pick the team,
  project, milestone, labels and estimate from what similar recent issues in
  that project use, asks only the clarifying questions that change the issue,
  writes a short professional title and description, splits work that belongs
  to another repo or project into sub-issues (tiny follow-ups become checkboxes
  in the description instead), shows the full draft, and creates the issue
  only after the user confirms. Use when the user asks to create, open, file,
  add or write a Linear task/issue/ticket, or says "make a ticket for this".
---

# Create Linear Task

Turn a rough request into a Linear issue a teammate can pick up without asking questions. The deliverable is one created issue (plus sub-issues when the work spans repos or projects), written short and precise, created only after the user has seen the draft and said yes.

## Before you start

- You need the Linear MCP server (`mcp__linear-server__*` tools). If its tools are unavailable, stop and tell the user to connect Linear.
- Read-only until the very end. Listing teams, projects, milestones, labels and issues is fine. `save_issue` runs once per issue, and only after the user confirms the draft.
- Never set assignee, state or due date unless the user asks for it.
- Write for a professional. The reader knows the product and the codebase. Do not explain what they already know, do not pad, do not repeat the title in the description.

## 1. Understand the request

The input can be text, a pasted chat message, a screenshot, a URL, or a mix. Read all of it before writing anything.

- **Screenshots**: describe what is wrong or wanted in words. Attach the image only if it carries information the words cannot.
- **Links** (PR, Slack thread, doc, Sentry event): fetch and read them when you can. Keep the URL for the description's references.
- Pull out: the problem or goal, where it shows up (screen, endpoint, repo), what "done" looks like, and anything that constrains the fix.

Ask clarifying questions **only** when the answer changes the issue: which product or repo, expected vs actual behavior when both are unclear, whether something is a bug or a feature request, scope when two readings lead to different work. Batch the questions in one message. Do not ask about things you can look up (project names, labels, estimate scale) or things that do not matter for the ticket.

## 2. Pick where it lives

Look the fields up instead of guessing:

1. **Team**: `list_teams`. If there is one team, use it. Otherwise pick from the repo or product the request names, and confirm if unsure.
2. **Project**: use the one the user named. If they did not, `list_projects` for the team and choose the project whose name or summary matches the request. Two plausible candidates means one clarifying question, not a guess.
3. **Recent issues in that project**: `list_issues` filtered by project, newest first, 10 to 20 of them. Use them to copy conventions:
   - **Milestone**: if the recent open issues share a milestone, or milestones follow an obvious sequence (`list_milestones`), use the current one. No pattern means no milestone.
   - **Labels**: `list_issue_labels` for the team. Apply the ones the project uses for this kind of work (`Bug`, `Feature`, area labels). One to three labels. None is fine.
   - **Estimate**: read the scale from recent issues (Fibonacci, linear, T-shirt as points). Size the new issue relative to comparable ones. Skip the estimate only if the team does not use them.
   - **Title style**: match how titles are phrased in that project.
4. **Priority**: leave it at None unless the user says it is urgent or the input makes that obvious (production down, data loss).

## 3. Write the title and description

**Title.** One line, imperative, specific, under about 70 characters. Name the thing and the change: "Fix duplicate push notifications after app resume", not "Notifications bug". No issue prefix, no trailing period.

**Description.** Markdown. Short. Every line must tell the implementer something they need. Use this shape and drop any section that would be empty:

```markdown
CONTEXT: one or two sentences on why this exists. Current behavior for a bug, the goal for a feature.

## What to do
- The concrete change(s), one per line.

## Acceptance criteria
- [ ] Checkable statement of done
- [ ] Another one

## References
- Link, with a few words on what it is
```

Rules:

- Bugs get steps to reproduce, expected and actual, in the fewest lines that let someone reproduce it.
- Do not paste the user's raw message. Rewrite it.
- No "please", no "it would be nice", no background the reader already has.
- File paths, endpoints, error strings and field names go in backticks. Include them when known. They save the implementer a search.
- When the input references another repo or project, say so with a `Repo:` line at the top of the description, the way sub-issues do below.

## 4. Sub-issues or checkboxes

The request may contain work for more than one repo or project (an API change plus a mobile change, a backend job plus an admin screen).

Make it a **sub-issue** when the piece:

- lives in a different repo or project than the parent, or
- can be delivered and reviewed on its own, or
- is big enough to get its own branch and PR.

Each sub-issue gets its own short title, a description that starts with `Repo: NAME`, `parentId` set to the parent, and its own estimate and labels. Put the sub-issue in the project that owns that repo when it differs from the parent's.

Make it a **checkbox** in the parent's acceptance criteria when the piece is a few minutes of work in the same repo (bump a version, update a copy string, add a config flag). Do not create an issue for that.

The parent's description keeps the overall goal and lists the sub-issues by title once they exist.

## 5. Show the draft, then create

Before any write, show the user everything that will be created:

```markdown
**Team / Project / Milestone**: ...
**Labels**: ...   **Estimate**: ...   **Priority**: ...

**Title**: ...

DESCRIPTION AS IT WILL APPEAR

**Sub-issues** (if any):
1. Title, project, estimate, labels
```

Wait for a yes. Apply any edits they give and show the changed parts again only if the edits were substantial.

On yes:

1. `save_issue` for the parent with `team`, `title`, `description`, `project`, `milestone`, `labels`, `estimate`, and `links` for any URLs worth attaching.
2. `save_issue` for each sub-issue with `parentId` set to the parent's identifier.
3. If the parent's description lists sub-issues, update it with their identifiers.
4. Report the created identifiers and URLs, parent first.

If a create fails midway, report exactly what was and was not created and stop. Do not retry blindly.

## Safety checklist

- [ ] Read the whole input (text, images, links) before drafting
- [ ] Asked only questions whose answers change the issue, in one batch
- [ ] Team, project, milestone, labels and estimate taken from what the project already uses, not invented
- [ ] Title is one specific imperative line; description has no filler and does not restate the title
- [ ] Cross-repo or standalone work became sub-issues with a `Repo:` line; tiny pieces became checkboxes
- [ ] Full draft shown and confirmed before `save_issue`
- [ ] No assignee, state or due date set unless the user asked
- [ ] Created identifiers and URLs reported back
