import logging
import inspect
import docstring_parser

from pydantic import create_model
from typing import Optional,Callable,Any,Type,Union

from .label import ToolLabels


logger = logging.getLogger()

def resolve_ref(schema, ref_path, root):
    parts = ref_path.split("/")
    for part in parts[1:]:  # 跳过第一个空字符串
        if part in schema:
            schema = schema[part]
        elif part in root:  # 直接从根开始的情况
            schema = root[part]
        else:
            raise ValueError(f"Reference path not found: {ref_path}")
    return schema

def resolve_schema(schema, root=None):
    if root is None:
        root = schema
    
    if isinstance(schema, dict):
        if "$ref" in schema:
            # 解析$ref引用
            ref_path = schema["$ref"]
            return resolve_schema(resolve_ref(root, ref_path, root), root)
        else:
            # 递归处理字典中的每个键值对
            return {k: resolve_schema(v, root) for k, v in schema.items()}
    elif isinstance(schema, list):
        # 递归处理列表中的每个元素
        return [resolve_schema(item, root) for item in schema]
    else:
        # 基本数据类型，直接返回
        return schema

def generate_tool_labels(
    name: str = None,
    enabled: bool = True,
    disabled_reason: Optional[str] = None,
    func: Callable[..., Any] = None,
    visible:bool = True,
)->Union[ToolLabels,None]:
    """
    Generate and return tool labels for the provided function. If the tool is not enabled,
    then a debug log message is printed and None is returned.

    Args:
        name (str, optional): The name of the tool. If it's not specified, the function's name is used.
        enabled (bool, optional): Determines if the tool is enabled or not. Defaults to True.
        disabled_reason (Optional[str], optional): The reason why the tool is disabled. Defaults to None.
        func (Callable[..., Any], optional): The function for which the tool labels are generated. Defaults to None.
        visible(bool, optional): The visibility status of the tool. Defaults to True.

    Returns:
        Union[ToolLabels,None]: A ToolLabels object containing tool information or None if tool is not enabled. 
    """

    if not enabled:
        if disabled_reason is not None:
            logger.debug(f"tool '{func.__name__}' is disabled: {disabled_reason}")
        return None

    # create pydantic function model
    kw = {n:(o.annotation, ... if o.default==inspect.Parameter.empty else o.default)
          for n, o in inspect.signature(func).parameters.items() if n != 'self' and n != 'cls' and o.annotation != inspect.Parameter.empty}
    func_model = create_model(f'{func.__name__} args', **kw)
    auto_signature: dict = func_model.model_json_schema()
    
    auto_signature = resolve_schema(auto_signature)
    auto_signature.pop('$defs',None)

    # check if the method have full annotations
    func_desc =  docstring_parser.parse(func.__doc__)
    required = []
    for arg in func_desc.params:
        if arg.arg_name not in auto_signature["properties"]:
            logger.warning(f'Function {func.__name__} has no annotation for argument {arg.arg_name}.')
            continue
        
        auto_signature["properties"][arg.arg_name]["description"] = arg.description
        
        if arg.default is not None:
            auto_signature["properties"][arg.arg_name]['default'] = arg.default
        if not arg.is_optional:
            required.append(arg.arg_name)
    auto_signature["required"] = required

    tool_name = func.__name__ if name is None else name
    description = ''
    if func_desc.short_description is not None:
        description = func_desc.short_description
    if func_desc.long_description is not None:
        description += '\n' + func_desc.long_description
    if func_desc.returns is not None:
        description += '\nReturn: ' + func_desc.returns.description
    
    
    return ToolLabels(
        name=tool_name,
        description=description,
        method=func,
        args_model=func_model,
        signature=auto_signature,
        enabled=enabled,
        disabled_reason=disabled_reason,
        visible=visible,
    )

def toolwrapper(
    name: str = None,
    enabled: bool = True,
    disabled_reason: Optional[str] = None,
    parent_tools_visible: bool = False,
    visible:bool = True,
)->Union[Type,Callable[..., Any]]:
    """The tool decorator for class, used to create tool objects from ordinary class."""

    def decorator(obj:object)->Union[Type,Callable[..., Any]]:
        if inspect.isfunction(obj):
            func = obj
            tool_labels = generate_tool_labels(
                name=name,
                enabled=enabled, 
                disabled_reason=disabled_reason,
                func=func,
                visible=visible)
            func.tool_labels = tool_labels
            return func
        else:
            raise NotImplementedError(f'Object with type {type(obj)} not recognized!')
    return decorator
