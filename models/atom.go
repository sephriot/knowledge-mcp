package models

import (
	"fmt"
	"time"
)

// AtomType represents the type of knowledge atom.
type AtomType string

const (
	AtomTypeFact      AtomType = "fact"
	AtomTypeDecision  AtomType = "decision"
	AtomTypeProcedure AtomType = "procedure"
	AtomTypePattern   AtomType = "pattern"
	AtomTypeGotcha    AtomType = "gotcha"
	AtomTypeGlossary  AtomType = "glossary"
	AtomTypeSnippet   AtomType = "snippet"
)

// ValidAtomTypes returns all valid atom types.
func ValidAtomTypes() []AtomType {
	return []AtomType{
		AtomTypeFact, AtomTypeDecision, AtomTypeProcedure,
		AtomTypePattern, AtomTypeGotcha, AtomTypeGlossary, AtomTypeSnippet,
	}
}

// IsValid checks if the atom type is valid.
func (t AtomType) IsValid() bool {
	for _, valid := range ValidAtomTypes() {
		if t == valid {
			return true
		}
	}
	return false
}

// AtomStatus represents the status of a knowledge atom.
type AtomStatus string

const (
	AtomStatusActive     AtomStatus = "active"
	AtomStatusDraft      AtomStatus = "draft"
	AtomStatusDeprecated AtomStatus = "deprecated"
)

// ValidAtomStatuses returns all valid atom statuses.
func ValidAtomStatuses() []AtomStatus {
	return []AtomStatus{AtomStatusActive, AtomStatusDraft, AtomStatusDeprecated}
}

// IsValid checks if the atom status is valid.
func (s AtomStatus) IsValid() bool {
	for _, valid := range ValidAtomStatuses() {
		if s == valid {
			return true
		}
	}
	return false
}

// Confidence represents the confidence level of a knowledge atom.
type Confidence string

const (
	ConfidenceHigh   Confidence = "high"
	ConfidenceMedium Confidence = "medium"
	ConfidenceLow    Confidence = "low"
)

// ValidConfidences returns all valid confidence levels.
func ValidConfidences() []Confidence {
	return []Confidence{ConfidenceHigh, ConfidenceMedium, ConfidenceLow}
}

// IsValid checks if the confidence level is valid.
func (c Confidence) IsValid() bool {
	for _, valid := range ValidConfidences() {
		if c == valid {
			return true
		}
	}
	return false
}

// SourceKind represents the kind of source reference.
type SourceKind string

const (
	SourceKindRepoPath     SourceKind = "repo_path"
	SourceKindTicket       SourceKind = "ticket"
	SourceKindURL          SourceKind = "url"
	SourceKindConversation SourceKind = "conversation"
)

// Source represents a reference source for a knowledge atom.
type Source struct {
	Kind SourceKind `json:"kind"`
	Ref  string     `json:"ref"`
}

// LinkRel represents the relationship type of a link.
type LinkRel string

const (
	LinkRelDependsOn   LinkRel = "depends_on"
	LinkRelSeeAlso     LinkRel = "see_also"
	LinkRelContradicts LinkRel = "contradicts"
)

// Link represents a link to another knowledge atom.
type Link struct {
	Rel LinkRel `json:"rel"`
	ID  string  `json:"id"`
}

// UpdateNote represents a note about an update to the atom.
type UpdateNote struct {
	Date string `json:"date"`
	Note string `json:"note"`
}

// AtomContent represents the content of a knowledge atom.
type AtomContent struct {
	Summary     string       `json:"summary"`
	Details     string       `json:"details"`
	Pitfalls    []string     `json:"pitfalls"`
	UpdateNotes []UpdateNote `json:"update_notes"`
}

// Atom represents a knowledge atom - the fundamental unit of knowledge storage.
type Atom struct {
	ID           string      `json:"id"`
	Title        string      `json:"title"`
	Type         AtomType    `json:"type"`
	Status       AtomStatus  `json:"status"`
	Confidence   Confidence  `json:"confidence"`
	Content      AtomContent `json:"content"`
	Language     *string     `json:"language,omitempty"`
	CreatedAt    string      `json:"created_at"`
	UpdatedAt    string      `json:"updated_at"`
	Tags         []string    `json:"tags"`
	Sources      []Source    `json:"sources"`
	Links        []Link      `json:"links"`
	Supersedes   []string    `json:"supersedes"`
	SupersededBy *string     `json:"superseded_by,omitempty"`
}

// IndexEntry represents an entry in the index for fast lookup.
type IndexEntry struct {
	ID         string     `json:"id"`
	Title      string     `json:"title"`
	Type       AtomType   `json:"type"`
	Status     AtomStatus `json:"status"`
	Confidence Confidence `json:"confidence"`
	Language   *string    `json:"language,omitempty"`
	Tags       []string   `json:"tags"`
	Path       string     `json:"path"`
	UpdatedAt  string     `json:"updated_at"`
}

// NewIndexEntryFromAtom creates an index entry from an atom.
func NewIndexEntryFromAtom(atom *Atom) *IndexEntry {
	return &IndexEntry{
		ID:         atom.ID,
		Title:      atom.Title,
		Type:       atom.Type,
		Status:     atom.Status,
		Confidence: atom.Confidence,
		Language:   atom.Language,
		Tags:       atom.Tags,
		Path:       fmt.Sprintf("atoms/%s.json", atom.ID),
		UpdatedAt:  atom.UpdatedAt,
	}
}

// Index represents the index of all knowledge atoms for fast lookup.
type Index struct {
	Version   int           `json:"version"`
	UpdatedAt string        `json:"updated_at"`
	Atoms     []*IndexEntry `json:"atoms"`
}

// NewEmptyIndex creates a new empty index.
func NewEmptyIndex() *Index {
	return &Index{
		Version:   1,
		UpdatedAt: time.Now().UTC().Format(time.RFC3339),
		Atoms:     []*IndexEntry{},
	}
}

// FindByID finds an entry by ID.
func (idx *Index) FindByID(atomID string) *IndexEntry {
	for _, entry := range idx.Atoms {
		if entry.ID == atomID {
			return entry
		}
	}
	return nil
}

// AddOrUpdate adds or updates an entry in the index.
func (idx *Index) AddOrUpdate(entry *IndexEntry) {
	for i, existing := range idx.Atoms {
		if existing.ID == entry.ID {
			idx.Atoms[i] = entry
			idx.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
			return
		}
	}
	idx.Atoms = append(idx.Atoms, entry)
	idx.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
}

// Remove removes an entry from the index.
func (idx *Index) Remove(atomID string) bool {
	for i, entry := range idx.Atoms {
		if entry.ID == atomID {
			idx.Atoms = append(idx.Atoms[:i], idx.Atoms[i+1:]...)
			idx.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
			return true
		}
	}
	return false
}

// GetNextID gets the next available atom ID.
func (idx *Index) GetNextID() string {
	if len(idx.Atoms) == 0 {
		return "K-000001"
	}

	maxNum := 0
	for _, entry := range idx.Atoms {
		var num int
		_, _ = fmt.Sscanf(entry.ID, "K-%d", &num)
		if num > maxNum {
			maxNum = num
		}
	}

	return fmt.Sprintf("K-%06d", maxNum+1)
}
