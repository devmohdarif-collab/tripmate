import os
import re
from typing import Optional

import certifi
import airportsdata
import pycountry
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

# Default origin and destination airports
DEFAULT_ORIGIN_IATA = os.getenv("DEFAULT_ORIGIN_IATA", "DEL")
DEFAULT_DESTINATION_IATA = os.getenv("DEFAULT_DESTINATION_IATA", "BOM")
FLIBASE_URL = os.getenv("FLIGHT_BASE_URL")

airports = airportsdata.load('IATA')
COUNTRY_MAIN_AIRPORTS = {
    "India": ["DEL", "BOM", "BLR", "MAA", "HYD", "CCU", "COK", "GOI", "PNQ", "TRV"],
    "United States": ["JFK", "LAX", "ORD", "ATL", "DFW", "DEN", "SFO", "LAS", "SEA", "MIA"],
    "United Kingdom": ["LHR", "LGW", "MAN", "STN", "LTN", "EDI", "BRS", "GLA", "BHX", "SEN"],
    "Canada": ["YYZ", "YVR", "YUL", "YYC", "YEG", "YOW", "YWG", "YHZ", "YQB", "YXE"],
    "Australia": ["SYD", "MEL", "BNE", "PER", "ADL", "CNS", "HBA", "OOL", "DRW", "MCY"],
    "Germany": ["FRA", "MUC", "BER", "DUS", "HAM", "STR", "CGN", "LEJ", "BRE", "NUE"],
    "France": ["CDG", "ORY", "LYS", "NCE", "TLS", "MRS", "BOD", "NTE", "LIL", "MPL"],
    "Japan": ["NRT", "HND", "KIX", "CTS", "FUK", "NGO", "ITM", "OKA", "KOJ", "SDJ"],
    "China": ["PEK", "PVG", "CAN", "SZX", "CTU", "XIY", "HGH", "NKG", "CSX", "TAO"],
    "Brazil": ["GRU", "GIG", "BSB", "CNF", "POA", "REC", "SSA", "FOR", "CWB", "VCP"],
    "Russia": ["SVO", "LED", "DME", "KZN", "VKO", "SVX", "ROV", "KRR", "OVB", "AER", "UFA"],
    "Italy": ["FCO", "MXP", "VCE", "BLQ", "NAP", "TSF", "CIA", "PMO", "BRI", "TRN"],
    "Spain": ["MAD", "BCN", "AGP", "SVQ", "VLC", "BIO", "LEI", "ALC", "PMI", "SCQ"],
    "Mexico": ["MEX", "CUN", "GDL", "MTY", "TIJ", "CJS", "PBC", "ZIH", "LAP", "SJD"],
    "South Africa": ["JNB", "CPT", "DUR", "PLZ", "ELS", "GRJ", "MQP", "NLP", "KIM", "BFN"],
    "United Arab Emirates": ["DXB", "AUH", "SHJ", "DWC", "RKT", "FJR", "AZI", "XSB", "DHF", "KHS"],
}

CITY_MAIN_AIRPORTS = {
    "New York": ["JFK", "LGA", "EWR"],
    "Los Angeles": ["LAX", "BUR", "LGB", "ONT", "SNA"],
    "Chicago": ["ORD", "MDW"],
    "Houston": ["IAH", "HOU"],
    "Phoenix": ["PHX", "DVT"],
    "Philadelphia": ["PHL"],
    "San Antonio": ["SAT"],
    "San Diego": ["SAN"],
    "Dallas": ["DFW", "DAL"],
    "San Jose": ["SJC"],
    "Austin": ["AUS"],
    "Jacksonville": ["JAX"],
    "Fort Worth": ["DFW", "FTW"],
    "Columbus": ["CMH"],
    "Charlotte": ["CLT"],
    "San Francisco": ["SFO", "OAK", "SJC"],
    "Indianapolis": ["IND"],
    "Seattle": ["SEA"],
    "Denver": ["DEN"],
    "Washington": ["DCA", "IAD", "BWI"],
    "Boston": ["BOS"],
    "El Paso": ["ELP"],
    "Nashville": ["BNA"],
    "Detroit": ["DTW"],
    "Oklahoma City": ["OKC"],
    "Portland": ["PDX"],
    "Las Vegas": ["LAS"],
    "Memphis": ["MEM"],
    "Louisville": ["SDF"],
    "Baltimore": ["BWI"],
    "Milwaukee": ["MKE"],
}

COUNTRY_ALIASES = {
    "USA": "US",
    "United States of America": "US",
    "UK": "GB",
    "Great Britain": "GB",
    "Russia": "RU",
    "South Korea": "KR",
    "North Korea": "KP",
    "Iran": "IR",
    "Syria": "SY",
    "Venezuela": "VE",
    "Bolivia": "BO",
    "Tanzania": "TZ",
    "Moldova": "MD",
    "Laos": "LA",
    "Brunei": "BN",
    # Add more aliases as needed
}

# clean_text function to remove unwanted characters and formatting from text
def clean_text(text:str) -> str:
    """
    Cleans the input text by removing unwanted characters and formatting.
    """
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading and trailing whitespace
    stop_words = ["the", "is", "in", "and", "to", "of", "a", "for", "on", "with", "as", "by", "at", "from",'under', 'over', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once']
    text = ' '.join(word for word in text.split() if word.lower() not in stop_words)
    return text.strip()

def airport_country_match(airport_code: str, airports: dict) -> str:
    """
    Returns the country name for a given airport code.
    """
    airport = airports.get(airport_code)
    if airport:
        country_code = airport['country']
        country = pycountry.countries.get(alpha_2=country_code)
        if country:
            return country.name
    return "Unknown Country"
def country_name_to_code(text: str) -> Optional[str]:
    text = text.strip()
    normalized_text = text.casefold()
    aliases = {alias.casefold(): code for alias, code in COUNTRY_ALIASES.items()}

    if normalized_text in aliases:
        return aliases[normalized_text]

    try:
        country = pycountry.countries.lookup(text)
        return country.alpha_2
    except LookupError:
        pass

    # Detect a complete country name or alias inside longer text.
    for country in pycountry.countries:
        country_name = country.name.casefold()
        if re.search(rf"(?<!\w){re.escape(country_name)}(?!\w)", normalized_text):
            return country.alpha_2

    for alias, code in aliases.items():
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized_text):
            return code

    return None


def get_best_airport_for_country(country_name: str) -> Optional[str]:
    """
    Returns the best airport code for a given country name.
    """
    country = pycountry.countries.get(alpha_2=country_name.strip().upper())
    if country:
        country_name = country.name

    airports_by_country = {
        name.casefold(): codes for name, codes in COUNTRY_MAIN_AIRPORTS.items()
    }
    main_airports = airports_by_country.get(country_name.strip().casefold())
    if main_airports:
        return main_airports[0]  # Return the first airport as the best one
    return None

def get_best_airport_for_city(city_name: str) -> Optional[str]:
    """
    Returns the best airport code for a given city name.
    """
    airports_by_city = {
        name.casefold(): codes for name, codes in CITY_MAIN_AIRPORTS.items()
    }
    main_airports = airports_by_city.get(city_name.strip().casefold())
    if main_airports:
        return main_airports[0]  # Return the first airport as the best one
    return None

def get_flight_data(origin: str, destination: str, date: str) -> dict:
    """
    Fetches flight data from the AviationStack API for a given origin, destination, and date.
    """
    if not API_KEY:
        return {"error": "AVIATIONSTACK_API_KEY is missing."}
    if not FLIBASE_URL:
        return {"error": "FLIGHT_BASE_URL is missing."}

    params = {
        'access_key': API_KEY,
        'dep_iata': origin,
        'arr_iata': destination,
        'flight_date': date
    }
    try:
        response = requests.get(
            FLIBASE_URL, params=params, verify=certifi.where(), timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as error:
        return {"error": f"Failed to fetch flight data: {error}"}
    except ValueError:
        return {"error": "Flight API returned invalid JSON."}

def get_flight_info(origin: str, destination: str, date: str) -> dict:
    """
    Fetches flight information for a given origin, destination, and date.
    If the origin or destination is a country or city name, it finds the best airport code.
    """
    origin_iata = resolve_location_to_iata(origin)
    destination_iata = resolve_location_to_iata(destination)
    if not origin_iata:
        return {"error": f"Could not resolve origin to an airport: {origin}"}
    if not destination_iata:
        return {"error": f"Could not resolve destination to an airport: {destination}"}

    # Fetch flight data
    flight_data = get_flight_data(origin_iata, destination_iata, date)
    return flight_data

def resolve_location_to_iata(location: str) -> Optional[str]:
    """
    Resolves a location name (country, city, or airport) to its corresponding IATA code.
    """
    ## Example: If the location is "India", it will return "DEL" (the best airport in India).

    location = location.strip()

    # Resolve country aliases before checking airport codes (e.g. USA is also
    # an airport code in the dataset).
    country_code = country_name_to_code(location)
    if country_code:
        best_airport = get_best_airport_for_country(country_code)
        if best_airport:
            return best_airport

    # Check if the location is already an IATA code.
    normalized_location = location.upper()
    if normalized_location in airports:
        return normalized_location

    # Check if the location is a city name
    best_airport = get_best_airport_for_city(location)
    if best_airport:
        return best_airport

    return None

def find_location_mentions(text: str) -> list:
    """
    Finds mentions of countries, cities, or airports in the given text and returns their IATA codes.
    """
    candidates = set(COUNTRY_MAIN_AIRPORTS)
    candidates.update(CITY_MAIN_AIRPORTS)
    candidates.update(COUNTRY_ALIASES)
    candidates.update(country.name for country in pycountry.countries)

    matches = []
    for location in candidates:
        for match in re.finditer(
            rf"(?<!\w){re.escape(location)}(?!\w)", text, re.IGNORECASE
        ):
            iata_code = resolve_location_to_iata(location)
            if iata_code:
                matches.append((match.start(), -len(location), iata_code))

    # IATA codes are considered in fallback text only when explicitly uppercase.
    for match in re.finditer(r"\b[A-Z]{3}\b", text):
        iata_code = resolve_location_to_iata(match.group())
        if iata_code:
            matches.append((match.start(), -3, iata_code))

    mentions = []
    for _, _, iata_code in sorted(matches):
        if iata_code not in mentions:
            mentions.append(iata_code)
    return mentions

def parse_route(query: str):
    """
    Returns:
    dep_iata, arr_iata

    Can return:
    None, None  -> global live flights
    DAC, NRT    -> filtered route
    DAC, None   -> all flights from DAC
    None, NRT   -> all flights to NRT
    """

    q = query.strip()
    q_lower = q.lower()

    # Global / all-country query
    global_keywords = [
        "all country",
        "all countries",
        "global flight",
        "global flights",
        "all flight",
        "all flights",
        "worldwide flight",
        "worldwide flights",
    ]

    if any(keyword in q_lower for keyword in global_keywords):
        return None, None

    # Route without "from": DEL to BOM or New York to Boston.
    route_match = re.search(
        r"\b(.+?)\s+to\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q,
        re.IGNORECASE,
    )
    if route_match:
        dep_iata = resolve_location_to_iata(route_match.group(1))
        arr_iata = resolve_location_to_iata(route_match.group(2))
        if dep_iata and arr_iata:
            return dep_iata, arr_iata

    # Pattern: from X to Y
    match = re.search(
        r"\bfrom\s+(.+?)\s+\bto\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q_lower,
    )

    if match:
        origin_text = match.group(1)
        dest_text = match.group(2)

        dep_iata = resolve_location_to_iata(origin_text)
        arr_iata = resolve_location_to_iata(dest_text)

        return dep_iata, arr_iata

    # Pattern: to Y from X
    match = re.search(
        r"\bto\s+(.+?)\s+\bfrom\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q_lower,
    )

    if match:
        dest_text = match.group(1)
        origin_text = match.group(2)

        dep_iata = resolve_location_to_iata(origin_text)
        arr_iata = resolve_location_to_iata(dest_text)

        return dep_iata, arr_iata

    # Pattern: flights from X
    match = re.search(r"\bfrom\s+(.+?)(?:[.!?]|$)", q_lower)

    if match:
        origin_text = match.group(1)
        dep_iata = resolve_location_to_iata(origin_text)
        return dep_iata, None

    # Pattern: flights to X
    match = re.search(r"\bto\s+(.+?)(?:[.!?]|$)", q_lower)

    if match:
        dest_text = match.group(1)
        arr_iata = resolve_location_to_iata(dest_text)
        return None, arr_iata

    # Fallback: find country/city mentions
    mentions = find_location_mentions(q)

    if len(mentions) >= 2:
        dep_iata = resolve_location_to_iata(mentions[0])
        arr_iata = resolve_location_to_iata(mentions[1])
        return dep_iata, arr_iata

    if len(mentions) == 1:
        arr_iata = resolve_location_to_iata(mentions[0])
        return DEFAULT_ORIGIN_IATA, arr_iata

    return None, None

def format_flight(flight: dict):
    airline_data = flight.get("airline")
    flight_data = flight.get("flight")
    airline = (
        airline_data.get("name")
        if isinstance(airline_data, dict)
        else None
    ) or "Unknown airline"
    flight_number = (
        flight_data.get("iata")
        if isinstance(flight_data, dict)
        else None
    ) or "Unknown flight number"
    status = flight.get("flight_status") or "Unknown"

    dep = flight.get("departure")
    arr = flight.get("arrival")
    dep = dep if isinstance(dep, dict) else {}
    arr = arr if isinstance(arr, dict) else {}

    dep_airport = dep.get("airport") or "Unknown departure airport"
    dep_iata = dep.get("iata") or "Unknown"
    dep_terminal = dep.get("terminal") or "N/A"
    dep_gate = dep.get("gate") or "N/A"
    dep_scheduled = dep.get("scheduled") or "Unknown"
    dep_delay = dep.get("delay")
    dep_delay_text = f"{dep_delay} minutes" if dep_delay is not None else "N/A"

    arr_airport = arr.get("airport") or "Unknown arrival airport"
    arr_iata = arr.get("iata") or "Unknown"
    arr_terminal = arr.get("terminal") or "N/A"
    arr_gate = arr.get("gate") or "N/A"
    arr_scheduled = arr.get("scheduled") or "Unknown"
    arr_delay = arr.get("delay")
    arr_delay_text = f"{arr_delay} minutes" if arr_delay is not None else "N/A"

    return f"""
Airline: {airline}
Flight: {flight_number}
Status: {status}

Departure:
- Airport: {dep_airport}
- IATA: {dep_iata}
- Terminal: {dep_terminal}
- Gate: {dep_gate}
- Scheduled: {dep_scheduled}
- Delay: {dep_delay_text}

Arrival:
- Airport: {arr_airport}
- IATA: {arr_iata}
- Terminal: {arr_terminal}
- Gate: {arr_gate}
- Scheduled: {arr_scheduled}
- Delay: {arr_delay_text}
""".strip()

def search_flights(query: str, limit: int = 10):
    if not API_KEY:
        return (
            "Flight API error: AVIATIONSTACK_API_KEY is missing.\n"
            "Please add this in your .env file:\n"
            "AVIATIONSTACK_API_KEY=your_api_key_here"
        )

    if not FLIBASE_URL:
        return "Flight API error: FLIGHT_BASE_URL is missing."
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        return "Flight API error: limit must be a positive integer."

    dep_iata, arr_iata = parse_route(query)
    result_limit = min(limit, 100)

    params = {
        "access_key": API_KEY,
        "limit": result_limit,
    }

    if dep_iata:
        params["dep_iata"] = dep_iata

    if arr_iata:
        params["arr_iata"] = arr_iata

    try:
        response = requests.get(FLIBASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return f"Flight API request failed: {e}"
    except ValueError:
        return "Flight API returned invalid JSON."

    if not isinstance(data, dict):
        return "Flight API returned an unexpected response format."

    if "error" in data:
        error = data["error"]
        if isinstance(error, dict):
            return (
                "Flight API error:\n"
                f"Code: {error.get('code', 'Unknown')}\n"
                f"Message: {error.get('message', 'Unknown error')}"
            )
        return f"Flight API error: {error}"

    flight_data = data.get("data", [])
    if not isinstance(flight_data, list):
        return "Flight API returned an unexpected flight-data format."
    if any(not isinstance(flight, dict) for flight in flight_data):
        return "Flight API returned an unexpected flight record."

    if not flight_data:
        route_text = ""

        if dep_iata and arr_iata:
            route_text = f" for route {dep_iata} to {arr_iata}"
        elif dep_iata:
            route_text = f" from {dep_iata}"
        elif arr_iata:
            route_text = f" to {arr_iata}"

        return (
            f"No live flight data found{route_text}.\n\n"
            "Note: AviationStack provides live/status flight data, not ticket prices. "
            "For actual fare prices, use a flight-pricing API such as Amadeus."
        )

    route_info = "Global live flights"

    if dep_iata and arr_iata:
        route_info = f"Live flights from {dep_iata} to {arr_iata}"
    elif dep_iata:
        route_info = f"Live flights from {dep_iata}"
    elif arr_iata:
        route_info = f"Live flights to {arr_iata}"

    formatted_flights = [
        format_flight(flight) for flight in flight_data[:result_limit]
    ]

    return f"{route_info}\n\n" + "\n\n---\n\n".join(formatted_flights)


if __name__ == "__main__":
    # print(search_flights("Plan a 7 days Japan trip from Bangladesh"))
    print("\n" + "=" * 80 + "\n")
    # print(search_flights("all country flight info"))