from __future__ import annotations

import unittest

from job_agent.adapters.naukri import NaukriAdapter
from job_agent.models import SearchFilters


class FakeResponse:
    def __init__(self, html: str) -> None:
        self._html = html

    def raise_for_status(self) -> None:
        return None

    @property
    def text(self) -> str:
        return self._html


class FakeSession:
    def __init__(self, html: str) -> None:
        self.headers = {"User-Agent": "python-requests/2.32.0"}
        self._html = html

    def get(self, url: str, timeout: int) -> FakeResponse:
        self.last_url = url
        self.last_timeout = timeout
        return FakeResponse(self._html)


NAUKRI_HTML = """
<html>
  <body>
    <div class="srp-jobtuple-wrapper" data-job-id="171024011437">
      <div class="cust-job-tuple layout-wrapper lay-2 sjw__tuple">
        <div class=" row1">
          <h2>
            <a
              class="title"
              title="Python Developer"
              href="https://www.naukri.com/job-listings-python-developer-persistent-systems-limited-bengaluru-3-to-7-years-171024011437"
              target="_blank"
              rel="noopener noreferrer"
            >Python Developer</a>
          </h2>
        </div>
        <div class=" row2">
          <span class=" comp-dtls-wrap">
            <a class=" comp-name mw-25" title="Persistent" href="https://www.naukri.com/persistent-jobs-careers-5929" target="_blank">Persistent</a>
          </span>
        </div>
        <div class=" row3">
          <div class="job-details">
            <span class="exp-wrap">
              <span class="ni-job-tuple-icon ni-job-tuple-icon-srp-experience exp">
                <span title="3-7 Yrs " class="expwdth">3-7 Yrs</span>
              </span>
            </span>
            <span class="loc-wrap ver-line">
              <span class="ni-job-tuple-icon ni-job-tuple-icon-srp-location loc">
                <span title="Bengaluru " class="locWdth">Bengaluru</span>
              </span>
            </span>
          </div>
        </div>
        <div class=" row4">
          <span class="job-desc ni-job-tuple-icon ni-job-tuple-icon-srp-description">
            Expertise You'll Bring. A Bachelor of Science degree in Computer Science, Engineering or similar.
          </span>
        </div>
        <div class=" row5">
          <ul class="tags-gt">
            <li class="dot-gt tag-li">python development</li>
            <li class="dot-gt tag-li">css</li>
            <li class="dot-gt tag-li">bootstrap</li>
            <li class="dot-gt tag-li">jquery</li>
            <li class="dot-gt tag-li">sql</li>
            <li class="dot-gt tag-li">git</li>
          </ul>
        </div>
        <div class=" row6">
          <span class="job-post-day">2 weeks ago</span>
        </div>
      </div>
    </div>
    <div class="srp-jobtuple-wrapper" data-job-id="171024099999">
      <div class="cust-job-tuple layout-wrapper lay-2 sjw__tuple">
        <div class=" row1">
          <h2>
            <a
              class="title"
              title="Data Scientist"
              href="https://www.naukri.com/job-listings-data-scientist-example-171024099999"
              target="_blank"
              rel="noopener noreferrer"
            >Data Scientist</a>
          </h2>
        </div>
        <div class=" row2">
          <span class=" comp-dtls-wrap">
            <a class=" comp-name mw-25" title="Example" href="https://www.naukri.com/example-jobs-careers-1234" target="_blank">Example</a>
          </span>
        </div>
        <div class=" row3">
          <div class="job-details">
            <span class="exp-wrap">
              <span class="ni-job-tuple-icon ni-job-tuple-icon-srp-experience exp">
                <span title="2-5 Yrs " class="expwdth">2-5 Yrs</span>
              </span>
            </span>
            <span class="loc-wrap ver-line">
              <span class="ni-job-tuple-icon ni-job-tuple-icon-srp-location loc">
                <span title="Remote " class="locWdth">Remote</span>
              </span>
            </span>
          </div>
        </div>
        <div class=" row4">
          <span class="job-desc ni-job-tuple-icon ni-job-tuple-icon-srp-description">
            Build models and ship insights.
          </span>
        </div>
        <div class=" row5">
          <ul class="tags-gt">
            <li class="dot-gt tag-li">python</li>
            <li class="dot-gt tag-li">machine learning</li>
          </ul>
        </div>
        <div class=" row6">
          <span class="job-post-day">3 days ago</span>
        </div>
      </div>
    </div>
  </body>
</html>
"""


class NaukriAdapterTests(unittest.TestCase):
    def test_collect_parses_selector_based_results(self) -> None:
        adapter = NaukriAdapter(session=FakeSession(NAUKRI_HTML))

        results = adapter.collect("Python Developer", SearchFilters())

        self.assertEqual(1, len(results))
        job = results[0]
        self.assertEqual("naukri", job["source"])
        self.assertEqual("Python Developer", job["title"])
        self.assertEqual("Persistent", job["company"])
        self.assertEqual("Bengaluru", job["location"])
        self.assertEqual(
            "https://www.naukri.com/job-listings-python-developer-persistent-systems-limited-bengaluru-3-to-7-years-171024011437",
            job["job_url"],
        )
        self.assertEqual("2 weeks ago", job["posted_date"])
        self.assertTrue(job["description_snippet"].startswith("Expertise You'll Bring."))
        self.assertEqual("Python Developer", job["search_keyword"])
        self.assertEqual("https://www.naukri.com/python-developer-jobs", adapter.session.last_url)

    def test_collect_respects_location_filter(self) -> None:
        adapter = NaukriAdapter(session=FakeSession(NAUKRI_HTML))

        results = adapter.collect("Python Developer", SearchFilters(location="Pune"))

        self.assertEqual([], results)


if __name__ == "__main__":
    unittest.main()
