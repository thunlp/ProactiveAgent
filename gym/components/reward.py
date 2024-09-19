import os
import openai
import json
import tenacity
from typing import Optional
from .base import BasicComponet, sinkChannels
from eval.reward_model_template import format_reward_instruction

from codelinker.models import SEvent
from gym.models.user import Judge

class RewardModel(BasicComponet):
    def __init__(self, ):
        super().__init__("reward_model")

    async def judge(self, pred_task: Optional[str]) -> Judge:
        events = self.gather(tags=[sinkChannels.events], return_dumper="identity")
        
        events = [{
            "time": msg['content'].time,
            "event": msg['content'].content,
            } for msg in events if isinstance(msg['content'],SEvent)]
        
        async for attemp in tenacity.AsyncRetrying(wait=tenacity.wait_fixed(1)):
            with attemp:
                ret = await self.cl.exec(
                    messages=format_reward_instruction(obs=events,pred_task=pred_task),
                    model="activerm",
                    completions_kwargs={"temperature": 0.0 + 0.4 * (attemp.retry_state.attempt_number > 1),}
                )
                res = json.loads(ret)
                res = Judge(thought=res["thought"], is_accepted=res["judgement"]=="accepted")
        self.logger.debug(res.model_dump_json())
        return res  