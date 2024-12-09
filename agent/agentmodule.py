import os
import sys
import json
import logging
import asyncio
import requests
import threading
from functools import partial
from typing import List, Dict, Tuple
from datetime import datetime, timezone
from copy import deepcopy
from abc import ABC, abstractmethod

logger = logging.getLogger('ActiveAgent')

Dialogue = List[Dict[str, str]]
sem = asyncio.Semaphore(16)

import pyperclip
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pynput import keyboard, mouse
from aw_client import ActivityWatchClient
import tenacity
from codelinker import CodeLinker, CodeLinkerConfig
# Load the codelinker.
default_cfg_file = os.path.join(os.path.dirname(__file__), '..', 'private.toml')
if not os.path.exists(default_cfg_file):
    default_cfg_file = os.path.join(os.path.dirname(__file__), 'private.toml')

CL_CFGFILE = os.getenv(key = 'CODELINKER_CFG',
                    default = default_cfg_file)

logger.info(f'Using config file: {CL_CFGFILE}')

if not os.path.exists(CL_CFGFILE):
    raise FileNotFoundError("No Config File Found. Please first set your configuration file by either through environment variable CODELINKER_CFG or refer to readme.")
codelinker_config = CodeLinkerConfig.from_toml(CL_CFGFILE)
codelinker_config.request.default_completions_model = "activeagent"
codelinker_config.request.use_cache = False
codelinker_config.request.save_completions = False

cl = CodeLinker(config = codelinker_config)
model_name = 'activeagent'

from prompt import SYSTEM_PROMPT
from constant import LAZY_UPDATE_INTERVAL_MILISECONDS, HOTKEY_DICT, AUMID

# import the toast library.
if sys.platform == "win32":
    from windows_toasts import InteractableWindowsToaster, Toast, ToastActivatedEventArgs, ToastSelection, ToastInputSelectionBox, WindowsToaster
    # We set some globals here. They include two toasts and one status.
    interactable = InteractableWindowsToaster(applicationText='ActiveAgent', notifierAUMID = AUMID)
    response_toaster = WindowsToaster('ActiveAgent')
    newToast: Toast = None
elif sys.platform == "darwin":
    from mac_notifications import client as Toastclient
else:
    raise NotImplementedError("Unsupported platform")



class AgentCore(object):
    def __init__(self,
                cl: CodeLinker,
                model_name:str):

        self.cl        : CodeLinker          = cl
        self.model_name: str                 = model_name
        self.contexts  : List[Dict[str,str]] = []

    def add_new_event(self, event:str):
        new_turn = {
            'event'        : event,
            'response'     : None,
            'user_feedback': None
        }
        self.contexts.append(new_turn)

    def update_response(self, response:str):
        if len(self.contexts) == 0:
            raise Exception('No event has been added.')

        if self.contexts[-1]['response'] is not None:
            raise Exception('The last event has already been updated.')
        self.contexts[-1]['response'] = response

    def update_feedback(self, feedback:str):
        if len(self.contexts) == 0:
            raise Exception('No event has been added.')

        if self.contexts[-1]['user_feedback'] is not None:
            raise Exception('The last event has already been updated.')
        self.contexts[-1]['user_feedback'] = feedback

    async def reflect(self, operations:List[Dict], screen_shot:List[bytes] = None, remain_content:int = -1) -> str:

        print('start reflecting')
        # Format the contexts into a dialogue.
        messages:Dialogue = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        # Add the histories.
        for idx in range(len(self.contexts) - 1):
            if idx > 0:
                # Add additional user feedback.
                user_content = {
                    "Observation": self.contexts[idx]["event"],
                    "user_feedback": self.contexts[idx - 1]["user_feedback"]
                }
            else:
                user_content = {
                    "Observation": self.contexts[idx]["event"],
                }

            messages.append({"role": "user", "content": json.dumps(user_content)})
            messages.append({"role": "assistant", "content": self.contexts[idx]["response"]})

        user_content = {
            "Observation": self.contexts[-1]["event"],
            "Instructions": "Now analyze the history events and provide a task if you think the user needs your help using the given format.",
            "Operations": operations
        }
        if len(self.contexts) >= 2:
            user_content["user_feedback"] = self.contexts[-2]["user_feedback"]

        messages.append(
            {"role": "user",
            "content": json.dumps(user_content)
            })

        # remove the previous user input.
        if remain_content > 0:
            for index in range(len(messages) - 1, -1, -1):
                if messages[index]['role'] == 'assistant':
                    continue
                if remain_content > 0:
                    remain_content -= 1
                    continue
                messages[index]['content'] = 'The user is interacting with the android.'
            pass


        with open('reflect.json','a',encoding='utf-8') as f:
            f.write(json.dumps(messages, ensure_ascii=False, indent=4,separators=(',', ':')) + '\n')

        async for attemp in tenacity.AsyncRetrying(stop=tenacity.stop_after_attempt(5),reraise=True):
            with attemp:
                async with sem:
                    res = await self.cl.exec(
                        model = self.model_name,
                        messages = messages,
                        completions_kwargs={"temperature":0.0 if attemp.retry_state.attempt_number < 1 else 0.5}
                        )

        return res

    async def generate_response(self, prompt:str) -> str:
        # For some reasons I have to reserve this.
        async with sem:
            res = await self.cl.exec(
                model              = self.model_name,
                return_type        = str,
                messages           = [{"role" : "user", "content": prompt}],
                completions_kwargs = {"temperature": 0.0})
        return res

    async def summary_context(self) -> None:
        # TODO: Add a summary to shorten the contexts for long time use.
        pass
        # Collect the user's preference.
        # concat the event observations.
        # Let the agent summarize the context. Adding it in the new turn.

def read_text_from_file(filepath:str, pages:int = 3) -> str:
    full_path = filepath
    import time
    time.sleep(1)

    # if not os.path.isfile(full_path):
    #     raise FileNotFoundError(f"File {filepath} not found in workspace.")
    # if not os.path.exists(full_path):
    #     raise FileNotFoundError(f"File {filepath} not found in workspace.")


    if filepath.endswith(".pdf"):
        from PyPDF2 import PdfReader

        reader = PdfReader(full_path)
        content = ''
        for page in reader.pages[:pages]:
            content += page.extract_text()
        return content

    # if filepath.endswith(".pdf"):
    #     import fitz
    #     doc = fitz.open(filepath)
    #     content = ''
    #     for page_num in range(min(pages, len(doc))):
    #         page = doc.load_page(page_num)
    #         text = page.get_text()
    #         content += text
    #     return content

    if filepath.endswith(".docx"):
        import docx
        doc = docx.Document(full_path)
        content = ''
        for para in doc.paragraphs[:pages]:
            content += para.text
        return content

    if filepath.endswith((".txt",".md")):
        with open(full_path, 'r') as f:
            content = f.read()
        return content

class Trigger(ABC):
    """
    A Trigger will be able to receive the content from the agent and pass it to the user.
    There are two main methods:
    - receive(): receive the content from the agent and store it.
    - send(): send the content to the user in a proper way.
    """

    @abstractmethod
    def receive(self, *args, **kwargs) -> None:
        """
        receive the content from the agent and store it.
        Args:
            infos (Any): information needed in any possible form.
        """
        pass

    @abstractmethod
    def send(self):
        """
        The action to send something from the agent to the user.
        """
        pass


class ActionListener(object):
    def __init__(self,
                chrome_apps:List[str],
                aw_client       : ActivityWatchClient,
                interval_seconds: int = 10,
                watched_path:List[str] = []
                ):

        # Aw client: client_hostname web_bucket_name app_names listen_port
        # Aw related.
        self.aw_client = aw_client
        self.chrome_apps = chrome_apps
        # data storages:
        # Contain the raw events. These events will be filtered and recorded in event_data
        self.raw_events      :List[Dict] = []
        self.event_data      :List[Dict] = []
        self.file_watch_events:List[Dict] = []
        # Record the whole string that user typed.(alphabet only now)
        self.text_content    :str = ""
        # Record the mouse position.
        self.pos  :Tuple[int,int] = None
        # Record the movement of the mouse.
        self.delta:Dict [str,int] = {"scrollX": 0, "scrollY": 0}

        # listen to keyboard and mouse.
        self.interval_seconds:int        = interval_seconds
        # listen to the press and relase event from keyboard.
        self.keyboard_listener = keyboard.Listener(
            on_press   = self.on_press,
            on_release = self.on_release
        )
        # listen to the move and click event from mouse.
        self.mouse_listener = mouse.Listener(
            # on_move   = self.on_move,
            on_click  = self.on_click
        )
        self.move_timer:threading.Timer  = None
        self.scroll_timer = None
        # Record the time period.
        self.last_post_time:datetime = None

        self.observer = Observer()

        class Watcher(FileSystemEventHandler):
            def __init__(self,linstener:ActionListener):
                self.listener = linstener
            def on_created(self, event):
                if not event.is_directory:
                    if event.src_path.endswith(('.pdf',"docx","txt","md","html")):
                        self.listener.file_watch_events.append({
                            "from": "filesystem",
                            "type": "create",
                            "time": datetime.now(tz=timezone.utc).timestamp(),
                            "data": {
                                "note": "A new file is created. Maybe you can rename it according to the content if it's name makes no sense. Rename with the same langugae as the file content. The name should contain the key words of the content. Such as `Invoice-{item_or_service_name}-{id}-{cost}.pdf` for an invoice PDF file.",
                                "path": event.src_path,
                                "content": read_text_from_file(event.src_path)[:1024] + "...TOO LONG TO DISPLAY"
                            }
                        })
                        print("*************** File Created ***************")
                        print(event.src_path)

        watcher = Watcher(self)
        for path in watched_path:
            self.observer.schedule(watcher, path, recursive=True)

    def __exit__(self):
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        self.observer.stop()

    def reset_data(self):
        """
        reset all the stored data.
        """
        self.raw_events.clear()
        self.event_data.clear()
        self.file_watch_events.clear()
        self.text_content = ""

    def send_data(self) -> dict:
        """
        Returns:
            Dict: a event dict containing:
            {
                "timestamp": (float),
                "duration": (int),
                "user_input": (str),
                "hot-keys": List[dict],
                "status": Literal ['afk'/'not-afk'],
                "app": (str),
                "info": None/Dict
            },
        """
        current_time = datetime.now(timezone.utc)
        start_time = self.last_post_time
        all_buckets = list(self.aw_client.get_buckets())

        def get_top_event(bucket_name:str, start, end):
            events = self.aw_client.get_events(bucket_id = bucket_name, start = start, end = end)
            if len(events) > 0:
                return [events[0].to_json_dict()]
            else:
                return []

        def get_full_events(bucket_name:str, start, end, bucket_type:str):
            events = self.aw_client.get_events(bucket_id = bucket_name, start = start, end = end)
            if events == []:
                return []
            events = [event.to_json_dict() for event in events[-1::-1]]

            structured_events = [events[0]]

            match bucket_type:
                # For AFK event, we merge the events with the same status.
                case "afk":
                    for event in events[1:]:
                        if event["data"]["status"] == structured_events[-1]["data"]["status"]:
                            structured_events[-1]["duration"] += event["duration"]
                        else:
                            structured_events.append(event)
                # For window event, we ignore those 'unknown' apps, and get the changes of the apps by listing all the titles.
                case "window":
                    # Filter the events with unknown app.
                    events = [event for event in events if event["data"]["app"] != "unknown"]
                    if events == []:
                        return []
                    structured_events = [events[0]]
                    # Change str to list.
                    structured_events[-1]["data"]["title"] = [structured_events[-1]["data"]["title"]]

                    for event in events[1:]:
                        if event["data"]["app"] == structured_events[-1]["data"]["app"]:
                            structured_events[-1]["duration"] += event["duration"]
                            structured_events[-1]["data"]["title"].append(event["data"]["title"])
                        else:
                            structured_events.append(event)
                            structured_events[-1]["data"]["title"] = [structured_events[-1]["data"]["title"]]
                # For vscode event, we merge the events under the same project. other information will be set in 'sequence' attribute.
                case 'vscode':
                    events = [event for event in events if event["data"]["file"] != "unknown"]
                    if events == []:
                        return []

                    structured_events = [events[0]]
                    structured_events[-1]["data"] = {
                        "project": structured_events[-1]["data"]["project"],
                        "sequence":[
                            {
                                "file": structured_events[-1]["data"]["file"],
                                "language": structured_events[-1]["data"]["language"]
                            }
                        ]
                    }

                    for event in events[1:]:
                        if event["data"]["project"] == structured_events[-1]["data"]["project"]:
                            structured_events[-1]["duration"] += event["duration"]
                            structured_events[-1]["data"]["sequence"].append({
                                "file": event["data"]["file"],
                                "language": event["data"]["language"]
                            })
                        else:
                            structured_events.append(event)
                            structured_events[-1]["data"] = {
                                "project": structured_events[-1]["data"]["project"],
                                "sequence":[
                                    {
                                        "file": structured_events[-1]["data"]["file"],
                                        "language": structured_events[-1]["data"]["language"]
                                    }
                                ]
                            }
                # We only collect the url, title, innerText of the web. We don't merge the same url. But give a update if new text arise.
                # Notice that due to the limitation of the extension, we can not update the content in real time, we ignore the difftext.
                case 'web':
                    events = [event for event in events if event["data"]["url"] != ""]
                    if events == []:
                        return []
                    structured_events = [events[0]]
                    structured_events[-1]["data"] = {
                        "url": structured_events[-1]["data"]["url"],
                        "title": structured_events[-1]["data"]["title"],
                        "innerText": structured_events[-1]["data"].get("innerText", "")
                    }

                    for event in events[1:]:
                        if event["data"].get("innerText", "") != "":
                            structured_events.append(event)
                            structured_events[-1]["data"] = {
                                "url": structured_events[-1]["data"]["url"],
                                "title": structured_events[-1]["data"]["title"],
                                "innerText": structured_events[-1]["data"].get("innerText", "")
                            }
                # For those we do not support yet, we just return the raw data.
                case __:
                    structured_events = events

            return structured_events


        event_chrome:Dict[str, List] = {}
        event_others:Dict[str, List] = {}

        for bucket in all_buckets:
            match bucket:
                # # get afk informations.
                case afk if "afk" in afk:
                    event_afk = get_full_events(afk, start_time, current_time, 'afk')

                case window if 'window' in window:
                    event_windows = get_full_events(window, start_time, current_time, 'window')

                case vscode if "vscode" in vscode:
                    event_vscode = get_full_events(vscode, start_time, current_time, 'vscode')

                case web if "web" in web:
                    chrome_type = web.split('-')[-1]
                    # avoid too may inforamtion crush the agent.
                    event_chrome[chrome_type] = get_top_event(web, start_time, current_time)
                    # print(web, event_chrome)

                case __:
                    # most types can be stripped from the last part.
                    app_type = bucket.split('-')[-1]
                    event_others[app_type] = get_full_events(bucket, start_time, current_time, bucket.split('-')[-1])

        # We would like to check those apps and attach related information.
        apps_showed = set([event["data"]["app"] for event in event_windows])
        attached_info = {}

        if "Code.exe" in apps_showed or "Code" in apps_showed:
            attached_info["vscode"] = event_vscode

        for app in self.chrome_apps:
            if app in apps_showed:
                attached_info["chromes"] = event_chrome

        if len(self.file_watch_events) > 0:
            attached_info["files"] = deepcopy(self.file_watch_events)

        # Other apps are now not supported and being ignored.
        result_event = {
            "timestamp": start_time.timestamp(),
            "duration": self.interval_seconds,
            "user_input": self.text_content,
            "hot-keys": list(filter(lambda x:"hot_key" in x["data"].keys(), self.event_data)), # add those hot keys.
            "status": event_afk if event_afk != [] else None,
            "apps": event_windows if event_windows != [] else None,
            "info": attached_info
        }

        print(result_event)

        self.last_post_time = current_time
        self.reset_data()

        # info_str = json.dumps(,ensure_ascii=False)
        return result_event

    def push_event(self, event:Dict):
        """
        Push an filtered event into the event_data bucket.
        Args:
            event (Dict): The filtered event.
        """
        self.event_data.append(event)

    def start(self):
        """
        Start the listener by activate keyboard listener, mouse listener and start the timer.
        Note the timezone of our data is UTC.
        """
        self.keyboard_listener.start()
        self.mouse_listener.start()
        self.observer.start()
        self.last_post_time = datetime.now(timezone.utc)

    def on_move(self, x:int, y:int):
        """
        Track the mouse movement.
        Record the data as:
        {
            "from": "mouse",
            "type": "move",
            "time": (timestamp),
            "data": {
                "x": x,
                "y": y
            }
        }

        Args:
            x (int): the x position of the mouse
            y (int): the y position of the mouse
        """

        if self.pos is None:
            self.pos = (x, y)

        def lazy_move_update():
            self.push_event({
                "from": "mouse",
                "type": "move",
                "time": datetime.now(tz=timezone.utc).timestamp(),
                "data": {
                    "x":self.pos[0],
                    "y":self.pos[1]
                }
            })
            del self.move_timer
            self.move_timer = None

        if self.move_timer is None:
            self.move_timer = threading.Timer(LAZY_UPDATE_INTERVAL_MILISECONDS, lazy_move_update,)
            self.move_timer.start()

    def on_click(self, x:int, y:int, button:mouse.Button, pressed:bool):
        """
        Track the click activity of the mouse.
        Record the data as:
        {
            "from": "mouse",
            "time": (timestamp),
            "duration": (float) how long the click continues,
            "data": {
                "type": "click",
                "button": button.name,
            }
        }

        Args:
            x (int): the x position of the mouse
            y (int): the y position of the mouse
            button (mouse.Button): left/right/middle key of the mouse.
            pressed (bool): true if keydown, and false when keyup.
        """
        # press down the button. Record to the raw events.
        if pressed:
            self.raw_events.append({
                "from": "mouse",
                "type": "click",
                "time": datetime.now(tz=timezone.utc).timestamp(),
                "data": {
                    "x": x,
                    "y": y,
                    "button": button.name,
                    "down": pressed
                }
            })
            return
        # release the button. Push the event.
        down_event = list(filter(lambda x:  x["from"] == "mouse" and\
                    x["type"] == "click" and\
                    x["data"]["button"] == button.name and \
                    x["data"]["down"],
                    self.raw_events))
        if len(down_event) > 0:
            down_event = down_event[0]
            self.raw_events.remove(down_event)
            self.push_event(
                {
                    "from": "mouse",
                    "time": down_event["time"],
                    "duration": (datetime.now(tz=timezone.utc).timestamp() - down_event["time"]),
                    "data": {
                        "type": "click",
                        "button": button.name,
                    }
                }
            )

    # Have Bug to fix.
    def on_scroll(self, x:int, y:int, scrollx:int, scrolly:int):
        """
        Track the scroll activity of the mouse.
        Record the data as:
        {
            "from": "mouse",
            "type": "scroll",
            "time": (timestamp),
            "data": {
                "x": x,
                "y": y,
                "scrollx": scrollx,
                "scrolly": scrolly
            }
        }

        Args:
            x (int): the x position.
            y (int): the y position.
            scrollx (int): the move length on direction x.
            scrolly (int): the move length on direction y.
        """

        def lazy_push():
            if self.delta["scrollX"] != 0 or self.delta["scrollY"] != 0:
                self.push_event({
                    "from": "mouse",
                    "type": "scroll",
                    "time": datetime.now(tz=timezone.utc).timestamp(),
                    "data": {
                        "x": x,
                        "y": y,
                        "scrollx": self.delta["scrollX"],
                        "scrolly": self.delta["scrollY"]
                    }
                })
            self.delta["scrollX"] = 0
            self.delta["scrollY"] = 0
            del self.scroll_timer
            self.scroll_timer = None

        if self.pos is None:
            if x != self.pos[0] or y != self.pos[1]:
                if self.scroll_timer is not None:
                    self.scroll_timer.cancel()
                    del self.scroll_timer
                    self.scroll_timer = None
                lazy_push()

        self.delta["scrollX"] += scrollx
        self.delta["scrollY"] += scrolly
        if self.scroll_timer is None:
            self.scroll_timer = threading.Timer(LAZY_UPDATE_INTERVAL_MILISECONDS, lazy_push,)
            self.scroll_timer.start()

    def on_press(self, key: keyboard.KeyCode):
        """
        Track the key press activity of the keyboard.
        We collect most of the keys from press event, including all single keys.
        Record the data as:
        {
            "from": "keyboard",
            "type": "press",
            "time": (timestamp),
            "data": {
                "key": key.name,
            }
        }

        Args:
            key (keyboard.KeyCode): the key.
        """

        if hasattr(key, "char") and key.char != None:

            key_info = key.char
            key_code = key.char

        elif hasattr(key, "name"):

            key_info = key.name
            if key == keyboard.Key.space:
                key_code = " "
            elif key == keyboard.Key.enter:
                key_code = "\n"
            # reserve the backspace key, let the agent know you are deleting.
            elif key == keyboard.Key.backspace:
                key_code = "\b"
            else:
                key_code = ""

        else:
            key_code = ""
            key_info = "unknown"
        # add it to the text content
        self.text_content += key_code
        self.push_event({
            "from": "keyboard",
            "type": "press",
            "time": datetime.now(tz=timezone.utc).timestamp(),
            "data": {
                "key": key_info
            }
        })

    def on_release(self, key: keyboard.KeyCode):
        """
        Track the key release activity of the keyboard.
        Most of the key are collected from press event, but the hot-keys and some special keys are collected from release event.
        Record the data as
        {
            "from": "keyboard",
            "type": "press",
            "time": (timestamp),
            "data": {
                "hot_key": key.name,
            }
        }

        Args:
            key (keyboard.KeyCode): _description_
        """

        key_code = '{}'.format(key)

        if key_code in HOTKEY_DICT.keys():
            self.push_event({
                "from": "keyboard",
                "type": "press",
                "time": datetime.now(tz=timezone.utc).timestamp(),
                "data": {
                    "hot_key": "+".format(HOTKEY_DICT[key_code])
                }
            })
            # Especially for copy event, we will read the content from the clipboard.
            if key_code == r"'\x16'":
                paste_str = pyperclip.paste()
                self.text_content += paste_str

class Executor(Trigger):
    '''
    This compoment will execute some actions based on the agent's result.
    '''
    def __init__(self):

        config = codelinker_config.get_apiconfig_by_model('activeagent')

        self.model = config.model
        self.api_key = config.api_key
        try:
            self.base_url = config.base_url
        except:
            self.base_url = None

    def receive(self, response:Dict, exec_args:Dict):

        self.response = response
        self.exec_args = exec_args

    def send(self):
        # The original response from the agent.
        response = self.response
        # The args including the event and the tool call format.
        action_labels = self.exec_args

        if sys.platform == "win32":
            # For windows user, we will use windows_toaster to notify the user.
            # Define the action where the user accepts the proposal.
            def activated_callback(activatedEventArgs: ToastActivatedEventArgs):
                # We dont' really need to pass the args here (for single cases.)
                global status, response_toaster
                status = 'The user accepts the last proposal from you.'

                # Load the params.
                infos = self.exec_args

                logger.debug(infos)
                func_call = infos['func_call']
                # Get the function name and function params, transform params as a dict.
                func_infos = func_call.split('&')
                func_name = func_infos[0]
                func_params = {k:v for k,v in (param.split('=') for param in func_infos[1:])}

                logger.debug(f'Function name {func_name}; Function origin params {func_params}.')

                # For each tool, we use different approches.
                match func_name:
                    case 'search':
                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()
                    # For chat we will update the api config and the backgrounds to the params.
                    case 'chat':
                        func_params.update({
                            'api_key' : self.api_key,
                            'model' : self.model,
                            'base_url': self.base_url,
                            'messages': json.dumps(infos["events"])})

                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()

                        if response['status'] == 'success':
                            notifier_toast = Toast(text_fields=['response copied in clipboard.'])
                            response_toaster.show_toast(notifier_toast)

                    # For read, we simply pass it.
                    case 'read':
                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()
                        # TODO: Need a update.
                        if response['status'] == 'success':
                            prompt = \
"""You are a helpful assistant, currently you are dealing with contents in a file.
Here is the background {target}.
Here is the content of the file: {content}
Please accomplish the proposal raised by the agent.""".format(target = infos, content = response['content'])

                            new_params = {'api_key':self.api_key, 'base_url':self.base_url, 'messages':prompt}
                            __ = requests.get('http://127.0.0.1:8000/chat',params = new_params)
                            notifier_toast = Toast(text_fields=['Feedback saved in copyboead.'])
                            response_toaster.show_toast(notifier_toast)

                    case __:
                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()



            # For dismiss cases, we change the status to notify the agent.
            def dismiss_callback(dismissedEventArgs):
                global status
                status = 'The user REJECT the last proposal from you. consider propose in another way or do not disturb the user.'

            # For now, we will assemble a toast.
            global interactable, newToast
            # create the toast.
            newToast = Toast(text_fields=[self.response["Response"]], on_activated = activated_callback, on_dismissed = dismiss_callback)
            # add the button.
            toastSelections = tuple(
                ( ToastSelection(selection_id = '_', content = res["Proactive_Task"]) for res in [self.response] )
            )

            selectionBoxInput = ToastInputSelectionBox('action', 'My Assistance', toastSelections, default_selection=toastSelections[0])
            newToast.AddInput(selectionBoxInput)
            interactable.show_toast(newToast)

        # MacOS still indevelopment.
        # The format of the params can be seen in function signature.
        else:
            def activated_callback():
                print('>' * 80)
                global status
                status = 'The user accepts the last proposal from you.'
                infos = self.exec_args
                func_call_str = infos['func_call']
                # parsing the arguments into function name and parameters
                func_infos = func_call_str.split('&')
                # Get the function name.
                func_name = func_infos[0]
                # Get the parameters as a dictionary.
                func_params = {k:v for k,v in (param.split('=') for param in func_infos[1:])}
                # For the chat (completion) function, add the api_key and base_url.

                logger.debug(f'Function name {func_name}; Function origin params {func_params}.')

                match func_name:
                    case 'search':
                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()
                    # For chat we will update the api config and the backgrounds to the params.
                    case 'chat':
                        func_params.update({
                            'api_key' : self.api_key,
                            'base_url': self.base_url,
                            'messages': json.dumps(infos["events"])})

                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()

                        if response['status'] == 'success':
                            Toastclient.create_notification(
                                title    = "Active Agent",
                                subtitle = "Response copied in clipboard."
                            )
                    # For read, we simply pass it.
                    case 'read':
                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()
                        # TODO: Need a update.
                        if response['status'] == 'success':
                            prompt = \
"""You are a helpful assistant, currently you are dealing with contents in a file.
Here is the background {target}.
Here is the content of the file: {content}
Please accomplish the proposal raised by the agent.""".format(target = infos, content = response['content'])

                            new_params = {'api_key':self.api_key, 'base_url':self.base_url, 'messages':prompt}
                            __ = requests.get('http://127.0.0.1:8000/chat',params = new_params)
                            Toastclient.create_notification(
                                title    = "Active Agent",
                                subtitle = "Response copied in clipboard."
                            )

            # Propose the candidates to choose.
            print('What wrong for proposal?')
            Toastclient.create_notification(
            title             = "Active Agent",
            subtitle          = self.response["Response"],
            icon              = "./icon.ico",
            action_button_str = self.response["Proactive_Task"],
            action_callback   = partial(activated_callback)
        )
