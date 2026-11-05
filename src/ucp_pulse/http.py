"""Bounded read-only source transport. Never logs headers or credentials."""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from ucp_pulse.util import canonical, digest, json_file


class SourceError(RuntimeError):
    pass


class RateLimited(SourceError):
    pass


def allowed(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443) or p.fragment:
        raise SourceError("source URL must be HTTPS without credentials, fragment or custom port")
    permitted = (p.hostname == "api.github.com" or
                 p.hostname == "pypi.org" and p.path.startswith("/pypi/") and p.path.endswith("/json") or
                 p.hostname == "registry.npmjs.org" or
                 p.hostname == "shopify.dev" and p.path == "/changelog/feed.xml" and not p.query)
    if not permitted:
        raise SourceError("source host/path not allowlisted")
    return p


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, cache=None, token=None, timeout=20, byte_cap=8_000_000, transport=None):
        self.cache_path = Path(cache) if cache else None
        self.cache = json_file(self.cache_path, {}) if cache else {}
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        self.timeout, self.byte_cap = timeout, byte_cap
        self.transport = transport or self._network
        self.stopped = False
        self.requests = 0

    def _network(self, url, headers, data):
        request = urllib.request.Request(url, headers=headers, data=data)
        opener = urllib.request.build_opener(NoRedirect())
        for attempt in range(3):
            try:
                response = opener.open(request, timeout=self.timeout)
                break
            except urllib.error.HTTPError as error:
                response = error
                break
            except (OSError, urllib.error.URLError) as error:
                if attempt == 2:
                    raise SourceError(type(error).__name__ + ": source connection failed after 3 attempts") from None
                time.sleep(0.25 * (attempt + 1))
        with response:
            body = response.read(self.byte_cap + 1)
            return response.status, {k.lower(): v for k, v in response.headers.items()}, body

    def get(self, url, query=None):
        origin = allowed(url)
        if self.stopped and origin.hostname == "api.github.com":
            raise RateLimited("GitHub remaining below 100; collection stopped")
        data = None
        if query is not None:
            if url != "https://api.github.com/graphql" or not query.lstrip().startswith("query") or re.search(r"\bmutation\b", query):
                raise SourceError("only read-only GraphQL queries allowed")
            data = canonical({"query": query}).encode()
        key = digest([url, query])
        old = self.cache.get(key)
        headers = {"User-Agent": "ucp-pulse/0.1", "Accept": "application/json"}
        if origin.hostname == "api.github.com":
            headers["X-GitHub-Api-Version"] = "2022-11-28"
            if self.token:
                headers["Authorization"] = "Bearer " + self.token
        if data:
            headers["Content-Type"] = "application/json"
        if old and old.get("etag") and data is None:
            headers["If-None-Match"] = old["etag"]
        for _ in range(4):
            self.requests += 1
            status, response_headers, body = self.transport(url, headers, data)
            response_headers = {k.lower(): str(v) for k, v in response_headers.items()}
            if len(body) > self.byte_cap:
                raise SourceError("response byte cap exceeded")
            if origin.hostname == "api.github.com":
                remaining = response_headers.get("x-ratelimit-remaining")
                if remaining is None:
                    raise SourceError("GitHub rate-limit header missing")
                if int(remaining) < 100:
                    self.stopped = True
                    raise RateLimited(f"GitHub remaining {int(remaining)} < 100; reset={response_headers.get('x-ratelimit-reset', 'unknown')}")
            if status in {301, 302, 303, 307, 308}:
                target = urllib.parse.urljoin(url, response_headers.get("location", ""))
                if allowed(target).hostname != origin.hostname:
                    raise SourceError("off-host redirect refused")
                url = target
                continue
            if status == 304:
                if not old:
                    raise SourceError("304 without cached response")
                return old["body"].encode(), {**old["headers"], **response_headers}
            if status != 200:
                raise SourceError(f"HTTP {status}; retry-after={response_headers.get('retry-after', 'not supplied')}")
            text = body.decode("utf-8")
            safe_headers = {k: v for k, v in response_headers.items() if k in {"etag", "link", "content-type"}}
            self.cache[key] = {"etag": response_headers.get("etag"), "body": text, "headers": safe_headers}
            if self.cache_path:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_text(canonical(self.cache))
            return body, response_headers
        raise SourceError("redirect limit exceeded")

    def json(self, url, query=None):
        body, headers = self.get(url, query)
        value = json.loads(body)
        if query is not None:
            if value.get("errors"):
                # GraphQL messages may echo query data. Error types are sufficient.
                kinds = sorted({str(e.get("type", "GRAPHQL_ERROR")) for e in value["errors"]})
                raise SourceError("GraphQL: " + ",".join(kinds))
            remaining = value.get("data", {}).get("rateLimit", {}).get("remaining")
            if remaining is None or remaining < 100:
                self.stopped = True
                raise RateLimited("GraphQL remaining missing or below 100")
        return value

    def pages(self, url):
        values, seen = [], set()
        for _ in range(500):
            if url in seen:
                raise SourceError("pagination cycle")
            seen.add(url)
            body, headers = self.get(url)
            page = json.loads(body)
            if not isinstance(page, list):
                raise SourceError("list endpoint returned non-list")
            values.extend(page)
            match = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("link", ""))
            if not match:
                return values
            following = urllib.parse.urljoin(url, match[1])
            if allowed(following).hostname != allowed(url).hostname:
                raise SourceError("off-host pagination refused")
            url = following
        raise SourceError("pagination limit exceeded; cursor retained")
