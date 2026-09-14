from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Konfigurace mcp-server kontejneru - vše přichází z .env (viz .env.example
    v rootu repa, sekce "MCP integrace").
    """

    model_config = SettingsConfigDict(env_prefix="MCP_")

    # Veřejná URL, na které tenhle server běží přes Cloudflare Tunnel
    # (např. https://mcp.oczkowi.eu) - používá se jako OAuth issuer a
    # jako základ pro redirect/login odkazy, musí sedět s tunnel routou.
    public_url: str = "http://localhost:8000"

    # Jediný přihlašovací údaj - tenhle server má jednoho uživatele (Martina).
    # Vygeneruj si silné náhodné heslo, ne něco zapamatovatelného - je to
    # jediná ochrana přístupu k CRM datům přes Claude.
    login_password: str = ""

    # Sdílený tajný token pro volání backendu (/api/mcp/*) - MUSÍ být stejný
    # jako MCP_SERVICE_TOKEN v .env backendu.
    service_token: str = ""

    # Interní URL backendu uvnitř crm-network (ne přes Cloudflare Tunnel).
    backend_url: str = "http://backend:8000"

    # Kam ukládat registrované OAuth klienty a tokeny, ať přežijí restart
    # kontejneru (viz app/oauth_provider.py) - namapováno na named volume.
    data_dir: str = "/app/data"

    port: int = 8000


settings = Settings()
