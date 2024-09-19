import jsonlines
import json
import openai

import asyncio
import json
import random


train_data = list(jsonlines.Reader(open("dataset/reward_data/train_data.jsonl")))
save_path = "dataset/reward_data/trainset_reward_llama.json"
category_nums = {
    "Missed-Need (MN)": 0,
    "Correct-Rejection (CR)": 0,
    "Correct-Detection (CD)": 0,
    "False-Alarm (FA)": 0
}

for item in train_data:
    category_nums[item["category"]] += 1

max_count = int(max(category_nums.values()) / 5)

total_num = len(train_data)
for cname in ["Missed-Need (MN)","Correct-Rejection (CR)","Correct-Detection (CD)","False-Alarm (FA)"]:
    if category_nums[cname] < max_count:
        num_to_add = max_count - category_nums[cname]
        category_items = [item for item in train_data if item["category"] == cname]
        train_data.extend(random.choices(category_items,k=num_to_add))

sem = asyncio.Semaphore(32)
client = openai.AsyncOpenAI(api_key="sk-xx",base_url="http://localhost:8000/v1/")
model = "llama3.1-70b"


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

def format_message(obs, pred_task, user):
    
    inst_dict = {
        "Observations (Time Ascending)": obs,
        "Proposed Task": pred_task,
        "User Judgement": "accepted" if user else "rejected",
        "Instruction": "You as the user have given the judgement to the proposed task. You should complete the reasoning process for your judgement in first person. Try to understand the decision and give same judgement.",
    }
    return [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":json.dumps(inst_dict,sort_keys=False,ensure_ascii=False,indent=4)}
    ]

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

def format_thought_check(thought:str):
    CHECK_SYSTEM = '''<Task>
You will be given a string of thoughts, you should generate the judgement by infer the thought.
Please generate the judgement according to the thought.
</Task>    

<Rule> 
1. Analyze the reasoning provided in the `reason` field to understand the thought process behind the decision.
2. If the reasoning indicates acceptance of the prediction, mark the judgement result as `accepted`.
3. If the reasoning indicates rejection of the prediction, mark the judgement result as `rejected`.
</Rule>

<Format>
You should answer with following JSON format:
{
    "reason": "Your analysis of the thought.",
    "judgement": "accepted or rejected"
}
</Format>'''
    inst_dict = {
        "Thought To Check": thought,
        "Instruction": "You should analyze the thought and provide the judgement result according to the provided thought.",
    }
    return [
        {"role":"system","content":CHECK_SYSTEM},
        {"role":"user","content":json.dumps(inst_dict,sort_keys=False,ensure_ascii=False,indent=4)}
    ]


async def obtain_reason(item,):
    messages = format_message(item['obs'], item['pred_task'], item['valid'])
        
    async with sem:
        res = await client.chat.completions.create(
            messages=messages,
            model=model,
        )
        
        messages.append({
            "role":"assistant",
            "content": res.choices[0].message.content
        })
    
        parsed_obj = json.loads(res.choices[0].message.content)
        acceptance = parsed_obj["judgement"]
    
        # check result for 3 times
        res = await client.chat.completions.create(
            messages=format_thought_check(parsed_obj["thought"]),
            model=model,
            temperature=0.8,
            n = 5
        )
        for choice in res.choices:
            validation = json.loads(choice.message.content)["judgement"]
            if validation not in ["accepted","rejected"]:
                raise ValueError("The judgement should be accepted or rejected.")
            if validation != acceptance:
                raise ValueError("The judgement should be consistent.")
            
        
    if acceptance not in ["accepted","rejected"]:
        raise ValueError("The judgement should be accepted or rejected.")
    if acceptance == "accepted" and not item['valid']:
        raise ValueError("The task should be rejected.")
    if acceptance == "rejected" and item['valid']:
        raise ValueError("The task should be accepted.")
    
    messages[:2] = format_reward_instruction(item['obs'],item['pred_task'])
    
    
    return messages


async def main():
    import json
    trainset = []
    while len(trainset) < len(train_data):
        
        category_nums = {
            "Missed-Need (MN)": 0,
            "Correct-Rejection (CR)": 0,
            "Correct-Detection (CD)": 0,
            "False-Alarm (FA)": 0
        }
        
        trainset = []
        trainset_hash = [hash(json.dumps(format_reward_instruction(item['obs'],item['pred_task']))) for item in train_data]
        coros = []
        
        try:
            for item in json.load(open(save_path)):
                new_hash = hash(json.dumps(item["conversations"][:2]))
                if new_hash in trainset_hash:
                    trainset_hash.remove(new_hash)
                    trainset.append(item["conversations"])
                    
        except:
            pass

        import tqdm

        
        for item in train_data:
            new_hash = hash(json.dumps(format_reward_instruction(item['obs'],item['pred_task'])))
            if new_hash in trainset_hash:
                coros.append(obtain_reason(item))
                trainset_hash.remove(new_hash)
                category_nums[item["category"]] += 1
        
        for f in tqdm.tqdm(asyncio.as_completed(coros), total=len(coros), ncols=150):
            try:
                trainset.append(await f)
            except Exception as e:
                print(e)

        print(len(trainset))
        


        trainset = [{"conversations":item} for item in trainset]
        import json
        json.dump(trainset, open(save_path, "w"))

if __name__ == "__main__":
    asyncio.run(main())


