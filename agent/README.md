<div align = "center">
    <h1> 🤖 Proactive Agent </h1>
</div>

# Overview

Proactive Agent is an agent which will monitor user's actions and outer environment, and be trying to be both proactive and helpful.

The current Demo will listen to your action from your keyboard and mouse events, your chrome and your vscode, and try to help you by popping up a toast.

## Data Processing

In our demo, we use ActivityWatcher for monitoring the user's action and environment.
Technically:
- By using `pynput` library, the agent will be able to capture your keyboard and mouse events, the data collected will be considered as your actions. The script is implemented in `ActionListener`. We also use `paperclip` to make sure the result will be written in your clipboard.
- By using chrome extensions, the agent will be able to know your browser activities including the number of tabs, the raw HTML you are reading, and so on.
- By using vscode extensions, the agent will be able to see your workspace, this includes the current project name, the coding language and the current file name.

For user's action, we will splice the keyboard events and mouse events to get the keyboard input and mouse movement, clicking of the user.

For environment information,
- By checking the `afk` bucket, the agent will be able to know if the user is busy or idle.
- By checking the `window` bucket, the agent will be able to know the focus of the user, our demo will ignore apps but chrome and vscode, and provide assistance mainly on the tow fields.
- By checking `vscode` bucket or `web` bucket, the agent will be able to know your working content and focus, then provide more suitable results.

For each period, the `ActionListener` will get the information from four buckets, and filter those period when the user is not focusing on chrome or vscode. Then, the agent will choose the necessary information for the last valid moment, and pass the aggregated event to the agent, the agent will depend on this to give proactive response to the user.

## Running the Proactive Agent
To fully experience the proactive agent, you will have to install additional dependencies.

0. Install dependencies. Check [here](../README.md#install-activity-watcher) for detailed installation for the ActivityWatcher extensions.

1. Configure necessary information.
  The configuration contains api_keys for LLM, some settings for the activity watcher. To edit and detected by our script, you will **copy** the template file `../example_config.toml`, **rename** it as `../private.toml` and **edit** the configuration related to the LLM calling.
  **To directly run the model, you should configurate an api_key named activeagent, which will be directly used for calling API. See the comment in example_config.toml**.
  It is suggested that you also change the `default_completion_model` to `activeagent` to avoid potential KeyErrors.

1. Running a server.
    ```bash
    python main.py
    ```
    This server is in charge of the functions the agent will be using. If succeeded, the terminal will show information.
    - For windows user, this server will register an AUMID for our agent, which is necessary for our notifications. The script will create a `appid.txt` file, which contains the AUMID. **DO NOT DELETE THIS FILE UNLESS YOU WANT TO GENERATE A NEW AMUID**.

2. With the previous terminal open, open a new terminal and run command:
    ```bash
    python ragent.py --platform PC [--chromes <the chrome you want to watch> --interval <interval seconds for each turn>]
    python ragent.py --platform PC --chromes explorer.exe,mesdge.exe --interval 10
    ```
    There are several params that you should notice:
    - `--platform`: The platform you are going to run. Now you can run the `PC` demo, the `Mobile` demo will be released in tht future.
    - `--apps`: The chrome names displayed in the ActivityWatcher. Based on different platforms and types of chromes, the apps' name varies, so we need you to find the app name through the window bucket of ActivityWatcher, and pass them separated in a comma `,`(will update in the future, sorry for the inconvenience.)
    - `--interval`: How often the agent will try to make a offer. Default to 15, the unit is second.
        A host name is the suffix of the default bucket name, e.g. `aw-watcher-windows_<client_hostname>`
    - `--port`: The port where ActivityWatcher holds and monitors, default is `5600`, you don't need to modify it unless you changed the port of the ActivityWatcher.

    If the agent runs successfully, the terminal will show a configuration information and a message of `Demo running Started.`

After that, you can open your chrome and/or vscode, and the agent will start to work.