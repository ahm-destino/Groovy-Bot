"""
Location services for geospatial queries
"""
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.models import Event
from datetime import datetime


async def get_events_near_location(
    lat: float,
    lng: float,
    db: AsyncSession,
    radius_miles: float = 100,
    limit: int = 10
) -> list:
    """
    Get events within radius of a location using PostGIS
    
    Args:
        lat: Latitude
        lng: Longitude
        radius_miles: Search radius in miles (default 20)
        db: Database session
        limit: Max number of results
    
    Returns:
        List of events with distance
    """
    # Convert miles to meters (PostGIS uses meters)
    radius_meters = radius_miles * 1609.34
    
    # PostGIS query to find events within radius
    # ST_DWithin uses spatial index for fast queries
    query = text("""
        SELECT 
            e.*,
            ST_Distance(
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                ST_SetSRID(ST_MakePoint(e.location_lng, e.location_lat), 4326)::geography
            ) / 1609.34 as distance_miles
        FROM events e
        WHERE 
            e.status = 'active'
            AND e.event_date > :now
            AND e.location_lat IS NOT NULL
            AND e.location_lng IS NOT NULL
            AND ST_DWithin(
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                ST_SetSRID(ST_MakePoint(e.location_lng, e.location_lat), 4326)::geography,
                :radius_meters
            )
        ORDER BY distance_miles ASC
        LIMIT :limit
    """)
    
    result = await db.execute(
        query,
        {
            'lat': lat,
            'lng': lng,
            'radius_meters': radius_meters,
            'now': datetime.now(),
            'limit': limit
        }
    )
    
    return result.fetchall()


async def geocode_location(location_name: str) -> Optional[Tuple[float, float]]:
    """
    Convert location name to coordinates
    Uses a simple mapping for Nigerian cities
    In production, use Google Maps Geocoding API
    
    Args:
        location_name: City or area name
    
    Returns:
        (latitude, longitude) or None
    """
    # Common Nigerian locations and all 36 states
    locations = {
        # Lagos areas
        'lagos': (6.5244, 3.3792), 'eko': (6.5244, 3.3792),
        'victoria island': (6.4281, 3.4219), 'vi': (6.4281, 3.4219),
        'lekki': (6.4474, 3.4700), 'ajah': (6.4698, 3.5852),
        'ikeja': (6.6018, 3.3515), 'surulere': (6.4969, 3.3590),
        'yaba': (6.5158, 3.3711), 'ikoyi': (6.4541, 3.4316),
        'festac': (6.4667, 3.2833),
        
        # 36 States & Capital
        'abuja': (9.0765, 7.3986), 'fct': (9.0765, 7.3986),
        'abia': (5.5320, 7.4860), 'umuahia': (5.5320, 7.4860), 'aba': (5.1066, 7.3667),
        'adamawa': (9.3265, 12.3984), 'yola': (9.2035, 12.4954),
        'akwa ibom': (5.0389, 7.9095), 'uyo': (5.0389, 7.9095),
        'anambra': (6.2209, 6.9370), 'awka': (6.2209, 6.9370), 'onitsha': (6.1498, 6.7860),
        'bauchi': (10.3158, 9.8442),
        'bayelsa': (4.7719, 6.0699), 'yenagoa': (4.9267, 6.2676),
        'benue': (7.3369, 8.7404), 'makurdi': (7.7322, 8.5391),
        'borno': (11.8333, 13.1500), 'maiduguri': (11.8333, 13.1500),
        'cross river': (5.8702, 8.5988), 'calabar': (4.9517, 8.3417),
        'delta': (5.7040, 5.9339), 'asaba': (6.2059, 6.6953), 'warri': (5.5160, 5.7500),
        'ebonyi': (6.2649, 8.0137), 'abakaliki': (6.3249, 8.1137),
        'edo': (6.6342, 5.9304), 'benin': (6.3350, 5.6037),
        'ekiti': (7.7190, 5.3110), 'ado ekiti': (7.6212, 5.2212),
        'enugu': (6.5244, 7.5106),
        'gombe': (10.2897, 11.1711),
        'imo': (5.5720, 7.0588), 'owerri': (5.4833, 7.0333),
        'jigawa': (12.2216, 9.5616), 'dutse': (11.7594, 9.3392),
        'kaduna': (10.5105, 7.4165),
        'kano': (12.0022, 8.5919),
        'katsina': (12.9818, 7.6018),
        'kebbi': (12.4468, 4.1979), 'birnin kebbi': (12.4539, 4.1975),
        'kogi': (7.7337, 6.7330), 'lokoja': (7.8023, 6.7333),
        'kwara': (8.9669, 4.3874), 'ilorin': (8.4966, 4.5421),
        'nasarawa': (8.5475, 8.5200), 'lafia': (8.4833, 8.5167),
        'niger': (9.9309, 5.5976), 'minna': (9.6102, 5.5496),
        'ogun': (7.1475, 3.3619), 'abeokuta': (7.1475, 3.3619),
        'ondo': (7.1000, 5.0500), 'akure': (7.2508, 5.2109),
        'osun': (7.5629, 4.5200), 'osogbo': (7.7827, 4.5624),
        'oyo': (8.1574, 3.6147), 'ibadan': (7.3775, 3.9470),
        'plateau': (9.2182, 9.5173), 'jos': (9.8965, 8.8583),
        'rivers': (4.8156, 7.0498), 'port harcourt': (4.8156, 7.0498), 'ph': (4.8156, 7.0498),
        'sokoto': (13.0059, 5.2476),
        'taraba': (8.8937, 11.3596), 'jalingo': (8.8937, 11.3596),
        'yobe': (12.0000, 11.5000), 'damaturu': (11.7470, 11.9608),
        'zamfara': (12.1628, 6.6601), 'gusau': (12.1628, 6.6601)
    }
    
    location_lower = location_name.lower().strip()
    
    # Direct match
    if location_lower in locations:
        return locations[location_lower]
    
    # Partial match
    for key, coords in locations.items():
        if key in location_lower or location_lower in key:
            return coords
    
    return None


async def get_user_location_from_phone(phone: str, db: AsyncSession) -> Optional[Tuple[float, float]]:
    """
    Get user's saved location preference
    
    Args:
        phone: User's phone number
        db: Database session
    
    Returns:
        (latitude, longitude) or None
    """
    from app.models import User
    from sqlalchemy import select, func
    from geoalchemy2 import Geometry
    
    # Extract coordinates by casting geography to geometry for ST_X and ST_Y
    query = select(
        func.ST_Y(User.location_preference.cast(Geometry)).label('lat'),
        func.ST_X(User.location_preference.cast(Geometry)).label('lng')
    ).where(User.phone == phone)
    
    result = await db.execute(query)
    row = result.first()
    
    if row and row.lat is not None:
        return (row.lat, row.lng)
    
    return None


async def geocode_address(address: str) -> tuple:
    """
    Mock geocoder for Nigerian locations.
    In production, this would use Google Maps or Mapbox API.
    """
    addr = address.lower()
    
    # Simple lookup - use the core mapping so they're in sync
    cities = {
        "lagos": (6.5244, 3.3792), "eko": (6.5244, 3.3792),
        "abuja": (9.0765, 7.3986), "fct": (9.0765, 7.3986),
        "lekki": (6.4698, 3.5852),
        "vi": (6.4253, 3.4000), "victoria island": (6.4253, 3.4000),
        "ikeja": (6.6018, 3.3515),
        "ibadan": (7.3775, 3.9470),
        "port harcourt": (4.8156, 7.0498), "ph": (4.8156, 7.0498),
        "surulere": (6.5059, 3.3491),
        "kano": (12.0022, 8.5919),
        "enugu": (6.5244, 7.5106),
        "kaduna": (10.5105, 7.4165),
        "owerri": (5.4833, 7.0333),
        "benin": (6.3350, 5.6037),
        "jos": (9.8965, 8.8583)
    }
    
    for city, coords in cities.items():
        if city in addr:
            return coords
            
    # Default to Lagos for demo if unrecognized
    return (6.5244, 3.3792)


def format_distance(miles: float) -> str:
    """Format distance for display"""
    if miles < 1:
        return f"{miles * 5280:.0f} ft away"
    elif miles < 10:
        return f"{miles:.1f} miles away"
    else:
        return f"{miles:.0f} miles away"
