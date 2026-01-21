package tools

import (
	"fmt"
	"time"

	"github.com/sephriot/knowledge-mcp/config"
	"github.com/sephriot/knowledge-mcp/models"
	"github.com/sephriot/knowledge-mcp/storage"
)

// UpsertHandler handles upsert operations.
type UpsertHandler struct {
	config       *config.Config
	indexManager *storage.IndexManager
	atomStorage  *storage.AtomStorage
}

// NewUpsertHandler creates a new upsert handler.
func NewUpsertHandler(cfg *config.Config, indexManager *storage.IndexManager) *UpsertHandler {
	if cfg == nil {
		cfg = config.GetConfig()
	}
	return &UpsertHandler{
		config:       cfg,
		indexManager: indexManager,
		atomStorage:  storage.NewAtomStorage(cfg),
	}
}

// UpsertInput represents the input for an upsert operation.
type UpsertInput struct {
	ID         *string          `json:"id,omitempty"`
	Title      string           `json:"title"`
	Type       models.AtomType  `json:"type"`
	Status     models.AtomStatus `json:"status"`
	Confidence models.Confidence `json:"confidence"`
	Summary    string           `json:"summary"`
	Details    string           `json:"details"`
	Pitfalls   []string         `json:"pitfalls"`
	Language   *string          `json:"language,omitempty"`
	Tags       []string         `json:"tags"`
	Sources    []models.Source  `json:"sources"`
	Links      []models.Link    `json:"links"`
}

// Upsert creates or updates a knowledge atom.
func (h *UpsertHandler) Upsert(input UpsertInput) (map[string]any, error) {
	// Validate enum fields
	if !input.Type.IsValid() {
		return nil, fmt.Errorf("invalid atom type: %s", input.Type)
	}
	if !input.Status.IsValid() {
		return nil, fmt.Errorf("invalid atom status: %s", input.Status)
	}
	if !input.Confidence.IsValid() {
		return nil, fmt.Errorf("invalid confidence level: %s", input.Confidence)
	}

	today := time.Now().Format("2006-01-02")

	// Handle existing atom update
	if input.ID != nil && *input.ID != "" {
		existing, err := h.atomStorage.Load(*input.ID)
		if err != nil {
			return nil, err
		}
		if existing != nil {
			return h.updateAtom(existing, input, today)
		}
	}

	// Create new atom
	var id string
	if input.ID != nil && *input.ID != "" {
		id = *input.ID
	} else {
		var err error
		id, err = h.indexManager.GetNextID()
		if err != nil {
			return nil, err
		}
	}

	// Ensure slices are not nil
	pitfalls := input.Pitfalls
	if pitfalls == nil {
		pitfalls = []string{}
	}
	tags := input.Tags
	if tags == nil {
		tags = []string{}
	}
	sources := input.Sources
	if sources == nil {
		sources = []models.Source{}
	}
	links := input.Links
	if links == nil {
		links = []models.Link{}
	}

	// Build content
	atomContent := models.AtomContent{
		Summary:  input.Summary,
		Details:  input.Details,
		Pitfalls: pitfalls,
		UpdateNotes: []models.UpdateNote{
			{Date: today, Note: "Initial creation"},
		},
	}

	// Build atom
	atom := &models.Atom{
		ID:         id,
		Title:      input.Title,
		Type:       input.Type,
		Status:     input.Status,
		Confidence: input.Confidence,
		Content:    atomContent,
		Language:   input.Language,
		CreatedAt:  today,
		UpdatedAt:  today,
		Tags:       tags,
		Sources:    sources,
		Links:      links,
		Supersedes: []string{},
	}

	// Save atom and update index
	if _, err := h.atomStorage.Save(atom); err != nil {
		return nil, err
	}

	entry := models.NewIndexEntryFromAtom(atom)
	if err := h.indexManager.AddOrUpdate(entry); err != nil {
		return nil, err
	}

	return atomToMap(atom), nil
}

// updateAtom updates an existing atom.
func (h *UpsertHandler) updateAtom(existing *models.Atom, input UpsertInput, today string) (map[string]any, error) {
	// Preserve existing update notes and add new one
	updateNotes := append(existing.Content.UpdateNotes, models.UpdateNote{
		Date: today,
		Note: "Updated",
	})

	// Preserve existing values if input is nil
	pitfalls := input.Pitfalls
	if pitfalls == nil {
		pitfalls = existing.Content.Pitfalls
	}
	tags := input.Tags
	if tags == nil {
		tags = existing.Tags
	}
	sources := input.Sources
	if sources == nil {
		sources = existing.Sources
	}
	links := input.Links
	if links == nil {
		links = existing.Links
	}

	// Build content
	details := input.Details
	if details == "" {
		details = existing.Content.Details
	}

	atomContent := models.AtomContent{
		Summary:     input.Summary,
		Details:     details,
		Pitfalls:    pitfalls,
		UpdateNotes: updateNotes,
	}

	// Build updated atom
	atom := &models.Atom{
		ID:           existing.ID,
		Title:        input.Title,
		Type:         input.Type,
		Status:       input.Status,
		Confidence:   input.Confidence,
		Content:      atomContent,
		Language:     input.Language,
		CreatedAt:    existing.CreatedAt,
		UpdatedAt:    today,
		Tags:         tags,
		Sources:      sources,
		Links:        links,
		Supersedes:   existing.Supersedes,
		SupersededBy: existing.SupersededBy,
	}

	// Save atom and update index
	if _, err := h.atomStorage.Save(atom); err != nil {
		return nil, err
	}

	entry := models.NewIndexEntryFromAtom(atom)
	if err := h.indexManager.AddOrUpdate(entry); err != nil {
		return nil, err
	}

	return atomToMap(atom), nil
}

// atomToMap converts an atom to a map for JSON response.
func atomToMap(atom *models.Atom) map[string]any {
	result := map[string]any{
		"id":         atom.ID,
		"title":      atom.Title,
		"type":       string(atom.Type),
		"status":     string(atom.Status),
		"confidence": string(atom.Confidence),
		"content": map[string]any{
			"summary":      atom.Content.Summary,
			"details":      atom.Content.Details,
			"pitfalls":     atom.Content.Pitfalls,
			"update_notes": atom.Content.UpdateNotes,
		},
		"created_at": atom.CreatedAt,
		"updated_at": atom.UpdatedAt,
		"tags":       atom.Tags,
		"sources":    atom.Sources,
		"links":      atom.Links,
		"supersedes": atom.Supersedes,
	}

	if atom.Language != nil {
		result["language"] = *atom.Language
	}
	if atom.SupersededBy != nil {
		result["superseded_by"] = *atom.SupersededBy
	}

	return result
}
