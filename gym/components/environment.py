import json
from gym.models.env import EnvironmentSetting, EntityStatus, EntityUpdate, IntroEnv, Events
from .base import BasicComponet, sinkChannels
import random

SYSTEM = """<Role>
You are tasked with simulating an environment within a system. The content labeled `Source: environment` reflects your past actions and decisions.
</Role>

<Task>
Generate and refine detailed environment settings. Based on the latest activities, create multiple events to describe changes in the environment.
</Task>

<Rules>
- Ensure the subject of the generated content aligns with the latest activities's source.
- Avoid subjective opinions or emotions; focus on objective changes.
- Ensure events are consistent with historical events labeled `[events]` and include all - changes from the activities.
- Introduce occasional failures or unexpected events for realism.
- Ensure each event is logically connected to the previous one and does not include nonexistent elements.
- Pay close attention to entity operations; if an operation is not allowed or impractical in the real or simulated environment, raise an error and explain the issue.
</Rules>"""


class EnvironmentStateManager(BasicComponet):

    def __init__(self, theme: str, description: str, events_example: list[str], agent_ops: str,entities:str, *args, **kwargs):
        super().__init__("EnvManager")

        self.theme = theme
        self.description = description
        self.setting: EnvironmentSetting = None
        self.events_example = events_example
        self.agent_ops = agent_ops
        self.entities = entities

    @property
    def memory(self):
        return [{"role": "system", "content": SYSTEM}]

    async def setup(self):
        self.logger.info("Initializing Environment Objects...")
        self.setting = await self.cl.exec(
            prompt=json.dumps({
                "Theme": self.theme,
                "Description": self.description,
                "Sample Agent Operations": self.agent_ops,
                "Possible Entities": self.entities,
                "Instructions": "Expand the scene description to create a more detailed environment setting based on the given theme and description. Focus on adding objects related to the theme and elements the user would interact with. Ensure the agent's operations are clear, feasible in the real world, and simple. Always provide basic operations."
            }),
            return_type=EnvironmentSetting,
            request_name="expand_scene_description",
            messages=self.memory
        )
        self.logger.debug(f"Initialized Environment Setting.\n{self.setting}")
        self.add(sinkChannels.agent.ops, content=f"# Assistant Available Operations\n{self.setting.agent_ops}")
        self.update_time(self.setting.time)
        
        self.add(tags=sinkChannels.env.status, content=f"! Initial Environment Settings !\n{self.setting}")
        
        self.listen(sinkChannels.env.intro)(self.intro)
        self.listen(sinkChannels.activity)(self.step)
        

    def update_entity(self, entity: EntityStatus):
        exist = False
        for e in self.setting.entities:
            if e.name == entity.name:
                self.logger.debug(f"Updating Entity: {entity}")
                e.description = entity.description
                e.status = entity.status
                e.properties = entity.properties
                e.available_ops = entity.available_ops
                exist = True
                return e
        if not exist:
            self.setting.entities.append(entity)
            self.logger.debug(f"Adding Entity: {entity}")
            return entity
        raise ValueError("Entity Not Found.")
    
    def update_status(self, eu: EntityUpdate):
        for e in self.setting.entities:
            if e.name == eu.name:
                self.logger.debug(f"Updating Entity: {eu}")
                return e.update(eu)
            
        entity = EntityStatus(name=eu.name,description=eu.name,status=eu.status,properties=eu.properties,past_actions=[eu.new_action],available_ops=[])
        self.setting.entities.append(entity)
        self.logger.debug(f"Adding Entity: {entity}")
        return entity
        # raise ValueError("Entity Not Found")
                
    async def intro(self):
        """Introduce the environment setting to the user."""
        hist = self.gather(sinkChannels.env.all)

        res = await self.cl.exec(
            return_type=IntroEnv,
            request_name="intro_env",
            messages=self.memory + hist
        )

        for e in res.updated_entities:
            self.update_entity(e)

        self.add(
            tags=sinkChannels.env.response,
            content=res.query_response,
        )
        self.logger.info(
            f"Update Entities: {[e.name for e in res.updated_entities]}")

    def update_delta_time(self, delta: int):
        import datetime 
        current_time = datetime.datetime.strptime(self.setting.time, "%m-%d %H:%M:%S")
        delta = datetime.timedelta(seconds=delta)
        new_time = current_time + delta
        self.setting.time = new_time.strftime("%m-%d %H:%M:%S")
        self.update_time(self.setting.time)
    
    async def step(self):
        """Updating environemnt """
        # update time
        async with self.get_tag_lock(sinkChannels.activity):
            hist = self.gather([sinkChannels.env.status,sinkChannels.events,sinkChannels.agent.ops,sinkChannels.agent.actions])

            last_activity = json.loads(self.gather(sinkChannels.activity)[-1]["content"])
                
            source = last_activity["Source"]
            samples = random.sample(self.events_example,k=5)

            if source == "User":
                replaces = [("Agent","User"),("agent","user")]
            elif source == "ProactiveAgent":
                replaces = [("User","Agent"),("user","agent")]
            
            for i in range(len(samples)):
                for r in replaces:
                    samples[i] = samples[i].replace(r[0],r[1])
                    
            res = await self.cl.exec(
                prompt=f"""<Samples>\n{json.dumps(samples)}\n</Samples>\n<Latest Activity>\n<From {source}>{json.dumps(last_activity['Event'])}</Last Activity>\nBased on the latest activity, generate multiple events describing environmental changes. Make sure the events' subject is {source}. Include both meaningful and occasionally meaningless actions, similar to the provided samples. Maintain consistent granularity across all events, and generate as many events as possible.""",
                return_type=Events,
                request_name="refine_events",
                messages=self.memory + hist
            )

            async with self.get_tag_lock(sinkChannels.events):
                for eve in res.events:
                    self.update_delta_time(eve.deltatime)
                    for eu in eve.updated_entities:
                        self.add(
                            tags=sinkChannels.env.status, content=f"Entity Updated.\n{self.update_status(eu=eu)}")
                    self.add(tags=sinkChannels.events, content=eve.event)

    # async def get_agent_ops(self):
    #     async with self.get_tag_lock(sinkChannels.env.status):
    #         if isinstance(self.agent_ops, str):
    #             hist = self.gather(sinkChannels.env.all)
    #             ops = await self.cl.exec(
    #                 return_type=list[Operation],
    #                 prompt="Now you should refine the operations available for the agent. Please make sure each operation is clear. Each argument is described. The expected result is clear. And what's more, please break down each operation into basic and simple ones so that the operation is feasible to construct in real world. \n" + "# Agent Ops Description\n" + self.agent_ops,
    #                 messages=self.memory + [{"role": "user", "content": f"! Initialized Environment Setting !\n{self.setting}"}] + hist
    #             )
    #             self.setting.agent_ops = ops
    #             self.agent_ops = ops
    #             self.add(tags=sinkChannels.agent.ops,
    #                      content=f"Agent Operations Updated.\n{ops}")
            
    #         return self.setting.agent_ops

if __name__ == "__main__":
    import asyncio
