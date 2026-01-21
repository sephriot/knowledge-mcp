package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"github.com/sephriot/knowledge-mcp/config"
	"github.com/sephriot/knowledge-mcp/models"
	"github.com/sephriot/knowledge-mcp/storage"
	"github.com/sephriot/knowledge-mcp/tools"
)

func main() {
	dataPath := flag.String("data-path", "", "Path to knowledge storage (default: .knowledge or KNOWLEDGE_MCP_PATH env)")
	flag.Parse()

	// Configure the data path
	cfg := config.New(*dataPath)
	config.SetConfig(cfg)

	// Create MCP server
	s := server.NewMCPServer(
		"knowledge-mcp",
		"0.1.0",
		server.WithResourceCapabilities(true, true),
		server.WithToolCapabilities(true),
	)

	// Initialize shared index manager and tools
	indexManager := storage.NewIndexManager(cfg)
	searchEngine := tools.NewSearchEngine(cfg, indexManager)
	upsertHandler := tools.NewUpsertHandler(cfg, indexManager)
	atomTools := tools.NewAtomTools(cfg, indexManager)

	// Register tools
	registerSearchTool(s, searchEngine)
	registerUpsertTool(s, upsertHandler)
	registerListAtomsTool(s, atomTools)
	registerGetAtomTool(s, atomTools)
	registerDeleteAtomTool(s, atomTools)
	registerPurgeAtomTool(s, atomTools)
	registerListAllIDsTool(s, atomTools)
	registerExportAllTool(s, atomTools)
	registerRebuildIndexTool(s, atomTools)
	registerGetSummaryTool(s, atomTools)
	registerGetNextIDTool(s, atomTools)

	// Start server
	if err := server.ServeStdio(s); err != nil {
		fmt.Fprintf(os.Stderr, "Server error: %v\n", err)
		os.Exit(1)
	}
}

func registerSearchTool(s *server.MCPServer, engine *tools.SearchEngine) {
	s.AddTool(mcp.NewTool("search",
		mcp.WithDescription(`Search knowledge atoms by title, tags, and content.

Args:
    query: Search query string.
    types: Filter by types (fact, decision, procedure, pattern, gotcha, glossary, snippet).
    tags: Filter by tags.
    language: Filter by programming language.
    status: Filter by status (active, draft, deprecated).
    limit: Maximum results (default 10).
    include_content: Search in atom content (summary, details) too. Slower but more thorough.

Returns:
    List of matching atoms with metadata and summary.`),
		mcp.WithString("query", mcp.Required(), mcp.Description("Search query string")),
		mcp.WithArray("types", mcp.Description("Filter by types")),
		mcp.WithArray("tags", mcp.Description("Filter by tags")),
		mcp.WithString("language", mcp.Description("Filter by programming language")),
		mcp.WithString("status", mcp.Description("Filter by status")),
		mcp.WithNumber("limit", mcp.Description("Maximum results")),
		mcp.WithBoolean("include_content", mcp.Description("Search in atom content too")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		query, _ := request.Params.Arguments["query"].(string)

		var types []string
		if t, ok := request.Params.Arguments["types"].([]any); ok {
			for _, v := range t {
				if s, ok := v.(string); ok {
					types = append(types, s)
				}
			}
		}

		var tags []string
		if t, ok := request.Params.Arguments["tags"].([]any); ok {
			for _, v := range t {
				if s, ok := v.(string); ok {
					tags = append(tags, s)
				}
			}
		}

		var language *string
		if l, ok := request.Params.Arguments["language"].(string); ok && l != "" {
			language = &l
		}

		var status *string
		if st, ok := request.Params.Arguments["status"].(string); ok && st != "" {
			status = &st
		}

		limit := 10
		if l, ok := request.Params.Arguments["limit"].(float64); ok {
			limit = int(l)
		}

		includeContent := false
		if ic, ok := request.Params.Arguments["include_content"].(bool); ok {
			includeContent = ic
		}

		var results []tools.SearchResult
		var err error
		if includeContent {
			results, err = engine.SearchContent(query, types, tags, language, status, limit)
		} else {
			results, err = engine.Search(query, types, tags, language, status, limit)
		}

		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(results)), nil
	})
}

func registerUpsertTool(s *server.MCPServer, handler *tools.UpsertHandler) {
	s.AddTool(mcp.NewTool("upsert",
		mcp.WithDescription(`Create or update a knowledge atom.

Args:
    title: Short descriptive title.
    type: Atom type (fact, decision, procedure, pattern, gotcha, glossary, snippet).
    status: Status (active, draft, deprecated).
    confidence: Confidence level (high, medium, low).
    summary: The main content summary of the atom.
    details: Detailed explanation or code.
    pitfalls: List of potential pitfalls or things to avoid.
    id: Optional ID for updates. Auto-generated for new atoms.
    language: Programming language (optional).
    tags: Keywords for search (optional).
    sources: References like [{"kind": "repo_path", "ref": "src/file.ts"}] (optional).
    links: Related atoms like [{"rel": "see_also", "id": "K-000001"}] (optional).

Returns:
    The created/updated atom.`),
		mcp.WithString("title", mcp.Required(), mcp.Description("Short descriptive title")),
		mcp.WithString("type", mcp.Required(), mcp.Description("Atom type"), mcp.Enum("fact", "decision", "procedure", "pattern", "gotcha", "glossary", "snippet")),
		mcp.WithString("status", mcp.Required(), mcp.Description("Status"), mcp.Enum("active", "draft", "deprecated")),
		mcp.WithString("confidence", mcp.Required(), mcp.Description("Confidence level"), mcp.Enum("high", "medium", "low")),
		mcp.WithString("summary", mcp.Required(), mcp.Description("Main content summary")),
		mcp.WithString("details", mcp.Description("Detailed explanation")),
		mcp.WithArray("pitfalls", mcp.Description("List of pitfalls")),
		mcp.WithString("id", mcp.Description("Optional ID for updates")),
		mcp.WithString("language", mcp.Description("Programming language")),
		mcp.WithArray("tags", mcp.Description("Keywords for search")),
		mcp.WithArray("sources", mcp.Description("Reference sources")),
		mcp.WithArray("links", mcp.Description("Related atoms")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		input := tools.UpsertInput{
			Title:      getString(request.Params.Arguments, "title"),
			Type:       getAtomType(request.Params.Arguments, "type"),
			Status:     getAtomStatus(request.Params.Arguments, "status"),
			Confidence: getConfidence(request.Params.Arguments, "confidence"),
			Summary:    getString(request.Params.Arguments, "summary"),
			Details:    getString(request.Params.Arguments, "details"),
			Pitfalls:   getStringArray(request.Params.Arguments, "pitfalls"),
			Tags:       getStringArray(request.Params.Arguments, "tags"),
			Sources:    getSources(request.Params.Arguments, "sources"),
			Links:      getLinks(request.Params.Arguments, "links"),
		}

		if id := getString(request.Params.Arguments, "id"); id != "" {
			input.ID = &id
		}
		if lang := getString(request.Params.Arguments, "language"); lang != "" {
			input.Language = &lang
		}

		result, err := handler.Upsert(input)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

func registerListAtomsTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("list_atoms",
		mcp.WithDescription(`List knowledge atoms with filtering.

Args:
    types: Filter by types.
    tags: Filter by tags.
    status: Filter by status.
    language: Filter by language.
    limit: Maximum results (default 50).

Returns:
    List of atom summaries.`),
		mcp.WithArray("types", mcp.Description("Filter by types")),
		mcp.WithArray("tags", mcp.Description("Filter by tags")),
		mcp.WithString("status", mcp.Description("Filter by status")),
		mcp.WithString("language", mcp.Description("Filter by language")),
		mcp.WithNumber("limit", mcp.Description("Maximum results")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		types := getStringArray(request.Params.Arguments, "types")
		tags := getStringArray(request.Params.Arguments, "tags")

		var status *string
		if s := getString(request.Params.Arguments, "status"); s != "" {
			status = &s
		}

		var language *string
		if l := getString(request.Params.Arguments, "language"); l != "" {
			language = &l
		}

		limit := 50
		if l, ok := request.Params.Arguments["limit"].(float64); ok {
			limit = int(l)
		}

		results, err := atomTools.ListAtoms(types, tags, status, language, limit)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(results)), nil
	})
}

func registerGetAtomTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("get_atom",
		mcp.WithDescription(`Get full atom content by ID.

Args:
    id: The atom ID (e.g., K-000001).

Returns:
    Full atom content or None if not found.`),
		mcp.WithString("id", mcp.Required(), mcp.Description("The atom ID")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		id := getString(request.Params.Arguments, "id")
		result, err := atomTools.GetAtom(id)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

func registerDeleteAtomTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("delete_atom",
		mcp.WithDescription(`Deprecate an atom (sets status to deprecated).

Args:
    id: The atom ID to deprecate.

Returns:
    Result with success status.`),
		mcp.WithString("id", mcp.Required(), mcp.Description("The atom ID to deprecate")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		id := getString(request.Params.Arguments, "id")
		result, err := atomTools.DeleteAtom(id)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

func registerPurgeAtomTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("purge_atom",
		mcp.WithDescription(`Permanently delete an atom from storage.

WARNING: This cannot be undone. Use delete_atom to deprecate instead.

Args:
    id: The atom ID to permanently delete.

Returns:
    Result with success status.`),
		mcp.WithString("id", mcp.Required(), mcp.Description("The atom ID to permanently delete")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		id := getString(request.Params.Arguments, "id")
		result, err := atomTools.PurgeAtom(id)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

func registerListAllIDsTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("list_all_ids",
		mcp.WithDescription(`List all atom IDs in storage.

Returns:
    Dictionary with list of IDs and count.`),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		result, err := atomTools.ListAllIDs()
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

func registerExportAllTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("export_all",
		mcp.WithDescription(`Export all knowledge as a single JSON structure.

Args:
    format: Export format (only "json" supported).

Returns:
    All atoms in a single structure.`),
		mcp.WithString("format", mcp.Description("Export format")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		format := getString(request.Params.Arguments, "format")
		if format == "" {
			format = "json"
		}

		result, err := atomTools.ExportAll(format)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

func registerRebuildIndexTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("rebuild_index",
		mcp.WithDescription(`Rebuild index.json from atom files.

Use this if the index gets out of sync with the atom files.

Returns:
    Result with count of atoms indexed.`),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		result, err := atomTools.RebuildIndex()
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

func registerGetSummaryTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("get_summary",
		mcp.WithDescription(`Get summary of knowledge grouped by type, tag, or language.

Args:
    group_by: Grouping criterion ("type", "tag", or "language").

Returns:
    Summary with counts and items per group.`),
		mcp.WithString("group_by", mcp.Description("Grouping criterion")),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		groupBy := getString(request.Params.Arguments, "group_by")
		if groupBy == "" {
			groupBy = "type"
		}

		result, err := atomTools.GetSummary(groupBy)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

func registerGetNextIDTool(s *server.MCPServer, atomTools *tools.AtomTools) {
	s.AddTool(mcp.NewTool("get_next_id",
		mcp.WithDescription(`Get the next available atom ID.

Returns:
    Dictionary with next_id field (e.g., K-000001).`),
	), func(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {

		result, err := atomTools.GetNextID()
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}

		return mcp.NewToolResultText(toJSON(result)), nil
	})
}

// Helper functions

func getString(args map[string]any, key string) string {
	if v, ok := args[key].(string); ok {
		return v
	}
	return ""
}

func getStringArray(args map[string]any, key string) []string {
	if arr, ok := args[key].([]any); ok {
		result := make([]string, 0, len(arr))
		for _, v := range arr {
			if s, ok := v.(string); ok {
				result = append(result, s)
			}
		}
		return result
	}
	return nil
}

func getAtomType(args map[string]any, key string) models.AtomType {
	return models.AtomType(getString(args, key))
}

func getAtomStatus(args map[string]any, key string) models.AtomStatus {
	return models.AtomStatus(getString(args, key))
}

func getConfidence(args map[string]any, key string) models.Confidence {
	return models.Confidence(getString(args, key))
}

func getSources(args map[string]any, key string) []models.Source {
	arr, ok := args[key].([]any)
	if !ok {
		return nil
	}

	result := make([]models.Source, 0, len(arr))
	for _, v := range arr {
		if m, ok := v.(map[string]any); ok {
			source := models.Source{
				Kind: models.SourceKind(getString(m, "kind")),
				Ref:  getString(m, "ref"),
			}
			result = append(result, source)
		}
	}
	return result
}

func getLinks(args map[string]any, key string) []models.Link {
	arr, ok := args[key].([]any)
	if !ok {
		return nil
	}

	result := make([]models.Link, 0, len(arr))
	for _, v := range arr {
		if m, ok := v.(map[string]any); ok {
			link := models.Link{
				Rel: models.LinkRel(getString(m, "rel")),
				ID:  getString(m, "id"),
			}
			result = append(result, link)
		}
	}
	return result
}

func toJSON(v any) string {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Sprintf(`{"error": "%s"}`, err.Error())
	}
	return string(data)
}
