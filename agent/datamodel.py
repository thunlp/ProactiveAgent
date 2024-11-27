from pydantic import BaseModel,Field
from typing import Literal

class Position(BaseModel):
    coord_y: float = Field(ge=0,lt=1)
    coord_x: float = Field(ge=0,lt=1)

class Click(BaseModel):
    pos: Position = Field(description="Position to click")

class DualPoint(BaseModel):
    start: Position = Field(description="Starting position")
    end: Position = Field(description="Ending position")
    duration: float = Field(gt=0,lt=3)

class Press(BaseModel):
    button: Literal["back","home","enter"] = Field(description="Functional button to press")

class Type(BaseModel):
    text: str = Field(description="Put the text you want to type in here")

class Stop(BaseModel):
    state: Literal["complete","impossible"]
    

if __name__ == "__main__":
    import json
    from pydantic import TypeAdapter
    print(json.dumps(TypeAdapter(list[Click|DualPoint|Press|Type|Stop]).json_schema()))