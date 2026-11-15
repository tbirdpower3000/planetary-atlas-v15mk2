#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression test for the Solar energy readout (solarBlock) in index.html.

solarBlock() lives inside the page's closure, so this test extracts the data it
reads -- the SOLAR_AU (distance/eccentricity), SOLAR_A (Bond albedo) and
SOLAR_CONST / SB_SIGMA constants -- and recomputes the same quantities the
readout shows (flux in W/m^2, % of Earth, equilibrium temperature, overhead-sun
/ subsolar temperature), checking them against known values. It guards against a
drift in the tables, the solar constant, or the temperature formula.

Pure standard library. Exit code 1 on any failed check.
"""
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
s = io.open(ROOT / "index.html", encoding="utf-8").read()


def _block(name):
    m = re.search(r"const " + name + r"\s*=\s*\{(.*?)\};", s, re.S)
    if not m:
        sys.exit("FAIL: could not find " + name + " in index.html")
    # strip // line comments so values inside them are not parsed
    return re.sub(r"//[^\n]*", "", m.group(1))


AU = {k: (float(a), float(e)) for k, a, e in
      re.findall(r"(\w+):\s*\[\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\]", _block("SOLAR_AU"))}
ALB = {k: float(v) for k, v in re.findall(r"(\w+):\s*([0-9.]+)", _block("SOLAR_A"))}

m = re.search(r"SOLAR_CONST\s*=\s*([0-9.]+)", s)
S0 = float(m.group(1)) if m else sys.exit("FAIL: SOLAR_CONST not found")
m = re.search(r"SB_SIGMA\s*=\s*([0-9.eE+-]+)", s)
SIG = float(m.group(1)) if m else sys.exit("FAIL: SB_SIGMA not found")


def flux(k):
    a = AU[k][0]
    return S0 / (a * a)


def pct_earth(k):
    a = AU[k][0]
    return 100.0 / (a * a)


def teq(k):
    return (flux(k) * (1 - ALB[k]) / (4 * SIG)) ** 0.25


def tsub(k):
    return (flux(k) * (1 - ALB[k]) / SIG) ** 0.25


fails = []


def chk(name, got, exp, tol):
    ok = abs(got - exp) <= tol
    print(("ok   " if ok else "FAIL ") + f"{name}: {got:.3f} (expect {exp} +/- {tol})")
    if not ok:
        fails.append(name)


# --- constants ---
chk("solar constant S0", S0, 1361, 1)

# --- flux and % of Earth (distance only; exact) ---
chk("earth flux W/m2", flux("earth"), 1361, 2)
chk("earth % of Earth", pct_earth("earth"), 100, 0.5)
chk("mercury % of Earth", pct_earth("mercury"), 668, 4)
chk("mercury flux W/m2", flux("mercury"), 9087, 40)
chk("mars flux W/m2", flux("mars"), 586, 3)
chk("neptune flux W/m2", flux("neptune"), 1.505, 0.1)

# --- equilibrium and subsolar temperatures ---
chk("earth Teq K", teq("earth"), 254, 1.5)
chk("earth subsolar K", tsub("earth"), 359, 2)
chk("mars Teq K", teq("mars"), 210, 2)
chk("mercury Teq K", teq("mercury"), 437, 3)
chk("titan Teq K", teq("titan"), 83, 4)

# --- corrected Bond albedos (v15mk2.40 data-accuracy fix) ---
for body, exp in [("titan", 0.265), ("callisto", 0.13), ("io", 0.52),
                  ("europa", 0.62), ("ganymede", 0.35)]:
    chk("Bond albedo " + body, ALB[body], exp, 1e-9)

# --- moons inherit their planet's heliocentric distance ---
chk("io AU == jupiter AU", AU["io"][0], AU["jupiter"][0], 1e-9)
chk("titan AU == saturn AU", AU["titan"][0], AU["saturn"][0], 1e-9)

if fails:
    print(f"\n{len(fails)} CHECK(S) FAILED: " + ", ".join(fails))
    sys.exit(1)
print("\nAll %d solar-energy checks passed." % (12 + 5 + 2))
