#!/usr/bin/env python2

import time
import gzip, base64, binascii, json
import re, sys, gi
from gi.repository import GLib
import urllib2

def load_cache(path):
    commit_map = {}
    try:
        f = open(path, 'r')
        commit_map = json.loads(f.read())
    except:
        pass

    return CommitCache(commit_map)

class CommitCache:
    def __init__(self, commit_map):
        self.commit_map = commit_map
        self.modified = False

        # Backwards compat, re-resolve all commits where we don't have root dirtree info
        for commit, cached_data in self.commit_map.items():
            if not isinstance(cached_data, list):
                self.update_for_commit(commit, cached_data)

    def update_for_commit(self, commit, known_branch = None):
        ref = known_branch
        root_dirtree = None
        url = "https://dl.flathub.org/repo/objects/%s/%s.commit" % (commit[0:2], commit[2:])
        try:
            response = urllib2.urlopen(url)
            commitv = response.read()
            if commitv:
                v = GLib.Variant.new_from_bytes(GLib.VariantType.new("(a{sv}aya(say)sstayay)"), GLib.Bytes.new(commitv), False)
                if "xa.ref" in v[0]:
                    ref = v[0]["xa.ref"]
                elif "ostree.ref-binding" in v[0]:
                    ref = v[0]["ostree.ref-binding"][0]
                root_dirtree = binascii.hexlify(bytearray(v[6]))
        except:
            pass
        print ("Resolving %s -> %s, %s" % (commit, ref, root_dirtree))
        self.modified = True
        self.commit_map[commit] = [ref, root_dirtree]

    def has_commit(self, commit):
        return commit in self.commit_map

    def lookup_ref(self, commit):
        if commit in self.commit_map:
            return self.commit_map[commit][0]
        return None

    def save(self, path):
        if self.modified:
            try:
                f = open(path, 'w')
                json.dump(self.commit_map, f)
                f.close()
            except:
                pass
            self.modified = False

# Indexes for log lines
CHECKSUM=0
DATE=1
REF=2
OSTREE_VERSION=3
FLATPAK_VERSION=4
IS_DELTA=5
IS_UPDATE=6
COUNTRY=7

# 151.100.102.134 "-" "-" [05/Jun/2018:10:01:16 +0000] "GET /repo/objects/ca/717a9f713291670035f228520523cdea82811eb34521b58b7eea6d5f9e4085.filez HTTP/1.1" 200 822627 "" "libostree/2018.5 flatpak/0.11.7" "runtime/org.freedesktop.Sdk/x86_64/1.6" "" IT
fastly_log_pat = (r''
                  ' ?' # allow leading space in syslog message per RFC3164
                  '([\da-f.:]+)' #source
                  '\s"-"\s"-"\s'
                  '\[([^\]]+)\]\s' #datetime
                  '"(\w+)\s([^\s"]+)\s([^"]+)"\s' #path
                  '(\d+)\s' #status
                  '([^\s]+)\s' #size
                  '"([^"]*)"\s' #referrer
                  '"([^"]*)"\s' #user agent
                  '"([^"]*)"\s' #ref
                  '"([^"]*)"\s' #update_from
                  '(\w+)' #update_from
)
fastly_log_re = re.compile(fastly_log_pat)

def deltaid_to_commit(deltaid):
    if deltaid:
        return binascii.hexlify(base64.b64decode(deltaid.replace("_", "/") + "=")).decode("utf-8")
    return None

def parse_log(logname):
    print ("loading log %s" % (logname))
    if logname.endswith(".gz"):
        log_file = gzip.open(logname, 'rb')
    else:
        log_file = open(logname, 'r')

    # detect log type
    first_line = log_file.readline().decode("utf-8")
    if first_line == "":
        return []

    l = fastly_log_re.match(first_line)
    if l:
        line_re = fastly_log_re
    else:
        raise Exception('Unknown log format')

    downloads = []

    while True:
        if first_line:
            line = first_line
            first_line = None
        else:
            line = log_file.readline().decode("utf-8")
        if line == "":
            break
        l = line_re.match(line)
        if not l:
            sys.stderr.write("Warning: Can't match line: %s\n" % (line[:-1]))
            continue
        op = l.group(3)
        result = l.group(6)
        path = l.group(4)
        if op != "GET" or result != "200":
            continue
        if not (path.startswith("/repo/deltas/") and path.endswith("/superblock")):
            continue

        delta = path[len("/repo/deltas/"):-len("/superblock")].replace("/", "")
        is_delta = False
        if delta.find("-") != -1:
            is_delta = True
            source = delta[:delta.find("-")]
            target = delta[delta.find("-")+1:]
        else:
            source = None
            target = delta

        commit = deltaid_to_commit(target)

        date_str = l.group(2)
        if (not date_str.endswith(" +0000")):
            sys.stderr.write("Unhandled date timezone: %s\n" % (date_str))
            continue
        date_str = date_str[:-6]
        date_struct = time.strptime(date_str, '%d/%b/%Y:%H:%M:%S')
        date = u"%d/%02d/%02d" % (date_struct.tm_year, date_struct.tm_mon,  date_struct.tm_mday)

        user_agent = l.group(9)

        uas = user_agent.split(" ")
        ostree_version = u"2017.15" # This is the last version that didn't list version
        flatpak_version = None
        for ua in uas:
            if ua.startswith("libostree/"):
                ostree_version = ua[10:]
            if ua.startswith("flatpak/"):
                flatpak_version = ua[8:]

        target_ref = l.group(10)
        if len(target_ref) == 0:
            target_ref = None

        update_from = l.group(11)
        if len(update_from) == 0:
            update_from = None

        country = l.group(12)

        is_update = is_delta or update_from
        download = (commit, date, target_ref, ostree_version, flatpak_version, is_delta, is_update, country)
        downloads.append(download)
    return downloads

if __name__ == "__main__":
    logs = []
    for logname in sys.argv[1:]:
        log = parse_log(logname)
        logs = logs + log
    for l in logs:
        print l
