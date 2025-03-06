# GYM 配置
运行以下命令。

```bash
python -m gym.main gym/example.yaml test.jsonl
```

其中 `gym/example.yaml` 是场景配置文件，`test.jsonl` 是输出文件。

配置将会从根目录下的 `private.toml` 进行读取，所以请确保填写与 `default_completions_model` 相对应的模型。
