---
name: leaf-full-design
description: Use for ARC InterfaceDesigner work when the current requirement node owns an executable feature chain.
---

# leaf-full-design

Use this skill when you determine the current node owns the smallest executable feature slice required by its scenarios.

## Instructions

1. Treat the current node as owning the smallest executable feature slice required by its scenarios.
2. Design only interfaces needed for the owned chain, which may span UI -> API -> FUNC -> DB when those layers are truly owned by the leaf.
3. Prefer existing entrypoints, boundary files, services, and persistence scaffolds before creating new owners.
4. Reuse existing parent/dependency interfaces when the leaf should implement, extend, or call them; return the existing `interface_id` so the current node can be attached to the same contract.
5. If a parent-designed UI shell is the user-facing entry for the leaf, include that UI interface in the leaf's interface list and connect it to leaf-owned API/FUNC/DB interfaces through callers/callees.
6. Materialize only minimal compilable owner files or skeleton code during DESIGN when the interface would otherwise be only abstract JSON.
7. Do not implement full validation, persistence, authentication/session semantics, encryption, or business behavior in DESIGN; that belongs to TestDrivenDeveloper.
8. Avoid large file writes in DESIGN. Prefer route/client/service/database placeholders with explicit TODO-free contract shape over complete feature implementation.
9. Do not hardcode screenshot data, sample rows, fake success messages, or fallback arrays as completed behavior.
10. Return interfaces that make later test generation straightforward: include `file_path`, `first_line`, responsibility, specification, callers/callees, and test focus.
11. The interface `type` must be one of `UI`, `API`, `FUNC`, or `DB`.
12. Keep the chain connected to existing routes, handlers, tests, and persistence so the leaf compiles into the current system rather than a detached fragment.
13. If the feature affects auth/session/authenticated state/current user/account state, use the auth-session-consistency skill and include global session state, session API, service, and persistence interfaces as needed.
14. If the feature affects cart, checkout, account, products, orders, catalog, inventory, or persisted user-owned data, prefer a connected UI -> API -> FUNC -> DB interface chain over frontend-local state. Omit a layer only when it is clearly not needed by the requirement or existing app architecture.
15. If the requirement description or GIVEN steps say that records, users, relationships, permissions, statuses, or catalog entries already exist, include or reuse a DB interface for deterministic idempotent seed/bootstrap initialization and specify the required ownership, visibility, relationships, and startup/reset timing. Do not treat this as a hidden test fixture or implement it as frontend constants.
16. Explore in ownership order: reused parent/dependency interface, current UI entrypoint, its direct component or hook, current API client, then only the route/service/repository/database scaffold required by the interface chain. Do not inventory unrelated application areas or manifests.
17. Extract every user-visible string from the requirement's description, scenarios, and visual references (buttons, menu items, labels, headings, placeholders, empty states, error messages) and record them in a `visible_texts` list on each UI interface's `specification`. Never leave the final wording for TestDrivenDeveloper to invent.
18. Give every interactive UI element a `role` (button, menuitem, link, navigation, dialog, etc.) and a stable `accessible_name` (aria-label or visible text) that matches the requirement wording. An interactive element specified only by a testid with no accessible name is not a valid contract.
19. For every user action, specify the interaction mechanics in the specification: trigger (hover vs click vs more-options menu), surface form (modal vs dropdown popover vs inline editor vs page navigation), and confirmation (direct action vs confirmation dialog vs undo notification). Never leave TestDrivenDeveloper to guess.
20. Use conservative, industry-standard wording for text the requirement does not spell out (Notion/Trello/Google Keep conventions). Buttons use bare verb infinitives (Delete, Archive, Edit, Save, Cancel); menu items use nouns or verb phrases (Change labels, Move to, Share); view titles use nouns (Notes, Archive, Trash, Settings). Avoid invented, obscure wording.
21. Keep text consistent across the whole app: one concept uses one string (never 'Archive' in one place and 'Archive note' in another); sidebar navigation text equals its view title; the action button text equals its confirmation dialog title. Read existing interfaces' `visible_texts` and reuse the same wording instead of introducing synonyms.
22. Define edge and empty-state copy: a view that can be empty must state its empty message (e.g. 'No notes yet'); a dismissible surface must define its cancel text (Cancel / Close / Dismiss); a failing operation must define its error message.
