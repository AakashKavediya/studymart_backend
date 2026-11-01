# app/routers/follower.py
from fastapi import APIRouter, Depends, status
from app.utils.user import get_current_user
from app.services.follow_service import (
    follow_user_service,
    unfollow_user_service,
    get_followers_service,
    get_following_service,
)

router = APIRouter(prefix="/users", tags=["Profile"])


@router.post("/{user_id}/follow", status_code=status.HTTP_200_OK)
async def follow_user(
    user_id: str,
    current_user=Depends(get_current_user),
):
    return await follow_user_service(user_id, current_user)


@router.delete("/{user_id}/follow", status_code=status.HTTP_200_OK)
async def unfollow_user(
    user_id: str,
    current_user=Depends(get_current_user),
):
    return await unfollow_user_service(user_id, current_user)


@router.get("/{user_id}/followers", status_code=status.HTTP_200_OK)
async def list_followers(
    user_id: str,
    current_user=Depends(get_current_user),
):
    viewer_id = str(current_user.get("_id") or current_user.get("id") or "")
    return await get_followers_service(user_id, viewer_id)


@router.get("/{user_id}/following", status_code=status.HTTP_200_OK)
async def list_following(
    user_id: str,
    current_user=Depends(get_current_user),
):
    viewer_id = str(current_user.get("_id") or current_user.get("id") or "")
    return await get_following_service(user_id, viewer_id)  