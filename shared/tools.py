import random
import requests
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

# Mock restaurant database (tidak butuh API key)
RESTAURANTS_DB = [
    {"id": 1, "name": "Sakura Garden", "city": "Tokyo", "cuisine": "Japanese", "price_per_person": 25, "rating": 4.8, "capacity": 40},
    {"id": 2, "name": "Ramen House Ichiban", "city": "Tokyo", "cuisine": "Ramen", "price_per_person": 15, "rating": 4.5, "capacity": 30},
    {"id": 3, "name": "Nobu Osaka", "city": "Osaka", "cuisine": "Fusion", "price_per_person": 60, "rating": 4.9, "capacity": 50},
    {"id": 4, "name": "Takoyaki Street", "city": "Osaka", "cuisine": "Street Food", "price_per_person": 10, "rating": 4.3, "capacity": 20},
    {"id": 5, "name": "Sushi Zanmai", "city": "Kyoto", "cuisine": "Sushi", "price_per_person": 40, "rating": 4.7, "capacity": 35},
    {"id": 6, "name": "Kyoto Kaiseki", "city": "Kyoto", "cuisine": "Traditional Japanese", "price_per_person": 80, "rating": 4.9, "capacity": 25},
    {"id": 7, "name": "Hakata Ramen", "city": "Fukuoka", "cuisine": "Ramen", "price_per_person": 12, "rating": 4.6, "capacity": 30},
    {"id": 8, "name": "Tempura Tenichi", "city": "Tokyo", "cuisine": "Tempura", "price_per_person": 35, "rating": 4.6, "capacity": 45},
]


@tool
def query_restaurants(city: str, cuisine: str = None) -> str:
    """Search for available restaurants in a city, optionally filtered by cuisine type.

    Args:
        city: City name to search restaurants in
        cuisine: Type of cuisine to filter by (optional, e.g. 'Sushi', 'Ramen')

    Returns:
        List of available restaurants with pricing and ratings
    """
    results = [r for r in RESTAURANTS_DB if r["city"].lower() == city.lower()]

    if cuisine:
        results = [r for r in results if cuisine.lower() in r["cuisine"].lower()]

    if not results:
        return f"No restaurants found in {city}" + (f" for cuisine '{cuisine}'" if cuisine else "") + "."

    formatted = []
    for r in results:
        formatted.append(
            f"ID:{r['id']} | {r['name']} | Cuisine: {r['cuisine']}"
            f" | ${r['price_per_person']}/person | {r['rating']} stars"
            f" | Capacity: {r['capacity']} people"
        )
    return "\n".join(formatted)


@tool
def calculate_bill_estimate(price_per_person: float, num_guests: int, tip_rate: float = 0.10) -> str:
    """Calculate total restaurant bill estimate including tip.

    Args:
        price_per_person: Average price per person
        num_guests: Number of guests
        tip_rate: Tip rate (default 10%)

    Returns:
        Detailed bill breakdown
    """
    subtotal = price_per_person * num_guests
    tip = subtotal * tip_rate
    total = subtotal + tip

    return f"""Bill Estimate:
- Price per person: ${price_per_person:.2f} x {num_guests} guests = ${subtotal:.2f}
- Tip ({tip_rate * 100:.0f}%): ${tip:.2f}
- Total: ${total:.2f}"""


@tool
def get_weather(city: str, date: str = None) -> str:
    """Get weather information for a city.

    Args:
        city: Name of the city
        date: Date in YYYY-MM-DD format (optional, defaults to today)

    Returns:
        Weather information including temperature and conditions
    """
    try:
        geocoding_url = (
            f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        )
        geo_response = requests.get(geocoding_url)
        geo_response.raise_for_status()

        geo_data = geo_response.json()
        if not geo_data.get("results"):
            return f"Error: City '{city}' not found"

        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current_weather=true"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            f"&timezone=auto"
        )

        if date:
            weather_url += f"&start_date={date}&end_date={date}"

        weather_response = requests.get(weather_url)
        weather_response.raise_for_status()

        data = weather_response.json()
        current = data.get("current_weather", {})
        daily = data.get("daily", {})

        result = f"Weather in {city}"
        if date and daily.get("time"):
            result += f" on {date}:\n"
            result += f"High: {daily['temperature_2m_max'][0]}°C\n"
            result += f"Low: {daily['temperature_2m_min'][0]}°C\n"
            result += f"Precipitation: {daily['precipitation_sum'][0]}mm"
        else:
            result += f" (current):\n"
            result += f"Temperature: {current.get('temperature', 'N/A')}°C\n"
            result += f"Wind Speed: {current.get('windspeed', 'N/A')} km/h"

        return result
    except Exception as e:
        return f"Error: Failed to get weather - {str(e)}"


@tool
def make_reservation(restaurant_id: int, guest_name: str, num_guests: int, date: str, time: str) -> str:
    """Make a restaurant reservation.

    Args:
        restaurant_id: The ID of the restaurant (from query_restaurants results)
        guest_name: Name of the person making the reservation
        num_guests: Number of guests
        date: Reservation date in YYYY-MM-DD format
        time: Reservation time in HH:MM format (e.g. '19:00')

    Returns:
        Reservation confirmation details
    """
    restaurant = next((r for r in RESTAURANTS_DB if r["id"] == restaurant_id), None)

    if not restaurant:
        return f"Error: Restaurant with ID {restaurant_id} not found."

    if num_guests > restaurant["capacity"]:
        return f"Error: {restaurant['name']} can only accommodate up to {restaurant['capacity']} guests."

    reservation_id = random.randint(10000, 99999)

    return (
        f"Reservation confirmed!\n"
        f"- Reservation ID: {reservation_id}\n"
        f"- Restaurant: {restaurant['name']} ({restaurant['city']})\n"
        f"- Guest: {guest_name}\n"
        f"- Guests: {num_guests} people\n"
        f"- Date & Time: {date} at {time}\n"
        f"- Estimated bill: ~${restaurant['price_per_person'] * num_guests:.2f} (before tip)"
    )


web_search = DuckDuckGoSearchRun()
