"""Phase 0 hello-world: fetch current weather for Raleigh, NC via OpenWeatherMap.

Run:  python -m src.integrations.weather
Requires OPENWEATHER_API_KEY in .env (free tier at openweathermap.org/api).
"""

import requests

from src import config


def get_current_weather() -> dict:
    response = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={
            "q": config.WEATHER_CITY,
            "appid": config.OPENWEATHER_API_KEY,
            "units": "imperial",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    data = get_current_weather()
    description = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    print(f"{config.WEATHER_CITY}: {temp}°F, {description}")
