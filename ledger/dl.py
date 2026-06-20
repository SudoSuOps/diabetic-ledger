#!/usr/bin/env python3
"""
DiabeticLedger — the real defendable truth
==========================================

The public, hash-chained giving ledger for OpenDiabetic / LocalDiabetic.
Follow every dollar: donation -> hosted rig -> income -> give -> job. Every hop
is a receipt; the whole thing is a tamper-evident chain anyone can verify —
including in their own browser at diabeticledger.com.

No PHI ever lands here. This is the MONEY/GIVING layer (donations, assets,
compute income, gives, jobs), not the health layer. Recipients are first-name
or role only.

  dl.py donation --donor Frank --form compute --item "RTX 5090" --value 2000 --note "host at home"
  dl.py asset    --id frank-5090 --from 1 --type gpu --hosted-by Frank --location "Frank's home"
  dl.py income   --asset frank-5090 --source "research dev" --amount 120 --period "year 1"
  dl.py give     --to Mary --need "Synology NAS" --value 400 --funded income --by OpenDiabetic
  dl.py job      --worker Joe --task "set up Mary's NAS" --pay 50 --for 4
  dl.py export   # writes ../ledger.json for the public site
  dl.py verify

Stdlib only. Keep all values ASCII so the in-browser verifier matches byte-for-byte.
"""

import argparse
import hashlib
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "giving.jsonl")
PUBLIC = os.path.join(os.path.dirname(HERE), "ledger.json")
ZERO = "0" * 64


def canon(body):
    # MUST match the browser verifier: sorted keys, no spaces, ASCII-escaped.
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(prev, body):
    return hashlib.sha256((prev + canon(body)).encode("utf-8")).hexdigest()


def load():
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def append(fields):
    led = load()
    prev = led[-1]["hash"] if led else ZERO
    body = {"seq": len(led), "prev_hash": prev, **fields}
    rec = {**body, "hash": _hash(prev, body)}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=True) + "\n")
    return rec


def verify():
    led = load()
    prev = ZERO
    for rec in led:
        body = {k: v for k, v in rec.items() if k != "hash"}
        if rec.get("prev_hash") != prev or _hash(prev, body) != rec.get("hash"):
            return False, rec["seq"]
        prev = rec["hash"]
    return True, len(led)


def now():
    return datetime.now().strftime("%Y-%m-%d")


# ── commands ─────────────────────────────────────────────────────────────────
def c_donation(a):
    r = append({"kind": "donation", "date": a.date or now(), "donor": a.donor,
                "form": a.form, "item": a.item, "value_usd": a.value, "note": a.note})
    print(f"#{r['seq']} donation: {a.donor} gave {a.item} (${a.value}) [{a.form}]")


def c_asset(a):
    r = append({"kind": "asset", "date": a.date or now(), "asset_id": a.id,
                "from_donation": a.from_seq, "asset_type": a.type,
                "hosted_by": a.hosted_by, "location": a.location})
    print(f"#{r['seq']} asset: {a.id} ({a.type}) hosted by {a.hosted_by} @ {a.location}")


def c_income(a):
    r = append({"kind": "income", "date": a.date or now(), "asset_id": a.asset,
                "source": a.source, "amount_usd": a.amount, "period": a.period})
    print(f"#{r['seq']} income: {a.asset} earned ${a.amount} from {a.source} ({a.period})")


def c_give(a):
    r = append({"kind": "give", "date": a.date or now(), "recipient": a.to,
                "need": a.need, "value_usd": a.value, "funded_from": a.funded,
                "fulfilled_by": a.by})
    print(f"#{r['seq']} give: {a.need} -> {a.to} (${a.value}) by {a.by}")


def c_job(a):
    r = append({"kind": "job", "date": a.date or now(), "worker": a.worker,
                "task": a.task, "pay_usd": a.pay, "for_give": a.for_seq})
    print(f"#{r['seq']} job: {a.worker} paid ${a.pay} — {a.task}")


def c_verify(a):
    ok, n = verify()
    print(f"{'OK' if ok else 'BROKEN at #'+str(n)}: {n} receipts" if ok else f"BROKEN at #{n}")


def c_export(a):
    led = load()
    ok, n = verify()
    tot = {"donated_usd": 0, "earned_usd": 0, "given_usd": 0, "jobs_paid_usd": 0,
           "donations": 0, "assets": 0, "gives": 0, "jobs": 0}
    for r in led:
        k = r["kind"]
        if k == "donation": tot["donated_usd"] += r["value_usd"]; tot["donations"] += 1
        elif k == "asset": tot["assets"] += 1
        elif k == "income": tot["earned_usd"] += r["amount_usd"]
        elif k == "give": tot["given_usd"] += r["value_usd"]; tot["gives"] += 1
        elif k == "job": tot["jobs_paid_usd"] += r["pay_usd"]; tot["jobs"] += 1
    out = {"name": "DiabeticLedger", "tagline": "the real defendable truth",
           "generated": now(), "chain_ok": ok, "count": len(led),
           "totals": tot, "receipts": led}
    with open(PUBLIC, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=True)
    print(f"exported {len(led)} receipts -> {PUBLIC}  (chain {'intact' if ok else 'BROKEN'})")


def main():
    p = argparse.ArgumentParser(description="DiabeticLedger — the giving ledger")
    p.add_argument("--date", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("donation"); d.set_defaults(fn=c_donation)
    d.add_argument("--donor", required=True); d.add_argument("--form", required=True, choices=["cash", "compute", "device"])
    d.add_argument("--item", required=True); d.add_argument("--value", type=int, required=True); d.add_argument("--note", default="")

    s = sub.add_parser("asset"); s.set_defaults(fn=c_asset)
    s.add_argument("--id", required=True); s.add_argument("--from", dest="from_seq", type=int, default=-1)
    s.add_argument("--type", required=True); s.add_argument("--hosted-by", required=True); s.add_argument("--location", default="")

    i = sub.add_parser("income"); i.set_defaults(fn=c_income)
    i.add_argument("--asset", required=True); i.add_argument("--source", required=True)
    i.add_argument("--amount", type=int, required=True); i.add_argument("--period", default="")

    g = sub.add_parser("give"); g.set_defaults(fn=c_give)
    g.add_argument("--to", required=True); g.add_argument("--need", required=True); g.add_argument("--value", type=int, required=True)
    g.add_argument("--funded", default="income", choices=["income", "donation", "in-kind"]); g.add_argument("--by", default="OpenDiabetic")

    j = sub.add_parser("job"); j.set_defaults(fn=c_job)
    j.add_argument("--worker", required=True); j.add_argument("--task", required=True)
    j.add_argument("--pay", type=int, required=True); j.add_argument("--for", dest="for_seq", type=int, default=-1)

    sub.add_parser("verify").set_defaults(fn=c_verify)
    sub.add_parser("export").set_defaults(fn=c_export)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
