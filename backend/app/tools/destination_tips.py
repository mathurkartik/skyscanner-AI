"""
Structured destination tips database and regional cost-saving advice (AG-047).
Covers major global travel corridors with genuine local saving strategies.
"""

from typing import List, Dict
from ..models.schemas import CostSavingTip


DESTINATION_TIPS_DATABASE: Dict[str, List[Dict[str, str]]] = {
    "france": [
        {
            "title": "Get the Paris Museum Pass",
            "description": "A 4-day Paris Museum Pass (€70) gives skip-the-line access to over 50 museums and monuments including the Louvre, Musée d'Orsay, and Arc de Triomphe.",
            "estimated_savings": "Save €40 - €70 vs individual tickets"
        },
        {
            "title": "Book TGV / OUIGO Trains Early",
            "description": "SNCF opens TGV high-speed and low-cost OUIGO bookings 3 months ahead with tickets from €19 compared to €80+ on travel week.",
            "estimated_savings": "Save 60% - 75% on intercity transit"
        },
        {
            "title": "Dine at Boulangeries and Set-Menu Bistros",
            "description": "Opt for a boulangerie formule déjeuner (sandwich, dessert, beverage for €8-€10) and bistros offering 'menu du jour' at lunch instead of pricey dinners.",
            "estimated_savings": "Save €25 - €40 per person daily"
        }
    ],
    "japan": [
        {
            "title": "Use 24/48/72-Hour Tokyo Subway Passes",
            "description": "Unlimited rides on all Tokyo Metro and Toei Subway lines for only ¥1,500 (72 hours), saving significant money over single IC fares.",
            "estimated_savings": "Save ¥1,000 - ¥2,000 per day"
        },
        {
            "title": "Take Advantage of Evening Depachika Sales",
            "description": "Department store basement food halls (depachika) discount gourmet bento and sushi boxes by 20% to 50% every evening after 7:30 PM.",
            "estimated_savings": "Save ¥1,500 - ¥3,000 per meal"
        },
        {
            "title": "Compare Regional Rail Passes with Individual Shinkansen",
            "description": "Unless doing heavy cross-country travel, point-to-point Shinkansen tickets via the SmartEX app often cost less than nationwide rail passes.",
            "estimated_savings": "Save $80 - $150 per person"
        }
    ],
    "iceland": [
        {
            "title": "Stock Up at Bónus or Krónan Discount Supermarkets",
            "description": "Icelandic restaurants and roadside diners carry high markups. Buying breakfast and road trip snacks at Bónus cuts food bills dramatically.",
            "estimated_savings": "Save $40 - $70 per person daily"
        },
        {
            "title": "Visit Local Geothermal Pools Over Commercial Spas",
            "description": "Local municipal pools like Laugardalslaug cost around 1,200 ISK ($9) and offer authentic hot pots, saunas, and steam rooms without $100+ resort fees.",
            "estimated_savings": "Save $80 - $120 per visit"
        },
        {
            "title": "Fill Up with Rental Fuel Key Discount Fobs",
            "description": "Most car rental agencies provide key fobs that give 3-5 ISK per liter discounts and free coffee at designated gas stations (N1, Olís, Orkan).",
            "estimated_savings": "Save 5% - 8% on total fuel"
        }
    ],
    "italy": [
        {
            "title": "Book Frecciarossa High-Speed Trains in Advance",
            "description": "Trenitalia and Italo release super-economy rail fares 3 to 4 months in advance, slashing fares between Rome, Florence, and Venice by over 60%.",
            "estimated_savings": "Save €35 - €60 per ticket"
        },
        {
            "title": "Stand at the Bar for Coffee & Pastries",
            "description": "In Italy, having your espresso or cappuccino 'al banco' (standing at the counter) costs €1.20-€1.50 vs €4-€6 when seated at a table (servizio).",
            "estimated_savings": "Save €5 - €10 daily per person"
        },
        {
            "title": "Visit State Museums on First Sundays",
            "description": "All Italian state museums, archaeological sites, and monuments (including the Colosseum and Pompeii) offer free entry on the first Sunday of each month.",
            "estimated_savings": "Save €18 - €30 per attraction"
        }
    ],
    "switzerland": [
        {
            "title": "Evaluate Swiss Half Fare Card vs Swiss Travel Pass",
            "description": "For 5-10 day itineraries, the Swiss Half Fare Card (CHF 120) combined with Saver Day Passes frequently beats the all-inclusive Swiss Travel Pass.",
            "estimated_savings": "Save CHF 80 - CHF 150 per traveler"
        },
        {
            "title": "Shop at Coop and Migros Supermarkets",
            "description": "Dine like locals with high-quality takeaway salads, rösti, and artisan sandwiches from Coop to avoid $40+ baseline restaurant meals.",
            "estimated_savings": "Save CHF 30 - CHF 50 per day"
        },
        {
            "title": "Take Free Guest Card Local Transit",
            "description": "Overnight hotel and Airbnb guests in cities like Lucerne, Interlaken, and Geneva receive free regional bus and local boat passes at check-in.",
            "estimated_savings": "Save CHF 10 - CHF 20 daily"
        }
    ],
    "india": [
        {
            "title": "Use IRCTC Tatkal or Premium Tatkal for Rail",
            "description": "Vande Bharat Express and 2AC/3AC Rajdhani trains provide world-class comfort at a fraction of domestic airfare between major hubs.",
            "estimated_savings": "Save ₹2,000 - ₹5,000 vs last-minute flights"
        },
        {
            "title": "Book ASI Monument Tickets Online via QR",
            "description": "Buying monument tickets online at asi.nic.in grants a direct discount and bypasses long ticket counter queues at monuments like the Taj Mahal.",
            "estimated_savings": "Save ₹50 - ₹100 per ticket + 45 min queue time"
        },
        {
            "title": "Use App-Based Cabs & Metro Smart Cards",
            "description": "In Delhi, Mumbai, and Bengaluru, metro transit and rideshare apps eliminate auto-rickshaw tourist markups and traffic delays.",
            "estimated_savings": "Save 40% - 60% on intra-city transfers"
        }
    ],
    "united kingdom": [
        {
            "title": "Tap In/Out with Contactless Cards in London",
            "description": "Daily contactless fare capping on TfL matches Oyster cards with zero deposit fee across underground, bus, and DLR networks.",
            "estimated_savings": "Save £10 - £15 vs single paper tickets"
        },
        {
            "title": "Book Advance Rail Tickets with Split-Ticketing",
            "description": "Splitting long-distance train tickets (e.g., London to Edinburgh) via apps like SplitMyFare cuts National Rail fares significantly.",
            "estimated_savings": "Save 30% - 50% on rail transit"
        },
        {
            "title": "Enjoy Free National Museums and Galleries",
            "description": "World-class institutions like the British Museum, Tate Modern, National Gallery, and V&A are completely free to enter.",
            "estimated_savings": "Save £20 - £30 per museum visit"
        }
    ],
    "united states": [
        {
            "title": "Get the America the Beautiful National Parks Pass",
            "description": "An $80 annual pass covers vehicle entrance to over 2,000 federal recreation sites including Yellowstone, Yosemite, and the Grand Canyon.",
            "estimated_savings": "Save $50 - $120 on multi-park road trips"
        },
        {
            "title": "Use Transit Passes in Major Metros",
            "description": "Cities like New York (OMNY 7-day cap), Chicago (CTA passes), and San Francisco offer steep unlimited transit savings.",
            "estimated_savings": "Save $20 - $40 per traveler weekly"
        },
        {
            "title": "Book Accommodations Outside City Centers with Transit Links",
            "description": "Staying 3-4 metro stops outside downtown Manhattan, San Francisco, or Washington DC lowers nightly room rates by 35-50%.",
            "estimated_savings": "Save $80 - $160 per night"
        }
    ],
    "russia": [
        {
            "title": "Use Troika & Podorozhnik Metro Smart Cards",
            "description": "Moscow and Saint Petersburg metros have world-class networks. A Troika card offers deeply discounted rides and seamless transfers between metro, MCC, and trams.",
            "estimated_savings": "Save 40% vs single ride tokens"
        },
        {
            "title": "Book Sapsan & Arctic Trains via Official RZD Portal",
            "description": "High-speed Sapsan trains between Moscow and St. Petersburg, and the Arctic overnight sleeper to Murmansk, open 90 days ahead with dynamic tiered pricing.",
            "estimated_savings": "Save 50% vs last-minute agencies"
        },
        {
            "title": "Book Multi-Night Aurora Chasing Packages",
            "description": "Northern lights in Murmansk/Teriberka require mobile weather tracking. Multi-night local guide passes guarantee re-runs on cloudy nights.",
            "estimated_savings": "Save 30% on combined aurora excursions"
        }
    ]
}

GENERIC_TIPS: List[Dict[str, str]] = [
    {
        "title": "Book Flights 6-8 Weeks in Advance",
        "description": "Skyscanner historical pricing indicates airfare rises by 18-24% inside the 3-week departure window.",
        "estimated_savings": "Save 15% - 25% on flights"
    },
    {
        "title": "Opt for Neighborhood Stays with Transit Links",
        "description": "Choosing well-reviewed accommodations just 2-3 metro stops from the historic center yields 30-40% lower nightly rates.",
        "estimated_savings": "Save $30 - $60 per night"
    },
    {
        "title": "Use Multi-Attraction City Passes & Walking Tours",
        "description": "City tourism cards bundle public transit with top museum admissions and offer free guided walking tours.",
        "estimated_savings": "Save $20 - $40 per traveler"
    }
]


def get_destination_tips(destination: str, currency: str = "USD") -> List[CostSavingTip]:
    """Retrieve curated destination tips for a country, region, or city (AG-047)."""
    dest_lower = (destination or "").lower()

    matched_tips: List[Dict[str, str]] = []
    for key, tips in DESTINATION_TIPS_DATABASE.items():
        if key in dest_lower or dest_lower in key:
            matched_tips = tips
            break

    if not matched_tips:
        matched_tips = GENERIC_TIPS

    return [
        CostSavingTip(
            title=tip["title"],
            description=tip["description"],
            estimated_savings=tip["estimated_savings"]
        )
        for tip in matched_tips
    ]

