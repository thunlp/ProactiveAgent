# GYM 配置

要运行 gym，您应该首先在 `gym` 文件夹下创建一个 `private.toml` 文件，格式如下：

之后，运行以下命令。

```bash
python -m gym.main gym/example.yaml test.jsonl
```

其中 `gym/example.yaml` 是场景配置文件，`test.jsonl` 是输出文件。
