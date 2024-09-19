import json
import os


def calculate_scores(event_trace: list[dict],eps=1e-8) -> list[int]:

    TP = 0
    TN = 0
    FP = 0
    FN = 0
    tasks_proposed = 0
    tasks_accepted = 0
    for event in event_trace:
        if len(event.get("agent_response", [])) > 0:
            for pred,judge in zip(event["agent_response"], event["judgement"]):
                if pred is not None:
                    tasks_proposed += 1
                    if judge:
                        tasks_accepted += 1
                        TP += 1
                    else:
                        FP += 1
                else:
                    if judge:
                        TN += 1
                    else:
                        FN += 1
    # turn based
    Recall = TP / (TP + FN + eps)
    Precision = TP / (TP + FP + eps)
    Accuracy = (TP + TN) / (TP + TN + FP + FN + eps)
    FA = FP / (TP + FP + eps)
    # single task based
    Accept = tasks_accepted / (tasks_proposed + eps)

    return {
        "Recall": Recall,
        "Precision": Precision,
        "Accuracy": Accuracy,
        "False-Alarm": FA,
        "F1-Score": 2 * (Precision * Recall) / (Precision + Recall + 1e-8),
        "Accept Rate": Accept,
        "Total Events": len(event_trace),
    }


def main(in_dir: str, output: str | None = None, dir_path = None):
    if dir_path is None:
        dir_path = os.path.dirname(__file__)
    splits: dict = json.load(fp=open(os.path.join(dir_path,"../dataset/test_data/splits.json")))
    results = []
    for split_name, split_cfg in splits.items():
        files = [os.path.join(in_dir, f) for f in split_cfg["files"]]

        datas = []
        valid_set = True
        
        for file in files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    datas.extend(data)
            except Exception as e:
                print(f"Error: {e}")
                valid_set = False
                break
        if not valid_set:
            continue
                
        # print("####  Split\t\t", split_name, f" {sum(map(lambda x:len(x),datas))} \t\t####")
        ret = {
            "Category": split_name,
            **calculate_scores(datas)
        }
        results.append(ret)

    import pandas as pd
    df = pd.DataFrame(results)
    print(df)
    if output is None:
        output = os.path.join(dir_path,"results", os.path.basename(in_dir) + ".csv")
    df.to_csv(output, index=False)


if __name__ == "__main__":
    import fire
    fire.Fire(main)
