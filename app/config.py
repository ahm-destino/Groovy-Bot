from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"

    # WhatsApp
    WHATSAPP_PHONE_NUMBER_ID: str
    WHATSAPP_BUSINESS_ACCOUNT_ID: str
    WHATSAPP_ACCESS_TOKEN: str
    VERIFY_TOKEN: str
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    # App Secret (from Meta Developer Console > App Settings > Basic)
    # Used for X-Hub-Signature-256 webhook verification in production
    WHATSAPP_APP_SECRET: Optional[str] = None

    # AI
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama3-70b-8192"
    # Classification should be deterministic — keep temperature at 0 unless tuning.
    GROQ_TEMPERATURE: float = 0.0
    GROQ_MAX_TOKENS: int = 700
    # Hard ceiling on a single Groq call (seconds) so a slow LLM never hangs a webhook.
    GROQ_TIMEOUT_SECONDS: float = 15.0
    # Transient-failure retries handled by the Groq SDK.
    GROQ_MAX_RETRIES: int = 2
    # Multi-turn memory: how many prior messages to replay to the model, and a
    # safety cap on total characters so the prompt can't grow without bound.
    AI_HISTORY_TURNS: int = 10
    AI_HISTORY_MAX_CHARS: int = 4000

    # Payments (Optional — system degrades gracefully when missing)
    FLUTTERWAVE_SECRET_KEY: Optional[str] = ""
    FLUTTERWAVE_PUBLIC_KEY: Optional[str] = ""
    # Secret hash you set in the Flutterwave dashboard (Settings > Webhooks).
    # Sent back on every webhook in the `verif-hash` header for verification.
    FLUTTERWAVE_VERIF_HASH: Optional[str] = ""
    FLUTTERWAVE_API_URL: str = "https://api.flutterwave.com/v3"

    # Storage (Optional — falls back to placeholder QR URLs when missing)
    CLOUDINARY_CLOUD_NAME: Optional[str] = ""
    CLOUDINARY_API_KEY: Optional[str] = ""
    CLOUDINARY_API_SECRET: Optional[str] = ""

    # App
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    WEBHOOK_BASE_URL: str = "http://localhost:8000"
    SECRET_KEY: str = "change-me-in-production"
    ENABLE_MOCK_EVENTS: bool = False

    class Config:
        # Use .env.test for testing, otherwise .env
        env_file = ".env.test" if os.getenv("TESTING") == "1" else ".env"
        case_sensitive = True


settings = Settings()
