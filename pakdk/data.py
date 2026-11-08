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
    2014: Survey(
        "2014/Pew Research Global Attitudes Spring 2014 Dataset for Web.sav", "weight", "Q132", "Q138PAK", 4.2
    ),
}

# Country labels that differ only in spelling between waves.
SAME_COUNTRY = {"Palestinian territories": "Palestinian Territories"}

# The same question in both waves. Kind decides which answers count as positive.
ITEMS = {
    "Taliban": ("favorability", "Q23D", "Q46D"),
    "al Qaeda": ("favorability", "Q23B", "Q46B"),
    "Hamas": ("favorability", "Q11K", "Q15N"),
    "Hezbollah": ("favorability", "Q11L", "Q15O"),
    "United States": ("favorability", "Q11A", "Q15A"),
    "China": ("favorability", "Q11C", "Q15B"),
    "Iran": ("favorability", "Q11D", "Q15C"),
    "Russia": ("favorability", "Q11E", "Q15E"),
    "European Union": ("favorability", "Q11F", "Q15F"),
    "Nawaz Sharif": ("favorability", "Q23A", "Q46A"),
    "Asif Ali Zardari": ("favorability", "Q23C", "Q46C"),
    "Iftikhar Chaudhry": ("favorability", "Q23E", "Q46E"),
    "Suicide bombing justified": ("justified", "Q58", "Q100"),
    "Concern about extremism": ("concern", "Q19", "Q39"),
    "Taliban a threat": ("threat", "Q60AA", "Q116A"),
    "al Qaeda a threat": ("threat", "Q60AC", "Q116C"),
    "India a threat": ("threat", "Q60AB", "Q116B"),
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
    """Both waves code 'no formal schooling' as 1; 98 and 99 are don't know and refused."""
    if pd.isna(code) or code >= 97:
        return np.nan
    return "none" if code == 1 else "some"


def load(year, raw=RAW):
    """One row per respondent, all countries, with harmonized items coded by answer class."""
    survey = SURVEYS[year]
    # Some value labels are not valid UTF-8; Latin-1 reads every byte.
    frame, meta = pyreadstat.read_sav(raw / survey.path, encoding="latin1")
    labels = meta.variable_value_labels
    column = 1 if year == 2009 else 2
    out = pd.DataFrame(
        {
            "year": year,
            "country": frame["COUNTRY"].map(labels["COUNTRY"]).str.strip().replace(SAME_COUNTRY),
            "weight": frame[survey.weight],
            "sex": frame[survey.sex].map(labels[survey.sex]),
            "education": frame[survey.education].map(education_group),
        }
    )
    for name, spec in ITEMS.items():
        kind, variable = spec[0], spec[column]
        coding = {code: classify(text, kind) for code, text in labels[variable].items()}
        out[name] = frame[variable].map(coding)
    return out
