---
name: huzaifa
description: >-
  Huzaifa's personal UI taste for webapps. Apply whenever building or styling
  web UI — pages, sections, components, landing pages, dashboards — so the
  result matches how Huzaifa likes interfaces to look. Covers section title
  structure (big heading + small subtitle, never an eyebrow label above the
  heading) and theming (every UI ships with both light and dark mode).
---

# Huzaifa's UI Taste

Personal design preferences for web UIs. When building or restyling any webapp UI, follow these rules by default — they override generic design habits, not explicit instructions from the user in the current task.

## Titles

Every section title uses **big heading first, small subtitle underneath**:

```
What we build          ← big heading
Everything we offer    ← smaller, muted subtitle
```

Rules:

- The heading is the first and largest text in the section.
- The subtitle sits directly below it — smaller size, muted/secondary color, one short line.
- **Never** use the eyebrow/overline pattern (a small, often uppercase label *above* the big heading, e.g. `OUR SERVICES` over `What we build`). If a design or template comes with one, remove it and fold its meaning into the heading or subtitle.
- Don't stack two headings of similar weight — one big heading per section, one subtitle, done.

Example (HTML/CSS-agnostic structure):

```html
<header class="section-header">
  <h2>What we build</h2>
  <p class="subtitle">Everything we offer, in one place</p>
</header>
```

The subtitle is optional — when a section needs no description, use the heading alone rather than inventing filler text.

## Theming

- **Always ship both light and dark mode**, from the first version — never light-only or dark-only.
- Define colors as tokens/variables (CSS custom properties or the framework's theme system), never hardcoded per component, so both themes stay consistent.
- Respect the user's system preference by default (`prefers-color-scheme`), and if the app has a theme toggle, let it override the system setting.
- Check both themes before calling the UI done: text contrast, borders, shadows, and images must read well in each.

## Scope

These preferences apply to webapp UI work (websites, landing pages, dashboards, web components). For anything not covered here, follow the project's existing conventions and good general design judgment.
