"""Pure normalizers and bounded GitHub readers for S1-S3."""
import base64
import json
import re
from datetime import timedelta
from urllib.parse import quote
from ucp_pulse.diff import alerts
from ucp_pulse.http import SourceError
from ucp_pulse.model import candidate
from ucp_pulse.util import digest, stamp, utc

ORG = "Universal-Commerce-Protocol"
SPEC = ORG + "/ucp"
NORMATIVE = ("source/", "docs/specification/", "docs/versioning.md")


def evidence(url, ref, snapshot, excerpt="", pointer=None):
    return {"url": url, "ref": ref, "pointer": pointer,
            "snapshot": "data/snapshots/" + digest(snapshot) + ".json", "excerpt": excerpt[:400]}


def declared(title, subject, labels):
    bang = r"^[a-zA-Z][\w-]*(?:\([^\n)]*\))?!:"
    return bool(re.search(bang, title) or re.search(bang, subject) or
                any("breaking" in label.lower() for label in labels))


def normalize_pr(repo, pr, merge_subject, observed, tracked=False):
    labels = sorted(label["name"] if isinstance(label, dict) else label for label in pr.get("labels", []))
    merged = bool(pr.get("merged_at"))
    is_breaking = declared(pr["title"], merge_subject, labels)
    if not tracked and not merged and not (pr["state"] == "open" and is_breaking):
        return None
    body = pr.get("body") or ""
    payload = {"number": pr["number"], "title": pr["title"], "merge_commit_subject": merge_subject,
               "base": pr["base"]["ref"], "state": pr["state"], "merged_at": pr.get("merged_at"),
               "merge_sha": pr.get("merge_commit_sha"), "labels": labels, "body": body,
               "notice_links": sorted(set(re.findall(r"https://github\.com/Universal-Commerce-Protocol/ucp/discussions/\d+", body))),
               "updated_at": pr.get("updated_at")}
    url = f"https://github.com/{repo}/pull/{pr['number']}"
    facts = {"opened": pr["state"] == "open", "merged": merged, "author_declared_breaking": is_breaking}
    return candidate("spec_pr" if repo == SPEC else "sdk_pr", {"repo": repo, "number": pr["number"]},
                     payload, facts, evidence(url, repo + "@" + (pr.get("merge_commit_sha") or digest(payload)), payload, pr["title"]),
                     pr.get("merged_at") or pr.get("created_at") or observed,
                     "merged" if merged else "posted" if pr.get("created_at") else "observed", "official_repo", "S2" if repo == SPEC else "S6")


def release_lines(tags, releases, branches, previous, observed, changes=None):
    tags = {t["name"].removeprefix("v"): t for t in tags if re.fullmatch(r"v\d{4}-\d{2}-\d{2}", t["name"])}
    releases = {r["tag_name"].removeprefix("v"): r for r in releases if re.fullmatch(r"v\d{4}-\d{2}-\d{2}", r["tag_name"])}
    branches = {b["name"].split("/", 1)[1]: b["commit"]["sha"] for b in branches if re.fullmatch(r"release/\d{4}-\d{2}-\d{2}", b["name"])}
    output = []
    for version in sorted(tags.keys() | releases.keys() | branches.keys() | previous.keys()):
        tag, release, old = tags.get(version, {}), releases.get(version, {}), previous.get(version, {})
        oldmat = old.get("material", {})
        payload = {"version": version, "tag": tag.get("name"), "tag_object": tag.get("object"),
                   "tag_commit": tag.get("commit"), "branch_head": branches.get(version),
                   "published_at": release.get("published_at"), "release_id": release.get("id"),
                   "notes": (release.get("body") or "").replace("\r\n", "\n").strip(), "assets": sorted([
                       {"id": a["id"], "digest": a.get("digest"), "size": a.get("size"), "updated_at": a.get("updated_at")}
                       for a in release.get("assets", [])], key=lambda a: a["id"]),
                   "draft": release.get("draft", False), "prerelease": release.get("prerelease", False),
                   "deleted": {"tag": bool((oldmat.get("tag") or oldmat.get("deleted", {}).get("tag")) and not tag), "release": bool((oldmat.get("release_id") or oldmat.get("deleted", {}).get("release")) and not release),
                               "branch": bool((oldmat.get("branch_head") or oldmat.get("deleted", {}).get("branch")) and version not in branches)},
                   "changes": (changes or {}).get(version, oldmat.get("changes", []))}
        # Amendment facts remain true once detected; unchanged subsequent polls dedupe.
        payload["amended"] = bool(oldmat.get("amended") or oldmat.get("branch_head") and branches.get(version) != oldmat["branch_head"])
        payload["artifact_republished"] = bool(oldmat.get("artifact_republished") or oldmat.get("release_id") and
                                             (payload["notes"] != oldmat.get("notes") or payload["assets"] != oldmat.get("assets")))
        if oldmat.get("deleted") and not tag and not release and version not in branches:
            payload["deleted"] = oldmat["deleted"]
        facts = {"tagged": bool(tag), "release_published": bool(release and not release.get("draft") and not release.get("prerelease")),
                 "amended": payload["amended"], "artifact_republished": payload["artifact_republished"], "deleted": payload["deleted"]}
        url = f"https://github.com/{SPEC}/releases/tag/v{version}"
        ref = SPEC + "@" + (tag.get("commit") or branches.get(version) or digest(payload))
        output.append(candidate("spec_release", {"repo": SPEC, "version": version}, payload, facts,
                                evidence(url, ref, payload, release.get("body") or tag.get("name", "")),
                                release.get("published_at") or tag.get("time") or observed,
                                "published" if release.get("published_at") else "tagged" if tag.get("time") else "observed", "official_repo", "S1"))
    return output


class GitHub:
    def __init__(self, client):
        self.client = client
        self.document_cache = {}

    def url(self, repo, resource):
        return f"https://api.github.com/repos/{repo}/{resource}"

    def head(self, repo, ref="main"):
        return self.client.json(self.url(repo, "commits/" + quote(ref, safe="")))["sha"]

    def tags(self, repo):
        refs = self.client.json(self.url(repo, "git/matching-refs/tags/"))
        if not isinstance(refs, list):
            raise SourceError("tag refs are not a list")
        tags = []
        for ref in refs:
            obj = ref["object"]
            original = obj["sha"]
            tagged_at = None
            for _ in range(8):
                if obj["type"] == "commit":
                    break
                if obj["type"] != "tag":
                    raise SourceError("unexpected tag target")
                tag = self.client.json(self.url(repo, "git/tags/" + obj["sha"]))
                tagged_at = tagged_at or tag.get("tagger", {}).get("date")
                obj = tag["object"]
            else:
                raise SourceError("tag peel depth exceeded")
            tags.append({"name": ref["ref"].removeprefix("refs/tags/"), "object": original,
                         "commit": obj["sha"], "time": tagged_at})
        return tags

    def file(self, repo, path, ref):
        value = self.client.json(self.url(repo, "contents/" + quote(path, safe="/") + "?ref=" + quote(ref, safe="")))
        if value.get("encoding") != "base64":
            raise SourceError("unsupported content encoding or file too large")
        return base64.b64decode(value["content"]).decode("utf-8")

    def documents(self, repo, ref):
        if ref in self.document_cache:
            return self.document_cache[ref]
        tree = self.client.json(self.url(repo, "git/trees/" + ref + "?recursive=1"))
        if tree.get("truncated"):
            raise SourceError("truncated tree")
        docs = {}
        for entry in tree["tree"]:
            if entry["type"] == "blob" and entry["path"].startswith(("source/schemas/", "source/services/")) and entry["path"].endswith(".json"):
                blob = self.client.json(self.url(repo, "git/blobs/" + entry["sha"]))
                docs[entry["path"]] = json.loads(base64.b64decode(blob["content"]))
        self.document_cache[ref] = docs
        return docs

    def s1(self, previous, observed):
        tags = self.tags(SPEC)
        releases = self.client.pages(self.url(SPEC, "releases?per_page=100"))
        branches = self.client.pages(self.url(SPEC, "branches?per_page=100"))
        old = {r["subject"]["version"]: r for r in previous.values() if r["family"] == "spec_release"}
        changes = {}
        ordered = sorted(tags, key=lambda t: t["name"])
        for i, tag in enumerate(ordered):
            version = tag["name"].removeprefix("v")
            prior = old.get(version, {}).get("material", {})
            head = next((b["commit"]["sha"] for b in branches if b["name"] == "release/" + version), tag["commit"])
            base = prior.get("branch_head") or (ordered[i - 1]["commit"] if i else None)
            if base and head != base:
                changes[version] = alerts(self.documents(SPEC, base), self.documents(SPEC, head))
        items = release_lines(tags, releases, branches, old, observed, changes)
        return {"source": "S1", "complete": True, "items": items, "snapshots": [i["material"] for i in items]}

    def prs(self, repo, since, observed, previous=None):
        # Sort updated, not created. Never stop on an old-created PR.
        values = self.client.pages(self.url(repo, "pulls?state=all&sort=updated&direction=desc&per_page=100"))
        items = []
        for pr in values:
            if utc(pr["updated_at"]) < utc(since):
                continue
            subject = ""
            if pr.get("merged_at") and pr.get("merge_commit_sha"):
                commit = self.client.json(self.url(repo, "commits/" + pr["merge_commit_sha"]))
                subject = commit["commit"]["message"].splitlines()[0]
            item = normalize_pr(repo, pr, subject, observed, tracked=f"{repo.rsplit('/', 1)[-1]}:pr:{pr['number']}" in (previous or {}))
            if item:
                items.append(item)
        return items

    def s2(self, previous, observed, since):
        items = self.prs(SPEC, since, observed, previous)
        return {"source": "S2", "complete": True, "items": items, "snapshots": [i["material"] for i in items]}

    def s3(self, previous, observed, since):
        branches = self.client.pages(self.url(SPEC, "branches?per_page=100"))
        heads = {b["name"]: b["commit"]["sha"] for b in branches if b["name"] == "main" or b["name"].startswith("release/")}
        commits = {}
        for branch, head in heads.items():
            for path in NORMATIVE:
                resource = "commits?per_page=100&sha=" + head + "&path=" + quote(path, safe="") + "&since=" + quote(since)
                for row in self.client.pages(self.url(SPEC, resource)):
                    commits.setdefault(row["sha"], set()).add(branch)
        items = []
        for sha, containing in sorted(commits.items()):
            # Immutable commits only need collecting once, independent of branch discovery.
            if "ucp:commit:" + sha in previous:
                continue
            detail = self.client.json(self.url(SPEC, "commits/" + sha + "?per_page=100&page=1"))
            files = list(detail.get("files", []))
            page = 2
            while len(detail.get("files", [])) == 100:
                detail = self.client.json(self.url(SPEC, f"commits/{sha}?per_page=100&page={page}"))
                files.extend(detail.get("files", [])); page += 1
                if page > 31:
                    raise SourceError("commit file limit reached")
            paths = sorted({f["filename"] for f in files if f["filename"].startswith(NORMATIVE)})
            if not paths:
                continue
            first = self.client.json(self.url(SPEC, "commits/" + sha))
            parents = [p["sha"] for p in first["parents"]]
            changes = []
            if any(p.startswith(("source/schemas/", "source/services/")) for p in paths):
                before = self.documents(SPEC, parents[0]) if parents else {}
                changes = alerts(before, self.documents(SPEC, sha))
            payload = {"sha": sha, "parents": parents, "subject": first["commit"]["message"].splitlines()[0],
                       "files": paths, "changes": changes, "branches": sorted(containing)}
            items.append(candidate("normative_commit", {"repo": SPEC, "sha": sha}, payload, {"classification": "unknown"},
                                   evidence(f"https://github.com/{SPEC}/commit/{sha}", SPEC + "@" + sha, payload, payload["subject"]),
                                   first["commit"]["committer"]["date"], "committed", "official_repo", "S3"))
        return {"source": "S3", "complete": True, "items": items, "snapshots": [i["material"] for i in items]}
