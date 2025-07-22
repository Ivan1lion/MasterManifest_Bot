from pydantic import BaseSettings

class DBConfig(BaseSettings):
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "manifest_bot"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    @property
    def db_url(self):
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

config = DBConfig()
