<div align= "center">
    <h1> 🧩 ProactiveBench </h1>
</div>

# Overview

ProactiveBench is a benchmark for evaluating proactive agents. It includes a dataset, a reward model, and evaluation scripts.
Our test set contains events in three categories: coding, writing, and daily life.
Currently, the test set contains `227` events.
The reward model is trained on the dataset and reaches an F1 score of `0.918` on the test set.
We provide all scripts to evaluate the performance of the proactive agent and the reward model.

## Reward Model Evaluation

The reward model is used to evaluate the performance of the Proactive Agent.
You can download the reward model from here (Coming soon) and host it with frameworks like [VLLM](https://github.com/vllm-project/vllm) to provide OpenAI style API.

After that, you should change the script `reward_model_scoring.py` to set the address of your model, and run the script with

```bash
python eval/reward_model_scoring.py
```

After the process, you will get the final score for your reward model.

## Proactive Agent Evaluation

To check your model's performance, you will need to change the `./eval/script.py` and load in your model(or use the SDK), and run the script with:

```bash
python eval/script.py
```

The test data will be send to the model, and all the traces with agent response will be saved under `./eval/traces_new` folder.
After the process, you could run

```bash
# You should modify the address in judge_agent_prediction.py to your reward model address before run the script.
sh eval/judge_result.sh
```

which will let the Reward Model to evaluate whether the response from the agent is acceptable or not. The results will be saved under `./eval/judged` folder.

After judged by the reward model, you could run

```bash
sh calculate.sh
```

to finally get a score for your model.
