from __future__ import annotations

from src.extension import ExtensionEngine
from src.extension import ToolCog

import json

from src.utils import Logger
from src.utils.weather_utils import get_city_current_weather

cog = ToolCog("weather_tool_cog")

@cog.tool
def get_current_weather(city: str) -> str:
    """Retrieve current weather for a city via the real Open-Meteo API."""
    return get_city_current_weather(city)

# -- Setup --
def setup(engine: ExtensionEngine):
    engine.add_cog(cog)


if __name__ == "__main__":
    cog.show()
