#!/usr/bin/env python3

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from .base import BaseNotifier, NotificationData

logger = logging.getLogger(__name__)

class EmailNotifier(BaseNotifier):
    """Email notification provider via SMTP"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.to_addresses = config.get('to_addresses', [])
        self.from_address = config.get('from_address', self.username)
        self.use_tls = config.get('use_tls', True)

    def is_configured(self) -> bool:
        """Check if email configuration is complete"""
        return bool(
            self.smtp_server and
            self.username and
            self.password and
            self.to_addresses
        )

    def send_notification(self, data: NotificationData) -> bool:
        """Send notification via email"""
        try:
            msg = self._create_email(data)

            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)

            if self.use_tls:
                server.starttls()

            server.login(self.username, self.password)

            # Send email to all recipients
            for to_address in self.to_addresses:
                msg['To'] = to_address
                server.send_message(msg)
                del msg['To']  # Remove for next iteration

            server.quit()

            logger.info(f"Sent email notification for {data.callsign} to {len(self.to_addresses)} recipients")
            return True

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False

    def _create_email(self, data: NotificationData) -> MIMEMultipart:
        """Create email message from notification data"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"APRS Update from {data.callsign}"
        msg['From'] = self.from_address

        # Create text content
        text_body = self._create_text_body(data)
        html_body = self._create_html_body(data)

        # Attach parts
        text_part = MIMEText(text_body, 'plain')
        html_part = MIMEText(html_body, 'html')

        msg.attach(text_part)
        msg.attach(html_part)

        return msg

    def _create_text_body(self, data: NotificationData) -> str:
        """Create plain text email body"""
        body = f"APRS Update from {data.callsign}\n"
        body += f"Time: {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        body += f"Type: {data.packet_type.title()}\n\n"

        if data.has_position():
            body += f"Location: {data.get_location_string()}\n\n"

        if data.has_message():
            body += f"Message:\n{data.get_message_text()}\n\n"

        body += f"Raw Packet:\n{data.raw_packet}\n"

        return body

    def _create_html_body(self, data: NotificationData) -> str:
        """Create HTML email body"""
        html = f"""
        <html>
        <head></head>
        <body>
            <h2>📡 APRS Update from {data.callsign}</h2>
            <p><strong>Time:</strong> {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            <p><strong>Type:</strong> {data.packet_type.title()}</p>
        """

        if data.has_position():
            html += f"<p><strong>📍 Location:</strong> {data.get_location_string()}</p>"

        if data.has_message():
            message_text = data.get_message_text().replace('\n', '<br>')
            html += f"<p><strong>💬 Message:</strong><br>{message_text}</p>"

        html += f"""
            <p><strong>Raw Packet:</strong></p>
            <pre style="background-color: #f4f4f4; padding: 10px; border-radius: 5px;">{data.raw_packet}</pre>
        </body>
        </html>
        """

        return html

    def validate_config(self) -> tuple[bool, str]:
        """Validate email configuration"""
        if not self.smtp_server:
            return False, "SMTP server not provided"

        if not self.username:
            return False, "SMTP username not provided"

        if not self.password:
            return False, "SMTP password not provided"

        if not self.to_addresses:
            return False, "No recipient email addresses provided"

        if not isinstance(self.to_addresses, list):
            return False, "Recipient addresses must be a list"

        return True, "Email configuration valid"