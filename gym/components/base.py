from codelinker import EventProcessor
from typing import Iterable, Literal
import json
from codelinker.models import SEvent, ChannelTag
from ..config import clinker, eventSink, sinkChannels
class BasicComponet(EventProcessor):
    def __init__(self,name:str):
        super().__init__(name=name,sink=eventSink)
        self.listen(sinkChannels.setup)(self.setup)
        self.cl = clinker
    def gather(self, tags: ChannelTag | Iterable[ChannelTag] | None = None,return_dumper:Literal['identity','json']='json') -> str | Iterable[dict]:
        messages = super().gather(tags=tags,return_dumper='identity')
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
                        })
                return messages
            case _:
                raise ValueError(f"return_dumper should be 'identity' or 'json', but got {return_dumper}")