#!/usr/bin/env python3

import base64
import binascii
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from gi.repository import GLib


def load_cache(path):
    commit_map = {}
    try:
        print(f"Loading cache from {path}")
        with open(path) as f:
            commit_map = json.loads(f.read())
    except OSError:
        print("Failed to load cache")
        pass

    return CommitCache(commit_map)


class CommitCache:
    def __init__(self, commit_map):
        self.commit_map: dict[str, list[str | None]] = commit_map
        self.dirtree_map: dict[str | None] = {}
        self.modified = False

        # Backwards compat, re-resolve all commits where we don't have root dirtree info
        # Also remove uninteresting things from the cache
        for commit, cached_data in list(self.commit_map.items()):
            if not isinstance(cached_data, list):
                ref = cached_data
                # Older version saved uninteresting refs in the cache, but we don't need them anymore
                if ref and should_keep_ref(ref):
                    self.update_for_commit(commit, ref)
                else:
                    del self.commit_map[commit]

        for commit, cached_data in list(self.commit_map.items()):
            dirtree = cached_data[1]
            if dirtree:
                self.dirtree_map[dirtree] = commit

        self.summary_map = {}
        url = "https://dl.flathub.org/repo/summary"
        try:
            response = urllib.request.urlopen(url)
            summaryv = response.read()
            if summaryv:
                v = GLib.Variant.new_from_bytes(
                    GLib.VariantType.new("(a(s(taya{sv}))a{sv})"),
                    GLib.Bytes.new(summaryv),
                    False,
                )
                for m in v[0]:
                    self.summary_map[m[0]] = binascii.hexlify(
                        bytearray(m[1][1])
                    ).decode("utf-8")
        except OSError:
            print("Failed to load summary: ")
            print(sys.exc_info())
            pass

    def update_from_summary(self, branch: str):
        commit = self.summary_map.get(branch, None)
        if commit and not self.has_commit(commit):
            self.update_for_commit(commit, branch)

    def update_for_commit(self, commit: str | None, known_branch: str | None = None):
        ref = known_branch
        root_dirtree = None
        url = f"https://dl.flathub.org/repo/objects/{commit[0:2]}/{commit[2:]}.commit"
        print(f"Resolving {commit}", end=" ")
        try:
            response = urllib.request.urlopen(url)
            commitv = response.read()
            if commitv:
                v = GLib.Variant.new_from_bytes(
                    GLib.VariantType.new("(a{sv}aya(say)sstayay)"),
                    GLib.Bytes.new(commitv),
                    False,
                )
                if "xa.ref" in v[0]:
                    ref = v[0]["xa.ref"]
                elif "ostree.ref-binding" in v[0]:
                    ref = v[0]["ostree.ref-binding"][0]
                root_dirtree = binascii.hexlify(bytearray(v[6])).decode("utf-8")
        except OSError:
            print("Failed to resolve commit")
            pass
        print(f"-> {ref}, {root_dirtree}")
        self.modified = True
        self.commit_map[commit] = [ref, root_dirtree]
        if root_dirtree:
            self.dirtree_map[root_dirtree] = commit

    def has_commit(self, commit):
        return commit in self.commit_map

    def lookup_ref(self, commit):
        pair = self.commit_map.get(commit, None)
        if pair:
            return pair[0]

    def lookup_by_dirtree(self, dirtree) -> str | None:
        return self.dirtree_map.get(dirtree, None)

    def save(self, path):
        if self.modified:
            try:
                with open(path, "w") as f:
                    json.dump(self.commit_map, f, indent=4)
            except OSError:
                print("Failed to save cache")
                pass
            self.modified = False


# Indexes for log lines
CHECKSUM = 0
DATE = 1
REF = 2
OSTREE_VERSION = 3
FLATPAK_VERSION = 4
IS_DELTA = 5
IS_UPDATE = 6
COUNTRY = 7
OS_ID = 8
OS_VERSION = 9

# 151.100.102.134 "-" "-" [05/Jun/2018:10:01:16 +0000] "GET /repo/objects/ca/717a9f713291670035f228520523cdea82811eb34521b58b7eea6d5f9e4085.filez HTTP/1.1" 200 822627 "" "libostree/2018.5 flatpak/0.11.7" "runtime/org.freedesktop.Sdk/x86_64/1.6" "" IT
fastly_log_pat = (
    r""
    " ?"  # allow leading space in syslog message per RFC3164
    "([\\da-f.:]+)"  # source
    '\\s"-"\\s"-"\\s'
    "\\[([^\\]]+)\\]\\s"  # datetime
    '"(\\w+)\\s([^\\s"]+)\\s([^"]+)"\\s'  # path
    "(\\d+)\\s"  # status
    "([^\\s]+)\\s"  # size
    '"([^"]*)"\\s'  # referrer
    '"([^"]*)"\\s'  # user agent
    '"([^"]*)"\\s'  # ref
    '"([^"]*)"\\s'  # update_from
    "(\\w+)"  # country
    '(?:\\s"([^"]*)")?'  # os_info (optional)
)
fastly_log_re = re.compile(fastly_log_pat)


def deltaid_to_commit(deltaid: str) -> str | None:
    try:
        if deltaid:
            return binascii.hexlify(
                base64.b64decode(deltaid.replace("_", "/") + "=")
            ).decode("utf-8")
    except binascii.Error:
        pass

    return None


def should_keep_ref(ref: str) -> bool:
    parts = ref.split("/")
    if parts[0] == "app":
        return True
    return bool(
        parts[0] == "runtime"
        and not (
            parts[1].endswith(".Debug")
            or parts[1].endswith(".Locale")
            or parts[1].endswith(".Sources")
        )
    )


def parse_log(logname: str, cache: CommitCache, ignore_deltas=False):
    print(f"loading log {logname}")

    downloads = []

    with (
        gzip.open(logname, "rb") if logname.endswith(".gz") else open(logname)
    ) as log_file:
        # detect log type
        try:
            first_line = log_file.readline()
        except UnicodeDecodeError:
            print(f"Skipping undecodable first line in {logname}")
            first_line = ""

        if first_line == "":
            return []

        match = fastly_log_re.match(first_line)
        if match:
            line_re = fastly_log_re
        else:
            raise Exception("Unknown log format")

        while True:
            if first_line:
                line = first_line
                first_line = None
            else:
                try:
                    line = log_file.readline()
                except UnicodeDecodeError:
                    print(f"Skipping undecodable line in {logname}")
                    continue

            if line == "":
                break
            match = line_re.match(line)
            if not match:
                sys.stderr.write(f"Warning: Can't match line: {line[:-1]}\n")
                continue
            op = match.group(3)
            result = match.group(6)
            path = match.group(4)
            if op != "GET" or result != "200":
                continue

            target_ref: str = match.group(10)
            if len(target_ref) == 0:
                target_ref = None

            # Early bailout for uninteresting refs (like locales) to keep work down
            if target_ref is not None and not should_keep_ref(target_ref):
                continue

            # Ensure we have (at least) the current HEAD for this branch cached.
            # We need this to have any chance to map a dirtree object to the
            # corresponding ref, because unless we saw the commit id for some
            # other reason before we will not have resolved it so we can do
            # the reverse lookup.
            if target_ref:
                cache.update_from_summary(target_ref)

            is_delta = False
            if path.startswith("/repo/deltas/") and path.endswith("/superblock"):
                if ignore_deltas:
                    continue
                delta = path[len("/repo/deltas/") : -len("/superblock")].replace(
                    "/", ""
                )
                if delta.find("-") != -1:
                    is_delta = True
                    delta[: delta.find("-")]
                    target = delta[delta.find("-") + 1 :]
                else:
                    target = delta

                commit = deltaid_to_commit(target)
                if not commit:
                    continue

            elif path.startswith("/repo/objects/") and path.endswith(".dirtree"):
                dirtree = path[len("/repo/objects/") : -len(".dirtree")].replace(
                    "/", ""
                )
                # Look up via the reverse map for all the commits we've seen so far
                commit = cache.lookup_by_dirtree(dirtree)
                if not commit:
                    continue  # No match, probably not a root dirtree (although could be commit we never saw before)
            else:
                # Some other kind of log line, ignore
                continue

            # Maybe this is a new commit, if so cache it for future use
            if not cache.has_commit(commit):
                cache.update_for_commit(commit, target_ref)

            # Some log entries have no ref specified, if so look it up via the cache
            if not target_ref:
                target_ref = cache.lookup_ref(commit)

            if not target_ref:
                print("Unable to figure out ref for commit " + str(commit))
                continue

            # Late bailout, as we're now sure of the ref
            if not should_keep_ref(target_ref):
                continue

            date_str = match.group(2)
            if not date_str.endswith(" +0000"):
                sys.stderr.write(f"Unhandled date timezone: {date_str}\n")
                continue
            date_str = date_str[:-6]
            date_struct = time.strptime(date_str, "%d/%b/%Y:%H:%M:%S")
            date = f"{date_struct.tm_year}/{date_struct.tm_mon:02d}/{date_struct.tm_mday:02d}"

            user_agent = match.group(9)

            uas = user_agent.split(" ")
            ostree_version = (
                "2017.15"  # This is the last version that didn't list version
            )
            flatpak_version = None
            for ua in uas:
                if ua.startswith("libostree/"):
                    ostree_version = ua[10:]
                if ua.startswith("flatpak/"):
                    flatpak_version = ua[8:]

            update_from = match.group(11)
            if len(update_from) == 0:
                update_from = None

            country = match.group(12)

            os_info = match.group(13)
            os_id = None
            os_version = None
            if os_info and len(os_info) > 0:
                parts = os_info.split(";")
                if len(parts) >= 2:
                    os_id = parts[0]
                    os_version = f"{parts[0]};{parts[1]}"

            is_update = is_delta or update_from
            download = (
                commit,
                date,
                target_ref,
                ostree_version,
                flatpak_version,
                is_delta,
                is_update,
                country,
                os_id,
                os_version,
            )
            downloads.append(download)

    return downloads


if __name__ == "__main__":
    logs = []
    for logname in sys.argv[1:]:
        log = parse_log(logname, CommitCache({}))
        logs = logs + log
    for log in logs:
        print(log)
