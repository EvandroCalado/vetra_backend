from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_USER: str = ''
    DB_PASSWORD: str = ''
    DB_HOST: str = ''
    DB_PORT: int = 3306
    DB_NAME: str = ''

    JWT_SECRET_KEY: str = ''
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TOKEN_TIME_MIN: int = 5
    JWT_REFRESH_TOKEN_TIME_DAY: int = 7

    model_config = SettingsConfigDict(
        env_file='.env', extra='ignore', env_file_encoding='utf-8'
    )


settings = Settings()
