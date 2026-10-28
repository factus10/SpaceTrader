# Sector table

Generated from `data/systems.json` by `tools/build_sector_data.py`. Do not edit by hand.

`Idx` doubles as the ECM art image index. Law level drives both the encounter table
and customs inspection odds; goods with a law threshold below a system's law level
are contraband there.

| Idx | System | Hex | TL | Law | Government | Pop | Exports | Imports |
|----:|--------|:---:|---:|----:|------------|----:|---------|---------|
| 1 | Coriolis Gate | 2,4 | 15 | 8 | Bureaucracy | 13 | ELEC MACH | ORE FOOD |
| 2 | Meridian | 1,6 | 14 | 9 | Impersonal Bureaucracy | 12 | MED ELEC | ORE TEXT |
| 3 | Verity | 3,2 | 14 | 7 | Feudal Technocracy | 10 | MACH ELEC | ORE FOOD TEXT |
| 4 | Tessellate | 2,8 | 13 | 6 | Religious Autocracy | 8 | LUX | FOOD TEXT MED |
| 5 | Aldebar Prime | 3,6 | 13 | 6 | Representative Democracy | 14 | ELEC WEAP MACH | ORE FOOD |
| 6 | Junction Nine | 5,4 | 10 | 5 | Representative Democracy | 9 | MACH | FOOD LUX |
| 7 | Hollow Sky | 4,7 | 8 | 4 | Participating Democracy | 10 | FOOD TEXT | MACH MED |
| 8 | Kestrel | 6,8 | 9 | 5 | Feudal Technocracy | 9 | FOOD | ELEC MACH |
| 9 | Ambergris | 5,2 | 11 | 4 | Charismatic Dictatorship | 7 | LUX TEXT | FOOD MACH |
| 10 | Tannhauser | 7,5 | 11 | 5 | Representative Democracy | 11 | ELEC MACH | ORE FOOD |
| 11 | Fenwick | 6,3 | 8 | 3 | Clan Holding | 6 | ORE | FOOD MED MACH |
| 12 | Pellucid | 4,5 | 12 | 6 | Impersonal Bureaucracy | 5 | MED ELEC | FOOD TEXT LUX |
| 13 | Sable Run | 8,7 | 9 | 3 | Participating Democracy | 7 | TEXT | ELEC MED |
| 14 | Rust Harbour | 10,5 | 6 | 1 | Anarchy | 6 | ORE WEAP | FOOD MED ELEC |
| 15 | Cinder | 9,3 | 5 | 2 | Company Rule | 4 | ORE | FOOD MED MACH |
| 16 | Vagrant | 12,6 | 6 | 0 | Anarchy | 5 | WEAP LUX | FOOD MED MACH |
| 17 | Ossuary | 13,3 | 4 | 1 | Company Rule | 3 | ORE WEAP | FOOD MED TEXT |
| 18 | Longshot | 9,7 | 5 | 2 | Clan Holding | 5 | ORE FOOD | ELEC MACH MED |
| 19 | Threadbare | 11,8 | 4 | 3 | Participating Democracy | 6 | FOOD TEXT | ELEC MACH MED |
| 20 | Kalideen | 11,2 | 7 | 2 | Clan Holding | 5 | ORE TEXT | ELEC WEAP MED |

## Trade goods

| ID | Good | Abbr | Base price | Law threshold |
|---:|------|------|-----------:|--------------:|
| 0 | Foodstuffs | FOOD | 20 | — |
| 1 | Ore | ORE | 35 | — |
| 2 | Textiles | TEXT | 45 | — |
| 3 | Medical Supplies | MED | 90 | 7 |
| 4 | Electronics | ELEC | 140 | 6 |
| 5 | Weapons | WEAP | 180 | 4 |
| 6 | Machinery | MACH | 110 | — |
| 7 | Luxuries | LUX | 250 | 5 |

A law threshold of — means the good is legal everywhere. Otherwise the good is
contraband in any system whose law level exceeds the threshold: Weapons (4) are
illegal across the whole core and most of the middle band, which is what makes the
frontier free ports worth the risk.
