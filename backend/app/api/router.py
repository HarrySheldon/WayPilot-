from fastapi import APIRouter

from .v1.endpoints.agent_runs import router as agent_runs_router
from .v1.endpoints.auth import router as auth_router
from .v1.endpoints.health import router as health_router
from .v1.endpoints.preferences import router as preferences_router
from .v1.endpoints.trip_candidates import router as trip_candidates_router
from .v1.endpoints.trip_versions import router as trip_versions_router
from .v1.endpoints.trips import router as trips_router
from .v1.endpoints.users import router as users_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(preferences_router, prefix="/preferences", tags=["preferences"])
api_router.include_router(trips_router, prefix="/trips", tags=["trips"])
api_router.include_router(trip_candidates_router, prefix="/trip-candidates", tags=["trip-candidates"])
api_router.include_router(trip_versions_router, prefix="/trip-versions", tags=["trip-versions"])
api_router.include_router(agent_runs_router, prefix="/agent-runs", tags=["agent-runs"])
