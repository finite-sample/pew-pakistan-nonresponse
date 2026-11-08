"""Read the Pew Global Attitudes files and code each answer as positive, negative, or no answer."""

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


@dataclass(frozen=True)
class Survey:
    path: str
    weight: str
    sex: str
    education: str
    # Pew's stated margin of error for Pakistan, used to back out a design effect.
    pakistan_moe: float


SURVEYS = {
    2009: Survey("2009/Pew Gap 2009 Data.sav", "WEIGHT", "Q80", "Q95PAK", 3.0),
    2013: Survey(
        "2013/Pew Research Global Attitudes Project Spring 2013 Dataset for web.sav", "WEIGHT", "Q164", "Q180PAK", 4.3
    ),
    2014: Survey(
        "2014/Pew Research Global Attitudes Spring 2014 Dataset for Web.sav", "weight", "Q132", "Q138PAK", 4.2
    ),
}

# Country labels that differ only in spelling between waves.
SAME_COUNTRY = {"Palestinian territories": "Palestinian Territories"}

# Each item's variable in each wave that asked it. Kind decides which answers count as positive.
ITEMS = {
    "Taliban": ("favorability", {2009: "Q23D", 2013: "Q41D", 2014: "Q46D"}),
    "al Qaeda": ("favorability", {2009: "Q23B", 2013: "Q41B", 2014: "Q46B"}),
    "Hamas": ("favorability", {2009: "Q11K", 2013: "Q9J", 2014: "Q15N"}),
    "Hezbollah": ("favorability", {2009: "Q11L", 2013: "Q9K", 2014: "Q15O"}),
    "United States": ("favorability", {2009: "Q11A", 2013: "Q9A", 2014: "Q15A"}),
    "China": ("favorability", {2009: "Q11C", 2013: "Q9C", 2014: "Q15B"}),
    "Iran": ("favorability", {2009: "Q11D", 2013: "Q9D", 2014: "Q15C"}),
    "Russia": ("favorability", {2009: "Q11E", 2013: "Q9E", 2014: "Q15E"}),
    "European Union": ("favorability", {2009: "Q11F", 2013: "Q9F", 2014: "Q15F"}),
    "Nawaz Sharif": ("favorability", {2009: "Q23A", 2013: "Q41A", 2014: "Q46A"}),
    "Asif Ali Zardari": ("favorability", {2009: "Q23C", 2013: "Q41C", 2014: "Q46C"}),
    "Iftikhar Chaudhry": ("favorability", {2009: "Q23E", 2013: "Q41E", 2014: "Q46E"}),
    "Pakistani Taliban (TTP)": ("favorability", {2013: "Q150A"}),
    "Afghan Taliban": ("favorability", {2013: "Q150C"}),
    "Lashkar-e-Taiba": ("favorability", {2013: "Q150B"}),
    "Haqqani network": ("favorability", {2013: "Q150D"}),
    "Suicide bombing justified": ("justified", {2009: "Q58", 2013: "Q121", 2014: "Q100"}),
    "Concern about extremism": ("concern", {2009: "Q19", 2013: "Q35", 2014: "Q39"}),
    "Taliban a threat": ("threat", {2009: "Q60AA", 2013: "Q142A", 2014: "Q116A"}),
    "al Qaeda a threat": ("threat", {2009: "Q60AC", 2013: "Q142C", 2014: "Q116C"}),
    "India a threat": ("threat", {2009: "Q60AB", 2013: "Q142B", 2014: "Q116B"}),
}

POSITIVE = {
    "favorability": r"^(very|somewhat) favorable",
    "justified": r"^(often|sometimes)",
    "concern": r"^(very|somewhat) concerned",
    "threat": r"^(a )?(very|somewhat) serious",
}
NEGATIVE = {
    "favorability": r"unfavorable",
    "justified": r"^(rarely|never)",
    "concern": r"^not (too|at all)",
    "threat": r"^(a )?minor|^no(t a)? threat",
}


def classify(label, kind):
    """Map one answer label to 'positive', 'negative', or 'no answer'."""
    text = label.strip().lower()
    if re.search(POSITIVE[kind], text):
        return "positive"
    if re.search(NEGATIVE[kind], text):
        return "negative"
    return "no answer"


def education_group(code):
    """Every wave codes 'no formal schooling' as 1; 97 and up are still in school, don't know, refused."""
    if pd.isna(code) or code >= 97:
        return np.nan
    return "none" if code == 1 else "some"


def load(year, raw=RAW):
    """One row per respondent, all countries, with harmonized items coded by answer class."""
    survey = SURVEYS[year]
    # Some value labels are not valid UTF-8; Latin-1 reads every byte.
    frame, meta = pyreadstat.read_sav(raw / survey.path, encoding="latin1")
    labels = meta.variable_value_labels
    out = pd.DataFrame(
        {
            "year": year,
            "country": frame["COUNTRY"].map(labels["COUNTRY"]).str.strip().replace(SAME_COUNTRY),
            "weight": frame[survey.weight],
            "sex": frame[survey.sex].map(labels[survey.sex]),
            "education": frame[survey.education].map(education_group),
        }
    )
    for name, (kind, variables) in ITEMS.items():
        if year not in variables:
            out[name] = np.nan
            continue
        variable = variables[year]
        coding = {code: classify(text, kind) for code, text in labels[variable].items()}
        out[name] = frame[variable].map(coding)
    return out
