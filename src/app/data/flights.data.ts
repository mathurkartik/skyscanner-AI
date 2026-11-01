import { FlightOffer, Airport, CabinClass, FlightSegment } from '../models/flight.model';

export interface RouteProfile {
  primaryAirlines: { name: string; code: string; logo: string }[];
  viaHubs: string[];
  baseDurationMinutes: number;
  basePriceUSD: number;
  stopsCount: number;
}

interface FlightOptionConfig {
  airline: string;
  airlineCode: string;
  logo: string;
  carrierFirstLeg?: { name: string; code: string; logo: string; flightNumber: string };
  stops: string[];
  outDepartTime: string;
  outArrivalTime: string;
  outDuration: number;
  inDepartTime: string;
  inArrivalTime: string;
  inDuration: number;
  aircraft: string;
  baseUSD: number;
  co2: number;
}

export function generateFlightsForRoute(
  origin: Airport,
  destination: Airport,
  departDate: string,
  returnDate: string | null,
  cabinClass: CabinClass,
  passengers: number
): FlightOffer[] {
  const offers: FlightOffer[] = [];
  const basePriceMultiplier = cabinClass === 'first' ? 3.5 : cabinClass === 'business' ? 2.5 : cabinClass === 'premium_economy' ? 1.4 : 1.0;

  // Regional classifications
  const isIndiaOrigin = origin.country === 'India';
  const isRegionalIndia = isIndiaOrigin && ['NAG', 'PNQ', 'AMD', 'COK', 'GOI', 'GOX'].includes(origin.code);
  const isAustralia = ['MEL', 'SYD', 'BNE', 'PER', 'AKL'].includes(destination.code);
  const isSingapore = destination.code === 'SIN';
  const isIceland = ['KEF', 'RKV'].includes(destination.code);
  const isJapan = ['HND', 'NRT', 'KIX'].includes(destination.code);
  const isEurope = ['LHR', 'CDG', 'FRA', 'AMS', 'ZRH', 'FCO', 'BCN', 'MAD', 'VIE'].includes(destination.code);
  const isNorthAmerica = ['JFK', 'EWR', 'SFO', 'LAX', 'ORD', 'SEA', 'BOS', 'YVR', 'YYZ'].includes(destination.code);
  const isMiddleEast = ['DXB', 'AUH', 'DOH', 'SHJ'].includes(destination.code);
  const isSoutheastAsia = ['BKK', 'HKT', 'DPS', 'KUL', 'CGK', 'SGN'].includes(destination.code);

  let routeOptions: FlightOptionConfig[] = [];

  // ==========================================
  // CASE 1: NAGPUR (NAG) / REGIONAL INDIA TO AUSTRALIA (MEL, SYD)
  // ==========================================
  if (isRegionalIndia && isAustralia) {
    routeOptions = [
      {
        airline: 'IndiGo & Qantas',
        airlineCode: 'QF',
        logo: 'https://images.kiwi.com/airlines/64/QF.png',
        carrierFirstLeg: { name: 'IndiGo', code: '6E', logo: 'https://images.kiwi.com/airlines/64/6E.png', flightNumber: '6E 5024' },
        stops: ['DEL'],
        outDepartTime: '07:15',
        outArrivalTime: '12:20', // +1 day
        outDuration: 1355, // 22h 35m
        inDepartTime: '15:15',
        inArrivalTime: '22:45',
        inDuration: 1380,
        aircraft: 'Airbus A320neo / Airbus A330-200',
        baseUSD: 820,
        co2: 18
      },
      {
        airline: 'Air India & Singapore Airlines',
        airlineCode: 'SQ',
        logo: 'https://images.kiwi.com/airlines/64/SQ.png',
        carrierFirstLeg: { name: 'Air India', code: 'AI', logo: 'https://images.kiwi.com/airlines/64/AI.png', flightNumber: 'AI 470' },
        stops: ['DEL', 'SIN'],
        outDepartTime: '08:45',
        outArrivalTime: '10:10', // +1 day
        outDuration: 1255, // 20h 55m
        inDepartTime: '00:45',
        inArrivalTime: '21:10',
        inDuration: 1315,
        aircraft: 'Airbus A350-900 / Boeing 777-300ER',
        baseUSD: 890,
        co2: 24
      },
      {
        airline: 'IndiGo & Malaysia Airlines',
        airlineCode: 'MH',
        logo: 'https://images.kiwi.com/airlines/64/MH.png',
        carrierFirstLeg: { name: 'IndiGo', code: '6E', logo: 'https://images.kiwi.com/airlines/64/6E.png', flightNumber: '6E 421' },
        stops: ['BOM', 'KUL'],
        outDepartTime: '17:30',
        outArrivalTime: '19:30', // +1 day
        outDuration: 1320, // 22h
        inDepartTime: '23:40',
        inArrivalTime: '00:15',
        inDuration: 1295,
        aircraft: 'Airbus A321neo / Airbus A330-300',
        baseUSD: 745,
        co2: 0
      },
      {
        airline: 'Air Arabia & Emirates',
        airlineCode: 'EK',
        logo: 'https://images.kiwi.com/airlines/64/EK.png',
        carrierFirstLeg: { name: 'Air Arabia', code: 'G9', logo: 'https://images.kiwi.com/airlines/64/G9.png', flightNumber: 'G9 498' },
        stops: ['SHJ', 'DXB'],
        outDepartTime: '04:10',
        outArrivalTime: '06:30', // +1 day
        outDuration: 1340, // 22h 20m
        inDepartTime: '18:15',
        inArrivalTime: '03:15',
        inDuration: 1410,
        aircraft: 'Airbus A320 / Airbus A380-800',
        baseUSD: 960,
        co2: 0
      }
    ];
  }

  // ==========================================
  // CASE 2: NAGPUR (NAG) / REGIONAL INDIA TO SINGAPORE (SIN)
  // ==========================================
  else if (isRegionalIndia && isSingapore) {
    routeOptions = [
      {
        airline: 'IndiGo',
        airlineCode: '6E',
        logo: 'https://images.kiwi.com/airlines/64/6E.png',
        stops: ['BOM'],
        outDepartTime: '07:15',
        outArrivalTime: '19:40',
        outDuration: 565, // 9h 25m
        inDepartTime: '21:00',
        inArrivalTime: '06:30',
        inDuration: 570,
        aircraft: 'Airbus A320neo / A321neo',
        baseUSD: 310,
        co2: 18
      },
      {
        airline: 'Air India & Singapore Airlines',
        airlineCode: 'SQ',
        logo: 'https://images.kiwi.com/airlines/64/SQ.png',
        carrierFirstLeg: { name: 'Air India', code: 'AI', logo: 'https://images.kiwi.com/airlines/64/AI.png', flightNumber: 'AI 470' },
        stops: ['DEL'],
        outDepartTime: '08:45',
        outArrivalTime: '20:15',
        outDuration: 570,
        inDepartTime: '16:55',
        inArrivalTime: '00:10',
        inDuration: 555,
        aircraft: 'Airbus A350-900',
        baseUSD: 420,
        co2: 12
      },
      {
        airline: 'Air India',
        airlineCode: 'AI',
        logo: 'https://images.kiwi.com/airlines/64/AI.png',
        stops: ['BOM'],
        outDepartTime: '09:20',
        outArrivalTime: '21:30',
        outDuration: 610,
        inDepartTime: '07:15',
        inArrivalTime: '14:40',
        inDuration: 565,
        aircraft: 'Boeing 787-8 Dreamliner',
        baseUSD: 350,
        co2: 0
      },
      {
        airline: 'Air Arabia & Emirates',
        airlineCode: 'EK',
        logo: 'https://images.kiwi.com/airlines/64/EK.png',
        carrierFirstLeg: { name: 'Air Arabia', code: 'G9', logo: 'https://images.kiwi.com/airlines/64/G9.png', flightNumber: 'G9 498' },
        stops: ['SHJ'],
        outDepartTime: '04:10',
        outArrivalTime: '21:10',
        outDuration: 840,
        inDepartTime: '09:30',
        inArrivalTime: '03:15',
        inDuration: 885,
        aircraft: 'Boeing 777-300ER',
        baseUSD: 480,
        co2: 0
      }
    ];
  }

  // ==========================================
  // CASE 3: NAGPUR (NAG) / INDIA TO REYKJAVIK (KEF)
  // ==========================================
  else if (isIndiaOrigin && isIceland) {
    routeOptions = [
      {
        airline: 'Air India & Lufthansa',
        airlineCode: 'LH',
        logo: 'https://images.kiwi.com/airlines/64/LH.png',
        carrierFirstLeg: { name: 'Air India', code: 'AI', logo: 'https://images.kiwi.com/airlines/64/AI.png', flightNumber: 'AI 470' },
        stops: isRegionalIndia ? ['DEL', 'FRA'] : ['FRA'],
        outDepartTime: '08:45',
        outArrivalTime: '23:40',
        outDuration: 1135,
        inDepartTime: '00:30',
        inArrivalTime: '01:50',
        inDuration: 1100,
        aircraft: 'Boeing 787-9 / Airbus A321',
        baseUSD: 790,
        co2: 14
      },
      {
        airline: 'IndiGo & British Airways',
        airlineCode: 'BA',
        logo: 'https://images.kiwi.com/airlines/64/BA.png',
        carrierFirstLeg: { name: 'IndiGo', code: '6E', logo: 'https://images.kiwi.com/airlines/64/6E.png', flightNumber: '6E 421' },
        stops: isRegionalIndia ? ['BOM', 'LHR'] : ['LHR'],
        outDepartTime: '07:15',
        outArrivalTime: '21:55',
        outDuration: 1180,
        inDepartTime: '11:15',
        inArrivalTime: '12:30',
        inDuration: 1155,
        aircraft: 'Airbus A350-1000',
        baseUSD: 845,
        co2: 0
      },
      {
        airline: 'Qatar Airways & Icelandair',
        airlineCode: 'FI',
        logo: 'https://images.kiwi.com/airlines/64/FI.png',
        carrierFirstLeg: { name: 'IndiGo', code: '6E', logo: 'https://images.kiwi.com/airlines/64/6E.png', flightNumber: '6E 421' },
        stops: isRegionalIndia ? ['BOM', 'DOH'] : ['DOH'],
        outDepartTime: '18:30',
        outArrivalTime: '15:20',
        outDuration: 1370,
        inDepartTime: '07:45',
        inArrivalTime: '05:30',
        inDuration: 1305,
        aircraft: 'Boeing 787-8 Dreamliner',
        baseUSD: 890,
        co2: 24
      }
    ];
  }

  // ==========================================
  // CASE 4: NAGPUR (NAG) / INDIA TO JAPAN (HND / NRT)
  // ==========================================
  else if (isIndiaOrigin && isJapan) {
    routeOptions = [
      {
        airline: 'All Nippon Airways (ANA)',
        airlineCode: 'NH',
        logo: 'https://images.kiwi.com/airlines/64/NH.png',
        carrierFirstLeg: isRegionalIndia ? { name: 'Air India', code: 'AI', logo: 'https://images.kiwi.com/airlines/64/AI.png', flightNumber: 'AI 470' } : undefined,
        stops: isRegionalIndia ? ['DEL'] : [],
        outDepartTime: '08:45',
        outArrivalTime: '06:00',
        outDuration: isRegionalIndia ? 795 : 555,
        inDepartTime: '10:45',
        inArrivalTime: '20:15',
        inDuration: isRegionalIndia ? 810 : 570,
        aircraft: 'Boeing 787-9 Dreamliner',
        baseUSD: 720,
        co2: 21
      },
      {
        airline: 'Japan Airlines (JAL)',
        airlineCode: 'JL',
        logo: 'https://images.kiwi.com/airlines/64/JL.png',
        carrierFirstLeg: isRegionalIndia ? { name: 'Air India', code: 'AI', logo: 'https://images.kiwi.com/airlines/64/AI.png', flightNumber: 'AI 470' } : undefined,
        stops: isRegionalIndia ? ['DEL'] : [],
        outDepartTime: '11:30',
        outArrivalTime: '07:15',
        outDuration: isRegionalIndia ? 765 : 525,
        inDepartTime: '11:30',
        inArrivalTime: '20:45',
        inDuration: isRegionalIndia ? 795 : 555,
        aircraft: 'Boeing 787-8 Dreamliner',
        baseUSD: 740,
        co2: 18
      },
      {
        airline: 'Singapore Airlines',
        airlineCode: 'SQ',
        logo: 'https://images.kiwi.com/airlines/64/SQ.png',
        carrierFirstLeg: isRegionalIndia ? { name: 'IndiGo', code: '6E', logo: 'https://images.kiwi.com/airlines/64/6E.png', flightNumber: '6E 421' } : undefined,
        stops: isRegionalIndia ? ['BOM', 'SIN'] : ['SIN'],
        outDepartTime: '07:15',
        outArrivalTime: '08:45',
        outDuration: 1050,
        inDepartTime: '11:15',
        inArrivalTime: '19:40',
        inDuration: 985,
        aircraft: 'Airbus A350-900',
        baseUSD: 660,
        co2: 0
      }
    ];
  }

  // ==========================================
  // CASE 5: NAGPUR (NAG) / REGIONAL INDIA TO EUROPE / USA
  // ==========================================
  else if (isRegionalIndia && (isEurope || isNorthAmerica)) {
    routeOptions = [
      {
        airline: 'IndiGo & British Airways',
        airlineCode: 'BA',
        logo: 'https://images.kiwi.com/airlines/64/BA.png',
        carrierFirstLeg: { name: 'IndiGo', code: '6E', logo: 'https://images.kiwi.com/airlines/64/6E.png', flightNumber: '6E 421' },
        stops: isNorthAmerica ? ['BOM', 'LHR'] : ['BOM'],
        outDepartTime: '07:15',
        outArrivalTime: '18:45',
        outDuration: isNorthAmerica ? 1280 : 810,
        inDepartTime: '10:30',
        inArrivalTime: '12:30',
        inDuration: isNorthAmerica ? 1220 : 790,
        aircraft: 'Boeing 777-300ER',
        baseUSD: isNorthAmerica ? 880 : 640,
        co2: 16
      },
      {
        airline: 'Air India',
        airlineCode: 'AI',
        logo: 'https://images.kiwi.com/airlines/64/AI.png',
        carrierFirstLeg: { name: 'Air India', code: 'AI', logo: 'https://images.kiwi.com/airlines/64/AI.png', flightNumber: 'AI 470' },
        stops: ['DEL'],
        outDepartTime: '08:45',
        outArrivalTime: '19:15',
        outDuration: isNorthAmerica ? 1190 : 750,
        inDepartTime: '13:00',
        inArrivalTime: '15:40',
        inDuration: isNorthAmerica ? 1160 : 720,
        aircraft: 'Boeing 777-200LR / B787-8',
        baseUSD: isNorthAmerica ? 940 : 680,
        co2: 0
      },
      {
        airline: 'Emirates',
        airlineCode: 'EK',
        logo: 'https://images.kiwi.com/airlines/64/EK.png',
        carrierFirstLeg: { name: 'Air Arabia', code: 'G9', logo: 'https://images.kiwi.com/airlines/64/G9.png', flightNumber: 'G9 498' },
        stops: ['SHJ', 'DXB'],
        outDepartTime: '04:10',
        outArrivalTime: '14:20',
        outDuration: isNorthAmerica ? 1340 : 850,
        inDepartTime: '16:45',
        inArrivalTime: '03:15',
        inDuration: isNorthAmerica ? 1290 : 820,
        aircraft: 'Airbus A380-800',
        baseUSD: isNorthAmerica ? 990 : 720,
        co2: 0
      }
    ];
  }

  // ==========================================
  // CASE 6: ALL OTHER GLOBAL PAIRS (e.g. JFK -> LHR, LHR -> KEF, SYD -> SIN, etc.)
  // ==========================================
  else {
    const isDirectAvailable = ['JFK-LHR', 'LHR-JFK', 'SIN-HND', 'HND-SIN', 'LHR-DXB', 'DXB-LHR', 'LHR-KEF', 'JFK-KEF', 'DEL-LHR'].includes(`${origin.code}-${destination.code}`);

    routeOptions = [
      {
        airline: destination.country === 'Iceland' ? 'Icelandair' : (destination.country === 'United States' ? 'Delta Air Lines' : (destination.country === 'United Kingdom' ? 'British Airways' : 'Singapore Airlines')),
        airlineCode: destination.country === 'Iceland' ? 'FI' : (destination.country === 'United States' ? 'DL' : (destination.country === 'United Kingdom' ? 'BA' : 'SQ')),
        logo: destination.country === 'Iceland' ? 'https://images.kiwi.com/airlines/64/FI.png' : (destination.country === 'United States' ? 'https://images.kiwi.com/airlines/64/DL.png' : 'https://images.kiwi.com/airlines/64/BA.png'),
        stops: isDirectAvailable ? [] : ['DXB'],
        outDepartTime: '11:20',
        outArrivalTime: '19:45',
        outDuration: isDirectAvailable ? 420 : 780,
        inDepartTime: '14:30',
        inArrivalTime: '22:15',
        inDuration: isDirectAvailable ? 430 : 790,
        aircraft: 'Boeing 787-9 Dreamliner',
        baseUSD: 540,
        co2: 22
      },
      {
        airline: 'Emirates',
        airlineCode: 'EK',
        logo: 'https://images.kiwi.com/airlines/64/EK.png',
        stops: isDirectAvailable ? [] : ['DXB'],
        outDepartTime: '18:30',
        outArrivalTime: '08:15',
        outDuration: 825,
        inDepartTime: '09:45',
        inArrivalTime: '20:30',
        inDuration: 810,
        aircraft: 'Airbus A380-800',
        baseUSD: 610,
        co2: 0
      },
      {
        airline: 'Qatar Airways',
        airlineCode: 'QR',
        logo: 'https://images.kiwi.com/airlines/64/QR.png',
        stops: ['DOH'],
        outDepartTime: '21:15',
        outArrivalTime: '11:45',
        outDuration: 870,
        inDepartTime: '18:20',
        inArrivalTime: '08:10',
        inDuration: 830,
        aircraft: 'Airbus A350-1000',
        baseUSD: 580,
        co2: 26
      }
    ];
  }

  // Construct comprehensive FlightOffer objects with accurate multi-carrier legs
  routeOptions.forEach((t, index) => {
    const pricePerPerson = Math.round(t.baseUSD * basePriceMultiplier);
    const mainCarrierFlightNum = `${t.airlineCode} ${Math.floor(100 + index * 43)}`;

    const outSegments: FlightSegment[] = [];

    if (t.stops.length === 0) {
      outSegments.push({
        flightNumber: mainCarrierFlightNum,
        airline: t.airline,
        airlineCode: t.airlineCode,
        airlineLogo: t.logo,
        aircraft: t.aircraft,
        originCode: origin.code,
        originCity: origin.city,
        originAirport: origin.name,
        destinationCode: destination.code,
        destinationCity: destination.city,
        destinationAirport: destination.name,
        departureTime: t.outDepartTime,
        arrivalTime: t.outArrivalTime,
        durationMinutes: t.outDuration
      });
    } else {
      const layover = t.stops[0];
      const leg1Dur = Math.round(t.outDuration * 0.35);
      const layoverDur = 140; // 2h 20m layover
      const leg2Dur = t.outDuration - leg1Dur - layoverDur;

      const firstLegCarrier = t.carrierFirstLeg || {
        name: isRegionalIndia ? 'IndiGo' : t.airline,
        code: isRegionalIndia ? '6E' : t.airlineCode,
        logo: isRegionalIndia ? 'https://images.kiwi.com/airlines/64/6E.png' : t.logo,
        flightNumber: `${isRegionalIndia ? '6E' : t.airlineCode} ${200 + index * 12}`
      };

      // Leg 1: From origin to layover hub
      outSegments.push({
        flightNumber: firstLegCarrier.flightNumber,
        airline: firstLegCarrier.name,
        airlineCode: firstLegCarrier.code,
        airlineLogo: firstLegCarrier.logo,
        aircraft: 'Airbus A320neo',
        originCode: origin.code,
        originCity: origin.city,
        originAirport: origin.name,
        destinationCode: layover,
        destinationCity: `${layover} Hub`,
        destinationAirport: `${layover} International Airport`,
        departureTime: t.outDepartTime,
        arrivalTime: '11:15',
        durationMinutes: leg1Dur,
        layoverDurationMinutes: layoverDur,
        layoverCity: `${layover} Hub`,
        layoverAirportCode: layover
      });

      // Leg 2: From layover hub to final destination
      outSegments.push({
        flightNumber: `${t.airlineCode} ${500 + index * 18}`,
        airline: t.airline,
        airlineCode: t.airlineCode,
        airlineLogo: t.logo,
        aircraft: t.aircraft,
        originCode: layover,
        originCity: `${layover} Hub`,
        originAirport: `${layover} International Airport`,
        destinationCode: destination.code,
        destinationCity: destination.city,
        destinationAirport: destination.name,
        departureTime: '13:35',
        arrivalTime: t.outArrivalTime,
        durationMinutes: leg2Dur
      });
    }

    const providers = [
      { name: 'Trip.com', logo: '🌐', priceUSD: pricePerPerson, rating: 4.8, reviewCount: 2100 },
      { name: `${t.airline} Direct`, logo: '✈️', priceUSD: pricePerPerson + 22, rating: 4.9, reviewCount: 8400, isDirectAirline: true },
      { name: 'Expedia', logo: '🏨', priceUSD: pricePerPerson + 14, rating: 4.6, reviewCount: 3900 },
      { name: 'Booking.com', logo: '🧳', priceUSD: pricePerPerson + 18, rating: 4.7, reviewCount: 5600 },
      { name: 'Gotogate', logo: '🎫', priceUSD: pricePerPerson - 8, rating: 4.1, reviewCount: 1100 }
    ];

    offers.push({
      id: `fl-${origin.code}-${destination.code}-${index}`,
      priceUSD: pricePerPerson,
      cabinClass: cabinClass,
      co2ReductionPercent: t.co2 > 0 ? t.co2 : undefined,
      baggage: {
        personalItem: true,
        carryOn: true,
        checkedBagCount: cabinClass === 'first' || cabinClass === 'business' ? 2 : 1
      },
      providers: providers.sort((a, b) => a.priceUSD - b.priceUSD),
      outbound: {
        id: `out-${index}`,
        departureTime: t.outDepartTime,
        arrivalTime: t.outArrivalTime,
        originCode: origin.code,
        destinationCode: destination.code,
        originCity: origin.city,
        destinationCity: destination.city,
        durationMinutes: t.outDuration,
        stopsCount: t.stops.length,
        stops: t.stops,
        airline: t.airline,
        airlineCode: t.airlineCode,
        airlineLogo: t.logo,
        flightNumber: mainCarrierFlightNum,
        overnight: t.outDuration > 600,
        segments: outSegments
      },
      inbound: returnDate ? {
        id: `in-${index}`,
        departureTime: t.inDepartTime,
        arrivalTime: t.inArrivalTime,
        originCode: destination.code,
        destinationCode: origin.code,
        originCity: destination.city,
        destinationCity: origin.city,
        durationMinutes: t.inDuration,
        stopsCount: t.stops.length,
        stops: t.stops,
        airline: t.airline,
        airlineCode: t.airlineCode,
        airlineLogo: t.logo,
        flightNumber: `${t.airlineCode} ${Math.floor(200 + index * 43)}`,
        overnight: t.inDuration > 600,
        segments: []
      } : undefined
    });
  });

  // Calculate Best, Cheapest, Fastest
  const minPrice = Math.min(...offers.map(o => o.priceUSD));
  const minDur = Math.min(...offers.map(o => o.outbound.durationMinutes));

  offers.forEach(o => {
    if (o.priceUSD === minPrice) o.cheapest = true;
    if (o.outbound.durationMinutes === minDur) o.fastest = true;
  });

  let bestOffer = offers[0];
  let bestScore = -Infinity;
  offers.forEach(o => {
    const priceScore = 1 - (o.priceUSD - minPrice) / (minPrice || 1);
    const durationScore = 1 - (o.outbound.durationMinutes - minDur) / (minDur || 1);
    const score = priceScore * 0.55 + durationScore * 0.45;
    if (score > bestScore) {
      bestScore = score;
      bestOffer = o;
    }
  });
  bestOffer.best = true;

  return offers;
}
