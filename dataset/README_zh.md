<div align= "center">
    <h1> 数据总览 </h1>
</div>

## 📊 数据公布

我们公布数据的三个部分：
- **测试数据**： 这一部分是[主动基准](../eval/README.md)的测试数据，包含了生成数据和人工采集数据，所有的个人信息已被移除。
- **奖励数据**：该部分数据包含三个部分。 `test_data.jsonl` 作为奖励模型的测试数据， `train_data.jsonl` 作为奖励模型的训练数据， `trainset_reward_llama.json` 则是 [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) 匹配奖励模型的训练数据。
- **智能体数据**：这个数据用来训练主动智能体的个性化模型。


## 运行数据标注
为了运行数据标注，你应当首先复制 [主动基准](../eval/README.md) 的测试数据于文件夹 `./dataset/annotation/data` 下，之后运行指令

```bash
python dataset/annotation/main.py
```

你将看到以下输出：

```bash
 * Running on http://localhost:7860/ (Press CTRL+C to quit)
```
此时你可以使用浏览器打开 `http://localhost:7860` 并标注数据。
已标注的数据将会存放于 `./dataset/annotation/result` 文件夹下。

提示：
- 默认的登陆密码为 `password`, 可以在 `dataset/annotation/main.py` 处修改默认密码，每个标注员将会被分配一个 UUID 作为验证。
- GUI将会展示时间序列和对应的智能体回应，标注员应选择你所期待的选项，或者对于没有适合任务的情况下，选择 `Reject all` 选项。
- 当前序列完毕后，需要点击 `next_trace` 以获得新的，未经标注的序列，尽量在窗口展示 `Current trace done. Press [next trace]!!!` 时退出以保证标注的完整性。

## 构建奖励模型训练集
在你标注完毕数据之后，你可以为奖励模型构建一个训练集，首先，你应当用下述指令提取与筛选数据：
```bash
cd dataset/annotation
python convert_annotations.py
```
这将在 `./dataset/reward_data` 文件夹下创建 `test_data.jsonl` 和 `train_data.jsonl` 文件。
之后，你可以运行下列指令构建奖励模型的训练集。

```bash
python build_reward_trainset.py
```
请注意：在运行 `build_reward_trainset.py` 之前，请确保你已经修改了脚本中的客户端配置为自己的配置。
```python
client = openai.AsyncOpenAI(api_key="sk-xx",base_url="http://localhost:8000/v1/")
model = "你的模型名称"
```

你可以在本地服务器上使用[VLLM](https://github.com/vllm-project/vllm)搭建自己的模型，同时修改 `base_url` 为自己的服务器地址。

在这之后，你可以使用 [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) 以在生成的训练集上训练自己的奖励模型。

## 构建主动智能体训练集
```Plaintext
警告：请在配置完毕 环境模拟器 后运行下列指令
```

为了构建主动智能体的训练集，你需要完成：
- 为 环境模拟器 构造场景以生成数据。
- 通过 环境模拟器 和你的场景配置以生成事件。
- 通过生成的事件为 主动智能体 构建训练数据。

### 为数据生成构建场景
你可以用下列指令为 环境模拟器 构建场景：
```bash
python  build_scenes.py --seedfile ./dataset/seedtask.yaml --savefile ./dataset/new_scenes.yaml
```

这将在 `./dataset` 文件夹下生成新的场景文件 `new_scenes.yaml`。
所有的场景也将会在 `dataset/agent_data` 文件夹下存有副本。

### 使用 环境模拟器 构建场景
你可以用下列指令，通过 环境模拟器生成事件

```bash
python run_datagen.py --scene_file ./dataset/new_scenes.yaml
```

这将生成事件并将其以 `.jsonl` 格式保存于 `./dataset/agent_data` 文件夹下。 

### 为主动智能体生成训练数据
你可以用下列指令为主动智能体生成训练数据。
```bash
python build_agent_trainset.py
```

这将在 `./dataset/agent_data` 文件夹下创建 `agent_trainset.jsonl` 文件。

现在，你可以用产生的模型来训练自己的主动智能体模型。
