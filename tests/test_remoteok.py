from __future__ import annotations

import unittest

from job_agent.adapters.remoteok import RemoteOKAdapter
from job_agent.models import SearchFilters


class FakeResponse:
    def __init__(self, payload: list[object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[object]:
        return self._payload


class FakeSession:
    def __init__(self, payload: list[object]) -> None:
        self.headers = {"User-Agent": "python-requests/2.32.0"}
        self._payload = payload

    def get(self, url: str, timeout: int) -> FakeResponse:
        self.last_url = url
        self.last_timeout = timeout
        return FakeResponse(self._payload)


class RemoteOKAdapterTests(unittest.TestCase):
    def test_collect_filters_and_maps_jobs(self) -> None:
        payload = [
            {"legal": "notice"},
            {
                "position": "Senior Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "description": "<p>Build APIs</p>",
                "tags": ["full time", "engineer"],
                "url": "https://remoteok.com/remote-jobs/1",
                "salary_min": 120000,
                "salary_max": 150000,
                "date": "2026-06-09T17:51:27+00:00",
                "epoch": 1781027487,
            },
            {
                "position": "Data Scientist",
                "company": "Acme",
                "location": "Remote",
                "description": "<p>Data</p>",
                "tags": ["engineer"],
                "url": "https://remoteok.com/remote-jobs/2",
                "salary_min": 0,
                "salary_max": 0,
                "date": "2026-06-09T17:51:27+00:00",
                "epoch": 1781027487,
            },
        ]
        adapter = RemoteOKAdapter(session=FakeSession(payload))

        results = adapter.collect("backend engineer", SearchFilters())

        self.assertEqual(1, len(results))
        job = results[0]
        self.assertEqual("remoteok", job["source"])
        self.assertEqual("Senior Backend Engineer", job["title"])
        self.assertEqual("Acme", job["company"])
        self.assertEqual("$120,000 - $150,000", job["salary"])
        self.assertEqual("https://remoteok.com/remote-jobs/1", job["job_url"])

    def test_collect_repairs_mojibake(self) -> None:
        payload = [
            {"legal": "notice"},
            {
                "position": "Principal Operations Engineer Hardware â€” Data Center Operations",
                "company": "Fluidstack",
                "location": "",
                "description": "<p>Build infrastructure.</p>",
                "tags": ["engineer"],
                "url": "https://remoteok.com/remote-jobs/3",
                "salary_min": 150000,
                "salary_max": 250000,
                "date": "2026-06-09T16:00:04+00:00",
                "epoch": 1781020804,
            },
        ]
        adapter = RemoteOKAdapter(session=FakeSession(payload))

        results = adapter.collect("engineer", SearchFilters())

        self.assertEqual(1, len(results))
        self.assertEqual(
            "Principal Operations Engineer Hardware — Data Center Operations",
            results[0]["title"],
        )


if __name__ == "__main__":
    unittest.main()
