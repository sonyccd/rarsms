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
        this.currentTab = 'live-feed';
        this.isAdmin = false;
        this.adminToken = null;

        this.init();
        this.setupTabNavigation();
        this.setupAuthentication();
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

    setupTabNavigation() {
        const navTabs = document.querySelectorAll('.nav-tab');
        const tabContents = document.querySelectorAll('.tab-content');

        navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.getAttribute('data-tab');
                this.switchTab(tabId);
            });
        });

        // Setup management interface buttons
        const addCallsignBtn = document.getElementById('add-callsign-btn');
        if (addCallsignBtn) {
            addCallsignBtn.addEventListener('click', () => {
                this.showAddCallsignModal();
            });
        }
    }

    switchTab(tabId) {
        // Switching to tab: ${tabId}

        // Check if admin access is required
        const targetTab = document.querySelector(`[data-tab="${tabId}"]`);

        if (targetTab && targetTab.classList.contains('admin-required') && !this.isAdmin) {
            this.showLoginModal();
            return;
        }

        // Update active states
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // Activate selected tab
        document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
        document.getElementById(tabId).classList.add('active');

        this.currentTab = tabId;

        // Load tab content
        this.loadTabContent(tabId);
    }

    async loadTabContent(tabId) {
        switch (tabId) {
            case 'live-feed':
                // Already loaded and updating
                break;
            case 'callsigns':
                await this.loadCallsignsTab();
                break;
            case 'statistics':
                await this.loadStatisticsTab();
                break;
            case 'search':
                this.setupSearchTab();
                break;
            case 'config':
                await this.loadConfigTab();
                break;
        }
    }

    async loadCallsignsTab() {
        if (!this.isAdmin) {
            this.showLoginModal();
            return;
        }

        const container = document.getElementById('callsigns-list');
        container.innerHTML = '<div class="loading-placeholder">Loading callsigns...</div>';

        try {
            const callsigns = await this.pb.collection('authorized_callsigns').getFullList({
                sort: 'callsign'
            });

            if (callsigns.length === 0) {
                container.innerHTML = '<div class="empty-search">No authorized callsigns configured</div>';
                return;
            }

            container.innerHTML = `
                <div class="row">
                    ${callsigns.map(callsign => `
                        <div class="col-lg-6 col-xl-4 mb-3">
                            <div class="card h-100">
                                <div class="card-body">
                                    <div class="d-flex justify-content-between align-items-start mb-2">
                                        <h6 class="card-title mb-0 font-monospace fs-5 text-primary">${callsign.callsign}</h6>
                                        ${callsign.enabled ?
                                            '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>Active</span>' :
                                            '<span class="badge bg-secondary"><i class="bi bi-pause-circle me-1"></i>Disabled</span>'
                                        }
                                    </div>
                                    <p class="card-text text-muted small mb-3">
                                        ${callsign.description || 'No description provided'}
                                    </p>
                                    <div class="d-flex gap-1 flex-wrap">
                                        <button onclick="viewer.editCallsign('${callsign.id}')"
                                                class="btn btn-sm btn-outline-secondary" title="Edit callsign">
                                            <i class="bi bi-pencil-square me-1"></i>Edit
                                        </button>
                                        <button onclick="viewer.toggleCallsign('${callsign.id}')"
                                                class="btn btn-sm ${callsign.enabled ? 'btn-outline-warning' : 'btn-outline-success'}"
                                                title="Toggle status">
                                            <i class="bi bi-${callsign.enabled ? 'pause' : 'play'} me-1"></i>
                                            ${callsign.enabled ? 'Disable' : 'Enable'}
                                        </button>
                                        <button onclick="viewer.deleteCallsign('${callsign.id}')"
                                                class="btn btn-sm btn-outline-danger" title="Delete callsign">
                                            <i class="bi bi-trash me-1"></i>Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;

        } catch (error) {
            console.error('Failed to load callsigns:', error);
            container.innerHTML = '<div class="empty-search">Error loading callsigns</div>';
        }
    }

    async loadStatisticsTab() {
        const container = document.getElementById('stats-content');
        container.innerHTML = '<div class="loading-placeholder">Loading statistics...</div>';

        try {
            // Get message counts by protocol
            const messages = await this.pb.collection('messages').getList(1, 1000, {
                fields: 'source_protocol,message_type,created'
            });

            const stats = this.calculateMessageStats(messages.items);

            container.innerHTML = `
                <div class="stats-overview">
                    <div class="stat-card">
                        <div class="stat-number">${stats.total}</div>
                        <div class="stat-label">Total Messages</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.today}</div>
                        <div class="stat-label">Messages Today</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.protocols.aprs || 0}</div>
                        <div class="stat-label">APRS Messages</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.protocols.discord || 0}</div>
                        <div class="stat-label">Discord Messages</div>
                    </div>
                </div>

                <div class="stats-details">
                    <h3>Message Types</h3>
                    <div class="type-stats">
                        ${Object.entries(stats.types).map(([type, count]) => `
                            <div class="type-stat">
                                <span class="type-name">${type}</span>
                                <span class="type-count">${count}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;

        } catch (error) {
            console.error('Failed to load statistics:', error);
            container.innerHTML = '<div class="empty-search">Error loading statistics</div>';
        }
    }

    calculateMessageStats(messages) {
        const today = new Date().toDateString();
        const stats = {
            total: messages.length,
            today: 0,
            protocols: {},
            types: {}
        };

        messages.forEach(msg => {
            // Count today's messages
            if (new Date(msg.created).toDateString() === today) {
                stats.today++;
            }

            // Count by protocol
            const protocol = msg.source_protocol?.replace('_main', '') || 'unknown';
            stats.protocols[protocol] = (stats.protocols[protocol] || 0) + 1;

            // Count by type
            stats.types[msg.message_type] = (stats.types[msg.message_type] || 0) + 1;
        });

        return stats;
    }

    setupSearchTab() {
        const searchBtn = document.getElementById('search-btn');
        const searchInput = document.getElementById('search-input');

        if (searchBtn && !searchBtn.hasListener) {
            searchBtn.addEventListener('click', () => this.performSearch());
            searchBtn.hasListener = true;
        }

        if (searchInput && !searchInput.hasListener) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.performSearch();
            });
            searchInput.hasListener = true;
        }
    }

    async performSearch() {
        const searchTerm = document.getElementById('search-input').value;
        const typeFilter = document.getElementById('search-filter').value;
        const resultsContainer = document.getElementById('search-results');

        if (!searchTerm.trim()) {
            resultsContainer.innerHTML = '<div class="empty-search">Enter search terms above</div>';
            return;
        }

        resultsContainer.innerHTML = '<div class="loading-placeholder">Searching...</div>';

        try {
            let filter = `content~"${searchTerm}" || source_id~"${searchTerm}"`;
            if (typeFilter) {
                filter += ` && message_type="${typeFilter}"`;
            }

            const results = await this.pb.collection('messages').getList(1, 50, {
                filter: filter,
                sort: '-timestamp'
            });

            if (results.items.length === 0) {
                resultsContainer.innerHTML = '<div class="empty-search">No messages found</div>';
                return;
            }

            resultsContainer.innerHTML = results.items.map(msg =>
                this.createMessageElement(msg).outerHTML
            ).join('');

        } catch (error) {
            console.error('Search failed:', error);
            resultsContainer.innerHTML = '<div class="empty-search">Search failed - try simpler terms</div>';
        }
    }

    async loadConfigTab() {
        if (!this.isAdmin) {
            this.showLoginModal();
            return;
        }

        const container = document.getElementById('config-content');
        container.innerHTML = '<div class="loading-placeholder">Loading configuration...</div>';

        try {
            // Load configuration from PocketBase
            const config = await this.loadConfigFromDatabase();

            container.innerHTML = `
                <!-- APRS Configuration Section -->
                <div class="card mb-4">
                    <div class="card-header bg-secondary text-white">
                        <h5 class="card-title mb-1">
                            <i class="bi bi-broadcast me-2"></i>
                            APRS Configuration
                        </h5>
                        <small class="text-white-50">Configure APRS-IS connection and geographic filtering</small>
                    </div>
                    <div class="card-body">
                        <form id="aprs-config-form">
                            <div class="row mb-3">
                                <div class="col-md-8">
                                    <label for="aprs-server" class="form-label">APRS Server</label>
                                    <input type="text" class="form-control" id="aprs-server"
                                           value="${config.aprs_server || 'rotate.aprs2.net'}"
                                           placeholder="rotate.aprs2.net" required>
                                    <div class="form-text">APRS-IS server hostname</div>
                                </div>
                                <div class="col-md-4">
                                    <label for="aprs-port" class="form-label">Port</label>
                                    <input type="number" class="form-control" id="aprs-port"
                                           value="${config.aprs_port || 14580}" min="1" max="65535" required>
                                    <div class="form-text">Usually 14580</div>
                                </div>
                            </div>

                            <div class="row mb-4">
                                <div class="col-md-6">
                                    <label for="aprs-callsign" class="form-label">Your Callsign</label>
                                    <input type="text" class="form-control" id="aprs-callsign"
                                           value="${config.aprs_callsign || ''}"
                                           pattern="[A-Za-z0-9-]{3,9}" placeholder="KK4ABC-0"
                                           style="text-transform: uppercase;" required>
                                    <div class="form-text">Your amateur radio callsign</div>
                                </div>
                                <div class="col-md-6">
                                    <label for="aprs-passcode" class="form-label">Passcode</label>
                                    <input type="text" class="form-control" id="aprs-passcode"
                                           value="${config.aprs_passcode || ''}" placeholder="Calculate passcode" required>
                                    <div class="form-text">
                                        <a href="https://apps.magicbug.co.uk/passcode/" target="_blank" class="link-info text-decoration-none">
                                            <i class="bi bi-calculator me-1"></i>Calculate passcode
                                        </a>
                                    </div>
                                </div>
                            </div>

                            <hr>
                            <h6 class="text-body-secondary mb-3">
                                <i class="bi bi-geo-alt me-2"></i>
                                Geographic Filter
                            </h6>

                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <label for="filter-lat" class="form-label">Latitude</label>
                                    <input type="number" class="form-control" id="filter-lat"
                                           value="${config.filter_lat || 35.7796}"
                                           step="0.0001" min="-90" max="90" required>
                                    <div class="form-text">Decimal degrees</div>
                                </div>
                                <div class="col-md-4">
                                    <label for="filter-lon" class="form-label">Longitude</label>
                                    <input type="number" class="form-control" id="filter-lon"
                                           value="${config.filter_lon || -78.6382}"
                                           step="0.0001" min="-180" max="180" required>
                                    <div class="form-text">Decimal degrees</div>
                                </div>
                                <div class="col-md-4">
                                    <label for="filter-distance" class="form-label">Radius (km)</label>
                                    <input type="number" class="form-control" id="filter-distance"
                                           value="${config.filter_distance || 100}"
                                           min="1" max="1000" required>
                                    <div class="form-text">Filter radius</div>
                                </div>
                            </div>

                            <div class="d-flex justify-content-end">
                                <button type="submit" class="btn btn-secondary">
                                    <i class="bi bi-check-circle me-1"></i>
                                    Save APRS Settings
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Discord Configuration Section -->
                <div class="card mb-4">
                    <div class="card-header bg-secondary text-white">
                        <h5 class="card-title mb-1">
                            <i class="bi bi-discord me-2"></i>
                            Discord Configuration
                        </h5>
                        <small class="text-white-50">Configure Discord bot integration for message forwarding</small>
                    </div>
                    <div class="card-body">
                        <form id="discord-config-form">
                            <div class="mb-3">
                                <label for="discord-bot-token" class="form-label">Bot Token</label>
                                <input type="password" class="form-control" id="discord-bot-token"
                                       value="${config.discord_bot_token || ''}"
                                       placeholder="Your Discord bot token" required>
                                <div class="form-text">
                                    <i class="bi bi-info-circle me-1"></i>
                                    Create a bot at <a href="https://discord.com/developers/applications" target="_blank" class="link-info">Discord Developer Portal</a>
                                </div>
                            </div>

                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label for="discord-channel-id" class="form-label">Channel ID</label>
                                    <input type="text" class="form-control" id="discord-channel-id"
                                           value="${config.discord_channel_id || ''}"
                                           pattern="[0-9]+" placeholder="123456789012345678" required>
                                    <div class="form-text">Discord channel ID (numbers only)</div>
                                </div>
                                <div class="col-md-6">
                                    <label for="discord-guild-id" class="form-label">Guild ID</label>
                                    <input type="text" class="form-control" id="discord-guild-id"
                                           value="${config.discord_guild_id || ''}"
                                           pattern="[0-9]+" placeholder="123456789012345678" required>
                                    <div class="form-text">Discord server/guild ID (numbers only)</div>
                                </div>
                            </div>

                            <div class="d-flex justify-content-end">
                                <button type="submit" class="btn btn-secondary">
                                    <i class="bi bi-check-circle me-1"></i>
                                    Save Discord Settings
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Message Filtering Section -->
                <div class="card mb-4">
                    <div class="card-header bg-secondary text-white">
                        <h5 class="card-title mb-1">
                            <i class="bi bi-funnel me-2"></i>
                            Message Filtering
                        </h5>
                        <small class="text-white-50">Configure message filtering and processing options</small>
                    </div>
                    <div class="card-body">
                        <form id="filtering-config-form">
                            <div class="row mb-3">
                                <div class="col-md-6">
                                    <label for="message-prefix" class="form-label">Message Prefix</label>
                                    <input type="text" class="form-control" id="message-prefix"
                                           value="${config.message_prefix || 'RARSMS'}"
                                           placeholder="RARSMS" required>
                                    <div class="form-text">Prefix required for message processing</div>
                                </div>
                                <div class="col-md-6">
                                    <label for="deduplication-timeout" class="form-label">Deduplication Timeout</label>
                                    <div class="input-group">
                                        <input type="number" class="form-control" id="deduplication-timeout"
                                               value="${config.deduplication_timeout || 600}"
                                               min="60" max="3600" required>
                                        <span class="input-group-text">seconds</span>
                                    </div>
                                    <div class="form-text">Time to ignore duplicate messages</div>
                                </div>
                            </div>

                            <div class="mb-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="require-prefix"
                                           ${config.require_prefix !== false ? 'checked' : ''}>
                                    <label class="form-check-label" for="require-prefix">
                                        Require message prefix for processing
                                    </label>
                                    <div class="form-text">Only process messages that start with the prefix</div>
                                </div>
                            </div>

                            <div class="mb-4">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="block-position-updates"
                                           ${config.block_position_updates !== false ? 'checked' : ''}>
                                    <label class="form-check-label" for="block-position-updates">
                                        Block position updates
                                    </label>
                                    <div class="form-text">Only process text messages, ignore position packets</div>
                                </div>
                            </div>

                            <div class="d-flex justify-content-end">
                                <button type="submit" class="btn btn-secondary">
                                    <i class="bi bi-check-circle me-1"></i>
                                    Save Filtering Settings
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                <!-- Database Configuration Section -->
                <div class="card mb-4">
                    <div class="card-header bg-secondary text-white">
                        <h5 class="card-title mb-1">
                            <i class="bi bi-database me-2"></i>
                            Database Configuration
                        </h5>
                        <small class="text-white-50">PocketBase connection settings</small>
                    </div>
                    <div class="card-body">
                        <form id="database-config-form">
                            <div class="mb-3">
                                <label for="pocketbase-url" class="form-label">PocketBase URL</label>
                                <input type="url" class="form-control" id="pocketbase-url"
                                       value="${config.pocketbase_url || 'http://pocketbase:8090'}"
                                       placeholder="http://pocketbase:8090" required>
                                <div class="form-text">
                                    <i class="bi bi-info-circle me-1"></i>
                                    Use 'pocketbase:8090' for Docker, 'localhost:8090' for local development
                                </div>
                            </div>

                            <div class="d-flex justify-content-end">
                                <button type="submit" class="btn btn-secondary">
                                    <i class="bi bi-check-circle me-1"></i>
                                    Save Database Settings
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            `;

            // Setup form handlers
            this.setupConfigFormHandlers();

        } catch (error) {
            console.error('Failed to load configuration:', error);
            container.innerHTML = '<div class="empty-search">Error loading configuration</div>';
        }
    }

    setupAuthentication() {
        // Check if already logged in
        const savedAuth = localStorage.getItem('pb_admin_auth');
        if (savedAuth) {
            try {
                const authData = JSON.parse(savedAuth);
                this.pb.authStore.save(authData.token, authData.model);
                if (this.pb.authStore.isValid) {
                    this.isAdmin = true;
                    this.updateAdminUI();
                }
            } catch (error) {
                localStorage.removeItem('pb_admin_auth');
            }
        }

        // Admin tab protection is now handled in switchTab method

        // Setup login form
        const loginForm = document.getElementById('login-form');
        const loginModal = document.getElementById('login-modal');
        const modalClose = document.getElementById('modal-close');
        const cancelLogin = document.getElementById('cancel-login');
        const logoutBtn = document.getElementById('logout-btn');

        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.performLogin();
            });
        }

        if (modalClose) {
            modalClose.addEventListener('click', () => this.hideLoginModal());
        }

        if (cancelLogin) {
            cancelLogin.addEventListener('click', () => this.hideLoginModal());
        }

        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.performLogout());
        }

        // Bootstrap Modal handles outside click automatically
    }

    showLoginModal() {
        const modal = document.getElementById('login-modal');
        const errorDiv = document.getElementById('login-error');

        // Clear previous errors and form
        if (document.getElementById('admin-email')) {
            document.getElementById('admin-email').value = '';
        }
        if (document.getElementById('admin-password')) {
            document.getElementById('admin-password').value = '';
        }
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }

        if (modal) {
            // Use Bootstrap Modal API
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();

            // Focus on email input after modal is shown
            modal.addEventListener('shown.bs.modal', function() {
                const emailInput = document.getElementById('admin-email');
                if (emailInput) {
                    emailInput.focus();
                }
            }, { once: true });
        } else {
            console.error('Login modal not found!');
        }
    }

    hideLoginModal() {
        const modal = document.getElementById('login-modal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
            bsModal.hide();
        }
    }

    async performLogin() {
        const email = document.getElementById('admin-email').value;
        const password = document.getElementById('admin-password').value;
        const errorDiv = document.getElementById('login-error');
        const submitBtn = document.getElementById('submit-login');

        // Clear previous errors
        errorDiv.style.display = 'none';

        // Show loading state
        submitBtn.textContent = 'Logging in...';
        submitBtn.disabled = true;

        try {
            // Use the correct PocketBase users authentication endpoint
            const authData = await this.pb.collection('users').authWithPassword(email, password);

            // Check if user has admin role
            const user = authData.record;
            this.isAdmin = user.role === 'admin';

            if (!this.isAdmin) {
                throw new Error('Admin access required');
            }
            this.updateAdminUI();
            this.hideLoginModal();

            // Show success message briefly
            this.showNotification('✅ Successfully logged in as admin', 'success');

        } catch (error) {
            console.error('Login failed:', error);

            let errorMessage = 'Invalid email or password. Please try again.';
            if (error.message === 'Admin access required') {
                errorMessage = 'Your account does not have admin privileges. Contact an administrator.';
            }

            errorDiv.textContent = errorMessage;
            errorDiv.style.display = 'block';
        } finally {
            // Reset button state
            submitBtn.textContent = 'Login';
            submitBtn.disabled = false;
        }
    }

    performLogout() {
        // Clear authentication
        this.pb.authStore.clear();
        localStorage.removeItem('pb_admin_auth');
        this.isAdmin = false;

        // Update UI
        this.updateAdminUI();

        // Switch to a public tab if currently on admin tab
        if (this.currentTab === 'callsigns' || this.currentTab === 'config') {
            this.switchTab('live-feed');
        }

        this.showNotification('👋 Logged out successfully', 'info');
    }

    updateAdminUI() {
        const adminStatus = document.getElementById('admin-status');
        const adminTabs = document.querySelectorAll('.admin-required');

        if (this.isAdmin) {
            // Show admin status
            adminStatus.style.display = 'flex';
            document.getElementById('admin-info').textContent = 'Admin Logged In';

            // Enable admin tabs
            adminTabs.forEach(tab => {
                tab.classList.add('admin-unlocked');
                // Hide lock icon
                const lock = tab.querySelector('.admin-lock');
                if (lock) lock.style.display = 'none';
            });
        } else {
            // Hide admin status
            adminStatus.style.display = 'none';

            // Show locked state
            adminTabs.forEach(tab => {
                tab.classList.remove('admin-unlocked');
                // Show lock icon
                const lock = tab.querySelector('.admin-lock');
                if (lock) lock.style.display = 'inline';
            });
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Add to page
        document.body.appendChild(notification);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    // Debug method - can be called from console
    debugAuth() {
        return {
            isAdmin: this.isAdmin,
            authStore: this.pb.authStore.model,
            token: !!this.pb.authStore.token
        };
    }

    // ==========================================
    // Configuration Management Methods
    // ==========================================

    async loadConfigFromDatabase() {
        try {
            // Get all config records
            const records = await this.pb.collection('config').getFullList();

            // Convert array of records to config object
            const config = {};
            records.forEach(record => {
                // Handle JSON values
                if (typeof record.value === 'object') {
                    config[record.key] = record.value;
                } else {
                    config[record.key] = record.value;
                }
            });

            return config;
        } catch (error) {
            console.error('Failed to load config from database:', error);
            // Return default config if database fails
            return {
                aprs_server: 'rotate.aprs2.net',
                aprs_port: 14580,
                filter_lat: '35.7796',
                filter_lon: '-78.6382',
                filter_distance: 100,
                message_prefix: 'RARSMS',
                require_prefix: true,
                block_position_updates: true,
                deduplication_timeout: 600,
                pocketbase_url: 'http://pocketbase:8090'
            };
        }
    }

    async saveConfigToDatabase(key, value, category = 'general', description = '') {
        try {
            // Try to update existing record first
            const existingRecords = await this.pb.collection('config').getList(1, 1, {
                filter: `key = "${key}"`
            });

            if (existingRecords.items.length > 0) {
                // Update existing record
                await this.pb.collection('config').update(existingRecords.items[0].id, {
                    value: value,
                    category: category,
                    description: description
                });
            } else {
                // Create new record
                await this.pb.collection('config').create({
                    key: key,
                    value: value,
                    category: category,
                    description: description
                });
            }
        } catch (error) {
            console.error(`Failed to save config ${key}:`, error);
            throw error;
        }
    }

    setupConfigFormHandlers() {
        // APRS Configuration Form
        const aprsForm = document.getElementById('aprs-config-form');
        if (aprsForm) {
            aprsForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveAprsConfig();
            });
        }

        // Discord Configuration Form
        const discordForm = document.getElementById('discord-config-form');
        if (discordForm) {
            discordForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveDiscordConfig();
            });
        }

        // Filtering Configuration Form
        const filteringForm = document.getElementById('filtering-config-form');
        if (filteringForm) {
            filteringForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveFilteringConfig();
            });
        }

        // Database Configuration Form
        const databaseForm = document.getElementById('database-config-form');
        if (databaseForm) {
            databaseForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveDatabaseConfig();
            });
        }
    }

    async saveAprsConfig() {
        try {
            const aprsServer = document.getElementById('aprs-server').value.trim();
            const aprsPort = parseInt(document.getElementById('aprs-port').value);
            const aprsCallsign = document.getElementById('aprs-callsign').value.trim().toUpperCase();
            const aprsPasscode = document.getElementById('aprs-passcode').value.trim();
            const filterLat = document.getElementById('filter-lat').value;
            const filterLon = document.getElementById('filter-lon').value;
            const filterDistance = parseInt(document.getElementById('filter-distance').value);

            // Save each config item
            await Promise.all([
                this.saveConfigToDatabase('aprs_server', aprsServer, 'aprs', 'APRS-IS server hostname'),
                this.saveConfigToDatabase('aprs_port', aprsPort, 'aprs', 'APRS-IS server port'),
                this.saveConfigToDatabase('aprs_callsign', aprsCallsign, 'aprs', 'Your amateur radio callsign'),
                this.saveConfigToDatabase('aprs_passcode', aprsPasscode, 'aprs', 'APRS-IS passcode for your callsign'),
                this.saveConfigToDatabase('filter_lat', filterLat, 'aprs', 'Geographic filter latitude'),
                this.saveConfigToDatabase('filter_lon', filterLon, 'aprs', 'Geographic filter longitude'),
                this.saveConfigToDatabase('filter_distance', filterDistance, 'aprs', 'Geographic filter distance in km')
            ]);

            this.showNotification('✅ APRS configuration saved successfully', 'success');
        } catch (error) {
            console.error('Failed to save APRS config:', error);
            this.showNotification('❌ Failed to save APRS configuration', 'error');
        }
    }

    async saveDiscordConfig() {
        try {
            const botToken = document.getElementById('discord-bot-token').value.trim();
            const channelId = document.getElementById('discord-channel-id').value.trim();
            const guildId = document.getElementById('discord-guild-id').value.trim();

            await Promise.all([
                this.saveConfigToDatabase('discord_bot_token', botToken, 'discord', 'Discord bot authentication token'),
                this.saveConfigToDatabase('discord_channel_id', channelId, 'discord', 'Discord channel ID for messages'),
                this.saveConfigToDatabase('discord_guild_id', guildId, 'discord', 'Discord server/guild ID')
            ]);

            this.showNotification('✅ Discord configuration saved successfully', 'success');
        } catch (error) {
            console.error('Failed to save Discord config:', error);
            this.showNotification('❌ Failed to save Discord configuration', 'error');
        }
    }

    async saveFilteringConfig() {
        try {
            const messagePrefix = document.getElementById('message-prefix').value.trim();
            const deduplicationTimeout = parseInt(document.getElementById('deduplication-timeout').value);
            const requirePrefix = document.getElementById('require-prefix').checked;
            const blockPositionUpdates = document.getElementById('block-position-updates').checked;

            await Promise.all([
                this.saveConfigToDatabase('message_prefix', messagePrefix, 'filtering', 'Required message prefix for processing'),
                this.saveConfigToDatabase('deduplication_timeout', deduplicationTimeout, 'filtering', 'Message deduplication timeout in seconds'),
                this.saveConfigToDatabase('require_prefix', requirePrefix, 'filtering', 'Require message prefix for processing'),
                this.saveConfigToDatabase('block_position_updates', blockPositionUpdates, 'filtering', 'Block APRS position updates, process only text messages')
            ]);

            this.showNotification('✅ Filtering configuration saved successfully', 'success');
        } catch (error) {
            console.error('Failed to save filtering config:', error);
            this.showNotification('❌ Failed to save filtering configuration', 'error');
        }
    }

    async saveDatabaseConfig() {
        try {
            const pocketbaseUrl = document.getElementById('pocketbase-url').value.trim();

            await this.saveConfigToDatabase('pocketbase_url', pocketbaseUrl, 'database', 'PocketBase database connection URL');

            this.showNotification('✅ Database configuration saved successfully', 'success');
        } catch (error) {
            console.error('Failed to save database config:', error);
            this.showNotification('❌ Failed to save database configuration', 'error');
        }
    }

    // ==========================================
    // Callsign Management Methods
    // ==========================================

    async showAddCallsignModal() {
        if (!this.isAdmin) {
            this.showLoginModal();
            return;
        }

        // Create Bootstrap modal HTML
        const modalHtml = `
            <div class="modal fade" id="add-callsign-modal" tabindex="-1" aria-labelledby="addCallsignModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-secondary text-white">
                            <h5 class="modal-title" id="addCallsignModalLabel">
                                <i class="bi bi-plus-circle me-2"></i>
                                Add New Callsign
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="add-callsign-form">
                                <div class="mb-3">
                                    <label for="new-callsign" class="form-label">Callsign *</label>
                                    <input type="text" class="form-control" id="new-callsign" required
                                           placeholder="e.g., KK4PWJ or W1AW" pattern="[A-Za-z0-9]{3,7}"
                                           title="Callsign: 3-7 characters, letters and numbers only"
                                           style="text-transform: uppercase;">
                                    <div class="form-text">Amateur radio callsign (3-7 characters)</div>
                                </div>
                                <div class="mb-3">
                                    <label for="new-description" class="form-label">Description</label>
                                    <input type="text" class="form-control" id="new-description"
                                           placeholder="Optional description (e.g., 'Emergency coordinator', 'Net control')">
                                    <div class="form-text">Optional description to identify this callsign</div>
                                </div>
                                <div class="mb-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" id="new-enabled" checked>
                                        <label class="form-check-label" for="new-enabled">
                                            Enable immediately
                                        </label>
                                        <div class="form-text">Callsign will be active and able to send messages</div>
                                    </div>
                                </div>
                                <div class="d-flex justify-content-end gap-2">
                                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                                    <button type="submit" class="btn btn-secondary">
                                        <i class="bi bi-check-circle me-1"></i>
                                        Add Callsign
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existingModal = document.getElementById('add-callsign-modal');
        if (existingModal) existingModal.remove();

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Show modal
        const modalElement = document.getElementById('add-callsign-modal');
        const modal = new bootstrap.Modal(modalElement);
        modal.show();

        // Handle form submission
        document.getElementById('add-callsign-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.addCallsign();
            modal.hide();
        });
    }

    async addCallsign() {
        const callsign = document.getElementById('new-callsign').value.toUpperCase().trim();
        const description = document.getElementById('new-description').value.trim();
        const enabled = document.getElementById('new-enabled').checked;

        try {
            await this.pb.collection('authorized_callsigns').create({
                callsign: callsign,
                description: description || '',
                enabled: enabled
            });

            this.showNotification('✅ Callsign added successfully', 'success');
            await this.loadCallsignsTab(); // Refresh the list
        } catch (error) {
            console.error('Failed to add callsign:', error);
            if (error.message.includes('duplicate')) {
                this.showNotification('❌ Callsign already exists', 'error');
            } else {
                this.showNotification('❌ Failed to add callsign', 'error');
            }
        }
    }

    async toggleCallsign(callsignId) {
        if (!this.isAdmin) return;

        try {
            // Get current record
            const record = await this.pb.collection('authorized_callsigns').getOne(callsignId);

            // Toggle enabled status
            await this.pb.collection('authorized_callsigns').update(callsignId, {
                enabled: !record.enabled
            });

            this.showNotification(`✅ Callsign ${record.enabled ? 'disabled' : 'enabled'}`, 'success');
            await this.loadCallsignsTab(); // Refresh the list
        } catch (error) {
            console.error('Failed to toggle callsign:', error);
            this.showNotification('❌ Failed to update callsign', 'error');
        }
    }

    async deleteCallsign(callsignId) {
        if (!this.isAdmin) return;

        try {
            // Get record for confirmation
            const record = await this.pb.collection('authorized_callsigns').getOne(callsignId);

            if (!confirm(`Are you sure you want to delete callsign "${record.callsign}"?\n\nThis action cannot be undone.`)) {
                return;
            }

            await this.pb.collection('authorized_callsigns').delete(callsignId);

            this.showNotification('✅ Callsign deleted successfully', 'success');
            await this.loadCallsignsTab(); // Refresh the list
        } catch (error) {
            console.error('Failed to delete callsign:', error);
            this.showNotification('❌ Failed to delete callsign', 'error');
        }
    }

    async editCallsign(callsignId) {
        if (!this.isAdmin) return;

        try {
            const record = await this.pb.collection('authorized_callsigns').getOne(callsignId);

            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>✏️ Edit Callsign</h2>
                        <button onclick="this.parentElement.parentElement.parentElement.remove()" class="modal-close">&times;</button>
                    </div>
                    <form id="edit-callsign-form" class="modal-form">
                        <div class="form-group">
                            <label for="edit-callsign">Callsign *</label>
                            <input type="text" id="edit-callsign" required value="${record.callsign}"
                                   pattern="[A-Za-z0-9]{3,7}" title="Callsign: 3-7 characters, letters and numbers only"
                                   style="text-transform: uppercase;">
                        </div>
                        <div class="form-group">
                            <label for="edit-description">Description</label>
                            <input type="text" id="edit-description" value="${record.description || ''}"
                                   placeholder="Optional description">
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="edit-enabled" ${record.enabled ? 'checked' : ''}>
                                Enabled (active)
                            </label>
                        </div>
                        <div class="form-actions">
                            <button type="button" onclick="this.closest('.modal-overlay').remove()" class="btn-secondary">Cancel</button>
                            <button type="submit" class="btn-primary">Save Changes</button>
                        </div>
                    </form>
                </div>
            `;

            document.body.appendChild(modal);

            // Handle form submission
            document.getElementById('edit-callsign-form').addEventListener('submit', async (e) => {
                e.preventDefault();

                const callsign = document.getElementById('edit-callsign').value.toUpperCase().trim();
                const description = document.getElementById('edit-description').value.trim();
                const enabled = document.getElementById('edit-enabled').checked;

                try {
                    await this.pb.collection('authorized_callsigns').update(callsignId, {
                        callsign: callsign,
                        description: description || '',
                        enabled: enabled
                    });

                    this.showNotification('✅ Callsign updated successfully', 'success');
                    await this.loadCallsignsTab(); // Refresh the list
                    modal.remove();
                } catch (error) {
                    console.error('Failed to update callsign:', error);
                    this.showNotification('❌ Failed to update callsign', 'error');
                }
            });

        } catch (error) {
            console.error('Failed to load callsign for editing:', error);
            this.showNotification('❌ Failed to load callsign data', 'error');
        }
    }
}

// Global viewer instance
let viewer;

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    viewer = new RARSMSViewer();
});

// Handle connection errors and retry
window.addEventListener('online', () => {
    location.reload();
});

window.addEventListener('offline', () => {
    document.getElementById('connection-status').innerHTML = '<span>📶 Offline</span>';
    document.getElementById('connection-status').className = 'status-item status-disconnected';
});