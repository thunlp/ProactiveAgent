
from pydantic import BaseModel, Field


class UserInfo(BaseModel):
    """Basic User Information. As detail as you can."""
    name: str
    age: int
    job: str
    education: str = Field(
        description="Highest education level. Include school name and major.")

    characteristics: list[str] = Field(
        description="Detailed description, like hobbies, habits, etc.")
    identities: list[str] = Field(
        description="List all identities that user may have.")
    
    def __str__(self):
        s = f"Name: {self.name}\n"
        s += f"Age: {self.age}\n"
        s += f"Job: {self.job}\n"
        s += f"Education: {self.education}\n"
        s += "Characteristics:\n  " + '\n  '.join(self.characteristics) + "\n"
        s += "Identities:\n  " + '\n  '.join(self.identities) + "\n"
        return s


class Activity(BaseModel):
    is_finished: bool = Field(description="Whether you have achieve your goal or not.",default=False)
    act: str = Field(description="The next one action you are going to take and why you take the action. Be specific but do not give predictive actions.")
    
class Judge(BaseModel):
    thought: str = Field(description="Your thought on the agent's proposal based on current events and what you are doing.")
    is_accepted: bool = Field(description="Whether you accept the agent's proposal or not.")