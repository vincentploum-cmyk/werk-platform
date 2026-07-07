from pydantic import model_validator
from pydantic_settings import BaseSettings

# Known non-secrets shipped in this repo / .env.example. Refusing to start with one of
# these outside debug mode prevents deployments with forgeable JWTs.
_PLACEHOLDER_SECRET_KEYS = {
    "werk-dev-secret-key-change-in-production",
    "change-this-to-a-random-64-char-string",
}


class Settings(BaseSettings):
    app_name: str = "Werk Platform"
    version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/werk"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Auth
    secret_key: str = "werk-dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    allowed_hosts: list[str] = ["*"]

    # Security
    cors_origins: list[str] = ["*"]
    rate_limit_per_minute: int = 60
    bcrypt_rounds: int = 12
    session_timeout_minutes: int = 480  # 8 hours

    # Secrets (loaded from env/vault — never hardcode in production)
    vault_addr: str = ""
    vault_token: str = ""
    use_vault: bool = False

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Local model (Ollama) — runs on your own machine, no external API or cost.
    # Enable by setting USE_OLLAMA=true and running Ollama with a pulled model.
    use_ollama: bool = False
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1"
    ollama_embed_model: str = "nomic-embed-text"

    # Storage
    artifact_storage_path: str = "/home/team/shared"

    # Execution layer — per-project code workspace + test running.
    # Code execution runs model-generated code in a subprocess; keep it off unless wanted.
    workspace_root: str = "/tmp/werk_workspaces"
    enable_code_execution: bool = False
    code_execution_timeout: int = 30

    # Agent config
    max_agent_concurrency: int = 5
    agent_timeout_seconds: int = 300

    @model_validator(mode="after")
    def _require_real_secret_key(self) -> "Settings":
        if not self.debug and self.secret_key in _PLACEHOLDER_SECRET_KEYS:
            raise RuntimeError(
                "SECRET_KEY is a known placeholder. Generate one (e.g. `openssl rand -hex 32`) "
                "and set it in .env before running with DEBUG=false."
            )
        return self

    class Config:
        env_file = ".env"


settings = Settings()