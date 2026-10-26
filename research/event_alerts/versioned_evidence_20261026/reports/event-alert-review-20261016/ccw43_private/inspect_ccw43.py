"""Offline private data schema validation; no network calls or raw case output."""
import json, pathlib, hashlib, sys
p = pathlib.Path(__file__).resolve().parents[1]
files = {
"dataset": p/"v2_private_sanitized.json",
"A": p/"reviewer_A_significance_for_pr1.json",
"B": p/"reviewer_B_significance_for_pr1.json",
"C": p/"ccw41_private/reviewer_c_sealed.json",
"owner": p/"ccw41_private/owner_reference_candidate_v1_20261022.json",
"manifest": p/"ccw16_private/pilot-manifest.json",
"ledger": p/"ccw16_private/pilot-ledger-complete_20261023_120.json",
"snapshot": p/"ccw16_private/pilot-ledger-stopped_20261022_86.json",
}
for n, f in files.items():
    obj = json.loads(f.read_text(encoding="utf-8"))
    print(n, "SHA", hashlib.sha256(f.read_bytes()).hexdigest(), "ROOT", list(obj), "ITEMS", {k:(len(v) if isinstance(v,list) else type(v).__name__) for k,v in obj.items() if k in ["cases","case_labels","results","labels","attempts"]})
    if n == "dataset": print("dataset.first", sorted(obj["cases"][0]), "digest", obj.get("dataset_sha256"))
    if n == "A": print("A.first", sorted(obj["labels"][0]))
    if n == "owner": print("owner.first", sorted(obj["case_labels"][0]))
    if n == "ledger": print("ledger.first", sorted(obj["attempts"][0]))
    if n == "manifest": print("manifest.first", sorted(obj["cases"][0]), "metadata", {k:v for k,v in obj.items() if k!="cases"})
