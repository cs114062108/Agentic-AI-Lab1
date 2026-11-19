from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING, TypeVar, ParamSpec, Generic, Callable, Coroutine
from functools import wraps

from openai.types.chat import ChatCompletionToolUnionParam
from openai.types import FunctionDefinition
from src.utils.definition import FuncInfo, FuncParam

from src.extension import errors

from src.utils.tool_utils import generate_schema

TOOL_T = TypeVar('TOOL_T')

class Tool(Generic[TOOL_T]):
    __func: TOOL_T
    __restore_func: Callable | Coroutine | None
    name: str
    
    def __init__(self, func: TOOL_T, name: str | None = None):
        self.__func = func
        
        if name:
            self.name = name
        else:
            self.name = self.__func.__name__
        
        self.__restore_func = None
    
    def __call__(self, *args, **kwargs):
        return self.__func(*args, **kwargs)
    
    async def __await__(self):
        pass
    
    def restorer(self, func: Callable | Coroutine):
        """Decorator that adds a function as the tool's restorer"""
        self.__restore_func = func
        
        return func

class ToolCog(Generic[TOOL_T]):
    """
    Class that collects and manages tool functions from a cog file
    """
    tool_names: list[str]
    tool_schemas: list[ChatCompletionToolUnionParam]
    tools: list[Tool[TOOL_T]]
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
    
    def tool(self, func: TOOL_T) -> Tool[TOOL_T]:
        """Decorator that adds a function to the tool cog object as a tool"""
        if func.__name__ not in self.tool_names:
            self.tool_names.append(func.__name__)
            
            tool: Tool[TOOL_T] = Tool(func)
            self.tools.append(tool)
            
            self.tool_schemas.append(generate_schema(func))
            
        return tool
    
    def show(self):
        print(f"Cog name: {self.name}")
        print(f"Cog tool names: {self.tool_names}")
        print(f"Cog tools: {self.tools}")
