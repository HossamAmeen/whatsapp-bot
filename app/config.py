from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    whatsapp_token: str
    phone_number_id: str
    verify_token: str
    app_secret: str = ""
    graph_version: str = "v21.0"


settings = Settings()
