from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    pg_host: str
    pg_port: str
    pg_user: str
    pg_password: str
    pg_db: str
    secret_key: str
    jwt_secret_key: str
    twillio_sendgrid_api_key: str
    registered_from_mail: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_sender: str
    twilio_sms_sender: str
    db_port: str
    # pg_database_url: str
    pricing_webhook_url: str
    @property
    def database_url(self):
        return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_db}"

    class Config:
        env_file = ".env"
        extra = "allow"  # This allows extra environment variables


settings = Settings()