from pydantic import BaseModel


class AppConfig(BaseModel):
    api_url: str = "https://localhost:8000"
    websocket_url: str = "wss://localhost:8000/connector/ws"
    auto_start: bool = False
