package main

import (
	"bufio"
	"fmt"
	"net"
	"regexp"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
)

// APRSMessage represents a parsed APRS message
type APRSMessage struct {
	FromCallsign string
	ToCallsign   string
	Content      string
	MessageID    string
	RawPacket    string
	Timestamp    time.Time
}

// APRSClient manages the APRS-IS connection
type APRSClient struct {
	config      *Config
	logger      *logrus.Logger
	conn        net.Conn
	connected   bool
	stopChannel chan bool
	db          *DatabaseClient
}

// APRS message parsing regex patterns
var (
	// APRS message format: FROM>TO,PATH::RARSMS   :Message content{MSGID
	messageRegex = regexp.MustCompile(`^([A-Z0-9-]+)>([^,]+),.*?::([A-Z0-9-]+)\s*:(.+?)(?:\{([A-Za-z0-9]+))?$`)
)

// NewAPRSClient creates a new APRS client
func NewAPRSClient(config *Config, logger *logrus.Logger, db *DatabaseClient) *APRSClient {
	return &APRSClient{
		config:      config,
		logger:      logger,
		db:          db,
		stopChannel: make(chan bool),
	}
}

// Connect establishes connection to APRS-IS
func (a *APRSClient) Connect() error {
	a.logger.WithFields(logrus.Fields{
		"server":   a.config.APRS.Server,
		"port":     a.config.APRS.Port,
		"callsign": a.config.APRS.Callsign,
	}).Info("Connecting to APRS-IS")

	conn, err := net.DialTimeout("tcp",
		fmt.Sprintf("%s:%d", a.config.APRS.Server, a.config.APRS.Port),
		30*time.Second)
	if err != nil {
		return fmt.Errorf("failed to connect to APRS-IS: %w", err)
	}

	a.conn = conn
	a.connected = true

	// Send login string
	loginString := fmt.Sprintf("user %s pass %s vers RARSMS 1.0 filter %s\r\n",
		a.config.APRS.Callsign,
		a.config.APRS.Passcode,
		a.config.APRS.Filter)

	if _, err := a.conn.Write([]byte(loginString)); err != nil {
		a.conn.Close()
		a.connected = false
		return fmt.Errorf("failed to send login: %w", err)
	}

	a.logger.Info("Successfully connected to APRS-IS")

	// Update system status
	if err := a.db.UpdateSystemStatus("aprs-connector", "online", map[string]interface{}{
		"server":     a.config.APRS.Server,
		"port":       a.config.APRS.Port,
		"callsign":   a.config.APRS.Callsign,
		"filter":     a.config.APRS.Filter,
		"connected":  true,
		"connect_time": time.Now().Unix(),
	}); err != nil {
		a.logger.WithError(err).Warn("Failed to update system status")
	}

	return nil
}

// Disconnect closes the APRS-IS connection
func (a *APRSClient) Disconnect() error {
	a.logger.Info("Disconnecting from APRS-IS")

	// Signal stop to goroutines
	close(a.stopChannel)

	if a.conn != nil {
		a.conn.Close()
	}
	a.connected = false

	// Update system status
	if err := a.db.UpdateSystemStatus("aprs-connector", "offline", map[string]interface{}{
		"connected":     false,
		"disconnect_time": time.Now().Unix(),
	}); err != nil {
		a.logger.WithError(err).Warn("Failed to update system status")
	}

	return nil
}

// IsConnected returns the connection status
func (a *APRSClient) IsConnected() bool {
	return a.connected
}

// Listen starts listening for APRS messages
func (a *APRSClient) Listen() error {
	if !a.connected {
		return fmt.Errorf("not connected to APRS-IS")
	}

	a.logger.Info("Starting APRS message listener")

	scanner := bufio.NewScanner(a.conn)
	scanner.Buffer(make([]byte, 1024), 8192) // Increase buffer size for long packets

	for scanner.Scan() {
		select {
		case <-a.stopChannel:
			a.logger.Info("APRS listener stopped")
			return nil
		default:
			line := strings.TrimSpace(scanner.Text())
			if line == "" {
				continue
			}

			// Log raw packet for debugging
			a.logger.WithField("packet", line).Debug("Received APRS packet")

			// Parse the packet
			if err := a.handleAPRSPacket(line); err != nil {
				a.logger.WithError(err).WithField("packet", line).Warn("Failed to handle APRS packet")
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return fmt.Errorf("APRS scanner error: %w", err)
	}

	return nil
}

// handleAPRSPacket processes a raw APRS packet
func (a *APRSClient) handleAPRSPacket(rawPacket string) error {
	// Store raw packet for debugging
	if err := a.storeRawPacket(rawPacket); err != nil {
		a.logger.WithError(err).Warn("Failed to store raw packet")
	}

	// Skip server messages and comments
	if strings.HasPrefix(rawPacket, "#") {
		return nil
	}

	// Parse APRS message
	message, err := a.parseAPRSMessage(rawPacket)
	if err != nil {
		// Not all packets are messages, so this is not always an error
		a.logger.WithField("packet", rawPacket).Debug("Packet is not a message")
		return nil
	}

	// Check if message is addressed to our callsign
	if strings.ToUpper(message.ToCallsign) != strings.ToUpper(a.config.APRS.Callsign) {
		return nil
	}

	a.logger.WithFields(logrus.Fields{
		"from":       message.FromCallsign,
		"to":         message.ToCallsign,
		"content":    message.Content,
		"message_id": message.MessageID,
	}).Info("Received APRS message for RARSMS")

	// Validate sender is authorized
	isAuthorized, err := a.db.IsAuthorizedMember(message.FromCallsign)
	if err != nil {
		a.logger.WithError(err).WithField("callsign", message.FromCallsign).Error("Failed to check authorization")
		return err
	}

	if !isAuthorized {
		a.logger.WithField("callsign", message.FromCallsign).Warn("Unauthorized callsign attempted to send message")

		// Send ACK if message has ID (standard practice)
		if message.MessageID != "" {
			if err := a.sendACK(message.FromCallsign, message.MessageID); err != nil {
				a.logger.WithError(err).Warn("Failed to send ACK")
			}
		}

		// Log unauthorized attempt
		if err := a.db.LogEvent("warn", "aprs", "auth",
			fmt.Sprintf("Unauthorized message from %s", message.FromCallsign),
			map[string]interface{}{
				"from_callsign": message.FromCallsign,
				"content":       message.Content,
				"raw_packet":    rawPacket,
			}, ""); err != nil {
			a.logger.WithError(err).Warn("Failed to log unauthorized attempt")
		}

		return nil
	}

	// Store the message for routing to other services
	if err := a.storeMessage(message); err != nil {
		a.logger.WithError(err).Error("Failed to store message")
		return err
	}

	// Send ACK if message has ID
	if message.MessageID != "" {
		if err := a.sendACK(message.FromCallsign, message.MessageID); err != nil {
			a.logger.WithError(err).Warn("Failed to send ACK")
		}
	}

	a.logger.WithField("from", message.FromCallsign).Info("Successfully processed APRS message")
	return nil
}

// parseAPRSMessage parses a raw APRS packet into an APRSMessage
func (a *APRSClient) parseAPRSMessage(rawPacket string) (*APRSMessage, error) {
	matches := messageRegex.FindStringSubmatch(rawPacket)
	if len(matches) < 5 {
		return nil, fmt.Errorf("packet is not a message format")
	}

	message := &APRSMessage{
		FromCallsign: strings.ToUpper(matches[1]),
		ToCallsign:   strings.ToUpper(matches[3]),
		Content:      strings.TrimSpace(matches[4]),
		RawPacket:    rawPacket,
		Timestamp:    time.Now(),
	}

	// Extract message ID if present
	if len(matches) > 5 && matches[5] != "" {
		message.MessageID = matches[5]
	}

	return message, nil
}

// storeRawPacket stores the raw APRS packet for debugging
func (a *APRSClient) storeRawPacket(rawPacket string) error {
	packet := map[string]interface{}{
		"raw_packet":       rawPacket,
		"packet_type":      "other", // Will be updated if it's a message
		"processed":        false,
		"processing_notes": "",
	}

	// Try to extract basic info for indexing
	if strings.Contains(rawPacket, "::") {
		packet["packet_type"] = "message"

		// Try to extract callsigns
		if matches := messageRegex.FindStringSubmatch(rawPacket); len(matches) >= 4 {
			packet["from_callsign"] = strings.ToUpper(matches[1])
			packet["to_callsign"] = strings.ToUpper(matches[3])
		}
	}

	return a.db.CreateAPRSPacket(packet)
}

// storeMessage stores a parsed message for routing
func (a *APRSClient) storeMessage(message *APRSMessage) error {
	// Generate correlation ID for message tracking
	correlationID := generateCorrelationID()

	messageData := map[string]interface{}{
		"correlation_id":  correlationID,
		"from_callsign":   message.FromCallsign,
		"from_service":    "aprs",
		"to_service":      "discord", // Phase 1: always route to Discord
		"content":         message.Content,
		"message_type":    "message",
		"status":          "pending",
		"metadata": map[string]interface{}{
			"aprs_message_id": message.MessageID,
			"raw_packet":      message.RawPacket,
			"server":          a.config.APRS.Server,
		},
	}

	// Get user ID for the sender
	userID, err := a.db.GetUserIDByCallsign(message.FromCallsign)
	if err != nil {
		a.logger.WithError(err).WithField("callsign", message.FromCallsign).Warn("Failed to get user ID")
	} else if userID != "" {
		messageData["user"] = userID
	}

	if err := a.db.CreateMessage(messageData); err != nil {
		return fmt.Errorf("failed to store message: %w", err)
	}

	// Create or update conversation
	if err := a.db.CreateOrUpdateConversation(correlationID, userID, message.Content); err != nil {
		a.logger.WithError(err).Warn("Failed to create/update conversation")
	}

	// Log successful message processing
	if err := a.db.LogEvent("info", "aprs", "message",
		fmt.Sprintf("Message received from %s", message.FromCallsign),
		map[string]interface{}{
			"correlation_id":  correlationID,
			"from_callsign":   message.FromCallsign,
			"content_length":  len(message.Content),
			"has_message_id":  message.MessageID != "",
		}, correlationID); err != nil {
		a.logger.WithError(err).Warn("Failed to log message event")
	}

	return nil
}

// sendACK sends an ACK back to the sender
func (a *APRSClient) sendACK(toCallsign, messageID string) error {
	if !a.connected {
		return fmt.Errorf("not connected to APRS-IS")
	}

	ackPacket := fmt.Sprintf("%s>APRS,TCPIP*::%s:ack%s\r\n",
		a.config.APRS.Callsign, toCallsign, messageID)

	if _, err := a.conn.Write([]byte(ackPacket)); err != nil {
		return fmt.Errorf("failed to send ACK: %w", err)
	}

	a.logger.WithFields(logrus.Fields{
		"to":         toCallsign,
		"message_id": messageID,
	}).Debug("Sent ACK")

	return nil
}

// SendMessage sends a message via APRS
func (a *APRSClient) SendMessage(toCallsign, content, messageID string) error {
	if !a.connected {
		return fmt.Errorf("not connected to APRS-IS")
	}

	// Truncate content if too long (APRS message limit is ~67 characters)
	if len(content) > 67 {
		content = content[:64] + "..."
	}

	var packet string
	if messageID != "" {
		packet = fmt.Sprintf("%s>APRS,TCPIP*::%s:%s{%s\r\n",
			a.config.APRS.Callsign, toCallsign, content, messageID)
	} else {
		packet = fmt.Sprintf("%s>APRS,TCPIP*::%s:%s\r\n",
			a.config.APRS.Callsign, toCallsign, content)
	}

	if _, err := a.conn.Write([]byte(packet)); err != nil {
		return fmt.Errorf("failed to send message: %w", err)
	}

	a.logger.WithFields(logrus.Fields{
		"to":         toCallsign,
		"content":    content,
		"message_id": messageID,
	}).Info("Sent APRS message")

	return nil
}

// StartHeartbeat starts sending periodic heartbeat/beacon
func (a *APRSClient) StartHeartbeat() {
	go func() {
		ticker := time.NewTicker(time.Duration(a.config.Services.APRSConnector.HeartbeatInterval) * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-a.stopChannel:
				return
			case <-ticker.C:
				if a.connected {
					// Send status beacon
					statusPacket := fmt.Sprintf("%s>APRS,TCPIP*::STATUS :RARSMS online - bridging APRS to Discord\r\n",
						a.config.APRS.Callsign)

					if _, err := a.conn.Write([]byte(statusPacket)); err != nil {
						a.logger.WithError(err).Warn("Failed to send heartbeat")
					} else {
						a.logger.Debug("Sent heartbeat beacon")
					}

					// Update system status with current stats
					if err := a.db.UpdateSystemStatus("aprs-connector", "online", map[string]interface{}{
						"last_heartbeat": time.Now().Unix(),
						"connected":      true,
					}); err != nil {
						a.logger.WithError(err).Warn("Failed to update heartbeat status")
					}
				}
			}
		}
	}()
}