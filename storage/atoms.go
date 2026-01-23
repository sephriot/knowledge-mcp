package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"

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

// getAtomPathYAML returns the YAML path for an atom file.
func (s *AtomStorage) getAtomPathYAML(atomID string) string {
	return filepath.Join(s.config.AtomsPath(), fmt.Sprintf("%s.yaml", atomID))
}

// getAtomPathJSON returns the legacy JSON path for an atom file.
func (s *AtomStorage) getAtomPathJSON(atomID string) string {
	return filepath.Join(s.config.AtomsPath(), fmt.Sprintf("%s.json", atomID))
}

// Save saves an atom to disk in YAML format.
// If a legacy JSON file exists, it is deleted after successful YAML write.
func (s *AtomStorage) Save(atom *models.Atom) (string, error) {
	if err := s.config.EnsureDirs(); err != nil {
		return "", fmt.Errorf("failed to create directories: %w", err)
	}

	yamlPath := s.getAtomPathYAML(atom.ID)
	jsonPath := s.getAtomPathJSON(atom.ID)

	data, err := yaml.Marshal(atom)
	if err != nil {
		return "", fmt.Errorf("failed to marshal atom to YAML: %w", err)
	}

	if err := os.WriteFile(yamlPath, data, 0644); err != nil {
		return "", fmt.Errorf("failed to write atom file: %w", err)
	}

	// Clean up legacy JSON file if it exists
	if _, err := os.Stat(jsonPath); err == nil {
		os.Remove(jsonPath) // Best effort, ignore errors
	}

	return yamlPath, nil
}

// Load loads an atom from disk.
// Tries YAML first, falls back to JSON for backward compatibility.
func (s *AtomStorage) Load(atomID string) (*models.Atom, error) {
	yamlPath := s.getAtomPathYAML(atomID)
	jsonPath := s.getAtomPathJSON(atomID)

	// Try YAML first
	if data, err := os.ReadFile(yamlPath); err == nil {
		var atom models.Atom
		if err := yaml.Unmarshal(data, &atom); err != nil {
			return nil, fmt.Errorf("failed to unmarshal YAML atom: %w", err)
		}
		return &atom, nil
	}

	// Fall back to JSON
	data, err := os.ReadFile(jsonPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("failed to read atom file: %w", err)
	}

	var atom models.Atom
	if err := json.Unmarshal(data, &atom); err != nil {
		return nil, fmt.Errorf("failed to unmarshal JSON atom: %w", err)
	}

	return &atom, nil
}

// Delete deletes an atom file from disk (both YAML and JSON versions).
func (s *AtomStorage) Delete(atomID string) (bool, error) {
	yamlPath := s.getAtomPathYAML(atomID)
	jsonPath := s.getAtomPathJSON(atomID)

	yamlExists := false
	jsonExists := false

	if _, err := os.Stat(yamlPath); err == nil {
		yamlExists = true
	}
	if _, err := os.Stat(jsonPath); err == nil {
		jsonExists = true
	}

	if !yamlExists && !jsonExists {
		return false, nil
	}

	if yamlExists {
		if err := os.Remove(yamlPath); err != nil {
			return false, fmt.Errorf("failed to delete YAML atom file: %w", err)
		}
	}
	if jsonExists {
		if err := os.Remove(jsonPath); err != nil {
			return false, fmt.Errorf("failed to delete JSON atom file: %w", err)
		}
	}

	return true, nil
}

// Exists checks if an atom file exists (YAML or JSON).
func (s *AtomStorage) Exists(atomID string) bool {
	yamlPath := s.getAtomPathYAML(atomID)
	jsonPath := s.getAtomPathJSON(atomID)

	if _, err := os.Stat(yamlPath); err == nil {
		return true
	}
	if _, err := os.Stat(jsonPath); err == nil {
		return true
	}
	return false
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

	// Use a map to deduplicate IDs (in case both .yaml and .json exist)
	idSet := make(map[string]bool)
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if !strings.HasPrefix(name, "K-") {
			continue
		}
		if strings.HasSuffix(name, ".yaml") {
			idSet[strings.TrimSuffix(name, ".yaml")] = true
		} else if strings.HasSuffix(name, ".json") {
			idSet[strings.TrimSuffix(name, ".json")] = true
		}
	}

	ids := make([]string, 0, len(idSet))
	for id := range idSet {
		ids = append(ids, id)
	}

	return ids, nil
}
