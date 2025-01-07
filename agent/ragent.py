'''
The main agent file.
'''
import os
from time import sleep
import json
import socket
import asyncio
import logging
from typing import Literal

import fire
from aw_client import ActivityWatchClient

from components import DemoAgent, AndroidEnv, PCEnv, Trigger, eventSink, logger
from channels import sc

# Get rid of other logging information.
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)
logging.getLogger("filelock").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("openai").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("aw_client").setLevel(logging.CRITICAL)


async def main(platform : Literal["PC","Mobile"],
                chromes : str = '',
                interval: int = 15,
                port    : int = 5600):

    match platform:
        case "Mobile":
            # change the default port.
            if port == 5600:
                port = 9999

            ip = '0.0.0.0'

            CONFIG_INFO = \
f'''
Android Listening Configuration:
- Set up server on IP: {ip}.
- Set up server listening on port: {port}.
- Assistance Interval: {interval} seconds.
'''
            logger.info(CONFIG_INFO)

            env = AndroidEnv(server_host=ip, server_port=port, name="Android")
            agent = DemoAgent(env = platform, name="Android Agent")
            trigger = Trigger(env = platform)

            eventSink.init()

            # Set up all components.
            eventSink.add(tags = sc.setup, content = 'Set up.')
            await eventSink.wait(sc.setup)
            logger.info("*** Components setup completed. ***")

            # send very first nop action to android.
            nop_action = {
                        "type": "action",
                        "action": {
                            "nop": {
                                "screenshot": True
                            }
                        }
                    }

            await asyncio.sleep(5)
            eventSink.add(tags = sc.android.write, content = json.dumps(nop_action))
            await eventSink.wait(sc.android.write)

            while True:
                await asyncio.sleep(interval)
                eventSink.add(tags = sc.android.write, content = json.dumps(nop_action))

        case 'PC':
            if chromes == '':
                raise ValueError('Please specify the chrome apps you want to read by adding params --chromes chrome1,chrome2,chrome3')

            chromes = [chrome.replace('-',' ') for chrome in chromes.split(',')]
            aw_client = ActivityWatchClient(port = port)
            display_buckets = ['    - ' + bucket for bucket in aw_client.get_buckets().keys()]
            CONFIG_INFO = \
f'''
Android Socket Configuration:
- Activity port: {port}.
- Assistance Interval: {interval} seconds.
- Reading chromes as: {chromes}.
- Reading buckets from:
''' + '\n'.join(display_buckets)

            logger.info(CONFIG_INFO)

            agent = DemoAgent(env = platform, name = 'PC Agent')
            pc = PCEnv(aw_client = aw_client,
                        chrome_apps = chromes,
                        interval_seconds = interval,
                        watched_path=[os.path.abspath('.')],
                        name = platform)
            trigger = Trigger(env = platform)
            eventSink.init()

            eventSink.add(tags = sc.setup, content = 'Set up.')
            await eventSink.wait(sc.setup)
            logger.info("*** Components setup completed. ***")

            while True:
                await asyncio.sleep(1)

        case __:
            raise ValueError('Please specify the platform as "PC" or "Mobile"')

if __name__ == "__main__":
    fire.Fire(main)

# eg for PC: python ragent.py --platform PC --chromes explorer.exe,mesdge.exe
# eg for Mobile: python ragent.py --platform Mobile --port 9999 --interval 10
