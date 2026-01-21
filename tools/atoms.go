package tools

import (
	"fmt"
	"sort"
	"time"

	"github.com/sephriot/knowledge-mcp/config"
	"github.com/sephriot/knowledge-mcp/models"
	"github.com/sephriot/knowledge-mcp/storage"
)

// AtomTools provides tools for managing knowledge atoms.
type AtomTools struct {
	config       *config.Config
	indexManager *storage.IndexManager
	atomStorage  *storage.AtomStorage
}

// NewAtomTools creates a new atom tools instance.
func NewAtomTools(cfg *config.Config) *AtomTools {
	if cfg == nil {
		cfg = config.GetConfig()
	}
	return &AtomTools{
		config:       cfg,
		indexManager: storage.NewIndexManager(cfg),
		atomStorage:  storage.NewAtomStorage(cfg),
	}
}

// GetAtom gets full atom content by ID.
func (t *AtomTools) GetAtom(id string) (map[string]any, error) {
	atom, err := t.atomStorage.Load(id)
	if err != nil {
		return nil, err
	}
	if atom == nil {
		return nil, nil
	}
	return atomToMap(atom), nil
}

// ListAtomsResult represents a list result entry.
type ListAtomsResult struct {
	ID         string   `json:"id"`
	Title      string   `json:"title"`
	Type       string   `json:"type"`
	Status     string   `json:"status"`
	Confidence string   `json:"confidence"`
	Language   *string  `json:"language,omitempty"`
	Tags       []string `json:"tags"`
	UpdatedAt  string   `json:"updated_at"`
}

// ListAtoms lists atoms with optional filtering.
func (t *AtomTools) ListAtoms(types []string, tags []string, status, language *string, limit int) ([]ListAtomsResult, error) {
	index, err := t.indexManager.GetIndex()
	if err != nil {
		return nil, err
	}

	// Convert types to set for fast lookup
	typeSet := make(map[models.AtomType]bool)
	for _, typ := range types {
		typeSet[models.AtomType(typ)] = true
	}

	var results []ListAtomsResult

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
				entryTagsLower[t] = true
			}
			found := false
			for _, tag := range tags {
				if entryTagsLower[tag] {
					found = true
					break
				}
			}
			if !found {
				continue
			}
		}

		results = append(results, ListAtomsResult{
			ID:         entry.ID,
			Title:      entry.Title,
			Type:       string(entry.Type),
			Status:     string(entry.Status),
			Confidence: string(entry.Confidence),
			Language:   entry.Language,
			Tags:       entry.Tags,
			UpdatedAt:  entry.UpdatedAt,
		})

		if len(results) >= limit {
			break
		}
	}

	return results, nil
}

// DeleteAtom deprecates an atom (sets status to deprecated).
func (t *AtomTools) DeleteAtom(id string) (map[string]any, error) {
	atom, err := t.atomStorage.Load(id)
	if err != nil {
		return nil, err
	}
	if atom == nil {
		return map[string]any{
			"success": false,
			"error":   fmt.Sprintf("Atom %s not found", id),
		}, nil
	}

	// Set status to deprecated
	today := time.Now().Format("2006-01-02")
	atom.Status = models.AtomStatusDeprecated
	atom.UpdatedAt = today

	// Save updated atom
	if _, err := t.atomStorage.Save(atom); err != nil {
		return nil, err
	}

	// Update index
	entry := models.NewIndexEntryFromAtom(atom)
	if err := t.indexManager.AddOrUpdate(entry); err != nil {
		return nil, err
	}

	return map[string]any{
		"success": true,
		"message": fmt.Sprintf("Atom %s deprecated", id),
	}, nil
}

// PurgeAtom permanently deletes an atom from storage.
func (t *AtomTools) PurgeAtom(id string) (map[string]any, error) {
	if !t.atomStorage.Exists(id) {
		return map[string]any{
			"success": false,
			"error":   fmt.Sprintf("Atom %s not found", id),
		}, nil
	}

	// Delete from storage
	if _, err := t.atomStorage.Delete(id); err != nil {
		return nil, err
	}

	// Remove from index
	if _, err := t.indexManager.Remove(id); err != nil {
		return nil, err
	}

	return map[string]any{
		"success": true,
		"message": fmt.Sprintf("Atom %s permanently deleted", id),
	}, nil
}

// ListAllIDs lists all atom IDs in storage.
func (t *AtomTools) ListAllIDs() (map[string]any, error) {
	ids, err := t.atomStorage.ListAllIDs()
	if err != nil {
		return nil, err
	}

	sort.Strings(ids)

	return map[string]any{
		"ids":   ids,
		"count": len(ids),
	}, nil
}

// GetNextID gets the next available atom ID.
func (t *AtomTools) GetNextID() (map[string]any, error) {
	nextID, err := t.indexManager.GetNextID()
	if err != nil {
		return nil, err
	}

	return map[string]any{
		"next_id": nextID,
	}, nil
}

// ExportAll exports all knowledge as a single structure.
func (t *AtomTools) ExportAll(format string) (map[string]any, error) {
	if format != "json" {
		return map[string]any{
			"error": fmt.Sprintf("Unsupported format: %s", format),
		}, nil
	}

	index, err := t.indexManager.GetIndex()
	if err != nil {
		return nil, err
	}

	atoms := make([]map[string]any, 0)

	for _, entry := range index.Atoms {
		atom, err := t.atomStorage.Load(entry.ID)
		if err != nil {
			continue
		}
		if atom != nil {
			atoms = append(atoms, atomToMap(atom))
		}
	}

	return map[string]any{
		"version":     1,
		"exported_at": time.Now().Format("2006-01-02"),
		"count":       len(atoms),
		"atoms":       atoms,
	}, nil
}

// RebuildIndex rebuilds index.json from atom files.
func (t *AtomTools) RebuildIndex() (map[string]any, error) {
	index, err := t.indexManager.RebuildFromAtoms(t.config.AtomsPath())
	if err != nil {
		return nil, err
	}

	return map[string]any{
		"success": true,
		"count":   len(index.Atoms),
		"message": fmt.Sprintf("Index rebuilt with %d atoms", len(index.Atoms)),
	}, nil
}

// GetSummary gets summary of knowledge grouped by type, tag, or language.
func (t *AtomTools) GetSummary(groupBy string) (map[string]any, error) {
	index, err := t.indexManager.GetIndex()
	if err != nil {
		return nil, err
	}

	groups := make(map[string][]map[string]any)

	for _, entry := range index.Atoms {
		switch groupBy {
		case "type":
			key := string(entry.Type)
			groups[key] = append(groups[key], map[string]any{
				"id":     entry.ID,
				"title":  entry.Title,
				"status": string(entry.Status),
			})
		case "tag":
			for _, tag := range entry.Tags {
				groups[tag] = append(groups[tag], map[string]any{
					"id":    entry.ID,
					"title": entry.Title,
					"type":  string(entry.Type),
				})
			}
		case "language":
			key := "unspecified"
			if entry.Language != nil {
				key = *entry.Language
			}
			groups[key] = append(groups[key], map[string]any{
				"id":    entry.ID,
				"title": entry.Title,
				"type":  string(entry.Type),
			})
		default:
			return map[string]any{
				"error": fmt.Sprintf("Invalid group_by value: %s", groupBy),
			}, nil
		}
	}

	// Build summary with counts
	groupsResult := make(map[string]any)
	for key, items := range groups {
		groupsResult[key] = map[string]any{
			"count": len(items),
			"items": items,
		}
	}

	return map[string]any{
		"group_by":    groupBy,
		"total_atoms": len(index.Atoms),
		"groups":      groupsResult,
	}, nil
}
