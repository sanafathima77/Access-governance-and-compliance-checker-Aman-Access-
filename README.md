# AmanAccess

An access-governance checker for a bank. It reads three tables (HR records, accounts, permissions), runs nine
rules that find the access problems auditors ask about, scores the risk, builds a review queue for managers,
and produces a browser dashboard. *Aman* is Arabic for safety.

Everything runs on the Python standard library. There is nothing to install.

**Live dashboard:** open `docs/index.html` (double-click it). Once this repo is on GitHub, turn on GitHub Pages
(Settings, Pages, deploy from branch `main`, folder `/docs`) to get a public link.

## Why this project

Banks are audited on one question again and again: *who has access to what, and should they?* In Oman, banks
follow the Central Bank of Oman's cyber security and resilience framework, which includes access control
management and third-party controls, and most also align to ISO/IEC 27001. The failures auditors find are
predictable: people who left but still have logins, people who changed department and kept their old access,
administrators without multi-factor login, one person able to both create and approve a payment. AmanAccess
turns each of those into a rule that can be run, tested and explained.

## Quick start

Easiest on Windows: double-click `run_windows.bat`. It runs the tests, runs the demo and opens the dashboard.
It needs Python 3.9 or newer (tested on 3.11) and nothing else.

By hand, from inside the AmanAccess folder:

```
python -m unittest discover -s tests          # 44 tests
python run_demo.py                            # synthetic bank, writes results/
python run_demo.py --export-sample sample_data   # also saves the synthetic tables as CSV
python run_demo.py --data-dir sample_data     # analyse a CSV export instead
```

On macOS or Linux use `python3`. Outputs land in `results/`: `dashboard.html`, `findings.csv`, `queue.csv`,
`summary.json`.

## What the demo bank looks like

A fictional bank with 10 departments, 13 applications in three criticality tiers, and about 50 entitlements
(permissions), built by `amanaccess/generate.py` from a seed (default 42). People appear only as pseudonymous
IDs such as `E0042` and `X017`.

| | |
|---|---|
| People | 580 (520 employees including 50 who have left, 60 contractors) |
| Accounts | 3,034 (2,814 active) |
| Permission assignments | 4,036 |
| Findings | 118: 30 critical, 41 high, 35 medium, 12 low |
| Review queue | 178 items for 52 reviewers |
| Runtime | about 0.1 seconds for the whole run |

## The nine rules

| Rule | Finds | ISO/IEC 27001:2022 Annex A |
|---|---|---|
| R1 Leaver keeps access | Employee left more than 1 day ago; account still active | A.5.18, A.6.5 |
| R2 Orphan account | Personal account with no matching person in HR | A.5.16, A.5.18 |
| R3 Mover keeps old access | Changed department more than 30 days ago; still holds the old department's access | A.5.18, A.6.5 |
| R4 Dormant account | Active account unused for more than 90 days (never used: counted from creation) | A.5.16, A.5.18 |
| R5 Privileged without MFA | Personal account with administrator-level access and no multi-factor login | A.8.2, A.8.5 |
| R6 Segregation of duties | One person holds both sides of a conflicting pair (for example create and approve a payment) | A.5.3 |
| R7 Outside department scope | Holds an entitlement that is not meant for their department | A.5.15, A.5.18 |
| R8 Service account without owner | Service or shared account with no owner, or an owner who has left | A.5.16, A.5.9 |
| R9 Expired contractor | Contract ended more than 1 day ago; account still active | A.5.18, A.6.5, A.5.19 |

The mapping to the Central Bank of Oman framework (Access Control Management for R1 to R8, Third Party Supply
Chain for R9) is **indicative**. Check control numbers and wording against the current official texts before
citing them anywhere formal.

Design choices that matter:

- **Each problem is reported once.** R3 owns a mover's old-department access and R7 stays silent about it; R1
  owns leavers so R4, R6 and R7 skip them; R9 owns expired contractors so R4 skips them. Overlaps would inflate
  the counts.
- **Rules are deterministic.** R7 compares an entitlement's declared scope with the person's department. It does
  not guess "unusual" access from peer statistics, because a statistical rule flags rare-but-legitimate access
  and cannot explain itself to an auditor.
- **Grace periods and exceptions are respected.** A leaver has 1 day, a mover 30 days, a contractor 1 day. People
  on approved leave are not dormant. An approved segregation-of-duties exception suppresses R6.
- **Only active accounts count.** A disabled account cannot be used, so it is not a finding.
- **R5 covers personal accounts.** Service accounts cannot answer an MFA prompt; R8 (ownership) is their control.

## Scoring and the review queue

`finding score = severity weight x application tier factor`, with critical 10, high 6, medium 3, low 1, and tier 1
(core banking, payments, cards, treasury, directory, deployment) x1.3, tier 2 x1.0, tier 3 x0.8. A person's risk
is the sum of their scores, capped at 100. The weights are judgement calls, not measurements; they live in
`catalog.py` and a bank would set its own.

The review queue contains every flagged item plus every administrator-level assignment (recertification), sorted
by priority. The reviewer is the person's manager. Leavers, orphans and ownerless accounts, and anyone whose manager
has left or is on leave, go to `IAM-OPS`. In the dashboard a reviewer can mark each item Keep or Revoke (saved in
the browser only) and export the decisions.

## How it is tested

The generator first builds a clean bank and then plants known problems **and known decoys**: leavers inside the
grace period, movers inside theirs, employees on leave with stale logins, users 90 days idle (not over the limit),
approved SoD exceptions. The list of what was planted is the answer key.

- Every rule is checked on small hand-built organisations, including the exact boundary days (leaver 1 vs 2 days,
  mover 30 vs 31, dormant 90 vs 91, contractor 1 vs 2).
- On the generated bank (seeds 42, 7 and 2026) the engine finds all 118 planted problems for seed 42, reports
  nothing extra, and flags none of the 429 decoys.
- A completely clean bank produces zero findings.
- The catalog is validated: role templates stay inside department scope and never grant a conflicting pair.
- CSV round trip, malformed-file errors, scoring, queue rules and the dashboard's data embedding are covered.
- As a spot check, deliberately breaking seven separate rule conditions made the suite fail each time.

**What the self-check does and does not show.** The dashboard's "Engine self-check" table (118 of 118) shows that the
rules do what they are written to do, on data built to test them. It is not a detection rate for a real bank. Real
data is messier, and its answer key is the auditor's judgement.

## Using your own data

Provide a folder with three CSV files (dates as `YYYY-MM-DD`, empty cell = none, `mfa` = `true` or `false`), plus an
optional `meta.json` such as `{"asof": "2026-09-01"}` holding the snapshot date:

```
hr.csv           emp_id, dept, level, manager_id, kind, status, hire_date, term_date, prev_dept, dept_change_date, contract_end
accounts.csv     account_id, app, kind, emp_id, owner_id, status, created, last_login, mfa
assignments.csv  account_id, entitlement, granted, exception_ref
```

`kind` is EMPLOYEE or CONTRACTOR in `hr.csv` and PERSONAL, SERVICE or SHARED in `accounts.csv`; `status` is ACTIVE,
ON_LEAVE or TERMINATED for people and ACTIVE or DISABLED for accounts. Then run
`python run_demo.py --data-dir your_folder`. Application and entitlement codes must exist in `amanaccess/catalog.py`
(edit it to describe your bank's systems, scopes and conflicting pairs). Errors name the file and line. `sample_data/`
is a working example.

## Limits

- It analyses exports. It does not connect to live systems and never changes an account.
- It checks rules that can be stated exactly. It will not catch access that the role model allows but that is wrong
  for a particular person.
- Service and shared accounts are checked for ownership only, not activity.
- Segregation-of-duties pairs are within one application in this catalog; conflicts that span applications need
  extra pairs and a small change to R6.
- All data here is generated. Nothing in this repo is real customer, employee or bank data.

## Files

- `amanaccess/catalog.py`: departments, applications, entitlements, conflicting pairs, role templates, control mapping
- `amanaccess/generate.py`: synthetic bank with planted problems, decoys and the answer key
- `amanaccess/rules.py`: the nine rules; `scoring.py`: risk scores; `review.py`: the review queue
- `amanaccess/io_csv.py`: CSV reader and writer; `report.py` and `dashboard_template.html`: outputs
- `run_demo.py`: command line; `run_windows.bat`: one-click run on Windows
- `tests/test_amanaccess.py`: 44 tests
- `sample_data/`: the demo bank as CSV; `results/`: its outputs; `docs/index.html`: the dashboard for GitHub Pages

## License

MIT, see `LICENSE`.
