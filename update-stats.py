#!/usr/bin/env python3

import argparse
import json
import os.path

import flathub

refs_cache = None


def ref_to_id(ref: str) -> str | None:
    parts = ref.split("/")
    if parts[0] == "app":
        return parts[1]
    if parts[0] == "runtime" and not (
        parts[1].endswith(".Debug")
        or parts[1].endswith(".Locale")
        or parts[1].endswith(".Sources")
    ):
        return f"{parts[1]}/{parts[3]}"
    return None


class RefInfo:
    def __init__(self):
        pass

    def add(self, ref: str, is_update: bool):
        parts = ref.split("/")
        arch = parts[2]
        old = vars(self).get(arch, (0, 0))
        downloads = old[0] + 1
        updates = old[1]
        if is_update:
            updates = updates + 1
        vars(self)[arch] = (downloads, updates)

    def from_dict(self, dct):
        for i in dct:
            vars(self)[i] = dct[i]


class DayInfo:
    def __init__(self, date):
        self.date = date
        self.downloads = 0
        self.updates = 0
        self.delta_downloads = 0
        self.ostree_versions = {}
        self.flatpak_versions = {}
        self.refs = {}
        self.countries = {}

    def from_dict(self, dct):
        self.countries = dct.get("countries", {})
        self.downloads = dct["downloads"]
        self.updates = dct["updates"]
        self.delta_downloads = dct["delta_downloads"]
        self.ostree_versions = dct["ostree_versions"]
        self.flatpak_versions = dct["flatpak_versions"]
        refs = dct["refs"]
        for id in refs:
            ri = self.get_ref_info(id)
            ri.from_dict(refs[id])

    def get_ref_info(self, id):
        if id not in self.refs:
            self.refs[id] = RefInfo()
        return self.refs[id]

    def add(self, download):
        download[flathub.CHECKSUM]
        ref = download[flathub.REF]

        if not ref:
            return

        id = ref_to_id(ref)
        if not id:
            return

        ri = self.get_ref_info(id)
        ri.add(ref, download[flathub.IS_UPDATE])

        self.downloads = self.downloads + 1
        if download[flathub.IS_DELTA]:
            self.delta_downloads = self.delta_downloads + 1
        if download[flathub.IS_UPDATE]:
            self.updates = self.updates + 1

        ostree_version = download[flathub.OSTREE_VERSION]
        self.ostree_versions[ostree_version] = (
            self.ostree_versions.get(ostree_version, 0) + 1
        )

        flatpak_version = download[flathub.FLATPAK_VERSION]
        if flatpak_version:
            self.flatpak_versions[flatpak_version] = (
                self.flatpak_versions.get(flatpak_version, 0) + 1
            )

        country = download[flathub.COUNTRY]
        if country:
            self.countries[country] = self.countries.get(country, 0) + 1


def load_dayinfo(dest, date) -> DayInfo:
    day = DayInfo(date)
    path = os.path.join(dest, date + ".json")
    if os.path.exists(path):
        day_f = open(path)
        dct = json.loads(day_f.read())
        day_f.close()
        day = DayInfo(dct["date"])
        day.from_dict(dct)
    return day


parser = argparse.ArgumentParser()
parser.add_argument("--dest", type=str, help="path to destination dir", default="stats")
parser.add_argument(
    "--ref-cache",
    type=str,
    dest="ref_cache_path",
    metavar="REFCACHE",
    default="ref-cache.json",
    help="path to ref-cache.json",
)
parser.add_argument(
    "--ignore-deltas", action="store_true", help="ignore deltas in the log"
)
parser.add_argument(
    "logfiles", metavar="LOGFILE", type=str, help="path to log file", nargs="+"
)
args = parser.parse_args()

refs_cache = flathub.load_cache(args.ref_cache_path)

downloads = []
for logname in args.logfiles:
    d = flathub.parse_log(logname, refs_cache, args.ignore_deltas)
    downloads = downloads + d

refs_cache.save(args.ref_cache_path)

days = {}

for d in downloads:
    date = d[flathub.DATE]
    day = days.get(date, None)
    if not day:
        day = load_dayinfo(args.dest, date)
        days[date] = day
    day.add(d)

for date in days:
    day = days[date]
    path = os.path.join(args.dest, date + ".json")
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory, 0o755)
    print("saving updated stats %s" % (path))
    f = open(path, "w")
    json.dump(day, f, default=lambda x: x.__dict__, sort_keys=True, indent=4)
    f.close()
