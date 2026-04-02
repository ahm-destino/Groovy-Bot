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
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Payments (Optional — system uses bypass mode when missing)
    PAYSTACK_SECRET_KEY: Optional[str] = ""
    PAYSTACK_PUBLIC_KEY: Optional[str] = ""
    PAYSTACK_API_URL: str = "https://api.paystack.co"

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
