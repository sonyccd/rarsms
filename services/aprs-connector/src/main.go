package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"
)

const (
	Version = "1.0.0"
)

func main() {
	// Parse command line flags
	var (
		configPath = flag.String("config", "/app/config/config.yaml", "Path to configuration file")
		version    = flag.Bool("version", false, "Show version information")
	)
	flag.Parse()

	if *version {
		fmt.Printf("RARSMS APRS Connector v%s\n", Version)
		os.Exit(0)
	}

	// Load configuration
	config, err := LoadConfig(*configPath)
	if err != nil {
		fmt.Printf("Failed to load configuration: %v\n", err)
		os.Exit(1)
	}

	// Setup logger
	logger := setupLogger(config)
	logger.WithFields(logrus.Fields{
		"version":    Version,
		"config":     *configPath,
		"callsign":   config.APRS.Callsign,
		"server":     config.APRS.Server,
	}).Info("Starting RARSMS APRS Connector")

	// Check if service is enabled
	if !config.Services.APRSConnector.Enabled {
		logger.Info("APRS Connector is disabled in configuration")
		os.Exit(0)
	}

	// Create database client
	db := NewDatabaseClient(config, logger)

	// Initialize system status
	if err := db.UpdateSystemStatus("aprs-connector", "starting", getSystemInfo()); err != nil {
		logger.WithError(err).Warn("Failed to initialize system status")
	}

	// Create APRS client
	aprsClient := NewAPRSClient(config, logger, db)

	// Create context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Setup signal handling for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start the main service loop
	go func() {
		if err := runService(ctx, aprsClient, logger); err != nil {
			logger.WithError(err).Error("Service error")
			cancel()
		}
	}()

	// Start message sender goroutine
	go func() {
		if err := runMessageSender(ctx, aprsClient, db, logger); err != nil {
			logger.WithError(err).Error("Message sender error")
		}
	}()

	// Wait for shutdown signal
	select {
	case sig := <-sigChan:
		logger.WithField("signal", sig).Info("Received shutdown signal")
	case <-ctx.Done():
		logger.Info("Context cancelled")
	}

	// Graceful shutdown
	logger.Info("Shutting down APRS Connector")

	// Disconnect from APRS-IS
	if err := aprsClient.Disconnect(); err != nil {
		logger.WithError(err).Warn("Error during APRS disconnect")
	}

	// Update system status
	if err := db.UpdateSystemStatus("aprs-connector", "offline", map[string]interface{}{
		"shutdown_reason": "graceful",
		"shutdown_time":   time.Now().Unix(),
	}); err != nil {
		logger.WithError(err).Warn("Failed to update shutdown status")
	}

	logger.Info("APRS Connector stopped")
}

// runService runs the main APRS service with reconnection logic
func runService(ctx context.Context, aprsClient *APRSClient, logger *logrus.Logger) error {
	for {
		select {
		case <-ctx.Done():
			return nil
		default:
		}

		// Connect to APRS-IS
		err := retryWithBackoff(func() error {
			return aprsClient.Connect()
		}, 5, 5*time.Second, logger)

		if err != nil {
			logger.WithError(err).Error("Failed to connect to APRS-IS after retries")

			// Update system status to error
			if dbErr := aprsClient.db.UpdateSystemStatus("aprs-connector", "error", map[string]interface{}{
				"error":      err.Error(),
				"error_time": time.Now().Unix(),
			}); dbErr != nil {
				logger.WithError(dbErr).Warn("Failed to update error status")
			}

			// Wait before trying again
			select {
			case <-ctx.Done():
				return nil
			case <-time.After(time.Duration(aprsClient.config.Services.APRSConnector.ReconnectDelay) * time.Second):
				continue
			}
		}

		// Start heartbeat
		aprsClient.StartHeartbeat()

		// Listen for messages
		logger.Info("Starting APRS message listener")
		if err := aprsClient.Listen(); err != nil {
			logger.WithError(err).Error("APRS listener error")

			// Log the error
			if logErr := aprsClient.db.LogEvent("error", "aprs", "connection",
				fmt.Sprintf("APRS listener error: %s", err.Error()),
				map[string]interface{}{
					"error": err.Error(),
				}, ""); logErr != nil {
				logger.WithError(logErr).Warn("Failed to log listener error")
			}
		}

		// Disconnect and wait before reconnecting
		aprsClient.Disconnect()

		if ctx.Err() != nil {
			return nil
		}

		logger.WithField("delay", aprsClient.config.Services.APRSConnector.ReconnectDelay).
			Info("Waiting before reconnecting to APRS-IS")

		select {
		case <-ctx.Done():
			return nil
		case <-time.After(time.Duration(aprsClient.config.Services.APRSConnector.ReconnectDelay) * time.Second):
			logger.Info("Attempting to reconnect to APRS-IS")
		}
	}
}

// runMessageSender handles sending messages from database to APRS
func runMessageSender(ctx context.Context, aprsClient *APRSClient, db *DatabaseClient, logger *logrus.Logger) error {
	ticker := time.NewTicker(10 * time.Second) // Check every 10 seconds
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			if !aprsClient.IsConnected() {
				continue
			}

			// Get pending messages for APRS
			messages, err := db.GetPendingMessages()
			if err != nil {
				logger.WithError(err).Warn("Failed to get pending messages")
				continue
			}

			for _, msgData := range messages {
				select {
				case <-ctx.Done():
					return nil
				default:
				}

				messageID, _ := msgData["id"].(string)
				fromCallsign, _ := msgData["from_callsign"].(string)
				content, _ := msgData["content"].(string)
				correlationID, _ := msgData["correlation_id"].(string)

				// Extract target callsign from metadata or use from_callsign
				metadata, _ := msgData["metadata"].(map[string]interface{})
				var targetCallsign string
				if metadata != nil {
					if target, ok := metadata["target_callsign"].(string); ok {
						targetCallsign = target
					}
				}
				if targetCallsign == "" {
					targetCallsign = fromCallsign
				}

				// Validate content
				if !isValidMessageContent(content) {
					logger.WithFields(logrus.Fields{
						"message_id":     messageID,
						"correlation_id": correlationID,
					}).Warn("Invalid message content, marking as failed")

					if err := db.UpdateMessageStatus(messageID, "failed", map[string]interface{}{
						"error": "invalid content",
					}); err != nil {
						logger.WithError(err).Warn("Failed to update message status")
					}
					continue
				}

				// Sanitize and truncate content for APRS
				sanitizedContent := sanitizeMessageContent(content)
				truncatedContent := truncateForAPRS(sanitizedContent, 67)

				// Generate message ID for APRS
				aprsMessageID := fmt.Sprintf("%d", time.Now().Unix()%10000)

				// Send message via APRS
				if err := aprsClient.SendMessage(targetCallsign, truncatedContent, aprsMessageID); err != nil {
					logger.WithError(err).WithFields(logrus.Fields{
						"message_id":     messageID,
						"target":         targetCallsign,
						"correlation_id": correlationID,
					}).Error("Failed to send APRS message")

					// Update status to failed
					if err := db.UpdateMessageStatus(messageID, "failed", map[string]interface{}{
						"error":            err.Error(),
						"aprs_message_id":  aprsMessageID,
						"truncated_content": truncatedContent,
					}); err != nil {
						logger.WithError(err).Warn("Failed to update message status")
					}
				} else {
					logger.WithFields(logrus.Fields{
						"message_id":      messageID,
						"target":          targetCallsign,
						"correlation_id":  correlationID,
						"aprs_message_id": aprsMessageID,
					}).Info("Successfully sent APRS message")

					// Update status to delivered
					if err := db.UpdateMessageStatus(messageID, "delivered", map[string]interface{}{
						"aprs_message_id":   aprsMessageID,
						"truncated_content": truncatedContent,
						"delivery_method":   "aprs-is",
					}); err != nil {
						logger.WithError(err).Warn("Failed to update message status")
					}

					// Log successful delivery
					if err := db.LogEvent("info", "aprs", "message",
						fmt.Sprintf("Message delivered to %s via APRS", targetCallsign),
						map[string]interface{}{
							"message_id":      messageID,
							"target_callsign": targetCallsign,
							"aprs_message_id": aprsMessageID,
							"content_length":  len(truncatedContent),
						}, correlationID); err != nil {
						logger.WithError(err).Warn("Failed to log delivery event")
					}
				}

				// Small delay between messages to avoid flooding
				time.Sleep(2 * time.Second)
			}
		}
	}
}