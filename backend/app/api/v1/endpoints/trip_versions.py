from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ....api.dependencies import get_current_user_id, get_trip_candidate_service
from ....schemas.trips import RollbackVersionRequest, TripVersionResponse, version_to_response
from ....services.trip_candidates import TripCandidateService, TripVersionNotFoundError

router = APIRouter()


@router.get("/{version_id}", response_model=TripVersionResponse)
def get_version(
    version_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TripCandidateService = Depends(get_trip_candidate_service),
) -> TripVersionResponse:
    try:
        return version_to_response(service.get_version(user_id=user_id, version_id=version_id))
    except TripVersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found") from exc


@router.post("/{version_id}/rollback", response_model=TripVersionResponse)
def rollback_version(
    version_id: str,
    request: RollbackVersionRequest,
    user_id: str = Depends(get_current_user_id),
    service: TripCandidateService = Depends(get_trip_candidate_service),
) -> TripVersionResponse:
    try:
        version = service.rollback_version(user_id=user_id, version_id=version_id, publish_note=request.publish_note)
        return version_to_response(version)
    except TripVersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found") from exc
