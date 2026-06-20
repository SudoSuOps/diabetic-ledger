/* DiabeticLedger — client-side renderer + hash-chain verifier.
   The verifier re-implements the exact canonical form the Python ledger uses
   (sorted keys, no spaces, ASCII-escaped) so it reproduces every SHA-256 link
   independently — in the visitor's own browser. Trust no one; recompute it.
   Runs in the browser AND in Node (both expose crypto.subtle) for testing. */

const ZERO = "0".repeat(64);

function pyString(s) {
  // Match Python json.dumps(ensure_ascii=True): JSON escaping + \uXXXX for non-ASCII.
  return JSON.stringify(s).replace(/[\u007f-\uffff]/g,
    c => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
}
function pyValue(v) {
  if (v === null) return "null";
  if (typeof v === "number") return String(v);
  if (typeof v === "boolean") return v ? "true" : "false";
  return pyString(v);
}
function canonicalize(obj) {
  // flat receipt body -> {"k":v,...} with sorted keys, no spaces (matches Python)
  return "{" + Object.keys(obj).sort()
    .map(k => pyString(k) + ":" + pyValue(obj[k])).join(",") + "}";
}
async function sha256hex(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
async function verifyChain(receipts) {
  let prev = ZERO, ok = true, brokenAt = -1;
  const per = [];
  for (const rec of receipts) {
    const body = { ...rec }; delete body.hash;
    const h = await sha256hex(prev + canonicalize(body));
    const good = rec.prev_hash === prev && h === rec.hash;
    per.push(good);
    if (!good && ok) { ok = false; brokenAt = rec.seq; }
    prev = rec.hash;
  }
  return { ok, brokenAt, per };
}

/* ---------- browser rendering ---------- */
if (typeof document !== "undefined") {
  const $ = s => document.querySelector(s);
  const money = n => "$" + Number(n).toLocaleString("en-US");

  function lineFor(r) {
    switch (r.kind) {
      case "donation": return `<b>${esc(r.donor)}</b> donated ${esc(r.item)} <span class="muted">· ${esc(r.note || r.form)}</span>`;
      case "asset":    return `<b>${esc(r.asset_id)}</b> (${esc(r.asset_type)}) hosted by <b>${esc(r.hosted_by)}</b> @ ${esc(r.location)}`;
      case "income":   return `<b>${esc(r.asset_id)}</b> earned from ${esc(r.source)} <span class="muted">· ${esc(r.period)}</span>`;
      case "give":     return `${esc(r.need)} → <b>${esc(r.recipient)}</b> <span class="muted">· by ${esc(r.fulfilled_by)}, funded ${esc(r.funded_from)}</span>`;
      case "job":      return `<b>${esc(r.worker)}</b> paid — ${esc(r.task)}`;
      default:         return esc(r.kind);
    }
  }
  function amtFor(r) {
    if (r.kind === "donation") return money(r.value_usd);
    if (r.kind === "income")   return "+" + money(r.amount_usd);
    if (r.kind === "give")     return r.value_usd ? money(r.value_usd) : "in-kind";
    if (r.kind === "job")      return money(r.pay_usd);
    return "";
  }
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function renderTotals(t) {
    const cards = [
      ["don", money(t.donated_usd), "donated"],
      ["earn", money(t.earned_usd), "compute earned"],
      ["give", money(t.given_usd), "given back"],
      ["", t.jobs, "jobs created"],
      ["", t.gives, "gives fulfilled"],
    ];
    $("#totals").innerHTML = cards.map(([c, n, l]) =>
      `<div class="card ${c}"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");
  }
  function renderChain(receipts, per) {
    $("#chain").innerHTML = receipts.map((r, i) => {
      const v = per ? `<span class="v ${per[i] ? "ok" : "bad"}">${per[i] ? "✓ link verified" : "✗ BROKEN"}</span>` : "";
      return `<div class="rec ${r.kind}">
        <div class="seq">#${r.seq}</div>
        <div class="kind">${r.kind}</div>
        <div class="body">${lineFor(r)}</div>
        <div class="amt">${amtFor(r)}</div>
        <div class="hash">sha256 ${r.hash.slice(0, 24)}… ${v}</div>
      </div>`;
    }).join("");
  }
  async function runVerify(receipts) {
    const el = $("#chainstate");
    el.className = "chainstate checking"; el.textContent = "verifying every link in your browser…";
    const { ok, brokenAt, per } = await verifyChain(receipts);
    renderChain(receipts, per);
    if (ok) { el.className = "chainstate ok"; el.textContent = `✓ chain intact — ${receipts.length} receipts, every SHA-256 link recomputed in your browser`; }
    else { el.className = "chainstate bad"; el.textContent = `✗ chain BROKEN at receipt #${brokenAt} — tampering detected`; }
  }

  // Single source of truth = the hive's giving ledger (live). If the hive is
  // unreachable, fall back to the committed snapshot so the proof is always up.
  const HIVE = "https://hive.opendiabetic.com/api/giving";
  async function loadLedger() {
    try {
      const r = await fetch(HIVE, { cache: "no-store" });
      if (r.ok) { const d = await r.json(); if (Array.isArray(d.receipts)) return { ...d, source: "live" }; }
    } catch (e) { /* fall through to snapshot */ }
    const d = await (await fetch("ledger.json", { cache: "no-store" })).json();
    return { ...d, source: "snapshot" };
  }
  async function init() {
    const data = await loadLedger();
    renderTotals(data.totals);
    renderChain(data.receipts, null);
    const src = $("#source");
    if (src) src.textContent = data.source === "live"
      ? "live from the hive · hive.opendiabetic.com"
      : "from the last published snapshot";
    $("#reverify").addEventListener("click", () => runVerify(data.receipts));
    runVerify(data.receipts);
  }
  document.addEventListener("DOMContentLoaded", init);
}

if (typeof module !== "undefined") module.exports = { canonicalize, sha256hex, verifyChain };
