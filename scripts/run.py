"""Build the report's inputs.

aggregate: read Pew's files (data/raw, not redistributed) and write small summary tables to results/.
report:    read results/ and write LaTeX tables and number macros to tabs/.
"""

import sys
import warnings
from pathlib import Path

import pandas as pd

from pakdk.analysis import education_standardized, other_countries, pakistan_by_sex
from pakdk.data import SURVEYS, load

ROOT = Path(__file__).resolve().parent.parent

RESULTS = ROOT / "results"
TABS = ROOT / "tabs"
MAIN_ITEMS = [
    "Taliban",
    "al Qaeda",
    "Hamas",
    "Hezbollah",
    "United States",
    "China",
    "Iran",
    "Nawaz Sharif",
    "Asif Ali Zardari",
    "Suicide bombing justified",
    "Taliban a threat",
]
PLACEBO_ITEMS = ["United States", "China"]


def aggregate():
    warnings.filterwarnings("ignore", category=FutureWarning)
    frames = {year: load(year) for year in SURVEYS}
    RESULTS.mkdir(exist_ok=True)
    pakistan_by_sex(frames).to_csv(RESULTS / "pakistan_by_sex.csv", index=False, float_format="%.6f")
    education_standardized(frames, ["Taliban", "al Qaeda", "United States", "China"]).to_csv(
        RESULTS / "education_standardized.csv", index=False, float_format="%.6f"
    )
    other_countries(frames, PLACEBO_ITEMS).to_csv(RESULTS / "other_countries.csv", index=False, float_format="%.6f")


def pct(value, digits=0):
    return f"{100 * value:.{digits}f}"


def signed(value):
    rounded = round(100 * value) + 0
    return f"${rounded:+d}$"


def write_table(name, headings, rows, align, breaks=()):
    body = []
    for index, row in enumerate(rows):
        if index in breaks:
            body.append("\\midrule")
        body.append(" & ".join(row) + " \\\\")
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule", " & ".join(headings) + " \\\\", "\\midrule"]
    lines += body + ["\\bottomrule", "\\end{tabular}"]
    (TABS / f"{name}.tex").write_text("\n".join(lines) + "\n")


def report():
    TABS.mkdir(exist_ok=True)
    by_sex = pd.read_csv(RESULTS / "pakistan_by_sex.csv")
    education = pd.read_csv(RESULTS / "education_standardized.csv")
    others = pd.read_csv(RESULTS / "other_countries.csv")

    def cell(year, sex, item):
        return by_sex[(by_sex.year == year) & (by_sex.sex == sex) & (by_sex.item == item)].iloc[0]

    rows = []
    for item in MAIN_ITEMS:
        row = [item]
        for sex in ["Female", "Male"]:
            before, after = cell(2009, sex, item), cell(2014, sex, item)
            change = after["no answer"] - before["no answer"]
            se = (before["no answer se"] ** 2 + after["no answer se"] ** 2) ** 0.5
            row += [pct(before["no answer"]), pct(after["no answer"]), f"{signed(change)} ({100 * se:.0f})"]
        rows.append(row)
    write_table(
        "no_answer_by_sex",
        ["", "Women 2009", "2014", "Change (SE)", "Men 2009", "2014", "Change (SE)"],
        rows,
        "lrrrrrr",
        breaks=(4, 9),
    )

    rows = []
    for item in ["Taliban", "al Qaeda", "United States"]:
        for sex in ["All", "Female", "Male"]:
            before, after = cell(2009, sex, item), cell(2014, sex, item)
            label = item if sex == "All" else f"\\quad {'Women' if sex == 'Female' else 'Men'}"
            rows.append(
                [label]
                + [pct(before[a]) for a in ["positive", "negative", "no answer"]]
                + [pct(after[a]) for a in ["positive", "negative", "no answer"]]
            )
    write_table(
        "answers_by_sex",
        ["", "Fav.\\ 2009", "Unfav.", "No answer", "Fav.\\ 2014", "Unfav.", "No answer"],
        rows,
        "lrrrrrr",
        breaks=(3, 6),
    )

    rows = []
    for _, r in education.iterrows():
        rows.append(
            [
                f"{'Women' if r.sex == 'Female' else 'Men'}: {r['item']}",
                pct(r["none 2009"]),
                pct(r["none 2014"]),
                pct(r["some 2009"]),
                pct(r["some 2014"]),
                pct(r["observed 2009"]),
                pct(r["observed 2014"]),
                pct(r["2014 at 2009 mix"]),
            ]
        )
    write_table(
        "education",
        ["", "None 2009", "None 2014", "Some 2009", "Some 2014", "All 2009", "All 2014", "2014, 2009 mix"],
        rows,
        "lrrrrrrr",
        breaks=(4,),
    )

    wide = others.pivot_table(index=["item", "country"], columns="sex", values="change").reset_index()
    rows, starts = [], []
    for item in PLACEBO_ITEMS:
        starts.append(len(rows))
        block = wide[wide["item"] == item].sort_values(by="Female", ascending=False)
        for position, (_, r) in enumerate(block.iterrows()):
            name = f"\\textbf{{{r.country}}}" if r.country == "Pakistan" else r.country
            rows.append([item if position == 0 else "", name, signed(r.Female), signed(r.Male)])
    write_table("other_countries", ["Item", "Country", "Women", "Men"], rows, "llrr", breaks=starts[1:])

    def change(sex, item):
        return cell(2014, sex, item)["no answer"] - cell(2009, sex, item)["no answer"]

    women = others[(others.sex == "Female") & (others.item == "United States")].set_index("country")["change"]
    men = others[(others.sex == "Male") & (others.item == "United States")].set_index("country")["change"]
    gap = (women - men).drop("Pakistan")
    edu = education.set_index(["sex", "item"])
    values = {
        "TalibanFav": pct(cell(2014, "All", "Taliban")["positive"]),
        "TalibanUnfav": pct(cell(2014, "All", "Taliban")["negative"]),
        "TalibanNoAnswer": pct(cell(2014, "All", "Taliban")["no answer"]),
        "TalibanFavOld": pct(cell(2009, "All", "Taliban")["positive"]),
        "TalibanUnfavOld": pct(cell(2009, "All", "Taliban")["negative"]),
        "TalibanNoAnswerOld": pct(cell(2009, "All", "Taliban")["no answer"]),
        "QaedaFav": pct(cell(2014, "All", "al Qaeda")["positive"]),
        "SuicideYes": pct(cell(2014, "All", "Suicide bombing justified")["positive"]),
        "SuicideNoAnswer": pct(cell(2014, "All", "Suicide bombing justified")["no answer"]),
        "WomenTalibanOld": pct(cell(2009, "Female", "Taliban")["no answer"]),
        "WomenTaliban": pct(cell(2014, "Female", "Taliban")["no answer"]),
        "MenTalibanOld": pct(cell(2009, "Male", "Taliban")["no answer"]),
        "MenTaliban": pct(cell(2014, "Male", "Taliban")["no answer"]),
        "WomenUSOld": pct(cell(2009, "Female", "United States")["no answer"]),
        "WomenUS": pct(cell(2014, "Female", "United States")["no answer"]),
        "MenUSOld": pct(cell(2009, "Male", "United States")["no answer"]),
        "MenUS": pct(cell(2014, "Male", "United States")["no answer"]),
        "WomenNawazOld": pct(cell(2009, "Female", "Nawaz Sharif")["no answer"]),
        "WomenNawaz": pct(cell(2014, "Female", "Nawaz Sharif")["no answer"]),
        "MenTalibanUnfavOld": pct(cell(2009, "Male", "Taliban")["negative"]),
        "MenTalibanUnfav": pct(cell(2014, "Male", "Taliban")["negative"]),
        "WomenTalibanUnfavOld": pct(cell(2009, "Female", "Taliban")["negative"]),
        "WomenTalibanUnfav": pct(cell(2014, "Female", "Taliban")["negative"]),
        "MenHamasChange": signed(change("Male", "Hamas")),
        "TalibanUnfavDrop": pct(cell(2009, "All", "Taliban")["negative"] - cell(2014, "All", "Taliban")["negative"]),
        "MenQaedaFavOld": pct(cell(2009, "Male", "al Qaeda")["positive"]),
        "MenQaedaFav": pct(cell(2014, "Male", "al Qaeda")["positive"]),
        "MenQaedaUnfavOld": pct(cell(2009, "Male", "al Qaeda")["negative"]),
        "MenQaedaUnfav": pct(cell(2014, "Male", "al Qaeda")["negative"]),
        "WomenNoSchoolingOld": pct(edu.loc[("Female", "Taliban"), "no schooling 2009"]),
        "WomenNoSchooling": pct(edu.loc[("Female", "Taliban"), "no schooling 2014"]),
        "WomenTalibanStandardized": pct(edu.loc[("Female", "Taliban"), "2014 at 2009 mix"]),
        "WomenTalibanSomeOld": pct(edu.loc[("Female", "Taliban"), "some 2009"]),
        "WomenTalibanSome": pct(edu.loc[("Female", "Taliban"), "some 2014"]),
        "WomenTalibanNoneOld": pct(edu.loc[("Female", "Taliban"), "none 2009"]),
        "WomenTalibanNone": pct(edu.loc[("Female", "Taliban"), "none 2014"]),
        "PakistanUSGap": signed(women["Pakistan"] - men["Pakistan"]),
        "NextUSGapCountry": gap.idxmax(),
        "NextUSGap": signed(gap.max()),
        "PlaceboCountries": str(others[others.item == "United States"]["country"].nunique()),
        "SampleOld": f"{int(cell(2009, 'All', 'Taliban')['n']):,}",
        "Sample": f"{int(cell(2014, 'All', 'Taliban')['n']):,}",
    }
    (TABS / "numbers.tex").write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in values.items()))


if __name__ == "__main__":
    {"aggregate": aggregate, "report": report}[sys.argv[1]]()
