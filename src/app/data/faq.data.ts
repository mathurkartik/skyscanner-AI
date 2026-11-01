export interface FAQItem {
  id: string;
  question: string;
  answer: string;
  category: 'flights' | 'hotels' | 'cars' | 'general';
}

export const SKYSCANNER_FAQS: FAQItem[] = [
  {
    id: 'faq-1',
    question: 'How does Skyscanner work?',
    answer: 'Skyscanner is a metasearch engine that scans over 1,200 travel providers, airlines, and online travel agencies (OTAs) simultaneously. When you search for flights, hotels, or car hire, we aggregate and compare all available options in real time so you can find the best deal without booking markups.',
    category: 'flights'
  },
  {
    id: 'faq-2',
    question: 'How can I find the cheapest flight using Skyscanner?',
    answer: 'To find the cheapest flights: 1) Use our "Whole Month" or "Explore Everywhere" search if your travel dates are flexible. 2) Set up a Price Alert to get notified when airfares drop. 3) Compare "Direct only" vs. 1-stop flights to balance speed and price.',
    category: 'flights'
  },
  {
    id: 'faq-3',
    question: 'Where should I book a flight to right now?',
    answer: 'Try searching "Explore everywhere" from your departure airport. We sort destinations worldwide by the lowest current price, revealing trending getaways, budget city breaks, and flight sales available this week or month.',
    category: 'flights'
  },
  {
    id: 'faq-4',
    question: 'Do I book my flight with Skyscanner?',
    answer: 'Skyscanner is free to use and never charges any hidden fees. Once you select a flight, hotel, or car deal, we redirect you directly to the airline, hotel, or travel agency to complete your booking securely on their platform.',
    category: 'general'
  },
  {
    id: 'faq-5',
    question: 'What happens after I have booked my flight?',
    answer: 'Your booking confirmation, electronic ticket (e-ticket), and itinerary are sent directly by the provider or airline you completed your purchase with. If you need to make changes or check baggage rules, simply contact your booking provider.',
    category: 'general'
  },
  {
    id: 'faq-6',
    question: 'Does Skyscanner do hotels too?',
    answer: 'Yes! Skyscanner compares millions of hotel rooms, boutique ryokans, apartments, and luxury resorts across leading platforms like Booking.com, Agoda, Expedia, and direct hotel sites, offering free cancellation filters and verified guest reviews.',
    category: 'hotels'
  },
  {
    id: 'faq-7',
    question: 'What about car hire?',
    answer: 'Our car rental search lets you compare deals from top rental companies (Hertz, Avis, Enterprise, Sixt, Europcar). You can filter by car size (Economy, SUV, Electric, Luxury), transmission type, fuel policy, and pickup location.',
    category: 'cars'
  },
  {
    id: 'faq-8',
    question: "What's a Price Alert?",
    answer: 'A Price Alert watches a specific route and travel date for you. Whenever airfares increase or drop, we send you an instant notification so you can lock in the lowest ticket price.',
    category: 'flights'
  },
  {
    id: 'faq-9',
    question: 'Can I book a flexible flight ticket?',
    answer: 'Yes. Many airlines provide flexible tickets that allow penalty-free date changes or flight credits. You can look for flexible booking badges on our flight cards or filter for providers with free rebooking.',
    category: 'flights'
  },
  {
    id: 'faq-10',
    question: 'Can I book flights that emit less CO₂?',
    answer: 'Look for our "Greener choice" leaf badge on flight results. These flights emit significantly lower carbon dioxide (CO₂) than the average flight on the same route, often due to more fuel-efficient modern aircraft or optimized direct flight paths.',
    category: 'flights'
  }
];

export const INTERNATIONAL_SITES = [
  { name: 'India', domain: 'www.skyscanner.co.in' },
  { name: 'United Kingdom', domain: 'www.skyscanner.net' },
  { name: 'United States', domain: 'www.skyscanner.com' },
  { name: 'France', domain: 'www.skyscanner.fr' },
  { name: 'Germany', domain: 'www.skyscanner.de' },
  { name: 'Japan', domain: 'www.skyscanner.jp' },
  { name: 'Spain', domain: 'www.skyscanner.es' },
  { name: 'Italy', domain: 'www.skyscanner.it' },
  { name: 'Australia', domain: 'www.skyscanner.com.au' },
  { name: 'Singapore', domain: 'www.skyscanner.com.sg' },
  { name: 'Canada', domain: 'www.skyscanner.ca' },
  { name: 'Brazil', domain: 'www.skyscanner.com.br' }
];

