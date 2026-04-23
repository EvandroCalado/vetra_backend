from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_USER: str = ''
    DB_PASSWORD: str = ''
    DB_HOST: str = ''
    DB_PORT: int = 3306
    DB_NAME: str = ''

    model_config = SettingsConfigDict(
        env_file='.env', extra='ignore', env_file_encoding='utf-8'
    )


settings = Settings()
