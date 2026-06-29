from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ....api.dependencies import get_current_user_id, get_trip_candidate_service
from ....domain.trips import PublishBlockedError
from ....schemas.trips import (
    PublishCandidateRequest,
    TripCandidateResponse,
    TripVersionResponse,
    candidate_to_response,
    version_to_response,
)
from ....services.trip_candidates import CandidateNotFoundError, TripCandidateService

router = APIRouter()


@router.get("/{candidate_id}", response_model=TripCandidateResponse)
def get_candidate(
    candidate_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TripCandidateService = Depends(get_trip_candidate_service),
) -> TripCandidateResponse:
    try:
        return candidate_to_response(service.get_candidate(user_id=user_id, candidate_id=candidate_id))
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found") from exc


@router.post("/{candidate_id}/validate", response_model=TripCandidateResponse)
def validate_candidate(
    candidate_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TripCandidateService = Depends(get_trip_candidate_service),
) -> TripCandidateResponse:
    try:
        return candidate_to_response(service.validate_candidate(user_id=user_id, candidate_id=candidate_id))
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found") from exc


@router.post("/{candidate_id}/publish", response_model=TripVersionResponse)
def publish_candidate(
    candidate_id: str,
    request: PublishCandidateRequest,
    user_id: str = Depends(get_current_user_id),
    service: TripCandidateService = Depends(get_trip_candidate_service),
) -> TripVersionResponse:
    try:
        version = service.publish_candidate(
            user_id=user_id,
            candidate_id=candidate_id,
            ignored_warning_conflict_ids=set(request.ignored_warning_conflict_ids),
            publish_note=request.publish_note,
        )
        return version_to_response(version)
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found") from exc
    except PublishBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{candidate_id}/discard", response_model=TripCandidateResponse)
def discard_candidate(
    candidate_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TripCandidateService = Depends(get_trip_candidate_service),
) -> TripCandidateResponse:
    try:
        return candidate_to_response(service.discard_candidate(user_id=user_id, candidate_id=candidate_id))
    except CandidateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found") from exc
