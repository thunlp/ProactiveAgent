import codelinker
import toml
import os
import logging
import colorlog


from .channel import sinkChannels


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = colorlog.ColoredFormatter(fmt='%(log_color)s%(levelname)s - %(name)s - %(message)s',
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



CL_CFGFILE = os.getenv("CODELINKER_CFG",os.path.join(os.path.dirname(__file__),'..',"private.toml"))

cl_config = codelinker.CodeLinkerConfig(**toml.load(open(CL_CFGFILE)))

clinker = codelinker.CodeLinker(config=cl_config,logger=logger)      
eventSink = codelinker.EventSink(sinkChannels=sinkChannels,logger=logger,)