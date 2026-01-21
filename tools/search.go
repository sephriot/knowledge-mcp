package tools

import (
	"strings"

	"github.com/sephriot/knowledge-mcp/config"
	"github.com/sephriot/knowledge-mcp/models"
	"github.com/sephriot/knowledge-mcp/storage"
)

// SearchEngine handles search operations.
type SearchEngine struct {
	config       *config.Config
	indexManager *storage.IndexManager
	atomStorage  *storage.AtomStorage
}

// Priority values for ranking.
var statusPriority = map[models.AtomStatus]int{
	models.AtomStatusActive:     3,
	models.AtomStatusDraft:      2,
	models.AtomStatusDeprecated: 1,
}

var confidencePriority = map[models.Confidence]int{
	models.ConfidenceHigh:   3,
	models.ConfidenceMedium: 2,
	models.ConfidenceLow:    1,
}

// NewSearchEngine creates a new search engine.
func NewSearchEngine(cfg *config.Config, indexManager *storage.IndexManager) *SearchEngine {
	if cfg == nil {
		cfg = config.GetConfig()
	}
	return &SearchEngine{
		config:       cfg,
		indexManager: indexManager,
		atomStorage:  storage.NewAtomStorage(cfg),
	}
}

// SearchResult represents a search result.
type SearchResult struct {
	ID         string   `json:"id"`
	Title      string   `json:"title"`
	Type       string   `json:"type"`
	Status     string   `json:"status"`
	Confidence string   `json:"confidence"`
	Language   *string  `json:"language,omitempty"`
	Tags       []string `json:"tags"`
	UpdatedAt  string   `json:"updated_at"`
	Score      int      `json:"score"`
	Summary    string   `json:"summary,omitempty"`
}

// Search searches for knowledge atoms.
func (e *SearchEngine) Search(query []string, types []string, tags []string, language, status *string, limit int) ([]SearchResult, error) {
	index, err := e.indexManager.GetIndex()
	if err != nil {
		return nil, err
	}

	type scoredEntry struct {
		entry *models.IndexEntry
		score int
	}

	var results []scoredEntry
	queryTokens := normalizeTokens(query)

	// Convert types to set for fast lookup
	typeSet := make(map[models.AtomType]bool)
	for _, t := range types {
		typeSet[models.AtomType(t)] = true
	}

	for _, entry := range index.Atoms {
		// Apply filters
		if len(typeSet) > 0 && !typeSet[entry.Type] {
			continue
		}
		if status != nil && string(entry.Status) != *status {
			continue
		}
		if language != nil && (entry.Language == nil || *entry.Language != *language) {
			continue
		}
		if len(tags) > 0 {
			entryTagsLower := make(map[string]bool)
			for _, t := range entry.Tags {
				entryTagsLower[strings.ToLower(t)] = true
			}
			found := false
			for _, tag := range tags {
				if entryTagsLower[strings.ToLower(tag)] {
					found = true
					break
				}
			}
			if !found {
				continue
			}
		}

		// Calculate relevance score
		score := e.calculateScore(entry, queryTokens)
		if score > 0 {
			results = append(results, scoredEntry{entry: entry, score: score})
		}
	}

	// Sort by score (descending) - simple bubble sort for small datasets
	for i := 0; i < len(results); i++ {
		for j := i + 1; j < len(results); j++ {
			if results[j].score > results[i].score {
				results[i], results[j] = results[j], results[i]
			}
		}
	}

	// Limit results
	if len(results) > limit {
		results = results[:limit]
	}

	// Format results
	formatted := make([]SearchResult, 0, len(results))
	for _, r := range results {
		formatted = append(formatted, e.formatResult(r.entry, r.score))
	}

	return formatted, nil
}

// normalizeTokens converts query tokens to lowercase for case-insensitive matching.
func normalizeTokens(tokens []string) []string {
	result := make([]string, 0, len(tokens))
	for _, t := range tokens {
		if t != "" {
			result = append(result, strings.ToLower(t))
		}
	}
	return result
}

// calculateScore calculates relevance score for an entry.
func (e *SearchEngine) calculateScore(entry *models.IndexEntry, queryTokens []string) int {
	// Empty query returns all atoms with base score
	if len(queryTokens) == 0 {
		baseScore := 10
		baseScore += statusPriority[entry.Status] * 5
		baseScore += confidencePriority[entry.Confidence] * 3
		return baseScore
	}

	matchScore := 0
	titleLower := strings.ToLower(entry.Title)

	// Check each token - OR logic with cumulative scoring
	for _, token := range queryTokens {
		// Title match (highest weight per token)
		if strings.Contains(titleLower, token) {
			matchScore += 100
			if strings.HasPrefix(titleLower, token) {
				matchScore += 50
			}
		}

		// Tag match (per token)
		for _, tag := range entry.Tags {
			if strings.Contains(strings.ToLower(tag), token) {
				matchScore += 30
				break // Only count once per token
			}
		}
	}

	// No match found - return 0
	if matchScore == 0 {
		return 0
	}

	// Add status and confidence priority for matched entries
	matchScore += statusPriority[entry.Status] * 5
	matchScore += confidencePriority[entry.Confidence] * 3

	return matchScore
}

// formatResult formats a search result.
func (e *SearchEngine) formatResult(entry *models.IndexEntry, score int) SearchResult {
	result := SearchResult{
		ID:         entry.ID,
		Title:      entry.Title,
		Type:       string(entry.Type),
		Status:     string(entry.Status),
		Confidence: string(entry.Confidence),
		Language:   entry.Language,
		Tags:       entry.Tags,
		UpdatedAt:  entry.UpdatedAt,
		Score:      score,
	}

	// Load atom to get content summary
	atom, err := e.atomStorage.Load(entry.ID)
	if err == nil && atom != nil {
		result.Summary = atom.Content.Summary
	}

	return result
}

// SearchContent performs deep search including atom content.
func (e *SearchEngine) SearchContent(query []string, types []string, tags []string, language, status *string, limit int) ([]SearchResult, error) {
	index, err := e.indexManager.GetIndex()
	if err != nil {
		return nil, err
	}

	type scoredEntry struct {
		entry *models.IndexEntry
		score int
	}

	var results []scoredEntry
	queryTokens := normalizeTokens(query)

	// Convert types to set for fast lookup
	typeSet := make(map[models.AtomType]bool)
	for _, t := range types {
		typeSet[models.AtomType(t)] = true
	}

	for _, entry := range index.Atoms {
		// Apply filters
		if len(typeSet) > 0 && !typeSet[entry.Type] {
			continue
		}
		if status != nil && string(entry.Status) != *status {
			continue
		}
		if language != nil && (entry.Language == nil || *entry.Language != *language) {
			continue
		}
		if len(tags) > 0 {
			entryTagsLower := make(map[string]bool)
			for _, t := range entry.Tags {
				entryTagsLower[strings.ToLower(t)] = true
			}
			found := false
			for _, tag := range tags {
				if entryTagsLower[strings.ToLower(tag)] {
					found = true
					break
				}
			}
			if !found {
				continue
			}
		}

		// Calculate relevance score (including content)
		score := e.calculateContentScore(entry, queryTokens)
		if score > 0 {
			results = append(results, scoredEntry{entry: entry, score: score})
		}
	}

	// Sort by score (descending)
	for i := 0; i < len(results); i++ {
		for j := i + 1; j < len(results); j++ {
			if results[j].score > results[i].score {
				results[i], results[j] = results[j], results[i]
			}
		}
	}

	// Limit results
	if len(results) > limit {
		results = results[:limit]
	}

	// Format results
	formatted := make([]SearchResult, 0, len(results))
	for _, r := range results {
		formatted = append(formatted, e.formatResult(r.entry, r.score))
	}

	return formatted, nil
}

// calculateContentScore calculates relevance score including content search.
func (e *SearchEngine) calculateContentScore(entry *models.IndexEntry, queryTokens []string) int {
	// Empty query returns all atoms with base score
	if len(queryTokens) == 0 {
		baseScore := 10
		baseScore += statusPriority[entry.Status] * 5
		baseScore += confidencePriority[entry.Confidence] * 3
		return baseScore
	}

	// Start with basic score from title/tag matching
	score := e.calculateScore(entry, queryTokens)

	// Also search in content
	atom, err := e.atomStorage.Load(entry.ID)
	if err == nil && atom != nil {
		contentText := strings.ToLower(atom.Content.Summary + " " + atom.Content.Details)
		for _, token := range queryTokens {
			if strings.Contains(contentText, token) {
				// If no title/tag match, give a base content match score
				if score == 0 {
					score = 20
					score += statusPriority[entry.Status] * 5
					score += confidencePriority[entry.Confidence] * 3
				} else {
					score += 20
				}
			}
		}
	}

	return score
}
