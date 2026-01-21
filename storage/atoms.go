package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/sephriot/knowledge-mcp/config"
	"github.com/sephriot/knowledge-mcp/models"
)

// AtomStorage manages atom file storage.
type AtomStorage struct {
	config *config.Config
}

// NewAtomStorage creates a new atom storage.
func NewAtomStorage(cfg *config.Config) *AtomStorage {
	if cfg == nil {
		cfg = config.GetConfig()
	}
	return &AtomStorage{config: cfg}
}

// getAtomPath returns the path for an atom file.
func (s *AtomStorage) getAtomPath(atomID string) string {
	return filepath.Join(s.config.AtomsPath(), fmt.Sprintf("%s.json", atomID))
}

// Save saves an atom to disk.
func (s *AtomStorage) Save(atom *models.Atom) (string, error) {
	if err := s.config.EnsureDirs(); err != nil {
		return "", fmt.Errorf("failed to create directories: %w", err)
	}

	atomPath := s.getAtomPath(atom.ID)

	data, err := json.MarshalIndent(atom, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal atom: %w", err)
	}

	if err := os.WriteFile(atomPath, data, 0644); err != nil {
		return "", fmt.Errorf("failed to write atom file: %w", err)
	}

	return atomPath, nil
}

// Load loads an atom from disk.
func (s *AtomStorage) Load(atomID string) (*models.Atom, error) {
	atomPath := s.getAtomPath(atomID)

	data, err := os.ReadFile(atomPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to read atom file: %w", err)
	}

	var atom models.Atom
	if err := json.Unmarshal(data, &atom); err != nil {
		return nil, fmt.Errorf("failed to unmarshal atom: %w", err)
	}

	return &atom, nil
}

// Delete deletes an atom file from disk.
func (s *AtomStorage) Delete(atomID string) (bool, error) {
	atomPath := s.getAtomPath(atomID)

	if _, err := os.Stat(atomPath); os.IsNotExist(err) {
		return false, nil
	}

	if err := os.Remove(atomPath); err != nil {
		return false, fmt.Errorf("failed to delete atom file: %w", err)
	}

	return true, nil
}

// Exists checks if an atom file exists.
func (s *AtomStorage) Exists(atomID string) bool {
	atomPath := s.getAtomPath(atomID)
	_, err := os.Stat(atomPath)
	return err == nil
}

// ListAllIDs lists all atom IDs in storage.
func (s *AtomStorage) ListAllIDs() ([]string, error) {
	atomsPath := s.config.AtomsPath()

	if _, err := os.Stat(atomsPath); os.IsNotExist(err) {
		return []string{}, nil
	}

	entries, err := os.ReadDir(atomsPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read atoms directory: %w", err)
	}

	var ids []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if strings.HasPrefix(name, "K-") && strings.HasSuffix(name, ".json") {
			ids = append(ids, strings.TrimSuffix(name, ".json"))
		}
	}

	return ids, nil
}
