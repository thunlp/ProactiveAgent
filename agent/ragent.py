
import sys
import json
import fire
import requests
import threading
from time import sleep
from functools import partial
from typing import List, Dict, Tuple
from datetime import datetime, timezone

import pyperclip
from pynput import keyboard, mouse
from aw_client import ActivityWatchClient

from codelinker import CodeLinkerConfig
cfg_file = "../gym/private.toml"

codelinker_config = CodeLinkerConfig.from_toml(cfg_file)
model_name = codelinker_config.request.default_completions_model
config = codelinker_config.get_apiconfig_by_model(model_name)



from ActiveAgent import ActiveAgent
from agentmodule import Core, LLMClient, Trigger
from constant import VSCODE_NAME
from constant import LAZY_UPDATE_INTERVAL_MILISECONDS, HOTKEY_DICT
from constant import AUMID
from prompt import MATCH_ACTION_PROMPT

from register import ToolRegister
toolreg = ToolRegister()

if sys.platform == "win32":
    from windows_toasts import InteractableWindowsToaster, Toast, ToastActivatedEventArgs, ToastInputTextBox, ToastButton, ToastSelection, ToastInputSelectionBox, WindowsToaster
    
    # We set some globals here. They include two toasts and one status.
    interactable = InteractableWindowsToaster(applicationText='ActiveAgent', notifierAUMID = AUMID)
    response_toaster = WindowsToaster('ActiveAgent')
    newToast: Toast = None
    
    status:str = 'initial'

elif sys.platform == "darwin":
    from mac_notifications import client as Toastclient

else:
    raise NotImplementedError("Unsupported platform")

class ActionListener(object):
    '''
    This class uses the pynput library to listen to keyboard and mouse events, at a certain interval, it will post all the datas to the event listener.
    '''
    
    def __init__(self, client_hostname:str,
                web_bucket_name:str,
                app_names: List[str],
                interval_seconds:int = 10, 
                listen_port:int = 5600, 
                allow_paste:bool = False,

                ):
        self.raw_events      :List[Dict] = []
        self.event_data      :List[Dict] = []
        self.interval_seconds:int        = interval_seconds
        self.listen_port     :int        = listen_port
        self.allow_paste     :bool       = allow_paste
        self.client_host_name:str        = client_hostname
        self.web_bucket_name :str        = web_bucket_name
        
        
        self.app_names: List[str]        = app_names
        
        
        
        self.text_content    :str = ""
        
        self.pos  :Tuple[int,int] = None
        self.delta:Dict [str,int] = {"scrollX": 0, "scrollY": 0}
        
        self.keyboard_listener = None
        self.mouse_listener    = None
        self.move_timer        = None    
        
        self.last_post_time:datetime = None
        
    def reset_data(self):
        """
        reset the stored data.
        """
        
        self.raw_events.clear()
        self.event_data.clear()
        self.text_content = ""
        
    def send_data(self) -> Dict:
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
        client = ActivityWatchClient(port = self.listen_port)
        hostname = self.client_host_name

        bucket_name = "aw-watcher-{}_" + hostname
        current_time = datetime.now(timezone.utc)
        start_time = self.last_post_time
        
        # All this only form one event. For simplicity, we just use the last event.
        
        # get afk informations.
        event_afk = client.get_events(bucket_id = bucket_name.format("afk"), start = start_time, end = current_time)
        if len(event_afk) > 0:
            event_afk = event_afk[0]
        
        # print(event_afk)
        
        # get application-level information.
        event_windows = client.get_events(bucket_id = bucket_name.format("window"), start = start_time, end = current_time)
        if len(event_windows) > 0:
            event_windows = event_windows[0]

        # get vscode information
        event_vscode = client.get_events(bucket_id =  bucket_name.format("vscode"), start = start_time, end = current_time)
        
        if len(event_vscode) > 0:
            event_vscode = event_vscode[0]

        # get chrome information
        event_chrome = client.get_events(bucket_id = self.web_bucket_name, start = start_time, end = current_time)
        
        if len(event_chrome) > 0:
            event_chrome = event_chrome[0]
        
        event = {
            "timestamp": start_time.timestamp(),
            "duration": self.interval_seconds,
            "user_input": self.text_content,
            "hot-keys": list(filter(lambda x:"hot_key" in x["data"].keys(), self.event_data)),
            "status": event_afk["data"]["status"] if event_afk != [] else None,
            "app": event_windows["data"]["app"] if event_windows != [] else None,
            "info": None
        }
        # json -> 自然语言
        
        if event["app"] == VSCODE_NAME:
            event["info"] = event_vscode["data"] if event_vscode != [] else None
            
        elif event["app"] in self.app_names:
            event["info"] = event_chrome["data"] if event_chrome != [] else None
            
        # print(event)
            
        # info_str = json.dumps(event)
        
        self.last_post_time = current_time
        
        self.reset_data()
        
        return event
    
    def push_event(self, event:Dict):
        self.event_data.append(event)
        
    def start(self):
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click)
        
        self.keyboard_listener.start()
        self.mouse_listener.start()
        self.last_post_time = datetime.now(timezone.utc)
    
    def on_move(self, x:int, y:int):
        """
        function to call when mouse move.
        
        Send data as
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
            x (int): 
            y (int): 
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
        called when mouse clicks.
        
        Send data as
        {
            "from": "mouse",
            "time": (timestamp),
            "duration": (float),
            "data": {
                "type": "click",
                "button": button.name,
            }
        }

        Args:
            x (int): 
            y (int): 
            button (mouse.Button): 
            pressed (bool): 
        """
        
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
        else:
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
            
    def on_scroll(self, x:int, y:int, scrollx:int, scrolly:int):
        """
        Called when the mouse scroll.
        Send data as
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
            x (int): _description_
            y (int): _description_
            scrollx (int): _description_
            scrolly (int): _description_
        """
        
        def lazy_push():
            if self.delta["scrollX"] != 0 or self.delta["scrollY"]!=0:
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
            if x != self.pos[0] or y!= self.pos[1]:
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
        Called when a key is pressed.
        Note that we get the key from press event rather than release event.
        Send data as
        {
            "from": "keyboard",
            "type": "press",
            "time": (timestamp),
            "data": {
                "key": key.name,
            }
        }

        Args:
            key (keyboard.KeyCode): _description_
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
            elif key == keyboard.Key.backspace:
                key_code = "\b"
            else:
                key_code = ""
                
        else:
            key_code = ""
            key_info = "unknown"
                
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
        Called when a key is released. Though the release event is not record.
        Some special keys and hot keys are handled here.
        Send data as
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
            
            if self.allow_paste and key_code == r"'\x16'":
                paste_str = pyperclip.paste()
                self.text_content += paste_str
                
class RestrictedCore(Core):
    
    def __init__(self,client):
        super().__init__(client)
        
    def describe_event(self, event:dict) -> str:
        """
        This function is used to transform the event dict to a statement, which is friendly for the agent.
        This function is used for ragent.

        Args:
            event (dict): the raw data generated from ActionListener.

        Returns:
            str, the string that describes the event.
        """
        prompt = f"""
        You are a data expert, here is a event written in json, what you need to do is to transform it into a statement without loss of information. You only need to output the sentence describing the event, do not output any other information.
        {event}
        """
        return self.generate_response(prompt)
    
    def classify_candidates(self,candidates:list):
        """
        This function is used to match the candidates with tools registered in toolreg.
        This function is provided for ragent.

        Args:
            candidates (list[str]): the list of candidates.
            background_info (str, optional): the past events for the user. Defaults to "".

        Returns:
            str: typically be a list containing the matched tools for respective candidates, the params were separated by comma '&'
        """
        
        prompt = MATCH_ACTION_PROMPT.format(candidates = candidates, tools = toolreg.get_all_tools_dict())
        response = self.generate_response(prompt)
        
        if response[0] != '[':
            lb = response.find('[')
            rb = response.find(']')
            
            response = response[lb : rb + 1]
            
        return response
    
    
class RestrictedTrigger(Trigger):
    '''
    This compoment will execute some actions based on the agent's result.
    '''
    def __init__(self):
        
        global  config
    
        self.model = config.model
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.header = ''
        
    def receive(self, response:dict, action_labels:list[Dict] = None):
        
        self.response = response
        self.action_labels = action_labels

    def send(self):
        """
        
        FYI: The format of the response be like
        {
            "purpose":(str),
            "profile":(str),
            "need_help":(str)
            "raise_query": (str)
            "candidate_task": List[str] (only one candidate in list now.)
        }
        
        action_labels: List[func_name&param1=value1&param2=value2...] (only one candidate in list now.)
        (you may view the format of action_labels in debug.txt once run the program.)
        """
        
        response = self.response
        action_labels = self.action_labels

        
        if sys.platform == "win32":
            # For windows user, we will use windows_toaster to notify the user.
            # Define the action where the user accepts the proposal.
            def activated_callback(activatedEventArgs: ToastActivatedEventArgs):
                # params we passed in is stored in the key 'action'. it is a json in string with a format as:
                # {'events': event, 'func_call': toolname&arg1=value1&arg2=value2&...}
                
                global status, response_toaster
                
                status = 'The user accepts the proposal from you.'

                # Load the params.
                infos = json.loads(activatedEventArgs.inputs['action'])
                func_call = infos['func_call']
                # Get the function name and function params, transform params as a dict.
                func_infos = func_call.split('&')
                func_name = func_infos[0]
                func_params = {k:v for k,v in (param.split('=') for param in func_infos[1:])}
                
                # print(func_name, func_params)
                
                # For each tool, we use different approches.
                match func_name:
                    # For chat we will update the api config and the backgrounds to the params.
                    case 'chat':
                        func_params.update({
                            'api_key' : self.api_key, 
                            'base_url': self.base_url,
                            'messages': json.dumps(infos)})
                        
                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()
                        
                        if response['status'] == 'success':
                            notifier_toast = Toast(text_fields=['response copied in clipboard.'])
                            response_toaster.show_toast(notifier_toast)
                    
                    # For read, we simply pass it.
                    case 'read':
                        response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                        response = response.json()
                        
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
            
            
            # For dismiss cases, we change the status to notify the agent.
            def dismiss_callback(dismissedEventArgs):
                global status
                status = 'The user REJECT the last proposal from you. consider propose in another way or do not disturb the user.'

            # For now, we will assemble a toast.
            global interactable, newToast
            # create the toast.
            newToast = Toast(text_fields=[response["raise_query"]], on_activated = activated_callback, on_dismissed = dismiss_callback)
            # add buttons.
            params = [f"{json.dumps(action)}"for action in action_labels]
            toastSelections = tuple(
                ( ToastSelection(f"{param}", res) for res, param in zip(response["candidate_task"], params) )) 
            selectionBoxInput = ToastInputSelectionBox('action', 'How can I help you?', toastSelections, default_selection=toastSelections[0])
            newToast.AddInput(selectionBoxInput)
            interactable.show_toast(newToast)

        # MacOS still indevelopment.
        # The format of the params can be seen in function signature.
        else:
            def activated_callback(func_call_str:str):
                
                infos = json.loads(func_call_str)
                
                func_call_str = infos['func_call']

                # parsing the arguments into function name and parameters
                func_infos = func_call_str.split('&')
                # Get the function name.
                func_name = func_infos[0]
                # Get the parameters as a dictionary.
                func_params = {k:v for k,v in (param.split('=') for param in func_infos[1:])}
                # For the chat (completion) function, add the api_key and base_url.
                
                print(func_name, func_params)
                
                if func_name == 'chat':
                    func_params.update({'api_key':self.api_key, 'base_url':self.base_url})
                    func_params.update({'messages':json.dumps(infos)})

                # Call the function by fastAPI.
                response = requests.get(f'http://127.0.0.1:8000/{func_name}',params=func_params)
                # Get the response from the fastAPI server. Now is the status of the request.
                response = response.json()

                # For chat function, the content will be copied in clipboard.
                if func_name == 'chat' and response['status'] == 'success':

                    Toastclient.create_notification(
                        title    = "Active Agent",
                        subtitle = "Response copied in clipboard."
                    )

                # For read function(filesystem), use gpt-3.5 to make a completion additionaly (use the content read to do the target.)
                if func_name == 'read' and response['status'] == 'success':

                    prompt = """
                    You are a helpful assistant, currently you are dealing with contents in a file. 
                    Here is your target {target}.
                    Here is the content of the file: {content}

                    Please accomplish the target.
                    """.format(target = func_infos[-1], content = response['content'])

                    new_params = {'api_key':self.api_key, 'base_url':self.base_url, 'messages':prompt}

                    new_response = requests.get('http://127.0.0.1:8000/chat',params = new_params)

                    # Copied in the clipboard.
                    Toastclient.create_notification(
                        title    = "Active Agent",
                        subtitle = "Response copied in clipboard."
                    )

            # Propose the candidates to choose.
            Toastclient.create_notification(
            title             = "Active Agent",
            subtitle          = response["raise_query"],
            icon              = "./icon.ico",
            action_button_str = response["candidate_task"][0],
            action_callback   = partial(activated_callback, json.dumps(action_labels[0]))
        )

class RestrictedAgent(ActiveAgent):
    
    def __init__(self, client:LLMClient, 
                *args, **kwargs):
        
        super().__init__(client = client)
        self.interval_seconds = kwargs["interval_seconds"]
        self.core:RestrictedCore = RestrictedCore(client = client)
        self.actionListner = ActionListener(**kwargs)
        self.trigger:RestrictedTrigger = RestrictedTrigger()
        
    def generating_proposal(self, interval):
        """
        Function rewrite the proposal generation process. Unlike `run_single_turn` in ActiveAgent.
        Args:
            addition_infos (str, optional): Control the generation type of the proposal.
        """
        
        global status
        
        single_event = self.actionListner.send_data()
        
        if status != 'initial' or status != 'undefined':
            single_event["proposal_feedback"] = status
            status = 'undefined'
        # Single Event will add the user's response.
        
        # debug: check the overall data.
        print(single_event)
        
        single_event = json.dumps(single_event)
        
        self.contextManager.add_event(single_event)
        
        response = self.core.reflect(self.contextManager.get_all_turns())
        # print(response)
        
        self.contextManager.update_response(json.dumps(response))

        if response['candidate_task'] == []:
            return

        func_call = self.core.classify_candidates(response['candidate_task'])
        # 
        try:
            func_call = eval(func_call)
        except:
            print(func_call)
            return
        infos = [{"events":single_event, "func_call": func} for func in func_call]

        self.trigger.receive(response, infos)
        self.trigger.send()
        
        sleep(interval - 2)
        
        # Remove the toast if the user ignores, and change the status.
        global interactable, newToast
        interactable.remove_toast(newToast)
        if status == 'undefined' or status == 'initial':
            status = 'The user ignores your last proposal, consider propose less to not disturb the user.'
            print(status)
        # Add the sleep time.
        sleep(2)

    def run(self):

        self.actionListner.start()

        print('Demo running Started.')

        while True:
            self.generating_proposal(self.interval_seconds)
            sleep(self.interval_seconds)
            
def main(apps:List[str], web:str, host:str = None, interval:int = 15, activity_port:int = 5600):
    model = config.model
    api_key = config.api_key
    base_url = config.base_url
    apps = apps.split(',')
    
    client = ActivityWatchClient(port = activity_port)
    if host is None:
        host = client.client_hostname
        
    CONFIG_INFO = \
f'''
Activity Watcher Configuration:
- Activity port: {activity_port}.
- Assistance Interval: {interval} seconds.
- Reading Chromes from: {apps}.
- Reading vscode content from: {VSCODE_NAME}.
- Reading buckets from:
    - aw-watcher-afk_{host}
    - aw-watcher-window_{host}
    - {web}
    - aw-watcher-vscode_{host}.
'''

    print(CONFIG_INFO)
    
    client = LLMClient(api_key= api_key,model_name=model, base_url=base_url)
    
    agent = RestrictedAgent(client = client,
                            interval_seconds = interval,
                            listen_port = activity_port,
                            client_hostname = host,
                            web_bucket_name = web,
                            app_names = apps)

    agent.run()

if __name__ == '__main__':
    fire.Fire(main)


