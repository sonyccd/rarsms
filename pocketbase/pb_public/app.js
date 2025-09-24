class RARSMSViewer {
    constructor() {
        this.pb = new PocketBase(window.location.origin);
        this.messagesContainer = document.getElementById('messages-container');
        this.emptyState = document.getElementById('empty-state');
        this.connectionStatus = document.getElementById('connection-status');
        this.messageCount = document.getElementById('count');

        this.messageBuffer = [];
        this.maxMessages = 100;
        this.isScrolledUp = false;

        this.init();
    }

    async init() {
        try {
            // Test PocketBase connection
            await this.pb.health.check();
            this.updateConnectionStatus('connected');

            // Load initial messages
            await this.loadInitialMessages();

            // Subscribe to real-time updates
            await this.subscribeToMessages();

        } catch (error) {
            console.error('Failed to initialize:', error);
            this.updateConnectionStatus('error');
        }

        // Set up scroll detection
        this.setupScrollDetection();
    }

    async loadInitialMessages() {
        try {
            const messages = await this.pb.collection('messages').getList(1, 50, {
                sort: '-timestamp',
                fields: 'id,message_id,source_protocol,source_id,message_type,content,timestamp,latitude,longitude,raw_packet'
            });

            // Reverse to show oldest first
            const sortedMessages = messages.items.reverse();

            if (sortedMessages.length > 0) {
                this.emptyState.style.display = 'none';
                sortedMessages.forEach(message => this.addMessage(message, false));
                this.updateMessageCount();
                this.scrollToBottom();
            }
        } catch (error) {
            console.error('Failed to load messages:', error);
        }
    }

    async subscribeToMessages() {
        try {
            await this.pb.collection('messages').subscribe('*', (e) => {
                if (e.action === 'create') {
                    this.addMessage(e.record, true);
                    this.updateMessageCount();

                    // Auto-scroll if user is at bottom
                    if (!this.isScrolledUp) {
                        setTimeout(() => this.scrollToBottom(), 100);
                    }
                }
            });

            console.log('Subscribed to real-time updates');
        } catch (error) {
            console.error('Failed to subscribe to messages:', error);
            this.updateConnectionStatus('error');
        }
    }

    addMessage(record, isNew = false) {
        this.emptyState.style.display = 'none';

        const messageElement = this.createMessageElement(record, isNew);
        this.messagesContainer.appendChild(messageElement);
        this.messageBuffer.push(messageElement);

        // Remove old messages if buffer is full
        if (this.messageBuffer.length > this.maxMessages) {
            const oldMessage = this.messageBuffer.shift();
            if (oldMessage && oldMessage.parentNode) {
                oldMessage.parentNode.removeChild(oldMessage);
            }
        }

        // Remove "new" highlighting after animation
        if (isNew) {
            setTimeout(() => {
                messageElement.classList.remove('message-new');
            }, 3000);
        }
    }

    createMessageElement(record, isNew = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isNew ? 'message-new' : ''}`;
        messageDiv.dataset.messageId = record.id;

        // Parse timestamp
        const timestamp = new Date(record.timestamp);
        const timeString = timestamp.toISOString().substr(11, 8) + ' UTC';

        // Create callsign link to QRZ.com
        const callsignLink = `<a href="https://www.qrz.com/db/${record.source_id}" target="_blank" class="message-callsign">${record.source_id}</a>`;

        // Message type styling
        const typeClass = `type-${record.message_type || 'text'}`;

        // Build message HTML
        let messageHTML = `
            <div class="message-header">
                <span class="message-time">${timeString}</span>
                ${callsignLink}
                <span class="message-type ${typeClass}">${record.message_type || 'text'}</span>
                <span class="message-protocol">${record.source_protocol}</span>
            </div>
            <div class="message-content">${this.escapeHtml(record.content)}</div>
        `;

        // Add position information if available
        if (record.latitude && record.longitude) {
            const mapsUrl = `https://www.google.com/maps?q=${record.latitude},${record.longitude}`;
            messageHTML += `
                <div class="message-position">
                    📍 Position:
                    <a href="${mapsUrl}" target="_blank" class="position-link">
                        ${record.latitude.toFixed(4)}, ${record.longitude.toFixed(4)}
                    </a>
                </div>
            `;
        }

        messageDiv.innerHTML = messageHTML;
        return messageDiv;
    }

    updateConnectionStatus(status) {
        const statusElement = this.connectionStatus;
        const statusText = statusElement.querySelector('span');

        // Remove all status classes
        statusElement.className = 'status-item';

        switch (status) {
            case 'connected':
                statusElement.classList.add('status-connected');
                statusElement.innerHTML = '<span>🟢 Connected</span>';
                break;
            case 'error':
                statusElement.classList.add('status-disconnected');
                statusElement.innerHTML = '<span>🔴 Connection Error</span>';
                break;
            case 'loading':
            default:
                statusElement.classList.add('status-loading');
                statusElement.innerHTML = '<div class="loading-spinner"></div><span>Connecting...</span>';
                break;
        }
    }

    updateMessageCount() {
        const count = this.messageBuffer.length;
        this.messageCount.textContent = count;
    }

    setupScrollDetection() {
        const container = this.messagesContainer;

        container.addEventListener('scroll', () => {
            const { scrollTop, scrollHeight, clientHeight } = container;
            const isAtBottom = scrollTop + clientHeight >= scrollHeight - 50;
            this.isScrolledUp = !isAtBottom;
        });
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new RARSMSViewer();
});

// Handle connection errors and retry
window.addEventListener('online', () => {
    location.reload();
});

window.addEventListener('offline', () => {
    document.getElementById('connection-status').innerHTML = '<span>📶 Offline</span>';
    document.getElementById('connection-status').className = 'status-item status-disconnected';
});