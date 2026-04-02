from typing import List, Dict, Optional, Any, Callable, Awaitable
import httpx
import asyncio
import time
from functools import wraps
import logging
from app.config import settings
from app.services.locks import outbound_phone_lock

logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
    """
    Retry decorator with exponential backoff for handling transient errors
    including DNS failures, connection errors, and timeouts.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (
                    httpx.ConnectError,
                    httpx.TimeoutException,
                    httpx.NetworkError,
                    OSError,
                    ConnectionError,
                    ConnectionRefusedError,
                    ConnectionResetError
                ) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_retries} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


class WhatsAppService:
    def __init__(self):
        self.api_url = f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        self._send_last_at: Dict[str, float] = {}
        self._min_send_gap_seconds = 0.25

    async def _send_with_order(
        self,
        phone: str,
        send_fn: Callable[[], Awaitable[Dict]]
    ) -> Dict:
        async with outbound_phone_lock(phone):
            last_sent = self._send_last_at.get(phone)
            now = time.monotonic()
            if last_sent is not None:
                wait = self._min_send_gap_seconds - (now - last_sent)
                if wait > 0:
                    await asyncio.sleep(wait)
            result = await send_fn()
            self._send_last_at[phone] = time.monotonic()
            return result
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def send_message(self, phone: str, text: str) -> Dict:
        """Send plain text message"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {"body": text}
        }

        async def _send():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        return await self._send_with_order(phone, _send)
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def send_interactive(
        self,
        phone: str,
        message: str,
        buttons: List[Dict[str, str]]
    ) -> Dict:
        """Send message with interactive buttons (max 3)"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": message},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {
                                "id": btn["id"],
                                "title": btn["title"][:20]  # Max 20 chars
                            }
                        }
                        for btn in buttons[:3]  # Max 3 buttons
                    ]
                }
            }
        }
        
        async def _send():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        return await self._send_with_order(phone, _send)
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def send_image(
        self,
        phone: str,
        image_url: str,
        caption: str = ""
    ) -> Dict:
        """Send image (e.g., QR code ticket)"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "image",
            "image": {
                "link": image_url,
                "caption": caption
            }
        }
        
        async def _send():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        return await self._send_with_order(phone, _send)
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def send_location(
        self,
        phone: str,
        latitude: float,
        longitude: float,
        name: str,
        address: str
    ) -> Dict:
        """Send location pin (for venue)"""
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "location",
            "location": {
                "latitude": str(latitude),
                "longitude": str(longitude),
                "name": name,
                "address": address
            }
        }
        
        async def _send():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        return await self._send_with_order(phone, _send)
    
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def mark_as_read(self, message_id: str) -> Dict:
        """Mark incoming message as read"""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/messages",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def send_list(
        self,
        phone: str,
        message: str,
        button_text: str,
        sections: List[Dict[str, Any]]
    ) -> Dict:
        """Send list message (interactive list)"""
        def _truncate(text: str, limit: int) -> str:
            if not text:
                return ""
            if len(text) <= limit:
                return text
            if limit <= 3:
                return text[:limit]
            return text[:limit - 3] + "..."
        
        # Enforce WhatsApp limits
        safe_sections = []
        for section in sections[:10]:
            rows = []
            for row in section.get("rows", [])[:10]:
                rows.append({
                    "id": str(row.get("id", ""))[:256],
                    "title": _truncate(str(row.get("title", "")), 24),
                    "description": _truncate(str(row.get("description", "")), 72) if row.get("description") else ""
                })
            if rows:
                safe_sections.append({
                    "title": _truncate(str(section.get("title", "Options")), 24),
                    "rows": rows
                })
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": message[:1024]},
                "action": {
                    "button": _truncate(button_text, 20),
                    "sections": safe_sections
                }
            }
        }
        
        async def _send():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

        return await self._send_with_order(phone, _send)


# Singleton instance
whatsapp_service = WhatsAppService()





