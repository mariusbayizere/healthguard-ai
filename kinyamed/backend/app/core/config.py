from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Security
    SECRET_KEY: str

    # Environment
    ENVIRONMENT: str

    # SMS
    SMS_API_KEY: str
    SMS_USERNAME: str = "sandbox"

    # App
    APP_NAME: str = "KinyaMed"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PATIENTS: str = "kinyamed_patients"
    KAFKA_TOPIC_ALERTS: str = "kinyamed_alerts"

    # ML Model
    MODEL_NAME: str = "Davlan/afro-xlmr-mini"
    MODEL_MAX_LENGTH: int = 512
    MODEL_CONFIDENCE_THRESHOLD: float = 0.75

    class Config:
        env_file = ".env"

settings = Settings()
