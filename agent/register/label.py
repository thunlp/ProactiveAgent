from typing import Optional,Callable,Any,Type,Union
from pydantic import BaseModel


class ToolLabels:
    """A class representing a tool.

    When invoked, this object runs the associated method using parameters defined in the signature.

    Attributes:
        name (str): The name of the tool.
        description (str): Description of the tool.
        method (Callable): The function/method that the tool executes.
        signature (dict): Argument keys and values needed by the method to execute.
        required (list): List of required arguments for the method.
        enabled (bool): Flag indicating whether the sstool is enabled or not.
        disabled_reason (str): Reason for disabling the tool, if applicable.
        func_type (str): Type of function for the tool, defaults to 'function'.
        visible (bool): Flag indicating whether the tool is visible or not.
    """

    def __init__(
        self,
        name: str,
        description: str,
        method: Callable[..., Any],
        args_model: BaseModel,
        signature: dict = {},
        enabled: bool = True,
        disabled_reason: Optional[str] = None,
        func_type: str = 'function',
        visible: bool = True,
    ):
        self.name = name
        self.description = description
        self.method = method
        self.args_model = args_model
        self.signature = signature
        self.enabled = enabled
        self.disabled_reason = disabled_reason
        self.func_type = func_type
        self.visible = visible

    def dict(self, name_overwrite: str = '') -> dict:
        """Returns the tool information as a dictionary.

        Args:
            name_overwrite (str): Replacement string for tool name, defaults to empty string.

        Returns:
            dict: Dictionary of tool attributes.
        """
        
        return {
            "name": self.name if name_overwrite == '' else name_overwrite,
            "description": self.description[:1024],
            "parameters":  self.signature
        }

    def __str__(self) -> str:
        """Returns the tool information in a formatted string.

        Returns:
            str: Formatted string containing tool attributes.
        """
        return f"{self.name}: {self.description}, args: {self.signature}"
