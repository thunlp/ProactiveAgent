# GYM Configuration

To run the gym, you should first create a `private.toml` file under `gym` folder with a format of:

After that, run the following command.

```bash
python -m gym.main gym/example.yaml test.jsonl
```

where `gym/example.yaml` is the senario configuration file, and `test.jsonl` is the output file.
