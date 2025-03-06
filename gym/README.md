# GYM Configuration

Run the following command.

```bash
python -m gym.main gym/example.yaml test.jsonl
```

where `gym/example.yaml` is the senario configuration file, and `test.jsonl` is the output file.

The configuration will read from the `private.toml` in the root folder, so please make sure to fill the model which is compatible with the `default_completions_model`.
