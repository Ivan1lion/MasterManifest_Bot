from pydantic import BaseModel

class YooKassaWebhook(BaseModel):
    type: str
    event: str
    object: dict