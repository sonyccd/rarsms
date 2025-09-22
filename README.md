# RARSMS Communication Bridge

A universal communication bridge that seamlessly connects amateur radio (APRS) with modern messaging platforms like Discord, enabling bidirectional message routing with intelligent protocol adaptation.

## 🌟 Features

### **Universal Message Interchange**
- **Protocol Abstraction**: Send one message to multiple protocols automatically
- **Smart Adaptation**: Messages automatically fit each protocol's capabilities and limits
- **Content Prioritization**: Critical information preserved when space is limited
- **Bidirectional Communication**: Messages flow seamlessly in both directions

### **Supported Protocols**
- **📡 APRS-IS**: Amateur radio packet network with position and messaging
- **💬 Discord**: Rich embeds, threading, and webhook integration
- **📁 File Logging**: Structured logging with rotation
- **🔧 Extensible**: Easy to add new protocols

### **Intelligent Message Routing**
- **RARSMS Prefix Filtering**: Only route APRS messages intended for the system
- **Geographic Filtering**: Location-based APRS packet filtering
- **Callsign Authorization**: Whitelist-based access control
- **Configurable Rules**: Custom routing between any protocols

### **Real-World Examples**

#### **APRS → Discord**
```
W4ABC>APRS,TCPIP*::RARSMS   :Emergency at I-40 mile marker 123
```
→ Discord embed with location map, emergency icon, and formatted message

#### **Discord → APRS**
```
@user: RARSMS Anyone monitoring 146.52?
```
→ APRS: `USER:Anyone monitoring 146.52?`

#### **Universal Message**
Create once, deliver everywhere:
```python
emergency_msg = create_emergency_message(
    "aprs_main", "W4ABC",
    "Vehicle accident, need assistance",
    35.7500, -78.7000
)
# Automatically adapts to APRS (67 chars), Discord (rich embed)
```

## 🚀 Quick Start

### 1. **Basic Setup**
```bash
git clone <repository>
cd rarsms
cp config.example.yaml config.yaml
```

### 2. **Configure Credentials**
Edit `config.yaml` with your credentials:
```yaml
# APRS Configuration (for amateur radio)
aprs_callsign: "YOUR-CALL"
aprs_passcode: "12345"

# Discord Configuration (for bidirectional communication)
discord_bot_token: "your_bot_token"
discord_channel_id: "your_channel_id"
discord_guild_id: "your_guild_id"  # optional

# Message filtering
message_prefix: "RARSMS"
require_prefix: true
block_position_updates: true
```

**⚠️ Important**: Never commit `config.yaml` to version control! It contains sensitive credentials.

### 3. **Configure Authorized Callsigns**
Edit `callsigns.txt`:
```
# One callsign per line (base callsign only)
W4ABC
KJ4XYZ
N4DEF
```

### 4. **Launch the Bridge**
```bash
docker-compose up -d
```

### 5. **Monitor Status**
```bash
# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

## 📡 APRS Message Filtering

The bridge implements smart filtering to reduce noise and ensure only intended messages are routed:

### **Message Routing Rules**
Only messages from **authorized callsigns** that meet **one of these criteria**:

1. **Addressed to RARSMS**: `:RARSMS   :Hello from the field!`
2. **Start with RARSMS**: `:CQ      :RARSMS Anyone on frequency?`

### **Examples**

#### **✅ ROUTED Messages:**
```
W4ABC>APRS,TCPIP*::RARSMS   :Meeting tonight at 7 PM
KJ4XYZ>APRS,TCPIP*::CQ      :RARSMS Weather update needed
N4DEF>APRS,TCPIP*::DISCORD :RARSMS: Emergency at grid FM15
```

#### **❌ BLOCKED Messages:**
```
W4ABC>APRS,TCPIP*::CQ      :Regular APRS chat
KJ4XYZ>APRS,TCPIP*::W4XYZ  :Direct message without prefix
```

#### **📍 ALWAYS ROUTED:**
- Position packets from authorized callsigns (regardless of content)

## 🤖 Discord Bot Setup

To enable bidirectional communication, you'll need to create a Discord bot:

### 1. **Create Discord Application**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name (e.g., "RARSMS Bridge")
3. Go to the "Bot" section and click "Add Bot"
4. Copy the bot token (keep this secret!)

### 2. **Configure Bot Permissions**
In the "Bot" section, enable these privileged intents:
- ✅ Message Content Intent
- ✅ Server Members Intent (optional)

### 3. **Invite Bot to Server**
1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ View Channels
   - ✅ Read Message History
   - ✅ Add Reactions
4. Use the generated URL to invite the bot to your server

### 4. **Get Channel ID**
1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click on your channel → Copy ID
3. Use this as `discord_channel_id` in your config

## 🔧 Configuration

### **Configuration File (`config.yaml`)**

Copy `config.example.yaml` to `config.yaml` and configure the following:

#### **Required APRS Settings:**
- `aprs_callsign`: Your amateur radio callsign
- `aprs_passcode`: APRS-IS passcode ([calculate here](https://apps.magicbug.co.uk/passcode/))
- `aprs_server`: APRS-IS server (default: "rotate.aprs2.net")
- `aprs_port`: APRS-IS port (default: 14580)

#### **Required Discord Settings:**
- `discord_bot_token`: Discord bot token from [Discord Developer Portal](https://discord.com/developers/applications)
- `discord_channel_id`: Discord channel ID for bidirectional communication
- `discord_guild_id`: (Optional) Discord server ID for faster startup

#### **Message Filtering:**
- `message_prefix`: Custom prefix (default: "RARSMS")
- `require_prefix`: Enable/disable prefix requirement (default: true)
- `block_position_updates`: Block noisy position updates (default: true)

#### **Geographic Filtering:**
- `filter_lat`: Latitude for APRS packet filtering
- `filter_lon`: Longitude for APRS packet filtering
- `filter_distance`: Filter radius in kilometers

### **Environment Variable Override**

You can also use environment variables to override config.yaml values (useful for Docker):
```yaml
protocols:
  aprs_emergency:
    type: "aprs"
    aprs_callsign: "EMERGENCY-1"
    message_prefix: "EMERGENCY"

  discord_alerts:
    type: "discord"
    discord_webhook_url: "https://discord.com/api/webhooks/..."
    discord_bot_token: "bot_token"
```

#### **Custom Routing Rules**:
```yaml
routing:
  emergency_alerts:
    source_protocols: ["aprs_main"]
    target_protocols: ["discord_alerts", "email_emergency"]
    message_types: ["emergency"]
    bidirectional: false

  position_sharing:
    source_protocols: ["aprs_main"]
    target_protocols: ["discord_main"]
    message_types: ["position"]
    source_filter: "^(W4|K4|N4).*"  # Only specific call areas
```

## 🔄 Message Flow Examples

### **Cross-Protocol Messaging**

#### **APRS → Discord (Position)**
```
W4ABC-9>APRS,TCPIP*:!3547.12N/07838.45W>Mobile station
```
→ Discord embed with:
- 📍 Interactive map link
- 🚗 Station status
- ⏰ Timestamp
- 📡 Technical details

#### **APRS → Discord (Message)**
```
KJ4XYZ>APRS,TCPIP*::RARSMS   :Anyone monitoring 146.52?
```
→ Discord: `[APRS] KJ4XYZ: Anyone monitoring 146.52?`

#### **Discord → APRS (Bot Mode Only)**
```
Reply to APRS message: APRS W4ABC Weather is clearing up, going mobile
```
→ APRS: `USERNAME:Weather is clearing up, going mobile`

## 🔄 Discord Bot Reply System

### **How to Reply to APRS Messages**

When using bot mode, RARSMS tracks APRS messages in Discord and allows replies:

1. **APRS message appears** in Discord with reply instructions
2. **Use Discord's reply function** (right-click → Reply)
3. **Format your reply**: `APRS <CALLSIGN> <your message>`
4. **Bot validates** the callsign matches the original sender
5. **Message routes back** to APRS with confirmation reaction

### **Reply Format Examples**

#### **✅ Valid Replies:**
```
APRS W4ABC Yes, I'm monitoring 146.52
APRS KJ4XYZ-9 Thanks for the weather update
APRS N4DEF Roger, see you at the meeting
```

#### **❌ Invalid Replies:**
```
W4ABC Yes (missing "APRS" prefix)
APRS WRONG-CALL Message (wrong callsign)
Just replying normally (not using reply function)
```

### **Bot Features**
- **Message Tracking**: Remembers last 100 APRS messages for replies
- **Callsign Validation**: Ensures replies go to correct station
- **Visual Feedback**: 📡 for success, ❌ for errors
- **Rich Formatting**: APRS messages shown with maps and metadata

### **Universal Message Adaptation**

#### **Rich Emergency Message:**
Original (multiple content blocks):
- 🚨 Emergency text (CRITICAL priority)
- 📍 GPS coordinates (HIGH priority)
- 📋 Additional details (MEDIUM priority)
- 🏷️ Metadata tags (LOW priority)

#### **Automatic Protocol Adaptation:**

**APRS (67 char limit):**
```
🚨 Emergency text GPS:35.7796,-78.6382 Details...
```

**Discord (2000 char limit):**
```
🚨 **EMERGENCY**
Emergency text

📍 **Location:** [35.7796, -78.6382](https://maps.google.com/?q=35.7796,-78.6382)
📋 Additional details
🏷️ Metadata: event_type=emergency, priority=high
```


## 🛠️ Docker Commands

```bash
# Start the bridge
docker-compose up -d

# View logs in real-time
docker-compose logs -f

# Stop the bridge
docker-compose down

# Rebuild after changes
docker-compose up -d --build

# Check status
docker-compose ps

# Restart specific service
docker-compose restart rarsms
```

## 📊 Monitoring & Troubleshooting

### **Log Messages**

#### **Successful Startup:**
```
✅ SUCCESSFULLY CONNECTED: 2 protocol(s)
🟢 aprs_main
🟢 discord_main

🚀 BRIDGING MODE ACTIVE
→ Messages will be routed between all connected protocols
→ APRS ↔ Discord bridging enabled
→ RARSMS prefix filtering active for APRS messages
```

#### **Configuration Issues:**
```
⚠ APRS protocol not configured - missing: APRS_CALLSIGN
→ APRS will not be available for message routing

⚠ Discord protocol not configured - missing: DISCORD_WEBHOOK_URL
→ Set DISCORD_WEBHOOK_URL to enable Discord integration
```

### **Common Issues**

| Issue | Cause | Solution |
|-------|-------|----------|
| No messages routed | Missing RARSMS prefix | Check message format: `:RARSMS :text` |
| APRS login failed | Wrong callsign/passcode | Verify credentials and passcode calculation |
| Discord not working | Invalid webhook URL | Check webhook URL format and permissions |
| Messages filtered | Callsign not authorized | Add callsign to `callsigns.txt` |

### **Debug Commands**
```bash
# Check message filtering
docker-compose logs -f | grep "Blocking message"

# Monitor protocol connections
docker-compose logs -f | grep "protocol.*connected"

# View routing statistics
docker-compose logs -f | grep "Statistics"
```

## 🏗️ Architecture

### **Protocol Abstraction Layer**
- **BaseProtocol**: Common interface for all communication protocols
- **UniversalMessage**: Standard message format with intelligent adaptation
- **MessageAdapter**: Automatic protocol-specific formatting and truncation
- **ProtocolManager**: Handles routing, authentication, and error recovery

### **Message Processing Pipeline**
1. **Receive**: Protocol-specific message parsing
2. **Convert**: Transform to universal message format
3. **Route**: Apply filtering and routing rules
4. **Adapt**: Protocol-specific formatting and truncation
5. **Send**: Deliver via target protocol

### **Extensibility**
Adding new protocols requires implementing the `BaseProtocol` interface:
```python
class NewProtocol(BaseProtocol):
    def get_capabilities(self) -> ProtocolCapabilities
    async def connect(self) -> bool
    async def send_message(self, message: Message) -> bool
    def parse_incoming_message(self, raw_data) -> Optional[Message]
```

## 🔐 Security Features

- **Callsign Whitelist**: Only authorized amateur radio operators
- **Prefix Filtering**: Prevents accidental message routing
- **Input Validation**: Sanitizes all incoming messages
- **Non-Root Container**: Runs with minimal privileges
- **Environment Variables**: Credentials never stored in code

## 📚 Use Cases

### **Emergency Communications**
- Route emergency APRS messages to multiple platforms instantly
- Automatic position sharing with interactive maps
- Cross-platform coordination during events

### **Club Communications**
- Bridge club meetings between radio and digital platforms
- Share announcements across multiple channels
- Archive conversations for later reference

### **Technical Coordination**
- Coordinate repeater maintenance across platforms
- Share technical information between operators
- Real-time status updates during testing

## 🤝 Contributing

1. **Protocol Development**: Add support for new messaging platforms
2. **Message Adapters**: Improve protocol-specific formatting
3. **Filter Rules**: Enhance message routing and filtering
4. **Documentation**: Improve setup guides and examples

## 📄 License

GPL 3.0 License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **APRS Information**: [aprs.org](http://aprs.org)
- **APRS Passcode Calculator**: [apps.magicbug.co.uk/passcode](https://apps.magicbug.co.uk/passcode/)
- **Discord Webhooks**: [Discord Developer Documentation](https://discord.com/developers/docs/resources/webhook)
- **Amateur Radio**: [arrl.org](http://arrl.org)

---

**Note**: This project is designed for licensed amateur radio operators. Please ensure compliance with your local amateur radio regulations when using APRS features.