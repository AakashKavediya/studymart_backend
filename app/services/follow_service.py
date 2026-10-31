# app/services/follow_service.py
"""
Follow / Unfollow services + list followers / following.
Auto-detects the follow collection name ("follows" or "user-follow").
"""

from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.mongodb.connect import connectdb

db = connectdb()
profile_collection = db["user-profile"]
signup_collection = db["signup"]

# ------------------------------------------------------------------
# Auto-detect the follow collection
# ------------------------------------------------------------------
def _resolve_follow_collection():
    existing = set(db.list_collection_names())
    for name in ("follows", "user-follow", "user_follow", "follow"):
        if name in existing:
            return db[name]
    # Fall back to "follows" (creates on first write)
    return db["follows"]

follow_collection = _resolve_follow_collection()
print(f"ℹ️  Using follow collection: {follow_collection.name}")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _oid(value) -> ObjectId:
    if not ObjectId.is_valid(str(value)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    return ObjectId(str(value))


async def _assert_user_exists(user_id: str):
    user = await run_in_threadpool(
        signup_collection.find_one, {"_id": _oid(user_id)}
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def _normalize(doc: dict) -> dict:
    """
    Map whatever field names exist in the collection to our canonical
    { follower_id, following_id } shape.
    """
    follower = (
        doc.get("follower_id")
        or doc.get("follower")
        or doc.get("from_user")
        or doc.get("from")
    )
    following = (
        doc.get("following_id")
        or doc.get("following")
        or doc.get("to_user")
        or doc.get("to")
    )
    return {"follower_id": follower, "following_id": following}


# ==========================================================
# FOLLOW
# ==========================================================
async def follow_user_service(target_user_id: str, current_user: dict):
    follower_id = _oid(current_user.get("_id") or current_user.get("id"))
    following_id = _oid(target_user_id)

    if follower_id == following_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself",
        )

    await _assert_user_exists(target_user_id)

    # Check existing — try multiple field name variants
    existing = await run_in_threadpool(
        follow_collection.find_one,
        {
            "$or": [
                {"follower_id": follower_id, "following_id": following_id},
                {"follower": follower_id, "following": following_id},
            ]
        },
    )
    if existing:
        return {
            "status": "ok",
            "message": "Already following",
            "data": {"following": True},
        }

    # Insert with canonical field names. If your code elsewhere reads
    # "follower"/"following", change the keys below.
    await run_in_threadpool(
        follow_collection.insert_one,
        {
            "follower_id": follower_id,
            "following_id": following_id,
            "created_at": datetime.utcnow(),
        },
    )

    # Update cached counters (best-effort)
    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": follower_id},
        {"$inc": {"following_count": 1}},
    )
    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": following_id},
        {"$inc": {"followers_count": 1}},
    )

    return {
        "status": "ok",
        "message": "Followed successfully",
        "data": {"following": True},
    }


# ==========================================================
# UNFOLLOW
# ==========================================================
async def unfollow_user_service(target_user_id: str, current_user: dict):
    follower_id = _oid(current_user.get("_id") or current_user.get("id"))
    following_id = _oid(target_user_id)

    result = await run_in_threadpool(
        follow_collection.delete_one,
        {
            "$or": [
                {"follower_id": follower_id, "following_id": following_id},
                {"follower": follower_id, "following": following_id},
            ]
        },
    )

    if result.deleted_count == 0:
        return {
            "status": "ok",
            "message": "Not following",
            "data": {"following": False},
        }

    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": follower_id, "following_count": {"$gt": 0}},
        {"$inc": {"following_count": -1}},
    )
    await run_in_threadpool(
        profile_collection.update_one,
        {"_id": following_id, "followers_count": {"$gt": 0}},
        {"$inc": {"followers_count": -1}},
    )

    return {
        "status": "ok",
        "message": "Unfollowed successfully",
        "data": {"following": False},
    }


# ==========================================================
# CHECK
# ==========================================================
async def check_follow_status(follower_id: str, following_id: str) -> bool:
    try:
        doc = await run_in_threadpool(
            follow_collection.find_one,
            {
                "$or": [
                    {
                        "follower_id": _oid(follower_id),
                        "following_id": _oid(following_id),
                    },
                    {
                        "follower": _oid(follower_id),
                        "following": _oid(following_id),
                    },
                ]
            },
        )
        return doc is not None
    except HTTPException:
        return False


# ==========================================================
# HYDRATE
# ==========================================================
async def _hydrate_users(user_ids: list, viewer_id: str | None) -> list:
    if not user_ids:
        return []

    # Who is the viewer following?
    viewer_following: set[str] = set()
    if viewer_id and ObjectId.is_valid(str(viewer_id)):
        cursor = follow_collection.find(
            {
                "$or": [
                    {"follower_id": ObjectId(str(viewer_id))},
                    {"follower": ObjectId(str(viewer_id))},
                ]
            },
            {"following_id": 1, "following": 1},
        )

        def _collect():
            return [
                str(_normalize(d).get("following_id"))
                for d in cursor
                if _normalize(d).get("following_id")
            ]

        viewer_following = set(await run_in_threadpool(_collect))

    # Fetch profiles
    profiles = await run_in_threadpool(
        lambda: list(profile_collection.find({"_id": {"$in": user_ids}}))
    )
    profile_by_id = {str(p["_id"]): p for p in profiles}

    # Fetch signup fallback
    signups = await run_in_threadpool(
        lambda: list(
            signup_collection.find(
                {"_id": {"$in": user_ids}},
                {"name": 1, "email": 1, "campus": 1},
            )
        )
    )
    signup_by_id = {str(s["_id"]): s for s in signups}

    results = []
    for uid in user_ids:
        sid = str(uid)
        profile = profile_by_id.get(sid, {})
        signup = signup_by_id.get(sid, {})
        results.append(
            {
                "id": sid,
                "name": profile.get("name")
                or signup.get("name")
                or "Unknown",
                "campus": profile.get("campus") or signup.get("campus"),
                "profile_image": profile.get("profile_image"),
                "is_following": sid in viewer_following,
            }
        )
    return results


# ==========================================================
# LIST FOLLOWERS
# ==========================================================
async def get_followers_service(user_id: str, viewer_id: str | None = None):
    _oid(user_id)
    cursor = follow_collection.find(
        {
            "$or": [
                {"following_id": ObjectId(user_id)},
                {"following": ObjectId(user_id)},
            ]
        }
    )

    def _ids():
        return [
            _normalize(d).get("follower_id")
            for d in cursor
            if _normalize(d).get("follower_id")
        ]

    follower_ids = await run_in_threadpool(_ids)
    results = await _hydrate_users(follower_ids, viewer_id)

    return {
        "status": "ok",
        "results": results,
        "count": len(results),
    }


# ==========================================================
# LIST FOLLOWING
# ==========================================================
async def get_following_service(user_id: str, viewer_id: str | None = None):
    _oid(user_id)
    cursor = follow_collection.find(
        {
            "$or": [
                {"follower_id": ObjectId(user_id)},
                {"follower": ObjectId(user_id)},
            ]
        }
    )

    def _ids():
        return [
            _normalize(d).get("following_id")
            for d in cursor
            if _normalize(d).get("following_id")
        ]

    following_ids = await run_in_threadpool(_ids)
    results = await _hydrate_users(following_ids, viewer_id)

    return {
        "status": "ok",
        "results": results,
        "count": len(results),
    }