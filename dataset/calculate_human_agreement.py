import jsonlines

for filen in ["dataset/reward_data/test_data.jsonl", "dataset/reward_data/train_data.jsonl"]:
    with open(filen, "r") as file:
        data = list(jsonlines.Reader(file))
    human_agreement = []
    for item in data:
        human_agreement.extend([i == item["valid"] for i in item["annotation"]])
    print(f"File: {filen}\nHuman Agreement: ", sum(human_agreement) / len(human_agreement))