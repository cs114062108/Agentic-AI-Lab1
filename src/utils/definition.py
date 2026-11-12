from __future__ import annotations

from typing import TypedDict, TypeAlias, Literal, Callable, Coroutine, Any
from dataclasses import dataclass, asdict

ConversationMode: TypeAlias = Literal["planning", "gathering"]

class ProfileData(TypedDict):
    department: str | None
    year: int | None
    completed_courses: list[str] | None
    interests: list[str] | None
    min_credits: int | None
    max_credits: int | None

@dataclass
class StudentProfile:
    department: str | None = None
    year: int | None = None

    completed_courses: list[str] | None = None
    interests: list[str] | None = None

    min_credits: int | None = None
    max_credits: int | None = None

    def reset(self):
        for field in self.__dict__.keys():
            self.__dict__[field] = None
    
    def missing_fields(self) -> list[str]:
        required = [
            "department",
            "year",
            "completed_courses",
            "interests"
        ]

        return [
            field
            for field in required
            if getattr(self, field) is None
        ]

    @property
    def is_ready(self) -> bool:
        return not self.missing_fields()

    def to_dict(self) -> ProfileData:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, dat: ProfileData) -> "StudentProfile":
        return cls(**dat)

ToolType: TypeAlias = Callable[[Any], str] | Coroutine[Any, Any, str]
SchemaType: TypeAlias = Literal["function", "custom"]

class ArgItemTypeInfo(TypedDict):
    type: str

class ArgTypeInfo(TypedDict):
    type: str | list[str]
    items: ArgItemTypeInfo

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

