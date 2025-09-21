package main

import (
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
)

// generateCorrelationID generates a unique correlation ID for message tracking
func generateCorrelationID() string {
	return fmt.Sprintf("aprs_%d_%s", time.Now().Unix(), uuid.New().String()[:8])
}

// setupLogger configures the logger based on configuration
func setupLogger(config *Config) *logrus.Logger {
	logger := logrus.New()

	// Set log level
	level, err := logrus.ParseLevel(config.Logging.Level)
	if err != nil {
		level = logrus.InfoLevel
	}
	logger.SetLevel(level)

	// Set log format
	if config.Logging.Format == "json" {
		logger.SetFormatter(&logrus.JSONFormatter{
			TimestampFormat: time.RFC3339,
		})
	} else {
		logger.SetFormatter(&logrus.TextFormatter{
			FullTimestamp:   true,
			TimestampFormat: time.RFC3339,
		})
	}

	return logger
}

// validateAPRSCallsign validates an APRS callsign format
func validateAPRSCallsign(callsign string) bool {
	if len(callsign) < 3 || len(callsign) > 9 {
		return false
	}

	// Basic pattern: 1-2 letters, 1 digit, 0-3 letters/digits
	// Examples: W4ABC, K4XYZ, VE3ABC, etc.
	for i, char := range callsign {
		if i == 0 || i == 1 {
			// First 1-2 characters must be letters
			if char < 'A' || char > 'Z' {
				if i == 1 && char >= '0' && char <= '9' {
					// Second character can be a digit
					continue
				}
				return false
			}
		} else {
			// Rest can be letters or digits
			if !((char >= 'A' && char <= 'Z') || (char >= '0' && char <= '9')) {
				return false
			}
		}
	}

	return true
}

// truncateForAPRS truncates a message to fit APRS limits
func truncateForAPRS(content string, maxLength int) string {
	if len(content) <= maxLength {
		return content
	}

	// Truncate and add ellipsis
	return content[:maxLength-3] + "..."
}

// retryWithBackoff executes a function with exponential backoff
func retryWithBackoff(fn func() error, maxRetries int, initialDelay time.Duration, logger *logrus.Logger) error {
	var err error
	delay := initialDelay

	for i := 0; i < maxRetries; i++ {
		err = fn()
		if err == nil {
			return nil
		}

		if i < maxRetries-1 {
			logger.WithFields(logrus.Fields{
				"attempt": i + 1,
				"delay":   delay,
				"error":   err,
			}).Warn("Operation failed, retrying")

			time.Sleep(delay)
			delay *= 2 // Exponential backoff
		}
	}

	return fmt.Errorf("operation failed after %d attempts: %w", maxRetries, err)
}

// isValidMessageContent checks if message content is valid for transmission
func isValidMessageContent(content string) bool {
	if content == "" {
		return false
	}

	// Check for control characters that might break APRS
	for _, char := range content {
		if char < 32 && char != 9 && char != 10 && char != 13 { // Allow tab, LF, CR
			return false
		}
	}

	return true
}

// sanitizeMessageContent sanitizes message content for APRS transmission
func sanitizeMessageContent(content string) string {
	// Remove or replace problematic characters
	sanitized := ""
	for _, char := range content {
		if char >= 32 || char == 9 { // Printable characters and tab
			sanitized += string(char)
		} else if char == 10 || char == 13 { // Line endings
			sanitized += " " // Replace with space
		}
		// Skip other control characters
	}

	return sanitized
}

// extractSSID extracts the SSID from a callsign (e.g., W4ABC-5 -> 5)
func extractSSID(callsign string) (string, string) {
	parts := strings.Split(callsign, "-")
	if len(parts) == 2 {
		return parts[0], parts[1]
	}
	return callsign, ""
}

// formatDuration formats a duration in a human-readable way
func formatDuration(d time.Duration) string {
	if d < time.Minute {
		return fmt.Sprintf("%.0fs", d.Seconds())
	} else if d < time.Hour {
		return fmt.Sprintf("%.1fm", d.Minutes())
	} else if d < 24*time.Hour {
		return fmt.Sprintf("%.1fh", d.Hours())
	} else {
		return fmt.Sprintf("%.1fd", d.Hours()/24)
	}
}

// getSystemInfo returns basic system information
func getSystemInfo() map[string]interface{} {
	return map[string]interface{}{
		"service":    "aprs-connector",
		"version":    "1.0.0",
		"go_version": "go1.21",
		"started_at": time.Now().Unix(),
	}
}