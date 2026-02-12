# Knowledge MCP Server

An MCP server providing project-specific knowledge management for coding agents (Claude Code, Codex, Gemini). Uses **stdio transport** and **YAML-based storage** for optimal LLM efficiency.

Better version of similar concept: [atlas-mcp](https://github.com/sephriot/atlas-mcp) 

**Local-first design**: Each project has its own `.knowledge` directory that can be committed to git.

> **Note**: There is another unrelated project with the same name on PyPI. This project is **not published to PyPI**. Install from GitHub only.

## Quick Start

The easiest way to use knowledge-mcp is via `uvx` (no installation required).

### Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "knowledge-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/sephriot/knowledge-mcp",
        "knowledge-mcp",
        "--data-path",
        ".knowledge"
      ]
    }
  }
}
```

Or add globally via CLI:

```bash
claude mcp add knowledge-mcp -- uvx --from git+https://github.com/sephriot/knowledge-mcp knowledge-mcp
```

Verify it works:

```bash
claude mcp list
```

### Gemini

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "knowledge-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/sephriot/knowledge-mcp",
        "knowledge-mcp",
        "--data-path",
        ".knowledge"
      ]
    }
  }
}
```

## Alternative Installation

If you prefer to install locally instead of using uvx:

```bash
# Clone and install
git clone https://github.com/sephriot/knowledge-mcp
cd knowledge-mcp
pip install -e .

# Then configure your MCP client to use the installed command
claude mcp add knowledge-mcp -- knowledge-mcp --data-path .knowledge
```

## CLI Options

| Option                 | Description                                                                            |
|------------------------|----------------------------------------------------------------------------------------|
| `--data-path PATH`     | Path to knowledge storage directory (default: `.knowledge` or `KNOWLEDGE_MCP_PATH` env)|
| `--persist-popularity` | Persist popularity counts to disk on each atom retrieval                               |

### Running Standalone

```bash
# Default: uses .knowledge in current directory
knowledge-mcp

# Custom data path
knowledge-mcp --data-path /path/to/knowledge

# Via environment variable
KNOWLEDGE_MCP_PATH=./my-knowledge knowledge-mcp
```

### Popularity Tracking

The server tracks how often each atom is retrieved via `get_atom`. This popularity score influences search ranking (more popular atoms rank higher). By default, popularity is tracked in memory only and persists when other index changes occur.

Use `--persist-popularity` to write popularity counts to disk immediately on each retrieval. This is useful when:

- Running short-lived sessions where in-memory counts would be lost
- You want guaranteed persistence of usage patterns
- Multiple server instances share the same storage

Note: Enabling this option increases disk writes. For most use cases, the default behavior is sufficient.

## Storage Structure

```text
.knowledge/
├── index.yaml           # Fast lookup index (denormalized metadata)
└── atoms/
    ├── K-000001.yaml    # Knowledge atom (YAML)
    ├── K-000002.yaml
    └── ...
```

## Knowledge Atom Types

| Type       | Description                                    |
|------------|------------------------------------------------|
| `fact`     | Verified information about the codebase        |
| `decision` | Architectural or design decisions              |
| `procedure`| Step-by-step processes or workflows            |
| `pattern`  | Reusable code patterns or practices            |
| `gotcha`   | Common pitfalls or tricky behaviors            |
| `glossary` | Domain-specific terminology                    |
| `snippet`  | Reusable code snippets                         |

## Available Tools

### Core Tools

| Tool     | Description                                      |
|----------|--------------------------------------------------|
| `search` | Search atoms by title, tags, content             |
| `upsert` | Create or update a knowledge atom                |

### Knowledge Organization

| Tool           | Description                                   |
|----------------|-----------------------------------------------|
| `list_atoms`   | List atoms with optional filtering            |
| `get_atom`     | Get full atom content by ID                   |
| `delete_atom`  | Deprecate an atom (set status to deprecated)  |
| `purge_atom`   | Permanently delete an atom (cannot be undone) |
| `list_all_ids` | List all atom IDs in storage                  |

### Bulk Operations

| Tool            | Description                              |
|-----------------|------------------------------------------|
| `export_all`    | Export all knowledge as single JSON      |
| `rebuild_index` | Rebuild index.yaml from atom files       |

### Utility

| Tool          | Description                                  |
|---------------|----------------------------------------------|
| `get_summary` | Summary grouped by type/tag/language         |
| `get_next_id` | Get next available K-XXXXXX ID               |

## Example Usage

### Creating a Knowledge Atom

```json
{
  "tool": "upsert",
  "arguments": {
    "title": "Error Handling Pattern",
    "type": "pattern",
    "status": "active",
    "confidence": "high",
    "language": "typescript",
    "tags": ["error-handling", "async"],
    "summary": "Centralized async error handling using Result types.",
    "details": "Always wrap async operations in try-catch with specific error types...",
    "pitfalls": ["Don't catch generic errors without re-throwing"],
    "sources": [
      {"kind": "repo_path", "ref": "src/utils/errors.ts"}
    ]
  }
}
```

### Searching Knowledge

```json
{
  "tool": "search",
  "arguments": {
    "query": ["error", "handling"],
    "types": ["pattern", "gotcha"],
    "language": "typescript",
    "limit": 5
  }
}
```

### Deep Content Search

Use `include_content: true` to search within atom content (summary and details), not just titles and tags:

```json
{
  "tool": "search",
  "arguments": {
    "query": ["exponential", "backoff"],
    "include_content": true
  }
}
```

### File Path Search

Use `file_path` to find atoms related to specific files. Supports hierarchical matching:

```json
{
  "tool": "search",
  "arguments": {
    "file_path": "src/utils/errors.ts"
  }
}
```

Or search multiple files:

```json
{
  "tool": "search",
  "arguments": {
    "file_path": ["src/api/client.ts", "src/api/server.ts"]
  }
}
```

Scoring: exact match (+100) > parent directory (+50 decaying) > child match (+30).

## Atom Fields Reference

| Field          | Required | Description                                                                 |
|----------------|----------|-----------------------------------------------------------------------------|
| `id`           | Yes      | Unique ID (K-XXXXXX format)                                                 |
| `title`        | Yes      | Short descriptive title                                                     |
| `type`         | Yes      | fact, decision, procedure, pattern, gotcha, glossary, snippet               |
| `status`       | Yes      | active, draft, deprecated                                                   |
| `confidence`   | Yes      | high, medium, low                                                           |
| `summary`      | Yes      | Main content summary                                                        |
| `details`      | No       | Detailed explanation or code                                                |
| `pitfalls`     | No       | List of potential pitfalls                                                  |
| `language`     | No       | Programming language                                                        |
| `tags`         | No       | Keywords for search                                                         |
| `sources`      | No       | References (repo_path, ticket, url, conversation)                           |
| `links`        | No       | Relations (depends_on, see_also, contradicts)                               |

## AI Assistant Integration

To ensure your AI assistant (Claude, Gemini, Codex, etc.) automatically uses knowledge-mcp, add the system prompt to your assistant's configuration file.

### For Gemini

Append the contents of [`SYSTEM_PROMPT.md`](./SYSTEM_PROMPT.md) to `~/.gemini/GEMINI.md`.

### For Claude Code

Append the contents of [`SYSTEM_PROMPT.md`](./SYSTEM_PROMPT.md) to `~/.claude/CLAUDE.md` or your project's `CLAUDE.md`.

### For other assistants

Copy the contents of [`SYSTEM_PROMPT.md`](./SYSTEM_PROMPT.md) to your assistant's system prompt or configuration file.

This ensures the assistant will:

1. Search existing knowledge before starting tasks
2. Apply relevant knowledge to decisions
3. Create new atoms when discovering reusable knowledge
4. Cite knowledge usage in responses

## Development

### Requirements

- Python 3.11+
- Dependencies: mcp, pyyaml, pydantic

### Running tests

```bash
pip install -e ".[dev]"
pytest tests/
```

### Type checking

```bash
mypy src/knowledge_mcp
```

## License

MIT
