from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
import pytest

from pakdk.analysis import design_effect, education_standardized, shares
from pakdk.data import ITEMS, SURVEYS, classify, education_group, load

RESULTS = Path(__file__).resolve().parent.parent / "results"


@pytest.mark.parametrize(
    "label, kind, expected",
    [
        ("Very favorable", "favorability", "positive"),
        ("Somewhat unfavorable", "favorability", "negative"),
        ("Don't know", "favorability", "no answer"),
        ("Donât know", "favorability", "no answer"),
        ("Refused", "favorability", "no answer"),
        ("Sometimes justified", "justified", "positive"),
        ("Rarely justified", "justified", "negative"),
        ("Very serious threat", "threat", "positive"),
        ("Minor threat", "threat", "negative"),
        ("No threat at all", "threat", "negative"),
        ("Not a threat at all", "threat", "negative"),
        ("Not too concerned", "concern", "negative"),
        ("Somewhat concerned", "concern", "positive"),
    ],
)
def test_every_answer_label_has_the_intended_class(label, kind, expected):
    assert classify(label, kind) == expected


def test_education_groups_drop_nonanswers():
    assert education_group(1) == "none"
    assert education_group(5) == "some"
    assert np.isnan(education_group(98))
    assert np.isnan(education_group(97))


def test_design_effect_recovers_a_stated_margin():
    assert design_effect(2014, 1203) == pytest.approx((4.2 / (196 * np.sqrt(0.25 / 1203))) ** 2)


def test_shares_are_weighted_and_sum_to_one():
    frame = pd.DataFrame({"weight": [1, 1, 2], "item": ["positive", "no answer", "no answer"]})
    out = shares(frame, "item")
    assert out["no answer"] == pytest.approx(0.75)
    assert out[["positive", "negative", "no answer"]].sum() == pytest.approx(1)


def test_standardization_removes_a_pure_composition_change():
    # Same rates within groups in both years; only the mix changes.
    rows = []
    for year, none_share in [(2009, 0.5), (2014, 0.8)]:
        for education, rate in [("none", 0.6), ("some", 0.2)]:
            weight = none_share if education == "none" else 1 - none_share
            rows += [(year, education, weight * rate, "no answer"), (year, education, weight * (1 - rate), "negative")]
    data = pd.DataFrame(rows, columns=["year", "education", "weight", "item"])
    data["country"], data["sex"] = "Pakistan", "Female"
    frames = {year: data[data.year == year] for year in (2009, 2014)}
    out = education_standardized(frames, ["item"], sexes=["Female"]).set_index("sex").loc["Female"]
    assert out["2014 at 2009 mix"] == pytest.approx(out["observed 2009"])
    assert out["observed 2014"] > out["observed 2009"]


def test_results_reproduce_pew_published_2014_figures():
    table = pd.read_csv(RESULTS / "pakistan_by_sex.csv")
    row = table[(table.year == 2014) & (table.sex == "All")].set_index("item")
    assert round(100 * row.loc["Taliban", "positive"]) == 8
    assert round(100 * row.loc["Taliban", "negative"]) == 59
    assert abs(round(100 * row.loc["al Qaeda", "positive"]) - 12) <= 1
    assert round(100 * row.loc["Suicide bombing justified", "positive"]) == 3
    shares_sum = table[["positive", "negative", "no answer"]].sum(axis=1)
    assert np.allclose(shares_sum, 1)


@pytest.mark.parametrize("year", [2010, 2014])
def test_load_reads_wave_columns_and_preserves_labels(tmp_path, year):
    survey = SURVEYS[year]
    columns = {"COUNTRY": [1, 1], survey.weight: [0.4, 1.6], survey.sex: [1, 2], survey.education: [1, 2]}
    labels = {"COUNTRY": {1: "Pakistan"}, survey.sex: {1: "Female", 2: "Male"}}
    for _, variables in ITEMS.values():
        if year in variables:
            columns[variables[year]] = [1, 2]
            labels[variables[year]] = {1: "Very favorable", 2: "Refused"}
    if survey.interviewer:
        columns[survey.interviewer] = [12, 16]
    if survey.interviewer_sex:
        columns[survey.interviewer_sex] = [1, 2]
        labels[survey.interviewer_sex] = labels[survey.sex]
    path = tmp_path / survey.path
    path.parent.mkdir()
    pyreadstat.write_sav(pd.DataFrame(columns).assign(unused=711), path, variable_value_labels=labels)
    frame = load(year, tmp_path)
    assert frame["Taliban"].tolist() == ["positive", "no answer"]
    assert frame["weight"].tolist() == [0.4, 1.6]
    assert frame["sex"].tolist() == ["Female", "Male"]
    assert frame["ISIS"].isna().all()
    if survey.interviewer_sex:
        assert frame["interviewer_sex"].tolist() == ["Female", "Male"]
    else:
        assert frame["interviewer_sex"].isna().all()
