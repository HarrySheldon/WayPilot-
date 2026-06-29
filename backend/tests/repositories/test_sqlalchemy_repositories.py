from __future__ import annotations

import unittest

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.domain.conflicts import DeterministicConflictDetector
from backend.app.models.orm import ItineraryItemORM, TripDayORM, TripVersionORM, UserORM
from backend.app.repositories.sqlalchemy import (
    SQLAlchemyTransactionManager,
    SQLAlchemyTripCandidateRepository,
    SQLAlchemyTripRepository,
)
from backend.app.services.trip_candidates import TripCandidateCreateInput, TripCandidateService
from backend.app.services.trips import TripCreateInput, TripService


class FailingPublishedCandidateRepository(SQLAlchemyTripCandidateRepository):
    def save(self, candidate):
        if candidate.status == "published":
            raise RuntimeError("candidate publish status write failed")
        return super().save(candidate)


class SQLAlchemyRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def test_publish_candidate_persists_version_and_current_projection(self) -> None:
        session = self.SessionLocal()
        self._seed_user(session, "user-1")
        trip_repository = SQLAlchemyTripRepository(session)
        candidate_repository = SQLAlchemyTripCandidateRepository(session)
        trip_service = TripService(trip_repository=trip_repository, id_generator=lambda: "trip-1")
        candidate_service = TripCandidateService(
            trip_repository=trip_repository,
            candidate_repository=candidate_repository,
            conflict_detector=DeterministicConflictDetector(),
            transaction_manager=SQLAlchemyTransactionManager(session),
            id_generator=lambda: "candidate-1",
        )

        trip_service.create_trip(
            user_id="user-1",
            data=TripCreateInput(title="Tokyo", destination="Tokyo", budget_total=5000),
        )
        candidate_service.create_candidate(
            user_id="user-1",
            trip_id="trip-1",
            data=TripCandidateCreateInput(
                source_type="agent",
                itinerary_snapshot={
                    "days": [
                        {
                            "date": "2026-07-01",
                            "items": [
                                {
                                    "temp_id": "item-1",
                                    "title": "Visit Senso-ji",
                                    "start_time": "09:00",
                                    "end_time": "11:00",
                                }
                            ],
                        }
                    ]
                },
                budget_snapshot={"total": 1200, "currency": "JPY"},
                preference_snapshot={"pace": "standard"},
            ),
        )
        session.commit()

        version = candidate_service.publish_candidate(
            user_id="user-1",
            candidate_id="candidate-1",
            publish_note="Initial publish",
        )
        session.commit()
        session.expire_all()

        stored_trip = trip_repository.get("trip-1")
        stored_candidate = candidate_repository.get("candidate-1")
        day_count = session.scalar(select(func.count()).select_from(TripDayORM).where(TripDayORM.trip_id == "trip-1"))
        item_count = session.scalar(select(func.count()).select_from(ItineraryItemORM))

        self.assertEqual(version.version_no, 1)
        self.assertEqual(stored_trip.active_version_id, "trip-1-v1")
        self.assertEqual(stored_trip.versions[0].publish_note, "Initial publish")
        self.assertEqual(stored_trip.days[0].items[0].title, "Visit Senso-ji")
        self.assertEqual(stored_candidate.status, "published")
        self.assertEqual(day_count, 1)
        self.assertEqual(item_count, 1)

    def test_publish_candidate_rolls_back_when_late_write_fails(self) -> None:
        session = self.SessionLocal()
        self._seed_user(session, "user-1")
        trip_repository = SQLAlchemyTripRepository(session)
        candidate_repository = SQLAlchemyTripCandidateRepository(session)
        trip_service = TripService(trip_repository=trip_repository, id_generator=lambda: "trip-1")
        candidate_service = TripCandidateService(
            trip_repository=trip_repository,
            candidate_repository=candidate_repository,
            conflict_detector=DeterministicConflictDetector(),
            transaction_manager=SQLAlchemyTransactionManager(session),
            id_generator=lambda: "candidate-1",
        )
        trip_service.create_trip(user_id="user-1", data=TripCreateInput(title="Tokyo", destination="Tokyo"))
        candidate_service.create_candidate(
            user_id="user-1",
            trip_id="trip-1",
            data=TripCandidateCreateInput(
                source_type="agent",
                itinerary_snapshot={"days": [{"date": "2026-07-01", "items": [{"temp_id": "item-1", "title": "Museum"}]}]},
            ),
        )
        session.commit()
        session.close()

        failing_session = self.SessionLocal()
        failing_service = TripCandidateService(
            trip_repository=SQLAlchemyTripRepository(failing_session),
            candidate_repository=FailingPublishedCandidateRepository(failing_session),
            conflict_detector=DeterministicConflictDetector(),
            transaction_manager=SQLAlchemyTransactionManager(failing_session),
            id_generator=lambda: "unused",
        )

        with self.assertRaisesRegex(RuntimeError, "candidate publish status write failed"):
            failing_service.publish_candidate(user_id="user-1", candidate_id="candidate-1")

        inspect_session = self.SessionLocal()
        self.assertEqual(inspect_session.scalar(select(func.count()).select_from(TripVersionORM)), 0)
        self.assertEqual(inspect_session.scalar(select(func.count()).select_from(TripDayORM)), 0)
        self.assertEqual(SQLAlchemyTripRepository(inspect_session).get("trip-1").active_version_id, None)
        self.assertEqual(SQLAlchemyTripCandidateRepository(inspect_session).get("candidate-1").status, "draft")

    def _seed_user(self, session: Session, user_id: str) -> None:
        session.add(
            UserORM(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="not-used",
                display_name=user_id,
            )
        )
        session.commit()


if __name__ == "__main__":
    unittest.main()
