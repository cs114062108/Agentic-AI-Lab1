from __future__ import annotations

from typing import TypedDict, TypeAlias, Literal

SchemaType: TypeAlias = Literal["function", "custom"]

class ArgTypeInfo(TypedDict):
    type: str

class FuncParam(TypedDict):
    type: Literal["object"]
    properties: dict[str, ArgTypeInfo]
    required: list[str]
    additionalProperties: bool
    strict: bool

class FuncInfo(TypedDict):
    name: str
    description: str
    parameters: FuncParam

class ToolSchema(TypedDict):
    type: SchemaType
    function: FuncInfo

