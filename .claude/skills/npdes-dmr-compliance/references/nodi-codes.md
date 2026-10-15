# NODI codes (EPA table)

Evidence tags: **[V]** verified against a primary or EPA/state source (see `sources.md`); **[G]** general domain knowledge, confirm against the actual permit before using it in user-facing text; **[?]** open question, do not guess.

Valid code **sets vary by state**; the EPA table is the superset. A DMR row
takes a numeric value **or** a NODI code, never both (hard error). [V]

| Code | Meaning | Note |
|---|---|---|
| C | No Discharge | whole monitoring point/period; a DMR is still required [V] |
| B | Below Detection Limit/No Detection | only as authority permits [V] |
| 9 | Conditional Monitoring - Not Required This Period | conditional / periodic limits [V] |
| E | Failed to Sample/Required Analysis Not Conducted | creates a non-receipt violation [V] |
| P | Laboratory Error or Invalid Test | creates a non-receipt violation [V] |
| T | Environmental Conditions - Monitoring Not Possible | e.g. flood/ice [V] |
| Q | Not Quantifiable | between QL and DL in some states [V] |
| 1 | Wrong Flow | state-dependent |
| 2 | Operation Shutdown | state-dependent |
| 3 | Special Report Attached | state-dependent |
| 4 | Discharge to Lagoon/Groundwater | state-dependent |
| 5 | Frozen Conditions | state-dependent |
| 7 | No Influent | state-dependent |
| 8 | Other (See Comments) | state-dependent |
| A | General Permit Exemption | |
| D | Lost Sample/Data Not Available | |
| F | Insufficient Flow for Sampling | |
| G | Sampling Equipment Failure | |
| H | Invalid Test | |
| I | Land Applied | |
| J | Recycled - Water-Closed System | |
| K | Natural Disaster | |
| M | Laboratory Error | |
| N | Not Constructed | |
| R | Administratively Resolved | |
| S | Fire Conditions | |
| V | Weather Related | |
| W | Dry Lysimeter/Well | |
| X | Parameter/Value Not Reported | |
| 6, Y | State-specific indicator (invalid / valid) | |
| L | DMR Received but not Entered | admin |
| Z | COVID-19 valid Mar-Aug 2020 | legacy |

Which codes *excuse* vs. *create* a violation is state- and permit-specific
[?]. The system must not assert that a NODI code excuses a missing value;
surface it and let the human decide.
