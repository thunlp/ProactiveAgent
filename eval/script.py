import os
import re
import json
import asyncio
from typing import List, Dict
from datetime import datetime

import tenacity 
from tqdm.asyncio import tqdm_asyncio as asyctqdm
from codelinker import CodeLinker,CodeLinkerConfig

cfg = CodeLinkerConfig.from_toml("private.toml")
cfg.request.use_cache = False
cl = CodeLinker(config=cfg)
sem = asyncio.Semaphore(16)

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

STEP = json.dumps({
    "Instructions": "Now analyze the history events and provide a task if you think the user needs your help.",
    "Observation": "[placeholder]"
    })


DIR = "./dataset/test_data"

data_files = os.listdir(DIR)

def extrat_pred(s):
    if '```json' in s:
        s = re.findall(r'```json\n(.*?)\n```', s, re.DOTALL)[0]
    
    ret = json.loads(s)
    if ret.get("Proactive Task",None) is None:
        ret["Proactive Task"] = None
    elif ret.get("Proactive Task") == "null":
        ret["Proactive Task"] = None
            
    if ret.get("Response",None) is not None and ret.get("Response") == "null":
        ret["Response"] = None
    return ret

async def get_response(messages:List[Dict[str,str]], model_name:str) -> Dict[str,str]:
    async for attemp in tenacity.AsyncRetrying(stop=tenacity.stop_after_attempt(5),reraise=True):
        with attemp:
            async with sem:
                res = await cl.exec(
                    model=model_name,
                    messages=messages,
                    completions_kwargs={"temperature":0.0 if attemp.retry_state.attempt_number< 1 else 0.5}
                )    
            result = extrat_pred(res)
            return result

async def get_trace(file_name:str, model_name:str) -> Dict[str,str]:
    """
    Get the agent response based on the history messages.

    Args:
        message (List[Dict[str,str]]): the history information with turns as {system, user, assistant, ..., user(new event)}
        model_name (str): 

    Returns:
        Dict[str,str], the agent response.
    """
    
    file_path = os.path.join(DIR, file_name)
    with open(file_path, 'r') as f:
        event_trace = json.load(f)
        
    messages = [
        {"role": "system", "content": SYSTEM},
    ]
    
    for idx,event in enumerate(event_trace):
        
        print(idx, file_name)
        
        raw_event = event["observation"]
        event_filtered = {"Time": raw_event["time"], "Event": raw_event["event"]}
        
        query_prompt = STEP.replace("[placeholder]", json.dumps(event_filtered))
        
        messages.append({"role": "user", "content": query_prompt})
        
        try:
            result = await get_response(messages, model_name)
        except Exception as e:
            print(e)
            continue
            
        
        event_trace[idx]["agent_response"] = [] if result["Proactive Task"] == None else [result["Proactive Task"]]
        event_trace[idx]["other_infomation"] = {k:v for k,v in result.items() if k != "Proactive Task"}
        
        messages.append({"role": "assistant", "content": json.dumps(result)})
        messages[-2]["content"] = json.dumps(event_filtered)

    return event_trace, file_name


async def main(model_name:str):
    files = [file for file in data_files if not (file.startswith('turns') or file.startswith('splits.json'))]
    
    results = await asyctqdm.gather(*[get_trace(file, model_name) for file in files])
    
    if not os.path.exists(f'./eval/traces_new/{model_name}'):
        os.makedirs(f'./eval/traces_new/{model_name}')
    
    for trace, file in results:
        if trace is not None:
            with open(f'./eval/traces_new/{model_name}/{file}','w',encoding='utf-8') as f:
                json.dump(trace, f, ensure_ascii = False, indent=4)
            

if __name__ == "__main__":
    models = ['claude-3-5-sonnet-20240620']

    for model in models:
        print(model)
        asyncio.run(main(model))

