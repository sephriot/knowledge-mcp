# Knowledge MCP Server

An MCP server providing project-specific knowledge management for coding agents (Claude Code, Codex, Gemini). Uses **stdio transport** and **JSON-based storage** for optimal LLM efficiency.

**Local-first design**: Each project has its own `.knowledge` directory that can be committed to git.

## Installation

### Building from Source

```bash
# Clone the repository
git clone https://github.com/sephriot/knowledge-mcp
cd knowledge-mcp

# Build the binary
go build -o knowledge-mcp .

# Optionally, install to your GOPATH
go install .
```

### Pre-built Binaries

Download the latest release from the [releases page](https://github.com/sephriot/knowledge-mcp/releases).

## Usage

### Running the Server

```bash
# Default: uses .knowledge in current directory
./knowledge-mcp

# Custom data path
./knowledge-mcp --data-path /path/to/knowledge

# Or via environment variable
KNOWLEDGE_MCP_PATH=./my-knowledge ./knowledge-mcp
```

### Adding to Claude Code

#### Option 1: Using the CLI (Recommended)

```bash
# Add as a global MCP server (assuming binary is in PATH)
claude mcp add knowledge-mcp -- knowledge-mcp

# Or with a custom data path
claude mcp add knowledge-mcp -- knowledge-mcp --data-path /path/to/.knowledge
```

#### Option 2: Project-level configuration

Create or edit `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "knowledge-mcp": {
      "command": "/path/to/knowledge-mcp",
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
    "knowledge-mcp": {
      "command": "/path/to/knowledge-mcp",
      "args": []
    }
  }
}
```

### Adding to Gemini

Edit `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "knowledge-mcp": {
      "command": "/path/to/knowledge-mcp",
      "args": ["--data-path", "/path/to/.knowledge"]
    }
  }
}
```

### Verify Installation

After adding, verify the server is available:

```bash
claude mcp list
```

You should see `knowledge-mcp` in the list of available MCP servers.

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

## License

MIT
