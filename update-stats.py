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
        try:
            arch = parts[2]
        except IndexError:
            arch = "x86_64"
        old = vars(self).get(arch, (0, 0))
        downloads = old[0] + 1
        updates = old[1]
        if is_update:
            updates = updates + 1
        vars(self)[arch] = (downloads, updates)

    def from_dict(self, dct):
        for i in dct:
            vars(self)[i] = dct[i]


class RefCountryInfo:
    def __init__(self):
        pass

    def add(self, is_update: bool, country: str):
        old_country = vars(self).get(country, (0, 0))
        downloads_country = old_country[0] + 1
        updates_country = old_country[1]
        if is_update:
            updates_country = updates_country + 1

        vars(self)[country] = (downloads_country, updates_country)

    def from_dict(self, dct):
        for i in dct:
            vars(self)[i] = dct[i]


class RefOsVersionInfo:
    def __init__(self):
        pass

    def add(self, is_update: bool, os_version: str):
        old_os_version = vars(self).get(os_version, (0, 0))
        downloads_os_version = old_os_version[0] + 1
        updates_os_version = old_os_version[1]
        if is_update:
            updates_os_version = updates_os_version + 1

        vars(self)[os_version] = (downloads_os_version, updates_os_version)

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
        self.ref_by_country = {}
        self.os_versions = {}
        self.ref_by_os_version = {}
        self.os_flatpak_versions = {}

    def from_dict(self, dct):
        self.countries = dct.get("countries", {})
        self.downloads = dct["downloads"]
        self.updates = dct["updates"]
        self.delta_downloads = dct["delta_downloads"]
        self.ostree_versions = dct["ostree_versions"]
        self.flatpak_versions = dct["flatpak_versions"]
        self.os_versions = dct.get("os_versions", {})
        refs = dct["refs"]
        for id in refs:
            ri = self.get_ref_info(id)
            ri.from_dict(refs[id])
        ref_by_country = dct.get("ref_by_country", {})
        for id in ref_by_country:
            ri = self.get_ref_country_info(id)
            ri.from_dict(ref_by_country[id])
        ref_by_os_version = dct.get("ref_by_os_version", {})
        for id in ref_by_os_version:
            ri = self.get_ref_os_version_info(id)
            ri.from_dict(ref_by_os_version[id])
        self.os_flatpak_versions = dct.get("os_flatpak_versions", {})

    def get_ref_info(self, id):
        if id not in self.refs:
            self.refs[id] = RefInfo()
        return self.refs[id]

    def get_ref_country_info(self, id):
        if id not in self.ref_by_country:
            self.ref_by_country[id] = RefCountryInfo()
        return self.ref_by_country[id]

    def get_ref_os_version_info(self, id):
        if id not in self.ref_by_os_version:
            self.ref_by_os_version[id] = RefOsVersionInfo()
        return self.ref_by_os_version[id]

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
            ri = self.get_ref_country_info(id)
            ri.add(download[flathub.IS_UPDATE], country)
            self.countries[country] = self.countries.get(country, 0) + 1

        os_version = download[flathub.OS_VERSION]
        if os_version:
            self.os_versions[os_version] = self.os_versions.get(os_version, 0) + 1
            ri = self.get_ref_os_version_info(id)
            ri.add(download[flathub.IS_UPDATE], os_version)

        if os_version and flatpak_version:
            if os_version not in self.os_flatpak_versions:
                self.os_flatpak_versions[os_version] = {}
            self.os_flatpak_versions[os_version][flatpak_version] = (
                self.os_flatpak_versions[os_version].get(flatpak_version, 0) + 1
            )


def load_dayinfo(dest, date) -> DayInfo:
    day = DayInfo(date)
    path = os.path.join(dest, date + ".json")
    if os.path.exists(path):
        with open(path) as day_f:
            dct = json.loads(day_f.read())
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
    day = days.get(date)
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
    print(f"saving updated stats {path}")
    with open(path, "w") as f:
        json.dump(day, f, default=lambda x: x.__dict__, sort_keys=True, indent=4)
