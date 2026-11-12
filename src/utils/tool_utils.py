from __future__ import annotations

import inspect
import types
from typing import Any, get_args, get_origin, get_type_hints

from openai.types.chat import ChatCompletionToolUnionParam
from openai.types import FunctionDefinition
from src.utils.definition import FuncInfo, FuncParam, ArgTypeInfo, ToolType

def _get_json_type(annotation: type) -> ArgTypeInfo:
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
    }

    # Handle Optional / Union, e.g., str | None
    args = get_args(annotation)
    nullable = type(None) in args

    if nullable:
        non_none_args = [
            arg for arg in args
            if arg is not type(None)
        ]

        if len(non_none_args) != 1:
            raise TypeError(
                f"Unsupported union type: {annotation}"
            )

        annotation = non_none_args[0]

    # Handle lists, e.g., list[str]
    if get_origin(annotation) is list:
        item_args = get_args(annotation)

        if len(item_args) != 1:
            raise TypeError(f"Unsupported list type: {annotation}")

        item_type = type_mapping.get(item_args[0])

        if item_type is None:
            raise TypeError(f"Unsupported list item type: {item_args[0]}")

        schema: ArgTypeInfo = {
            "type": "array",
            "items": {"type": item_type}
        }

    else:
        json_type = type_mapping.get(annotation)

        if json_type is None:
            raise TypeError(
                f"Unsupported parameter type: {annotation}"
            )

        schema: ArgTypeInfo = {"type": json_type}

    # nullable property, such as ["string", "null"]
    if nullable:
        schema["type"] = [schema["type"], "null"]

    return schema

def generate_schema(func: ToolType) -> ChatCompletionToolUnionParam:
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
    
    hints = get_type_hints(func)

    for name, param in sig.parameters.items():
        annotation = hints.get(name, param.annotation)

        if annotation is inspect.Parameter.empty:
            raise TypeError(
                f"Missing type annotation for parameter '{name}'"
            )

        param_info["properties"][name] = _get_json_type(annotation)

        if param.default is inspect.Parameter.empty:
            param_info["required"].append(name)
    
    param_info["additionalProperties"] = False
    
    func_info["parameters"] = param_info
    
    schema["function"] = func_info
    
    return schema
