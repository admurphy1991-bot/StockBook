"""Daily jobs list from the Sansom AI feed (Telepathy). Falls back to the hardcoded list on any problem."""
import csv, io, re
import httpx

FEED_URL = "https://sansom-ai.vercel.app/api/feeds/jobs"
TOKEN_ENV = "JOBS_FEED_TOKEN"
MIN_JOBS = 100
MIN_KEEP_RATIO = 0.7
MAX_LEN = 200

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _clean(s):
    return _CONTROL.sub(" ", s or "").strip()[:MAX_LEN]


def parse_jobs_csv(text):
    """Feed CSV -> ["CODE - Name", ...] in feed order, same shape as DEFAULT_JOBS."""
    out, seen = [], set()
    for row in csv.DictReader(io.StringIO(text)):
        norm = {(k or "").strip().lower(): v for k, v in row.items()}
        code = _clean(norm.get("code") or norm.get("job") or norm.get("job number"))
        name = _clean(norm.get("name"))
        if not code:
            continue
        entry = f"{code} - {name}" if name else code
        if entry not in seen:
            seen.add(entry)
            out.append(entry)
    return out


def acceptable(new_jobs, current_count):
    """Refuse an empty, truncated or garbled feed so it can never wipe the working list."""
    return len(new_jobs) >= MIN_JOBS and len(new_jobs) >= MIN_KEEP_RATIO * current_count


async def fetch_jobs(token):
    # The token only ever goes to FEED_URL, and redirects are not followed.
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        r = await client.get(FEED_URL, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return parse_jobs_csv(r.text)
