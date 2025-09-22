# Security Guidelines

## Configuration Security

### ⚠️ Never Commit Credentials

The following files contain sensitive information and should **NEVER** be committed to version control:

- `config.yaml` - Contains APRS passcodes and Discord bot tokens
- `.env` files - Environment variables with credentials
- `callsigns.txt` - May contain personal callsign information

### ✅ Safe Configuration Practices

1. **Use Example Files**: Copy `config.example.yaml` to `config.yaml` and fill in your values
2. **Environment Variables**: Use environment variables for production deployments
3. **Local Overrides**: Create `config.local.yaml` for development-specific settings
4. **Docker Secrets**: Use Docker secrets or external secret management in production

### 🔐 Credential Sources

#### APRS Passcode
- Calculate your APRS-IS passcode at: https://apps.magicbug.co.uk/passcode/
- Never share your passcode - it's unique to your callsign

#### Discord Bot Token
- Obtain from Discord Developer Portal: https://discord.com/developers/applications
- Treat bot tokens like passwords - regenerate if compromised

#### Channel and Guild IDs
- These are not secret, but specific to your Discord server setup
- Get them by enabling Developer Mode in Discord

### 🛡️ Additional Security

- **Firewall**: Restrict APRS-IS connections to known ports (14580)
- **Access Control**: Use `authorized_callsigns` to limit who can send messages
- **Monitoring**: Enable logging to track message activity
- **Updates**: Keep dependencies updated for security patches

### 📋 Security Checklist

- [ ] `config.yaml` is in `.gitignore`
- [ ] No credentials in commit history
- [ ] Bot token has minimal required permissions
- [ ] APRS passcode is kept private
- [ ] Authorized callsigns list is configured
- [ ] Logs are monitored for unauthorized access

## Reporting Security Issues

If you discover a security vulnerability, please:

1. **Do not** open a public issue
2. Email the maintainer privately
3. Include steps to reproduce the issue
4. Allow time for a patch before public disclosure

## Regular Security Maintenance

- Rotate Discord bot tokens annually
- Review authorized callsigns quarterly
- Monitor logs for suspicious activity
- Update dependencies monthly
- Review access permissions semi-annually