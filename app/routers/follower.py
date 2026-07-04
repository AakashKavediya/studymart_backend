from fastapi import APIRouter, Depends, HTTPException, status
from app.utils.user import get_current_user
from app.services.follow_service import follow_user_service, unfollow_user_service

router = APIRouter(prefix="/users", tags=["Profile"])


@router.post("/{user_id}/follow", status_code=status.HTTP_200_OK)
async def follow_user(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """
    Follow a user.
    """
    return await follow_user_service(user_id, current_user)


@router.delete("/{user_id}/follow", status_code=status.HTTP_200_OK)
async def unfollow_user(
    user_id: str,
    current_user = Depends(get_current_user)
):
    """
    Unfollow a user.
    """
    return await unfollow_user_service(user_id, current_user)