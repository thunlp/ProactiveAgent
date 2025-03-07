<div align= "center">
    <h1> データ概要 </h1>
</div>

## 📊 データ公開

データの3つの部分を公開します：

- **テストデータ**：これは[ProactiveBench](../eval/README.md)のテストデータで、生成データと手動で収集されたデータが含まれています。すべての個人情報は削除されています。
- **報酬データ**：これは3つの部分で構成されています。`test_data.jsonl`は報酬モデルのテストデータ、`train_data.jsonl`は報酬モデルのトレーニングデータ、`trainset_reward_llama.json`は[LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory)互換の報酬モデルトレーニングデータです。
- **エージェントデータ**：これはProactive Agentのカスタムモデルをトレーニングするために使用されるデータです。

## データアノテーションの実行

データアノテーションを実行するには、まず[ProactiveBench](../eval/README.md)のテストデータを`./dataset/annotation/data`フォルダにコピーします。その後、以���のコマンドを実行します。

```bash
python dataset/annotation/main.py
```

次の出力が表示されます：

```bash
 * Running on http://localhost:7860/ (Press CTRL+C to quit)
```

この時点で、ブラウザで`http://localhost:7860`を開くと、データをアノテートできるようになります。
アノテートされたデータは`./dataset/annotation/result`フォルダに保存されます。

ヒント：
- デフォルトのログインパスワードは`password`です。`dataset/annotation/main.py`でパスワードを変更できます。アノテーターには識別のためにUUIDが割り当てられます。
- GUIはイベントトレースと対応するエージェントの応答を表示します。アノテーターは自分の好みに合ったタスクをチェックするか、適切なタスクがない場合は`Reject all`を選択します。
- 現在のトレースが完了したら、`next_trace`をクリックして新しい、アノテートされていないトレースを取得します。ウィンドウに`Current trace done. Press [next trace]!!!`と表示されている時に終了することで、アノテーションの完全性を確保します。

## 報酬モデルのトレーニングセットの構築

データをアノテートした後、報酬モデルのトレーニングセットを構築できます。
まず、以下のコマンドを使用してアノテートされたデータを抽出およびフィルタリングします。

```bash
cd dataset/annotation
python convert_annotations.py
```

これにより、`./dataset/reward_data`フォルダに`test_data.jsonl`と`train_data.jsonl`が作成されます。
次に、以下のコマンドを実行して報酬モデルのトレーニングセットを構築します。

```bash
python build_reward_trainset.py
```

`build_reward_trainset.py`を実行する前に、スクリプト内のクライアント設定を自分の設定に変更してください。

```python
client = openai.AsyncOpenAI(api_key="sk-xx",base_url="http://localhost:8000/v1/")
model = "your_model_name"
```

[ VLLM](https://github.com/vllm-project/vllm)を使用してローカルサーバーで独自のモデルをホストし、`base_url`を独自のサーバーアドレスに変更できます。

その後、生成されたトレーニングセットを使用して[LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory)を使用して報酬モデルをトレーニングできます。

## プロアクティブエージェントのトレーニングセットの構築

```Plaintext
警告：以下のコマンドを実行する前にGYMを構成してください。
```

プロアクティブエージェントのトレーニングセットを構築するには、以下のことを行う必要があります：

- データ生成のためにGYMのシーンを構築します。
- GYMとシーン構成を使用してイベントを生成します。
- 生成されたイベントを使用してプロアクティブエージェントのトレーニングデータを生成します。

### データ生成のためのシーンの構築

以下のコマンドを使用してGYMのシーンを構築できます(ルートフォルダで実行)。

```bash
python dataset/build_scenes.py --seedfile ./dataset/seedtask.yaml --savefile ./dataset/new_scenes.yaml
```

これにより、`./dataset`フォルダに新しいシーンファイル`new_scenes.yaml`が生成されます。
すべてのシーンは`dataset/agent_data`フォルダにもコピーされます。

### GYMを使用したイベントの生成

以下のコマンドを使用してGYMでイベントを生成できます。

```bash
python dataset/run_datagen.py --scene_file ./dataset/new_scenes.yaml
```

これにより、イベントが生成され、`./dataset/agent_data`フォルダに`.jsonl`形式で保存されます。

### プロアクティブエージェントのトレーニングデータの生成

以下のコマンドを使用してプロアクティブエージェントのトレーニングデータを生成できます。

```bash
python build_agent_trainset.py
```

これにより、`./dataset/agent_data`フォルダに`agent_trainset.jsonl`が作成されます。

これで、生成されたデータを使用してプロアクティブエージェントのカスタムモデルをトレーニングできます。
