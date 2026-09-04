# Reddit Lounge Intelligence

Reddit Lounge Intelligence is an executive voice-of-customer dashboard for understanding how travelers describe airport lounge experiences. It presents a frozen, offline analysis of Reddit discussion from January through August 2026. Results are directional and should not be interpreted as representative customer research or market share.

## Dashboard

The Streamlit application contains five pages:

1. **Home** — scope, analytical funnel, source context and navigation.
2. **Executive Overview** — national brand feedback and five experience themes.
3. **Airport View** — supported US airports and valid same-location comparisons.
4. **Voice of Customer** — approved Reddit excerpts selected deterministically from the measured population.
5. **FAQ / Methodology** — definitions, validation, limitations and worked examples.

The four headline brand ecosystems are Amex, Chase, Capital One and Delta.

## Scope and analytical funnel

The analysis covers parent posts dated January–August 2026. The frozen funnel is:

`61,413 → 17,742 → 5,850 → 3,696 → 2,215 → 6,003 → 5,997`

This represents exploded Reddit comment units, experience-bearing comments, the 2026 YTD production scope, usable comments, known-attribution comments, extracted observations and final clean observations respectively.

A **comment** is one Reddit response and is the primary executive counting unit. An **observation** is one supported brand or lounge × detailed experience area × sentiment proposition. One comment can therefore produce more than one observation. Executive views collapse observations back to unique comments at the relevant brand, theme or airport level.

## Methodology in brief

- Experience-relevance filtering retains comments that communicate a lounge-experience judgment.
- Usability filtering retains comments specific enough for detailed analysis.
- Conservative attribution prefers explicit comment evidence and preserves `UNKNOWN` when evidence is insufficient.
- Detailed extraction assigns supported experience aspects, sentiment and exact evidence spans.
- Executive presentation groups detailed aspects into five themes without changing the underlying classifications.
- Airport results appear only when the frozen evidence thresholds are met; same-airport comparisons are never replaced with national comparisons.
- Voice of Customer excerpts come from an offline, approved evidence mart and are selected deterministically. No runtime LLM is used.

Reddit users and communities are self-selected. Discussion volume is not market share, source communities are concentrated, and results are directional rather than representative of all lounge customers. Individual comment timestamps were unavailable, so monthly analysis uses the parent post month.

The dashboard’s FAQ / Methodology page contains the complete business-facing interpretation guidance, validation disclosures and limitations.

## Public data boundary

This repository is designed to include only small aggregate presentation marts and intentionally curated Reddit excerpts required by the dashboard.

Raw Reddit data, processed observation-level data, gold-label files, validation working rows, intermediate outputs, notebooks and secrets are intentionally excluded from the public repository. Reddit source links remain attached to approved excerpts.

## Local setup

The project uses [uv](https://docs.astral.sh/uv/) and targets Python 3.14.

```bash
uv sync
uv run streamlit run dashboard/app.py
```

The application reads frozen local CSV assets only. It does not require an OpenAI key, Reddit API credentials, a database or Streamlit secrets.

## Streamlit Community Cloud

- Repository entry point: `dashboard/app.py`
- Select Python 3.14 in the deployment advanced settings when that version is supported by the target Streamlit Community Cloud environment. Do not assume the platform default matches the local project.
- No secrets are required for the dashboard.
- Keep the public runtime CSV allowlist in `.gitignore` intact when updating presentation data.

All analytical outputs must be rebuilt offline and validated before replacing a frozen public presentation mart.
