#!/usr/bin/env python2

import time
import gzip, base64, binascii
import re, sys, gi
from gi.repository import GLib
import urllib2

# Indexes for log lines
CHECKSUM=0
DATE=1
REF=2
OSTREE_VERSION=3
FLATPAK_VERSION=4
IS_DELTA=5
IS_UPDATE=6

# 196.52.60.9 - - [30/Apr/2018:03:31:14 +0000] "GET /repo/deltas/c8/9hOBWniEuCUmvZGpmjoGNHqCrrlEoKxCTinfPDAOQ-Nf7zLm3IV8GxRH4W68kjhuUsXpIOOHZGUP1Rz8F4yuE/superblock HTTP/1.1" 200 9320 "-" "ostree libsoup/2.52.2" "-"
nginx_log_pat = (r''
                 '([\da-f.:]+)' #source
                 '\s-\s-\s'
                 '\[([^\]]+)\]\s' #datetime
                 '"(\w+)\s([^\s"]+)\s([^"]+)"\s' #path
                 '(\d+)\s' #status
                 '(\d+)\s' #size
                 '"([^"]*)"\s' #referrer
                 '"([^"]*)"\s' #user agent
                 '"([^"]*)"' #forwarded for
)
nginx_log_re = re.compile(nginx_log_pat)

# 2a03:a960:3:1:204:200:0:1003 "-" "-" [08/May/2018:11:07:26 +0000] "GET /repo/deltas/Lh/+60ySNnHW48IMvGVWv9oY_tZDGc2JYtf7rvKohoGY-uP7vHfq1pss_ojTPIK_1RgkYG6hklljVx5Vh6cNtroM/superblock HTTP/1.1" 200 1148 "" "ostree libsoup/2.52.2" ""
fastly_log_pat = (r''
                  '([\da-f.:]+)' #source
                  '\s"-"\s"-"\s'
                  '\[([^\]]+)\]\s' #datetime
                  '"(\w+)\s([^\s"]+)\s([^"]+)"\s' #path
                  '(\d+)\s' #status
                  '([^\s]+)\s' #size
                  '"([^"]*)"\s' #referrer
                  '"([^"]*)"\s' #user agent
                  '"([^"]*)"' #ref
)
fastly_log_re = re.compile(fastly_log_pat)

def deltaid_to_commit(deltaid):
    if deltaid:
        return binascii.hexlify(base64.b64decode(deltaid.replace("_", "/") + "=")).decode("utf-8")
    return None

def resolve_commit(commit):
    ref = None
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
    except:
        pass
    print ("Resolving %s -> %s" % (commit, ref))
    return ref

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

    target_ref_group = -1
    forwarded_for_group = -1
    l = nginx_log_re.match(first_line)
    if l:
        line_re = nginx_log_re
        forwarded_for_group = 10
    else:
        l = fastly_log_re.match(first_line)
        if l:
            line_re = fastly_log_re
            target_ref_group = 10
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

        # If forwarded-for is set we're probably looking at something the cdn sent, so ignore that as we
        # get that from the cdn logs
        if forwarded_for_group > 0:
            forwarded_for = l.group(forwarded_for_group)
            if len(forwarded_for) == 0:
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
        date = u"%d/%d/%d" % (date_struct.tm_year, date_struct.tm_mon,  date_struct.tm_mday)

        user_agent = l.group(9)

        uas = user_agent.split(" ")
        ostree_version = u"2017.15" # This is the last version that didn't list version
        flatpak_version = None
        for ua in uas:
            if ua.startswith("libostree/"):
                ostree_version = ua[10:]
            if ua.startswith("flatpak/"):
                flatpak_version = ua[8:]

        target_ref = None
        if target_ref_group > 0:
            target_ref = l.group(target_ref_group)
            if len(target_ref) == 0:
                target_ref = None

        is_update = is_delta # TODO: Get this from extra header
        download = (commit, date, target_ref, ostree_version, flatpak_version, is_delta, is_update)
        downloads.append(download)
    return downloads

if __name__ == "__main__":
    logs = []
    for logname in sys.argv[1:]:
        log = parse_log(logname)
        logs = logs + log
    for l in logs:
        print l
