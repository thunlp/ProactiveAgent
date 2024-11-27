import logging
import importlib
import traceback

from copy import deepcopy
from typing import Optional, Callable, Any, Type, Union

from .label import ToolLabels
from .exceptions import ToolNotFound, EnvNotFound, ToolRegisterError

logger = logging.getLogger()

def get_func_name(func: Callable, env = None) -> str:
    if env is None or not hasattr(env, 'env_labels'):
        if hasattr(func, 'tool_labels') and isinstance(func.tool_labels, ToolLabels):
            return func.tool_labels.name
        else:
            return func.__name__
    else:
        if hasattr(func, 'tool_labels') and isinstance(func.tool_labels, ToolLabels):
            return env.env_labels.alias + '_0_' + func.tool_labels.name
        else:
            return env.env_labels.alias + '_0_' + func.__name__

class Tool(Callable):
    tool_labels: ToolLabels

class ToolRegister:
    def __init__(self,
                ):
        # load modules
        self.tools: dict[str, Tool] = {}

        for module_name in ['register.tools',]:
            sub_modules = importlib.import_module(module_name).__all__
            for module in sub_modules:
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    self.check_and_register(attr)

        logger.info(
            f'Loaded {len(self.tools)} tools !')
        # print(self.tools)

    def check_and_register(self, attr: Any):
        if hasattr(attr, 'tool_labels') and isinstance(attr.tool_labels, ToolLabels):
            tool_name = get_func_name(attr)
            if tool_name in self.tools:
                logger.warning(
                    f'Tool {tool_name} is replicated! The new one will be replaced!')
                return None

            self.tools[tool_name] = attr
            logger.info(f'Register tool {tool_name}!')
            return attr

        return None


    def dynamic_extension_load(self, extension: str) -> bool:
        '''Load extension dynamically.

        :param string extension: The load path of the extension.
        :return boolean: True if success, False if failed.
        '''
        try:
            module = importlib.import_module(extension)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                self.check_and_register(attr)
        except Exception as e:
            logger.error(
                f'Failed to load extension {extension}! Exception: {e}')
            # logger.error(traceback.format_exc())
            return False

        return True

    def get_tool_dict(self, tool_name: str) -> dict:
        return self[tool_name].tool_labels.dict(name_overwrite=tool_name)

    def get_all_tools(self, include_invisible=False) -> list[str]:
        if include_invisible:
            return [tool_name for tool_name in self.tools]
        else:
            return [tool_name for tool_name in self.tools if self.tools[tool_name].tool_labels.visible]

    def get_all_tools_dict(self, include_invisible=False) -> list[dict]:
        return [self.tools[tool_name].tool_labels.dict(name_overwrite=tool_name) for tool_name in self.get_all_tools(include_invisible)]

    def __getitem__(self, key) -> Tool[..., Any]:
        # two stage index, first find env, then find tool
        if isinstance(key, str):
            if key not in self.tools:
                raise ToolNotFound(tool_name=key)
            return self.tools[key]

        elif isinstance(key, tuple):
            raise NotImplementedError(f'Key {key} is not valid!')

        raise NotImplementedError(f'Key {key} is not valid!')
