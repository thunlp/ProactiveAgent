import asyncio
import os
import json

from gym.models.user import UserInfo, Activity, Judge
from .base import BasicComponet, sinkChannels
from codelinker.models import SEvent

SYSTEM = """<Role>
You are tasked with simulating a user within a system. The content labeled `Source: user` reflects your past actions and decisions.
</Role>

<Task>
Generate human-like activities with distinct characteristics and identities. You will receive events and observations from the environment; analyze these closely to decide your actions.
</Task>

<Rules>
- Respond like a real user; don’t be overly predictable.
- Refer to # User Info to understand your identity.
- Critically evaluate the received information, as it may not always be accurate.
- Stay aware of environmental changes, which can occur at any time.
</Rules>"""


class UserAgent(BasicComponet):
    def __init__(self, goal: str, theme: str, adapt_times: int = 2, action_times: int = 7, *args, **kwargs):
        super().__init__("User")
        self.goal = goal
        self.theme = theme
        self.info: UserInfo = None
        self.finish = False
        self.adapt_times = adapt_times
        self.action_times = action_times
        self.wait_agent = False
        self.step_lock = asyncio.Lock()

    @property
    def memory(self):
        return [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"# Goal\n{self.goal}\n# User Info\n{self.info}"}
        ]

    async def setup(self):
        # create characteristics and identities
        await self.update_info()

        # init listen
        self.listen(sinkChannels.env.response, max_emit_time=self.adapt_times)(
            self.adapt_environment)
        self.listen(sinkChannels.events, max_emit_time=self.action_times)(
            self.step)
        self.listen(sinkChannels.agent.proactive)(self.judge)

    async def update_info(self, load: bool = False):
        if load:
            hist = self.gather(sinkChannels.env.all)
        else:
            hist = []

        self.info = await self.cl.exec(
            prompt=f"Update your user info according to the observation.\n# Theme: {self.theme}",
            return_type=UserInfo,
            request_name="update_info",
            messages=self.memory + hist
        )
        self.logger.debug(f"User info updated.\n{self.info}")

    def set_goal(self, goal: str):
        self.goal = goal
        # TODO Update the goal to the user thread

    async def adapt_environment(self):
        # adjust the user info and memory for the environment
        await self.update_info()
        # further question
        hist = self.gather(
            tags=[sinkChannels.env.response])

        question = await self.cl.exec(
            prompt="Now give your informative query if you need more specific infomation about the environment settings. Ask about entities in the environment to help refine the environment, rather than things to finish your goal. You can have multiple query at once. ",
            return_type=str,
            messages=self.memory + hist
        )
        self.add(tags=sinkChannels.env.intro, content=question +
                 "\nPlease answer the question one by one.",)

    async def step(self):
        # random wait to simulate user's action
        await asyncio.sleep(1)
        if self.step_lock.locked():
            self.logger.warning("User step is locked.")
            return

        async with self.step_lock:
            await self.wait(sinkChannels.agent.proactive)
            await asyncio.sleep(1)
            if self.wait_agent:
                await self.wait([sinkChannels.activity])

            async with self.get_tag_lock(sinkChannels.activity):
                hist = self.gather(tags=[sinkChannels.activity, sinkChannels.env.status,
                                   sinkChannels.events, sinkChannels.agent.proactive])

                res = await self.cl.exec(
                    prompt="Now describe what's your next action to achieve the goal based on the environmental observation.",
                    return_type=Activity,
                    request_name="generate_activities",
                    messages=self.memory + hist
                )
                if not res.is_finished:
                    return self.add(tags=sinkChannels.activity, content=res.act)

            if res.is_finished:
                self.finish = True

    async def judge(self) -> bool:

        if os.environ.get("USE_ACTIVERM", "False") == "True":
            from .reward import RewardModel
            rm = RewardModel()
            pred_task = None
            for e in list(self.gather(tags=[sinkChannels.agent.proactive], return_dumper="identity"))[::-1]:
                if isinstance(e["content"], SEvent):
                    if e["content"].source == "ProactiveAgent":
                        d = json.loads(e["content"].content)
                        if "Proactive Task" in d:
                            pred_task = d["Proactive Task"]
                            break
            
            res = await rm.judge(pred_task=pred_task)
            
        else:
            hist = self.gather(tags=[sinkChannels.activity, sinkChannels.env.status,
                            sinkChannels.events, sinkChannels.agent.proactive])
            res = await self.cl.exec(
                prompt="Do you accept the agent's proposal?",
                return_type=Judge,
                request_name="judge",
                messages=self.memory + hist
            )

        self.add(tags=sinkChannels.agent.proactive,
                 content=f"{res.thought}\nIs Accepted: {res.is_accepted}")

        return res.is_accepted
