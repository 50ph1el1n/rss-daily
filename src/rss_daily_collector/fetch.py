import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 10 * 1024 * 1024
USER_AGENT = "rss-daily-collector/1.0 (+https://github.com/50ph1el1n/rss-daily)"


@dataclass(frozen=True)
class FetchResult:
    body: bytes
    final_url: str
    status: int
    content_type: str | None
    etag: str | None
    last_modified: str | None
    attempts: int


class FetchFailure(RuntimeError):
    def __init__(self, code: str, attempts: int, status: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.attempts = attempts
        self.status = status


def fetch(url: str, timeout: int = 20) -> FetchResult:
    last: FetchFailure | None = None
    for attempt in range(1, 4):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "application/rss+xml, application/atom+xml, " "application/xml, text/xml"
                    ),
                },
            )
            with urlopen(request, timeout=timeout) as response:
                length = response.headers.get("Content-Length")
                if length and int(length) > MAX_RESPONSE_BYTES:
                    raise FetchFailure("FETCH_RESPONSE_TOO_LARGE", attempt, response.status)
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise FetchFailure("FETCH_RESPONSE_TOO_LARGE", attempt, response.status)
                return FetchResult(
                    body=body,
                    final_url=response.url,
                    status=response.status,
                    content_type=response.headers.get("Content-Type"),
                    etag=response.headers.get("ETag"),
                    last_modified=response.headers.get("Last-Modified"),
                    attempts=attempt,
                )
        except HTTPError as exc:
            last = FetchFailure(f"FETCH_HTTP_{exc.code}", attempt, exc.code)
            if exc.code != 429 and exc.code < 500:
                raise last from exc
        except (URLError, TimeoutError) as exc:
            last = FetchFailure(f"FETCH_NETWORK:{type(exc).__name__}", attempt)
        if attempt < 3:
            time.sleep(2 ** (attempt - 1))
    raise last or FetchFailure("FETCH_UNKNOWN", 3)
