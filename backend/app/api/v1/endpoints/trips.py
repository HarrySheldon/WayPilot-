from fastapi import APIRouter, Depends, HTTPException, status

from ....api.dependencies import get_current_user_id, get_trip_candidate_service, get_trip_service
from ....schemas.trips import (
    TripCandidateResponse,
    TripCreateRequest,
    TripResponse,
    TripVersionResponse,
    candidate_to_response,
    trip_to_response,
    version_to_response,
)
from ....services.trip_candidates import TripCandidateService
from ....services.trips import TripCreateInput, TripNotFoundError, TripService

router = APIRouter()


@router.get("", response_model=list[TripResponse])
def list_trips(
    user_id: str = Depends(get_current_user_id),
    service: TripService = Depends(get_trip_service),
) -> list[TripResponse]:
    return [trip_to_response(trip) for trip in service.list_trips(user_id=user_id)]


@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
    request: TripCreateRequest,
    user_id: str = Depends(get_current_user_id),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    trip = service.create_trip(
        user_id=user_id,
        data=TripCreateInput(
            title=request.title,
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            travelers_count=request.travelers_count,
            budget_total=request.budget_total,
            pace=request.pace,
            interests=request.interests,
            dietary_preferences=request.dietary_preferences,
            must_visit_places=request.must_visit_places,
            avoidances=request.avoidances,
            natural_language_note=request.natural_language_note,
        ),
    )
    return trip_to_response(trip)


@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    try:
        return trip_to_response(service.get_trip(user_id=user_id, trip_id=trip_id))
    except TripNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found") from exc


@router.get("/{trip_id}/candidates", response_model=list[TripCandidateResponse])
def list_trip_candidates(
    trip_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TripCandidateService = Depends(get_trip_candidate_service),
) -> list[TripCandidateResponse]:
    try:
        return [candidate_to_response(candidate) for candidate in service.list_candidates(user_id=user_id, trip_id=trip_id)]
    except TripNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found") from exc


@router.get("/{trip_id}/versions", response_model=list[TripVersionResponse])
def list_trip_versions(
    trip_id: str,
    user_id: str = Depends(get_current_user_id),
    service: TripCandidateService = Depends(get_trip_candidate_service),
) -> list[TripVersionResponse]:
    try:
        return [version_to_response(version) for version in service.list_versions(user_id=user_id, trip_id=trip_id)]
    except TripNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found") from exc
