from pymongo import MongoClient, DESCENDING, TEXT
from datetime import datetime
from bson import ObjectId
import psycopg2
from db_connection import get_connection, release_connection
from dotenv import load_dotenv
import os

load_dotenv()

client     = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
db         = client[os.getenv('MONGO_DATABASE', 'reservations_system')]
reviews_col = db['reviews']

reviews_col.create_index([('restaurant_id', 1)])
reviews_col.create_index([('customer_id',   1)])
reviews_col.create_index([('created_at', DESCENDING)])
reviews_col.create_index([('title', TEXT), ('body', TEXT)])

print("MongoDB connected — reviews collection ready.")


def submit_review(
    customer_id: int,
    restaurant_id: int,
    reservation_id: int,
    rating: float,
    title: str,
    body: str,
    tags: list = None,
    food_rating: float = None,
    service_rating: float = None,
    ambiance_rating: float = None
) -> str:
    """
    Save the review body in MongoDB and the overall rating in PostgreSQL.
    """
    if not (1.0 <= rating <= 5.0):
        raise ValueError(f"rating must be between 1.0 and 5.0, got {rating}")
    if not title or not body:
        raise ValueError("title and body are required.")

    mongo_doc = {
        'restaurant_id': restaurant_id,
        'customer_id': customer_id,
        'reservation_id': reservation_id,
        'title': title,
        'body': body,
        'tags': tags or [],
        'food_rating': food_rating,
        'service_rating': service_rating,
        'ambiance_rating': ambiance_rating,
        'helpful_votes': 0,
        'owner_response': None,
        'photos': [],
        'created_at': datetime.utcnow()
    }
    result = reviews_col.insert_one(mongo_doc)
    mongo_id = str(result.inserted_id)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reviews
                (customer_id, restaurant_id, reservation_id, rating, mongo_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING review_id
            """,
            (customer_id, restaurant_id, reservation_id, rating, mongo_id)
        )
        review_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Review #{review_id} saved (SQL) | MongoDB: {mongo_id}")
        return mongo_id

    except psycopg2.Error as e:
        conn.rollback()
        reviews_col.delete_one({'_id': ObjectId(mongo_id)})
        print(f"SQL insert failed, MongoDB document removed: {e}")
        raise
    finally:
        release_connection(conn)


def get_review_full(mongo_id: str) -> dict:
    """Return one full review document from MongoDB."""
    return reviews_col.find_one({'_id': ObjectId(mongo_id)})


def get_restaurant_reviews(restaurant_id: int, limit: int = 20,
                            sort_by: str = 'newest') -> list:
    """
    Return restaurant reviews sorted by the requested mode.
    """
    sort_map = {
        'newest':  [('created_at',   DESCENDING)],
        'helpful': [('helpful_votes', DESCENDING)],
        'highest': [('food_rating',   DESCENDING)],
        'lowest':  [('food_rating',   1)]
    }
    sort_order = sort_map.get(sort_by, sort_map['newest'])
    cursor = reviews_col.find({'restaurant_id': restaurant_id}).sort(sort_order).limit(limit)
    return list(cursor)


def search_reviews(restaurant_id: int, keyword: str) -> list:
    """Search review titles and bodies with MongoDB text search."""
    return list(reviews_col.find({
        'restaurant_id': restaurant_id,
        '$text': {'$search': keyword}
    }, {'score': {'$meta': 'textScore'}}).sort([('score', {'$meta': 'textScore'})]))


def add_owner_response(mongo_id: str, response_text: str):
    """Attach an owner response to a review."""
    reviews_col.update_one(
        {'_id': ObjectId(mongo_id)},
        {'$set': {'owner_response': response_text,
                  'responded_at':  datetime.utcnow()}}
    )
    print(f"Owner response added to review {mongo_id}")


def upvote_review(mongo_id: str):
    """Increment the helpful vote count for a review."""
    reviews_col.update_one(
        {'_id': ObjectId(mongo_id)},
        {'$inc': {'helpful_votes': 1}}
    )


def get_review_stats(restaurant_id: int) -> dict:
    """
    Return aggregated review statistics for one restaurant.
    """
    pipeline = [
        {'$match': {'restaurant_id': restaurant_id}},
        {'$group': {
            '_id':              '$restaurant_id',
            'total_reviews':    {'$sum': 1},
            'avg_food':         {'$avg': '$food_rating'},
            'avg_service':      {'$avg': '$service_rating'},
            'avg_ambiance':     {'$avg': '$ambiance_rating'},
            'helpful_total':    {'$sum': '$helpful_votes'}
        }}
    ]
    results = list(reviews_col.aggregate(pipeline))
    return results[0] if results else {}
