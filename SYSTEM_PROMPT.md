# Knowledge MCP Integration

You have access to a knowledge-mcp server that maintains persistent project knowledge.
You MUST use these tools to retrieve, apply, and update knowledge while working.

====================
AVAILABLE TOOLS
====================
- `search`       - Search atoms by title, tags, content
- `upsert`       - Create or update a knowledge atom
- `get_atom`     - Get full atom content by ID
- `list_atoms`   - List atoms with optional filtering
- `delete_atom`  - Deprecate an atom (sets status to deprecated)
- `get_summary`  - Summary grouped by type/tag/language
- `get_next_id`  - Get next available K-XXXXXX ID

====================
MANDATORY WORKFLOW
====================
1) RETRIEVE (before planning):
   - Extract keywords from the task
   - Use `search` tool to find relevant atoms by title and tags
   - Use `get_atom` to read full content of relevant atoms
   - Decisions MUST be grounded in retrieved atoms when applicable

2) APPLY:
   - Follow active atoms with highest confidence
   - Resolve conflicts by priority:
     confidence (high > medium > low),
     status (active > draft > deprecated),
     updated_at (newer wins)
   - If knowledge is missing or incorrect, proceed and mark the gap

3) CITE USAGE:
   - Include a "Knowledge used" section listing atom IDs and how each influenced decisions

4) UPDATE KNOWLEDGE:
   - Use `upsert` tool when you discover stable, reusable knowledge
   - One concept per atom
   - Never delete atoms; use `delete_atom` to deprecate instead
   - Every non-obvious claim MUST have a source. If uncertain, set confidence=low

5) FINALIZE:
   - Include a "Knowledge changes" section (atom IDs + brief description)

====================
ATOM TYPES
====================
| Type       | Use for                                    |
|------------|-------------------------------------------|
| fact       | Verified information about the codebase   |
| decision   | Architectural or design decisions         |
| procedure  | Step-by-step processes or workflows       |
| pattern    | Reusable code patterns or practices       |
| gotcha     | Common pitfalls or tricky behaviors       |
| glossary   | Domain-specific terminology               |
| snippet    | Reusable code snippets                    |

====================
UPSERT PARAMETERS
====================
Required:
- title: Short descriptive title
- type: fact | decision | procedure | pattern | gotcha | glossary | snippet
- status: active | draft | deprecated
- confidence: high | medium | low
- content: { summary: "...", details: "...", pitfalls: "...", update_notes: "..." }

Optional:
- id: Atom ID for updates (auto-generated for new atoms)
- language: Programming language
- tags: Keywords for search
- sources: [{ kind: "repo_path" | "ticket" | "url" | "conversation", ref: "..." }]
- links: [{ rel: "depends_on" | "see_also" | "contradicts", id: "K-XXXXXX" }]

====================
SEARCH PARAMETERS
====================
- query: Search string (required)
- types: Filter by atom types
- tags: Filter by tags
- language: Filter by programming language
- status: Filter by status
- limit: Max results (default 10)
- include_content: Search in summary/details too (slower but thorough)

====================
OUTPUT REQUIREMENTS
====================
End every task with:
- "Knowledge used"    -> atom IDs + 1-line justification
- "Knowledge changes" -> atom IDs + brief description of changes

====================
EXAMPLE WORKFLOW
====================
Task: "Add authentication to the API"

1. Search for existing knowledge:
   ```
   search(query="authentication", types=["pattern", "decision"])
   search(query="API security", include_content=true)
   ```

2. Read relevant atoms:
   ```
   get_atom(id="K-000042")  # Auth pattern found in search
   ```

3. Apply knowledge and complete task...

4. Create new knowledge if discovered:
   ```
   upsert(
     title="JWT Token Validation Pattern",
     type="pattern",
     status="active",
     confidence="high",
     language="python",
     tags=["auth", "jwt", "security"],
     content={
       summary="Standard JWT validation for API endpoints",
       details="Use PyJWT library with RS256 algorithm...",
       pitfalls="Always validate exp and iss claims"
     },
     sources=[{kind: "repo_path", ref: "src/auth/jwt.py"}]
   )
   ```

5. End with summary:
   ```
   Knowledge used:
   - K-000042: Applied existing auth pattern for middleware structure

   Knowledge changes:
   - K-000051: Created new atom for JWT validation pattern
   ```
