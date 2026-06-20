# DiabeticLedger — the real defendable truth

The public, hash-chained **giving ledger** for [OpenDiabetic](https://github.com/SudoSuOps/OpenDiabetic-Compute)
& [LocalDiabetic](https://github.com/SudoSuOps/LocalDiabetic-Home-Vault). Live at **diabeticledger.com**.

> Follow every dollar, end to end: **donation → hosted rig → income → give → job.**
> No vanity metrics. No black box. And you don't take our word for it —
> **your browser verifies the chain itself.**

---

## Why this exists

Every "we give it all back" outfit eventually smells like a rug pull, because nobody can
see the money. We don't do trust-me-bro. We are math and code. So the anti-rug-pull isn't
a promise — it's a **tamper-evident ledger** anyone can verify.

A donation isn't burned here; it's planted. $100 buys a GPU, the GPU earns on the
marketplace, the net income buys the shoes and ships them free — and the GPU keeps
working. Read the full model: [MODEL.md in the OpenDiabetic repo](https://github.com/SudoSuOps/OpenDiabetic-Compute/blob/main/MODEL.md).

## What's in the chain

Five kinds of receipt, each linked to the one before by SHA-256:

| kind | meaning |
|---|---|
| `donation` | cash, compute, or a device came in |
| `asset` | a rig was placed (often **hosted in the donor's own home** — we route, we don't warehouse) |
| `income` | an asset earned on the marketplace (research / business, for a fee) |
| `give` | income recycled into a real need (a NAS, shoes, a ride, a cookbook) |
| `job` | the give created paid work for a neighbor |

**No PHI ever appears here.** This is the money layer, not the health layer — patient
records live on the patient's own box and never touch this ledger. Recipients are
first-name or role only.

## Verify it yourself

The page recomputes every hash in your browser (Web Crypto) against the published
receipts. Change one character in `ledger.json` and the chain breaks at that receipt.
Proven: the same verifier runs in the browser and in Node, and it catches a tampered
amount.

## Add to the ledger

```bash
cd ledger
python3 dl.py donation --donor Frank --form compute --item "RTX 5090" --value 2000 --note "hosts at home"
python3 dl.py asset    --id frank-5090 --from 1 --type gpu --hosted-by Frank --location "Frank's home"
python3 dl.py income   --asset frank-5090 --source "indie dev" --amount 120 --period "year 1"
python3 dl.py give     --to Mary --need "Synology NAS" --value 400 --funded income --by OpenDiabetic
python3 dl.py job      --worker Joe --task "set up Mary's NAS" --pay 50 --for 8
python3 dl.py export    # regenerates ../ledger.json for the site
python3 dl.py verify
```

Stdlib only — no pip install. `ledger/giving.jsonl` is the source of truth; `ledger.json`
is the exported public copy the site reads.

## Deploy (Cloudflare Pages)

Static site at the repo root — no build step.
- **Build command:** *(none)*
- **Output directory:** `/`

`index.html` + `app.js` + `style.css` + `ledger.json`. That's it.

---

*OpenDiabetic is the hive · LocalDiabetic is the healers · **DiabeticLedger is the proof.***
