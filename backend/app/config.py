from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "pipeline"
    postgres_password: str = "pipeline"
    postgres_db: str = "pipeline"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg2",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


settings = Settings()
