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

    setupTabNavigation() {
        const navTabs = document.querySelectorAll('.nav-tab');
        const tabContents = document.querySelectorAll('.tab-content');

        navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.getAttribute('data-tab');
                this.switchTab(tabId);
            });
        });
    }

    switchTab(tabId) {
        console.log('switchTab called with:', tabId);

        // Check if admin access is required
        const targetTab = document.querySelector(`[data-tab="${tabId}"]`);
        console.log('Target tab:', targetTab);
        console.log('Has admin-required class:', targetTab?.classList.contains('admin-required'));
        console.log('Is admin:', this.isAdmin);

        if (targetTab && targetTab.classList.contains('admin-required') && !this.isAdmin) {
            console.log('Showing login modal...');
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

            container.innerHTML = callsigns.map(callsign => `
                <div class="callsign-card">
                    <div class="callsign-header">
                        <strong>${callsign.callsign}</strong>
                        <span class="status-badge ${callsign.enabled ? 'enabled' : 'disabled'}">
                            ${callsign.enabled ? '✓ Active' : '✗ Disabled'}
                        </span>
                    </div>
                    <div class="callsign-description">${callsign.description || 'No description'}</div>
                    <div class="callsign-actions">
                        <button onclick="viewer.toggleCallsign('${callsign.id}')" class="btn-toggle">
                            ${callsign.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button onclick="viewer.deleteCallsign('${callsign.id}')" class="btn-delete">Delete</button>
                    </div>
                </div>
            `).join('');

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
        container.innerHTML = '<div class="loading-placeholder">Configuration management coming soon...</div>';
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

        // Close modal on outside click
        if (loginModal) {
            loginModal.addEventListener('click', (e) => {
                if (e.target === loginModal) {
                    this.hideLoginModal();
                }
            });
        }
    }

    showLoginModal() {
        console.log('showLoginModal called');
        const modal = document.getElementById('login-modal');
        const errorDiv = document.getElementById('login-error');

        console.log('Modal element:', modal);
        console.log('Error div:', errorDiv);

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
            modal.style.display = 'flex';
            console.log('Modal display set to flex');

            const emailInput = document.getElementById('admin-email');
            if (emailInput) {
                emailInput.focus();
            }
        } else {
            console.error('Login modal not found!');
        }
    }

    hideLoginModal() {
        document.getElementById('login-modal').style.display = 'none';
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
            console.log('Attempting login with:', email);

            // Use the correct PocketBase users authentication endpoint
            const authData = await this.pb.collection('users').authWithPassword(email, password);

            console.log('Authentication successful:', authData);

            // Check if user has admin role
            const user = authData.record;
            this.isAdmin = user.role === 'admin';

            console.log('User role:', user.role, 'Is admin:', this.isAdmin);

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
        console.log('Admin status:', this.isAdmin);
        console.log('Auth store:', this.pb.authStore);
        console.log('Admin tabs:', document.querySelectorAll('.admin-required'));
        return {
            isAdmin: this.isAdmin,
            authStore: this.pb.authStore.model,
            token: !!this.pb.authStore.token
        };
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