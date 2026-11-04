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

What was changed: only the format. Each figure's lines are kept as in the source, with the Hipparcos star numbers replaced by positions in `stars.json`; names are the sources' English names (and native names where given). One Norse star (HIP 78727) isn't in the star list, so the line to it is left out. These sky cultures describe how other peoples saw the sky, as recorded by the contributors and the books and papers they cite; read the sources for the full stories and their context.
