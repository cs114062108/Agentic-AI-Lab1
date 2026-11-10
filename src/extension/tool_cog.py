from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING, TypeVar, ParamSpec, Generic
from functools import wraps
import inspect

from openai.types.chat import ChatCompletionToolUnionParam
from openai.types import FunctionDefinition
from src.utils.definition import FuncInfo, FuncParam

from src.extension import errors

TOOL_T = TypeVar('TOOL_T')

class ToolCog(Generic[TOOL_T]):
    """
    Class that collects and manages tool functions from a cog file
    """
    tool_names: list[str]
    tool_schemas: list[ChatCompletionToolUnionParam]
    tools: list[TOOL_T]
    name: str
    
    def __init__(self, name: str):
        """
        Arg:
            name (str):
                The name of the cog
        """
        self.name = name
        self.tool_names = []
        self.tool_schemas = []
        self.tools = []
    
    @staticmethod
    def get_json_type(annotation: str) -> str:
        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
        }

        if annotation not in type_mapping:
            raise TypeError(
                f"Unsupported parameter type: {annotation}"
            )

        return type_mapping[annotation]
    
    def generate_schema(self, func: TOOL_T) -> ChatCompletionToolUnionParam:
        schema: ChatCompletionToolUnionParam = {}
        schema["type"] = "function"
        
        sig = inspect.signature(func)
        
        func_info: FuncInfo = {}
        func_info["name"] = func.__name__
        func_info["description"] = inspect.getdoc(func) or ""
        
        param_info: FuncParam = {}
        param_info["type"] = "object"
        
        param_info["properties"] = {}
        param_info["required"] = []
        
        for name, param in sig.parameters.items():
            param_info["properties"][name] = {
                "type": self.get_json_type(param.annotation)
            }
            
            if param.default is inspect.Parameter.empty:
                param_info["required"].append(name)
        
        param_info["additionalProperties"] = False
        
        func_info["parameters"] = param_info
        
        schema["function"] = func_info
        
        return schema
    
    def tool(self, func: TOOL_T):
        """Decorator that adds a function to the tool cog object as a tool"""
        if func.__name__ not in self.tool_names:
            self.tool_names.append(func.__name__)
            self.tools.append(func)
            
            self.tool_schemas.append(self.generate_schema(func))
            
        return func
    
    def show(self):
        print(f"Cog name: {self.name}")
        print(f"Cog tool names: {self.tool_names}")
        print(f"Cog tools: {self.tools}")
