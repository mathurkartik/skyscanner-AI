"""
HotelClient - Booking.com RapidAPI client for real accommodation data.
Phase 2: Destination resolution, live hotel search, coordinate search, caching, and realistic fallback.
"""

import asyncio
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from ..config import get_settings
from ..models.schemas import RealHotelOffer

logger = logging.getLogger(__name__)

# Pre-cached destination IDs for instant lookup & offline reliability
KNOWN_DESTINATIONS: Dict[str, Dict[str, Any]] = {
    "reykjavik": {"dest_id": "-2646452", "dest_type": "city", "label": "Reykjavik, Capital Region, Iceland", "lat": 64.1466, "lng": -21.9426},
    "vik": {"dest_id": "-2646892", "dest_type": "city", "label": "Vík, South Iceland, Iceland", "lat": 63.4186, "lng": -19.0060},
    "akureyri": {"dest_id": "-2641512", "dest_type": "city", "label": "Akureyri, Northeast Iceland, Iceland", "lat": 65.6835, "lng": -18.0878},
    "tokyo": {"dest_id": "-246227", "dest_type": "city", "label": "Tokyo, Kanto, Japan", "lat": 35.6762, "lng": 139.6503},
    "kyoto": {"dest_id": "-235553", "dest_type": "city", "label": "Kyoto, Kansai, Japan", "lat": 35.0116, "lng": 135.7681},
    "osaka": {"dest_id": "-240905", "dest_type": "city", "label": "Osaka, Kansai, Japan", "lat": 34.6937, "lng": 135.5023},
    "zurich": {"dest_id": "-2554988", "dest_type": "city", "label": "Zürich, Canton of Zurich, Switzerland", "lat": 47.3769, "lng": 8.5417},
    "london": {"dest_id": "-2601889", "dest_type": "city", "label": "London, Greater London, United Kingdom", "lat": 51.5074, "lng": -0.1278},
    "paris": {"dest_id": "-1456928", "dest_type": "city", "label": "Paris, Île-de-France, France", "lat": 48.8566, "lng": 2.3522},
    "rome": {"dest_id": "-126693", "dest_type": "city", "label": "Rome, Lazio, Italy", "lat": 41.9028, "lng": 12.4964},
    "melbourne": {"dest_id": "-1586835", "dest_type": "city", "label": "Melbourne, Victoria, Australia", "lat": -37.8136, "lng": 144.9631},
    "sydney": {"dest_id": "-1603135", "dest_type": "city", "label": "Sydney, New South Wales, Australia", "lat": -33.8688, "lng": 151.2093},
    "singapore": {"dest_id": "-73635", "dest_type": "city", "label": "Singapore, Singapore", "lat": 1.3521, "lng": 103.8198},
    "dubai": {"dest_id": "-782831", "dest_type": "city", "label": "Dubai, Emirate of Dubai, United Arab Emirates", "lat": 25.2048, "lng": 55.2708},
"lyon": {"dest_id": "-1448471", "dest_type": "city", "label": "Lyon, Auvergne-Rhône-Alpes, France", "lat": 45.7640, "lng": 4.8357},
    "nice": {"dest_id": "-1455208", "dest_type": "city", "label": "Nice, Provence-Alpes-Côte d'Azur, France", "lat": 43.7102, "lng": 7.2620},
    "barcelona": {"dest_id": "-372490", "dest_type": "city", "label": "Barcelona, Catalonia, Spain", "lat": 41.3851, "lng": 2.1734},
    "madrid": {"dest_id": "-390625", "dest_type": "city", "label": "Madrid, Community of Madrid, Spain", "lat": 40.4168, "lng": -3.7038},
    "amsterdam": {"dest_id": "-2140479", "dest_type": "city", "label": "Amsterdam, North Holland, Netherlands", "lat": 52.3676, "lng": 4.9041},
    "bangkok": {"dest_id": "-3414440", "dest_type": "city", "label": "Bangkok, Bangkok Province, Thailand", "lat": 13.7563, "lng": 100.5018},
    "bali": {"dest_id": "-2679652", "dest_type": "city", "label": "Bali, Indonesia", "lat": -8.4095, "lng": 115.1889},
    "new york": {"dest_id": "20088325", "dest_type": "city", "label": "New York, New York State, United States", "lat": 40.7128, "lng": -74.0060},
    "moscow": {"dest_id": "-2960561", "dest_type": "city", "label": "Moscow, Central Federal District, Russia", "lat": 55.7558, "lng": 37.6173},
    "saint petersburg": {"dest_id": "-2999464", "dest_type": "city", "label": "Saint Petersburg, Northwestern Federal District, Russia", "lat": 59.9343, "lng": 30.3351},
    "murmansk": {"dest_id": "-2961556", "dest_type": "city", "label": "Murmansk, Murmansk Oblast, Russia", "lat": 68.9585, "lng": 33.0827},
    "lucerne": {"dest_id": "-2552882", "dest_type": "city", "label": "Lucerne, Canton of Lucerne, Switzerland", "lat": 47.0502, "lng": 8.3093},
    "interlaken": {"dest_id": "-2552467", "dest_type": "city", "label": "Interlaken, Bern, Switzerland", "lat": 46.6863, "lng": 7.8632},
}

# Curated high-fidelity hotel inventory for reliable demo fallback
CURATED_HOTELS: Dict[str, List[Dict[str, Any]]] = {
    "reykjavik": [
        {
            "name": "SM Hostel",
            "price_per_night": 112.0,
            "star_rating": 3.0,
            "guest_rating": 8.4,
            "review_count": 890,
            "neighborhood": "Vesturbær",
            "address": "Kaplaskjólsvegur, 107 Reykjavík",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Free WiFi", "Shared Kitchen", "Luggage Storage", "Heating"]
        },
        {
            "name": "B18 Apartments",
            "price_per_night": 200.0,
            "star_rating": 4.0,
            "guest_rating": 9.1,
            "review_count": 420,
            "neighborhood": "Miðborg (Downtown)",
            "address": "Barónsstígur 18, 101 Reykjavík",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Kitchenette", "Balcony", "Free WiFi", "Espresso Machine"]
        },
        {
            "name": "Center Hotels Plaza",
            "price_per_night": 245.0,
            "star_rating": 4.0,
            "guest_rating": 8.6,
            "review_count": 2150,
            "neighborhood": "Old Town",
            "address": "Aðalstræti 4-6, 101 Reykjavík",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Bar", "Buffet Breakfast", "Airport Shuttle", "24-Hour Front Desk"]
        },
        {
            "name": "Kex Hostel",
            "price_per_night": 85.0,
            "star_rating": 2.5,
            "guest_rating": 8.7,
            "review_count": 3400,
            "neighborhood": "Harbor Front",
            "address": "Skúlagata 28, 101 Reykjavík",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Craft Beer Bar", "Live Music", "Free WiFi", "Ocean View Terrace"]
        }
    ],
    "vik": [
        {
            "name": "Guesthouse Carina",
            "price_per_night": 145.0,
            "star_rating": 3.0,
            "guest_rating": 8.9,
            "review_count": 780,
            "neighborhood": "Vik Village Hill",
            "address": "Sunnuvegur 26, 870 Vík",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Black Beach Views", "Free Breakfast", "Free Parking", "Free WiFi"]
        },
        {
            "name": "Hotel Kría",
            "price_per_night": 220.0,
            "star_rating": 4.0,
            "guest_rating": 9.0,
            "review_count": 1320,
            "neighborhood": "Vik Center",
            "address": "Sléttuvegur 12-14, 870 Vík",
            "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Mountain Views", "Drangar Restaurant", "Bar", "Cocktail Lounge"]
        },
        {
            "name": "The Barn Hostel Vik",
            "price_per_night": 90.0,
            "star_rating": 3.0,
            "guest_rating": 9.2,
            "review_count": 1950,
            "neighborhood": "Reynisfjara Road",
            "address": "Norður-Vík, 870 Vík",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Modern Bunks", "Kitchen", "Social Bar", "Free Parking"]
        }
    ],
    "akureyri": [
        {
            "name": "Hotel Kea by Keahotels",
            "price_per_night": 165.0,
            "star_rating": 4.0,
            "guest_rating": 8.5,
            "review_count": 1100,
            "neighborhood": "Akureyri Town Square",
            "address": "Hafnarstræti 87-89, 600 Akureyri",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Múlaberg Bistro", "Cocktail Bar", "Free WiFi", "Church Steps View"]
        },
        {
            "name": "Akureyri Backpackers",
            "price_per_night": 75.0,
            "star_rating": 2.5,
            "guest_rating": 8.8,
            "review_count": 1650,
            "neighborhood": "Pedestrian Street",
            "address": "Hafnarstræti 98, 600 Akureyri",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Café & Bar", "Sauna", "Guest Kitchen", "Tour Desk"]
        },
        {
            "name": "Hafdals Hotel",
            "price_per_night": 190.0,
            "star_rating": 3.5,
            "guest_rating": 9.4,
            "review_count": 480,
            "neighborhood": "Fjord Overlook",
            "address": "Hafnarsveit, 601 Akureyri",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Panoramic Fjord Views", "Aurora Borealis Terrace", "Free Breakfast"]
        }
    ],
    "tokyo": [
        {
            "name": "Park Hyatt Tokyo",
            "price_per_night": 620.0,
            "star_rating": 5.0,
            "guest_rating": 9.3,
            "review_count": 2100,
            "neighborhood": "Shinjuku",
            "address": "3-7-1-2 Nishi-Shinjuku, Shinjuku-ku, Tokyo",
            "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop&q=80",
            "amenities": ["New York Grill", "Spa & Pool", "Mount Fuji View", "Concierge"]
        },
        {
            "name": "Hotel Gracery Shinjuku",
            "price_per_night": 185.0,
            "star_rating": 4.0,
            "guest_rating": 8.6,
            "review_count": 5200,
            "neighborhood": "Kabukicho, Shinjuku",
            "address": "1-19-1 Kabukicho, Shinjuku-ku, Tokyo",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Godzilla Head Terrace", "Free High-Speed WiFi", "Restaurant", "Metro 5m"]
        },
        {
            "name": "Candeo Hotels Tokyo Shimbashi",
            "price_per_night": 170.0,
            "star_rating": 4.0,
            "guest_rating": 8.8,
            "review_count": 1800,
            "neighborhood": "Ginza / Shimbashi",
            "address": "3-6-8 Shimbashi, Minato-ku, Tokyo",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Rooftop SkySpa Onsen", "Open-Air Bath", "Tokyo Tower Views"]
        }
    ],
    "kyoto": [
        {
            "name": "Kyoto Ryokan Gion Sano",
            "price_per_night": 280.0,
            "star_rating": 4.5,
            "guest_rating": 9.4,
            "review_count": 620,
            "neighborhood": "Gion Historic District",
            "address": "504 Washio-cho, Higashiyama-ku, Kyoto",
            "image_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Tatami Rooms", "Kaiseki Breakfast", "Hinoki Wood Bath", "Garden View"]
        },
        {
            "name": "The Thousand Kyoto",
            "price_per_night": 310.0,
            "star_rating": 5.0,
            "guest_rating": 9.2,
            "review_count": 1400,
            "neighborhood": "Kyoto Station",
            "address": "570 Higashishiokoji-cho, Shimogyo-ku, Kyoto",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Tea Ceremony Room", "Spa", "Fine Dining", "Direct Station Access"]
        },
        {
            "name": "Piece Hostel Sanjo",
            "price_per_night": 75.0,
            "star_rating": 3.0,
            "guest_rating": 9.3,
            "review_count": 2800,
            "neighborhood": "Sanjo / Downtown",
            "address": "531 Asakura-cho, Nakagyo-ku, Kyoto",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Terrace Bar", "Free Continental Breakfast", "Bike Rental", "Library"]
        }
    ],
"paris": [
        {
            "name": "Generator Paris",
            "price_per_night": 68.0,
            "star_rating": 3.0,
            "guest_rating": 8.3,
            "review_count": 4200,
            "neighborhood": "Canal Saint-Martin / 10th Arr.",
            "address": "9-11 Place du Colonel Fabien, 75010 Paris",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Rooftop Bar with Sacré-Cœur Views", "Free WiFi", "Metro Access", "24/7 Desk"]
        },
        {
            "name": "CitizenM Paris Gare de Lyon",
            "price_per_night": 165.0,
            "star_rating": 4.0,
            "guest_rating": 8.9,
            "review_count": 3100,
            "neighborhood": "Gare de Lyon / 12th Arr.",
            "address": "8 Rue Van Gogh, 75012 Paris",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Mood Lighting & iPad Controls", "Rooftop CloudM Bar", "Rain Showers", "Free High-Speed WiFi"]
        },
        {
            "name": "Pullman Paris Tour Eiffel",
            "price_per_night": 340.0,
            "star_rating": 4.5,
            "guest_rating": 9.1,
            "review_count": 2850,
            "neighborhood": "Eiffel Tower / 15th Arr.",
            "address": "18 Avenue De Suffren, 75015 Paris",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Direct Eiffel Tower Balcony Views", "FR/AME French Brasserie", "Fitness Lounge", "Concierge"]
        }
    ],
    "lyon": [
        {
            "name": "Away Hostel & Coffee Shop",
            "price_per_night": 55.0,
            "star_rating": 3.0,
            "guest_rating": 8.8,
            "review_count": 1850,
            "neighborhood": "Presqu'île / 1st Arr.",
            "address": "21 Rue Alsace Lorraine, 69001 Lyon",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Artisan Coffee Shop", "Free WiFi", "Historic 19th Century Building", "Shared Kitchen"]
        },
        {
            "name": "Hôtel Silky by HappyCulture",
            "price_per_night": 135.0,
            "star_rating": 4.0,
            "guest_rating": 8.7,
            "review_count": 1200,
            "neighborhood": "Presqu'île Downtown",
            "address": "2 Place Francisque Régaud, 69002 Lyon",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Boutique Silk Heritage Decor", "Nespresso Bar", "Afternoon Wine Tasting", "Air Conditioning"]
        },
        {
            "name": "Villa Florentine & Spa",
            "price_per_night": 310.0,
            "star_rating": 5.0,
            "guest_rating": 9.3,
            "review_count": 920,
            "neighborhood": "Vieux Lyon / Fourvière",
            "address": "25 Montée Saint-Barthélémy, 69005 Lyon",
            "image_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Panoramic Heated Rooftop Pool", "Michelin-Starred Restaurant", "Sauna & Hammam", "Old Lyon Views"]
        }
    ],
    "nice": [
        {
            "name": "Villa Saint Exupéry Beach",
            "price_per_night": 58.0,
            "star_rating": 3.0,
            "guest_rating": 8.5,
            "review_count": 2400,
            "neighborhood": "Old Town / Port",
            "address": "6 Rue Sacha Guitry, 06000 Nice",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["50m to Promenade des Anglais", "Beach Equipment", "Social Bar & Lounge", "Free WiFi"]
        },
        {
            "name": "Hôtel Suisse",
            "price_per_night": 165.0,
            "star_rating": 4.0,
            "guest_rating": 8.9,
            "review_count": 1650,
            "neighborhood": "Promenade des Anglais",
            "address": "15 Quai Rauba Capeu, 06300 Nice",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Unobstructed Baie des Anges Sea Views", "Italian-Style Architecture", "Balconies", "Breakfast on Terrace"]
        },
        {
            "name": "Le Negresco",
            "price_per_night": 380.0,
            "star_rating": 5.0,
            "guest_rating": 9.2,
            "review_count": 2100,
            "neighborhood": "Promenade des Anglais",
            "address": "37 Promenade des Anglais, 06000 Nice",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Iconic Belle Époque Palace", "Private Beach Club", "Chantecler Michelin Dining", "Curated Art Collection"]
        }
    ],
    "london": [
        {
            "name": "Wombat's City Hostel London",
            "price_per_night": 65.0,
            "star_rating": 3.0,
            "guest_rating": 8.7,
            "review_count": 3900,
            "neighborhood": "Tower Bridge / Aldgate",
            "address": "7 Dock Street, London E1 8LL",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Historic Victorian Brewery", "Wombar Lounge", "Courtyard", "Free High-Speed WiFi"]
        },
        {
            "name": "The Hoxton, Holborn",
            "price_per_night": 185.0,
            "star_rating": 4.0,
            "guest_rating": 8.9,
            "review_count": 2200,
            "neighborhood": "Holborn / Covent Garden",
            "address": "199-206 High Holborn, London WC1V 7BD",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Boutique Retro Style", "Rondo Restaurant", "Walk to West End Theatres", "Pet Friendly"]
        },
        {
            "name": "The Savoy",
            "price_per_night": 460.0,
            "star_rating": 5.0,
            "guest_rating": 9.4,
            "review_count": 3100,
            "neighborhood": "Strand / Covent Garden",
            "address": "Strand, London WC2R 0EZ",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Iconic River Thames Views", "American Bar (World's Best Bar)", "Gordon Ramsay Grill", "Butler Service"]
        }
    ],
    "rome": [
        {
            "name": "The RomeHello",
            "price_per_night": 55.0,
            "star_rating": 3.0,
            "guest_rating": 9.2,
            "review_count": 3100,
            "neighborhood": "Repubblica / Monti",
            "address": "Via Torino 45, 00184 Rome",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Street Art Murals", "Courtyard Garden Bar", "Live Music Events", "Walk to Colosseum"]
        },
        {
            "name": "Hotel Artemide",
            "price_per_night": 165.0,
            "star_rating": 4.0,
            "guest_rating": 9.3,
            "review_count": 2800,
            "neighborhood": "Via Nazionale",
            "address": "Via Nazionale 22, 00184 Rome",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Panoramic Ambrosia Rooftop Bar", "Artemis Spa & Turkish Bath", "Free Minibar", "Complimentary Breakfast"]
        },
        {
            "name": "Hotel Hassler Roma",
            "price_per_night": 420.0,
            "star_rating": 5.0,
            "guest_rating": 9.4,
            "review_count": 1400,
            "neighborhood": "Spanish Steps",
            "address": "Piazza Trinità dei Monti 6, 00187 Rome",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Top of the Spanish Steps", "Imàgo Michelin Dining", "Panoramic Terraces", "Luxury Wellness Suite"]
        }
    ],
    "barcelona": [
        {
            "name": "Yeah Hostel Barcelona",
            "price_per_night": 52.0,
            "star_rating": 3.0,
            "guest_rating": 9.3,
            "review_count": 3400,
            "neighborhood": "Eixample / Gràcia",
            "address": "Carrer de Girona 176, 08037 Barcelona",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Rooftop Plunge Pool", "Communal Tapas Dinners", "Walk to Sagrada Família", "Bar & Terrace"]
        },
        {
            "name": "Room Mate Gerard",
            "price_per_night": 145.0,
            "star_rating": 4.0,
            "guest_rating": 8.9,
            "review_count": 1900,
            "neighborhood": "Fort Pienc / Eixample",
            "address": "Carrer d'Ausiàs Marc 49, 08010 Barcelona",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Rooftop Sun Terrace & Pool", "Jaime Beriestain Designer Interiors", "Gym", "Buffet Breakfast"]
        },
        {
            "name": "W Barcelona",
            "price_per_night": 350.0,
            "star_rating": 5.0,
            "guest_rating": 8.8,
            "review_count": 3800,
            "neighborhood": "Barceloneta Beach",
            "address": "Plaça de la Rosa dels Vents 1, 08039 Barcelona",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Iconic Sail Tower on Beachfront", "WET Deck Infinity Pool", "ECLIPSE 26th Floor Skybar", "Bliss Spa"]
        }
    ],
    "madrid": [
        {
            "name": "The Hat Madrid",
            "price_per_night": 48.0,
            "star_rating": 3.0,
            "guest_rating": 9.0,
            "review_count": 2700,
            "neighborhood": "La Latina / Plaza Mayor",
            "address": "Calle Imperial 9, 28012 Madrid",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Award-Winning Eco Rooftop Bar", "100m to Plaza Mayor", "Free WiFi", "Solarium"]
        },
        {
            "name": "Only YOU Boutique Hotel",
            "price_per_night": 160.0,
            "star_rating": 4.0,
            "guest_rating": 9.2,
            "review_count": 1650,
            "neighborhood": "Chueca / Downtown",
            "address": "Calle del Barquillo 21, 28004 Madrid",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["19th Century Palace Setting", "Lázaro Rosa-Violán Design", "Cocktail Bar", "Thai Spa"]
        },
        {
            "name": "The Westin Palace, Madrid",
            "price_per_night": 370.0,
            "star_rating": 5.0,
            "guest_rating": 9.1,
            "review_count": 2200,
            "neighborhood": "Literary Quarter / Prado",
            "address": "Plaza de las Cortes 7, 28014 Madrid",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Stained Glass Dome Rotunda", "Facing Prado Museum", "Opera & Dim Sum Brunches", "Heavenly Beds"]
        }
    ],
    "amsterdam": [
        {
            "name": "ClinkNOORD Hostel",
            "price_per_night": 58.0,
            "star_rating": 3.0,
            "guest_rating": 8.4,
            "review_count": 4100,
            "neighborhood": "Amsterdam Noord",
            "address": "Badhuiskade 3, 1031 KV Amsterdam",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["3-Min Free Ferry to Centraal Station", "ZincBAR", "Atrium Lounge", "Bike Rental"]
        },
        {
            "name": "Hotel V Nesplein",
            "price_per_night": 175.0,
            "star_rating": 4.0,
            "guest_rating": 9.1,
            "review_count": 1850,
            "neighborhood": "Theater District / Dam Square",
            "address": "Nes 49, 1012 KD Amsterdam",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["The Lobby Restaurant & Open Fireplace", "Canal District Walk", "Deep Soaking Tubs", "Artisanal Coffee"]
        },
        {
            "name": "Conservatorium Hotel",
            "price_per_night": 440.0,
            "star_rating": 5.0,
            "guest_rating": 9.3,
            "review_count": 1500,
            "neighborhood": "Museumplein",
            "address": "Van Baerlestraat 27, 1071 AN Amsterdam",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Opposite Rijksmuseum & Van Gogh", "Akasha Holistic Wellbeing Spa", "Taiko Asian Cuisine", "Glass Atrium"]
        }
    ],
    "bangkok": [
        {
            "name": "Mad Monkey Bangkok",
            "price_per_night": 22.0,
            "star_rating": 3.0,
            "guest_rating": 8.8,
            "review_count": 3100,
            "neighborhood": "Khao San / Phra Nakhon",
            "address": "55 Phra Sumen Rd, Chana Songkhram, Bangkok 10200",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Outdoor Swimming Pool", "Canalside Bar", "Social Tours & Pub Crawls", "Air Conditioning"]
        },
        {
            "name": "Centara Grand at CentralWorld",
            "price_per_night": 115.0,
            "star_rating": 4.5,
            "guest_rating": 8.9,
            "review_count": 4800,
            "neighborhood": "Siam / Pathum Wan",
            "address": "999/99 Rama 1 Road, Pathumwan, Bangkok 10330",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Red Sky 55th Floor Rooftop", "Direct Mall Connection", "Infinity Pool & Tennis", "Lifestyles on 26 Spa"]
        },
        {
            "name": "The Peninsula Bangkok",
            "price_per_night": 275.0,
            "star_rating": 5.0,
            "guest_rating": 9.4,
            "review_count": 2900,
            "neighborhood": "Chao Phraya Riverside",
            "address": "333 Charoen Nakhon Rd, Khlong San, Bangkok 10600",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["3-Tiered Riverside Pool", "Private Peninsula River Ferry", "All River-View Rooms", "Authentic Thai Cooking Classes"]
        }
    ],
    "bali": [
        {
            "name": "Kosta Hostel Seminyak",
            "price_per_night": 24.0,
            "star_rating": 3.0,
            "guest_rating": 8.9,
            "review_count": 1850,
            "neighborhood": "Seminyak",
            "address": "Jl. Dewi Saraswati III No.77, Seminyak, Bali",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Tropical Swimming Pool", "Good Mantra Cafe", "Surf Board Storage", "Boutique Beach Style"]
        },
        {
            "name": "Maya Ubud Resort & Spa",
            "price_per_night": 135.0,
            "star_rating": 4.5,
            "guest_rating": 9.2,
            "review_count": 2400,
            "neighborhood": "Petanu River Valley, Ubud",
            "address": "Jl. Gunung Sari, Peliatan, Ubud, Bali",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Hidden River Valley Spa", "Infinity Pool Overlooking Jungle", "Free Morning Yoga", "Shuttle to Ubud Centre"]
        },
        {
            "name": "Four Seasons Resort Bali at Sayan",
            "price_per_night": 460.0,
            "star_rating": 5.0,
            "guest_rating": 9.6,
            "review_count": 1600,
            "neighborhood": "Sayan, Ubud",
            "address": "Jl. Raya Sayan, Ubud, Bali",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Dramatic Suspension Bridge Entry", "Ayung Riverfront Villas", "Sacred River Spa", "Rice Bowl Architecture"]
        }
    ],
    "new york": [
        {
            "name": "HI NYC Hostel",
            "price_per_night": 72.0,
            "star_rating": 3.0,
            "guest_rating": 8.5,
            "review_count": 5200,
            "neighborhood": "Upper West Side / Manhattan",
            "address": "891 Amsterdam Ave, New York, NY 10025",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["2 Blocks to Central Park", "Large Private Courtyard Patio", "Organized Walking Tours", "Subway Line 1 Access"]
        },
        {
            "name": "Arlo SoHo",
            "price_per_night": 210.0,
            "star_rating": 4.0,
            "guest_rating": 8.8,
            "review_count": 3300,
            "neighborhood": "SoHo / Hudson Square",
            "address": "231 Hudson St, New York, NY 10013",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["A.R.T. Rooftop with Hudson River Views", "Courtyard Foosball & Games", "Lindens Restaurant", "Custom Bunk Rooms"]
        },
        {
            "name": "The Plaza",
            "price_per_night": 540.0,
            "star_rating": 5.0,
            "guest_rating": 9.1,
            "review_count": 2800,
            "neighborhood": "Fifth Avenue / Central Park South",
            "address": "768 5th Ave, New York, NY 10019",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Facing Central Park", "Palm Court Afternoon Tea", "Guerlain Spa", "White Glove Concierge"]
        }
    ],
    "moscow": [
        {
            "name": "Ibis Moscow Centre Bakhrushina",
            "price_per_night": 55.0,
            "star_rating": 3.0,
            "guest_rating": 8.7,
            "review_count": 2400,
            "neighborhood": "Zamoskvorechye",
            "address": "Bakhrushina St, 11, Moscow 115054",
            "image_url": "https://images.unsplash.com/photo-1555854877-bab0e564b8d5?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Close to Paveletskaya Metro", "Free High-Speed WiFi", "Restaurant & Bar", "Fitness Center"]
        },
        {
            "name": "Hotel Baltschug Kempinski Moscow",
            "price_per_night": 210.0,
            "star_rating": 5.0,
            "guest_rating": 9.2,
            "review_count": 1850,
            "neighborhood": "Red Square / Moskva River",
            "address": "Ulitsa Balchug, 1, Moscow 115035",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Direct View of Saint Basil's Cathedral", "Luxury Spa & Indoor Pool", "Fine Dining", "Concierge Service"]
        }
    ],
    "saint petersburg": [
        {
            "name": "Station Hotel M19",
            "price_per_night": 45.0,
            "star_rating": 3.0,
            "guest_rating": 8.6,
            "review_count": 1900,
            "neighborhood": "Nevsky Prospekt / Tsentralny",
            "address": "Marata St, 19, St Petersburg 191025",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600&auto=format&fit=crop&q=80",
            "amenities": ["5-Minute Walk to Mayakovskaya Metro", "Free WiFi", "Breakfast Buffet", "24/7 Front Desk"]
        },
        {
            "name": "Grand Hotel Europe, A Belmond Hotel",
            "price_per_night": 260.0,
            "star_rating": 5.0,
            "guest_rating": 9.4,
            "review_count": 1420,
            "neighborhood": "Arts Square / Nevsky",
            "address": "Mikhailovskaya Ulitsa 1/7, St Petersburg 191186",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Historic Caviar Bar", "Steps from Russian Museum & Hermitage", "World-Class Concierge", "Live Classical Music"]
        }
    ],
    "murmansk": [
        {
            "name": "Azimut Hotel Murmansk",
            "price_per_night": 65.0,
            "star_rating": 4.0,
            "guest_rating": 8.8,
            "review_count": 2100,
            "neighborhood": "Five Corners Central Square",
            "address": "Lenina Prospekt 82, Murmansk 183038",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Highest Building above Arctic Circle", "Aurora Borealis Tour Desk", "Arctic Seafood Restaurant", "Panoramic City Views"]
        },
        {
            "name": "Aurora Village Glamping",
            "price_per_night": 185.0,
            "star_rating": 4.0,
            "guest_rating": 9.1,
            "review_count": 820,
            "neighborhood": "Lake Kanentyavr Wilderness",
            "address": "Serebryanskoe Shosse 49 km, Murmansk Oblast",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
            "amenities": ["Glass-Domed Aurora Igloos", "Zero Light Pollution Sky Watching", "Open Air Wood Banya Hot Tub", "Snowmobile Safari Access"]
        }
    ]
}


class HotelClient:
    """
    Client for Booking.com RapidAPI hotel searches with destination resolution,
    24h destination cache, 1h search cache, and curated fallback inventory.
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._dest_cache: Dict[str, Dict[str, Any]] = {}
        self._search_cache: Dict[str, Dict[str, Any]] = {}
        self.dest_cache_ttl_seconds: int = 86400  # 24 hours
        self.search_cache_ttl_seconds: int = 3600  # 1 hour

    async def search_destination(self, query: str) -> Dict[str, Any]:
        """
        Resolve city or location name to Booking.com dest_id and dest_type.
        """
        clean_query = query.strip().lower()
        if not clean_query:
            return KNOWN_DESTINATIONS["reykjavik"]

        # Check static directory first (exact match first, then word-boundary match)
        if clean_query in KNOWN_DESTINATIONS:
            return KNOWN_DESTINATIONS[clean_query]

        for name, dest in KNOWN_DESTINATIONS.items():
            if re.search(r'\b' + re.escape(name) + r'\b', clean_query):
                return dest

        # Check in-memory 24h cache
        cached = self._dest_cache.get(clean_query)
        if cached:
            age = time.time() - cached.get("timestamp", 0)
            if age < self.dest_cache_ttl_seconds:
                return cached["data"]

        # If RapidAPI key configured and explicitly enabled, query booking-com15.p.rapidapi.com
        if getattr(self.settings, "enable_rapidapi", False):
            rapidapi_key = self.settings.rapidapi_key or ""
            if rapidapi_key and rapidapi_key.strip():
                try:
                    headers = {
                        "x-rapidapi-key": rapidapi_key.strip(),
                        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
                    }
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.get(
                            "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination",
                            params={"query": query},
                            headers=headers
                        )
                        if resp.status_code == 200:
                            data = resp.json().get("data", [])
                            if data and len(data) > 0:
                                first = data[0]
                                result = {
                                    "dest_id": str(first.get("dest_id", "-2646452")),
                                    "dest_type": str(first.get("dest_type", "city")),
                                    "label": first.get("label", query),
                                    "lat": float(first.get("latitude", 64.1466)),
                                    "lng": float(first.get("longitude", -21.9426))
                                }
                                self._dest_cache[clean_query] = {"timestamp": time.time(), "data": result}
                                return result
                except Exception as err:
                    logger.warning("Destination search failed for '%s': %s", query, err)

        # Default fallback
        fallback = {
            "dest_id": f"-{abs(hash(clean_query)) % 10000000}",
            "dest_type": "city",
            "label": query.title(),
            "lat": 64.1466,
            "lng": -21.9426
        }
        self._dest_cache[clean_query] = {"timestamp": time.time(), "data": fallback}
        return fallback

    async def search_hotels(
        self,
        dest_id: str,
        dest_type: str = "city",
        arrival_date: str = "2026-12-01",
        departure_date: str = "2026-12-04",
        adults: int = 1,
        room_qty: int = 1,
        currency: str = "USD",
        city_name: Optional[str] = None
    ) -> List[RealHotelOffer]:
        """
        Search hotels by dest_id or fallback to curated inventory.
        """
        cache_key = f"{dest_id}:{arrival_date}:{departure_date}:{adults}:{room_qty}:{currency}".lower()
        cached = self._search_cache.get(cache_key)
        if cached:
            age = time.time() - cached.get("timestamp", 0)
            if age < self.search_cache_ttl_seconds:
                return cached["data"]

        if getattr(self.settings, "enable_rapidapi", False):
            rapidapi_key = self.settings.rapidapi_key or ""
            if rapidapi_key and rapidapi_key.strip():
                try:
                    offers = await self._query_booking_api(
                        dest_id=dest_id,
                        dest_type=dest_type,
                        arrival_date=arrival_date,
                        departure_date=departure_date,
                        adults=adults,
                        room_qty=room_qty,
                        currency=currency,
                        city_name=city_name or "Destination"
                    )
                    if offers:
                        self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
                        return offers
                except Exception as err:
                    logger.warning("Booking.com hotel search failed for dest_id %s: %s", dest_id, err)

        # Curated instant cache for blueprint destinations
        if city_name:
            cn_lower = city_name.strip().lower()
            if cn_lower in CURATED_HOTELS:
                offers = self._generate_fallback_hotels(
                    dest_id=dest_id,
                    city_name=city_name,
                    arrival_date=arrival_date,
                    departure_date=departure_date,
                    currency=currency
                )
                self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
                return offers

        # Dynamic LLM-generated hotels for any other city worldwide
        if city_name and city_name.strip():
            llm_hotels = await self._generate_llm_hotels(
                city_name=city_name.strip(),
                arrival_date=arrival_date,
                departure_date=departure_date,
                currency=currency
            )
            if llm_hotels:
                self._search_cache[cache_key] = {"timestamp": time.time(), "data": llm_hotels}
                return llm_hotels

        # Fallback to curated inventory
        offers = self._generate_fallback_hotels(
            dest_id=dest_id,
            city_name=city_name,
            arrival_date=arrival_date,
            departure_date=departure_date,
            currency=currency
        )
        self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
        return offers

    async def _generate_llm_hotels(
        self,
        city_name: str,
        budget_tier: str = "moderate",
        arrival_date: str = "2026-12-01",
        departure_date: str = "2026-12-04",
        currency: str = "USD"
    ) -> List[RealHotelOffer]:
        """Generate 3 real existing hotels in city_name using Groq/LLM."""
        if not city_name or len(city_name.strip()) < 2:
            return []
        try:
            from ..llm import get_llm_client
            llm = get_llm_client()
            if not llm:
                return []

            clean_city = city_name.strip().title()
            prompt = f"""Generate 3 REAL, currently operating hotels in {clean_city} for a {budget_tier} traveler.
Return ONLY a valid JSON array of 3 objects with this exact format:
[
  {{
    "name": "Actual Real Hotel Name",
    "price_per_night": 140.0,
    "star_rating": 4.0,
    "guest_rating": 8.8,
    "review_count": 1250,
    "neighborhood": "Real Neighborhood or District",
    "address": "Real street address or district, {clean_city}",
    "amenities": ["Free WiFi", "Breakfast Included", "Air Conditioning"]
  }}
]"""
            response = await asyncio.wait_for(
                llm.chat_with_retry(
                    messages=[
                        {"role": "system", "content": "You are a hotel booking inventory data engine. Return ONLY a valid JSON array of real hotels."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=600
                ),
                timeout=25.0
            )
            text = response.strip()
            bracket = text.find("[")
            if bracket >= 0:
                text = text[bracket:]
                end_b = text.rfind("]")
                if end_b > 0:
                    text = text[:end_b + 1]
            data = json.loads(text)
            offers = []
            for idx, h in enumerate(data):
                nightly = float(h.get("price_per_night", 120.0))
                total = round(nightly * 3, 2)
                offers.append(RealHotelOffer(
                    id=f"llm-ht-{clean_city.lower().replace(' ', '-')}-{idx + 1}",
                    name=h.get("name", f"Hotel in {clean_city}"),
                    city=clean_city,
                    price_per_night=nightly,
                    total_price=total,
                    currency=currency,
                    star_rating=float(h.get("star_rating", 4.0)),
                    guest_rating=float(h.get("guest_rating", 8.5)),
                    review_count=int(h.get("review_count", 500)),
                    neighborhood=h.get("neighborhood", f"{clean_city} Center"),
                    address=h.get("address", f"{clean_city}"),
                    image_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
                    deeplink=f"https://www.booking.com/searchresults.html?ss={clean_city.lower().replace(' ', '+')}",
                    amenities=h.get("amenities", ["Free WiFi", "Air Conditioning", "Breakfast"])
                ))
            if len(offers) >= 2:
                return offers
        except Exception as e:
            logger.warning("LLM hotel generation failed for %s: %s", city_name, e)
        return []

    async def search_hotels_by_coords(
        self,
        lat: float,
        lng: float,
        arrival_date: str = "2026-12-01",
        departure_date: str = "2026-12-04",
        adults: int = 1,
        currency: str = "USD",
        city_name: Optional[str] = None
    ) -> List[RealHotelOffer]:
        """
        Alternative search by geographic coordinates.
        """
        cache_key = f"{lat:.2f}:{lng:.2f}:{arrival_date}:{departure_date}:{adults}:{currency}".lower()
        cached = self._search_cache.get(cache_key)
        if cached:
            age = time.time() - cached.get("timestamp", 0)
            if age < self.search_cache_ttl_seconds:
                return cached["data"]

        if getattr(self.settings, "enable_rapidapi", False):
            rapidapi_key = self.settings.rapidapi_key or ""
            if rapidapi_key and rapidapi_key.strip():
                try:
                    headers = {
                        "x-rapidapi-key": rapidapi_key.strip(),
                        "x-rapidapi-host": "booking-com15.p.rapidapi.com"
                    }
                    params = {
                        "latitude": str(lat),
                        "longitude": str(lng),
                        "arrival_date": arrival_date,
                        "departure_date": departure_date,
                        "adults": str(adults),
                        "currency_code": currency
                    }
                    async with httpx.AsyncClient(timeout=20.0) as client:
                        resp = await client.get(
                            "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotelsByCoordinates",
                            params=params,
                            headers=headers
                        )
                        if resp.status_code == 200:
                            data = resp.json().get("data", {}).get("result", [])
                            offers = self._transform_booking_hotels(data, city_name or "Location", currency, 3)
                            if offers:
                                self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
                                return offers
                except Exception as err:
                    logger.warning("Coordinates hotel search failed for (%f, %f): %s", lat, lng, err)

        # Fallback
        offers = self._generate_fallback_hotels(
            dest_id=f"coord-{lat:.1f}-{lng:.1f}",
            city_name=city_name or "Location",
            arrival_date=arrival_date,
            departure_date=departure_date,
            currency=currency
        )
        self._search_cache[cache_key] = {"timestamp": time.time(), "data": offers}
        return offers

    async def _query_booking_api(
        self,
        dest_id: str,
        dest_type: str,
        arrival_date: str,
        departure_date: str,
        adults: int,
        room_qty: int,
        currency: str,
        city_name: str
    ) -> List[RealHotelOffer]:
        headers = {
            "x-rapidapi-key": self.settings.rapidapi_key.strip(),
            "x-rapidapi-host": "booking-com15.p.rapidapi.com"
        }
        params = {
            "dest_id": dest_id,
            "search_type": dest_type,
            "arrival_date": arrival_date,
            "departure_date": departure_date,
            "adults": str(adults),
            "room_qty": str(room_qty),
            "currency_code": currency
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels",
                params=params,
                headers=headers
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Booking.com API status {resp.status_code}: {resp.text[:200]}")
            data = resp.json().get("data", {}).get("result", [])
            return self._transform_booking_hotels(data, city_name, currency, 3)

    def _transform_booking_hotels(
        self,
        results: List[Dict[str, Any]],
        city_name: str,
        currency: str,
        nights: int = 3
    ) -> List[RealHotelOffer]:
        offers: List[RealHotelOffer] = []
        for idx, item in enumerate(results[:10]):
            name = item.get("hotel_name", f"Hotel {city_name}")
            price_total = float(item.get("min_total_price", 150.0 * nights))
            price_per_night = round(price_total / max(nights, 1), 2)
            star = float(item.get("class", 3.5))
            score = float(item.get("review_score", 8.5))
            reviews = int(item.get("review_nr", 500))
            address = item.get("address", f"{city_name} Center")
            neighborhood = item.get("district", city_name)
            photo = item.get("max_photo_url") or "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80"
            deeplink = item.get("url") or f"https://www.booking.com/searchresults.html?dest_id={item.get('hotel_id')}"

            offers.append(
                RealHotelOffer(
                    id=f"bk-{idx}-{item.get('hotel_id', uuid4().hex[:6])}",
                    name=name,
                    city=city_name,
                    price_per_night=price_per_night,
                    total_price=price_total,
                    currency=currency,
                    star_rating=star,
                    guest_rating=score,
                    review_count=reviews,
                    address=address,
                    neighborhood=neighborhood,
                    image_url=photo,
                    deeplink=deeplink,
                    amenities=["Free WiFi", "Private Bathroom", "Air Conditioning", "24-Hour Desk"]
                )
            )
        return offers

    def _generate_fallback_hotels(
        self,
        dest_id: str,
        city_name: Optional[str],
        arrival_date: str,
        departure_date: str,
        currency: str
    ) -> List[RealHotelOffer]:
        target_key = "reykjavik"
        if city_name:
            cn = city_name.strip().lower()
            if cn in CURATED_HOTELS:
                target_key = cn
            else:
                for k in CURATED_HOTELS:
                    if re.search(r'\b' + re.escape(k) + r'\b', cn):
                        target_key = k
                        break
        else:
            for k, dest in KNOWN_DESTINATIONS.items():
                if dest["dest_id"] == dest_id:
                    target_key = k
                    break

        display_city = (city_name or target_key).title()
        if target_key in CURATED_HOTELS:
            hotel_list = CURATED_HOTELS[target_key]
        else:
            # Generate high-fidelity dynamic hotel offerings for any global destination
            hotel_list = [
                {
                    "name": f"Grand {display_city} Hotel & Suites",
                    "price_per_night": 175.0,
                    "star_rating": 4.5,
                    "guest_rating": 9.1,
                    "review_count": 640,
                    "neighborhood": f"{display_city} Center",
                    "address": f"Central Avenue, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free WiFi", "Spa & Wellness", "Breakfast Included", "City View", "Concierge"]
                },
                {
                    "name": f"{display_city} Heritage Boutique Hotel",
                    "price_per_night": 135.0,
                    "star_rating": 4.0,
                    "guest_rating": 8.8,
                    "review_count": 480,
                    "neighborhood": f"Historic District, {display_city}",
                    "address": f"Old Town Square, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free WiFi", "Boutique Bar", "Room Service", "Airport Shuttle"]
                },
                {
                    "name": f"Urban Prime Suites {display_city}",
                    "price_per_night": 95.0,
                    "star_rating": 3.5,
                    "guest_rating": 8.5,
                    "review_count": 310,
                    "neighborhood": f"Downtown {display_city}",
                    "address": f"Station Road, {display_city}",
                    "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&auto=format&fit=crop&q=80",
                    "amenities": ["Free High-Speed WiFi", "Kitchenette", "Air Conditioning", "24/7 Desk"]
                }
            ]

        offers: List[RealHotelOffer] = []
        for idx, h in enumerate(hotel_list):
            nightly = float(h["price_per_night"])
            total = round(nightly * 3, 2)
            deeplink = f"https://www.skyscanner.com/hotels/search?destination={target_key}&checkin={arrival_date}&checkout={departure_date}"

            offers.append(
                RealHotelOffer(
                    id=f"ht-{target_key}-{idx}",
                    name=h["name"],
                    city=display_city,
                    price_per_night=nightly,
                    total_price=total,
                    currency=currency,
                    star_rating=h["star_rating"],
                    guest_rating=h["guest_rating"],
                    review_count=h["review_count"],
                    neighborhood=h["neighborhood"],
                    address=h["address"],
                    image_url=h["image_url"],
                    deeplink=deeplink,
                    amenities=h["amenities"]
                )
            )

        return offers


_hotel_client_instance: Optional[HotelClient] = None


def get_hotel_client() -> HotelClient:
    """Get singleton HotelClient instance."""
    global _hotel_client_instance
    if _hotel_client_instance is None:
        _hotel_client_instance = HotelClient()
    return _hotel_client_instance
