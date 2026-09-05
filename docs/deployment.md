# Deployment

The dashboard is deployed to **Streamlit Community Cloud**, reading from **MongoDB Atlas**.
Both are free tiers, and the serving layer is ~2 MB against Atlas's 512 MB limit.

## What is deployed, and what is not

```
LOCAL (this machine)                     DEPLOYED (Streamlit Cloud)
─────────────────────────────────        ──────────────────────────────
PySpark 4.0 + Java 21                    no JVM, no Spark
  notebooks 01–12                          app/ only
  5.8M-row ETL, MLlib training           
  Structured Streaming producer/consumer 
        │                                
        ├── data/marts/*.parquet ────────▶ MongoDB Atlas ──▶ dashboard
        └── serving model (~2 MB) ───────▶ committed to the repo
```

**Training stays distributed; serving does not need to be.** Streamlit Cloud has no JVM, so
`data/models/best_delay_classifier` — a Spark `GBTClassificationModel` — cannot be loaded
there. `scripts/export_serving_model.py` retrains the same feature set with scikit-learn's
`HistGradientBoostingClassifier` and writes a small artefact the app can load anywhere. See
**D6** in `engineering_decisions.md` for why not LightGBM.

The Spark GBT remains the project's training artefact and the big-data result. The exported
model exists only so the dashboard can be shown to someone who does not have this repo.

---

## Step 1 — Export the serving model (local, ~2 min)

```bash
.venv/bin/python scripts/export_serving_model.py
```

Writes `data/models/serving/hgb_delay_classifier.joblib` and `serving_model.json`. The
script prints its ROC-AUC next to the Spark GBT's 0.7134. **If they differ materially, say
so in the report** — the deployed model must not silently be a different model.

`data/` is git-ignored, so the serving model must be force-added for Cloud to see it:

```bash
git add -f data/models/serving/
```

Only once. Git tracks the file from then on, so later re-exports are picked up by a normal
`git add`. The `-f` is not a workaround being repeated — it is the one-time declaration that
this particular artefact, unlike the rest of `data/`, is not regenerable by the grader.

---

## Step 2 — MongoDB Atlas (needs your account)

1. Create a free **M0** cluster at <https://cloud.mongodb.com>.
2. **Database Access** → add a user with *Read and write to any database*. Record the
   password; it goes in the connection string.
3. **Network Access** → allow `0.0.0.0/0`. Streamlit Cloud egress IPs are dynamic, so an
   allowlist of specific addresses will not work. The database holds only public flight
   statistics, so this is an acceptable exposure for this project — it would not be for
   anything with personal data.
4. Copy the connection string and put it in your local `.env`:

   ```
   MONGO_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
   MONGO_DB=airline_intel
   ```

5. Re-run **notebook 08**. It needs no code change — it reads `MONGO_URI` from the
   environment and auto-discovers every mart in `data/marts/`.
6. Verify the document counts match the local instance before moving on.

`.env` is git-ignored and must stay that way. The connection string contains a password.

---

## Step 3 — Streamlit Community Cloud (needs your account)

1. Sign in at <https://share.streamlit.io> with the GitHub account that owns the repo.
2. **New app** → repository `RohanTrivedi09/Airline-Operations-Intelligence`, branch
   `main`, main file path **`app/Home.py`**.
3. **Advanced settings → Secrets**, paste:

   ```toml
   MONGO_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
   MONGO_DB = "airline_intel"
   ```

   Streamlit exposes secrets as environment variables, which is exactly what
   `app/utils/db.py` already reads via `os.getenv`. No code change is needed.
4. Deploy. The build installs `app/requirements.txt`.

### Why `app/requirements.txt` is written by hand

It contains only what the app imports. **Never regenerate it with `pip freeze`** from the
development venv — that venv contains `pyspark` and `py4j`, and the Cloud build would try to
install a 400 MB package that needs a JVM the platform does not have.

---

## Known limitations of the deployed version

| Limitation | Why | Correct behaviour |
|---|---|---|
| **Live Monitor shows "stream not running"** | The producer and consumer are local Spark processes; nothing streams into Atlas | The page renders its explanatory idle state. The live demo runs locally. |
| **Prediction uses the exported model, not the Spark GBT** | No JVM on Cloud | The page states which model produced the number |
| **Cold start after inactivity** | Community Cloud sleeps idle apps | First load takes ~30s |

---

## Verification checklist

- [ ] All 7 pages load at the public URL with no exception
- [ ] Home reports **MongoDB** as the source, not the Parquet fallback
- [ ] Atlas document counts equal the local mart row counts
- [ ] A prediction returns a probability, and the page names the serving model
- [ ] Live Monitor shows the idle state rather than an error
- [ ] **Pause Atlas briefly and reload** — the Parquet fallback in `app/utils/db.py` should
      keep the pages rendering. This is the path that protects a live demo, so it is worth
      testing deliberately rather than assuming.
- [ ] Public URL added to `README.md` and `docs/project_report.md`
