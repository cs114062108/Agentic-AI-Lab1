from __future__ import annotations

import os
from typing import Callable, Coroutine, TYPE_CHECKING, Any, TypeAlias
import asyncio
from collections import defaultdict

import json
from src.utils import Logger, RESULTS_DIR

from src.extension import ExtensionEngine

from openai.types.chat import ChatCompletionToolUnionParam
ToolType: TypeAlias = Callable[[Any], str] | Coroutine[Any, Any, str]

class Toolbox(ExtensionEngine[ToolType]):
    # -- Tools --
    initial_extensions: list[str]
    tools: list[ToolType]
    tool_names: list[str]
    tool_schemas: list[ChatCompletionToolUnionParam]
    tools_dict: dict[str, ToolType]
    
    def __init__(self, tools: list[ToolType] = []):
        super().__init__()
        
        self.tools = tools
        self.tool_names = []
        self.tool_schemas = []
        
        # -- Tools --
        self.initial_extensions = []
        for filename in os.listdir("./src/tools"):
            if filename.endswith(".py"):
                self.initial_extensions.append("src.tools." + filename[:-3])
        Logger.info(f"Toolbox initial_extensions = {self.initial_extensions}")
        
        Logger.info(f"Loading {len(self.initial_extensions)} tool files")
        count = 0
        for extension in self.initial_extensions:
            try:
                Logger.info(f"Loading tool extention: {extension}")
                self.load_extension(extension)
                count += 1
            except Exception as e:
                Logger.warning(f"Error loading '{extension}' tool: {e}")
        Logger.info(f"Loaded {count}/{len(self.initial_extensions)} tool files")
        Logger.info(f"Found {len(self.tools)} tools: {list(self.tools_dict.keys())}")
    
    # --- Process Tools ---
    def process_tool(self, name: str, args_text: str) -> tuple[bool, str]:
        """Processes tool

        Args:
            name (str): The name of the tool
            args_text (str): The jsonfied arguments text

        Returns:
            succeeded (bool): Succeeded or not
            result (str): The result
        """
        succeeded = False
        result = ""
        
        try:
            args: dict[str, object] = json.loads(args_text)
            if not isinstance(args, dict):
                raise ValueError("arguments must be a JSON object")
        except (json.JSONDecodeError, ValueError) as jerr:
            Logger.warning(f"[Tool Arguments] Invalid arguments")
            Logger.warning(f"{jerr.__class__.__name__}: {jerr}")
            result = f"The arguments provided are invalid"
            return (succeeded, result)
        
        func = self.tools_dict.get(name)
        if func:
            Logger.info(f"[Tool] Processing tool '{name}'...")
            try:
                result = func(**args)
                Logger.info(f"[Tool] Tool '{name}' execution completed")
                succeeded = True
                return (succeeded, result)
            except Exception as err:
                Logger.warning(f"[Tool Failed] Error processing tool '{name}'")
                Logger.warning(f"{err.__class__.__name__}: {err}")
                result = f"The tool '{name}' has failed when executing with unprovided reasons"
                return (succeeded, result)

        Logger.warning(f"[No Tool] Tool named '{name}' not found")
        result = f"The tool '{name}' is not available or not found"
        return (succeeded, result)
    
    # Just leave it, won't be used now
    async def process_tool_async(self, name: str, args: dict[str, object]) -> str:
        func = self.tools_dict.get(name)
        if func:
            if isinstance(func, Coroutine):
                Logger.info(f"Processing CORO tool '{name}'")
                return await func(**args)
            else:
                Logger.info(f"Processing tool '{name}'")
                return func(**args)
        Logger.warning(f"Tool named '{name}' not found")
        return f"Sorry, tool '{name}' not available or not found"
    
    # --- Dump and Save Schemas ---
    def save_tool_schemas(self):
        json_path = RESULTS_DIR / "tool_schemas.json"
        with json_path.open("w", encoding="utf-8") as file:
            json.dump(self.tool_schemas, file, indent=2, ensure_ascii=False)
    

tools_to_get = []
AgentToolbox = Toolbox(tools=tools_to_get)


if __name__ == "__main__":
    print()
    print("----- Test -----")
    print(f"cog_names: {AgentToolbox.cog_names}")
    print(f"tools: {AgentToolbox.tools}")
    print(f"tool_names: {AgentToolbox.tool_names}")
    print(f"tools_dict: {AgentToolbox.tools_dict}")
    
    print(f"tool_schemas: {AgentToolbox.tool_schemas}")
    tool_schemas_text = json.dumps(AgentToolbox.tool_schemas, indent=2, ensure_ascii=False)
    print(tool_schemas_text)
    
    AgentToolbox.save_tool_schemas()
