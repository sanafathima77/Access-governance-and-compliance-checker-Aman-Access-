"""Run AmanAccess.

    python run_demo.py                          synthetic bank, seed 42, writes results/
    python run_demo.py --seed 7                 a different synthetic bank
    python run_demo.py --export-sample sample_data    also save the synthetic tables as CSV files
    python run_demo.py --data-dir my_export     analyse your own CSV export (see README for the format)
    python run_demo.py --data-dir my_export --asof 2026-09-01

Outputs (in --out, default results/): findings.csv, queue.csv, summary.json, dashboard.html
"""
import argparse
import sys
from datetime import date

from amanaccess.generate import ASOF, generate
from amanaccess.io_csv import read_dataset, write_dataset
from amanaccess.report import build_data, write_outputs
from amanaccess.review import build_queue
from amanaccess.rules import Settings, run_rules
from amanaccess.scoring import risk_tables, score_findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="AmanAccess: access-governance checks for a bank")
    ap.add_argument("--seed", type=int, default=42, help="seed for the synthetic bank (default 42)")
    ap.add_argument("--data-dir", help="folder with hr.csv, accounts.csv, assignments.csv instead of synthetic data")
    ap.add_argument("--asof", help="snapshot date YYYY-MM-DD (default: from meta.json, else today; synthetic: 2026-09-01)")
    ap.add_argument("--out", default="results", help="output folder (default results)")
    ap.add_argument("--export-sample", metavar="DIR", help="also write the synthetic tables to DIR as CSV")
    args = ap.parse_args(argv)

    asof = date.fromisoformat(args.asof) if args.asof else None
    if args.data_dir:
        try:
            ds, truth = read_dataset(args.data_dir, asof), None
        except (OSError, ValueError) as exc:
            print(f"Could not read the data: {exc}", file=sys.stderr)
            return 2
        synthetic = False
    else:
        ds, truth = generate(args.seed, asof or ASOF)
        synthetic = True
        if args.export_sample:
            write_dataset(ds, args.export_sample)
            print(f"Synthetic tables written to {args.export_sample}/")

    settings = Settings()
    findings = score_findings(run_rules(ds, settings))
    tables = risk_tables(findings, ds)
    queue = build_queue(ds, findings)
    data = build_data(ds, findings, tables, queue, settings, truth, synthetic)
    out = write_outputs(args.out, data, findings, queue)

    k = data["kpis"]
    print(f"\nAmanAccess  snapshot {ds.asof}  ({'synthetic fictional bank, seed ' + str(args.seed) if synthetic else args.data_dir})")
    print(f"{k['people']} people, {k['accounts']} accounts ({k['active_accounts']} active), {k['assignments']} assignments\n")
    print(f"{'rule':<5}{'finding':<38}{'count':>6}   critical high medium low")
    for r in data["rules"]:
        s = r["by_severity"]
        print(f"{r['id']:<5}{r['name']:<38}{r['count']:>6}   {s['critical']:>8}{s['high']:>5}{s['medium']:>7}{s['low']:>4}")
    print(f"\nTotal findings: {k['findings']} on {k['accounts_flagged']} accounts "
          f"({k['critical']} critical, {k['high']} high, {k['medium']} medium, {k['low']} low)")
    print(f"Review queue: {k['queue_items']} items for {len(data['workload'])} reviewers "
          f"(every flagged item plus administrator access; {k['privileged_assignments']} administrator assignments exist)")
    if data["selfcheck"]:
        planted = sum(r["planted"] for r in data["selfcheck"])
        correct = sum(r["true_positive"] for r in data["selfcheck"])
        extra = sum(r["false_positive"] for r in data["selfcheck"])
        look = sum(r["lookalikes"] for r in data["selfcheck"])
        wrong = sum(r["lookalikes_flagged"] for r in data["selfcheck"])
        print(f"Self-check against the answer key: {correct} of {planted} planted problems found, {extra} extra, "
              f"{wrong} of {look} decoys wrongly flagged")
    print(f"\nFiles written to {out}/  (open dashboard.html in a browser)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
