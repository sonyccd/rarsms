"""Database client for PocketBase integration."""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import aiohttp
import structlog

from config import DatabaseConfig

logger = structlog.get_logger()


class DatabaseClient:
    """Async client for PocketBase database operations."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.base_url = config.url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self._auth_token: Optional[str] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self):
        """Initialize the HTTP session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("Database client connected", url=self.base_url)

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Database client closed")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to PocketBase API."""
        if not self.session:
            raise RuntimeError("Database client not connected")

        url = urljoin(f"{self.base_url}/api/collections/", endpoint)
        headers = {'Content-Type': 'application/json'}

        # Add auth token if available
        if self._auth_token:
            headers['Authorization'] = f'Bearer {self._auth_token}'

        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            ) as response:
                response_text = await response.text()

                if response.status >= 400:
                    logger.error(
                        "Database request failed",
                        method=method,
                        url=url,
                        status=response.status,
                        response=response_text[:500]
                    )
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=response_text
                    )

                if response_text:
                    return json.loads(response_text)
                return {}

        except aiohttp.ClientError as e:
            logger.error("Database request error", error=str(e), url=url)
            raise

    async def get_pending_messages(self, to_service: str = "discord") -> List[Dict[str, Any]]:
        """Get messages pending delivery to Discord."""
        params = {
            'filter': f"to_service='{to_service}' && status='pending'",
            'sort': '-created',
            'perPage': 50
        }

        try:
            response = await self._make_request('GET', 'messages/records', params=params)
            return response.get('items', [])
        except Exception as e:
            logger.error("Failed to get pending messages", error=str(e))
            return []

    async def update_message_status(
        self,
        message_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update message status and metadata."""
        update_data = {'status': status}

        if status == 'delivered':
            update_data['delivered_at'] = datetime.utcnow().isoformat() + 'Z'

        if metadata:
            update_data['metadata'] = metadata

        try:
            await self._make_request('PATCH', f'messages/records/{message_id}', update_data)
            logger.debug("Message status updated", message_id=message_id, status=status)
            return True
        except Exception as e:
            logger.error("Failed to update message status", message_id=message_id, error=str(e))
            return False

    async def create_message(self, message_data: Dict[str, Any]) -> Optional[str]:
        """Create a new message in the database."""
        try:
            response = await self._make_request('POST', 'messages/records', message_data)
            message_id = response.get('id')
            logger.debug("Message created", message_id=message_id)
            return message_id
        except Exception as e:
            logger.error("Failed to create message", error=str(e))
            return None

    async def get_user_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """Get user information by Discord ID."""
        params = {
            'filter': f"discord_id='{discord_id}'"
        }

        try:
            response = await self._make_request('GET', 'member_profiles/records', params=params)
            items = response.get('items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error("Failed to get user by Discord ID", discord_id=discord_id, error=str(e))
            return None

    async def get_conversation_by_correlation_id(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by correlation ID."""
        params = {
            'filter': f"correlation_id='{correlation_id}'"
        }

        try:
            response = await self._make_request('GET', 'conversations/records', params=params)
            items = response.get('items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error("Failed to get conversation", correlation_id=correlation_id, error=str(e))
            return None

    async def create_or_update_conversation(
        self,
        correlation_id: str,
        user_id: Optional[str],
        subject: str
    ) -> bool:
        """Create or update a conversation record."""
        # Truncate subject
        if len(subject) > 50:
            subject = subject[:47] + "..."

        # Check if conversation exists
        existing = await self.get_conversation_by_correlation_id(correlation_id)

        conversation_data = {
            'correlation_id': correlation_id,
            'services_involved': ['aprs', 'discord'],
            'subject': subject,
            'status': 'active',
            'last_activity': datetime.utcnow().isoformat() + 'Z',
            'message_count': 1
        }

        if user_id:
            conversation_data['initiated_by'] = user_id

        try:
            if existing:
                # Update existing conversation
                conversation_data['message_count'] = existing.get('message_count', 0) + 1
                await self._make_request(
                    'PATCH',
                    f"conversations/records/{existing['id']}",
                    conversation_data
                )
            else:
                # Create new conversation
                await self._make_request('POST', 'conversations/records', conversation_data)

            return True
        except Exception as e:
            logger.error("Failed to create/update conversation", error=str(e))
            return False

    async def create_discord_thread_record(
        self,
        thread_id: str,
        channel_id: str,
        correlation_id: str,
        user_id: Optional[str],
        thread_name: str
    ) -> bool:
        """Create a Discord thread tracking record."""
        thread_data = {
            'thread_id': thread_id,
            'channel_id': channel_id,
            'correlation_id': correlation_id,
            'thread_name': thread_name,
            'active': True,
            'last_message_at': datetime.utcnow().isoformat() + 'Z'
        }

        if user_id:
            thread_data['initiated_by'] = user_id

        try:
            await self._make_request('POST', 'discord_threads/records', thread_data)
            logger.debug("Discord thread record created", thread_id=thread_id)
            return True
        except Exception as e:
            logger.error("Failed to create Discord thread record", error=str(e))
            return False

    async def get_discord_thread_by_id(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get Discord thread record by thread ID."""
        params = {
            'filter': f"thread_id='{thread_id}'"
        }

        try:
            response = await self._make_request('GET', 'discord_threads/records', params=params)
            items = response.get('items', [])
            return items[0] if items else None
        except Exception as e:
            logger.error("Failed to get Discord thread", thread_id=thread_id, error=str(e))
            return None

    async def update_discord_thread_activity(self, thread_id: str) -> bool:
        """Update last activity time for a Discord thread."""
        thread_record = await self.get_discord_thread_by_id(thread_id)
        if not thread_record:
            return False

        update_data = {
            'last_message_at': datetime.utcnow().isoformat() + 'Z'
        }

        try:
            await self._make_request(
                'PATCH',
                f"discord_threads/records/{thread_record['id']}",
                update_data
            )
            return True
        except Exception as e:
            logger.error("Failed to update thread activity", thread_id=thread_id, error=str(e))
            return False

    async def log_event(
        self,
        level: str,
        service: str,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """Log an event to the system logs."""
        log_data = {
            'level': level,
            'service': service,
            'event_type': event_type,
            'message': message
        }

        if metadata:
            log_data['metadata'] = metadata
        if correlation_id:
            log_data['correlation_id'] = correlation_id
        if user_id:
            log_data['user'] = user_id

        try:
            await self._make_request('POST', 'system_logs/records', log_data)
            return True
        except Exception as e:
            logger.error("Failed to log event", error=str(e))
            return False

    async def update_system_status(
        self,
        service: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update system status for the Discord bot service."""
        # Try to get existing record first
        params = {'filter': f"service='{service}'"}

        status_data = {
            'service': service,
            'status': status,
            'last_heartbeat': datetime.utcnow().isoformat() + 'Z'
        }

        if metadata:
            status_data['metadata'] = metadata

        try:
            # Check if record exists
            response = await self._make_request('GET', 'system_status/records', params=params)
            items = response.get('items', [])

            if items:
                # Update existing record
                record_id = items[0]['id']
                await self._make_request('PATCH', f'system_status/records/{record_id}', status_data)
            else:
                # Create new record
                await self._make_request('POST', 'system_status/records', status_data)

            return True
        except Exception as e:
            logger.error("Failed to update system status", service=service, error=str(e))
            return False

    def generate_correlation_id(self) -> str:
        """Generate a unique correlation ID."""
        return f"discord_{int(time.time())}_{uuid.uuid4().hex[:8]}"