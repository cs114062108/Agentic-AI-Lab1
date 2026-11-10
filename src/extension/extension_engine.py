from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING, TypeVar, Generic, Callable
import types

import sys
import importlib
import importlib.util
import importlib.machinery

from src.extension import errors
from src.extension import ToolCog

if TYPE_CHECKING:
    from discord.ext.commands import bot

TOOL_T = TypeVar('TOOL_T')

class ExtensionEngine(Generic[TOOL_T]):
    """
    Base class that load in extensions with tools in it
    """
    __extensions: dict[str, types.ModuleType]
    __cogs: dict[str, ToolCog]
    tools: list[TOOL_T]
    tools_dict: dict[str, TOOL_T]
    tool_names: list[str]
    tool_schemas: list[dict[str, object]]

    def __init__(self):
        self.__extensions = {}
        self.__cogs = {}
        self.tools = []
        self.tools_dict = {}
        self.tool_names = []
        self.tool_schemas = []
    
    @property
    def cog_names(self) -> list[str]:
        return list(self.__cogs.keys())
    
    def add_cog(self, cog: ToolCog):
        """
        Adds a "cog" to the extension engine.
        
        Parameters
        -----------
        cog: `.ToolCog`
            The cog to register to the bot.
        
        Raises
        -------
        TypeError
            The cog does not inherit from :class:`.ToolCog`.
        EngineException
            A cog with the same name is already loaded.
        """
        if not isinstance(cog, ToolCog):
            raise TypeError("cogs must derive from ToolCog")
        
        cog_name = cog.name
        existing = self.__cogs.get(cog_name)
        
        if existing is not None:
            raise errors.EngineException(f"ToolCog named {cog_name!r} already loaded")
        
        self.__cogs[cog_name] = cog
        
        # Extend tools
        if cog.tools:
            self.tools.extend(cog.tools)
            self.tool_names.extend(cog.tool_names)
            self.tool_schemas.extend(cog.tool_schemas)
            
            for tool in cog.tools:
                self.tools_dict[tool.__name__] = tool
    
    def _resolve_name(self, name: str, package: Optional[str]) -> str:
        try:
            return importlib.util.resolve_name(name, package)
        except ImportError:
            raise errors.ExtensionNotFound(name)
    
    def _load_from_module_spec(self, spec: importlib.machinery.ModuleSpec, key: str) -> None:
        # precondition: key not in self.__extensions
        lib = importlib.util.module_from_spec(spec)
        sys.modules[key] = lib
        try:
            spec.loader.exec_module(lib)  # type: ignore
        except Exception as e:
            del sys.modules[key]
            raise errors.ExtensionFailed(key, e) from e
        
        try:
            setup = getattr(lib, 'setup')
        except AttributeError:
            del sys.modules[key]
            raise errors.NoEntryPointError(key)
        
        try:
            setup(self)
        except Exception as e:
            del sys.modules[key]
            raise errors.ExtensionFailed(key, e) from e
        else:
            self.__extensions[key] = lib
    
    def load_extension(self, name: str, *, package: Optional[str] = None) -> None:
        """
        Loads an extension.
        
        An extension is a python module that contains tools or whatever.
        
        Parameters
        ------------
        name: `str`
            The extension name to load. It must be dot separated like
            regular Python imports if accessing a sub-module. e.g.
            ``foo.test`` if you want to import ``foo/test.py``.
        package: Optional[`str`]
            The package name to resolve relative imports with.
            This is required when loading an extension using a relative path, e.g ``.foo.test``.
            Defaults to ``None``.
        
        Raises
        --------
        ExtensionNotFound
            The extension could not be imported.
            This is also raised if the name of the extension could not
            be resolved using the provided ``package`` parameter.
        ExtensionAlreadyLoaded
            The extension is already loaded.
        """
        name = self._resolve_name(name, package)
        if name in self.__extensions:
            raise errors.ExtensionAlreadyLoaded(name)

        spec = importlib.util.find_spec(name)
        if spec is None:
            raise errors.ExtensionNotFound(name)
        
        self._load_from_module_spec(spec, name)


if __name__ == "__main__":
    import os

    engine: ExtensionEngine[Callable[[str, int, float], dict]] = ExtensionEngine()

    initial_extensions = []
    for filename in os.listdir("./src/tools"):
        if filename.endswith(".py"):
            initial_extensions.append("src.tools." + filename[:-3])
    print(f"Toolbox initial_extensions = {initial_extensions}")
    
    print(f"Loading {len(initial_extensions)} tool files")
    count = 0
    for extension in initial_extensions:
        try:
            print(f"Loading tool extention: {extension}")
            engine.load_extension(extension)
            count += 1
        except Exception as e:
            print(f"Error loading '{extension}' tool: {e}")
    print(f"Loaded {count}/{len(initial_extensions)} tool files")
    print(f"Found {len(engine.tools)} tools: {engine.tools_dict.keys()}")
