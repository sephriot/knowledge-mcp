# Knowledge MCP Server

An MCP server providing project-specific knowledge management for coding agents (Claude Code, Codex, Gemini). Uses **stdio transport** and **JSON-based storage** for optimal LLM efficiency.

**Local-first design**: Each project has its own `.knowledge` directory that can be committed to git.

## Installation

```bash
# Using pip
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

## Usage

### Running the Server

```bash
# Default (uses .knowledge/ in current directory)
knowledge-mcp

# Custom path
knowledge-mcp --data-path /path/to/knowledge

# Or via environment variable
KNOWLEDGE_MCP_PATH=./my-knowledge knowledge-mcp
```

### Adding to Claude Code

#### Option 1: Using the CLI (Recommended)

```bash
# Add as a global MCP server
claude mcp add knowledge-mcp -- knowledge-mcp

# Or with a custom data path
claude mcp add knowledge-mcp -- knowledge-mcp --data-path /path/to/.knowledge
```

#### Option 2: Project-level configuration

Create or edit `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "knowledge": {
      "command": "knowledge-mcp",
      "args": ["--data-path", ".knowledge"]
    }
  }
}
```

#### Option 3: Global configuration

Edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "knowledge": {
      "command": "knowledge-mcp",
      "args": []
    }
  }
}
```

#### Verify Installation

After adding, verify the server is available:

```bash
claude mcp list
```

You should see `knowledge` in the list of available MCP servers.

## Storage Structure

```text
.knowledge/
├── index.json           # Fast lookup index (denormalized metadata)
└── atoms/
    ├── K-000001.json    # Knowledge atom (JSON)
    ├── K-000002.json
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
| `rebuild_index` | Rebuild index.json from atom files       |

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
    "content": {
      "summary": "Centralized async error handling using Result types.",
      "details": "Always wrap async operations in try-catch with specific error types...",
      "pitfalls": ["Don't catch generic errors without re-throwing"]
    },
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
    "query": "error handling",
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
    "query": "exponential backoff",
    "include_content": true
  }
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector knowledge-mcp
```

## Atom Fields Reference

| Field          | Required | Description                                                                 |
|----------------|----------|-----------------------------------------------------------------------------|
| `id`           | Yes      | Unique ID (K-XXXXXX format)                                                 |
| `title`        | Yes      | Short descriptive title                                                     |
| `type`         | Yes      | fact, decision, procedure, pattern, gotcha, glossary, snippet               |
| `status`       | Yes      | active, draft, deprecated                                                   |
| `confidence`   | Yes      | high, medium, low                                                           |
| `content`      | Yes      | Object with summary, details, pitfalls (optional), update_notes (optional)  |
| `language`     | No       | Programming language                                                        |
| `tags`         | No       | Keywords for search                                                         |
| `sources`      | No       | References (repo_path, ticket, url, conversation)                           |
| `links`        | No       | Relations (depends_on, see_also, contradicts)                               |
| `supersedes`   | No       | IDs of atoms this replaces                                                  |
| `superseded_by`| No       | ID of atom that replaced this                                               |

## License

MIT
