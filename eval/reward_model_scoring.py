from tqdm import tqdm
import jsonlines
import openai
import asyncio
import tenacity
import re
import json
import os
from reward_model_template import format_reward_instruction
with open("dataset/reward_data/test_data.jsonl", "r") as file:
    data = list(jsonlines.Reader(file))
    
print("Total number:", len(data))


category_nums = {
    "Missed-Need (MN)": 0,
    "Correct-Rejection (CR)": 0,
    "Correct-Detection (CD)": 0,
    "False-Alarm (FA)": 0
}


for item in data:
    category_nums[item["category"]] += 1
print(category_nums)
            
category_result  = {
    "Missed-Need (MN)": 0,
    "Correct-Rejection (CR)": 0,
    "Correct-Detection (CD)": 0,
    "False-Alarm (FA)": 0
}

async def main():

    results = []
    client = openai.AsyncOpenAI(
        api_key="sk-1234",
        base_url="http://localhost:8000/v1/"
    )
    sem = asyncio.Semaphore(32)
    model="activellama"

    async def get_response(item):
        async for attemp in tenacity.AsyncRetrying(stop=tenacity.stop_after_attempt(3),wait=tenacity.wait_fixed(1)):
            with attemp:
                async with sem:
                    ret = await client.chat.completions.create(
                        messages=format_reward_instruction(item["obs"], item["pred_task"]),
                        model=model,
                        temperature=0.0,
                        timeout=20,
                    )
            
        
        res = ret.choices[0].message.content
        try:
            acceptance = json.loads(res)["judgement"]
            
        except:
            try:
                acceptance = re.match(r'(.*)"judgement": "(accepted|rejected)"', res, re.DOTALL).groups()[-1]
            except:
                acceptance = None
            
        if acceptance is None:
            pass
        elif acceptance == "accepted":
            acceptance = True
        elif acceptance == "rejected":
            acceptance = False
        else:
            acceptance = None
                
        return {
            "task": item["pred_task"],
            "res":res,
            "valid": item["valid"],
            "pred": acceptance,
            "category": item["category"]
        }
    
    coros = [get_response(item) for item in data]
    pbar = tqdm(asyncio.as_completed(coros), total=len(coros), ncols=100)

    category_progress = {
        "Missed-Need (MN)": 0,
        "Correct-Rejection (CR)": 0,
        "Correct-Detection (CD)": 0,
        "False-Alarm (FA)": 0
    }
    res = {
        "TP": 0,
        "FP": 0,
        "TN": 0,
        "FN": 0
        }
    
    for ret in pbar:
        x = await ret
        category_progress[x["category"]] += 1
        category_result[x["category"]] +=  x["pred"] is not None and x["valid"] == x["pred"]
        results.append(x)
        if x["pred"]:
            if x["valid"]:
                res["TP"] += 1
            else:
                res["FP"] += 1
        else:
            if x["valid"]:
                res["FN"] += 1
            else:
                res["TN"] += 1
        
        with open("rm_result.json", "w") as f:
            json.dump(results, f, indent=4)
        
        s = []
        for sk,k in zip(["MN","CR","CD","FA"], ["Missed-Need (MN)","Correct-Rejection (CR)","Correct-Detection (CD)","False-Alarm (FA)"]):
            s.append("{}: {:0.3f}".format(sk, category_result[k] / (category_progress[k]+1e-6)))
        pbar.set_description(" | ".join(s))
        

    print("Final result:")
    for k,v in category_result.items():
        print(k, v / category_progress[k])
    
    print("Average:", sum(category_result.values()) / sum(category_progress.values()))
    
    print("Confusion Matrix:")
    print(res)
    
    print("Accuracy:", (res["TP"] + res["TN"]) / (res["TP"] + res["TN"] + res["FP"] + res["FN"]))
    print("Precision:", res["TP"] / (res["TP"] + res["FP"]))
    print("Recall:", res["TP"] / (res["TP"] + res["FN"]))
    print("F1:", 2 * res["TP"] / (2 * res["TP"] + res["FP"] + res["FN"]))
    
if __name__ == "__main__":
    asyncio.run(main())
