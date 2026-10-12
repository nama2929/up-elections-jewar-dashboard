# Saarthi Electoral Lens — Jewar Assembly Constituency 63

**A separate Streamlit dashboard for Jewar, using the uploaded 2017, 2019, 2022 and 2024 Form 20 records.** The interface is light-themed and intended for an on-laptop candidate meeting and subsequent research. Unlike an election forecast tool, it presents verified historical EVM station data and dated public-issues reporting. No live field survey or 2027 election prediction is claimed.

## Start on Windows (quickest way)

1. Extract the entire ZIP directly to a short folder such as `C:\Jewar63`. **Don't put it inside another deeply nested folder**: Windows filename-length issues caused earlier installation failures.
2. Make sure Python is installed. Open PowerShell in the extracted folder.
3. Run these commands together:

```powershell
cd C:\Jewar63
py -m pip install -r requirements.txt
py -m streamlit run app.py --server.port 8502
```

Or double-click `RUN_JEWAR_DASHBOARD.bat`, which installs missing packages and starts the app. Internet is needed for a first-time pip install but not for local dashboards once dependencies are available.

4. Open `http://localhost:8502` if it doesn't open automatically. Stop with **Ctrl+C** in the terminal.

If `py` is unavailable, replace it with `python`:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8502
```

If you already have Python packages installed, do not create a deep nested virtual environment. If you want one, create it in `C:\Jewar63\.venv` or use `C:\J63Venv`.

## Dashboard pages

| Page | Purpose |
| --- | --- |
| Overview | Interactive home, 2017 candidate record and navigation |
| Election History | Each election's EVM candidate results and station totals |
| Booth Intelligence | All candidates, Q1/median/Q3, a *true* histogram, dot-based vote share–signed margin scatter, vote-share × margin heatmap, filters and CSV exports |
| Candidate Landscape | Vote totals, shares, and outright polling-station lead counts for all contestants |
| Cross-Year Lens | Separate Assembly and Lok Sabha comparisons and documented identity/alliance changes |
| Issues & Timeline | 17 dated issue and development records with source links, limitations and verification questions |
| Game Data Lab | Select/deselect historical candidates, add manual entrants, change hypothetical shares, inspect unallocated shares, compare with historical baseline, save/load JSON and export CSV |
| Diagnostics Lab | Interactive historical share/margin threshold checks; optional import of aggregated public-issue survey data |
| Research & QA | Source records, reconciliation discrepancies and raw CSV exports |
| Meeting Brief | Candidate-conversation notes and key historical talking points |

## Game Data Lab — candidate roster and hypothetical inputs

1. Open **Game Data Lab** in the left menu.
2. Select a historical ballot roster (2017 or 2022 Assembly, or the 2019/2024 parliamentary segment). All names in the roster are *historical* for that particular year, not certified 2027 nominations.
3. Switch historical candidates ON/OFF. Switching OFF does not transfer any share: unallocated/other share increases by their removed amount.
4. Under **Add candidates**, enter a name, party/Independent, and initial hypothetical share. This creates a *manual* entry only; it does not alter the original Form 20 or assert that the individual is contesting.
5. Adjust the number fields for any included candidates to make an illustrative distribution. When totals exceed 100%, the lab warns and disables exports. It does **not** automatically redistribute historical votes.
6. Compare the recorded EVM shares with the hypothetical shares. Use the **arithmetic combination** selector to sum specified entered percentages, without implying alliance vote transfer.
7. Download **CSV** for a simple table or **JSON** to save your complete scenario; later use **Load a previously saved scenario** to restore it. New entries are otherwise stored only in Streamlit session memory.
8. If port 8502 is occupied, start manually using `py -m streamlit run app.py --server.port 8503`.

**These inputs are not current opinion polling or a 2027 electoral forecast.** Changes reflect only values typed in the sandbox. The historical records in the other dashboard tabs are untouched.

## Source material

- `sources/Jewar_Electoral_Research_Quartiles_Margins_Matrix_Enhanced.xlsx`: the underlying 17-tab workbook, included for audit and reproducibility.
- `sources/63- jewar 2017 form 20.xls`: 2017 original provided by user.
- `sources/63- 2019 form 20 data.xls`: 2019 original provided by user.
- `sources/AC63- form 20 jewar 2022.xls`: 2022 original provided by user.
- `sources/form 20 data 2024.pdf`: 2024 official result sheet provided by user.
- `data/form20_{year}.csv`: normalized individual-station data extracted from the enhanced workbook.
- `data/metadata.json`: year, candidate, party and alliance references.
- `data/issues.csv`, `data/sources.csv`: source-attributed dated research, not current field results.

The tool `tools/build_dataset.py` can regenerate all normalized files from the included **enhanced Excel workbook** using the Python standard library only. It does not edit the source.

## Data limitations — read before presenting

1. **EVM vs final declared votes:** 2017 Narender Nagar received 13,216 polling-station EVM votes. The official final count was 13,239 including postal ballots. Booth charts all use EVM-only figures.
2. **Not the same person:** Narender Nagar is the 2017 SP Assembly candidate. The 2019 BSP alliance candidate Satveer, 2022 RLD alliance candidate Avtar Singh Bhadana and 2024 SP parliamentary candidate Dr. Mahendra Singh Nagar are separate people. The 2022 BSP candidate Narender Kumar must not be confused with Narender Nagar.
3. **2019 source discrepancy:** printed station-1 candidate subtotal exceeds candidate-column sum by 90 votes. Source station totals including NOTA remain reconciled.
4. **2022 source discrepancy:** 419 station-level EVM totals sum to 230,872, versus 231,196 in the workbook source's printed aggregate (324-vote discrepancy). Published results including postal ballots are a different scope. Verify against official RO sheets before treating the aggregate as certified.
5. **2024 source limitation:** 398 station rows but one is zero EVM; 397 usable for percentage distributions. Polling-station place names/elector counts aren't present in the uploaded Form 20. Do not invent a booth map.
6. **No validated cross-year station crosswalk:** booth numbers can change after splitting/merging. Cross-year visualizations compare aggregate election results only, not the same individual stations without verification.
7. **No 2027 forecast:** no estimated vote conversion, win probability, or inferred individual preferences. This workspace describes historical data and dated public-interest issues.

## Updating the data

Update the **enhanced workbook** in `sources/`, then run `python tools/build_dataset.py` to rebuild CSVs (the script expects the exact existing workbook filename and raw Form20 tabs layout). Restart Streamlit or clear its cached data. Every updated result should be checked against official Form 20 totals and documented.

## Deploying to Streamlit Community Cloud

1. Create a **private GitHub repository** containing `app.py`, `requirements.txt`, `data/`, `.streamlit/config.toml` and the optional `tools/` folder. The dashboard itself does **not** require uploading the original raw XLS/PDF files or `sources/` to GitHub.
2. In Streamlit Community Cloud select that repository and `app.py`.
3. Confirm data files are present, click **Deploy**, and check the `Research & QA` tab after launch.
4. Be aware: Streamlit Community Cloud access settings vary by account. Use a private app or appropriate access controls if your project material isn't intended for public sharing.

## Quick numerical checks

Run `python tools/test_data.py` in the project folder. It checks row-level candidate vote reconciliation and the expected counts, 2017 reference candidate votes and 2024 zero-EVM station.
