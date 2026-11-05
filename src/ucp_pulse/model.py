"""Immutable evidence candidates and revisions."""
from urllib.parse import urlsplit
from copy import deepcopy
from ucp_pulse.families import NORM_VERSION, event_id, material, revision_id
from ucp_pulse.util import digest, stamp


def candidate(family, subject, payload, facts, evidence, event_time, time_kind, authority, source):
    if time_kind not in {"merged", "tagged", "published", "posted", "committed", "observed"}:
        raise ValueError("invalid event time kind")
    if authority not in {"official_repo", "official_registry", "official_vendor", "secondary"}:
        raise ValueError("invalid authority")
    parsed = urlsplit(evidence.get("url", ""))
    if parsed.scheme != "https" or not parsed.hostname or not evidence.get("ref"):
        raise ValueError("evidence requires HTTPS URL and immutable ref or digest")
    if len(evidence.get("excerpt", "")) > 400:
        raise ValueError("excerpt too long")
    return dict(event_id=event_id(family, subject), family=family, subject=subject,
                material=material(family, payload), facts=facts, evidence=evidence,
                event_time=stamp(event_time), event_time_kind=time_kind,
                authority=authority, source=source, norm_version=NORM_VERSION)


def revise(item, previous, observed_at, run_id):
    item = deepcopy(item)
    if previous and previous["material"] == item["material"]:
        # Facts must be deterministic from material. Reject silent reclassification.
        if previous["facts"] != item["facts"]:
            raise ValueError("facts changed without material revision")
        return None
    item.update(material_digest=digest(item["material"]),
                revision_id=revision_id(item["event_id"], item["material"]),
                supersedes=previous["revision_id"] if previous else None,
                first_seen_at=stamp(observed_at), observed_at=stamp(observed_at), run_id=run_id)
    item["observation_id"] = digest([item["revision_id"], item["supersedes"], item["observed_at"]])
    return item
