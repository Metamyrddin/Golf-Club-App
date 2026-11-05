# Fairway Ledger

An open-source fitting desk that turns a golfer’s measurements into **three full bags** — distance, control, and brand match — with the rule that produced every number written down.

It is a starting sheet for a professional fitter, not a substitute for a lie board or a launch monitor.

## What you get

- Driver, 3-wood or 5-wood, hybrid or utility iron, iron set, gap/sand/lob wedges, putter.
- A specific head and shaft on every club, in one flex family when the catalog allows it.
- Plain-language rationale, the rule ids that fired, CSV / PDF / JSON export.
- JWT auth, optional profile, “taken to fitter” feedback.
- A v1 catalog: Titleist, TaylorMade, Callaway. Ten heads and ten shafts each. Names are synthetic; loft ladders and shaft weights are realistic and meant to be extended.

The rule engine is the source of truth. An optional scikit-learn tree (`scripts/train_ranker.py`) can only try to recover the flex label. It is never asked to choose a club.

## Fitting logic, in plain language

1. **Wrist-to-floor** decides length and lie. One inch away from the gender reference (men 87 cm, women 81 cm) is one inch of length and one degree of lie. Higher wrists → longer and more upright. Clamped to ±2 inches and ±4°. Body type adds a small nudge (heavier builds slightly longer and more upright, ectomorphs slightly flatter). If wrist-to-floor was not measured, it is estimated from height and that is said out loud.
2. **Driver speed** starts at 95 mph for a 30-year-old man and 76 mph for a 30-year-old woman. It falls 0.35 mph per year after 35. Squat and bench, relative to body weight, move it (squat counts twice as much as bench). Fitness, VO2, and resting heart rate are averaged if you have them. A handicap is blended in when speed was not measured. A measured speed replaces the estimate.
3. **Flex** is L < 75, A 75–84, R 85–95, S 96–104, X at 105 mph and up. The same flex is preferred on every full-swing club. The putter shaft is stock and does not count as a mixed bag.
4. **Head family** follows handicap when you have one (players, players-distance, game improvement, super game improvement). Otherwise it follows speed and age.
5. **Three bags**, on purpose. Distance adds loft and a lighter high-launch shaft, and steps one category more forgiving. Control takes loft off and prefers a heavier low-launch shaft, one step toward a players head. Brand match is the baseline spec in the preferred brand, or the current brand, or Titleist if you named neither. Length, lie, grip, and flex stay the same across the three.
6. **Medical flags run last.** Shoulder or back: one flex softer, lighter shaft, +1° driver loft. Arthritis and wrist: larger grip. Low bone density: lighter, softer, and no players head. Missing optional data is skipped, not treated as zero.

Every constant and paragraph lives in [`app/fitting/rulebook.py`](app/fitting/rulebook.py). A saved sheet lists the rule ids it used. The same text is on `/rules` and `GET /api/rules`.

## How a fitter should use the sheet

Read the spec line first: speed (and whether it was measured), flex before and after medical, length versus that gender’s standard, lie label, grip. Then read one bag at a time. The distance bag is the high-launch build, the control bag is the heavier one, the brand-match bag is what to compare with the golfer’s current set.

Check, do not trust:

- Wrist-to-floor marked **estimated** — measure it.
- Any “mixed flex” note — the catalog did not have that flex in that shaft.
- Putter lie — it is not copied from the irons.
- A shoulder, back, arthritis, or bone-density note — confirm with the golfer before anyone orders lighter shafts or bigger grips.

Mark the sheet “taken to fitter” and leave a rating once you have been on the lie board. That feedback does not retrain the rules.

## Privacy

Medical flags and notes are optional. They are not required to get a bag.

- Set `MEDICAL_FERNET_KEY` to a Fernet key and the profile’s medical fields, plus the saved fitting snapshot, are encrypted at rest.
- Without that key the API reports `medical_storage: "plaintext"`. Fine for a laptop demo. Not fine for a shared database.
- Do not log request bodies. Anonymous sheets are unlisted links (the id is a UUID); a logged-in golfer’s sheets are visible only to that account.
- This is not a medical device and it does not clear anyone to play.

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Run with PostgreSQL (supported setup)

```bash
docker compose up --build
```

API and the fitting desk: `http://localhost:8000`  
OpenAPI: `http://localhost:8000/docs`

`docker-compose.yml` sets `DATABASE_URL` to Postgres. Change `JWT_SECRET` and set `MEDICAL_FERNET_KEY` before anyone real uses it.

Demo login after seed: `demo@example.com` / `FitSheet-demo-1`  
Sample accounts `sample01@example.com` … `sample10@example.com` share the password `Sample-fit-10`. Delete them before a production deploy.

### Without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://golf:golf@localhost:5432/golf
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")
export MEDICAL_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
alembic upgrade head
python -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The app also calls `create_all` on startup, so a fresh database comes up even if you skip Alembic. Use Alembic once you have a database you need to migrate.

If `DATABASE_URL` is unset, the process uses a SQLite file at `data/golf_demo.db` so the desk and the test suite run with no server. **PostgreSQL is the database this project is meant to run.** SQLite is a demo and test convenience; do not point a shared deployment at it.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Covered on purpose: very tall, very short, strong young player, senior with no gym data, injured player, low bone density versus a players head, preferred brand beating the current set, missing optional fields, auth, export.

## Synthetic golfers

Generate this **before** you change a fitting rule, and again after, so labels stay honest. Labels are produced by calling the same engine the API uses.

```bash
python scripts/generate_synthetic.py --n 10000 --out data/synthetic_profiles.jsonl
python scripts/generate_synthetic.py --n 50 --out data/sample_profiles.jsonl
```

Aim for 8,000–15,000 rows. The big file is gitignored. A 50-row sample is checked in.

Optional sanity check (not used for recommendations):

```bash
pip install -r requirements-ml.txt
python scripts/train_ranker.py
```

## Extend the catalog

Edit [`app/catalog/data.py`](app/catalog/data.py). Each house needs a bag it can actually fill: two drivers (players and max), a fairway with 15° and 18°, a hybrid, a utility iron, players / game-improvement / max irons, a wedge from 46° to 60°, a putter, and shafts that cover driver, fairway, hybrid, iron, wedge, and a stock putter shaft.

Restart, or run `python -m app.seed`. Seed upserts on id, so edits replace the row instead of duplicating it. Add a brand by appending to `BRANDS` and to `BRAND_ORDER` in the rulebook, and teach `canonical_brand` the alias.

## API examples

Register and save a profile:

```bash
curl -s -c /tmp/golf.jar -X POST localhost:8000/api/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"ada@example.com","password":"correct-horse"}'

curl -s -b /tmp/golf.jar -X PUT localhost:8000/api/profile \
  -H 'content-type: application/json' \
  -d '{
    "age": 46, "height_cm": 180, "weight_kg": 86, "gender": "male",
    "wrist_to_floor_cm": 89, "handicap": 14,
    "preferred_brands": ["Titleist"], "current_brand": "Callaway"
  }'
```

Fit from the saved profile, or anonymously:

```bash
curl -s -b /tmp/golf.jar -X POST localhost:8000/api/recommendations \
  -H 'content-type: application/json' \
  -d '{"use_saved_profile": true}'

curl -s -X POST localhost:8000/api/recommendations \
  -H 'content-type: application/json' \
  -d '{"profile": {"age": 74, "height_cm": 173, "gender": "male"}, "save": true}'
```

Export, feedback, catalog:

```bash
curl -s -b /tmp/golf.jar localhost:8000/api/recommendations/$ID/export.csv
curl -s -b /tmp/golf.jar localhost:8000/api/recommendations/$ID/export.pdf -o sheet.pdf
curl -s -b /tmp/golf.jar -X POST localhost:8000/api/recommendations/$ID/feedback \
  -H 'content-type: application/json' \
  -d '{"taken_to_fitter": true, "rating": 4, "fitter_notes": "Lie board agreed."}'

curl -s localhost:8000/api/catalog/brands
curl -s localhost:8000/api/catalog/heads?brand=Titleist
curl -s localhost:8000/api/rules
```

Bearer tokens work the same way: `Authorization: Bearer <access_token>`. The interactive schema is `/docs`.

## Project layout

| Path | Role |
| --- | --- |
| `app/fitting/rulebook.py` | Constants and the words a fitter audits |
| `app/fitting/specs.py` | Speed, flex, length, lie, grip, medical |
| `app/fitting/engine.py` | Three bags and the rationales |
| `app/catalog/data.py` | v1 heads and shafts |
| `app/synthetic.py` | Labelled profile generator |
| `app/api/routes.py` | REST |
| `app/web/routes.py` | Server-rendered desk |
| `alembic/` | Postgres schema migration |
| `tests/` | Rules, bags, API |

## Dependencies

Runtime: FastAPI, Uvicorn, SQLAlchemy, Alembic, psycopg, Pydantic, email-validator, PyJWT, cryptography, Jinja2, python-multipart, HTTPX.  
Dev: pytest. Optional: scikit-learn. All open source. See the requirements files for versions.

## License

MIT. See [LICENSE](LICENSE).
