import asyncio
import fire
import json
import openai
import re
import os
import tenacity
import tqdm

import json5
import sys
sys.path.append("./")

from reward_model_template import format_reward_instruction

async def run_check(data):
    client = openai.AsyncOpenAI(
        base_url="http://localhost:8000/v1/",
        api_key="sk-1234",
    )
    sem = asyncio.Semaphore(32)
    pbar = tqdm.tqdm(total=sum(map(lambda x: "agent_response" in x,data)),ncols=100)
    async def check_event_seq(events):
        last_event = events[-1]
        if "agent_response" not in last_event:
            return

        if last_event["agent_response"] is None:
            last_event["agent_response"] = [None]      
        if len(last_event["agent_response"]) == 0:
            last_event["agent_response"] = [None]

        
        last_event["judgement"] = []
        for pid,pred in enumerate(last_event["agent_response"]):
            obs = list(map(lambda x: x["observation"], events))
            messages = format_reward_instruction(obs, pred)
            async with sem:
                try:
                    async for attempt in tenacity.AsyncRetrying(stop= tenacity.stop_after_attempt(10)):
                        with attempt:
                            response = await client.chat.completions.create(
                                messages=messages,
                                model="activellama",
                                temperature=(attempt.retry_state.attempt_number > 2)*0.5,
                                # response_format={"type": "json_object"}
                            )
                            res = response.choices[0].message.content                        
                            last_event["judgement"].append(json5.loads(res)["judgement"] == "accepted")
                            
                except ValueError as e:
                    print(f"Error: {e}")
                    continue
            pbar.update(1)
    
    coros = [check_event_seq(data[:idx+1]) for idx in range(len(data))]
    
    await asyncio.gather(*coros)
        

def main(
    infile:str,
    outfile:str,
):
    if os.path.exists(outfile):
        print(f"Warning: Output file {outfile} already exists. Exiting.")
        return
    
    with open(infile) as f:
        data = json.load(f)
    print(f"File {infile} loaded.")
    
    asyncio.run(run_check(data))
    
    with open(outfile, 'w') as f:
        json.dump(data, f)
        
    
    
if __name__ == '__main__':
    fire.Fire(main)