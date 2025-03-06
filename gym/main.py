from typing import Optional
import yaml
import fire
import json
import uuid
import os

from .components import ProactiveAgent,UserAgent,EnvironmentStateManager
from .config import logger,eventSink
from .channel import sinkChannels

async def data_loop(cfg_file: str,out_file: Optional[str] = None):
    with open(cfg_file, 'r') as f:
        cfg = yaml.safe_load(f)

    if out_file is None:
        out_file = cfg['eventSink'].get("out_file", uuid.uuid4().hex + ".jsonl")

    if os.path.exists(out_file):
        os.remove(out_file)

    out = open(out_file,"x")

    def decorator(func):
        def wrapped_add(*args,**kwargs):
            ret = func(*args,**kwargs)
            for item in ret:
                out.write(json.dumps(item.model_dump()) +'\n')
            out.flush()
            return ret
        return wrapped_add
    eventSink.add = decorator(eventSink.add)

    # setup event source
    eventSink.init(**cfg["eventSink"])

    env = EnvironmentStateManager(**cfg["environment"])
    user = UserAgent(**cfg["user"])
    if os.environ.get("SETUP_PROACTIVE_AGENT","False") == "True":
        agent = ProactiveAgent(**cfg["agent"])

    # wait Setup
    eventSink.add(tags=sinkChannels.setup, content="Setup Components...",)
    await eventSink.wait(sinkChannels.setup)
    eventSink.add(tags=sinkChannels.setup,
                    content="Setup Completed!", silent=True)

    logger.info("*** Components setup completed. ***")
    # setup environment adapation
    await env.intro()
    await eventSink.wait(sinkChannels.env.all)
    logger.info("*** Environment Adaptation Completed. ***")

    # start activity and events generation
    await user.step()

    await eventSink.wait([sinkChannels.activity, sinkChannels.events, sinkChannels.agent.proactive])
    out.close()

if __name__ == "__main__":
    fire.Fire(data_loop)
