package main

import (
	"fmt"
	"gopkg.in/yaml.v3"
	"io/ioutil"
	"os"
	"strconv"
	"strings"
)

// Config represents the application configuration
type Config struct {
	APRS     APRSConfig     `yaml:"aprs"`
	Database DatabaseConfig `yaml:"database"`
	Logging  LoggingConfig  `yaml:"logging"`
	Services ServicesConfig `yaml:"services"`
}

// APRSConfig contains APRS-IS connection settings
type APRSConfig struct {
	Callsign        string `yaml:"callsign"`
	Passcode        string `yaml:"passcode"`
	Server          string `yaml:"server"`
	Port            int    `yaml:"port"`
	Filter          string `yaml:"filter"`
	BeaconInterval  int    `yaml:"beacon_interval"`
}

// DatabaseConfig contains PocketBase connection settings
type DatabaseConfig struct {
	URL           string `yaml:"url"`
	AdminEmail    string `yaml:"admin_email"`
	AdminPassword string `yaml:"admin_password"`
}

// LoggingConfig contains logging settings
type LoggingConfig struct {
	Level  string `yaml:"level"`
	Format string `yaml:"format"`
	Output string `yaml:"output"`
}

// ServicesConfig contains service-specific settings
type ServicesConfig struct {
	APRSConnector APRSConnectorConfig `yaml:"aprs_connector"`
}

// APRSConnectorConfig contains APRS connector specific settings
type APRSConnectorConfig struct {
	Enabled           bool `yaml:"enabled"`
	ReconnectDelay    int  `yaml:"reconnect_delay"`
	HeartbeatInterval int  `yaml:"heartbeat_interval"`
}

// LoadConfig loads configuration from file and environment variables
func LoadConfig(configPath string) (*Config, error) {
	config := &Config{
		// Set defaults
		APRS: APRSConfig{
			Callsign:       "RARSMS",
			Server:         "rotate.aprs2.net",
			Port:           14580,
			Filter:         "t/m",
			BeaconInterval: 1800,
		},
		Database: DatabaseConfig{
			URL: "http://pocketbase:8090",
		},
		Logging: LoggingConfig{
			Level:  "info",
			Format: "json",
			Output: "stdout",
		},
		Services: ServicesConfig{
			APRSConnector: APRSConnectorConfig{
				Enabled:           true,
				ReconnectDelay:    30,
				HeartbeatInterval: 300,
			},
		},
	}

	// Load from config file if it exists
	if configPath != "" {
		if _, err := os.Stat(configPath); err == nil {
			data, err := ioutil.ReadFile(configPath)
			if err != nil {
				return nil, fmt.Errorf("failed to read config file: %w", err)
			}

			if err := yaml.Unmarshal(data, config); err != nil {
				return nil, fmt.Errorf("failed to parse config file: %w", err)
			}
		}
	}

	// Override with environment variables
	loadEnvOverrides(config)

	// Validate configuration
	if err := validateConfig(config); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}

	return config, nil
}

// loadEnvOverrides loads configuration overrides from environment variables
func loadEnvOverrides(config *Config) {
	// APRS configuration
	if val := os.Getenv("APRS_CALLSIGN"); val != "" {
		config.APRS.Callsign = strings.ToUpper(val)
	}
	if val := os.Getenv("APRS_PASSCODE"); val != "" {
		config.APRS.Passcode = val
	}
	if val := os.Getenv("APRS_SERVER"); val != "" {
		config.APRS.Server = val
	}
	if val := os.Getenv("APRS_PORT"); val != "" {
		if port, err := strconv.Atoi(val); err == nil {
			config.APRS.Port = port
		}
	}
	if val := os.Getenv("APRS_FILTER"); val != "" {
		config.APRS.Filter = val
	}

	// Database configuration
	if val := os.Getenv("DATABASE_URL"); val != "" {
		config.Database.URL = val
	}
	if val := os.Getenv("DATABASE_ADMIN_EMAIL"); val != "" {
		config.Database.AdminEmail = val
	}
	if val := os.Getenv("DATABASE_ADMIN_PASSWORD"); val != "" {
		config.Database.AdminPassword = val
	}

	// Logging configuration
	if val := os.Getenv("LOG_LEVEL"); val != "" {
		config.Logging.Level = strings.ToLower(val)
	}
	if val := os.Getenv("LOG_FORMAT"); val != "" {
		config.Logging.Format = strings.ToLower(val)
	}

	// Services configuration
	if val := os.Getenv("APRS_CONNECTOR_ENABLED"); val != "" {
		config.Services.APRSConnector.Enabled = val == "true"
	}
	if val := os.Getenv("APRS_CONNECTOR_RECONNECT_DELAY"); val != "" {
		if delay, err := strconv.Atoi(val); err == nil {
			config.Services.APRSConnector.ReconnectDelay = delay
		}
	}
}

// validateConfig validates the configuration
func validateConfig(config *Config) error {
	// Validate APRS configuration
	if config.APRS.Callsign == "" {
		return fmt.Errorf("APRS callsign is required")
	}
	if config.APRS.Passcode == "" {
		return fmt.Errorf("APRS passcode is required")
	}
	if config.APRS.Server == "" {
		return fmt.Errorf("APRS server is required")
	}
	if config.APRS.Port <= 0 || config.APRS.Port > 65535 {
		return fmt.Errorf("APRS port must be between 1 and 65535")
	}

	// Validate database configuration
	if config.Database.URL == "" {
		return fmt.Errorf("database URL is required")
	}

	// Validate logging configuration
	validLogLevels := map[string]bool{
		"debug": true, "info": true, "warn": true, "error": true, "fatal": true,
	}
	if !validLogLevels[config.Logging.Level] {
		return fmt.Errorf("invalid log level: %s", config.Logging.Level)
	}

	validLogFormats := map[string]bool{
		"json": true, "text": true,
	}
	if !validLogFormats[config.Logging.Format] {
		return fmt.Errorf("invalid log format: %s", config.Logging.Format)
	}

	return nil
}

// GetAPRSPasscode calculates APRS passcode for a given callsign
func GetAPRSPasscode(callsign string) int {
	callsign = strings.ToUpper(callsign)

	// Remove SSID if present
	if idx := strings.Index(callsign, "-"); idx != -1 {
		callsign = callsign[:idx]
	}

	hash := 0x73e2
	for i := 0; i < len(callsign); i += 2 {
		hash ^= int(callsign[i]) << 8
		if i+1 < len(callsign) {
			hash ^= int(callsign[i+1])
		}
	}

	return hash & 0x7fff
}