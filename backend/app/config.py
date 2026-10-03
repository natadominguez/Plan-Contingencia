from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    pay_to_address: str = ""
    x402_facilitator_url: str = "https://x402-facilitator.molandak.org"
    monad_network: str = "eip155:10143"
    monad_usdc_address: str = "0x534b2f3A21130d7a60830c2Df862319e593943A3"

    monad_rpc_url: str = "https://testnet-rpc.monad.xyz"
    attester_private_key: str = ""
    plan_registry_address: str = ""

    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    monitor_interval_seconds: int = 60


settings = Settings()
