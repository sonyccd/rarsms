// PocketBase hooks for RARSMS user approval workflow and automated setup

// Collections will be created manually through the PocketBase UI

// Email configuration (inline to avoid module issues)
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
    system_url: process.env.SYSTEM_URL || "http://localhost:8090"
}

// Configuration
const APPROVAL_EXPIRY_DAYS = 7

// Helper function to send email
function sendEmail(to, subject, body) {
    try {
        const message = new MailerMessage({
            from: {
                address: EMAIL_CONFIG.from.address,
                name: EMAIL_CONFIG.from.name
            },
            to: [{address: to}],
            subject: subject,
            html: body
        })

        $app.newMailClient().send(message)
        console.log(`[EMAIL] Sent: ${subject} to ${to}`)
        return true
    } catch (error) {
        console.error(`[EMAIL] Failed to send to ${to}:`, error)
        return false
    }
}

// Helper function to notify all admins
function notifyAdmins(subject, body) {
    let successCount = 0
    EMAIL_CONFIG.admin_emails.forEach(email => {
        if (sendEmail(email, subject, body)) {
            successCount++
        }
    })
    return successCount > 0
}

// Helper function to create expiry date
function getExpiryDate() {
    const date = new Date()
    date.setDate(date.getDate() + APPROVAL_EXPIRY_DAYS)
    return date.toISOString()
}

// Hook: User registration
onRecordAfterCreateRequest((e) => {
    if (e.record.collection().name === "users" && e.record.get("role") === "member") {
        try {
            // Create pending approval record
            const pendingApproval = new Record($app.dao().findCollectionByNameOrId("pending_approvals"))
            pendingApproval.set("user", e.record.getId())
            pendingApproval.set("callsign", e.record.get("username"))
            pendingApproval.set("name", e.record.get("name") || e.record.get("username"))
            pendingApproval.set("email", e.record.get("email"))
            pendingApproval.set("expires_at", getExpiryDate())
            pendingApproval.set("admin_notified", false)
            pendingApproval.set("user_notified", false)

            $app.dao().saveRecord(pendingApproval)

            // Send admin notification
            notifyAdmins("adminApproval", {
                callsign: e.record.get("username"),
                name: e.record.get("name") || e.record.get("username"),
                email: e.record.get("email"),
                created: e.record.get("created")
            })

            // Send user notification
            sendEmail(e.record.get("email"), "userPending", {
                callsign: e.record.get("username"),
                name: e.record.get("name") || e.record.get("username"),
                email: e.record.get("email"),
                created: e.record.get("created")
            })

            // Update pending approval flags
            pendingApproval.set("admin_notified", true)
            pendingApproval.set("user_notified", true)
            $app.dao().saveRecord(pendingApproval)

            // Log the registration
            const logRecord = new Record($app.dao().findCollectionByNameOrId("system_logs"))
            logRecord.set("level", "info")
            logRecord.set("service", "pocketbase")
            logRecord.set("event_type", "registration")
            logRecord.set("message", `New user registration: ${e.record.get("username")}`)
            logRecord.set("metadata", {
                "callsign": e.record.get("username"),
                "email": e.record.get("email"),
                "expires_at": getExpiryDate()
            })
            logRecord.set("user", e.record.getId())
            $app.dao().saveRecord(logRecord)

        } catch (error) {
            console.error("Error in user registration hook:", error)
        }
    }
})

// Hook: User approval
onRecordAfterUpdateRequest((e) => {
    if (e.record.collection().name === "users") {
        const wasApproved = e.record.get("approved") && !e.oldRecord.get("approved")

        if (wasApproved) {
            try {
                // Create member profile
                const memberProfile = new Record($app.dao().findCollectionByNameOrId("member_profiles"))
                memberProfile.set("user", e.record.getId())
                memberProfile.set("callsign", e.record.get("username"))
                memberProfile.set("name", e.record.get("name") || e.record.get("username"))
                memberProfile.set("joined_date", new Date().toISOString().split('T')[0])

                $app.dao().saveRecord(memberProfile)

                // Send approval email
                sendEmail(e.record.get("email"), "userApproved", {
                    callsign: e.record.get("username"),
                    name: e.record.get("name") || e.record.get("username"),
                    email: e.record.get("email")
                })

                // Clean up pending approval
                $app.dao().deleteRecord($app.dao().findFirstRecordByFilter(
                    "pending_approvals",
                    `user = "${e.record.getId()}"`
                ))

                // Log the approval
                const logRecord = new Record($app.dao().findCollectionByNameOrId("system_logs"))
                logRecord.set("level", "info")
                logRecord.set("service", "pocketbase")
                logRecord.set("event_type", "approval")
                logRecord.set("message", `User account approved: ${e.record.get("username")}`)
                logRecord.set("metadata", {
                    "callsign": e.record.get("username"),
                    "approved_by": e.record.get("approved_by")
                })
                logRecord.set("user", e.record.getId())
                $app.dao().saveRecord(logRecord)

            } catch (error) {
                console.error("Error in user approval hook:", error)
            }
        }
    }
})

// Hook: User deletion (cleanup all related data)
onRecordBeforeDeleteRequest((e) => {
    if (e.record.collection().name === "users") {
        try {
            const userId = e.record.getId()
            const callsign = e.record.get("username")

            // Delete member profile
            const memberProfile = $app.dao().findFirstRecordByFilter("member_profiles", `user = "${userId}"`)
            if (memberProfile) {
                $app.dao().deleteRecord(memberProfile)
            }

            // Delete all messages by this user
            const messages = $app.dao().findRecordsByFilter("messages", `user = "${userId}"`)
            messages.forEach(message => {
                $app.dao().deleteRecord(message)
            })

            // Delete conversations initiated by this user
            const conversations = $app.dao().findRecordsByFilter("conversations", `initiated_by = "${userId}"`)
            conversations.forEach(conversation => {
                $app.dao().deleteRecord(conversation)
            })

            // Delete APRS packets from this callsign
            const packets = $app.dao().findRecordsByFilter("aprs_packets", `from_callsign = "${callsign}"`)
            packets.forEach(packet => {
                $app.dao().deleteRecord(packet)
            })

            // Delete Discord threads initiated by this user
            const threads = $app.dao().findRecordsByFilter("discord_threads", `initiated_by = "${userId}"`)
            threads.forEach(thread => {
                $app.dao().deleteRecord(thread)
            })

            // Delete pending approval if exists
            const pendingApproval = $app.dao().findFirstRecordByFilter("pending_approvals", `user = "${userId}"`)
            if (pendingApproval) {
                $app.dao().deleteRecord(pendingApproval)
            }

            // Log the deletion (keep audit trail)
            const logRecord = new Record($app.dao().findCollectionByNameOrId("system_logs"))
            logRecord.set("level", "info")
            logRecord.set("service", "pocketbase")
            logRecord.set("event_type", "deletion")
            logRecord.set("message", `User account deleted: ${callsign}`)
            logRecord.set("metadata", {
                "callsign": callsign,
                "user_id": userId,
                "deletion_type": "user_requested"
            })
            $app.dao().saveRecord(logRecord)

        } catch (error) {
            console.error("Error in user deletion hook:", error)
        }
    }
})

// Scheduled task: Clean up expired pending approvals (run daily)
cronAdd("cleanup-expired", "0 2 * * *", () => {
    try {
        const now = new Date().toISOString()
        const expiredApprovals = $app.dao().findRecordsByFilter(
            "pending_approvals",
            `expires_at < "${now}"`
        )

        expiredApprovals.forEach(approval => {
            const userId = approval.get("user")
            const callsign = approval.get("callsign")

            // Delete the user account
            const user = $app.dao().findRecordById("users", userId)
            if (user) {
                $app.dao().deleteRecord(user)
            }

            // Delete the pending approval
            $app.dao().deleteRecord(approval)

            // Log the expiry
            const logRecord = new Record($app.dao().findCollectionByNameOrId("system_logs"))
            logRecord.set("level", "info")
            logRecord.set("service", "pocketbase")
            logRecord.set("event_type", "expiry")
            logRecord.set("message", `Expired pending approval deleted: ${callsign}`)
            logRecord.set("metadata", {
                "callsign": callsign,
                "user_id": userId,
                "deletion_type": "expired"
            })
            $app.dao().saveRecord(logRecord)
        })

        if (expiredApprovals.length > 0) {
            console.log(`Cleaned up ${expiredApprovals.length} expired pending approvals`)
        }

    } catch (error) {
        console.error("Error in cleanup expired approvals:", error)
    }
})