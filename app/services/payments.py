from typing import Dict, Optional
import httpx
from decimal import Decimal
from app.config import settings


class PaystackService:
    def __init__(self):
        self.api_url = settings.PAYSTACK_API_URL
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def _check_api_key(self):
        """Check if API key is configured"""
        if not self.secret_key:
            raise ValueError("Paystack API key not configured. Please set PAYSTACK_SECRET_KEY in .env")
    
    async def initialize_transaction(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        metadata: Dict,
        channels: Optional[list] = None
    ) -> Dict:
        """
        Initialize a payment transaction
        
        Args:
            email: Customer email
            amount: Amount in kobo (multiply Naira by 100)
            reference: Unique transaction reference
            metadata: Additional data (booking_id, event_id, etc.)
            channels: Payment channels ['card', 'bank', 'ussd', 'mobile_money']
        
        Returns:
            {
                'authorization_url': 'https://checkout.paystack.com/...',
                'access_code': 'xxx',
                'reference': 'xxx'
            }
        """
        if channels is None:
            channels = ['card', 'bank', 'ussd', 'mobile_money']
        
        payload = {
            "email": email,
            "amount": int(amount * 100),  # Convert to kobo
            "reference": reference,
            "channels": channels,
            "metadata": metadata,
            "callback_url": f"{settings.WEBHOOK_BASE_URL}/webhooks/paystack/callback"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/transaction/initialize",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result['status']:
                return result['data']
            else:
                raise Exception(f"Paystack error: {result.get('message')}")
    
    async def verify_transaction(self, reference: str) -> Dict:
        """
        Verify a transaction status
        
        Returns:
            {
                'status': 'success',
                'amount': 3050000,  # in kobo
                'reference': 'xxx',
                'paid_at': '2026-02-15T10:30:00.000Z',
                'channel': 'card',
                'customer': {...}
            }
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/transaction/verify/{reference}",
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result['status']:
                return result['data']
            else:
                raise Exception(f"Verification failed: {result.get('message')}")
    
    async def initiate_refund(
        self,
        transaction_reference: str,
        amount: Optional[Decimal] = None,
        reason: str = "Customer request"
    ) -> Dict:
        """
        Initiate a refund
        
        Args:
            transaction_reference: Original transaction reference
            amount: Amount to refund in kobo (None = full refund)
            reason: Refund reason
        """
        payload = {
            "transaction": transaction_reference,
            "merchant_note": reason
        }
        
        if amount:
            payload["amount"] = int(amount * 100)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/refund",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result['status']:
                return result['data']
            else:
                raise Exception(f"Refund failed: {result.get('message')}")
    
    async def get_banks(self, country: str = "nigeria") -> list:
        """Get list of banks for bank transfer"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/bank",
                params={"country": country},
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            if result['status']:
                return result['data']
            else:
                return []


# Singleton instance
paystack_service = PaystackService()
