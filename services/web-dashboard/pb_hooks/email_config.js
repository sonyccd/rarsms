// Email configuration and utilities for PocketBase
// This file handles email settings and provides helper functions

// Load email configuration from environment variables
const EMAIL_CONFIG = {
    smtp: {
        host: process.env.SMTP_HOST || "smtp.gmail.com",
        port: parseInt(process.env.SMTP_PORT) || 587,
        username: process.env.SMTP_USERNAME || "",
        password: process.env.SMTP_PASSWORD || "",
        tls: process.env.SMTP_TLS === "true" || true
    },
    from: {
        address: process.env.FROM_EMAIL || "rarsms@rars.org",
        name: process.env.FROM_NAME || "RARSMS System"
    },
    admin_emails: (process.env.ADMIN_EMAILS || "admin@rars.org").split(",").map(email => email.trim()),
    system_url: process.env.SYSTEM_URL || "http://localhost:8090",
    development: {
        enabled: process.env.EMAIL_DEV_MODE === "true" || false,
        log_only: process.env.EMAIL_LOG_ONLY === "true" || false,
        test_recipient: process.env.EMAIL_TEST_RECIPIENT || ""
    }
}

// Validate email configuration
function validateEmailConfig() {
    const required = ['smtp.username', 'smtp.password']
    const missing = []

    if (!EMAIL_CONFIG.smtp.username) missing.push('SMTP_USERNAME')
    if (!EMAIL_CONFIG.smtp.password) missing.push('SMTP_PASSWORD')

    if (missing.length > 0) {
        console.warn(`Email configuration incomplete. Missing: ${missing.join(', ')}`)
        return false
    }

    return true
}

// Configure PocketBase mailer
function configureMailer() {
    try {
        if (!validateEmailConfig()) {
            console.warn("Email functionality disabled due to incomplete configuration")
            return false
        }

        // Configure SMTP settings
        $app.settings().smtp.enabled = true
        $app.settings().smtp.host = EMAIL_CONFIG.smtp.host
        $app.settings().smtp.port = EMAIL_CONFIG.smtp.port
        $app.settings().smtp.username = EMAIL_CONFIG.smtp.username
        $app.settings().smtp.password = EMAIL_CONFIG.smtp.password
        $app.settings().smtp.tls = EMAIL_CONFIG.smtp.tls

        // Set sender info
        $app.settings().meta.senderName = EMAIL_CONFIG.from.name
        $app.settings().meta.senderAddress = EMAIL_CONFIG.from.address

        console.log("Email configuration applied successfully")
        return true
    } catch (error) {
        console.error("Failed to configure email:", error)
        return false
    }
}

// Email template functions
const EMAIL_TEMPLATES = {
    adminApproval: (data) => ({
        subject: `RARSMS Account Approval Required - ${data.callsign}`,
        html: `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #667eea; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">RARSMS</h1>
                    <p style="margin: 5px 0 0 0;">Raleigh Amateur Radio Society Messaging Service</p>
                </div>

                <div style="padding: 30px; background: #f8f9fa;">
                    <h2 style="color: #4a5568; margin-top: 0;">New Account Registration</h2>

                    <p>A new member has registered for RARSMS access and requires approval:</p>

                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <table style="width: 100%;">
                            <tr>
                                <td style="padding: 5px 0; font-weight: bold;">Callsign:</td>
                                <td style="padding: 5px 0;">${data.callsign}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px 0; font-weight: bold;">Name:</td>
                                <td style="padding: 5px 0;">${data.name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px 0; font-weight: bold;">Email:</td>
                                <td style="padding: 5px 0;">${data.email}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px 0; font-weight: bold;">Registration Date:</td>
                                <td style="padding: 5px 0;">${new Date(data.created).toLocaleString()}</td>
                            </tr>
                        </table>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="${EMAIL_CONFIG.system_url}/_/"
                           style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                            Review in Admin Panel
                        </a>
                    </div>

                    <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <strong>⚠️ Important:</strong> This request will expire in 7 days if not processed.
                    </div>
                </div>

                <div style="background: #6c757d; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p style="margin: 0;">RARSMS - Bridging Amateur Radio Networks</p>
                    <p style="margin: 5px 0 0 0;">This is an automated message from the RARSMS system.</p>
                </div>
            </div>
        `
    }),

    userPending: (data) => ({
        subject: `RARSMS Account Under Review - ${data.callsign}`,
        html: `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #667eea; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">RARSMS</h1>
                    <p style="margin: 5px 0 0 0;">Raleigh Amateur Radio Society Messaging Service</p>
                </div>

                <div style="padding: 30px; background: #f8f9fa;">
                    <h2 style="color: #4a5568; margin-top: 0;">Registration Received</h2>

                    <p>Hello ${data.name || data.callsign},</p>

                    <p>Your RARSMS account registration has been received and is under review by club administrators.</p>

                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <table style="width: 100%;">
                            <tr>
                                <td style="padding: 5px 0; font-weight: bold;">Callsign:</td>
                                <td style="padding: 5px 0;">${data.callsign}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px 0; font-weight: bold;">Registration Date:</td>
                                <td style="padding: 5px 0;">${new Date(data.created).toLocaleString()}</td>
                            </tr>
                        </table>
                    </div>

                    <div style="background: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <strong>📧 Next Steps:</strong>
                        <ul style="margin: 10px 0 0 20px;">
                            <li>You will receive an email confirmation once your account is approved</li>
                            <li>This process typically takes 1-2 business days</li>
                            <li>If you have questions, please contact the club administrators</li>
                        </ul>
                    </div>

                    <p>Thank you for your patience.</p>

                    <p>73,<br>
                    <strong>RARSMS System</strong></p>
                </div>

                <div style="background: #6c757d; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p style="margin: 0;">RARSMS - Bridging Amateur Radio Networks</p>
                    <p style="margin: 5px 0 0 0;">This is an automated message from the RARSMS system.</p>
                </div>
            </div>
        `
    }),

    userApproved: (data) => ({
        subject: `RARSMS Account Activated - ${data.callsign}`,
        html: `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #28a745; color: white; padding: 20px; text-align: center;">
                    <h1 style="margin: 0;">RARSMS</h1>
                    <p style="margin: 5px 0 0 0;">Raleigh Amateur Radio Society Messaging Service</p>
                </div>

                <div style="padding: 30px; background: #f8f9fa;">
                    <h2 style="color: #4a5568; margin-top: 0;">🎉 Account Approved!</h2>

                    <p>Hello ${data.name || data.callsign},</p>

                    <p>Great news! Your RARSMS account has been approved and activated!</p>

                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <table style="width: 100%;">
                            <tr>
                                <td style="padding: 5px 0; font-weight: bold;">Callsign:</td>
                                <td style="padding: 5px 0;">${data.callsign}</td>
                            </tr>
                            <tr>
                                <td style="padding: 5px 0; font-weight: bold;">Account Status:</td>
                                <td style="padding: 5px 0; color: #28a745; font-weight: bold;">✅ Active</td>
                            </tr>
                        </table>
                    </div>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="${EMAIL_CONFIG.system_url}"
                           style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                            Access Your Dashboard
                        </a>
                    </div>

                    <div style="background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <strong>🔧 You can now:</strong>
                        <ul style="margin: 10px 0 0 20px;">
                            <li>Send messages to RARSMS via APRS and see them in Discord</li>
                            <li>View your complete message history</li>
                            <li>Monitor system status and health</li>
                            <li>Manage your account settings</li>
                        </ul>
                    </div>

                    <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 6px; margin: 20px 0;">
                        <strong>📡 Getting Started:</strong>
                        <p style="margin: 5px 0;">To send a message via APRS, simply send to callsign <strong>RARSMS</strong> and it will appear in the club Discord channel.</p>
                    </div>

                    <p>Welcome to RARSMS!</p>

                    <p>73,<br>
                    <strong>RARSMS System</strong></p>
                </div>

                <div style="background: #6c757d; color: white; padding: 15px; text-align: center; font-size: 12px;">
                    <p style="margin: 0;">RARSMS - Bridging Amateur Radio Networks</p>
                    <p style="margin: 5px 0 0 0;">This is an automated message from the RARSMS system.</p>
                </div>
            </div>
        `
    })
}

// Send email function with error handling and logging
function sendEmail(to, template, data) {
    try {
        // Skip if email not configured
        if (!validateEmailConfig()) {
            console.log(`[EMAIL] Skipped (not configured): ${template} to ${to}`)
            return false
        }

        // Development mode handling
        if (EMAIL_CONFIG.development.enabled) {
            if (EMAIL_CONFIG.development.log_only) {
                console.log(`[EMAIL] Dev Mode (log only): ${template} to ${to}`)
                console.log(`[EMAIL] Data:`, JSON.stringify(data, null, 2))
                return true
            }

            if (EMAIL_CONFIG.development.test_recipient) {
                to = EMAIL_CONFIG.development.test_recipient
                console.log(`[EMAIL] Dev Mode: Redirecting to ${to}`)
            }
        }

        // Get email template
        if (!EMAIL_TEMPLATES[template]) {
            console.error(`[EMAIL] Unknown template: ${template}`)
            return false
        }

        const emailContent = EMAIL_TEMPLATES[template](data)

        // Create and send message
        const message = new MailerMessage({
            from: {
                address: EMAIL_CONFIG.from.address,
                name: EMAIL_CONFIG.from.name
            },
            to: [{ address: to }],
            subject: emailContent.subject,
            html: emailContent.html
        })

        $app.newMailClient().send(message)

        console.log(`[EMAIL] Sent: ${template} to ${to}`)

        // Log email activity
        const logRecord = new Record($app.dao().findCollectionByNameOrId("system_logs"))
        logRecord.set("level", "info")
        logRecord.set("service", "pocketbase")
        logRecord.set("event_type", "email")
        logRecord.set("message", `Email sent: ${template} to ${to}`)
        logRecord.set("metadata", {
            template: template,
            recipient: to,
            subject: emailContent.subject
        })
        $app.dao().saveRecord(logRecord)

        return true

    } catch (error) {
        console.error(`[EMAIL] Failed to send ${template} to ${to}:`, error)

        // Log email error
        const logRecord = new Record($app.dao().findCollectionByNameOrId("system_logs"))
        logRecord.set("level", "error")
        logRecord.set("service", "pocketbase")
        logRecord.set("event_type", "email")
        logRecord.set("message", `Email failed: ${template} to ${to} - ${error.message}`)
        logRecord.set("metadata", {
            template: template,
            recipient: to,
            error: error.message
        })
        $app.dao().saveRecord(logRecord)

        return false
    }
}

// Send notification to all admins
function notifyAdmins(template, data) {
    let successCount = 0

    EMAIL_CONFIG.admin_emails.forEach(email => {
        if (sendEmail(email, template, data)) {
            successCount++
        }
    })

    console.log(`[EMAIL] Admin notification: ${successCount}/${EMAIL_CONFIG.admin_emails.length} sent`)
    return successCount > 0
}

// Initialize email configuration on startup
console.log("[EMAIL] Initializing email configuration...")
if (configureMailer()) {
    console.log("[EMAIL] Email system ready")
} else {
    console.log("[EMAIL] Email system disabled")
}

// Export functions for use in other hooks
if (typeof module !== 'undefined') {
    module.exports = {
        sendEmail,
        notifyAdmins,
        EMAIL_TEMPLATES,
        EMAIL_CONFIG,
        validateEmailConfig
    }
}