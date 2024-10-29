from pathlib import Path

from faker import Faker

fake = Faker()

day = "16/May/2023:00:03:15 +0000"


def fake_apps():
    return fake.random_element(
        elements=(
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/net.lutris.Lutris/x86_64/stable",
            ),
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/org.stellarium.Stellarium/x86_64/stable",
            ),
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/org.libretro.RetroArch/x86_64/stable",
            ),
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/org.x.Warpinator/x86_64/stable",
            ),
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/net.rpcs3.RPCS3/x86_64/stable",
            ),
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/net.pcsx2.PCSX2/x86_64/stable",
            ),
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/org.citra_emu.citra/x86_64/stable",
            ),
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/org.qgis.qgis/x86_64/stable",
            ),
            (
                "/repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock",
                "app/org.qgis.qgis/x86_64/stable",
            ),
            (
                "/repo/deltas/oe/6ouxwlSuSPUaySy1Mrm0giFJrK2Kh9HoQpfZBzitI-PQssorSbAXMJAjQ8vOWWDwq10hKxB2zz0R1UPSs_0b8/superblock",
                "app/org.mozilla.firefox/x86_64/stable",
            ),
        )
    )


def fake_ip() -> str:
    return fake.random_element(
        elements=(
            fake.ipv4(),
            fake.ipv6(),
        )
    )


def fake_user_agent() -> str:
    return fake.random_element(
        elements=(
            "libostree/2022.6 flatpak/1.12.4",
            "libostree/2020.8 flatpak/1.14.0",
            "libostree/2022.5 flatpak/1.12.8",
            "libostree/2022.2 flatpak/1.12.7",
            "libostree/2022.7 flatpak/1.14.4",
            "libostree/2022.1 flatpak/1.12.8",
            "libostree/2023.2 flatpak/1.15.4",
            "libostree/2023.1 flatpak/1.15.4",
        )
    )


def fake_is_update() -> str:
    return fake.random_element(
        elements=(
            "",
            "abcdefg",  # doesn't matter
        )
    )


def data_row() -> str:
    app = fake_apps()
    return f'{fake_ip()} "-" "-" [{day}] "GET {app[0]} HTTP/1.1" 200 {fake.random_number(digits=12)} "" "{fake_user_agent()}" "{app[1]}" "{fake_is_update()}" {fake.country_code()}'


Path("test").mkdir(parents=True, exist_ok=True)

# write to file
with open("test/test-data.log", "w") as f:
    for i in range(1000):
        f.write(data_row() + "\n")

print("done")
