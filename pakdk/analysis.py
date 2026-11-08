"""Weighted answer shares and the comparisons the report rests on."""

import numpy as np
import pandas as pd

from .data import ITEMS, SURVEYS

CLASSES = ["positive", "negative", "no answer"]


def design_effect(year, n):
    """Back out the design effect from Pew's stated Pakistan margin of error (95%, p = 0.5)."""
    simple = 100 * 1.96 * np.sqrt(0.25 / n)
    return (SURVEYS[year].pakistan_moe / simple) ** 2


def shares(frame, item):
    """Weighted share of each answer class among respondents asked the item, with a standard error."""
    asked = frame[frame[item].notna()]
    weight = asked["weight"]
    rows = {}
    effective = weight.sum() ** 2 / (weight**2).sum()
    for answer in CLASSES:
        share = weight[asked[item] == answer].sum() / weight.sum()
        rows[answer] = share
        rows[answer + " se"] = np.sqrt(share * (1 - share) / effective)
    rows["n"] = len(asked)
    return pd.Series(rows)


def pakistan_by_sex(frames):
    """Answer shares for every item, by year and sex, in Pakistan."""
    rows = []
    for year, frame in frames.items():
        pakistan = frame[frame["country"] == "Pakistan"]
        deff = design_effect(year, len(pakistan))
        for sex in ["All", "Female", "Male"]:
            group = pakistan if sex == "All" else pakistan[pakistan["sex"] == sex]
            for item in ITEMS:
                if group[item].notna().sum() == 0:
                    continue
                row = shares(group, item)
                for answer in CLASSES:
                    row[answer + " se"] *= np.sqrt(deff)
                rows.append({"year": year, "sex": sex, "item": item, **row.to_dict()})
    return pd.DataFrame(rows)


def education_standardized(frames, items, sexes=("Female", "Male")):
    """Women's and men's no-answer shares in 2014 if each sex had its 2009 education mix."""
    rows = []
    for sex in sexes:
        groups = {}
        for year, frame in frames.items():
            pakistan = frame[(frame["country"] == "Pakistan") & (frame["sex"] == sex) & frame["education"].notna()]
            groups[year] = pakistan
        mix = {year: g.groupby("education")["weight"].sum() / g["weight"].sum() for year, g in groups.items()}
        for item in items:
            rate = {
                year: g.groupby("education").apply(
                    lambda cell: cell["weight"][cell[item] == "no answer"].sum()
                    / cell["weight"][cell[item].notna()].sum()
                )
                for year, g in groups.items()
            }
            rows.append(
                {
                    "sex": sex,
                    "item": item,
                    "no schooling 2009": mix[2009]["none"],
                    "no schooling 2014": mix[2014]["none"],
                    "none 2009": rate[2009]["none"],
                    "none 2014": rate[2014]["none"],
                    "some 2009": rate[2009]["some"],
                    "some 2014": rate[2014]["some"],
                    "observed 2009": (rate[2009] * mix[2009]).sum(),
                    "observed 2014": (rate[2014] * mix[2014]).sum(),
                    "2014 at 2009 mix": (rate[2014] * mix[2009]).sum(),
                }
            )
    return pd.DataFrame(rows)


def other_countries(frames, items, minimum=300):
    """Change in no-answer share by sex, 2009 to 2014, in every country surveyed on the item in both waves."""
    rows = []
    for item in items:
        per_year = {}
        for year in (2009, 2014):
            frame = frames[year]
            asked = frame[frame[item].notna()]
            per_year[year] = {
                (country, sex): group
                for (country, sex), group in asked.groupby(["country", "sex"])
                if len(group) >= minimum / 2
            }
        for country, sex in sorted(set(per_year[2009]) & set(per_year[2014])):
            before = shares(per_year[2009][(country, sex)], item)["no answer"]
            after = shares(per_year[2014][(country, sex)], item)["no answer"]
            rows.append({"item": item, "country": country, "sex": sex, "2009": before, "2014": after})
    out = pd.DataFrame(rows)
    out["change"] = out["2014"] - out["2009"]
    return out


BATTERY = ["Taliban", "al Qaeda", "United States", "China", "Iran"]


def same_respondents(frames, battery=BATTERY):
    """Whether the people who skip one question are the people who skip the others, by year and sex."""
    rows = []
    for year, frame in frames.items():
        pakistan = frame[frame["country"] == "Pakistan"]
        for sex in ["Female", "Male"]:
            group = pakistan[pakistan["sex"] == sex]
            skipped = group[battery] == "no answer"
            weight = group["weight"]
            taliban, us = skipped["Taliban"], skipped["United States"]
            count = skipped.sum(axis=1)
            rows.append(
                {
                    "year": year,
                    "sex": sex,
                    "skip US if skipped Taliban": weight[taliban & us].sum() / weight[taliban].sum(),
                    "skip US if answered Taliban": weight[~taliban & us].sum() / weight[~taliban].sum(),
                    "skip all": weight[count == len(battery)].sum() / weight.sum(),
                    "skip none": weight[count == 0].sum() / weight.sum(),
                }
            )
    return pd.DataFrame(rows)


def interviewer_spread(frames, item="Taliban", minimum=10):
    """Spread of the no-answer rate across interviewers, against the spread sampling alone would produce."""
    rows = []
    for year, frame in frames.items():
        pakistan = frame[(frame["country"] == "Pakistan") & frame["interviewer"].notna()]
        if pakistan.empty:
            continue
        for sex in ["Female", "Male"]:
            group = pakistan[pakistan["sex"] == sex].assign(skip=lambda d: (d[item] == "no answer").astype(float))
            per = group.groupby("interviewer")["skip"].agg(["mean", "size"])
            per = per[per["size"] >= minimum]
            overall = group["skip"].mean()
            chance = (overall * (1 - overall) / per["size"]).mean()
            same_sex = np.nan
            if group["interviewer_sex"].notna().any():
                same_sex = (group["interviewer_sex"] == sex).mean()
            rows.append(
                {
                    "year": year,
                    "sex": sex,
                    "interviewers": len(per),
                    "lowest": per["mean"].min(),
                    "highest": per["mean"].max(),
                    "variance": per["mean"].var(),
                    "chance variance": chance,
                    "same-sex interviewer": same_sex,
                }
            )
    return pd.DataFrame(rows)
