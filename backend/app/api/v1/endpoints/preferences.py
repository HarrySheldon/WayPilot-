from fastapi import APIRouter, Depends, HTTPException, status

from ....api.dependencies import get_current_user_id, get_preference_service
from ....schemas.trips import (
    UserPreferenceRequest,
    UserPreferenceResponse,
    user_preference_to_response,
)
from ....services.trips import PreferenceService, UserPreferenceInput

router = APIRouter()


@router.get("", response_model=UserPreferenceResponse)
def get_preferences(
    user_id: str = Depends(get_current_user_id),
    service: PreferenceService = Depends(get_preference_service),
) -> UserPreferenceResponse:
    preference = service.get_user_preference(user_id=user_id)
    if preference is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found")
    return user_preference_to_response(preference)


@router.put("", response_model=UserPreferenceResponse)
def upsert_preferences(
    request: UserPreferenceRequest,
    user_id: str = Depends(get_current_user_id),
    service: PreferenceService = Depends(get_preference_service),
) -> UserPreferenceResponse:
    preference = service.upsert_user_preference(
        user_id=user_id,
        data=UserPreferenceInput(
            default_pace=request.default_pace,
            interests=request.interests,
            dietary_preferences=request.dietary_preferences,
            avoidances=request.avoidances,
        ),
    )
    return user_preference_to_response(preference)
