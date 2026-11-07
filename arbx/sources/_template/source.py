"""Template for a new bookmaker adapter.

Copy this directory, rename it, set ``name``, add a block to
config/sources.yaml and register the class in arbx/sources/registry.py.
Nothing outside sources/ should need to change.

Recommended order of work for a new site:
  1. Open the site with the browser devtools network tab and find the XHR that
     carries the line. arbx.http.browser.capture_xhr automates this.
  2. Call that endpoint directly with arbx.http.session, save one response
     into tests/fixtures/.
  3. Write parse() against the fixture until events and quotes come out right.
  4. Only then wire fetch() into the pipeline.
"""

from __future__ import annotations

from arbx.models import Quote, RawSnapshot, SourceEvent, Sport
from arbx.sources.base import BaseSource


class TemplateSource(BaseSource):
    name = "template"

    def fetch(self, sports: list[Sport]) -> RawSnapshot:
        raise NotImplementedError

    def parse(self, snapshot: RawSnapshot) -> tuple[list[SourceEvent], list[Quote]]:
        raise NotImplementedError
