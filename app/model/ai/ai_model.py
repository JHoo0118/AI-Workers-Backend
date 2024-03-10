from pydantic import BaseModel
from typing import Dict, List, Union


class ChatModel(BaseModel):
    role: str
    content: Union[str, List[Union[str, Dict]]]
