"""Versioned family contracts. Unknown material fields are rejected."""
from ucp_pulse.util import digest

NORM_VERSION = 1
FIELDS = {
    "spec_release": {"version", "tag", "tag_object", "tag_commit", "branch_head", "published_at", "release_id", "notes", "assets", "draft", "prerelease", "deleted", "changes", "amended", "artifact_republished"},
    "spec_pr": {"number", "title", "merge_commit_subject", "base", "state", "merged_at", "merge_sha", "labels", "body", "notice_links", "updated_at"},
    "sdk_pr": {"number", "title", "merge_commit_subject", "base", "state", "merged_at", "merge_sha", "labels", "body", "notice_links", "updated_at"},
    "normative_commit": {"sha", "parents", "subject", "files", "changes", "branches"},
    "sdk_tag": {"tag", "scheme", "tag_object", "tag_commit", "published_at", "notes", "assets", "deleted", "draft", "prerelease"},
    "registry_version": {"package", "version", "repo", "files", "yanked", "deleted", "dist_tags", "published_at", "binding_ref"},
    "announcement": {"date", "slug", "title", "body", "discussion_urls", "deleted"},
    "governance": {"path", "body", "deleted"},
    "discussion": {"number", "title", "body", "category", "author", "association", "updated_at", "deleted", "announcement_event"},
    "changelog": {"guid", "title", "body", "published_at", "url"},
}


def material(family, value):
    if family not in FIELDS or set(value) - FIELDS[family]:
        raise ValueError("unknown family or material fields")
    value = dict(value)
    for key in ("title", "body", "notes", "subject", "merge_commit_subject"):
        if isinstance(value.get(key), str):
            value[key] = value[key].replace("\r\n", "\n").strip()
    for key in ("labels", "notice_links", "discussion_urls", "branches", "dist_tags"):
        if key in value:
            value[key] = sorted(set(value[key]))
    return value


def event_id(family, subject):
    repo = subject.get("repo", "").rsplit("/", 1)[-1]
    if family == "spec_release":
        return "ucp:release:" + subject["version"]
    if family in {"spec_pr", "sdk_pr"}:
        return f"{repo}:pr:{subject['number']}"
    if family == "normative_commit":
        return "ucp:commit:" + subject["sha"]
    if family == "sdk_tag":
        return f"{repo}:tag:{subject['tag']}"
    if family == "registry_version":
        return f"{subject['registry']}:{subject['package']}:{subject['version']}"
    if family == "announcement":
        return f"ucp:announce:{subject['date']}:{subject['slug']}"
    if family == "governance":
        return "ucpgov:file:" + subject["path"]
    if family == "discussion":
        return f"ucp:discussion:{subject['number']}"
    if family == "changelog":
        return "shopify:changelog:" + subject["guid"]
    raise ValueError("unknown family")


def revision_id(identity, payload):
    return digest([identity, digest(payload)])
