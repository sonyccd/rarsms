package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
)

// DatabaseClient handles communication with PocketBase
type DatabaseClient struct {
	config     *Config
	logger     *logrus.Logger
	baseURL    string
	httpClient *http.Client
}

// NewDatabaseClient creates a new database client
func NewDatabaseClient(config *Config, logger *logrus.Logger) *DatabaseClient {
	return &DatabaseClient{
		config:  config,
		logger:  logger,
		baseURL: strings.TrimSuffix(config.Database.URL, "/"),
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// makeRequest makes an HTTP request to PocketBase API
func (db *DatabaseClient) makeRequest(method, endpoint string, body interface{}) (*http.Response, error) {
	var reqBody *bytes.Buffer
	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		reqBody = bytes.NewBuffer(jsonBody)
	} else {
		reqBody = &bytes.Buffer{}
	}

	url := fmt.Sprintf("%s/api/collections/%s", db.baseURL, endpoint)
	req, err := http.NewRequest(method, url, reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := db.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %w", err)
	}

	return resp, nil
}

// IsAuthorizedMember checks if a callsign is an authorized member
func (db *DatabaseClient) IsAuthorizedMember(callsign string) (bool, error) {
	callsign = strings.ToUpper(callsign)

	// Query member_profiles collection for the callsign
	endpoint := fmt.Sprintf("member_profiles/records?filter=callsign='%s'", callsign)
	resp, err := db.makeRequest("GET", endpoint, nil)
	if err != nil {
		return false, fmt.Errorf("failed to query member: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == 404 {
		return false, nil // Member not found
	}

	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return false, fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	var result struct {
		Items []map[string]interface{} `json:"items"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return false, fmt.Errorf("failed to decode response: %w", err)
	}

	// Check if member found and get associated user
	if len(result.Items) == 0 {
		return false, nil
	}

	memberProfile := result.Items[0]
	userID, ok := memberProfile["user"].(string)
	if !ok {
		return false, fmt.Errorf("invalid user ID in member profile")
	}

	// Check if user is approved and active
	userResp, err := db.makeRequest("GET", fmt.Sprintf("users/records/%s", userID), nil)
	if err != nil {
		return false, fmt.Errorf("failed to query user: %w", err)
	}
	defer userResp.Body.Close()

	if userResp.StatusCode != 200 {
		return false, nil
	}

	var user map[string]interface{}
	if err := json.NewDecoder(userResp.Body).Decode(&user); err != nil {
		return false, fmt.Errorf("failed to decode user response: %w", err)
	}

	approved, _ := user["approved"].(bool)
	return approved, nil
}

// GetUserIDByCallsign gets the user ID for a given callsign
func (db *DatabaseClient) GetUserIDByCallsign(callsign string) (string, error) {
	callsign = strings.ToUpper(callsign)

	endpoint := fmt.Sprintf("member_profiles/records?filter=callsign='%s'", callsign)
	resp, err := db.makeRequest("GET", endpoint, nil)
	if err != nil {
		return "", fmt.Errorf("failed to query member: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", nil // Member not found
	}

	var result struct {
		Items []map[string]interface{} `json:"items"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("failed to decode response: %w", err)
	}

	if len(result.Items) == 0 {
		return "", nil
	}

	userID, ok := result.Items[0]["user"].(string)
	if !ok {
		return "", fmt.Errorf("invalid user ID in member profile")
	}

	return userID, nil
}

// CreateMessage stores a new message in the database
func (db *DatabaseClient) CreateMessage(messageData map[string]interface{}) error {
	resp, err := db.makeRequest("POST", "messages/records", messageData)
	if err != nil {
		return fmt.Errorf("failed to create message: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	db.logger.WithField("correlation_id", messageData["correlation_id"]).Debug("Message created in database")
	return nil
}

// CreateAPRSPacket stores a raw APRS packet
func (db *DatabaseClient) CreateAPRSPacket(packetData map[string]interface{}) error {
	resp, err := db.makeRequest("POST", "aprs_packets/records", packetData)
	if err != nil {
		return fmt.Errorf("failed to create APRS packet: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

// LogEvent creates a system log entry
func (db *DatabaseClient) LogEvent(level, service, eventType, message string, metadata map[string]interface{}, correlationID string) error {
	logData := map[string]interface{}{
		"level":       level,
		"service":     service,
		"event_type":  eventType,
		"message":     message,
		"metadata":    metadata,
	}

	if correlationID != "" {
		logData["correlation_id"] = correlationID
	}

	resp, err := db.makeRequest("POST", "system_logs/records", logData)
	if err != nil {
		return fmt.Errorf("failed to create log: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

// UpdateSystemStatus updates the system status for a service
func (db *DatabaseClient) UpdateSystemStatus(service, status string, metadata map[string]interface{}) error {
	// First try to get existing record
	endpoint := fmt.Sprintf("system_status/records?filter=service='%s'", service)
	resp, err := db.makeRequest("GET", endpoint, nil)
	if err != nil {
		return fmt.Errorf("failed to query system status: %w", err)
	}
	defer resp.Body.Close()

	statusData := map[string]interface{}{
		"service":        service,
		"status":         status,
		"last_heartbeat": time.Now().Format(time.RFC3339),
		"metadata":       metadata,
	}

	if resp.StatusCode == 200 {
		// Parse existing records
		var result struct {
			Items []map[string]interface{} `json:"items"`
		}

		respBody, _ := ioutil.ReadAll(resp.Body)
		if err := json.Unmarshal(respBody, &result); err == nil && len(result.Items) > 0 {
			// Update existing record
			recordID := result.Items[0]["id"].(string)
			updateResp, err := db.makeRequest("PATCH", fmt.Sprintf("system_status/records/%s", recordID), statusData)
			if err != nil {
				return fmt.Errorf("failed to update system status: %w", err)
			}
			defer updateResp.Body.Close()

			if updateResp.StatusCode != 200 {
				body, _ := ioutil.ReadAll(updateResp.Body)
				return fmt.Errorf("API error %d: %s", updateResp.StatusCode, string(body))
			}
			return nil
		}
	}

	// Create new record if none exists
	createResp, err := db.makeRequest("POST", "system_status/records", statusData)
	if err != nil {
		return fmt.Errorf("failed to create system status: %w", err)
	}
	defer createResp.Body.Close()

	if createResp.StatusCode != 200 && createResp.StatusCode != 201 {
		body, _ := ioutil.ReadAll(createResp.Body)
		return fmt.Errorf("API error %d: %s", createResp.StatusCode, string(body))
	}

	return nil
}

// CreateOrUpdateConversation creates or updates a conversation record
func (db *DatabaseClient) CreateOrUpdateConversation(correlationID, userID, subject string) error {
	// Truncate subject to first 50 characters
	if len(subject) > 50 {
		subject = subject[:47] + "..."
	}

	// Try to find existing conversation
	endpoint := fmt.Sprintf("conversations/records?filter=correlation_id='%s'", correlationID)
	resp, err := db.makeRequest("GET", endpoint, nil)
	if err != nil {
		return fmt.Errorf("failed to query conversation: %w", err)
	}
	defer resp.Body.Close()

	conversationData := map[string]interface{}{
		"correlation_id":    correlationID,
		"services_involved": []string{"aprs", "discord"},
		"subject":          subject,
		"status":           "active",
		"last_activity":    time.Now().Format(time.RFC3339),
		"message_count":    1,
	}

	if userID != "" {
		conversationData["initiated_by"] = userID
	}

	if resp.StatusCode == 200 {
		// Parse existing records
		var result struct {
			Items []map[string]interface{} `json:"items"`
		}

		respBody, _ := ioutil.ReadAll(resp.Body)
		if err := json.Unmarshal(respBody, &result); err == nil && len(result.Items) > 0 {
			// Update existing conversation
			recordID := result.Items[0]["id"].(string)
			existingCount, _ := result.Items[0]["message_count"].(float64)
			conversationData["message_count"] = int(existingCount) + 1

			updateResp, err := db.makeRequest("PATCH", fmt.Sprintf("conversations/records/%s", recordID), conversationData)
			if err != nil {
				return fmt.Errorf("failed to update conversation: %w", err)
			}
			defer updateResp.Body.Close()

			if updateResp.StatusCode != 200 {
				body, _ := ioutil.ReadAll(updateResp.Body)
				return fmt.Errorf("API error %d: %s", updateResp.StatusCode, string(body))
			}
			return nil
		}
	}

	// Create new conversation
	createResp, err := db.makeRequest("POST", "conversations/records", conversationData)
	if err != nil {
		return fmt.Errorf("failed to create conversation: %w", err)
	}
	defer createResp.Body.Close()

	if createResp.StatusCode != 200 && createResp.StatusCode != 201 {
		body, _ := ioutil.ReadAll(createResp.Body)
		return fmt.Errorf("API error %d: %s", createResp.StatusCode, string(body))
	}

	return nil
}

// GetPendingMessages retrieves messages pending delivery to APRS
func (db *DatabaseClient) GetPendingMessages() ([]map[string]interface{}, error) {
	endpoint := "messages/records?filter=to_service='aprs'%20%26%26%20status='pending'&sort=-created"
	resp, err := db.makeRequest("GET", endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to query pending messages: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	var result struct {
		Items []map[string]interface{} `json:"items"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result.Items, nil
}

// UpdateMessageStatus updates the status of a message
func (db *DatabaseClient) UpdateMessageStatus(messageID, status string, metadata map[string]interface{}) error {
	updateData := map[string]interface{}{
		"status": status,
	}

	if status == "delivered" {
		updateData["delivered_at"] = time.Now().Format(time.RFC3339)
	}

	if metadata != nil {
		updateData["metadata"] = metadata
	}

	resp, err := db.makeRequest("PATCH", fmt.Sprintf("messages/records/%s", messageID), updateData)
	if err != nil {
		return fmt.Errorf("failed to update message status: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return fmt.Errorf("API error %d: %s", resp.StatusCode, string(body))
	}

	return nil
}