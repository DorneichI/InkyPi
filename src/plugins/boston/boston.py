from plugins.base_plugin.base_plugin import BasePlugin
import logging
import requests
from google.transit import gtfs_realtime_pb2
import json
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Boston(BasePlugin):
    FEED_URL = "https://cdn.mbta.com/realtime/TripUpdates.pb"
    LOCATION = "BOSTON,MA"

    load_dotenv()
    API_KEY = os.getenv("WEATHER_API_KEY")

    def generate_image(self, settings, device_config):
        departures = self._get_next_departures()

        stops_path = os.path.join(os.path.dirname(__file__), "stops.json")
        with open(stops_path, "r") as file:
            stops = json.load(file)

        stop_data = {str(stop["id"]): {"name": stop["name"], "icon": stop["icon"]} for stop in stops["stops"]}

        stations = []
        for stop_id, times in departures.items():
            if stop_id in stop_data:
                stop_info = stop_data[stop_id]
                formatted_times = [time.strftime('%H:%M') for time in sorted(times)[:2]]  # Take the next 2 departures
                stations.append({
                    "stop_id": stop_id,
                    "name": stop_info["name"],
                    "icon": os.path.join(os.path.dirname(__file__), "icons", stop_info["icon"]),
                    "departures": formatted_times
                })

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        json_weather = self._get_weatherapi_forecast()

        weather_info = self._parse_weather(json_weather)

        template_params = {
            "stations": stations,
            "plugin_settings": settings,
            "weather_info": weather_info
        }

        return self.render_image(dimensions, "boston.html", "boston.css", template_params)

    def _get_trip_updates(self):
        response = requests.get(self.FEED_URL)
        response.raise_for_status()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)

        return feed
    
    def _get_stop_ids(self):
        stops_path = os.path.join(os.path.dirname(__file__), "stops.json")
        with open(stops_path, "r") as file:
            stops = json.load(file)
        
        stop_ids = []
        for stop in stops["stops"]:
            stop_ids.append(str(stop["id"]))
        
        return stop_ids

    def _get_next_departures(self):
        feed = self._get_trip_updates()

        stop_ids = self._get_stop_ids()

        departures_times = {stop_id: [] for stop_id in stop_ids}

        for entity in feed.entity:
            if entity.HasField("trip_update"):
                trip = entity.trip_update
                for stop_time_update in trip.stop_time_update:
                    stop_id = stop_time_update.stop_id
                    if stop_id in stop_ids:
                        dep = stop_time_update.departure.time if stop_time_update.HasField("departure") else None
                        if dep:
                            departures_times[stop_id].append(datetime.fromtimestamp(dep))

        return departures_times
    
    def _get_weatherapi_forecast(self):
        url = "http://api.weatherapi.com/v1/forecast.json"
        params = {
            "key": self.API_KEY,
            "q": self.LOCATION,
            "days": 2,
            "aqi": "no",
            "alerts": "no"
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    
    def _parse_weather(self, json_data):
        forecast = json_data["forecast"]

        today = forecast["forecastday"][0]

        rain = today['day']['daily_chance_of_rain']
        current_hour = datetime.now(timezone.utc).hour
        current_temp = today["hour"][current_hour]["temp_c"]
        logger.info(f"current_temp {current_temp}")
        max_temp = today["day"]["maxtemp_c"]
        min_temp = today["day"]["mintemp_c"]

        return {
            "rain": rain,
            "current_temp": current_temp,
            "max_temp": max_temp,
            "min_temp": min_temp,
        }






