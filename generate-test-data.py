# 73.97.123.190 "-" "-" [16/May/2023:00:03:15 +0000] "GET /repo/objects/b2/c8c6a483f1b614ab10f9a608ed128d085799f1480cbb09b7449dbc06730db3.dirtree HTTP/1.1" 200 115 "" "libostree/2022.6 flatpak/1.12.4" "app/org.libretro.RetroArch/x86_64/stable" "" US

from faker import Faker

fake = Faker()

day = "16/May/2023:00:03:15 +0000"


def fake_apps() -> str:
    return fake.random_element(
        elements=(
            "app/net.lutris.Lutris/x86_64/stable",
            "app/org.stellarium.Stellarium/x86_64/stable",
            "app/org.libretro.RetroArch/x86_64/stable",
            "app/org.x.Warpinator/x86_64/stable",
            "app/net.rpcs3.RPCS3/x86_64/stable",
            "app/net.pcsx2.PCSX2/x86_64/stable",
            "app/org.citra_emu.citra/x86_64/stable",
            "app/org.qgis.qgis/x86_64/stable",
        )
    )


def fake_ip() -> str:
    return fake.random_element(
        elements=(
            fake.ipv4(),
            fake.ipv6(),
        )
    )


def data_row() -> str:
    return f'{fake_ip()} "-" "-" [{day}] "GET /repo/deltas/p1/IypJ6rKkrBepGnmgBqfxTzTjJYU64QcY1VsZH2Z6Y/superblock HTTP/1.1" 200 {fake.random_number(digits=12)} "" "libostree/2022.6 flatpak/1.12.4" "{fake_apps()}" "" {fake.country_code()}'


# write to file
with open("test/test-data.log", "w") as f:
    for i in range(1000):
        f.write(data_row() + "\n")

print("done")
