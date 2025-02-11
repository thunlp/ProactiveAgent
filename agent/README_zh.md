<div align = "center">
    <h1> 🤖 主动智能体 </h1>
</div>

# 总览

主动智能体是一个监听用户行为和外部环境的智能体，它将尽可能做到主动和帮助用户。

当前的展示将会监听用户的键鼠事件，用户的浏览器和 `vscode` 并通过弹出桌面通知帮助用户。

## 数据处理
在我们的展示中，我们采用 ActivityWatcher 来监听用户的行为和环境。技术上而言，
- 通过调用 `pynput` 库，智能体将能够获取你的键鼠事件，这些收集的数据将会视为你的行为，该脚本于 `ActionListener` 中实现。我们也通过 `paperclip` 库来确保最终结果将会被写入你的粘贴板。
- 通过使用浏览器插件，智能体将能够获知你的浏览器活动，包括标签个数，你正在浏览的原 HTML 代码等内容。
- 通过使用 vscode 插件，智能体将能够观察到你的工作空间，这包括当前项目名称，编程语言和当前文件名等。

对于用户行为，我们将拼接键鼠事件以获得键盘输入与鼠标的移动，点击等行为。

对于环境信息，
- 通过检查 `afk` 桶，智能体能够了解用户是忙碌或是空闲。
- 通过检查 `windows` 桶，智能体能够知道用户的聚焦处，我们的展示将会忽略除了浏览器和 vscode 之外的其他软件，并主要在这两个软件上提供帮助。
- 通过检查 `vscode` 桶和 `web` 桶，智能体将会知道你的工作内容和重心，并提供更合适的结果。

对于每段时期，`ActionListener` 将会从四个桶中获得信息，并且筛去用户重心不在浏览器或 vscode 上的时间。选择最后一个有效时刻的必要信息，将整合后的事件发送给智能体，而智能体将依赖此向用户提供主动回应。

## 运行主动智能体
为了完整体验主动智能体，你需要先下载额外依赖。

0. 下载依赖。查询 [此处](../README.md#install-activity-watcher) 以获得详细的下载 ActivityWatcher 插件的指导。

1. 配置必要信息
  配置信息包括大语言模型的 api_key, 以及对于 ActivityWatcher 的必要设置，要编辑并被我们的脚本读入，你需要 **复制** 模板文件 `../example_config.toml`, **重命名**为 `../private.toml` 并 **编辑** 其中与 LLM 调用有关的参数。
  **为了能够直接运行模型，你应当配置一个名称为 activeagent 的令牌，该令牌将会被直接调用。请参考 example_config 的注释。**
  同样建议您将 `default_completion_model` 更换为 `activeagent` 以避免可能的 KeyError 错误。

2. 运行指令
    ```bash
    python ragent.py --platform PC [--chromes <你希望监听的浏览器名称> --interval <每轮之间的间隔>]
    python ragent.py --platform PC --chromes explorer.exe,mesdge.exe --interval 10
    ```
    参数说明：
    - `--platform`: 你希望协助的操作平台。当前可以运行 `PC` demo, `Mobile` demo 将会在未来进一步推出。
    - `--apps`: ActivityWatcher 所显示的浏览器名。由于操作平台和浏览器的不同，app 名称也会不同，我们需要你去通过 ActivityWatcher 的 window 桶找到 app 名称，并且通过半角符号 `,` 分割并传入（将在之后更新，为其不便深感抱歉）
    - `--interval`: 智能体尝试提供帮助的频率. 默认为 15，单位为秒。
    - `--_port`: ActivityWatcher所持有和监听的端口，默认为 `5600`, 除非你修改了 ActivityWatcher 的端口，否则无需传入内容。
    如果智能体运行成功，控制台将会展示配置信息以及信息 `Demo running Started.`

在这之后，你就可以打开你的浏览器 和/或 vscode， 我们的智能体将会开始工作。
