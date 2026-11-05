"""S4-S8 and S10 collectors. Normalization functions are independently testable."""
import re
import tomllib
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from datetime import datetime
from ucp_pulse.collectors import ORG, SPEC, evidence
from ucp_pulse.http import SourceError
from ucp_pulse.model import candidate
from ucp_pulse.util import digest, stamp

SDK_REPOS = [ORG + '/' + name for name in ('js-sdk', 'python-sdk', 'ucp-schema')]
FEED = 'https://shopify.dev/changelog/feed.xml'
ANNOUNCEMENTS = 'docs/documentation/announcements.md'


def batch(source, items):
    return {'source': source, 'complete': True, 'items': items, 'snapshots': [i['material'] for i in items]}


def announcements(text, ref, previous, observed):
    # A dated heading starts an entry; subordinate undated headings stay inside it.
    headings = list(re.finditer(r'^#{1,6}\s+([^\n]*(?:\b\d{4}-\d{2}-\d{2}\b|\b[A-Z][a-z]+ +\d{1,2}, +\d{4}\b)[^\n]*)$', text, re.M))
    if text.strip() and not headings:
        raise SourceError('announcements has no recognized dated headings')
    items = []
    for index, match in enumerate(headings):
        title = match[1].strip()
        iso = re.search(r'\d{4}-\d{2}-\d{2}', title)
        written = iso[0] if iso else re.search(r'[A-Z][a-z]+ +\d{1,2}, +\d{4}', title)[0]
        date = written if iso else datetime.strptime(written, '%B %d, %Y').date().isoformat()
        stamp(date + 'T00:00:00Z')
        slug = re.sub(r'[^a-z0-9]+', '-', title.replace(written, '').lower()).strip('-') or 'notice'
        body = text[match.end():headings[index + 1].start() if index + 1 < len(headings) else len(text)].strip()
        payload = {'date': date, 'slug': slug, 'title': title, 'body': body, 'deleted': False,
                   'discussion_urls': sorted(set(re.findall(r'https://github\.com/Universal-Commerce-Protocol/ucp/discussions/\d+', body)))}
        items.append(candidate('announcement', {'date': date, 'slug': slug}, payload, {'notice_posted': True, 'deleted': False},
                               evidence(f'https://github.com/{SPEC}/blob/{ref}/{ANNOUNCEMENTS}', f'{SPEC}@{ref}:{ANNOUNCEMENTS}', payload, title),
                               date + 'T00:00:00Z', 'posted', 'official_repo', 'S4'))
    ids = {i['event_id'] for i in items}
    if len(ids) != len(items):
        raise SourceError('ambiguous duplicate announcement identity')
    for old in previous.values():
        if old['family'] == 'announcement' and old['event_id'] not in ids:
            payload = {**old['material'], 'deleted': True}
            items.append(candidate('announcement', old['subject'], payload, {'notice_posted': False, 'deleted': True},
                                   evidence(f'https://github.com/{SPEC}/blob/{ref}/{ANNOUNCEMENTS}', f'{SPEC}@{ref}:{ANNOUNCEMENTS}', payload),
                                   observed, 'observed', 'official_repo', 'S4'))
    return items


def governance(files, ref, previous, observed):
    repo = ORG + '/.github'
    prior = {r['subject']['path']: r for r in previous.values() if r['family'] == 'governance'}
    items = []
    for path in sorted(files.keys() | prior.keys()):
        deleted = path not in files
        payload = {'path': path, 'body': files.get(path, prior.get(path, {}).get('material', {}).get('body', '')), 'deleted': deleted}
        items.append(candidate('governance', {'repo': repo, 'path': path}, payload, {'deleted': deleted},
                               evidence(f'https://github.com/{repo}/blob/{ref}/{path}', f'{repo}@{ref}:{path}', payload),
                               observed, 'observed', 'official_repo', 'S5'))
    return items


def scheme(tag):
    if re.fullmatch(r'v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?', tag):
        return 'semver'
    if re.fullmatch(r'v?\d{4}-\d{2}-\d{2}', tag):
        return 'spec_date'
    if re.fullmatch(r'v?\d{4}-\d{2}-\d{2}[-.][\w.-]+', tag):
        return 'spec_date_suffixed'
    return 'unknown'


def sdk_tags(repo, tags, releases, previous, observed):
    tags = {t['name']: t for t in tags}
    releases = {r['tag_name']: r for r in releases}
    prior = {r['subject']['tag']: r for r in previous.values() if r['family'] == 'sdk_tag' and r['subject']['repo'] == repo}
    items = []
    for name in sorted(tags.keys() | releases.keys() | prior.keys()):
        tag, release = tags.get(name, {}), releases.get(name, {})
        old = prior.get(name, {}).get('material', {})
        payload = {'tag': name, 'scheme': scheme(name), 'tag_object': tag.get('object'), 'tag_commit': tag.get('commit'),
                   'published_at': release.get('published_at'), 'notes': release.get('body') or '',
                   'assets': sorted([{'id': a['id'], 'digest': a.get('digest'), 'size': a.get('size'), 'updated_at': a.get('updated_at')} for a in release.get('assets', [])], key=lambda a: a['id']),
                   'draft': release.get('draft', False), 'prerelease': release.get('prerelease', False),
                   'deleted': {'tag': bool((old.get('tag_commit') or old.get('deleted', {}).get('tag')) and not tag),
                               'release': bool((old.get('published_at') or old.get('deleted', {}).get('release')) and not release)}}
        facts = {'tagged': bool(tag), 'release_published': bool(release and not payload['draft'] and not payload['prerelease']), 'deleted': payload['deleted']}
        items.append(candidate('sdk_tag', {'repo': repo, 'tag': name}, payload, facts,
                               evidence(f'https://github.com/{repo}/releases/tag/{name}', repo + '@' + (tag.get('commit') or digest(payload)), payload),
                               release.get('published_at') or tag.get('time') or observed,
                               'published' if release.get('published_at') else 'tagged' if tag.get('time') else 'observed', 'official_repo', 'S6'))
    return items


def bound(url, repo):
    if not isinstance(url, str):
        return False
    url = url.removeprefix('git+')
    p = urlsplit(url)
    return p.scheme in {'https', 'git'} and p.hostname == 'github.com' and not p.username and p.path.rstrip('/').removesuffix('.git').lower() == '/' + repo.lower()


def registry(registry_name, value, previous, observed, binding_ref=None):
    is_pypi = registry_name == 'pypi'
    if registry_name not in {'pypi', 'npm'}:
        raise ValueError('unknown registry')
    package = 'ucp-sdk' if is_pypi else '@ucp-js/sdk'
    repo = ORG + ('/python-sdk' if is_pypi else '/js-sdk')
    if is_pypi:
        info = value.get('info', {})
        urls = (info.get('project_urls') or {}).values()
        if not info.get('project_urls') and binding_ref:
            # Explicit source link in the PyPI description plus the official
            # repository's pinned package manifest are both required.
            urls = re.findall(r'https://github\.com/Universal-Commerce-Protocol/python-sdk(?:\.git)?(?=[\s)\]\"<>]|$)', info.get('description') or '')
        correct_name = value.get('info', {}).get('name') == package
        versions = value.get('releases', {})
        tags = {'latest': value.get('info', {}).get('version')}
    else:
        repository = value.get('repository', {})
        urls = [repository.get('url') if isinstance(repository, dict) else repository]
        correct_name = value.get('name') == package
        versions = value.get('versions', {})
        tags = value.get('dist-tags', {})
    if not correct_name or not any(bound(url, repo) for url in urls):
        raise SourceError('registry package-to-repository binding failed')
    if not isinstance(versions, dict) or not versions:
        raise SourceError('registry returned no version mapping')
    if any(version not in versions for version in tags.values()):
        raise SourceError('registry dist-tag references absent version')
    prior = {r['subject']['version']: r for r in previous.values() if r['family'] == 'registry_version' and r['subject']['registry'] == registry_name}
    items = []
    for version in sorted(versions.keys() | prior.keys()):
        old = prior.get(version, {}).get('material', {})
        present = version in versions
        row = versions.get(version)
        if is_pypi and present:
            files = sorted([{'filename': f['filename'], 'sha256': f.get('digests', {}).get('sha256'),
                             'yanked': bool(f.get('yanked')), 'yanked_reason': f.get('yanked_reason'),
                             'uploaded_at': f.get('upload_time_iso_8601')} for f in row], key=lambda f: f['filename'])
            published = min((f['uploaded_at'] for f in files if f['uploaded_at']), default=None)
            yanked = bool(files) and all(f['yanked'] for f in files)
            deleted = not files
        elif present:
            if row.get('name') != package or row.get('version') != version:
                raise SourceError('npm version identity mismatch')
            vr = row.get('repository', value.get('repository', {}))
            if not bound(vr.get('url') if isinstance(vr, dict) else vr, repo):
                raise SourceError('npm version repository binding failed')
            dist = row.get('dist', {})
            files = [{'integrity': dist.get('integrity'), 'shasum': dist.get('shasum')}]
            if not any(files[0].values()):
                raise SourceError('npm distribution digest missing')
            published = value.get('time', {}).get(version)
            # npm deprecation is not an unpublish or a yank.
            files[0]['deprecated'] = row.get('deprecated')
            yanked, deleted = False, False
        else:
            files, published, yanked, deleted = old.get('files', []), old.get('published_at'), old.get('yanked', False), True
        payload = {'package': package, 'version': version, 'repo': repo, 'files': files, 'published_at': published,
                   'yanked': yanked, 'deleted': deleted, 'dist_tags': sorted(t for t, v in tags.items() if v == version)}
        if binding_ref and is_pypi:
            payload['binding_ref'] = binding_ref
        url = f'https://pypi.org/pypi/{package}/{version}/json' if is_pypi else 'https://registry.npmjs.org/@ucp-js%2fsdk/' + version
        items.append(candidate('registry_version', {'registry': registry_name, 'package': package, 'version': version}, payload,
                               {'package_published': present and not deleted, 'yanked': yanked, 'deleted': deleted},
                               evidence(url, registry_name + ':sha256:' + digest(payload), payload),
                               published or observed, 'published' if published else 'observed', 'official_registry', 'S7' if is_pypi else 'S8'))
    return items


def eligible(title, body, url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.hostname != 'shopify.dev' or p.username:
        return False
    text = title + '\n' + body
    if 'Universal Commerce Protocol' in text or re.search(r'\bdev\.ucp\.[a-zA-Z0-9_.-]+', text):
        return True
    # The acronym and authoritative URL must be within one sentence and 160 characters.
    return bool(re.search(r'\bUCP\b.{0,160}https://(?:www\.)?ucp\.dev(?:[/\s"<>]|$)|https://(?:www\.)?ucp\.dev/[^\s<>]*.{0,160}\bUCP\b', text))


def changelog(xml, observed):
    if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
        raise SourceError('XML declarations refused')
    root = ET.fromstring(xml)
    if root.tag != 'rss' or root.find('channel') is None:
        raise SourceError('expected RSS channel')
    items = []
    for node in root.findall('./channel/item'):
        title, body, url = (node.findtext(key, default='').strip() for key in ('title', 'description', 'link'))
        if not eligible(title, body, url):
            continue
        guid = node.findtext('guid') or url
        date = node.findtext('pubDate')
        try:
            published = stamp(parsedate_to_datetime(date)) if date else None
        except (ValueError, TypeError):
            raise SourceError('invalid RSS publication date') from None
        payload = {'guid': guid, 'title': title, 'body': body, 'url': url, 'published_at': published}
        items.append(candidate('changelog', {'guid': guid}, payload, {'notice_posted': True},
                               evidence(url, 'rss:sha256:' + digest(payload), payload, title),
                               published or observed, 'published' if published else 'observed', 'official_vendor', 'S10'))
    if len({i['event_id'] for i in items}) != len(items):
        raise SourceError('duplicate RSS identity')
    return items


class Secondary:
    def __init__(self, github):
        self.github, self.client = github, github.client

    def s4(self, previous, observed):
        ref = self.github.head(SPEC)
        return batch('S4', announcements(self.github.file(SPEC, ANNOUNCEMENTS, ref), ref, previous, observed))

    def s5(self, previous, observed):
        repo = ORG + '/.github'
        ref = self.github.head(repo)
        tree = self.client.json(self.github.url(repo, 'git/trees/' + ref + '?recursive=1'))
        if tree.get('truncated'):
            raise SourceError('truncated governance tree')
        paths = [e['path'] for e in tree['tree'] if e['type'] == 'blob' and
                 (e['path'].rsplit('/', 1)[-1].split('.')[0].upper() in {'GOVERNANCE', 'MAINTAINERS', 'TC_ELECTIONS'} or 'charter' in e['path'].lower())]
        if not paths:
            raise SourceError('no recognized governance files')
        files = {path: self.github.file(repo, path, ref) for path in paths}
        return batch('S5', governance(files, ref, previous, observed))

    def s6(self, previous, observed, since):
        items = []
        for repo in SDK_REPOS:
            items.extend(sdk_tags(repo, self.github.tags(repo), self.client.pages(self.github.url(repo, 'releases?per_page=100')), previous, observed))
            items.extend(self.github.prs(repo, since, observed, previous))
        return batch('S6', items)

    def s7(self, previous, observed):
        value = self.client.json('https://pypi.org/pypi/ucp-sdk/json')
        binding_ref = None
        if not value.get('info', {}).get('project_urls'):
            repo = ORG + '/python-sdk'
            head = self.github.head(repo)
            manifest = tomllib.loads(self.github.file(repo, 'pyproject.toml', head))
            if manifest.get('project', {}).get('name') != 'ucp-sdk':
                raise SourceError('official Python SDK manifest package identity mismatch')
            binding_ref = repo + '@' + head + ':pyproject.toml'
        return batch('S7', registry('pypi', value, previous, observed, binding_ref=binding_ref))

    def s8(self, previous, observed):
        return batch('S8', registry('npm', self.client.json('https://registry.npmjs.org/@ucp-js%2fsdk'), previous, observed))

    def s10(self, previous, observed):
        body, _ = self.client.get(FEED)
        return batch('S10', changelog(body.decode('utf-8'), observed))
