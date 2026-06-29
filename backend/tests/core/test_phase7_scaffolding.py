from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]


class Phase7ScaffoldingTests(unittest.TestCase):
    def test_candidate_version_and_agent_run_surfaces_are_wired(self) -> None:
        required_files = [
            ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "trip_candidates.py",
            ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "trip_versions.py",
            ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "agent_runs.py",
            ROOT / "frontend" / "src" / "pages" / "CandidateReviewPage.tsx",
            ROOT / "frontend" / "src" / "pages" / "VersionsPage.tsx",
            ROOT / "frontend" / "src" / "pages" / "AgentRunPage.tsx",
        ]
        for path in required_files:
            self.assertTrue(path.exists(), f"{path} is required")

        router = (ROOT / "backend" / "app" / "api" / "router.py").read_text(encoding="utf-8")
        app = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
        types = (ROOT / "frontend" / "src" / "api" / "types.ts").read_text(encoding="utf-8")

        self.assertIn("trip_candidates_router", router)
        self.assertIn("trip_versions_router", router)
        self.assertIn("agent_runs_router", router)
        self.assertIn("/trips/:tripId/candidates/:candidateId", app)
        self.assertIn("/trips/:tripId/versions", app)
        self.assertIn("/agent-runs/:runId", app)
        self.assertIn("interface TripCandidate", types)
        self.assertIn("interface TripVersion", types)
        self.assertIn("interface AgentRun", types)


if __name__ == "__main__":
    unittest.main()
