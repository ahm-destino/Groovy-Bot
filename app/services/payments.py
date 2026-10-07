from typing import Dict, Optional
import httpx
from decimal import Decimal
from app.config import settings


class FlutterwaveService:
    """Thin wrapper around the Flutterwave v3 API.

    Amounts are handled in whole Naira (Flutterwave's unit for NGN) — unlike
    Paystack which uses kobo. The public methods keep the same names and return
    shapes the rest of the app already expects, so booking/gift/tier code did not
    need to change when the provider was swapped.
    """

    def __init__(self):
        self.api_url = settings.FLUTTERWAVE_API_URL.rstrip("/")
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    def _check_api_key(self):
        """Raise if the secret key is not configured."""
        if not self.secret_key:
            raise ValueError(
                "Flutterwave secret key not configured. "
                "Please set FLUTTERWAVE_SECRET_KEY in .env"
            )

    async def initialize_transaction(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        metadata: Dict,
        channels: Optional[list] = None
    ) -> Dict:
        """
        Initialize a payment transaction.

        Args:
            email: Customer email
            amount: Amount in Naira (whole units, NOT kobo)
            reference: Unique transaction reference (sent as tx_ref)
            metadata: Additional data (booking_id, event_id, etc.)
            channels: Accepted payment options, e.g. ['card', 'banktransfer', 'ussd']

        Returns:
            {
                'authorization_url': 'https://checkout.flutterwave.com/v3/hosted/pay/...',
                'reference': 'xxx'
            }
        """
        self._check_api_key()
        if channels is None:
            channels = ['card', 'banktransfer', 'ussd']

        payload = {
            "tx_ref": reference,
            "amount": float(amount),  # Naira, whole units
            "currency": "NGN",
            "redirect_url": f"{settings.WEBHOOK_BASE_URL}/webhooks/flutterwave/callback",
            "customer": {"email": email},
            "payment_options": ",".join(channels),
            "meta": metadata,
            "customizations": {"title": "Grooovy Tickets"}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/payments",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "success":
                return {
                    "authorization_url": result["data"]["link"],
                    "reference": reference
                }
            raise Exception(f"Flutterwave error: {result.get('message')}")

    async def verify_transaction(self, reference: str) -> Dict:
        """
        Verify a transaction by its reference (tx_ref).

        Returns a normalized dict the app expects:
            {
                'status': 'success' | 'failed',
                'amount': <Decimal Naira>,
                'tx_id': <int transaction id>,   # needed for refunds
                'currency': 'NGN',
                'raw': {...}
            }
        """
        self._check_api_key()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/transactions/verify_by_reference",
                params={"tx_ref": reference},
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") != "success":
                raise Exception(f"Verification failed: {result.get('message')}")

            data = result["data"]
            normalized_status = "success" if data.get("status") == "successful" else "failed"

            return {
                "status": normalized_status,
                "amount": Decimal(str(data.get("amount", 0))),
                "tx_id": data.get("id"),
                "currency": data.get("currency"),
                "raw": data
            }

    async def initiate_refund(
        self,
        transaction_reference: str,
        amount: Optional[Decimal] = None,
        reason: str = "Customer request"
    ) -> Dict:
        """
        Initiate a refund for a transaction reference.

        Flutterwave refunds are keyed on the numeric transaction id, so we first
        verify the reference to resolve it.

        Args:
            transaction_reference: Original tx_ref
            amount: Amount to refund in Naira (None = full refund)
            reason: Refund reason
        """
        self._check_api_key()
        verified = await self.verify_transaction(transaction_reference)
        tx_id = verified.get("tx_id")
        if not tx_id:
            raise Exception("Refund failed: could not resolve transaction id")

        payload = {"comments": reason}
        if amount is not None:
            payload["amount"] = float(amount)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/transactions/{tx_id}/refund",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "success":
                return result["data"]
            raise Exception(f"Refund failed: {result.get('message')}")


# Singleton instance
flutterwave_service = FlutterwaveService()

# Backwards-compatible alias: existing call sites import `paystack_service`.
# Kept so booking/gift/tier modules keep working without edits.
paystack_service = flutterwave_service
