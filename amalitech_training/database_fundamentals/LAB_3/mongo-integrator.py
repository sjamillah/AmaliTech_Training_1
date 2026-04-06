from pymongo import MongoClient, DESCENDING, TEXT
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "learning_platform")
MONGO_THREADS_COLLECTION = os.getenv("MONGO_THREADS_COLLECTION", "forum_threads")

client = MongoClient(MONGO_URI)

db = client[MONGO_DATABASE]
threads_collection = db[MONGO_THREADS_COLLECTION]

threads_collection.create_index([("course_id", 1)])
threads_collection.create_index([("author_id", 1)])
threads_collection.create_index([("created_at", DESCENDING)])
threads_collection.create_index([("title", TEXT), ("content", TEXT)])

print("MongoDB connected and indexes ensured.")


def create_thread(
    course_id: int,
    author_id: int,
    author_name: str,
    title: str,
    content: str,
    tags: list = None,
) -> str:
    """
    Create a new forum thread for a course and return its document ID.
    """
    now = datetime.utcnow()

    thread_doc = {
        "course_id": course_id,
        "title": title,
        "content": content,
        "author_id": author_id,
        "author_name": author_name,
        "created_at": now,
        "updated_at": now,
        "upvotes": 0,
        "tags": tags or [],
        "is_pinned": False,
        "replies": [],
    }

    result = threads_collection.insert_one(thread_doc)
    thread_id = str(result.inserted_id)
    print(f"Forum thread created: {thread_id} | '{title}'")
    return thread_id


def add_reply(thread_id: str, author_id: int, author_name: str, content: str) -> str:
    """
    Add a reply to a thread and return the new reply ID.
    """
    reply_id = str(ObjectId())

    reply_doc = {
        "reply_id": reply_id,
        "author_id": author_id,
        "author_name": author_name,
        "content": content,
        "created_at": datetime.utcnow(),
        "upvotes": 0,
    }

    result = threads_collection.update_one(
        {"_id": ObjectId(thread_id)},
        {"$push": {"replies": reply_doc}, "$set": {"updated_at": datetime.utcnow()}},
    )

    if result.modified_count == 0:
        print(f"WARNING: Thread {thread_id} not found!")
        return None

    print(f"Reply added to thread {thread_id}")
    return reply_id


def get_course_threads(
    course_id: int, limit: int = 20, skip: int = 0, pinned_first: bool = True
) -> list:
    """
    Return course threads with optional pagination and pinned-first sorting.
    """
    sort_order = []
    if pinned_first:
        sort_order.append(("is_pinned", DESCENDING))
    sort_order.append(("created_at", DESCENDING))

    projection = {"replies": 0}

    cursor = (
        threads_collection.find({"course_id": course_id}, projection)
        .sort(sort_order)
        .skip(skip)
        .limit(limit)
    )

    threads = list(cursor)
    print(f"Found {len(threads)} threads for course {course_id}")
    return threads


def get_thread_with_replies(thread_id: str) -> dict:
    """
    Return one thread with all embedded replies, or None if not found.
    """
    thread = threads_collection.find_one({"_id": ObjectId(thread_id)})
    if thread:
        print(
            f"Retrieved thread '{thread.get('title')}' with "
            f"{len(thread.get('replies', []))} replies"
        )
    return thread


def search_threads(course_id: int, keyword: str, limit: int = 10) -> list:
    """
    Search thread titles and content for a keyword within one course.
    """
    cursor = (
        threads_collection.find(
            {"course_id": course_id, "$text": {"$search": keyword}},
            {"replies": 0, "score": {"$meta": "textScore"}},
        )
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )

    results = list(cursor)
    print(f"Search '{keyword}' in course {course_id}: {len(results)} results")
    return results


def upvote_thread(thread_id: str) -> bool:
    """
    Increment the thread upvote count by one.
    """
    result = threads_collection.update_one(
        {"_id": ObjectId(thread_id)}, {"$inc": {"upvotes": 1}}
    )
    return result.modified_count > 0


def get_thread_count_per_course(course_ids: list) -> dict:
    """
    Return thread counts grouped by course ID.
    """
    pipeline = [
        {"$match": {"course_id": {"$in": course_ids}}},
        {"$group": {"_id": "$course_id", "count": {"$sum": 1}}},
    ]
    result = threads_collection.aggregate(pipeline)
    return {doc["_id"]: doc["count"] for doc in result}
