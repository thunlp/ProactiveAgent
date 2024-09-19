import json
SYSTEM = '''<Task>
Evaluate the task proposed by the proactive assistant as the user.
</Task>

<Rule>
0. Analyze the current observation to understand your current situation and requirements.
1. If the proposed task is `null` (indicating no task is proposed under the current observation), follow these steps:
   - Accept the `null` task if you believe there is no need for a task.
   - Reject the `null` task if you believe a task is needed.
2. Minimize interruptions from the assistant by only accepting tasks that are valuable.
3. Evaluate the current observation and make a judgment on the proposed task accordingly.
</Rule>

<Format>
You should answer with following JSON format:
{
    "thought": "Give your thoughts first, then provide the judgement of the task.",
    "judgement": "accepted or rejected"
}
</Format>'''

def format_reward_instruction(obs:list[dict],pred_task:str) -> list[dict]:
    inst_dict = {
        "Observations (Time Ascending)": obs,
        "Proposed Task": pred_task,
        "Instruction": "Now give your judgement. You should complete the reasoning process in first person."
    }
    
    return [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":json.dumps(inst_dict,sort_keys=False,ensure_ascii=False,indent=4)}
    ]
