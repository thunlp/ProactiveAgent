<div align= "center">
    <h1> Data Overview </h1>
</div>

## 📊 Data Release

We release three part of our data:

- **test_data**: This is the test data for the [ProactiveBench](../eval/README.md), containing both generated data and manually collected data. All personal information has been removed.
- **reward_data**: This consists of three parts, the `test_data.jsonl` is the test data for the reward model, the `train_data.jsonl` is train data for the reward model, and the `trainset_reward_llama.json` is [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) compatible reward model training data.
- **agent_data**: This data is used to training custom models for the Proactive Agent.

## Running Data Annotation

To run a data annotation, you should first copy the test data of the [ProactiveBench](../eval/README.md) to the `./dataset/annotation/data` folder. Then run the command

```bash
python dataset/annotation/main.py
```

You will see the following output:

```bash
 * Running on http://localhost:7860/ (Press CTRL+C to quit)
```

Now you can open `http://localhost:7860` with your browser, and you will be able to annotate the data.
Annotated data will be saved under `./dataset/annotation/result` folder.

Tips:
- The default login password is `password`, you can change the password in the `dataset/annotation/main.py`. The annotator will be assigned to a UUID for identification.
- the GUI will display the event trace and the corresponding agent response, for annotators, you will check those tasks in your favor, or choose `Reject all` if no tasks are suitable for you.
- You will click on `next_trace` to get a new, not annotated trace when current trace is done. Make sure to exit when the window showing `Current trace done. Press [next trace]!!!` for the integrity of the annotation.

## Build Trainset for the Reward Model
After you annotate the data, you can build a trainset for the reward model.
First, you should extract and filter the annotated data with following commands:

```bash
cd dataset/annotation
python convert_annotations.py
```

This will create `test_data.jsonl` and `train_data.jsonl` in the `./dataset/reward_data` folder.
Then you can run the following command to build the trainset for the reward model:

```bash
python build_reward_trainset.py
```

To be noticed, before you run `build_reward_trainset.py`, please make sure you change the client configuration in the script to your own configuration.

```python
client = openai.AsyncOpenAI(api_key="sk-xx",base_url="http://localhost:8000/v1/")
model = "your_model_name"
```

You can host your own model with [VLLM](https://github.com/vllm-project/vllm) on the local server, and change the `base_url` to your own server address.

After that, you could use [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) to train your reward model with the generated trainset.

## Build the Proactive Agent Trainset

```Plaintext
Warning: Please configure the GYM before you run the following commands.
```

To build the trainset for the Proactive Agent, you have to do following things:

- Build the scenes for the GYM to generate data.
- Generate the events with the GYM and your scenes configuration.
- Generate trainings data for the Proactive Agent with generated events.

### Build Scenes for Data Generation

You can build scenes for the GYM with the following command (Run in root folder):

```bash
python dataset/build_scenes.py --seedfile ./dataset/seedtask.yaml --savefile ./dataset/new_scenes.yaml
```

This will generate a new scene file `new_scenes.yaml` in the `./dataset` folder.
All scenes will also have a copy in the `dataset/agent_data` folder.

### Generate Events with the GYM

You can generate events with the GYM with the following command:

```bash
python dataset/run_datagen.py --scene_file ./dataset/new_scenes.yaml
```

This will generate events and store them in `.jsonl` format under the `./dataset/agent_data` folder.


### Generate Trainings Data for the Proactive Agent

You can generate trainings data for the Proactive Agent with the following command:

```bash
python build_agent_trainset.py
```

This will create `agent_trainset.jsonl` in the `./dataset/agent_data` folder.

Now you can use the data to train your custom model for the Proactive Agent.