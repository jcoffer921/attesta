"""Versioned citation map for explanations.

A plain lookup keyed by permit clause type -- not a search index -- so the
same clause always yields the same citation and changes show up in review
diffs. Bump CITATIONS_VERSION whenever an entry is added, removed or reworded;
it is stored with each explanation so an old explanation can be traced to the
map it was checked against.

Only add an entry when the regulation text has been checked by a person.
`reviewed` stays False until then. Permit-specific behaviour (for example how
non-detects are averaged) comes from the permit file itself, not a CFR
section, so it is deliberately absent here.
"""

from __future__ import annotations

CITATIONS_VERSION = 2

# Wording checked against the current eCFR text (via Cornell LII) on
# 2026-10-15; `reviewed` stays False until a person confirms it.
CITATIONS: dict[str, dict] = {
    "monthly-avg": {
        "cite": "40 CFR 122.45(d)(1)",
        "summary": (
            "For continuous discharges from dischargers other than POTWs, limitations are "
            "stated, unless impracticable, as maximum daily and average monthly discharge limitations."
        ),
        "reviewed": False,
    },
    "daily-max": {
        "cite": "40 CFR 122.45(d)(1)",
        "summary": (
            "For continuous discharges from dischargers other than POTWs, limitations are "
            "stated, unless impracticable, as maximum daily and average monthly discharge limitations."
        ),
        "reviewed": False,
    },
    "averaging": {
        "cite": "40 CFR 122.41(l)(4)(iii)",
        "summary": "Averages are calculated as arithmetic means unless the permit specifies otherwise.",
        "reviewed": False,
    },
    "sample": {
        "cite": "40 CFR 122.44(i)(1)",
        "summary": "Permits must require monitoring sufficient to assure compliance with permit limitations.",
        "reviewed": False,
    },
    "dmr-reporting": {
        "cite": "40 CFR 122.41(l)(4)",
        "summary": "Monitoring results are reported on a Discharge Monitoring Report.",
        "reviewed": False,
    },
}


def applicable_keys(clause: str) -> list[str]:
    """Citation keys an explanation of `clause` may reference."""
    keys = [clause] if clause in CITATIONS else []
    if clause == "monthly-avg":
        keys.append("averaging")
    keys.append("dmr-reporting")
    return keys
