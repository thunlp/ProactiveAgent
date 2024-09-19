import jsonlines
import json
import glob
import asyncio
import os
import re
import tqdm
import tenacity
import jsonlines
import logging
from copy import deepcopy
from gym.components.activeagent import SYSTEM, STEP_OBJ
from eval.reward_model_template import format_reward_instruction
from codelinker import CodeLinker, CodeLinkerConfig

cfg_file = "private.toml"
cl = CodeLinker(CodeLinkerConfig.from_toml(cfg_file))
agent_data_path = "dataset/agent_data"

save_file = os.path.join(agent_data_path, "agent_traindata.jsonl")
save_writer = jsonlines.open(save_file,mode="w")

sem = asyncio.Semaphore(64)

logger = logging.getLogger()
logger.setLevel(logging.WARNING)


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

def cut_messages(messages,max_length=20000,max_agent_response_length=10000):
    cuted = []
    
    lengths = list(map(lambda x:len(x['content']), messages[1:]))
    total_length = len(messages[0]['content'])
    agent_response_length = 0
    for length,msg in zip(lengths[::-1],messages[:0:-1]):
        if length + total_length < max_length:
            if msg['role'] == "assistant":
                if length + agent_response_length < max_agent_response_length:
                    agent_response_length += length
                    cuted.append(msg)                    
                    total_length += length
                else:
                    continue
            else:
                cuted.append(msg)
                total_length += length
        else:
            break            
        
    cuted = cuted[::-1]
    
    while cuted[0]['role'] != 'user':
        cuted.pop(0)
    
    # merge adjacent user message
    ret = []
    obs = []
    idx = 0
    
    while idx < len(cuted):
        if cuted[idx]['role'] == 'user':
            obs.append(json.loads(cuted[idx]['content']))
        else:
            if len(obs) == 1:
                ret.append({"role":"user","content":json.dumps(obs[0])})
            elif len(obs) > 1:
                ret.append({"role":"user","content":json.dumps({"Observations":obs})})
            else:
                raise ValueError("Empty Observations")
            obs = []
            ret.append(cuted[idx])
        
        idx += 1
    if len(obs) == 1:
        ret.append({"role":"user","content":json.dumps(obs[0])})
    elif len(obs) > 1:
        ret.append({"role":"user","content":json.dumps({"Observations":obs})})
    
    ret.insert(0,messages[0])
    return ret


async def make_valid_prediction(messages,past_events,max_trials = 15):
    messages = cut_messages(deepcopy(messages))
    
    trials = 0
    pred = None
    res = None
    while trials < max_trials:
        try:
            async with sem:
                if trials > 1 and pred is not None and res is not None:
                    ret = await cl.exec(
                        model=os.environ.get("ACTIVEAGENT_MODEL", "activeagent"),
                        messages=messages + [{"role":"user","content":json.dumps({
                            "Previous Prediction": pred,
                            "Status":"Rejected",
                            "User Feedback":res["thought"],
                            "Instructions":"Your previous prediction is rejected! You must make a different prediction."
                        })}],
                        completions_kwargs={"temperature": 0.8},
                    )
                else:
                    ret = await cl.exec(
                        model=os.environ.get("ACTIVEAGENT_MODEL", "activeagent"),
                        messages=messages,
                        completions_kwargs={"temperature": 0.8},
                    )
                    
            pred = extrat_pred(ret)

            async for attemp in tenacity.AsyncRetrying(stop=tenacity.stop_after_attempt(5),reraise=True):
                with attemp:
                    ret = await cl.exec(
                            messages=format_reward_instruction(obs=past_events,pred_task=pred["Proactive Task"]),
                            model=os.environ.get(
                                "ACTIVERM_MODEL", "activerm"),
                            completions_kwargs={"temperature": 0.0 + 0.4 * (attemp.retry_state.attempt_number > 1)},
                        )
                    res = json.loads(ret)
            if res["judgement"] == "accepted":
                break
        except Exception as e:
            trials += 1
            if trials >= max_trials:
                import traceback
                traceback.print_exc()
                print("Failed to make valid prediction", e)
                return []
            continue
    
    return messages + [{"role":"assistant","content":json.dumps(pred)}]
    
pbar = tqdm.tqdm(total=0,ncols=150)
async def generate_new_data(fevents):
    
    messages = [
        {"role":"system","content":SYSTEM},
    ]
    past_events = []
    for e in fevents:
        match e["source"]:
            case "ProactiveAgent":
                # replace last assistant message
                if messages[-1]["role"] == "assistant":
                    messages[-1] = {"role":"assistant","content":e["content"]}
                    ret = deepcopy(messages)
                    step_obj = deepcopy(STEP_OBJ)
                    step_obj["Observations"] = json.loads(ret[-2]["content"])
                    ret[-2]["content"] = json.dumps(step_obj)
                    
                    record_step(ret)

                elif messages[-1]["role"] == "user":
                    messages.append({"role":"assistant","content":e["content"]})
                    ret = deepcopy(messages)
                    step_obj = deepcopy(STEP_OBJ)
                    step_obj["Observations"] = json.loads(ret[-2]["content"])
                    ret[-2]["content"] = json.dumps(step_obj)
                    
                    record_step(ret)
            case _:
                new_event = {"Time": e["time"], "Event": e["content"]}
                past_events.append(new_event)
                
                step_obj = deepcopy(STEP_OBJ)
                step_obj["Observations"] = new_event
                messages.append({"role":"user","content": json.dumps(step_obj)})
                
                ret = await make_valid_prediction(messages,past_events)
                
                if len(ret) > 0:
                    record_step(ret)
                    messages[-1]["content"] = json.dumps(json.loads(messages[-1]["content"])["Observations"])
                    messages.append(ret[-1])
                else:
                    messages[-1]["content"] = json.dumps(json.loads(messages[-1]["content"])["Observations"])

        pbar.update(1)
  

def record_step(messages):
    
    save_writer.write(messages)
    
async def main():
    files = glob.glob(os.path.join(agent_data_path,"scene*.jsonl"))
    tasks = []
    total_length = 0
    for f in files:
        with jsonlines.open(f) as reader:
            data = list(reader)
            fevents = list(filter(lambda x: 'events' in x['tags'] or ("agent.proactive" in x['tags'] and x["source"]=="ProactiveAgent"),data))
            total_length += len(fevents)
            pbar.total = total_length
        for d in data:
            if 'agent.response' in d['tags']:
                messages = json.loads(d['content'])
                record_step(messages)

        tasks.append(asyncio.create_task(generate_new_data(fevents)))

    for t in asyncio.as_completed(tasks):
        try:
            await t
        except Exception as e:
            import traceback
            traceback.print_exc()

    save_writer.close()
    
    # load the saved data
    
    with jsonlines.open(save_file) as reader:
        data = list(reader)
        print("Trainset Size: ",len(data))
        print("Example: ",data[0])
        print("Estimate Events Nums: ",sum(map(lambda x: (len(x)-1)/2 ,data)))

        trainset = []
        for d in data:
            trainset.append({"conversations":d})
        with open(os.path.join(agent_data_path,"agent_trainset.json"),"w") as f:
            json.dump(trainset,f)

if __name__=="__main__":
    asyncio.run(main())