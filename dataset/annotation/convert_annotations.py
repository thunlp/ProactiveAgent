# %%
import glob
import json

# %%
files = glob.glob("./result/*.json")

# %%
files

# %%
import numpy as np
import math
def parse_label(label, tasks):
    if isinstance(label,str) and label == "Reject all":
        return [False]*len(tasks)
    elif isinstance(label,list):
        return [True if idx in label else False for idx in range(len(tasks))]
    else:
        raise ValueError("Invalid label")


parsed_data = []

help_turns = 0

human_agreement = []

def add_data(labels,tasks,obs):
    global help_turns
    help_needed = False

    
    # major vote
    a = np.array(labels)
    if any(np.sum(a, axis=0) == len(labels)):
        help_needed = True

    no_select = []
    for i in np.sum(a, axis=1):
        if i == 0:
            no_select.append(True)
        else:
            no_select.append(False)
    if len(no_select) >= 2:
        if help_needed and sum(map(lambda x: 1-x,no_select))>=2:
            help_turns += 1
            parsed_data.append({
                "obs": obs,
                "pred_task": None,
                "valid": False,
                "help_needed": help_needed,
                "annotation": no_select
            })
        elif sum(map(lambda x: 1-x,no_select)) > 0:
            parsed_data.append({
                "obs": obs,
                "pred_task": None,
                "valid": True,
                "help_needed": help_needed,
                "annotation": no_select
            })


    valid_true = np.sum(a, axis=0) >= 2
    for idx in range(len(tasks)):
        if valid_true[idx]:
            human_agreement.extend(list(a[:,idx] == True))
            
            parsed_data.append({
                "obs": obs,
                "pred_task": tasks[idx],
                "valid": True,
                "help_needed": help_needed,
                "annotation": list(map(lambda x:bool(x),a[:,idx]))
            })

    
    valid_false = np.sum(1-a, axis=0) >= 2
    for idx in range(len(tasks)):
        if valid_false[idx]:
            human_agreement.extend(list(a[:,idx] == False))
            
            parsed_data.append({
                "obs": obs,
                "pred_task": tasks[idx],
                "valid": False,
                "help_needed": help_needed,
                "annotation": list(map(lambda x:bool(x),a[:,idx]))
            })

    
    
total_turns = 0

for file in files:
    data = json.load(open(file))
    total_turns += len(data)
    for idx in range(len(data)):
        item = data[idx]
        if "real_user" in item:
            labels = [parse_label(label, item["candidate_task"]) for label in item["real_user"].values()]
            add_data(labels,item["candidate_task"],[data[i]["observation"] for i in range(idx+1)])

# %%
sum(human_agreement)/len(human_agreement)

# %%
help_turns/total_turns

# %%
len(parsed_data)

# %%
sum(map(lambda x:x["valid"],parsed_data))

# %%
sum(map(lambda x:x["help_needed"],parsed_data))

# %%
category_nums = {
    "Missed-Need (MN)": 0,
    "Correct-Rejection (CR)": 0,
    "Correct-Detection (CD)": 0,
    "False-Alarm (FA)": 0
}

cate_data = {
    "Missed-Need (MN)": [],
    "Correct-Rejection (CR)": [],
    "Correct-Detection (CD)": [],
    "False-Alarm (FA)": []
}

human_agree = {
    "Missed-Need (MN)": [],
    "Correct-Rejection (CR)": [],
    "Correct-Detection (CD)": [],
    "False-Alarm (FA)": []
}

for item in parsed_data:
    if item["pred_task"] is None:
        if item["help_needed"]:
            item["category"] = "Missed-Need (MN)"
            category_nums["Missed-Need (MN)"] += 1
            cate_data["Missed-Need (MN)"].append(item)
        else:
            item["category"] = "Correct-Rejection (CR)"
            category_nums["Correct-Rejection (CR)"] += 1
            cate_data["Correct-Rejection (CR)"].append(item)
    else:
        if item["valid"]:
            item["category"] = "Correct-Detection (CD)"
            category_nums["Correct-Detection (CD)"] += 1
            cate_data["Correct-Detection (CD)"].append(item)
        else:
            item["category"] = "False-Alarm (FA)"
            category_nums["False-Alarm (FA)"] += 1
            cate_data["False-Alarm (FA)"].append(item)

# %%
category_nums

# %%
avg_test_size = 30
avg_test_size

# %%
import random
random.seed(42)
testdata = []
traindata = []
for c_name in ["Missed-Need (MN)","Correct-Rejection (CR)","Correct-Detection (CD)","False-Alarm (FA)"]:
    random.shuffle(cate_data[c_name])
    # for testdata, the annotation must contains 3 labels
    c = 0
    idx = 0
    while c < avg_test_size and idx < len(cate_data[c_name]):
        item = cate_data[c_name][idx]
        if len(item["annotation"]) == 3 and sum(map(lambda x:x==item["valid"],item["annotation"])) == 3:
            testdata.append(cate_data[c_name].pop(idx))
            c += 1
        else:
            idx += 1
    
    idx = 0
    while c < avg_test_size and idx < len(cate_data[c_name]):
        item = cate_data[c_name][idx]
        if sum(map(lambda x:x==item["valid"],item["annotation"])) == 2:
            testdata.append(cate_data[c_name].pop(idx))
            c += 1
        else:
            idx += 1
            
    print(c_name,c)

    traindata.extend(cate_data[c_name])

# %%
valid_data = {
    "Missed-Need (MN)": [],
    "Correct-Rejection (CR)": [],
    "Correct-Detection (CD)": [],
    "False-Alarm (FA)": []
}
for item in traindata:
    cate = item["category"]
    # if sum(map(lambda x:x==item["valid"],item["annotation"])) >= 2:
    valid_data[cate].append(item)
        
list(map(len,valid_data.values()))

# %%
import jsonlines

jsonlines.Writer(open('../reward_data/train_data.jsonl', 'w')).write_all(traindata)
jsonlines.Writer(open('../reward_data/test_data.jsonl', 'w')).write_all(testdata)

# %%



