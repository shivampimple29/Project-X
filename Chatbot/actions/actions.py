import json
import math
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# Load stations data once when actions server starts
with open('evstations.json', 'r', encoding='utf-8') as file:
    STATIONS = json.load(file)

def safe_get(data: Dict, *keys, default=""):
    """Safely get nested dictionary values"""
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError, IndexError):
            return default
    return data if data is not None else default

def format_station_basic(station: Dict) -> str:
    """Format station for basic listing"""
    name = safe_get(station, 'name', default='Unknown')
    operator = safe_get(station, 'operator', default='Unknown operator')
    
    # Get first charger details
    chargers = safe_get(station, 'chargers', default=[])
    if chargers and len(chargers) > 0:
        charger = chargers[0]
        power = safe_get(charger, 'power', default='?')
        charger_type = safe_get(charger, 'type', default='Unknown')
        available = safe_get(charger, 'availablePorts', default=0)
        return f"• {name} - {power}kW {charger_type} ({available} ports available) - {operator}"
    else:
        return f"• {name} - No charger info available - {operator}"

def format_station_details(station: Dict) -> str:
    """Format station with full details"""
    name = safe_get(station, 'name', default='Unknown')
    operator = safe_get(station, 'operator', default='Unknown')
    
    # Address
    city = safe_get(station, 'address', 'city', default='Unknown')
    state = safe_get(station, 'address', 'state', default='Unknown')
    country = safe_get(station, 'address', 'country', default='India')
    address = f"{city}, {state}, {country}"
    
    # Chargers
    chargers_text = ""
    chargers = safe_get(station, 'chargers', default=[])
    for i, charger in enumerate(chargers, 1):
        c_type = safe_get(charger, 'type', default='Unknown')
        power = safe_get(charger, 'power', default='?')
        total = safe_get(charger, 'totalPorts', default=0)
        available = safe_get(charger, 'availablePorts', default=0)
        chargers_text += f"\n    Charger {i}: {c_type} - {power}kW ({available}/{total} ports available)"
    
    if not chargers_text:
        chargers_text = "\n    No charger information available"
    
    # Status
    verified = "✅ Verified" if safe_get(station, 'isVerified', default=False) else "❌ Not verified"
    rating = safe_get(station, 'averageRating', default=0)
    review_count = safe_get(station, 'reviewCount', default=0)
    
    return f"""
📍 **{name}**
🏢 Operator: {operator}
📮 Address: {address}
{verified} | ⭐ {rating} ({review_count} reviews)
🔌 Chargers:{chargers_text}
    """

class ActionFindByCity(Action):
    """Find stations by city name"""
    
    def name(self) -> Text:
        return "action_find_by_city"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get city from slot
        city = tracker.get_slot("city")
        
        if not city:
            dispatcher.utter_message(text="Please tell me which city you want to search in.")
            return []
        
        # Filter stations by city (case-insensitive partial match)
        matching_stations = []
        for station in STATIONS:
            station_city = safe_get(station, 'address', 'city', default='').lower()
            if city.lower() in station_city:
                matching_stations.append(station)
        
        if not matching_stations:
            dispatcher.utter_message(
                text=f"Sorry, I couldn't find any charging stations in {city}. Try another city like Pune, Mumbai, or Bangalore."
            )
            return [SlotSet("city", None)]
        
        # Prepare response
        if len(matching_stations) == 1:
            response = f"I found 1 station in {city}:\n"
        else:
            response = f"I found {len(matching_stations)} stations in {city}:\n"
        
        # Show first 5 stations
        for station in matching_stations[:5]:
            response += format_station_basic(station) + "\n"
        
        if len(matching_stations) > 5:
            response += f"\n... and {len(matching_stations) - 5} more stations."
        
        dispatcher.utter_message(text=response)
        return [SlotSet("city", None)]

class ActionFindNearest(Action):
    """Find nearest station based on user location"""
    
    def name(self) -> Text:
        return "action_find_nearest"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # For demo, we'll use city to approximate location
        city = tracker.get_slot("city")
        
        if not city:
            dispatcher.utter_message(
                text="I need your location to find the nearest station. Please tell me your current city."
            )
            return []
        
        # Find stations in that city
        city_stations = []
        for station in STATIONS:
            station_city = safe_get(station, 'address', 'city', default='').lower()
            if city.lower() == station_city.lower():
                city_stations.append(station)
        
        if not city_stations:
            dispatcher.utter_message(
                text=f"I couldn't find any stations in {city}. Would you like to try another city?"
            )
            return [SlotSet("city", None)]
        
        # For demo, just return the first station
        # In production, you'd sort by actual distance
        nearest = city_stations[0]
        
        response = f"The nearest station I found in {city} is:\n"
        response += format_station_details(nearest)
        response += "\n\n(Note: For precise nearest station, please enable location sharing in your browser.)"
        
        dispatcher.utter_message(text=response)
        return [SlotSet("city", None)]

class ActionGetDetails(Action):
    """Get detailed information about a specific station"""
    
    def name(self) -> Text:
        return "action_get_details"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        station_name = tracker.get_slot("station_name")
        
        if not station_name:
            dispatcher.utter_message(text="Please tell me the name of the station you want details for.")
            return []
        
        # Search for station by name (partial match, case-insensitive)
        matches = []
        for station in STATIONS:
            name = safe_get(station, 'name', default='').lower()
            if station_name.lower() in name:
                matches.append(station)
        
        if not matches:
            dispatcher.utter_message(
                text=f"Sorry, I couldn't find a station matching '{station_name}'. Try a different name or check your spelling."
            )
            return [SlotSet("station_name", None)]
        
        # If multiple matches, show first and mention others
        station = matches[0]
        response = format_station_details(station)
        
        if len(matches) > 1:
            response += f"\n\n(I found {len(matches)} stations with similar names. Please be more specific if this isn't the right one.)"
        
        dispatcher.utter_message(text=response)
        return [SlotSet("station_name", None)]