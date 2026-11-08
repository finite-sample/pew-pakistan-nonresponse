# Who Stopped Answering?

Between Pew's 2009 and 2014 surveys of Pakistan, the share viewing the Taliban unfavorably fell from 70% to 59% while the favorable share stayed near one in ten. Pew described extremist groups as "seen negatively, but less so in recent years," and press coverage read the third of respondents without an answer as reluctance to talk about the Taliban.

The respondent-level data show a change in who answered:

- **Women stopped answering, about everything foreign.** Women's no-answer share rose from 25% to 53% on the Taliban and from 26% to 48% on the United States. Men's stayed at 15% and 14% on the Taliban and 7% and 8% on the United States. Women still rated Nawaz Sharif (5% and 7% without an answer).
- **Men's views of the Taliban did not change** (74% and 75% unfavorable). Men's views of al Qaeda did soften (8% to 15% favorable).
- **Not education.** More 2014 women had no schooling, but the rise occurs within both schooling groups.
- **Specific to Pakistan.** Among 23 countries Pew surveyed in both years, Pakistan is the only one where the rise is confined to women.

The report is [ms/report.pdf](ms/report.pdf).

## Reproducing

Pew's terms do not allow redistributing their data, so `data/raw/` is not in the repository. The summary tables in `results/` are, so the report builds without the raw files.

```sh
make install   # uv sync
make report    # results/ -> tabs/
make paper     # tabs/ -> ms/report.pdf
make check     # lint, tests, tables current, PDF builds with no undefined references
```

To rebuild `results/` from the raw files, create a free account at [pewresearch.org/global/datasets](https://www.pewresearch.org/global/datasets/), download the Spring 2009 and Spring 2014 Global Attitudes datasets, unzip them into `data/raw/2009/` and `data/raw/2014/`, and run `make aggregate`.

## Layout

```text
pakdk/data.py       Read Pew files; harmonize items; code answers as positive, negative, or no answer
pakdk/analysis.py   Weighted shares, education standardization, cross-country comparison
scripts/run.py      aggregate (raw -> results/) and report (results/ -> tabs/)
tests/              Answer coding, weighting, standardization, and agreement with Pew's published 2014 figures
results/            Committed summary tables
tabs/               Generated LaTeX tables and number macros
ms/                 Report source, bibliography, and PDF
```

## License

Code and report are MIT-licensed. Pew data are subject to Pew Research Center's terms of use.
