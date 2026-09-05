"""Run every dashboard page headlessly and fail on any exception.

The README claims all seven pages execute cleanly. This is the script that checks it,
so the claim is reproducible rather than something that was true once on my machine.

What this catches: import errors, missing columns, bad `column_config`, empty-frame
crashes, anything that raises.

What it does NOT catch: anything visual. The airport map once rendered every US airport
over Africa -- a missing `center`/`zoom` is not an exception, and it passed this entire
suite. Visual checks are a separate step, not a substitute for one.

Run:  .venv/bin/python scripts/smoke_test_dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app"
PAGES = ["Home.py"] + sorted(str(p.relative_to(APP)) for p in (APP / "pages").glob("*.py"))
TIMEOUT = 90  # parquet fallback reads are slower than the 3s default


def main() -> int:
    print("=" * 68)
    print("DASHBOARD SMOKE TEST")
    print("=" * 68)

    # Start from the real entrypoint and navigate, rather than running each page as
    # its own app. Streamlit registers sibling pages relative to the entrypoint, so
    # a page opened standalone has no siblings and every st.page_link in the sidebar
    # raises StreamlitPageNotFoundError -- an artefact of the harness, not a bug in
    # the app. Driving it through switch_page tests what `streamlit run` actually does.
    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=TIMEOUT)
    failures = []

    def check(name: str) -> None:
        if at.exception:
            msgs = "; ".join(e.message for e in at.exception)
            failures.append((name, msgs))
            print(f"  FAIL  {name:26} {msgs}")
        else:
            widgets = len(at.dataframe) + len(at.markdown) + len(at.metric)
            print(f"  ok    {name:26} {len(at.error)} errors, "
                  f"{len(at.warning)} warnings, {widgets} elements, "
                  f"{len(at.sidebar.markdown)} sidebar blocks")

    at.run()
    check("Home.py")

    for rel in PAGES[1:]:
        try:
            at.switch_page(f"pages/{rel}" if not rel.startswith("pages/") else rel)
            at.run()
        except Exception as exc:                      # noqa: BLE001 - report, don't raise
            failures.append((rel, f"{type(exc).__name__}: {exc}"))
            print(f"  FAIL  {rel:26} {type(exc).__name__}: {exc}")
            continue
        check(rel)

    print("-" * 68)
    if failures:
        print(f"FAIL - {len(failures)} of {len(PAGES)} pages raised")
        return 1
    print(f"PASS - all {len(PAGES)} pages executed with zero exceptions")
    print("\nNote: this proves the pages RUN. It does not prove they look right.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
