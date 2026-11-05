# The night sky (`sky/`)

These files are not mine either; each keeps the licence of where it came from.

| File | What | Source | Licence |
|---|---|---|---|
| `stars.json` | 2,896 stars: everything brighter than magnitude 5.5, plus every star a figure below uses (right ascension, declination J2000, magnitude, B–V colour) | [HYG database v4.1](https://github.com/astronexus/HYG-Database), David Nash (astronexus.com) | CC BY-SA 4.0 |
| `western.json` | 88 figures | [Stellarium sky cultures: western](https://github.com/Stellarium/stellarium-skycultures/tree/master/western), Stellarium team | CC BY-SA |
| `norse.json` | 6 figures | [Stellarium: norse](https://github.com/Stellarium/stellarium-skycultures/tree/master/norse), Jonas Persson | CC BY-SA |
| `egyptian.json` | 28 figures | [Stellarium: egyptian](https://github.com/Stellarium/stellarium-skycultures/tree/master/egyptian), Karrie Berglund (Digitalis Education Solutions), after “A Map of the Ancient Egyptian Firmament” | GNU GPL v2.0 |
| `navajo.json` | 8 figures | [Stellarium: navajo](https://github.com/Stellarium/stellarium-skycultures/tree/master/navajo), Karrie Berglund (Digitalis Education Solutions), after *Star Trails-Navajo* | GNU GPL v2.0 |
| `blackfoot.json` | 4 figures | [Stellarium: blackfoot](https://github.com/Stellarium/stellarium-skycultures/tree/master/blackfoot), Doina Bucur | CC BY-SA |
| `chinese.json` | 312 figures | [Karrie Berglund (Digitalis Education Solutions) and Sun Shuwei, text rework by the Stellarium team; based on Hong Kong Space Museum star maps and Yi Shitong's star catalogue](https://github.com/Stellarium/stellarium-skycultures/tree/master/chinese) | CC BY-SA |
| `arabic_lunar_stations.json` | 51 figures | [Khalid al-Ajaji, for Stellarium](https://github.com/Stellarium/stellarium-skycultures/tree/master/arabic_lunar_stations) | CC BY-ND 4.0 |
| `hawaiian_starlines.json` | 13 figures | [Darren Kamalu, Christopher Blake and the Celestial Navigation class at Kamehameha Schools Kapalama; artwork by Kealoha Kaneakua; reworked by Susanne M Hoffmann](https://github.com/Stellarium/stellarium-skycultures/tree/master/hawaiian_starlines) | CC BY-SA |
| `inuit.json` | 11 figures | [Karrie Berglund (Digitalis Education Solutions), based on 'The Arctic Sky' by John MacDonald; illustrations by Johan Meuris; edited by Susanne M Hoffmann and the Stellarium team](https://github.com/Stellarium/stellarium-skycultures/tree/master/inuit) | GNU GPL v2.0 |
| `aztec.json` | 5 figures | [Enrique Gomez Candelario; English translation by Rafael Rojas Segoviano; rework by the Stellarium team](https://github.com/Stellarium/stellarium-skycultures/tree/master/aztec) | GNU GPL v2.0 |
| `sami.json` | 10 figures | [Jonas Persson; technical rework by Susanne M Hoffmann](https://github.com/Stellarium/stellarium-skycultures/tree/master/sami) | CC BY-SA |

What was changed: only the format. Each figure's lines are kept as in the source, with the Hipparcos star numbers replaced by positions in `stars.json`; names are the sources' English names (and native names where given). The six cultures added on 5 Nov 2026 (Chinese, Arabic lunar stations, Hawaiian, Inuit, Aztec, Sami) use 207 stars that were not already in the list; those were appended to `stars.json` (from HYG v4.1, same source and licence). Three Chinese figure stars were missing from HYG and left out of their segments. One Norse star (HIP 78727) isn't in the star list, so the line to it is left out. These sky cultures describe how other peoples saw the sky, as recorded by the contributors and the books and papers they cite; read the sources for the full stories and their context.
