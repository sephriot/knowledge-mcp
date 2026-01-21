package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"sync"

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
func (m *IndexManager) loadLocked() error {
	if m.index != nil {
		return nil
	}

	indexPath := m.config.IndexPath()

	data, err := os.ReadFile(indexPath)
	if err != nil {
		if os.IsNotExist(err) {
			m.index = models.NewEmptyIndex()
			return nil
		}
		return fmt.Errorf("failed to read index file: %w", err)
	}

	var index models.Index
	if err := json.Unmarshal(data, &index); err != nil {
		return fmt.Errorf("failed to unmarshal index: %w", err)
	}

	m.index = &index
	return nil
}

// saveLocked saves the index to disk. Caller must hold the lock.
func (m *IndexManager) saveLocked() error {
	if m.index == nil {
		return nil
	}

	if err := m.config.EnsureDirs(); err != nil {
		return fmt.Errorf("failed to create directories: %w", err)
	}

	indexPath := m.config.IndexPath()

	data, err := json.MarshalIndent(m.index, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal index: %w", err)
	}

	if err := os.WriteFile(indexPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write index file: %w", err)
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

	var loadErrors []string
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		name := entry.Name()
		if !strings.HasPrefix(name, "K-") || !strings.HasSuffix(name, ".json") {
			continue
		}

		atomID := strings.TrimSuffix(name, ".json")
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
