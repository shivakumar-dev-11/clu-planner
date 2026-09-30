# Clu Daily Visit Planner

Hackathon MVP: assign and sequence customer visits for collection executives under hard constraints.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
streamlit run app.py
```

Or without activating the venv:

```bash
npm run dev
```

(`npm` here only runs the Streamlit command; dependencies are installed with `pip`, not `npm install`.)

Then open **http://localhost:8501** in your browser. If Streamlit asks for an email on first run, press **Enter** once (empty), or use the project `.streamlit/credentials.toml` already configured to skip it.

Sign in with demo credentials (see login screen) or set `CLU_EXEC_PASSWORDS=E01:secret;admin:secret`.

## Inputs

- **Executives** are loaded from [`data/executives.csv`](data/executives.csv) only (not uploaded in the UI).
- **Customers** CSV upload (or sample in `data/`): supports `address`, aliases `id`, `priority`, `amount`, `svc`, `window`.

### Maps

- **Route map** tab: multi-stop map from your fixed **branch office** (`data/executives.csv`) through numbered customer stops (no API key).
- **Google Maps** opens in the browser for office, single-leg, or full-route navigation (no API key).

## Outputs

- `plan.csv` — `arrival_time` is **scheduled visit start** (after waiting for window)
- `unvisited_customers.csv` — reason codes per customer
- Dashboard KPIs from `metrics.py` (single source of truth)

## Assumptions

- **A1:** Haversine × 1.3 road km, 25 km/h travel speed
- **A2:** Time window end inclusive for service finish
- **A3:** Export `arrival_time` = visit start; physical arrival in optional columns
- **A4:** λ = 2 default for score
- **A5:** Greedy insertion is not globally optimal
- **A6:** Baseline uses same route simulator as optimizer
- **A7:** Map lines are straight-line estimates, not road navigation

## Tests

```bash
pytest tests/ -q
```

## Security (demo)

- Passwords verified with bcrypt; override via `CLU_EXEC_PASSWORDS` env var
- Do not commit real customer CSVs or production passwords
- Uploaded files are processed in memory only
