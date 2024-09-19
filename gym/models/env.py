from pydantic import BaseModel, Field

class Operation(BaseModel):
    name: str = Field(
        description="Name of the operation. In Python style.")
    arguments: list[str] = Field(
        description="List all arguments that possible for the operation. In Python style.")
    doc: str = Field(
        description="Detailed description of the operation. Introduce the arguments and the expected result of the operation.")
    
    def __str__(self) -> str:
        return self.model_dump_json()
        s = f"{self.name}("
        s += ', '.join(self.arguments)
        s += f") - {self.description}"
        
        return s
    
    
class EntityUpdate(BaseModel):
    name: str = Field(
        description="Name of the object, be concise of its modal and version.")
    description: str = Field(
        description="Updated Detailed desciption of the object, include model name Like `VsCode 1.92.0`,`Xiaomi Smart Door Bell 3`, `Microsoft Edge 127.0.2651.86`. Be as concise as you can.")
    status: str = Field(
        description="Updated Object's status that should pay attention to.")
    properties: list[str] = Field(
        description="Updated Describe the object's properties one by one.")
    
    new_action: str = Field(
        description="Describe what operation is applied to the entity and how entity status changed."
    )
    
class EntityStatus(BaseModel):
    name: str = Field(
        description="Name of the object, be concise of its modal and version.")
    description: str = Field(
        description="Detailed desciption of the object, include model name Like `VsCode 1.92.0`,`Xiaomi Smart Door Bell 3`, `Microsoft Edge 127.0.2651.86`. Be as concise as you can.")
    status: str = Field(
        description="Object's status that should pay attention to.")
    properties: list[str] = Field(
        description="Describe the object's properties one by one.")
    available_ops: list[Operation] = Field(
        description="What's the available operations that can be applied to the object.")
    past_actions: list[str] = Field(description="History actions that happend on this entity.")
    def update(self, s_up: EntityUpdate):
        if s_up.name != self.name:
            raise KeyError("Mismatch entity name!")
        self.description = s_up.description
        self.status = s_up.status
        self.properties = s_up.properties
        self.past_actions.append(s_up.new_action)
        
        s = f"Name: {self.name}\n"
        s += f"{self.description}\n"
        s += f"Status: {self.status}\n"
        s += f"Last Action: {self.past_actions[-1]}"
        return s
        
    def __str__(self):
        s = f"Name: {self.name}\n"
        s += f"{self.description}\n"
        s += f"Status: {self.status}\n"
        
        s += "Properties:\n  " 
        if len(self.properties) > 0:
            s += '\n  '.join(self.properties) + "\n"
        else:
            s += "No Properties.\n"
        
        
        s += f"Available Operations:\n  " 
        if len(self.available_ops) > 0:
            s += '\n  '.join([str(op) for op in self.available_ops]) + "\n"
        else:
            s += "No Operations.\n"
            
        s += "Past Actions:\n  "
        if len(self.past_actions) > 0:
            s += '\n  '.join(self.past_actions)
        else:
            s += "No history."
        return s
        

class EnvironmentSetting(BaseModel):

    overview: str = Field(description="A overview of this environment")
    time: str = Field(
        description="Date Time Setting for the environment. Add some randomness. Format: M-D H:M:S")

    agent_ops: list[Operation] = Field(description="List all operations that can be applied to the agent. Should be detailed and clear. In Python style.")
    
    entities: list[EntityStatus] = Field(
        description="List all objects in current environemnt. Like physical objects or digital software.")
    
    def __str__(self):
        s = f"# Environment Overview\n{self.overview}\n"
        s += f"Time: {self.time}\n"
        s += "# Agent Operations\n"
        for op in self.agent_ops:
            s += f"{op}\n"
        s += "# Entities in the Environment"
        for e in self.entities:
            s += f"\n{e}\n"
        return s

class IntroEnv(BaseModel):
    """Introduce the environment setting and response the query."""
    query_response: str = Field(
        description="Detailed and specific response to the latest query.")
    updated_entities: list[EntityStatus] = Field(
        description="According your response, update the description of related entities. Keep the same entity name. Use a different name if you want to add new entities. Make sure the updated description is clear and integrity.")
    
        

class NewEvent(BaseModel):                
    event: str = Field(description="Detailed description of the event. Be specific and clear.")
    deltatime: int = Field(description="Estimate how many seconds passed for this event to finish. Add some randomness.")
    updated_entities: list[EntityUpdate] = Field(description="Update the entities based on the event.")
class Events(BaseModel):
    thoughts: str = Field(description="Your thoughts on the generated events.")
    events: list[NewEvent] = Field(description="List of events that happened in the environment. Be specific and clear. The event's format or granularity should be similar to the given examples.")