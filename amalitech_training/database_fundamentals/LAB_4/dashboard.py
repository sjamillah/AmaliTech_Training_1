from db_connection import get_connection, release_connection
from redis_caching import get_available_tables_cached
from reviews import get_review_stats
from datetime import datetime


def get_restaurant_rankings(city: str) -> list:
    """
    Return city restaurants ranked by average review score.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                r.restaurant_id,
                r.name,
                r.cuisine_type,
                r.city,
                COUNT(rv.review_id)          AS review_count,
                ROUND(AVG(rv.rating), 2)     AS avg_rating,
                RANK() OVER (
                    PARTITION BY r.city
                    ORDER BY AVG(rv.rating) DESC
                )                            AS city_rank
            FROM restaurants r
            LEFT JOIN reviews rv ON r.restaurant_id = rv.restaurant_id
            WHERE r.city = %s
            GROUP BY r.restaurant_id, r.name, r.cuisine_type, r.city
            HAVING COUNT(rv.review_id) >= 1
            ORDER BY city_rank
            """,
            (city,)
        )
        rows = cursor.fetchall()
        return [
            {
                'restaurant_id': r[0], 'name': r[1],
                'cuisine':       r[2], 'city': r[3],
                'review_count':  r[4], 'avg_rating': float(r[5]) if r[5] else None,
                'city_rank':     r[6]
            }
            for r in rows
        ]
    finally:
        release_connection(conn)


def get_restaurant_details(restaurant_id: int) -> dict:
    """
    Return one restaurant's core profile including JSON fields.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                restaurant_id, name, city, address,
                cuisine_type, phone,
                operating_hours, menu
            FROM restaurants
            WHERE restaurant_id = %s
            """,
            (restaurant_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            'restaurant_id':   row[0], 'name': row[1], 'city': row[2],
            'address':         row[3], 'cuisine_type': row[4], 'phone': row[5],
            'operating_hours': row[6], 'menu': row[7]
        }
    finally:
        release_connection(conn)


def find_nearby_restaurants(lat: float, lon: float, radius_km: float = 5) -> list:
    """
    Return restaurants within the given radius of a geo point.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                restaurant_id,
                name,
                city,
                cuisine_type,
                ROUND(
                    ST_Distance(
                        location,
                        ST_MakePoint(%s, %s)::GEOGRAPHY
                    ) / 1000.0, 2
                ) AS distance_km
            FROM restaurants
            WHERE ST_DWithin(
                location,
                ST_MakePoint(%s, %s)::GEOGRAPHY,
                %s
            )
            ORDER BY distance_km ASC
            """,
            (lon, lat, lon, lat, radius_km * 1000)
        )
        rows = cursor.fetchall()
        return [
            {'restaurant_id': r[0], 'name': r[1],
             'city': r[2], 'cuisine': r[3], 'distance_km': float(r[4])}
            for r in rows
        ]
    finally:
        release_connection(conn)


def get_full_dashboard(city: str, party_size: int,
                       starts_at: datetime, ends_at: datetime) -> dict:
    """
    Build dashboard data with rankings, availability, and review stats.
    """
    if ends_at <= starts_at:
        raise ValueError("ends_at must be after starts_at")

    ranked = get_restaurant_rankings(city)

    result = {'city': city, 'restaurants': []}

    for r in ranked:
        rid = r['restaurant_id']

        available_tables = get_available_tables_cached(
            rid, party_size, starts_at, ends_at
        )

        mongo_stats = get_review_stats(rid)

        result['restaurants'].append({
            **r,
            'available_tables': len(available_tables),
            'tables':           available_tables[:3],
            'mongo_avg_food':    round(mongo_stats.get('avg_food', 0) or 0, 2),
            'mongo_avg_service': round(mongo_stats.get('avg_service', 0) or 0, 2),
        })

    return result
