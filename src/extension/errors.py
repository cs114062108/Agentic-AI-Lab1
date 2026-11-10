from __future__ import annotations
from typing import Optional, Any

class ExException(Exception):
    """Base exception class for the extensioning module

    Ideally speaking, this could be caught to handle any exceptions raised from this library.
    """

    pass

class EngineException(ExException):
    """Exception that's raised when an operation in the :class:`ExtensionEngine` fails.

    These are usually for exceptions that happened due to user input.
    """

    pass

class ExtensionError(ExException):
    """Base exception for extension related errors.

    This inherits from :exc:`~discord.DiscordException`.

    Attributes
    ------------
    name: `str`
        The extension that had an error.
    """

    def __init__(self, message: Optional[str] = None, *args: Any, name: str) -> None:
        self.name: str = name
        message = message or f'Extension {name!r} had an error.'
        # clean-up
        m = message
        super().__init__(m, *args)


class ExtensionAlreadyLoaded(ExtensionError):
    """An exception raised when an extension has already been loaded.

    This inherits from :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f'Extension {name!r} is already loaded.', name=name)


class ExtensionNotLoaded(ExtensionError):
    """An exception raised when an extension was not loaded.

    This inherits from :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f'Extension {name!r} has not been loaded.', name=name)


class NoEntryPointError(ExtensionError):
    """An exception raised when an extension does not have a ``setup`` entry point function or ``tools`` list.

    This inherits from :exc:`ExtensionError`
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"Extension {name!r} has no 'setup' function or 'tools' list.", name=name)


class ExtensionFailed(ExtensionError):
    """An exception raised when an extension failed to load during execution of the module or ``setup`` entry point.

    This inherits from :exc:`ExtensionError`

    Attributes
    -----------
    name: `str`
        The extension that had the error.
    original: `Exception`
        The original exception that was raised. You can also get this via
        the ``__cause__`` attribute.
    """

    def __init__(self, name: str, original: Exception) -> None:
        self.original: Exception = original
        msg = f'Extension {name!r} raised an error: {original.__class__.__name__}: {original}'
        super().__init__(msg, name=name)


class ExtensionNotFound(ExtensionError):
    """An exception raised when an extension is not found.

    This inherits from :exc:`ExtensionError`

    Attributes
    -----------
    name: `str`
        The extension that had the error.
    """

    def __init__(self, name: str) -> None:
        msg = f'Extension {name!r} could not be loaded or found.'
        super().__init__(msg, name=name)
