<div align= "center">
    <h1> 🧩 ProactiveBench </h1>
</div>

# 总览

ProactiveBench 是用来评估主动智能体的基准点。其包含一个数据集，一个奖励模型和评估脚本。
我们的训练集包含了三个类别的事件：编程，写作和日常生活。
当前，我们的测试集包含`227`个事件。
在数据集上训练的奖励模型在测试集上的 F1 分数达到了 `0.918`.
我们将提供所有用于评估主动智能体和奖励模型的脚本。

## 奖励模型评估
奖励模型用于评估主动智能体的性能。
你可以在此(敬请期待)下载奖励模型并且通过 [VLLM](https://github.com/vllm-project/vllm) 等框架以搭建并提供 OpenAI 风格的 API。

在此之后，你应当修改 `reward_model_scoring.py` 脚本并设置地址为自己模型的地址，运行脚本
```bash
python eval/reward_model_scoring.py
```
在该过程之后，你将会得到你的奖励模型的最终分数。

## 主动智能体评估
为了检查模型性能，你需要修改文件 `./eval/script.py` 以导入你的模型，同时运行脚本
```bash
python eval/script.py
```
该脚本会向模型输入测试数据，并且保存所有的轨迹和智能体应答于文件夹 `./eval/traces_new` 下。
在该过程之后，你可以运行
```bash
# 你应当在运行该脚本前修改 judge_agent_prediction.py 中的地址为自己的奖励模型
sh eval/judge_result.sh
```
其将让奖励模型评估来自智能体的回复是否可接受，结果将会存放于 `./eval/judged` 文件夹下。

在经过奖励模型评估之后，你可以运行
```bash
sh calculate.sh
```
获得你的模型的最终分数。
