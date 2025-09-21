# 📦 PocketBase Collections Setup

After setting up your admin account at http://localhost:8090/_/, you need to create the following collections manually through the PocketBase admin interface.

## Required Collections

### 1. **member_profiles** (Base Collection)

**Settings:**
- Type: Base
- Name: `member_profiles`

**API Rules:**
- List rule: `@request.auth.role = 'admin'`
- View rule: `@request.auth.id = user || @request.auth.role = 'admin'`
- Create rule: `@request.auth.role = 'admin'`
- Update rule: `@request.auth.id = user || @request.auth.role = 'admin'`
- Delete rule: `@request.auth.role = 'admin'`

**Fields:**
- `user` - Relation (required, unique) → users, cascade delete, max 1, display: username, email
- `callsign` - Text (required, unique) → min: 3, max: 10, pattern: `^[A-Z0-9]+$`
- `name` - Text (required) → min: 1, max: 100
- `discord_id` - Text (optional) → max: 20
- `joined_date` - Date (optional)
- `last_login` - Date (optional)
- `notes` - Editor (optional)

### 2. **messages** (Base Collection)

**Settings:**
- Type: Base
- Name: `messages`

**API Rules:**
- List rule: `@request.auth.role = 'admin' || @request.auth.id = user`
- View rule: `@request.auth.role = 'admin' || @request.auth.id = user`
- Create rule: `@request.auth.id != ""`
- Update rule: `@request.auth.role = 'admin'`
- Delete rule: `@request.auth.role = 'admin'`

**Fields:**
- `correlation_id` - Text (required) → max: 50
- `user` - Relation (optional) → users, cascade delete, max 1, display: username
- `from_callsign` - Text (optional) → max: 10
- `to_callsign` - Text (optional) → max: 10
- `content` - Text (required) → max: 500
- `platform` - Select (required) → values: aprs, discord, web
- `status` - Select (required) → values: pending, sent, delivered, failed
- `direction` - Select (required) → values: inbound, outbound
- `metadata` - JSON (optional)

### 3. **conversations** (Base Collection)

**Settings:**
- Type: Base
- Name: `conversations`

**API Rules:**
- List rule: `@request.auth.role = 'admin' || @request.auth.id = initiated_by`
- View rule: `@request.auth.role = 'admin' || @request.auth.id = initiated_by`
- Create rule: `@request.auth.id != ""`
- Update rule: `@request.auth.role = 'admin' || @request.auth.id = initiated_by`
- Delete rule: `@request.auth.role = 'admin'`

**Fields:**
- `correlation_id` - Text (required, unique) → max: 50
- `initiated_by` - Relation (optional) → users, cascade delete, max 1, display: username
- `participants` - Text (required) → max: 100
- `platform` - Select (required) → values: aprs, discord, web
- `status` - Select (required) → values: active, closed, archived
- `last_activity` - Date (optional)
- `metadata` - JSON (optional)

### 4. **aprs_packets** (Base Collection)

**Settings:**
- Type: Base
- Name: `aprs_packets`

**API Rules:**
- List rule: `@request.auth.role = 'admin'`
- View rule: `@request.auth.role = 'admin'`
- Create rule: `@request.auth.role = 'admin'`
- Update rule: `@request.auth.role = 'admin'`
- Delete rule: `@request.auth.role = 'admin'`

**Fields:**
- `raw_packet` - Text (required) → max: 1000
- `from_callsign` - Text (required) → max: 10
- `to_callsign` - Text (optional) → max: 10
- `message` - Text (optional) → max: 500
- `packet_type` - Select (required) → values: message, position, status, other
- `processed` - Bool (required)
- `correlation_id` - Text (optional) → max: 50
- `metadata` - JSON (optional)

### 5. **discord_threads** (Base Collection)

**Settings:**
- Type: Base
- Name: `discord_threads`

**API Rules:**
- List rule: `@request.auth.role = 'admin'`
- View rule: `@request.auth.role = 'admin'`
- Create rule: `@request.auth.role = 'admin'`
- Update rule: `@request.auth.role = 'admin'`
- Delete rule: `@request.auth.role = 'admin'`

**Fields:**
- `thread_id` - Text (required, unique) → max: 30
- `correlation_id` - Text (required) → max: 50
- `initiated_by` - Relation (optional) → users, cascade delete, max 1, display: username
- `participants` - Text (required) → max: 100
- `status` - Select (required) → values: active, archived, closed
- `last_activity` - Date (optional)
- `metadata` - JSON (optional)

### 6. **pending_approvals** (Base Collection)

**Settings:**
- Type: Base
- Name: `pending_approvals`

**API Rules:**
- List rule: `@request.auth.role = 'admin'`
- View rule: `@request.auth.role = 'admin'`
- Create rule: `@request.auth.role = 'admin'`
- Update rule: `@request.auth.role = 'admin'`
- Delete rule: `@request.auth.role = 'admin'`

**Fields:**
- `user` - Relation (required) → users, cascade delete, max 1, display: username, email
- `callsign` - Text (required) → max: 10
- `name` - Text (required) → max: 100
- `email` - Email (required) → max: 200
- `expires_at` - Date (required)
- `admin_notified` - Bool (required)
- `user_notified` - Bool (required)

### 7. **system_logs** (Base Collection)

**Settings:**
- Type: Base
- Name: `system_logs`

**API Rules:**
- List rule: `@request.auth.role = 'admin'`
- View rule: `@request.auth.role = 'admin'`
- Create rule: `@request.auth.role = 'admin'`
- Update rule: `@request.auth.role = 'admin'`
- Delete rule: `@request.auth.role = 'admin'`

**Fields:**
- `level` - Select (required) → values: debug, info, warn, error, critical
- `service` - Text (required) → max: 50
- `event_type` - Text (required) → max: 50
- `message` - Text (required) → max: 500
- `user` - Relation (optional) → users, no cascade, max 1, display: username
- `metadata` - JSON (optional)

### 8. **system_status** (Base Collection)

**Settings:**
- Type: Base
- Name: `system_status`

**API Rules:**
- List rule: `@request.auth.role = 'admin'`
- View rule: `@request.auth.role = 'admin'`
- Create rule: `@request.auth.role = 'admin'`
- Update rule: `@request.auth.role = 'admin'`
- Delete rule: `@request.auth.role = 'admin'`

**Fields:**
- `service` - Text (required, unique) → max: 50
- `status` - Select (required) → values: healthy, degraded, unhealthy, unknown
- `last_check` - Date (required)
- `message` - Text (optional) → max: 200
- `metadata` - JSON (optional)

## Modify Users Collection

You also need to add custom fields to the existing **users** collection:

### **users** (Auth Collection - Modify Existing)

**Add these fields:**
- `role` - Select (required) → values: member, admin
- `approved` - Bool (optional)
- `approved_by` - Relation (optional) → users, no cascade, max 1, display: username
- `approved_at` - Date (optional)
- `pending_deletion` - Bool (optional)
- `deletion_requested_at` - Date (optional)

**Update API Rules:**
- List rule: `@request.auth.role = 'admin'`
- View rule: `@request.auth.id = id || @request.auth.role = 'admin'`
- Create rule: (leave empty for public registration)
- Update rule: `@request.auth.id = id || @request.auth.role = 'admin'`
- Delete rule: `@request.auth.role = 'admin'`

## 🎯 Quick Tips

1. **Order matters**: Create users field modifications first, then other collections
2. **Field types**: Pay attention to field types (Text vs Email vs Select vs Bool vs JSON)
3. **Relations**: When creating relation fields, make sure target collections exist first
4. **Validation**: Use the provided min/max values and patterns for proper validation
5. **Rules**: Copy the API rules exactly as shown for proper security

## ✅ Verification

After creating all collections, restart your RARSMS services:
```bash
docker compose restart
```

Check the logs to ensure services can now connect to all required collections:
```bash
docker compose logs
```

You should no longer see "404 collection not found" errors.