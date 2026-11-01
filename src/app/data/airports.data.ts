import { Airport } from '../models/flight.model';

export const POPULAR_AIRPORTS: Airport[] = [
  // India
  { code: 'NAG', name: 'Dr. Babasaheb Ambedkar Intl Airport', city: 'Nagpur', country: 'India' },
  { code: 'DEL', name: 'Indira Gandhi Intl Airport', city: 'New Delhi', country: 'India' },
  { code: 'BOM', name: 'Chhatrapati Shivaji Maharaj Intl Airport', city: 'Mumbai', country: 'India' },
  { code: 'BLR', name: 'Kempegowda Intl Airport', city: 'Bengaluru', country: 'India' },
  { code: 'HYD', name: 'Rajiv Gandhi Intl Airport', city: 'Hyderabad', country: 'India' },
  { code: 'MAA', name: 'Chennai International Airport', city: 'Chennai', country: 'India' },
  { code: 'CCU', name: 'Netaji Subhash Chandra Bose Intl Airport', city: 'Kolkata', country: 'India' },
  { code: 'GOI', name: 'Dabolim Airport', city: 'Goa', country: 'India' },
  { code: 'GOX', name: 'Manohar Intl Airport (Mopa)', city: 'Goa', country: 'India' },
  { code: 'PNQ', name: 'Pune Airport', city: 'Pune', country: 'India' },
  { code: 'AMD', name: 'Sardar Vallabhbhai Patel Intl Airport', city: 'Ahmedabad', country: 'India' },
  { code: 'COK', name: 'Cochin International Airport', city: 'Kochi', country: 'India' },

  // Iceland & Nordic (Addressing user's Reykjavik request)
  { code: 'KEF', name: 'Keflavík International Airport', city: 'Reykjavik', country: 'Iceland' },
  { code: 'RKV', name: 'Reykjavík Domestic Airport', city: 'Reykjavik', country: 'Iceland' },
  { code: 'OSL', name: 'Oslo Gardermoen Airport', city: 'Oslo', country: 'Norway' },
  { code: 'TOS', name: 'Tromsø Airport, Langnes', city: 'Tromsø', country: 'Norway' },
  { code: 'ARN', name: 'Stockholm Arlanda Airport', city: 'Stockholm', country: 'Sweden' },
  { code: 'CPH', name: 'Copenhagen Kastrup Airport', city: 'Copenhagen', country: 'Denmark' },
  { code: 'HEL', name: 'Helsinki-Vantaa Airport', city: 'Helsinki', country: 'Finland' },

  // Western & Southern Europe
  { code: 'LHR', name: 'Heathrow Airport', city: 'London', country: 'United Kingdom' },
  { code: 'LGW', name: 'Gatwick Airport', city: 'London', country: 'United Kingdom' },
  { code: 'MAN', name: 'Manchester Airport', city: 'Manchester', country: 'United Kingdom' },
  { code: 'EDI', name: 'Edinburgh Airport', city: 'Edinburgh', country: 'United Kingdom' },
  { code: 'CDG', name: 'Charles de Gaulle Airport', city: 'Paris', country: 'France' },
  { code: 'ORY', name: 'Paris Orly Airport', city: 'Paris', country: 'France' },
  { code: 'NCE', name: 'Nice Côte d’Azur Airport', city: 'Nice', country: 'France' },
  { code: 'FRA', name: 'Frankfurt am Main Airport', city: 'Frankfurt', country: 'Germany' },
  { code: 'MUC', name: 'Munich Airport', city: 'Munich', country: 'Germany' },
  { code: 'BER', name: 'Berlin Brandenburg Airport', city: 'Berlin', country: 'Germany' },
  { code: 'AMS', name: 'Amsterdam Schiphol Airport', city: 'Amsterdam', country: 'Netherlands' },
  { code: 'ZRH', name: 'Zurich Airport', city: 'Zurich', country: 'Switzerland' },
  { code: 'GVA', name: 'Geneva Airport', city: 'Geneva', country: 'Switzerland' },
  { code: 'VIE', name: 'Vienna International Airport', city: 'Vienna', country: 'Austria' },
  { code: 'FCO', name: 'Leonardo da Vinci–Fiumicino Airport', city: 'Rome', country: 'Italy' },
  { code: 'MXP', name: 'Milan Malpensa Airport', city: 'Milan', country: 'Italy' },
  { code: 'VCE', name: 'Venice Marco Polo Airport', city: 'Venice', country: 'Italy' },
  { code: 'BCN', name: 'Josep Tarradellas Barcelona-El Prat', city: 'Barcelona', country: 'Spain' },
  { code: 'MAD', name: 'Adolfo Suárez Madrid–Barajas Airport', city: 'Madrid', country: 'Spain' },
  { code: 'LIS', name: 'Humberto Delgado Airport', city: 'Lisbon', country: 'Portugal' },
  { code: 'ATH', name: 'Athens International Airport', city: 'Athens', country: 'Greece' },
  { code: 'IST', name: 'Istanbul Airport', city: 'Istanbul', country: 'Turkey' },

  // Asia & Southeast Asia
  { code: 'SIN', name: 'Singapore Changi Airport', city: 'Singapore', country: 'Singapore' },
  { code: 'BKK', name: 'Suvarnabhumi Airport', city: 'Bangkok', country: 'Thailand' },
  { code: 'DMK', name: 'Don Mueang Intl Airport', city: 'Bangkok', country: 'Thailand' },
  { code: 'HKT', name: 'Phuket International Airport', city: 'Phuket', country: 'Thailand' },
  { code: 'KUL', name: 'Kuala Lumpur International Airport', city: 'Kuala Lumpur', country: 'Malaysia' },
  { code: 'DPS', name: 'Ngurah Rai (Bali) International Airport', city: 'Denpasar Bali', country: 'Indonesia' },
  { code: 'CGK', name: 'Soekarno–Hatta International Airport', city: 'Jakarta', country: 'Indonesia' },
  { code: 'SGN', name: 'Tan Son Nhat International Airport', city: 'Ho Chi Minh City', country: 'Vietnam' },
  { code: 'HAN', name: 'Noi Bai International Airport', city: 'Hanoi', country: 'Vietnam' },
  { code: 'HKG', name: 'Hong Kong International Airport', city: 'Hong Kong', country: 'Hong Kong' },

  // East Asia
  { code: 'HND', name: 'Tokyo Haneda Airport', city: 'Tokyo', country: 'Japan' },
  { code: 'NRT', name: 'Narita International Airport', city: 'Tokyo', country: 'Japan' },
  { code: 'KIX', name: 'Kansai International Airport', city: 'Osaka', country: 'Japan' },
  { code: 'ICN', name: 'Incheon International Airport', city: 'Seoul', country: 'South Korea' },
  { code: 'TPE', name: 'Taiwan Taoyuan International Airport', city: 'Taipei', country: 'Taiwan' },
  { code: 'PEK', name: 'Beijing Capital International Airport', city: 'Beijing', country: 'China' },
  { code: 'PVG', name: 'Shanghai Pudong International Airport', city: 'Shanghai', country: 'China' },

  // Middle East
  { code: 'DXB', name: 'Dubai International Airport', city: 'Dubai', country: 'United Arab Emirates' },
  { code: 'AUH', name: 'Zayed International Airport', city: 'Abu Dhabi', country: 'United Arab Emirates' },
  { code: 'DOH', name: 'Hamad International Airport', city: 'Doha', country: 'Qatar' },
  { code: 'SHJ', name: 'Sharjah International Airport', city: 'Sharjah', country: 'United Arab Emirates' },
  { code: 'RUH', name: 'King Khalid International Airport', city: 'Riyadh', country: 'Saudi Arabia' },

  // North America
  { code: 'JFK', name: 'John F. Kennedy International Airport', city: 'New York', country: 'United States' },
  { code: 'EWR', name: 'Newark Liberty International Airport', city: 'New York', country: 'United States' },
  { code: 'LGA', name: 'LaGuardia Airport', city: 'New York', country: 'United States' },
  { code: 'LAX', name: 'Los Angeles International Airport', city: 'Los Angeles', country: 'United States' },
  { code: 'SFO', name: 'San Francisco International Airport', city: 'San Francisco', country: 'United States' },
  { code: 'ORD', name: "O'Hare International Airport", city: 'Chicago', country: 'United States' },
  { code: 'MIA', name: 'Miami International Airport', city: 'Miami', country: 'United States' },
  { code: 'SEA', name: 'Seattle-Tacoma International Airport', city: 'Seattle', country: 'United States' },
  { code: 'BOS', name: 'Logan International Airport', city: 'Boston', country: 'United States' },
  { code: 'YVR', name: 'Vancouver International Airport', city: 'Vancouver', country: 'Canada' },
  { code: 'YYZ', name: 'Toronto Pearson International Airport', city: 'Toronto', country: 'Canada' },

  // Oceania
  { code: 'SYD', name: 'Sydney Kingsford Smith Airport', city: 'Sydney', country: 'Australia' },
  { code: 'MEL', name: 'Melbourne Airport', city: 'Melbourne', country: 'Australia' },
  { code: 'AKL', name: 'Auckland Airport', city: 'Auckland', country: 'New Zealand' }
];
