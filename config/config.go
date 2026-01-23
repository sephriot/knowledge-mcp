package config

import (
	"os"
	"path/filepath"
)

// Config represents the configuration for the knowledge storage.
type Config struct {
	DataPath string
}

// New creates a new configuration.
func New(dataPath string) *Config {
	if dataPath == "" {
		dataPath = os.Getenv("KNOWLEDGE_MCP_PATH")
		if dataPath == "" {
			dataPath = ".knowledge"
		}
	}

	// Resolve relative paths to absolute paths
	if !filepath.IsAbs(dataPath) {
		cwd, err := os.Getwd()
		if err == nil {
			dataPath = filepath.Join(cwd, dataPath)
		}
	}

	return &Config{
		DataPath: dataPath,
	}
}

// IndexPath returns the path to the index.yaml file.
func (c *Config) IndexPath() string {
	return filepath.Join(c.DataPath, "index.yaml")
}

// IndexPathJSON returns the path to the legacy index.json file.
func (c *Config) IndexPathJSON() string {
	return filepath.Join(c.DataPath, "index.json")
}

// AtomsPath returns the path to the atoms directory.
func (c *Config) AtomsPath() string {
	return filepath.Join(c.DataPath, "atoms")
}

// EnsureDirs ensures the storage directories exist.
func (c *Config) EnsureDirs() error {
	return os.MkdirAll(c.AtomsPath(), 0755)
}

// Global config instance
var globalConfig *Config

// GetConfig returns the global configuration instance.
func GetConfig() *Config {
	if globalConfig == nil {
		globalConfig = New("")
	}
	return globalConfig
}

// SetConfig sets the global configuration instance.
func SetConfig(cfg *Config) {
	globalConfig = cfg
}
