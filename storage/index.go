package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"gopkg.in/yaml.v3"

	"github.com/sephriot/knowledge-mcp/config"
	"github.com/sephriot/knowledge-mcp/models"
)

// IndexManager manages the knowledge index file.
type IndexManager struct {
	config *config.Config
	index  *models.Index
	mu     sync.RWMutex
}

// NewIndexManager creates a new index manager.
func NewIndexManager(cfg *config.Config) *IndexManager {
	if cfg == nil {
		cfg = config.GetConfig()
	}
	return &IndexManager{config: cfg}
}

// loadLocked loads the index from disk. Caller must hold the lock.
// Tries YAML first, falls back to JSON for backward compatibility.
func (m *IndexManager) loadLocked() error {
	if m.index != nil {
		return nil
	}

	indexPath := m.config.IndexPath()
	indexPathJSON := m.config.IndexPathJSON()

	// Try YAML first
	if data, err := os.ReadFile(indexPath); err == nil {
		var index models.Index
		if err := yaml.Unmarshal(data, &index); err != nil {
			return fmt.Errorf("failed to unmarshal YAML index: %w", err)
		}
		m.index = &index
		return nil
	}

	// Fall back to JSON
	data, err := os.ReadFile(indexPathJSON)
	if err != nil {
		if os.IsNotExist(err) {
			m.index = models.NewEmptyIndex()
			return nil
		}
		return fmt.Errorf("failed to read index file: %w", err)
	}

	var index models.Index
	if err := json.Unmarshal(data, &index); err != nil {
		return fmt.Errorf("failed to unmarshal JSON index: %w", err)
	}

	m.index = &index
	return nil
}

// saveLocked saves the index to disk in YAML format. Caller must hold the lock.
// If a legacy JSON index file exists, it is deleted.
func (m *IndexManager) saveLocked() error {
	if m.index == nil {
		return nil
	}

	if err := m.config.EnsureDirs(); err != nil {
		return fmt.Errorf("failed to create directories: %w", err)
	}

	indexPath := m.config.IndexPath()
	indexPathJSON := m.config.IndexPathJSON()

	data, err := yaml.Marshal(m.index)
	if err != nil {
		return fmt.Errorf("failed to marshal index to YAML: %w", err)
	}

	if err := os.WriteFile(indexPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write index file: %w", err)
	}

	// Clean up legacy JSON index file if it exists
	if _, err := os.Stat(indexPathJSON); err == nil {
		os.Remove(indexPathJSON) // Best effort, ignore errors
	}

	return nil
}

// Load loads the index from disk.
func (m *IndexManager) Load() (*models.Index, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if err := m.loadLocked(); err != nil {
		return nil, err
	}
	return m.index, nil
}

// Save saves the index to disk.
func (m *IndexManager) Save() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	return m.saveLocked()
}

// GetIndex gets the current index, loading if necessary.
func (m *IndexManager) GetIndex() (*models.Index, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if err := m.loadLocked(); err != nil {
		return nil, err
	}
	return m.index, nil
}

// AddOrUpdate adds or updates an entry in the index.
func (m *IndexManager) AddOrUpdate(entry *models.IndexEntry) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if err := m.loadLocked(); err != nil {
		return err
	}
	m.index.AddOrUpdate(entry)
	return m.saveLocked()
}

// Remove removes an entry from the index.
func (m *IndexManager) Remove(atomID string) (bool, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if err := m.loadLocked(); err != nil {
		return false, err
	}
	result := m.index.Remove(atomID)
	if result {
		if err := m.saveLocked(); err != nil {
			return false, err
		}
	}
	return result, nil
}

// FindByID finds an entry by ID.
func (m *IndexManager) FindByID(atomID string) (*models.IndexEntry, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if err := m.loadLocked(); err != nil {
		return nil, err
	}
	return m.index.FindByID(atomID), nil
}

// GetNextID gets the next available atom ID.
func (m *IndexManager) GetNextID() (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if err := m.loadLocked(); err != nil {
		return "", err
	}
	return m.index.GetNextID(), nil
}

// RebuildFromAtoms rebuilds the index from atom files.
func (m *IndexManager) RebuildFromAtoms(atomsPath string) (*models.Index, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.index = models.NewEmptyIndex()

	if _, err := os.Stat(atomsPath); os.IsNotExist(err) {
		if err := m.saveLocked(); err != nil {
			return nil, err
		}
		return m.index, nil
	}

	storage := NewAtomStorage(m.config)

	entries, err := os.ReadDir(atomsPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read atoms directory: %w", err)
	}

	// Collect unique atom IDs (may have both .yaml and .json for same atom)
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

	var loadErrors []string
	for atomID := range idSet {
		atom, err := storage.Load(atomID)
		if err != nil {
			loadErrors = append(loadErrors, fmt.Sprintf("%s: %v", atomID, err))
			continue
		}
		if atom != nil {
			indexEntry := models.NewIndexEntryFromAtom(atom)
			m.index.AddOrUpdate(indexEntry)
		}
	}

	// Log any errors to stderr (MCP uses stdout for communication)
	if len(loadErrors) > 0 {
		fmt.Fprintf(os.Stderr, "Warning: failed to load %d atoms during rebuild:\n", len(loadErrors))
		for _, e := range loadErrors {
			fmt.Fprintf(os.Stderr, "  - %s\n", e)
		}
	}

	if err := m.saveLocked(); err != nil {
		return nil, err
	}

	return m.index, nil
}

// MigrateAndRebuild migrates all JSON atoms to YAML and rebuilds the index.
func (m *IndexManager) MigrateAndRebuild(atomsPath string) (*models.Index, int, error) {
	storage := NewAtomStorage(m.config)

	// Collect all JSON files that need migration
	entries, err := os.ReadDir(atomsPath)
	if err != nil && !os.IsNotExist(err) {
		return nil, 0, fmt.Errorf("failed to read atoms directory: %w", err)
	}

	var migrated int
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if !strings.HasPrefix(name, "K-") || !strings.HasSuffix(name, ".json") {
			continue
		}

		atomID := strings.TrimSuffix(name, ".json")
		yamlPath := filepath.Join(atomsPath, atomID+".yaml")

		// Skip if YAML already exists
		if _, err := os.Stat(yamlPath); err == nil {
			continue
		}

		// Load from JSON (will use JSON since YAML doesn't exist)
		atom, err := storage.Load(atomID)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Warning: failed to load %s for migration: %v\n", atomID, err)
			continue
		}
		if atom == nil {
			continue
		}

		// Save as YAML (this also deletes the JSON file)
		if _, err := storage.Save(atom); err != nil {
			fmt.Fprintf(os.Stderr, "Warning: failed to migrate %s: %v\n", atomID, err)
			continue
		}
		migrated++
	}

	// Now rebuild the index
	index, err := m.RebuildFromAtoms(atomsPath)
	return index, migrated, err
}

// InvalidateCache invalidates the cached index.
func (m *IndexManager) InvalidateCache() {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.index = nil
}

// GetConfig returns the config.
func (m *IndexManager) GetConfig() *config.Config {
	return m.config
}
