'''
This file provide three distinct components:
1. Environment: The platform which we are interacting with. (PC and Android)
2. Trigger: How we will actually execute the command.
3. Agent: Get the observation from the environment and generate the action.
'''
import io
import os
import json
import base64
import asyncio
import logging
import traceback
import threading
import subprocess
from typing import Iterable, Literal, Optional, Dict, List

import colorlog
from PIL import Image
from codelinker import CodeLinker, CodeLinkerConfig, EventProcessor, EventSink
from codelinker.models import SEvent, ChannelTag


from channels import sc
from agentmodule import ActionListener, Executor, ActivityWatchClient
from prompt import SYSTEM_PROMPT
from constant import AgentResponse
from constant import MAX_TRANSFER_SIZE, TIMEOUT, BUFFER_SIZE

from register import ToolRegister
toolreg = ToolRegister()
img_base64 = None

# Set the logger format.
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = colorlog.ColoredFormatter(
    fmt='%(log_color)s%(levelname)s - %(name)s - %(message)s',
                            log_colors={
                                'DEBUG':    'white',
                                'INFO':     'green',
                                'WARNING':  'yellow',
                                'ERROR':    'red',
                                'CRITICAL': 'red,bg_white',
                            })
# formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# load information.
default_cfg_file = os.path.join(os.path.dirname(__file__), '..', 'private.toml')
if not os.path.exists(default_cfg_file):
    default_cfg_file = os.path.join(os.path.dirname(__file__), 'private.toml')

CL_CFGFILE = os.getenv(key = 'CODELINKER_CFG',
                    default = default_cfg_file)

codelinker_config = CodeLinkerConfig.from_toml(CL_CFGFILE)
codelinker_config.request.default_completions_model = "activeagent"
codelinker_config.request.use_cache = False
codelinker_config.request.save_completions = True

clinker = CodeLinker(config = codelinker_config)
eventSink = EventSink(sinkChannels=sc,logger=logger)

class BasicComponent(EventProcessor):
    def __init__(self,name:str):
        super().__init__(name = name,
                        sink = eventSink)
        self.listen(sc.setup)(self.setup)
        self.cl = clinker

    def gather(self,
            tags: ChannelTag | Iterable[ChannelTag] | None = None,
            return_dumper:Literal['identity','json'] = 'identity') -> str | Iterable[dict]:
        messages = super().gather(tags = tags,return_dumper = 'identity')
        match return_dumper:
            case 'identity':
                return messages
            case 'json':
                for msg in messages:
                    o = msg['content']
                    if isinstance(o,SEvent):
                        msg['content'] = json.dumps({
                            "Time": o.time,
                            "Source": o.source,
                            "Tags": o.tags,
                            "Event": o.content
                        },ensure_ascii=False)
                return messages
            case __:
                raise ValueError(f"return_dumper should be 'identity' or 'json', but got {return_dumper}")

class AndroidEnv(BasicComponent):
    def __init__(self, *,
                server_host:str = '0.0.0.0',
                server_port:int = 9999,
                name = "AndroidEnv",):
        """
        Args:
            server_host (str, optional): the IP of the socket connection. Defaults to '0.0.0.0'.
            server_port (int, optional): the port of the socket connection. Defaults to 9999.
            name (str, optional): The name of the environment. Defaults to "AndroidEnv".
        """
        super().__init__(name)

        self.client_count: int = 0
        self.server_host : str = server_host
        self.server_port : int = server_port

        complete_tools:List[Dict] = toolreg.get_all_tools_dict()
        self.tools:List[Dict] = [t for t in complete_tools if 'android' in t["name"]]

    async def setup(self):
        """
        For the set up of the android:
        1. Establish a socket connection and wait a client to connect.
        2. Listen on several channels.
        """
        async def run_server():
            async with server:
                await server.serve_forever()

        self.logger.info("Initializing Android Environment...")
        self.add(sc.agent.operations, content = json.dumps(self.tools), silent = True)

        logger.info("Android socket waiting for connection.")
        server = await asyncio.start_server(self.handle_client, self.server_host, self.server_port, limit = MAX_TRANSFER_SIZE)
        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        logger.info(f'Serving on {addrs}')

        self.server_task = asyncio.create_task(run_server())

        while self.client_count == 0:
            await asyncio.sleep(0.5)

        logger.info("Android socket connected.")
        logger.info("Env setup done.")

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.client_count += 1
        async def read_data():

            while True:
                try:
                    datalen_bytes = await asyncio.wait_for(
                        reader.read(4),
                        timeout=TIMEOUT)
                except asyncio.TimeoutError:
                    logger.info("Timeout waiting for data length. Closing connection.")
                    continue

                if not datalen_bytes:
                    logger.info("Received empty message. Closing connection.")
                    await asyncio.sleep(1)
                    continue

                datalen:int = int.from_bytes(datalen_bytes, byteorder='big')
                logger.info(f"Received data length: {datalen}")
                msg:bytes = b''

                while datalen > 0:
                    try:
                        data = await asyncio.wait_for(reader.read(min(BUFFER_SIZE, datalen)), timeout=TIMEOUT)
                    except asyncio.TimeoutError:
                        print("Timeout waiting for data chunk. Closing connection.")
                        break

                    if not data:
                        break
                    datalen -= len(data)
                    msg += data

                try:
                    msg_str:str = msg.decode('utf-8')
                except UnicodeDecodeError:
                    logger.error("Failed to decode data chunk.")

                if datalen > 0:
                    logger.error('Data integrity error. Closing connection.')

                try:
                    msg_json:Dict = json.loads(msg_str)
                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON message.")
                    self.logger.error(msg_str)
                    continue

                logger.info(f"Receive Msg Type: {msg_json['type']}")
                logger.info(f'Received msg Down.')

                match msg_json["type"]:
                        case "act_error":
                            logger.error(msg_json["act_error"])
                        case "act_ret":
                            if "screenshot" in msg_json["act_ret"] and len(msg_json["act_ret"]["screenshot"]) > 0:
                                global img_base64
                                img_base64 = msg_json["act_ret"].pop("screenshot")

                                img_data = base64.b64decode(img_base64)

                                with open("screenshot.jpeg", "wb") as f:
                                    f.write(img_data)
                                img = Image.open(io.BytesIO(img_data))
                                img.save("screenshot.jpeg")
                            logger.debug(msg_json["act_ret"])
                        case __:
                            logger.info(msg_json[msg_json["type"]])

                msg_str:str = json.dumps(msg_json)
                self.add(sc.observation, msg_str)

        async def write_data():
            data_event:SEvent = self.get(sc.android.write)
            data_str:str = data_event.content
            send_msg:bytes = data_str.encode(encoding = 'utf-8')
            writer.write(len(send_msg).to_bytes(4, byteorder = 'big'))
            writer.write(send_msg)
            await writer.drain()
            logger.info('<Write complete>')

        try:
            read_task = asyncio.create_task(read_data())
            # listen to the write event.
            self.listen(sc.android.write)(write_data)
            await asyncio.gather(read_task)

        except Exception as e:
            logger.error(f"Error in main_process: {e}")
            logger.error(traceback.format_exc())

        finally:
            read_task.cancel()
            writer.close()
            await writer.wait_closed()
            self.client_count -= 1

class PCEnv(BasicComponent):
    def __init__(self, *,
                aw_client:ActivityWatchClient,
                chrome_apps:List[str],
                interval_seconds:int = 15,
                watched_path:List[str] = [],
                name:str = 'PCEnv',
                ):
        """
        Args:
            aw_client (ActivityWatchClient): The client to let us monitor the PC.
            chrome_apps (List[str]): the chromes that you want to monitor( We can't get rid of this :( )
            interval_seconds (int, optional): The pause time between two interactions. Defaults to 15 [seconds].
            name (str, optional): the name of the environment. Defaults to 'PCEnv'.
        """
        super().__init__(name)
        self.aw_client = aw_client
        self.chrome_apps = chrome_apps
        self.interval_seconds = interval_seconds

        self.action_listener = ActionListener(
            aw_client = aw_client,
            chrome_apps = chrome_apps,
            interval_seconds = interval_seconds,
            watched_path=watched_path)

        self.executor = Executor()

        complete_tools = toolreg.get_all_tools_dict()
        self.tools = [t for t in complete_tools if 'android' not in t["name"]]

    async def setup(self):
        self.logger.info("Initializing PC Environment...")

        def start_local_server():
            try:
                subprocess.run(['python', 'main.py'])
            except:
                subprocess.run(['python3', 'main.py'])

        # We set up the uvicorn in another thread, so we don't have to open to terminal.
        self.thread = threading.Thread(target = start_local_server, daemon=True)
        self.thread.start()
        self.logger.info("Local server established.")

        self.add(sc.agent.operations, content = json.dumps(self.tools), silent = True)
        self.listen(sc.pc.notify)(self.execute)
        self.action_listener.start()
        read_task = asyncio.create_task(self.read_data())
        self.logger.info("PC Environment Initialized. Action Listener running...")

        await asyncio.gather(read_task)

    async def read_data(self):

        await asyncio.sleep(self.interval_seconds)

        while True:
            data:Dict = self.action_listener.send_data()
            async with self.get_tag_lock(sc.activity):
                self.add(sc.observation, content = json.dumps(data,ensure_ascii=False))
            await asyncio.sleep(self.interval_seconds)

    async def execute(self):
        operation:str = self.get(sc.agent.execute).content

        if operation == 'nop':
            return

        current_event:str = self.get(sc.observation).content
        proposal:str = self.get(sc.agent.propose).content
        proposal_json:Dict = json.loads(proposal)

        exec_args = {"events": current_event, "func_call": operation}
        self.executor.receive(proposal_json, exec_args)
        self.executor.send()

class DemoAgent(BasicComponent):
    def __init__(self,*,
                env:Literal["PC","Mobile"],
                name:str = "ActiveAgent"):
        """
        Args:
            env (Literal['PC','Mobile']): Whether we are on PC or the Mobile.
            name (str, optional): The name of the agent. Defaults to "ActiveAgent".
        """
        super().__init__(name)
        self.env:str = env

    @property
    def memory(self):
        return [{"role": "system", "content": SYSTEM_PROMPT}]

    async def setup(self):
        logger.info("Initializing Agent...")
        self.listen(sc.observation)(self.propose)
        logger.info("Agent setup done.")

    async def propose(self):

        if self.get_tag_lock(sc.agent.propose).locked():
            logger.error("Another agent is proposing.")
            return

        async with self.get_tag_lock(sc.agent.propose):
            async with self.get_tag_lock(sc.activity):

                ops_event:SEvent = self.get(sc.agent.operations)
                ops:str = ops_event.content

                obs:Dict = self.gather([sc.observation],return_dumper='json')

                history = obs

                # TODO: Can we add user feedback for PC?

                user_content:str = json.dumps({
                    "Instructions": "Now analyze the history events and provide a task if you think the user needs your help using the given format. If the user is in an email application and there are no mails, you could first refresh the mail by swipe down using `swipe` tool.",
                    "operations": ops
                })

                if self.env == "Mobile":
                    history = history[-1:]

                global img_base64

                if self.env == 'Mobile' and img_base64 is not None:
                    img = [{
                        "type": "image_url",
                        "image_url":{
                            "url": f"data:image/jpeg;base64,{img_base64}",
                            "detail": "low"
                        }
                    }]
                    img_base64 = None

                else:
                    img = []

                logger.debug('Start Proposing....')

                res: AgentResponse = await self.cl.exec(
                    prompt = user_content,
                    return_type = AgentResponse,
                    messages = self.memory + history,
                    images = img
                )

                self.logger.info(res)
                self.add(sc.agent.propose, content = res.model_dump_json())

                if res.Operation is not None and res.Operation != 'null':
                    self.add(sc.agent.execute, res.Operation)
                else:
                    self.add(sc.agent.execute, "nop")

class Trigger(BasicComponent):
    def __init__(self,*,
                env: Literal["PC","Mobile"],
                name:str = "Trigger",
                ):
        """
        Args:
            env (Literal['PC','Mobile']): Whether we are on PC or the Mobile. we send the proposal to different channels.
            name (str, optional): The name of the agent. Defaults to "Trigger".
        """
        super().__init__(name)
        self.env:str = env

    async def setup(self):
        logger.info("Initializing Trigger...")
        self.listen(sc.agent.execute)(self.execute)
        logger.info("Trigger setup done.")

    async def execute(self):
        def reformat_action(tool_description:Optional[str] = 'nop') -> Dict:
            """
            (Android only) Reformat the description from agent to restriced format.

            Args:
                tool_description (str): a string containing the name of the tool and the arguments joined by separator '&'
                Example input: func_name&param1=value1&param2=value2
            """

            nop_action = {
                "type": "action",
                "action": {
                    "nop": {
                        "screenshot": True
                    }
                }
            }

            if tool_description == 'nop':
                return nop_action

            action_json = None

            func_list = tool_description.split('&')

            func_name = func_list[0]
            func_param = func_list[1:]

            try:
                param_dict = {k:v for k,v in [p.split('=') for p in func_param]}
            except:
                param_dict = {}

            # The fucntion name is changed beacuse of the unique function name in the agent. so we manually change this.
            match func_name:
                case 'android_tap_viewId':
                    action_json = {
                        "type": "action",
                        "action": {
                            "tap": param_dict
                        }
                    }

                case 'android_tap_position':
                    action_json = {
                        "type": "action",
                        "action": {
                            "tap": {
                                "coordinates": param_dict
                            }
                        }
                    }

                case 'android_press_viewId':
                    action_json = {
                        "type": "action",
                        "action": {
                            "press": param_dict
                        }
                    }

                case 'android_press_pos':
                    action_json = {
                        "type": "action",
                        "action": {
                            "press": {
                                "coordinates":{
                                    'x' : param_dict["x"],
                                    'y' : param_dict["y"]
                                },
                                "duration": param_dict["duration"]
                            }
                        }
                    }

                case 'android_input':
                    action_json = {
                        "type": "action",
                        "action": {
                            "input": param_dict
                        }
                    }
                    if action_json["action"]["input"]["viewId"] is None:
                        del action_json["action"]["input"]["viewId"]

                case 'android_swipe':
                    action_json = {
                        "type": "action",
                        "action": {
                            "swipe":{
                                "start_coordinates":{
                                    "x": param_dict["start_x"],
                                    "y": param_dict["start_y"],
                                },
                                "end_coordinates":{
                                    "x": param_dict["end_x"],
                                    "y": param_dict["end_y"],
                                },
                                "duration": param_dict["duration"]
                            }
                        }
                    }

                case 'android_back':
                    action_json = {
                        "type": "action",
                        "action": {
                            "back": {}
                        }
                    }

                case 'android_home':
                    action_json = {
                        "type": "action",
                        "action": {
                            "home": {}
                        }
                    }

                case 'android_get_notification':
                    action_json = {
                        "type": "notifications_get_all","notifications_get_all": {}
                    }

                case 'android_add_notification':
                    action_json = {
                        "type": "notifications_add",
                        "notifications_add": param_dict
                    }

                case 'android_get_calendar':
                    action_json = {
                        "type": "calendar_get",
                        "calendar_get": param_dict
                    }

                case 'android_add_calendar':
                    action_json = {
                        "type": "calendar_add",
                        "calendar_add": param_dict
                    }

                case __:
                    self.logger.warning(f"Invalid action {func_name}")
                    return nop_action

            return action_json

        operation:str = self.get(sc.agent.execute).content

        match self.env:
            case 'Mobile':
                action_json:Dict = reformat_action(operation)
                self.add(sc.android.write, content = json.dumps(action_json))

            case 'PC':
                self.add(sc.pc.notify, content = operation)

            case __:
                raise Exception(f"Invalid Environment parameters. {self.env}")
