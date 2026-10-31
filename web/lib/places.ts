export interface Place {
  /** What goes into the destination field. */
  city: string;
  /** Neighbourhood, when the suggestion is an area inside the city. */
  area?: string;
  /** Shown next to the name, e.g. the state. */
  region: string;
  /** Extra spellings that should also match. */
  aliases?: string[];
}

const c = (city: string, region: string, aliases: string[] = []): Place => ({ city, region, aliases });
const a = (area: string, city: string, region: string): Place => ({ city, area, region });

/** Popular destinations. A fixed list keeps suggestions instant and free of any third-party service. */
export const PLACES: Place[] = [
  c("Bengaluru", "Karnataka", ["bangalore", "blr"]),
  a("HSR Layout", "Bengaluru", "Karnataka"),
  a("Koramangala", "Bengaluru", "Karnataka"),
  a("Indiranagar", "Bengaluru", "Karnataka"),
  a("Whitefield", "Bengaluru", "Karnataka"),
  a("MG Road", "Bengaluru", "Karnataka"),
  c("Mysuru", "Karnataka", ["mysore"]),
  c("Mangaluru", "Karnataka", ["mangalore"]),
  c("Hampi", "Karnataka"),
  c("Coorg", "Karnataka", ["madikeri", "kodagu"]),
  c("Goa", "Goa"),
  a("Calangute", "Goa", "Goa"),
  a("Baga", "Goa", "Goa"),
  a("Panaji", "Goa", "Goa"),
  a("Anjuna", "Goa", "Goa"),
  c("Mumbai", "Maharashtra", ["bombay"]),
  a("Bandra", "Mumbai", "Maharashtra"),
  a("Andheri", "Mumbai", "Maharashtra"),
  c("Pune", "Maharashtra"),
  c("Nagpur", "Maharashtra"),
  c("Delhi", "Delhi", ["new delhi", "ncr"]),
  a("Connaught Place", "Delhi", "Delhi"),
  a("Aerocity", "Delhi", "Delhi"),
  c("Gurugram", "Haryana", ["gurgaon"]),
  c("Noida", "Uttar Pradesh"),
  c("Jaipur", "Rajasthan"),
  c("Udaipur", "Rajasthan"),
  c("Jodhpur", "Rajasthan"),
  c("Jaisalmer", "Rajasthan"),
  c("Chennai", "Tamil Nadu", ["madras"]),
  c("Coimbatore", "Tamil Nadu"),
  c("Madurai", "Tamil Nadu"),
  c("Ooty", "Tamil Nadu", ["udhagamandalam"]),
  c("Pondicherry", "Puducherry", ["puducherry"]),
  c("Hyderabad", "Telangana"),
  c("Visakhapatnam", "Andhra Pradesh", ["vizag"]),
  c("Tirupati", "Andhra Pradesh"),
  c("Kochi", "Kerala", ["cochin"]),
  c("Munnar", "Kerala"),
  c("Alappuzha", "Kerala", ["alleppey"]),
  c("Thiruvananthapuram", "Kerala", ["trivandrum"]),
  c("Kolkata", "West Bengal", ["calcutta"]),
  c("Darjeeling", "West Bengal"),
  c("Ahmedabad", "Gujarat"),
  c("Surat", "Gujarat"),
  c("Lucknow", "Uttar Pradesh"),
  c("Varanasi", "Uttar Pradesh", ["banaras", "benares"]),
  c("Agra", "Uttar Pradesh"),
  c("Amritsar", "Punjab"),
  c("Chandigarh", "Chandigarh"),
  c("Shimla", "Himachal Pradesh"),
  c("Manali", "Himachal Pradesh"),
  c("Dharamshala", "Himachal Pradesh"),
  c("Rishikesh", "Uttarakhand"),
  c("Dehradun", "Uttarakhand"),
  c("Srinagar", "Jammu and Kashmir"),
  c("Leh", "Ladakh"),
  c("Gangtok", "Sikkim"),
  c("Guwahati", "Assam"),
  c("Bhubaneswar", "Odisha"),
  c("Puri", "Odisha"),
  c("Indore", "Madhya Pradesh"),
  c("Bhopal", "Madhya Pradesh"),
  c("Port Blair", "Andaman and Nicobar", ["andaman"]),
];

const norm = (s: string) => s.toLowerCase().normalize("NFKD").replace(/[^a-z0-9 ]/g, "").trim();

export function placeLabel(p: Place): string {
  return p.area ? `${p.area}, ${p.city}` : p.city;
}

/** Up to `limit` matches: names that start with the query first, then names that contain it. */
export function searchPlaces(query: string, limit = 6): Place[] {
  const q = norm(query);
  if (q.length < 1) return [];
  const scored: Array<[number, Place]> = [];
  for (const p of PLACES) {
    const names = [p.area ?? p.city, p.city, ...(p.aliases ?? [])].map(norm);
    const label = norm(placeLabel(p));
    let score = -1;
    if (names.some((n) => n.startsWith(q))) score = 0;
    else if (names.some((n) => n.split(" ").some((w) => w.startsWith(q)))) score = 1;
    else if (label.includes(q)) score = 2;
    if (score >= 0) scored.push([score + (p.area ? 0.5 : 0), p]);
  }
  return scored.sort((x, y) => x[0] - y[0]).slice(0, limit).map(([, p]) => p);
}