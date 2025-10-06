from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageDraw, ImageFont
import logging
import requests
from google.transit import gtfs_realtime_pb2
import json
from datetime import datetime
import os
from html2image import Html2Image

logger = logging.getLogger(__name__)

class MBTA(BasePlugin):
    FEED_URL = "https://cdn.mbta.com/realtime/TripUpdates.pb"


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

        template_params = {
            "stations": stations,
            "plugin_settings": settings
        }

        return self.render_image(dimensions, "mbta.html", "mbta.css", template_params)

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





