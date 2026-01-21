# Knowledge-MCP Integration – Enforced Workflow

You have access to a running `knowledge-mcp` server that maintains persistent project knowledge. During all tasks, you **MUST use these tools** to retrieve, apply, and update knowledge to improve task quality and reuse across future tasks. Knowledge usage is required but secondary to fulfilling the current objective.

==================== AVAILABLE TOOLS ====================
- `search`         – Search atoms by title, tags, content
- `get_atom`       – Retrieve full content of an atom by ID
- `upsert`         – Create or update a knowledge atom
- `list_atoms`     – List atoms with optional filtering
- `delete_atom`    – Deprecate an atom
- `get_summary`    – Retrieve a grouped summary of atoms
- `get_next_id`    – Get the next available atom ID

==================== REQUIRED WORKFLOW ====================

1) **BEFORE PLANNING**
- Extract domain keywords from the user request or context.
- Use `search` to find existing atoms relevant to the task.
- For promising search results, use `get_atom` to read full content.
- If relevant atoms exist, **ground planning and decisions in those atoms**.

2) **PLANNING & EXECUTION**
- Use existing knowledge as guidance for decisions and implementation.
- **Task completion remains the top priority.** Knowledge use must not delay progress.
- When multiple atoms apply, resolve conflicts based on:
  - *confidence*: high > medium > low
  - *status*: active > draft > deprecated
  - *last updated*: newer > older
- Cite existing atoms only when they *inform or influence* decisions, not merely because they exist.

3) **CITING KNOWLEDGE**
- At the end of the task response, include a **Knowledge Used** section.
- List each atom ID and a short description of how it influenced your decisions.

4) **UPDATING KNOWLEDGE**
- Only upsert knowledge that is **reliable, reusable, and non-trivial**.
- New atoms must represent one clear concept.
- Use `upsert` to add new atoms when you encounter:
  - confirmed best practices
  - recurring patterns
  - documented gotchas
  - definitions that help future reasoning
- Never delete; use `delete_atom` to deprecate outdated atoms.
- Provide sources for each new atom (e.g., code files, tickets, URLs).
- If unsure about accuracy or permanence, mark confidence as `low`.

5) **FINALIZING**
Conclude with the required sections:
- Knowledge used: K-XXXXXX: One-line description of how this atom influenced your output.
- Knowledge changes: K-YYYYYY: One-line description of any new or updated atoms.

==================== ATOM TYPES ====================
| Type      | Description |
|-----------|-------------|
| fact      | Verified information about the project |
| decision  | Explicit design or architectural choice |
| procedure | Step-by-step workflows |
| pattern   | Reusable coding or design pattern |
| gotcha    | Common pitfalls and caveats |
| glossary  | Domain terms and definitions |
| snippet   | Reusable code samples |

==================== GENERAL RULES ====================
- **Retrieval before creation:** Always look for applicable existing knowledge before inventing new content.
- **Knowledge is supportive:** Use knowledge *to improve task quality and future reuse*, not to justify overengineering.
- **Efficiency:** Searching and retrieving knowledge must be efficient; avoid exhaustive exploration beyond relevant scope.
