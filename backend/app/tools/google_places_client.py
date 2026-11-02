"""
GooglePlacesClient - Google Places API client for attractions, POIs, ratings, and photos.
Phase 3: Nearby search, text search, place details, 24h caching, and realistic curated fallback.
"""

import logging
import math
import re
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from ..config import get_settings
from ..models.schemas import PlaceInfo

logger = logging.getLogger(__name__)

# ============================================================================
# Curated High-Fidelity Attraction Inventory for Demo Reliability
# ============================================================================

CURATED_PLACES: Dict[str, List[Dict[str, Any]]] = {
    "reykjavik": [
        {
            "place_id": "ChIJc860Z0pZ1kgRnV-Q9xGkP4g",
            "name": "Hallgrímskirkja",
            "rating": 4.6,
            "review_count": 18200,
            "types": ["church", "place_of_worship", "tourist_attraction"],
            "opening_hours": ["Monday: 9:00 AM – 8:00 PM", "Tuesday: 9:00 AM – 8:00 PM", "Wednesday: 9:00 AM – 8:00 PM", "Thursday: 9:00 AM – 8:00 PM", "Friday: 9:00 AM – 8:00 PM", "Saturday: 9:00 AM – 8:00 PM", "Sunday: 9:00 AM – 8:00 PM"],
            "open_now": True,
            "address": "Hallgrímstorg 1, 101 Reykjavík, Iceland",
            "city": "Reykjavik",
            "lat": 64.1417,
            "lng": -21.9266,
            "photo_url": "https://images.unsplash.com/photo-1517411032315-54ef2cb783bb?w=800&auto=format&fit=crop&q=80",
            "price_level": 1,
            "description": "Iconic expressionist Lutheran church standing 74.5m tall with panoramic observation tower overlooking Reykjavik.",
            "google_maps_url": "https://maps.google.com/?cid=123456789012"
        },
        {
            "place_id": "ChIJb_fN4E5Z1kgRkn0JkYgHwYs",
            "name": "Harpa Concert Hall and Conference Centre",
            "rating": 4.6,
            "review_count": 12400,
            "types": ["point_of_interest", "tourist_attraction", "auditorium"],
            "opening_hours": ["Monday: 10:00 AM – 6:00 PM", "Tuesday: 10:00 AM – 6:00 PM", "Wednesday: 10:00 AM – 6:00 PM", "Thursday: 10:00 AM – 6:00 PM", "Friday: 10:00 AM – 6:00 PM", "Saturday: 10:00 AM – 6:00 PM", "Sunday: 10:00 AM – 6:00 PM"],
            "open_now": True,
            "address": "Austurbakki 2, 101 Reykjavík, Iceland",
            "city": "Reykjavik",
            "lat": 64.1504,
            "lng": -21.9329,
            "photo_url": "https://images.unsplash.com/photo-1529963183134-61a90db47eaf?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Award-winning geometric glass concert hall by Henning Larsen and Olafur Eliasson on Reykjavik's old harbour.",
            "google_maps_url": "https://maps.google.com/?cid=234567890123"
        },
        {
            "place_id": "ChIJBb0eTEZZ1kgR49Uf9w1B2qM",
            "name": "Sun Voyager (Sólfar)",
            "rating": 4.5,
            "review_count": 9800,
            "types": ["tourist_attraction", "point_of_interest"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "Sæbraut, 101 Reykjavík, Iceland",
            "city": "Reykjavik",
            "lat": 64.1476,
            "lng": -21.9223,
            "photo_url": "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Striking stainless-steel Viking ship sculpture facing Mount Esja, symbolizing hope, freedom, and undiscovered territory.",
            "google_maps_url": "https://maps.google.com/?cid=345678901234"
        },
        {
            "place_id": "ChIJcQe9o1BZ1kgR_QJjY38Zl0I",
            "name": "Perlan",
            "rating": 4.5,
            "review_count": 14100,
            "types": ["museum", "tourist_attraction", "restaurant"],
            "opening_hours": ["Monday: 9:00 AM – 10:00 PM", "Tuesday: 9:00 AM – 10:00 PM", "Wednesday: 9:00 AM – 10:00 PM", "Thursday: 9:00 AM – 10:00 PM", "Friday: 9:00 AM – 10:00 PM", "Saturday: 9:00 AM – 10:00 PM", "Sunday: 9:00 AM – 10:00 PM"],
            "open_now": True,
            "address": "Öskjuhlíð, 105 Reykjavík, Iceland",
            "city": "Reykjavik",
            "lat": 64.1292,
            "lng": -21.9192,
            "photo_url": "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&auto=format&fit=crop&q=80",
            "price_level": 2,
            "description": "Futuristic glass dome featuring an artificial indoor ice cave, 360° observation deck, and Northern Lights planetarium.",
            "google_maps_url": "https://maps.google.com/?cid=456789012345"
        },
        {
            "place_id": "ChIJa9W39_FZ1kgRV-d0pS_Q2dI",
            "name": "Sky Lagoon",
            "rating": 4.7,
            "review_count": 7800,
            "types": ["spa", "tourist_attraction", "point_of_interest"],
            "opening_hours": ["Monday: 11:00 AM – 10:00 PM", "Tuesday: 11:00 AM – 10:00 PM", "Wednesday: 11:00 AM – 10:00 PM", "Thursday: 11:00 AM – 10:00 PM", "Friday: 11:00 AM – 10:00 PM", "Saturday: 10:00 AM – 10:00 PM", "Sunday: 10:00 AM – 10:00 PM"],
            "open_now": True,
            "address": "Vesturvör 44-48, 200 Kópavogur, Iceland",
            "city": "Reykjavik",
            "lat": 64.1166,
            "lng": -21.9542,
            "photo_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&auto=format&fit=crop&q=80",
            "price_level": 3,
            "description": "Oceanfront geothermal lagoon featuring an infinity edge overlooking the North Atlantic and a traditional 7-step ritual.",
            "google_maps_url": "https://maps.google.com/?cid=567890123456"
        },
        {
            "place_id": "ChIJU6n_4KxX1kgRg7uI6m5o65o",
            "name": "Blue Lagoon",
            "rating": 4.4,
            "review_count": 28500,
            "types": ["spa", "tourist_attraction", "point_of_interest"],
            "opening_hours": ["Monday: 8:00 AM – 9:00 PM", "Tuesday: 8:00 AM – 9:00 PM", "Wednesday: 8:00 AM – 9:00 PM", "Thursday: 8:00 AM – 9:00 PM", "Friday: 8:00 AM – 9:00 PM", "Saturday: 8:00 AM – 9:00 PM", "Sunday: 8:00 AM – 9:00 PM"],
            "open_now": True,
            "address": "Norðurljósavegur 9, 240 Grindavík, Iceland",
            "city": "Reykjavik",
            "lat": 63.8804,
            "lng": -22.4495,
            "photo_url": "https://images.unsplash.com/photo-1528728329032-2972f65dfb3f?w=800&auto=format&fit=crop&q=80",
            "price_level": 4,
            "description": "World-famous mineral-rich geothermal spa set in volcanic black lava fields, renowned for healing silica mud masks.",
            "google_maps_url": "https://maps.google.com/?cid=678901234567"
        }
    ],
    "vik": [
        {
            "place_id": "ChIJc7aZp6hU1kgRl_O88K-gD8Y",
            "name": "Reynisfjara Black Sand Beach",
            "rating": 4.7,
            "review_count": 11500,
            "types": ["natural_feature", "tourist_attraction"],
            "opening_hours": ["Open 24 hours (Daylight recommended)"],
            "open_now": True,
            "address": "Reynisfjara, 871 Vík í Mýrdal, Iceland",
            "city": "Vík",
            "lat": 63.4044,
            "lng": -19.0494,
            "photo_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "World-renowned dramatic black volcanic sand beach featuring towering hexagonal basalt columns and Reynisdrangar sea stacks.",
            "google_maps_url": "https://maps.google.com/?cid=789012345678"
        },
        {
            "place_id": "ChIJb7c_M_tU1kgR18LpWkE1d2I",
            "name": "Dyrhólaey Peninsula & Arch",
            "rating": 4.8,
            "review_count": 6200,
            "types": ["natural_feature", "tourist_attraction"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "Dyrhólaey, 871 Vík, Iceland",
            "city": "Vík",
            "lat": 63.4022,
            "lng": -19.1297,
            "photo_url": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "120m high promontory with gigantic natural black lava arch, historic lighthouse, and puffin breeding colonies in summer.",
            "google_maps_url": "https://maps.google.com/?cid=890123456789"
        },
        {
            "place_id": "ChIJ-2374-1U1kgR2_64vI0gEwo",
            "name": "Víkurkirkja (Vík Church)",
            "rating": 4.6,
            "review_count": 2100,
            "types": ["church", "place_of_worship", "tourist_attraction"],
            "opening_hours": ["Monday: 9:00 AM – 5:00 PM", "Sunday: 10:00 AM – 2:00 PM"],
            "open_now": True,
            "address": "Sunnuvegur, 870 Vík í Mýrdal, Iceland",
            "city": "Vík",
            "lat": 63.4187,
            "lng": -19.0062,
            "photo_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Picturesque red-roofed hillside church offering unobstructed panoramic views of the coastal village and Atlantic ocean.",
            "google_maps_url": "https://maps.google.com/?cid=901234567890"
        },
        {
            "place_id": "ChIJXw0Vb5JU1kgR9T3Ld_0vFkM",
            "name": "Skógafoss Waterfall",
            "rating": 4.8,
            "review_count": 16800,
            "types": ["natural_feature", "tourist_attraction"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "Skógar, 861 Hvolsvöllur, Iceland",
            "city": "Vík",
            "lat": 63.5321,
            "lng": -19.5114,
            "photo_url": "https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Thundering 60-meter high and 25-meter wide waterfall famous for persistent single and double rainbows on sunny days.",
            "google_maps_url": "https://maps.google.com/?cid=112233445566"
        },
        {
            "place_id": "ChIJrw0-l4VU1kgR1YQ8vL4gGoQ",
            "name": "Seljalandsfoss Waterfall",
            "rating": 4.8,
            "review_count": 18200,
            "types": ["natural_feature", "tourist_attraction"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "Þórsmerkurvegur, 861 Hvolsvöllur, Iceland",
            "city": "Vík",
            "lat": 63.6156,
            "lng": -19.9886,
            "photo_url": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Breathtaking 60m cascading waterfall with an accessible path enabling visitors to walk entirely behind the water curtain.",
            "google_maps_url": "https://maps.google.com/?cid=223344556677"
        }
    ],
    "akureyri": [
        {
            "place_id": "ChIJW0j9Z14F1kgRf-2tJ_0wF5Y",
            "name": "Akureyrarkirkja",
            "rating": 4.5,
            "review_count": 2300,
            "types": ["church", "place_of_worship", "tourist_attraction"],
            "opening_hours": ["Monday: 10:00 AM – 4:00 PM", "Tuesday: 10:00 AM – 4:00 PM", "Wednesday: 10:00 AM – 4:00 PM", "Thursday: 10:00 AM – 4:00 PM", "Friday: 10:00 AM – 4:00 PM"],
            "open_now": True,
            "address": "Eyrarlandsvegur, 600 Akureyri, Iceland",
            "city": "Akureyri",
            "lat": 65.6798,
            "lng": -18.0906,
            "photo_url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Prominent modernist Lutheran church designed by Guðjón Samúelsson, consecrated in 1940 with a 3200-pipe organ.",
            "google_maps_url": "https://maps.google.com/?cid=334455667788"
        },
        {
            "place_id": "ChIJc4p29_8E1kgR7K2-qN0gBqo",
            "name": "Akureyri Botanical Garden (Lystigarðurinn)",
            "rating": 4.7,
            "review_count": 3100,
            "types": ["park", "tourist_attraction"],
            "opening_hours": ["Monday: 8:00 AM – 10:00 PM", "Tuesday: 8:00 AM – 10:00 PM", "Wednesday: 8:00 AM – 10:00 PM", "Thursday: 8:00 AM – 10:00 PM", "Friday: 8:00 AM – 10:00 PM", "Saturday: 9:00 AM – 10:00 PM", "Sunday: 9:00 AM – 10:00 PM"],
            "open_now": True,
            "address": "Eyrarlandsvegur, 600 Akureyri, Iceland",
            "city": "Akureyri",
            "lat": 65.6756,
            "lng": -18.0933,
            "photo_url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "One of the world's northernmost public botanical gardens displaying over 7,000 Arctic and subarctic plant species.",
            "google_maps_url": "https://maps.google.com/?cid=445566778899"
        },
        {
            "place_id": "ChIJrW9gN_wF1kgRy7J_qT0gEgo",
            "name": "Forest Lagoon (Skógarböðin)",
            "rating": 4.8,
            "review_count": 2900,
            "types": ["spa", "tourist_attraction", "point_of_interest"],
            "opening_hours": ["Monday: 10:00 AM – 12:00 AM", "Tuesday: 10:00 AM – 12:00 AM", "Wednesday: 10:00 AM – 12:00 AM", "Thursday: 10:00 AM – 12:00 AM", "Friday: 10:00 AM – 12:00 AM", "Saturday: 10:00 AM – 12:00 AM", "Sunday: 10:00 AM – 12:00 AM"],
            "open_now": True,
            "address": "Vaðlabyggð 9, 605 Akureyri, Iceland",
            "city": "Akureyri",
            "lat": 65.6872,
            "lng": -18.0583,
            "photo_url": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=800&auto=format&fit=crop&q=80",
            "price_level": 3,
            "description": "Serene geothermal baths tucked into the Vaðlaskógur pine forest overlooking the sparkling Eyjafjörður fjord.",
            "google_maps_url": "https://maps.google.com/?cid=556677889900"
        },
        {
            "place_id": "ChIJ_6t_o9cF1kgR0wG9vK0gFYo",
            "name": "Goðafoss Waterfall",
            "rating": 4.8,
            "review_count": 8900,
            "types": ["natural_feature", "tourist_attraction"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "Ring Road, 645 Fosshóll, Iceland",
            "city": "Akureyri",
            "lat": 65.6828,
            "lng": -17.5502,
            "photo_url": "https://images.unsplash.com/photo-1518457607834-6e8d80c183c5?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "'Waterfall of the Gods' — spectacular 12m horseshoe cascade where pagan idols were cast into the waters in year 1000.",
            "google_maps_url": "https://maps.google.com/?cid=667788990011"
        }
    ],
    "tokyo": [
        {
            "place_id": "ChIJ8T1_0T-LGGARqpmGnv3tAio",
            "name": "Sensō-ji Temple",
            "rating": 4.5,
            "review_count": 68000,
            "types": ["place_of_worship", "tourist_attraction"],
            "opening_hours": ["Main Hall: 6:00 AM – 5:00 PM daily", "Grounds: Open 24 hours"],
            "open_now": True,
            "address": "2-3-1 Asakusa, Taito City, Tokyo 111-0032, Japan",
            "city": "Tokyo",
            "lat": 35.7148,
            "lng": 139.7967,
            "photo_url": "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Tokyo's oldest and most significant ancient Buddhist temple founded in 645 AD, approached via the Nakamise shopping street.",
            "google_maps_url": "https://maps.google.com/?cid=778899001122"
        },
        {
            "place_id": "ChIJ1X2J3VqMGGARx_pC8F1gHqo",
            "name": "Meiji Jingu Shrine",
            "rating": 4.6,
            "review_count": 42000,
            "types": ["place_of_worship", "tourist_attraction"],
            "opening_hours": ["Sunrise to Sunset daily"],
            "open_now": True,
            "address": "1-1 Yoyogikamizonocho, Shibuya City, Tokyo 151-8557, Japan",
            "city": "Tokyo",
            "lat": 35.6764,
            "lng": 139.6993,
            "photo_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Tranquil Shinto shrine nestled in a serene 170-acre evergreen forest dedicated to Emperor Meiji and Empress Shoken.",
            "google_maps_url": "https://maps.google.com/?cid=889900112233"
        },
        {
            "place_id": "ChIJL_R7w_6MGGAR3v6Jk0gH-wo",
            "name": "Shibuya Scramble Crossing",
            "rating": 4.5,
            "review_count": 45000,
            "types": ["tourist_attraction", "point_of_interest"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "2 Chome-2-1 Dogenzaka, Shibuya City, Tokyo 150-0043, Japan",
            "city": "Tokyo",
            "lat": 35.6591,
            "lng": 139.7006,
            "photo_url": "https://images.unsplash.com/photo-1542051841857-5f90071e7989?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "World's busiest pedestrian intersection where up to 3,000 people cross simultaneously beneath dazzling neon video screens.",
            "google_maps_url": "https://maps.google.com/?cid=990011223344"
        },
        {
            "place_id": "ChIJk54XvV6MGGAR5r7_vN0gIqo",
            "name": "teamLab Planets TOKYO",
            "rating": 4.6,
            "review_count": 31000,
            "types": ["museum", "tourist_attraction"],
            "opening_hours": ["Daily: 9:00 AM – 10:00 PM"],
            "open_now": True,
            "address": "6-1-16 Toyosu, Koto City, Tokyo 135-0061, Japan",
            "city": "Tokyo",
            "lat": 35.6491,
            "lng": 139.7898,
            "photo_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=800&auto=format&fit=crop&q=80",
            "price_level": 3,
            "description": "Immersive barefoot digital art museum where visitors walk through water and colossal interactive light gardens.",
            "google_maps_url": "https://maps.google.com/?cid=101112131415"
        }
    ],
    "kyoto": [
        {
            "place_id": "ChIJ1Z7bY_MIAWAR_K2-qN0gBqo",
            "name": "Fushimi Inari Taisha",
            "rating": 4.7,
            "review_count": 52000,
            "types": ["place_of_worship", "tourist_attraction"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "68 Fukakusa Yabunouchicho, Fushimi Ward, Kyoto 612-0882, Japan",
            "city": "Kyoto",
            "lat": 34.9671,
            "lng": 135.7727,
            "photo_url": "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Head shrine of Inari featuring a spellbinding tunnel of over 10,000 vibrant vermilion torii gates winding up sacred Mount Inari.",
            "google_maps_url": "https://maps.google.com/?cid=202122232425"
        },
        {
            "place_id": "ChIJY7v_M_AIAWAR3v6Jk0gH-wo",
            "name": "Kinkaku-ji (Golden Pavilion)",
            "rating": 4.5,
            "review_count": 38000,
            "types": ["place_of_worship", "tourist_attraction"],
            "opening_hours": ["Daily: 9:00 AM – 5:00 PM"],
            "open_now": True,
            "address": "1 Kinkakujicho, Kita Ward, Kyoto 603-8361, Japan",
            "city": "Kyoto",
            "lat": 35.0394,
            "lng": 135.7292,
            "photo_url": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=800&auto=format&fit=crop&q=80",
            "price_level": 1,
            "description": "Celebrated Zen Buddhist temple with top two floors completely covered in brilliant gold leaf, overlooking the Mirror Pond.",
            "google_maps_url": "https://maps.google.com/?cid=303132333435"
        },
        {
            "place_id": "ChIJL-X_v_IIAWAR5r7_vN0gIqo",
            "name": "Kiyomizu-dera Temple",
            "rating": 4.6,
            "review_count": 45000,
            "types": ["place_of_worship", "tourist_attraction"],
            "opening_hours": ["Daily: 6:00 AM – 6:00 PM"],
            "open_now": True,
            "address": "1-294 Kiyomizu, Higashiyama Ward, Kyoto 605-0862, Japan",
            "city": "Kyoto",
            "lat": 34.9949,
            "lng": 135.7850,
            "photo_url": "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=800&auto=format&fit=crop&q=80",
            "price_level": 1,
            "description": "Historic hillside temple founded in 778 AD, famous for its massive wooden stage built without a single nail and sweeping city vistas.",
            "google_maps_url": "https://maps.google.com/?cid=404142434445"
        },
        {
            "place_id": "ChIJ77b_N_MIAWAR_K2-qN0gBqo",
            "name": "Arashiyama Bamboo Grove",
            "rating": 4.5,
            "review_count": 27000,
            "types": ["natural_feature", "tourist_attraction"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "Sagatenryuji Sagahiakaricho, Ukyo Ward, Kyoto 616-8385, Japan",
            "city": "Kyoto",
            "lat": 35.0169,
            "lng": 135.6713,
            "photo_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Ethereal walking pathway flanked by towering, densely packed green bamboo stalks that sway and rustle gently in the breeze.",
            "google_maps_url": "https://maps.google.com/?cid=505152535455"
        }
    ],
    "paris": [
        {
            "place_id": "ChIJLU7jZClu5kcR4PcOOO6p3I0",
            "name": "Eiffel Tower",
            "rating": 4.7,
            "review_count": 340000,
            "types": ["tourist_attraction", "point_of_interest"],
            "opening_hours": ["Daily: 9:00 AM – 11:45 PM"],
            "open_now": True,
            "address": "Champ de Mars, 5 Av. Anatole France, 75007 Paris, France",
            "city": "Paris",
            "lat": 48.8584,
            "lng": 2.2945,
            "photo_url": "https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?w=800&auto=format&fit=crop&q=80",
            "price_level": 2,
            "description": "Iconic wrought-iron lattice tower on the Champ de Mars, offering unmatched 360-degree panoramic views of Paris.",
            "google_maps_url": "https://maps.google.com/?cid=123456789"
        },
        {
            "place_id": "ChIJD39Ckep-5kcRKuEIcrAE-xA",
            "name": "Louvre Museum",
            "rating": 4.7,
            "review_count": 280000,
            "types": ["museum", "tourist_attraction"],
            "opening_hours": ["Mon, Thu, Sat, Sun: 9:00 AM – 6:00 PM", "Wed, Fri: 9:00 AM – 9:00 PM", "Tue: Closed"],
            "open_now": True,
            "address": "Rue de Rivoli, 75001 Paris, France",
            "city": "Paris",
            "lat": 48.8606,
            "lng": 2.3376,
            "photo_url": "https://images.unsplash.com/photo-1543349689-9a4d426bee8e?w=800&auto=format&fit=crop&q=80",
            "price_level": 2,
            "description": "The world's largest art museum and historic monument housing the Mona Lisa, Venus de Milo, and vast royal masterpieces.",
            "google_maps_url": "https://maps.google.com/?cid=987654321"
        },
        {
            "place_id": "ChIJyXjhwtBx5kcRwfM0B035w3s",
            "name": "Musée d'Orsay",
            "rating": 4.7,
            "review_count": 95000,
            "types": ["museum", "tourist_attraction"],
            "opening_hours": ["Tue-Sun: 9:30 AM – 6:00 PM", "Thu: until 9:45 PM", "Mon: Closed"],
            "open_now": True,
            "address": "1 Rue de la Légion d'Honneur, 75007 Paris, France",
            "city": "Paris",
            "lat": 48.8599,
            "lng": 2.3265,
            "photo_url": "https://images.unsplash.com/photo-1574958269340-fa927503f3dd?w=800&auto=format&fit=crop&q=80",
            "price_level": 2,
            "description": "Grand Beaux-Arts former railway station housing premier Impressionist and Post-Impressionist masterpieces by Monet, Van Gogh, and Renoir.",
            "google_maps_url": "https://maps.google.com/?cid=11223344"
        }
    ],
    "lyon": [
        {
            "place_id": "ChIJc861vj3q9EcRQF6g-c4q4Q8",
            "name": "Basilica of Notre-Dame de Fourvière",
            "rating": 4.8,
            "review_count": 32000,
            "types": ["place_of_worship", "tourist_attraction"],
            "opening_hours": ["Daily: 7:00 AM – 8:00 PM"],
            "open_now": True,
            "address": "8 Pl. de Fourvière, 69005 Lyon, France",
            "city": "Lyon",
            "lat": 45.7623,
            "lng": 4.8222,
            "photo_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Dramatic hilltop 19th-century basilica perched over Lyon offering mosaic-filled interiors and sweeping city horizons.",
            "google_maps_url": "https://maps.google.com/?cid=55667788"
        }
    ],
    "nice": [
        {
            "place_id": "ChIJF1i8i6HLzRIR8-V_LwY98iM",
            "name": "Promenade des Anglais",
            "rating": 4.7,
            "review_count": 48000,
            "types": ["tourist_attraction", "point_of_interest"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "Promenade des Anglais, 06000 Nice, France",
            "city": "Nice",
            "lat": 43.6953,
            "lng": 7.2562,
            "photo_url": "https://images.unsplash.com/photo-1533105079780-92b9be482077?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Famous palm-fringed Mediterranean boulevard curving 7km along the azure Baie des Anges with iconic blue chairs.",
            "google_maps_url": "https://maps.google.com/?cid=99887766"
        }
    ],
    "moscow": [
        {
            "place_id": "ChIJw8gX671KtUYRQVb0xQOa8p0",
            "name": "Red Square & Saint Basil's Cathedral",
            "rating": 4.9,
            "review_count": 82000,
            "types": ["tourist_attraction", "point_of_interest"],
            "opening_hours": ["Daily: 10:00 AM – 6:00 PM"],
            "open_now": True,
            "address": "Red Square, Moscow 109012, Russia",
            "city": "Moscow",
            "lat": 55.7539,
            "lng": 37.6208,
            "photo_url": "https://images.unsplash.com/photo-1513622470522-26c3c8a854bc?w=800&auto=format&fit=crop&q=80",
            "price_level": 1,
            "description": "World-famous central city square flanked by the Kremlin walls, GUM department store, and the multicolored onion domes of Saint Basil's.",
            "google_maps_url": "https://maps.google.com/?cid=123123123"
        },
        {
            "place_id": "ChIJt-17d91KtUYRE2Z8-8rL8lM",
            "name": "The Moscow Kremlin",
            "rating": 4.8,
            "review_count": 65000,
            "types": ["museum", "tourist_attraction"],
            "opening_hours": ["Fri-Wed: 10:00 AM – 5:00 PM", "Thu: Closed"],
            "open_now": True,
            "address": "Moscow Kremlin, Moscow 103132, Russia",
            "city": "Moscow",
            "lat": 55.7520,
            "lng": 37.6175,
            "photo_url": "https://images.unsplash.com/photo-1547448415-e9f5b28e570d?w=800&auto=format&fit=crop&q=80",
            "price_level": 2,
            "description": "Fortified historic complex encompassing tsarist cathedrals, the Armory Chamber museum, and the Tsar Cannon.",
            "google_maps_url": "https://maps.google.com/?cid=456456456"
        }
    ],
    "saint petersburg": [
        {
            "place_id": "ChIJk956jM7xlkYRk6p0xQOa8p0",
            "name": "The State Hermitage Museum",
            "rating": 4.9,
            "review_count": 91000,
            "types": ["museum", "tourist_attraction"],
            "opening_hours": ["Tue, Thu, Sun: 11:00 AM – 6:00 PM", "Wed, Fri, Sat: 11:00 AM – 8:00 PM", "Mon: Closed"],
            "open_now": True,
            "address": "Palace Square, 2, St Petersburg 190000, Russia",
            "city": "Saint Petersburg",
            "lat": 59.9398,
            "lng": 30.3146,
            "photo_url": "https://images.unsplash.com/photo-1556610961-2fecc5927173?w=800&auto=format&fit=crop&q=80",
            "price_level": 2,
            "description": "Vast museum of art and culture housed within the Winter Palace, featuring over 3 million items including Da Vinci and Rembrandt masterpieces.",
            "google_maps_url": "https://maps.google.com/?cid=789789789"
        }
    ],
    "murmansk": [
        {
            "place_id": "ChIJb9x7kM7xlkYRv8p0xQOa8p0",
            "name": "Lenin Nuclear Icebreaker Museum",
            "rating": 4.8,
            "review_count": 14000,
            "types": ["museum", "tourist_attraction"],
            "opening_hours": ["Wed-Sun: 12:00 PM – 6:00 PM", "Mon-Tue: Closed"],
            "open_now": True,
            "address": "Portovy Spusk, 25, Murmansk 183038, Russia",
            "city": "Murmansk",
            "lat": 68.9744,
            "lng": 33.0597,
            "photo_url": "https://images.unsplash.com/photo-1517411032315-54ef2cb783bb?w=800&auto=format&fit=crop&q=80",
            "price_level": 1,
            "description": "The world's first nuclear-powered surface ship now preserved as a museum ship in Murmansk harbor.",
            "google_maps_url": "https://maps.google.com/?cid=321321321"
        },
        {
            "place_id": "ChIJc861vj3q9EcRQF6g-c4q4Q9",
            "name": "Teriberka Arctic Ocean & Aurora Base",
            "rating": 4.9,
            "review_count": 8500,
            "types": ["natural_feature", "tourist_attraction"],
            "opening_hours": ["Open 24 hours"],
            "open_now": True,
            "address": "Teriberka Coastal Settlement, Murmansk Oblast, Russia",
            "city": "Murmansk",
            "lat": 69.1650,
            "lng": 35.1420,
            "photo_url": "https://images.unsplash.com/photo-1579033461380-adb47c3eb938?w=800&auto=format&fit=crop&q=80",
            "price_level": 0,
            "description": "Dramatic Barents Sea coastline with dragon egg pebble beaches, ship graveyards, and world-class Northern Lights visibility.",
            "google_maps_url": "https://maps.google.com/?cid=654654654"
        }
    ]
}


def _haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth's radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class GooglePlacesClient:
    """
    Client for Google Places API queries (nearby search, text search, place details)
    with 24h caching and high-fidelity fallback inventory for Iceland, Japan, and global hubs.
    """

    def __init__(self, settings=None):
        self.settings = settings or get_settings()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl_seconds: int = 86400  # 24 hours

    def _get_api_key(self) -> Optional[str]:
        return self.settings.google_places_api_key

    # ========================================================================
    # Public Methods
    # ========================================================================

    async def search_nearby(
        self,
        lat: float,
        lng: float,
        radius_m: int = 5000,
        place_type: Optional[str] = "tourist_attraction",
        limit: int = 10,
    ) -> List[PlaceInfo]:
        """
        Search for attractions/places near coordinates.
        Uses Google Places Nearby Search API or curated fallback.
        """
        cache_key = f"nearby:{round(lat, 4)}:{round(lng, 4)}:{radius_m}:{place_type}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached.get("timestamp", 0) < self.cache_ttl_seconds):
            return cached["data"]

        api_key = self._get_api_key()
        if api_key:
            try:
                places = await self._query_google_nearby(lat, lng, radius_m, place_type, api_key, limit)
                if places:
                    self._cache[cache_key] = {"data": places, "timestamp": time.time()}
                    return places
            except Exception as e:
                logger.warning(f"Google Places search_nearby error: {e}. Falling back to curated inventory.")

        # Fallback to curated inventory
        fallback_places = self._generate_nearby_fallback(lat, lng, radius_m, place_type, limit)
        self._cache[cache_key] = {"data": fallback_places, "timestamp": time.time()}
        return fallback_places

    async def get_place_details(self, place_id: str) -> Optional[PlaceInfo]:
        """
        Get full details for a place_id (ratings, opening hours, photos, coordinates).
        Uses Google Places Place Details API or curated fallback.
        """
        cache_key = f"details:{place_id}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached.get("timestamp", 0) < self.cache_ttl_seconds):
            return cached["data"]

        api_key = self._get_api_key()
        if api_key:
            try:
                place = await self._query_google_details(place_id, api_key)
                if place:
                    self._cache[cache_key] = {"data": place, "timestamp": time.time()}
                    return place
            except Exception as e:
                logger.warning(f"Google Places get_place_details error: {e}. Checking curated fallback.")

        # Check curated inventory
        for city_places in CURATED_PLACES.values():
            for p in city_places:
                if p["place_id"] == place_id or place_id in p.get("name", ""):
                    place_info = PlaceInfo(**p)
                    self._cache[cache_key] = {"data": place_info, "timestamp": time.time()}
                    return place_info

        return None

    async def search_text(
        self,
        query: str,
        location_bias: Optional[Dict[str, float]] = None,
        limit: int = 10,
    ) -> List[PlaceInfo]:
        """
        Search for places matching a natural language or name query.
        Uses Google Places Text Search API or curated fallback.
        """
        clean_query = query.strip()
        bias_str = f"{round(location_bias['lat'], 3)},{round(location_bias['lng'], 3)}" if location_bias else "none"
        cache_key = f"text:{clean_query.lower()}:{bias_str}"

        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached.get("timestamp", 0) < self.cache_ttl_seconds):
            return cached["data"]

        api_key = self._get_api_key()
        if api_key:
            try:
                places = await self._query_google_text(clean_query, location_bias, api_key, limit)
                if places:
                    self._cache[cache_key] = {"data": places, "timestamp": time.time()}
                    return places
            except Exception as e:
                logger.warning(f"Google Places search_text error: {e}. Falling back to curated inventory.")

        # Fallback to curated inventory
        fallback_places = self._generate_text_fallback(clean_query, location_bias, limit)
        self._cache[cache_key] = {"data": fallback_places, "timestamp": time.time()}
        return fallback_places

    # ========================================================================
    # Google API Queries
    # ========================================================================

    async def _query_google_nearby(
        self,
        lat: float,
        lng: float,
        radius_m: int,
        place_type: Optional[str],
        api_key: str,
        limit: int,
    ) -> List[PlaceInfo]:
        # 1. Try Google Places API (New) first (preferred by modern Google Cloud keys)
        url_new = "https://places.googleapis.com/v1/places:searchNearby"
        headers_new = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.googleMapsUri,places.types"
        }
        body_new: Dict[str, Any] = {
            "maxResultCount": limit,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius_m)
                }
            }
        }
        if place_type:
            body_new["includedTypes"] = [place_type]

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url_new, json=body_new, headers=headers_new)
                if resp.status_code == 200:
                    data = resp.json()
                    new_places = data.get("places", [])
                    if new_places:
                        return [self._transform_google_v1_place_item(p) for p in new_places[:limit]]
            except Exception as e:
                logger.debug(f"Places API (New) nearby search failed: {e}")

        # 2. Fallback to Legacy Nearby Search API
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params: Dict[str, Any] = {
            "location": f"{lat},{lng}",
            "radius": radius_m,
            "key": api_key,
        }
        if place_type:
            params["type"] = place_type

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        places: List[PlaceInfo] = []
        for item in results[:limit]:
            places.append(self._transform_google_place_item(item, api_key))
        return places

    async def _query_google_details(self, place_id: str, api_key: str) -> Optional[PlaceInfo]:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "place_id,name,rating,user_ratings_total,formatted_address,geometry,opening_hours,photos,types,price_level,url,website",
            "key": api_key,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        result = data.get("result")
        if not result:
            return None
        return self._transform_google_place_item(result, api_key)

    async def _query_google_text(
        self,
        query: str,
        location_bias: Optional[Dict[str, float]],
        api_key: str,
        limit: int,
    ) -> List[PlaceInfo]:
        # 1. Try Google Places API (New) first (preferred by modern Google Cloud keys)
        url_new = "https://places.googleapis.com/v1/places:searchText"
        headers_new = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location,places.googleMapsUri,places.types"
        }
        body_new: Dict[str, Any] = {
            "textQuery": query,
            "pageSize": limit
        }
        if location_bias and "lat" in location_bias and "lng" in location_bias:
            body_new["locationBias"] = {
                "circle": {
                    "center": {"latitude": location_bias["lat"], "longitude": location_bias["lng"]},
                    "radius": 50000.0
                }
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url_new, json=body_new, headers=headers_new)
                if resp.status_code == 200:
                    data = resp.json()
                    new_places = data.get("places", [])
                    if new_places:
                        return [self._transform_google_v1_place_item(p) for p in new_places[:limit]]
            except Exception as e:
                logger.debug(f"Places API (New) text search failed: {e}")

        # 2. Fallback to Legacy Text Search API
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params: Dict[str, Any] = {
            "query": query,
            "key": api_key,
        }
        if location_bias and "lat" in location_bias and "lng" in location_bias:
            params["location"] = f"{location_bias['lat']},{location_bias['lng']}"
            params["radius"] = 50000

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        places: List[PlaceInfo] = []
        for item in results[:limit]:
            places.append(self._transform_google_place_item(item, api_key))
        return places

    def _transform_google_v1_place_item(self, item: Dict[str, Any]) -> PlaceInfo:
        """Map Google Places API (New) JSON item to PlaceInfo schema."""
        display_name = item.get("displayName", {})
        name = display_name.get("text") if isinstance(display_name, dict) else str(item.get("name", "Attraction"))
        loc = item.get("location", {})
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        types = item.get("types", [])
        place_id = item.get("id")
        maps_url = item.get("googleMapsUri") or (f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}" if name else None)

        return PlaceInfo(
            name=name,
            place_id=place_id,
            rating=item.get("rating"),
            review_count=item.get("userRatingCount"),
            types=types if isinstance(types, list) else [],
            address=item.get("formattedAddress"),
            lat=lat,
            lng=lng,
            google_maps_url=maps_url
        )

    def _transform_google_place_item(self, item: Dict[str, Any], api_key: str) -> PlaceInfo:
        """Map raw Google Places JSON item to PlaceInfo schema."""
        geom = item.get("geometry", {}).get("location", {})
        lat = geom.get("lat")
        lng = geom.get("lng")

        # Opening hours
        opening = item.get("opening_hours", {})
        weekday_text = opening.get("weekday_text")
        open_now = opening.get("open_now")

        # Photo reference
        photo_url = None
        photos = item.get("photos", [])
        if photos and isinstance(photos, list):
            photo_ref = photos[0].get("photo_reference")
            if photo_ref:
                photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photo_reference={photo_ref}&key={api_key}"

        return PlaceInfo(
            place_id=item.get("place_id"),
            name=item.get("name", "Unknown Attraction"),
            rating=float(item["rating"]) if "rating" in item else None,
            review_count=item.get("user_ratings_total"),
            types=item.get("types", []),
            opening_hours=weekday_text,
            open_now=open_now,
            address=item.get("formatted_address") or item.get("vicinity"),
            lat=lat,
            lng=lng,
            photo_url=photo_url,
            price_level=item.get("price_level"),
            google_maps_url=item.get("url"),
            website=item.get("website"),
        )

    # ========================================================================
    # Curated Fallback Logic
    # ========================================================================

    def _generate_nearby_fallback(
        self,
        lat: float,
        lng: float,
        radius_m: int,
        place_type: Optional[str],
        limit: int,
    ) -> List[PlaceInfo]:
        """Find curated attractions near given coordinates."""
        radius_km = radius_m / 1000.0
        candidates: List[tuple[float, Dict[str, Any]]] = []

        for city_places in CURATED_PLACES.values():
            for p in city_places:
                p_lat, p_lng = p.get("lat"), p.get("lng")
                if p_lat is None or p_lng is None:
                    continue
                dist = _haversine_distance_km(lat, lng, p_lat, p_lng)
                # Include within requested radius or within 100km if sparse
                if dist <= max(radius_km, 80.0):
                    candidates.append((dist, p))

        # Sort by distance
        candidates.sort(key=lambda x: x[0])
        return [PlaceInfo(**p[1]) for p in candidates[:limit]]

    def _generate_text_fallback(
        self,
        query: str,
        location_bias: Optional[Dict[str, float]],
        limit: int,
    ) -> List[PlaceInfo]:
        """Search curated attractions matching text query."""
        q_lower = query.lower().strip()
        matched: List[Dict[str, Any]] = []

        # 1. First check if query matches a city name directly
        for city_key, city_places in CURATED_PLACES.items():
            if re.search(r'\b' + re.escape(city_key) + r'\b', q_lower):
                matched.extend(city_places)

        # 2. Check individual attraction names, types, or descriptions
        for city_places in CURATED_PLACES.values():
            for p in city_places:
                if p in matched:
                    continue
                p_name = p.get("name", "").lower()
                p_desc = p.get("description", "").lower()
                p_city = p.get("city", "").lower()
                p_types = [t.lower() for t in p.get("types", [])]

                if (
                    q_lower in p_name
                    or any(q_lower in t for t in p_types)
                    or q_lower in p_city
                    or any(word in p_name for word in q_lower.split() if len(word) > 3)
                ):
                    matched.append(p)

        # If location bias is provided, sort by distance to bias
        if location_bias and "lat" in location_bias and "lng" in location_bias:
            b_lat = location_bias["lat"]
            b_lng = location_bias["lng"]
            matched.sort(
                key=lambda p: _haversine_distance_km(
                    b_lat, b_lng, p.get("lat", b_lat), p.get("lng", b_lng)
                )
            )

        if not matched:
            # Fallback to Reykjavik landmarks for general travel prompts
            matched = CURATED_PLACES.get("reykjavik", [])

        return [PlaceInfo(**p) for p in matched[:limit]]


# ============================================================================
# Singleton Factory
# ============================================================================

_google_places_client: Optional[GooglePlacesClient] = None


def get_google_places_client() -> GooglePlacesClient:
    """Get or create singleton GooglePlacesClient instance."""
    global _google_places_client
    if _google_places_client is None:
        _google_places_client = GooglePlacesClient()
    return _google_places_client

