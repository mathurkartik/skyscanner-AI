"""
Pre-populated coordinates for top global travel destinations.
Used as instant local geocoding cache before falling back to Google Places.
"""

CITY_COORDS = {
    # Europe
    "paris": (48.8566, 2.3522),
    "london": (51.5074, -0.1278),
    "rome": (41.9028, 12.4964),
    "barcelona": (41.3879, 2.16992),
    "madrid": (40.4168, -3.7038),
    "amsterdam": (52.3676, 4.9041),
    "berlin": (52.5200, 13.4050),
    "munich": (48.1351, 11.5820),
    "frankfurt": (50.1109, 8.6821),
    "vienna": (48.2082, 16.3738),
    "prague": (50.0755, 14.4378),
    "budapest": (47.4979, 19.0402),
    "zurich": (47.3769, 8.5417),
    "geneva": (46.2044, 6.1432),
    "lucerne": (47.0502, 8.3093),
    "interlaken": (46.6863, 7.8632),
    "zermatt": (45.9765, 7.7491),
    "stockholm": (59.3293, 18.0686),
    "gothenburg": (57.7089, 11.9746),
    "malmo": (55.6050, 13.0038),
    "malmö": (55.6050, 13.0038),
    "kiruna": (67.8558, 20.2253),
    "abisko": (68.3495, 18.8312),
    "uppsala": (59.8586, 17.6389),
    "mora": (61.0049, 14.5370),
    "oslo": (59.9139, 10.7522),
    "bergen": (60.3913, 5.3221),
    "tromso": (69.6492, 18.9553),
    "copenhagen": (55.6761, 12.5683),
    "helsinki": (60.1699, 24.9384),
    "reykjavik": (64.1466, -21.9426),
    "vik": (63.4186, -19.0060),
    "akureyri": (65.6885, -18.1262),
    "hofn": (64.2539, -15.2082),
    "dublin": (53.3498, -6.2603),
    "edinburgh": (55.9533, -3.1883),
    "lisbon": (38.7223, -9.1393),
    "porto": (41.1579, -8.6291),
    "athens": (37.9838, 23.7275),
    "santorini": (36.3932, 25.4615),
    "mykonos": (37.4467, 25.3289),
    "venice": (45.4408, 12.3155),
    "florence": (43.7696, 11.2558),
    "milan": (45.4642, 9.1900),
    "naples": (40.8518, 14.2681),
    "dubrovnik": (42.6507, 18.0944),
    "split": (43.5081, 16.4402),
    "istanbul": (41.0082, 28.9784),
    "tbilisi": (41.7151, 44.8271),
    "batumi": (41.6168, 41.6367),

    # Asia & Middle East
    "tokyo": (35.6762, 139.6503),
    "kyoto": (35.0116, 135.7681),
    "osaka": (34.6937, 135.5023),
    "sapporo": (43.0618, 141.3545),
    "fukuoka": (33.5904, 130.4017),
    "seoul": (37.5665, 126.9780),
    "busan": (35.1796, 129.0756),
    "bangkok": (13.7563, 100.5018),
    "phuket": (7.8804, 98.3923),
    "chiang mai": (18.7883, 98.9853),
    "krabi": (8.0863, 98.9063),
    "singapore": (1.3521, 103.8198),
    "kuala lumpur": (3.1390, 101.6869),
    "bali": (-8.3405, 115.0920),
    "ubud": (-8.5069, 115.2625),
    "jakarta": (-6.2088, 106.8456),
    "hanoi": (21.0285, 105.8542),
    "ho chi minh city": (10.8231, 106.6297),
    "da nang": (16.0544, 108.2022),
    "manila": (14.5995, 120.9842),
    "dubai": (25.2048, 55.2708),
    "abu dhabi": (24.4539, 54.3773),
    "doha": (25.2854, 51.5310),
    "riyadh": (24.7136, 46.6753),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "jaipur": (26.9124, 75.7873),
    "goa": (15.2993, 74.1240),
    "varanasi": (25.3176, 82.9739),
    "rishikesh": (30.0869, 78.2676),
    "agra": (27.1767, 78.0081),
    "udaipur": (24.5854, 73.7125),
    "pondicherry": (11.9416, 79.8083),
    "puducherry": (11.9416, 79.8083),
    "kerala": (10.8505, 76.2711),
    "kochi": (9.9312, 76.2673),
    "munnar": (10.0889, 77.0595),
    "sikkim": (27.5330, 88.5122),
    "gangtok": (27.3314, 88.6138),
    "kathmandu": (27.7172, 85.3240),
    "pokhara": (28.2096, 83.9856),
    "colombo": (6.9271, 79.8612),

    # Americas
    "new york": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "san francisco": (37.7749, -122.4194),
    "las vegas": (36.1699, -115.1398),
    "chicago": (41.8781, -87.6298),
    "miami": (25.7617, -80.1918),
    "orlando": (28.5383, -81.3792),
    "seattle": (47.6062, -122.3321),
    "boston": (42.3601, -71.0589),
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    "montreal": (45.5017, -73.5673),
    "cancun": (21.1619, -86.8515),
    "mexico city": (19.4326, -99.1332),
    "rio de janeiro": (-22.9068, -43.1729),
    "sao paulo": (-23.5505, -46.6333),
    "são paulo": (-23.5505, -46.6333),
    "buenos aires": (-34.6037, -58.3816),
    "lima": (-12.0464, -77.0428),
    "cusco": (-13.5319, -71.9675),

    # Oceania & Africa
    "sydney": (-33.8688, 151.2093),
    "melbourne": (-37.8136, 144.9631),
    "brisbane": (-27.4698, 153.0251),
    "perth": (-31.9505, 115.8605),
    "auckland": (-36.8485, 174.7633),
    "queenstown": (-45.0312, 168.6626),
    "christchurch": (-43.5321, 172.6362),
    "cairo": (30.0444, 31.2357),
    "cape town": (-33.9249, 18.4241),
    "johannesburg": (-26.2041, 28.0473),
    "nairobi": (-1.2921, 36.8219),
    "marrakech": (31.6295, -7.9811),
    "casablanca": (33.5731, -7.5898),
}


def get_city_coords(city: str) -> tuple[float, float] | None:
    """Retrieve latitude and longitude for a city name from the curated directory."""
    if not city:
        return None
    c = city.lower().strip()
    if c in CITY_COORDS:
        return CITY_COORDS[c]
    for k, v in CITY_COORDS.items():
        if k in c or c in k:
            return v
    return None


# Primary Commercial Airport Coordinates (AG-021)
# Prevents airport pins from being placed on tourist attractions.
AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    # India & South Asia
    "DEL": (28.5562, 77.1000), "BOM": (19.0896, 72.8656), "BLR": (13.1986, 77.7066),
    "HYD": (17.2403, 78.4294), "MAA": (12.9941, 80.1709), "CCU": (22.6547, 88.4467),
    "JAI": (26.8242, 75.8122), "GOI": (15.3808, 73.8314), "GOX": (15.7533, 73.8683),
    "AMD": (23.0734, 72.6347), "COK": (10.1520, 76.4019), "KTM": (27.6966, 85.3591),
    "CMB": (7.1808, 79.8841),

    # Europe & Iceland
    "KEF": (63.9850, -22.6056), "LHR": (51.4700, -0.4543), "LGW": (51.1537, -0.1821),
    "CDG": (49.0097, 2.5479), "ORY": (48.7262, 2.3652), "AMS": (52.3105, 4.7683),
    "FRA": (50.0379, 8.5622), "MUC": (48.3537, 11.7750), "ZRH": (47.4582, 8.5555),
    "GVA": (46.2370, 6.1092), "FCO": (41.8003, 12.2389), "MXP": (45.6301, 8.7255),
    "BCN": (41.2974, 2.0833), "MAD": (40.4839, -3.5680), "VIE": (48.1103, 16.5697),
    "PRG": (50.1008, 14.2600), "BUD": (47.4369, 19.2556), "DUB": (53.4264, -6.2499),
    "EDI": (55.9508, -3.3725), "LIS": (38.7756, -9.1354), "OPO": (41.2481, -8.6814),
    "ATH": (37.9364, 23.9445), "IST": (41.2753, 28.7519), "CPH": (55.6180, 12.6508),
    "ARN": (59.6498, 17.9238), "OSL": (60.1976, 11.1004), "HEL": (60.3172, 24.9633),
    "TBS": (41.6692, 44.9547),

    # Americas
    "JFK": (40.6413, -73.7781), "EWR": (40.6895, -74.1745), "LGA": (40.7769, -73.8740),
    "BOS": (42.3656, -71.0096), "ORD": (41.9742, -87.9073), "LAX": (33.9416, -118.4085),
    "SFO": (37.6213, -122.3790), "SEA": (47.4502, -122.3088), "MIA": (25.7959, -80.2870),
    "MCO": (28.4312, -81.3081), "LAS": (36.0840, -115.1537), "DFW": (32.8998, -97.0403),
    "ATL": (33.6407, -84.4277), "YYZ": (43.6777, -79.6248), "YVR": (49.1967, -123.1815),
    "YUL": (45.4657, -73.7455), "MEX": (19.4361, -99.0719), "CUN": (21.0365, -86.8771),
    "GRU": (-23.4356, -46.4731), "GIG": (-22.8134, -43.2494), "EZE": (-34.8222, -58.5358),
    "LIM": (-12.0219, -77.1143),

    # Asia-Pacific & Middle East
    "HND": (35.5494, 139.7798), "NRT": (35.7720, 140.3929), "KIX": (34.4320, 135.2304),
    "CTS": (42.7752, 141.6923), "FUK": (33.5859, 130.4507), "ICN": (37.4602, 126.4407),
    "PUS": (35.1795, 128.9382), "SIN": (1.3644, 103.9915), "BKK": (13.6900, 100.7501),
    "DMK": (13.9126, 100.6067), "HKT": (8.1132, 98.3169), "CNX": (18.7713, 98.9626),
    "KUL": (2.7456, 101.7072), "DPS": (-8.7482, 115.1672), "CGK": (-6.1275, 106.6537),
    "HAN": (21.2212, 105.8072), "SGN": (10.8188, 106.6518), "MNL": (14.5086, 121.0194),
    "SYD": (-33.9399, 151.1753), "MEL": (-37.6690, 144.8410), "BNE": (-27.3942, 153.1218),
    "PER": (-31.9403, 115.9668), "AKL": (-37.0082, 174.7850), "ZQN": (-45.0216, 168.7392),
    "CHC": (-43.4894, 172.5322), "DXB": (25.2532, 55.3657), "AUH": (24.4330, 54.6511),
    "DOH": (25.2731, 51.6081), "RUH": (24.9576, 46.6988),

    # Africa
    "CAI": (30.1219, 31.4056), "JNB": (-26.1367, 28.2411), "CPT": (-33.9715, 18.6021),
    "NBO": (-1.3192, 36.9275), "RAK": (31.6069, -8.0363), "CMN": (33.3675, -7.5898),
}


def get_airport_coords(iata_or_city: str) -> tuple[float, float] | None:
    """
    Retrieve commercial airport coordinates by IATA code or city name (AG-021).
    Falls back to city center coordinates if airport not specifically indexed.
    """
    if not iata_or_city:
        return None
    clean = iata_or_city.strip()
    upper_code = clean.upper()
    if upper_code in AIRPORT_COORDS:
        return AIRPORT_COORDS[upper_code]

    # Resolve city name to IATA if applicable
    from .airports import lookup_iata_code
    resolved_iata = lookup_iata_code(clean)
    if resolved_iata and resolved_iata in AIRPORT_COORDS:
        return AIRPORT_COORDS[resolved_iata]

    # Fall back to city center coordinates
    return get_city_coords(clean)

