---
name: non-leaf-ui-only-design
description: Use for ARC InterfaceDesigner work when a parent node only owns visual shell, layout reference behavior, route slots, or child mount surfaces. This is intentionally weak design, not feature implementation.
---

# non-leaf-ui-only-design

Use this skill when you determine the current node owns only visual shell, layout, route slots, navigation surface, or mount-point behavior.

Non-leaf UI-only design must stay thin. The purpose is to give children a stable visual/composition boundary, not to pre-implement child features or create test-heavy behavior.

## Instructions

1. Use this skill only when the non-leaf node has visual references or explicit parent-owned UI composition requirements.
2. Focus on visual shell, layout hierarchy, navigation surface, container structure, and presentation scaffolding.
3. Match visual reference structure where present: ordering, grouping, spacing, density, major visible regions, and style language.
4. Do not implement child-owned business behavior or detailed runtime interactions.
5. If visual references exist, materialize the UI shell files and style boundary that preserve the parent composition; otherwise return no interfaces and do not read or edit files.
6. Prefer one or two broad interface contracts for the shell or mount boundary; avoid one interface per visual subsection.
7. Interface specifications should describe stable regions and allowed child attachment points, not exact child copy, form internals, route-transition mechanics, or backend data loops.
8. Do not create API, FUNC, or DB contracts for non-leaf UI-only design.
9. Keep `test_focus` minimal: smoke-level renderability, presence of the parent shell, and absence of fake child data are enough.
10. The interface `type` must be one of `UI`, `API`, `FUNC`, or `DB`; for non-leaf UI-only design, default to `UI`.
11. Keep data dynamic or placeholder-neutral; never copy screenshot rows as business data.
12. Start with the parent route/page and its direct style and composition files: typically `frontend/src/App.tsx`, the current page in `frontend/src/pages/`, its direct components, and `frontend/src/index.css`. Read only the smallest set needed to place the shell.
13. Do not inspect backend, database, API client, test harness, package manifest, or child feature implementation for a UI-only node unless a current-node failure names that file.
14. Extract every user-visible string the non-leaf node owns (navigation labels, sidebar items, view titles, shell headings, empty states) from the requirement's description, scenarios, and visual references, and record them in a `visible_texts` list on the UI interface's `specification`. Never leave shell/navigation wording for children to invent.
15. Give every interactive shell element a `role` (navigation, link, button, etc.) and a stable `accessible_name` (aria-label or visible text) matching the requirement wording. A navigation or interactive element with only a testid and no accessible name is not a valid contract.
16. For any owned shell interaction, specify the mechanics: trigger (click vs hover), surface form (page navigation vs dropdown vs drawer), and confirmation (direct action vs dialog). Keep it thin, but do not leave the trigger/surface for children to guess.
17. Use conservative, industry-standard wording for shell text the requirement does not spell out (Notion/Trello/Google Keep conventions): navigation and view titles use nouns (Notes, Archive, Trash, Settings); sidebar actions use bare verbs or verb phrases.
18. Keep shell text consistent: the sidebar navigation label equals the corresponding view title; the same concept uses the same string across the shell. When designing, read existing shell interfaces' `visible_texts` and reuse the wording.
19. Define shell edge copy: a mount/route-slot that can render empty must state its empty message; a dismissible shell surface must state its cancel/close text.
