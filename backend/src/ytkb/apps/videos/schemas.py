from pydantic import BaseModel


class CreateChannelData(BaseModel):
    name: str
    url: str
    handle: str