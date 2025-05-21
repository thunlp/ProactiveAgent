from .base import BasicComponet, sinkChannels
import re
import os
import sys
import json
from copy import deepcopy

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


SYSTEM = """<Role> You are a helpful assistant that provides proactive suggestions to the user. </Role> 

<Task> Understand what the user is doing and anticipate their needs based on events. Only propose assistance when you fully understand the user's actions. Use available operations to ensure the task is feasible. Execute the task if the user accepts your proposal. </Task> 

<Format> Respond in the following JSON format: 
{
    "Purpose": "The purpose of the user's last action.", 
    "Thoughts": "Your thoughts on the user's actions.", 
    "Proactive Task": "Describe your proposed task, or set to `null` if no assistance is needed.", 
    "Response": "Inform the user about your assistance if proposing a task." 
}
</Format>

<Rules>
- Ensure the proposed task is relevant to the events. - Focus on the user's current needs and predict helpful tasks.
- Consider the timing of events.
- Only offer proactive assistance when necessary.
- Deduce the user's purpose and whether they need help based on event history.
- Set `Proactive Task` to `null` if the user doesn't need help. 
</Rules>"""

STEP_OBJ = {
    "Instructions": "Now analyze the history events and provide a task if you think the user needs your help.",
}

EXEC = """{
    "Instructions": "Decide what to do next by executing available actions.",
}
<Format>
Respond in the following JSON format:
{
    "Thoughts": "Your thoughts on the situation.",
    "Action": "The action to take next. Set to `null` if no action is needed or if the user rejects your proposal."
}
</Format>"""




class ProactiveAgent(BasicComponet):
    def __init__(self,):
        super().__init__("ProactiveAgent")

    @property
    def memory(self):
        return [{"role": "system", "content": SYSTEM}]

    async def setup(self):
        self.listen(sinkChannels.events)(self.step)
        self.listen(sinkChannels.agent.proactive)(self.exec)

    async def exec(self):
        async with self.get_tag_lock(sinkChannels.agent.proactive):
            self.unlisten(self.step)
            while True:
                async with self.get_tag_lock(sinkChannels.activity):
                    hist = self.gather([sinkChannels.activity, sinkChannels.events,
                                       sinkChannels.agent.proactive, sinkChannels.agent.ops])
                                        
                    res = await self.cl.exec(
                        prompt=EXEC,
                        return_type=str,
                        messages=self.memory + hist
                    )
                    self.logger.warning(res)
                    ret = json.loads(res)

                    if ret.get("Action", None) is None or ret.get("Action") == "null":
                        # restore listening
                        self.listen(sinkChannels.events)(self.step)
                        self.logger.info("Exit Execution.\n" +
                                         ret.get("Thoughts", "None"))
                        return
                    self.add(sinkChannels.activity, content=res)

                await self.wait(sinkChannels.activity)

    def extrat_pred(self, s):
        if '```json' in s:
            s = re.findall(r'```json\n(.*?)\n```', s, re.DOTALL)[0]
        
        ret = json.loads(s)
        if ret.get("Proactive Task",None) is not None and ret.get("Proactive Task") == "null":
            ret["Proactive Task"] = None
        if ret.get("Response",None) is not None and ret.get("Response") == "null":
            ret["Response"] = None
        return ret
        
    
    async def step(self):
        if self.get_tag_lock(sinkChannels.agent.proactive).locked():
            self.logger.debug("Agent is doing proactive task, skip this step.")
            return
        await self.wait(sinkChannels.agent.proactive)

        async with self.get_tag_lock(sinkChannels.agent.proactive):
            async with self.get_tag_lock(sinkChannels.activity):
                hist = []
                obs = []

                for e in self.gather([
                    sinkChannels.events,
                    sinkChannels.agent.proactive,
                    sinkChannels.agent.ops
                ]):
                    if e['role'] == 'assistant':
                        hist.append({"role": "user", "content": json.dumps(obs)})
                        obs = []
                        hist.append(e)
                    else:
                        obs.append(e['content'])
                        
                step_obj = deepcopy(STEP_OBJ)
                step_obj["Observations"] = obs
                
                res = await self.cl.exec(
                    prompt=json.dumps(step_obj),
                    return_type=str,
                    messages=self.memory + hist
                )
                self.logger.warning(res)
                pred = self.extrat_pred(res)
                
                if os.environ.get("USE_ACTIVERM", "False") == "True":
                    from .reward import RewardModel
                    rm = RewardModel()
                    res = await rm.judge(pred.get("Proactive Task", None))
                    
                    retry_times = 3
                    while not res.is_accepted and retry_times > 0:
                        step_obj["Previous Prediction"] = pred
                        step_obj["Status"] = "Rejected"
                        step_obj["User Feedback"] = res.thought
                        step_obj["Instructions"] = f"Your previous prediction is rejected! You must make a different prediction."
                        
                        res = await self.cl.exec(
                            prompt=json.dumps(step_obj),
                            return_type=str,
                            messages=self.memory + hist,
                            completions_kwargs={"temperature": 0.8}
                        )
                        self.logger.warning(res)
                        pred = self.extrat_pred(res)
                        res = await rm.judge(pred.get("Proactive Task", None))
                        retry_times -= 1
                    
                    if not res.is_accepted:
                        self.logger.error("Prediction is rejected! Will Skip this step.")
                        return
                    
                    # save the accepted prediction
                    new_obs = []
                    for ob in obs:
                        loaded_ob = json.loads(ob)
                        new_obs.append({
                            'Time': loaded_ob['Time'],
                            'Event': loaded_ob['Event']
                        })
                    step_obj = deepcopy(STEP_OBJ)
                    step_obj["Observations"] = new_obs
                    data = self.memory + hist + [{"role":"user","content":json.dumps(step_obj)},{"role": "assistant","content": json.dumps(pred)}]
                    self.add(sinkChannels.agent.response, content=json.dumps(data), silent=True)
                    
                self.add(sinkChannels.agent.proactive, content=json.dumps(pred),silent=pred.get("Proactive Task", None) is None)
