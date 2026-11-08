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
    interviewer: str | None = None
    interviewer_sex: str | None = None


SURVEYS = {
    2009: Survey("2009/Pew Gap 2009 Data.sav", "WEIGHT", "Q80", "Q95PAK", 3.0, interviewer="Q106"),
    2010: Survey(
        "2010/Pew Research Center Global Attitudes Spring 2010 Dataset WEB.sav",
        "WEIGHT",
        "Q120",
        "Q129PAK",
        3.0,
        "Q141",
        "Q141B",
    ),
    2011: Survey("2011/Pew Global Attitudes Spring 2011 Dataset WEB.sav", "WEIGHT", "Q111", "Q120PAK", 3.0),
    2012: Survey(
        "2012/Pew Research Global Attitudes Project Spring 2012 Dataset for web.sav", "WEIGHT", "Q141", "Q154PAK", 4.2
    ),
    2013: Survey(
        "2013/Pew Research Global Attitudes Project Spring 2013 Dataset for web.sav", "WEIGHT", "Q164", "Q180PAK", 4.3
    ),
    # Pew's 2015 Pakistan margin of error is not in the released files; 4.2 is its figure for 2012 and 2014.
    2015: Survey(
        "2015/Pew Research Global Attitudes Spring 2015 Dataset for Web FINAL.sav", "WEIGHT", "Q145", "Q163PAK", 4.2
    ),
    2014: Survey(
        "2014/Pew Research Global Attitudes Spring 2014 Dataset for Web.sav", "weight", "Q132", "Q138PAK", 4.2
    ),
}

# Country labels that differ only in spelling between waves.
SAME_COUNTRY = {"Palestinian territories": "Palestinian Territories"}

# Each item's variable in each wave that asked it. Kind decides which answers count as positive.
ITEMS = {
    "Taliban": (
        "favorability",
        {2015: "Q109D", 2010: "Q35D", 2011: "Q49D", 2012: "Q46D", 2009: "Q23D", 2013: "Q41D", 2014: "Q46D"},
    ),
    "al Qaeda": (
        "favorability",
        {2015: "Q109B", 2010: "Q35B", 2011: "Q49B", 2012: "Q46B", 2009: "Q23B", 2013: "Q41B", 2014: "Q46B"},
    ),
    "Hamas": ("favorability", {2010: "Q7N", 2011: "Q3M", 2012: "Q8P", 2009: "Q11K", 2013: "Q9J", 2014: "Q15N"}),
    "Hezbollah": ("favorability", {2010: "Q7O", 2011: "Q3N", 2012: "Q8Q", 2009: "Q11L", 2013: "Q9K", 2014: "Q15O"}),
    "United States": (
        "favorability",
        {2015: "Q12A", 2010: "Q7A", 2011: "Q3A", 2012: "Q8A", 2009: "Q11A", 2013: "Q9A", 2014: "Q15A"},
    ),
    "China": (
        "favorability",
        {2015: "Q12B", 2010: "Q7C", 2011: "Q3C", 2012: "Q8C", 2009: "Q11C", 2013: "Q9C", 2014: "Q15B"},
    ),
    "Iran": (
        "favorability",
        {2015: "Q12C", 2010: "Q7D", 2011: "Q3D", 2012: "Q8D", 2009: "Q11D", 2013: "Q9D", 2014: "Q15C"},
    ),
    "Russia": ("favorability", {2010: "Q7E", 2011: "Q3E", 2012: "Q8E", 2009: "Q11E", 2013: "Q9E", 2014: "Q15E"}),
    "European Union": (
        "favorability",
        {2010: "Q7F", 2011: "Q3F", 2012: "Q8F", 2009: "Q11F", 2013: "Q9F", 2014: "Q15F"},
    ),
    "Nawaz Sharif": (
        "favorability",
        {2015: "Q109A", 2010: "Q35A", 2011: "Q49A", 2012: "Q46A", 2009: "Q23A", 2013: "Q41A", 2014: "Q46A"},
    ),
    "Asif Ali Zardari": (
        "favorability",
        {2010: "Q35C", 2011: "Q49C", 2012: "Q46C", 2009: "Q23C", 2013: "Q41C", 2014: "Q46C"},
    ),
    "Iftikhar Chaudhry": (
        "favorability",
        {2010: "Q35E", 2011: "Q49E", 2012: "Q46E", 2009: "Q23E", 2013: "Q41E", 2014: "Q46E"},
    ),
    "Pakistani Taliban (TTP)": (
        "favorability",
        {2015: "Q114A", 2010: "Q115A", 2011: "Q105A", 2012: "Q134A", 2013: "Q150A"},
    ),
    "Afghan Taliban": ("favorability", {2015: "Q114C", 2010: "Q115C", 2011: "Q105C", 2012: "Q134C", 2013: "Q150C"}),
    "Lashkar-e-Taiba": ("favorability", {2015: "Q114B", 2010: "Q115B", 2011: "Q105B", 2012: "Q134B", 2013: "Q150B"}),
    "Haqqani network": ("favorability", {2013: "Q150D"}),
    "ISIS": ("favorability", {2015: "Q12N"}),
    "Suicide bombing justified": (
        "justified",
        {2015: "Q133", 2010: "Q96", 2011: "Q89", 2009: "Q58", 2013: "Q121", 2014: "Q100"},
    ),
    "Concern about extremism": (
        "concern",
        {2010: "Q30", 2011: "Q44", 2012: "Q38", 2009: "Q19", 2013: "Q35", 2014: "Q39"},
    ),
    "Taliban a threat": (
        "threat",
        {2010: "Q99A", 2011: "Q96A", 2012: "Q125A", 2009: "Q60AA", 2013: "Q142A", 2014: "Q116A"},
    ),
    "al Qaeda a threat": (
        "threat",
        {2010: "Q99C", 2011: "Q96C", 2012: "Q125C", 2009: "Q60AC", 2013: "Q142C", 2014: "Q116C"},
    ),
    "India a threat": (
        "threat",
        {2010: "Q99B", 2011: "Q96B", 2012: "Q125B", 2009: "Q60AB", 2013: "Q142B", 2014: "Q116B"},
    ),
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
            "interviewer": frame[survey.interviewer] if survey.interviewer else np.nan,
            "interviewer_sex": (
                frame[survey.interviewer_sex].map(labels[survey.interviewer_sex]) if survey.interviewer_sex else np.nan
            ),
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
