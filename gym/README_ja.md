# GYMの設定

以下のコマンドを実行します。

```bash
python -m gym.main gym/example.yaml test.jsonl
```

ここで、`gym/example.yaml`はシナリオ設定ファイルであり、`test.jsonl`は出力ファイルです。

設定はルートフォルダの `private.toml` から読み込むので、`default_completions_model` と互換性のあるモデルを記入してください。
