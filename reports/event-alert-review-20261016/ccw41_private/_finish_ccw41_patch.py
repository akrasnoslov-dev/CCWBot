from pathlib import Path
import shutil

root = Path(r"D:\Projects\CCWBot")
p = root / "scripts/ccw41_reviewer_c_audit.py"
source = p.read_text(encoding="utf-8")
backup = root / "reports/event-alert-review-20261016/ccw41_private/_working_code_backup.py"
if not backup.exists():
    shutil.copyfile(p, backup)

def change(before, after):
    global source
    if source.count(before) != 1:
        raise RuntimeError(f"Expected one matching span, got {source.count(before)}: {before[:120]!r}")
    source = source.replace(before, after, 1)

change(
'EXPECTED_AB_CONFLICTS = 99\n',
'''EXPECTED_AB_CONFLICTS = 99
FROZEN_RUBRIC_SHA256 = "2615ebb4d4bd0fd53f41f0fe4db260f092a2e7ea7d430e857d9bfbaf102027b0"
FROZEN_SCHEMA_SHA256 = "e2acbfdc878d71071fcf95e93017035200860e4839dac2941a1bd84b4334cc40"
FROZEN_PROMPT_SHA256 = "d5169b9a87442da61807cbb9841c865b3c134d9df3b79485c24e56d4749199c2"
''')
change(
'    "provider", "model", "reasoning_effort", "interface", "data_transfer_approval",\n',
'    "provider", "model", "reasoning_effort", "interface", "data_transfer_approval",\n    "model_identity_verification",\n')
change(
'    schema_json = json.loads(schema)\n    if schema_json.get("title") != "CCW-41 Reviewer C batch result":\n        raise ValueError("Unexpected Reviewer C schema")\n    prompt = _operator_prompt(rubric, schema)\n    prompt_sha256 = hashlib.sha256(prompt.encode()).hexdigest()\n',
'''    schema_json = json.loads(schema)
    if schema_json.get("title") != "CCW-41 Reviewer C batch result":
        raise ValueError("Unexpected Reviewer C schema")
    prompt = _operator_prompt(rubric, schema)
    prompt_sha256 = hashlib.sha256(prompt.encode()).hexdigest()
    if (
        _sha256_file(RUBRIC_PATH) != FROZEN_RUBRIC_SHA256
        or _sha256_file(SCHEMA_PATH) != FROZEN_SCHEMA_SHA256
        or prompt_sha256 != FROZEN_PROMPT_SHA256
    ):
        raise ValueError("Frozen CCW-41 v1 protocol differs from approved fingerprints")
''')
change(
'    if manifest.get("protocol_version") != "ccw41-v1" or manifest.get("case_count") != 200:\n        raise ValueError("Invalid CCW-41 manifest")\n',
'''    if manifest.get("protocol_version") != "ccw41-v1" or manifest.get("case_count") != 200:
        raise ValueError("Invalid CCW-41 manifest")
    pinned = {
        "rubric_sha256": FROZEN_RUBRIC_SHA256,
        "result_schema_sha256": FROZEN_SCHEMA_SHA256,
        "operator_prompt_sha256": FROZEN_PROMPT_SHA256,
    }
    if any(manifest.get(field) != value for field, value in pinned.items()):
        raise ValueError("Frozen CCW-41 v1 protocol fingerprint mismatch")
''')
anchor='\n\nREFERENCE_PART = re.compile'
helper='''

def _verified_packets(private_dir: Path, manifest: dict) -> tuple[dict, dict]:
    packets: dict[str, dict] = {}
    expected_by_batch: dict[str, set[str]] = {}
    mapped = {row["opaque_id"]: row for row in manifest["cases"]}
    if len(mapped) != 200:
        raise ValueError("Duplicate or missing cases in the frozen manifest")
    seen: set[str] = set()
    for batch in manifest["batches"]:
        batch_id = batch["batch_id"]
        if batch_id in packets:
            raise ValueError("Duplicate frozen batch")
        path = private_dir / "packets" / f"{batch_id}.json"
        if _sha256_file(path) != batch["packet_sha256"]:
            raise ValueError("Frozen review packet fingerprint mismatch")
        packet = json.loads(path.read_text(encoding="utf-8"))
        if (
            packet.get("batch_id") != batch_id
            or packet.get("protocol_version") != "ccw41-v1"
            or packet.get("dataset_sha256") != manifest["dataset_sha256"]
            or packet.get("rubric_sha256") != manifest["rubric_sha256"]
            or packet.get("result_schema_sha256") != manifest["result_schema_sha256"]
        ):
            raise ValueError("Frozen packet protocol mismatch")
        cards = {row["case_id"]: row for row in packet["cases"]}
        ids = set(cards)
        if (
            len(cards) != len(packet["cases"])
            or len(cards) != batch["case_count"]
            or len(cards) != len(batch["opaque_ids"])
            or ids != set(batch["opaque_ids"])
            or ids & seen
        ):
            raise ValueError("Frozen packet has missing, repeated, or misbucketed cases")
        for case_id, card in cards.items():
            if (
                case_id not in mapped
                or mapped[case_id]["batch_id"] != batch_id
                or card["input_sha256"] != mapped[case_id]["input_sha256"]
                or card["symbol"] != mapped[case_id]["symbol"]
            ):
                raise ValueError("Frozen packet case mapping mismatch")
        packets[batch_id] = cards
        expected_by_batch[batch_id] = ids
        seen.update(ids)
    if seen != set(mapped):
        raise ValueError("Frozen packet coverage mismatch")
    return packets, expected_by_batch


def _verify_run_metadata(run: dict) -> None:
    if (
        not isinstance(run, dict)
        or not RUN_METADATA_FIELDS.issubset(run)
        or any(not isinstance(run[key], str) or not run[key].strip()
               for key in RUN_METADATA_FIELDS)
    ):
        raise ValueError("Complete Reviewer C output requires verified run metadata")
    for name in ("request_errors", "measured_tokens"):
        value = run.get(name)
        if value is not None and (
            type(value) is not int or value < 0
        ):
            raise ValueError(f"Invalid Reviewer C {name}")
    cost = run.get("measured_cost_usd")
    if cost is not None and (
        type(cost) not in (int, float) or not 0 <= cost < float("inf")
    ):
        raise ValueError("Invalid Reviewer C measured cost")


def _verify_sealed_record(private_dir: Path, manifest: dict, sealed: dict) -> None:
    run = json.loads((private_dir / "run_manifest.json").read_text(encoding="utf-8"))
    _verify_run_metadata(run)
    expected = {
        "protocol_version": "ccw41-v1",
        "dataset_sha256": manifest["dataset_sha256"],
        "rubric_sha256": manifest["rubric_sha256"],
        "result_schema_sha256": manifest["result_schema_sha256"],
        "operator_prompt_sha256": manifest["operator_prompt_sha256"],
        "batch_count": len(manifest["batches"]),
        "result_count": 200,
        "reviewer_c_sha256": _sha256_file(private_dir / "reviewer_c_sealed.json"),
    }
    if any(run.get(key) != value for key, value in expected.items()):
        raise ValueError("Sealed Reviewer C provenance/hash mismatch")
    if not isinstance(run.get("sealed_at"), str) or not run["sealed_at"].strip():
        raise ValueError("Missing Reviewer C seal timestamp")
    if (
        sealed.get("protocol_version") != "ccw41-v1"
        or sealed.get("dataset_sha256") != manifest["dataset_sha256"]
        or sealed.get("result_count") != 200
        or not isinstance(sealed.get("results"), list)
        or len(sealed["results"]) != 200
    ):
        raise ValueError("Reviewer C output is incomplete or from the wrong dataset")
    packets, _ = _verified_packets(private_dir, manifest)
    mapped = {row["opaque_id"]: row for row in manifest["cases"]}
    seen: set[str] = set()
    for row in sealed["results"]:
        case_id = row.get("case_id") if isinstance(row, dict) else None
        if case_id not in mapped or case_id in seen:
            raise ValueError("Duplicate or unknown sealed Reviewer C case")
        seen.add(case_id)
        expected_case = mapped[case_id]
        if any(row.get(key) != expected_case[key] for key in
               ("source_case_id", "symbol", "batch_id")):
            raise ValueError("Sealed Reviewer C case provenance mismatch")
        pure = {key: value for key, value in row.items()
                if key not in {"source_case_id", "symbol", "batch_id"}}
        validated = _validate_result(
            pure, expected_case, packets[expected_case["batch_id"]][case_id]
        )
        if pure != validated:
            raise ValueError("Invalid sealed Reviewer C schema")
    if seen != set(mapped):
        raise ValueError("Sealed Reviewer C cases are incomplete")
'''
change(anchor,helper+anchor)
start='''    packets = {}
    expected_by_batch = {}
    for batch in manifest["batches"]:
        path = private_dir / "packets" / f"{batch['batch_id']}.json"
        if _sha256_file(path) != batch["packet_sha256"]:
            raise ValueError("Frozen review packet fingerprint mismatch")
        packet = json.loads(path.read_text(encoding="utf-8"))
        packets[batch["batch_id"]] = {row["case_id"]: row for row in packet["cases"]}
        expected_by_batch[batch["batch_id"]] = set(batch["opaque_ids"])
'''
change(start,'    packets, expected_by_batch = _verified_packets(private_dir, manifest)\n')
change(
'''        if journal.get("dataset_sha256") != manifest["dataset_sha256"]:
            raise ValueError("Partial Reviewer C journal belongs to another dataset")
        accepted = {row["case_id"]: row for row in journal.get("results", [])}
''',
'''        if (
            not isinstance(journal, dict)
            or set(journal) != {"protocol_version", "dataset_sha256", "results"}
            or journal["protocol_version"] != "ccw41-v1"
            or journal["dataset_sha256"] != manifest["dataset_sha256"]
            or not isinstance(journal["results"], list)
        ):
            raise ValueError("Partial Reviewer C journal belongs to another protocol/dataset")
        for row in journal["results"]:
            case_id = row.get("case_id") if isinstance(row, dict) else None
            if case_id not in expected or case_id in accepted:
                raise ValueError("Duplicate or unknown partial Reviewer C case")
            batch_id = expected[case_id]["batch_id"]
            if case_id not in expected_by_batch[batch_id]:
                raise ValueError("Partial Reviewer C case in wrong batch")
            accepted[case_id] = _validate_result(
                row, expected[case_id], packets[batch_id][case_id]
            )
''')
change(
'''        batch_id = payload.get("batch_id")
        if batch_id not in packets or path.stem != batch_id:
''',
'''        if not isinstance(payload, dict) or set(payload) != {"batch_id", "results"}:
            raise ValueError("Reviewer C batch root fields do not match frozen schema")
        batch_id = payload.get("batch_id")
        if batch_id not in packets or path.stem != batch_id:
''')
change(
'''    if (
        run_metadata is None
        or not RUN_METADATA_FIELDS.issubset(run_metadata)
        or any(
            not isinstance(run_metadata[field], str) or not run_metadata[field].strip()
            for field in RUN_METADATA_FIELDS
        )
    ):
        raise ValueError("Complete Reviewer C output requires verified run metadata")
''',
'    _verify_run_metadata(run_metadata)\n')
change(
'''    if sealed.get("result_count") != 200:
        raise ValueError("Reviewer C output is incomplete")

    sources = manifest["sources"]
''',
'''    _verify_sealed_record(private_dir, manifest, sealed)

    sources = manifest["sources"]
''')
change(
'    dataset = load_frozen(Path(sources["benchmark"]["path"]))\n',
'''    dataset = load_frozen(Path(sources["benchmark"]["path"]))
    if dataset["dataset_sha256"] != manifest["dataset_sha256"]:
        raise ValueError("Frozen dataset fingerprint mismatch")
''')
p.write_text(source, encoding="utf-8", newline="\n")

t = root / "tests/test_ccw41_reviewer_c_audit.py"
code = t.read_text(encoding="utf-8")
code = code.replace(
'            "data_transfer_approval": "synthetic",\n',
'            "data_transfer_approval": "synthetic",\n            "model_identity_verification": "synthetic-test",\n')
code = code.replace(
'            "data_transfer_approval": "synthetic",\n        },',
'            "data_transfer_approval": "synthetic",\n            "model_identity_verification": "synthetic-test",\n        },')
code = code.replace(
'                "data_transfer_approval": "",\n',
'                "data_transfer_approval": "",\n                "model_identity_verification": "synthetic-test",\n')
code = code.replace(
'''        prepare_review(
            benchmark, a, b, tmp_path / "private", enforce_canonical=False,
        )
''',
'''        prepare_review(
            benchmark, a, b, Path(__file__).resolve().parents[1] / "benchmarks"
            / "ccw41-unsafe-private", enforce_canonical=False,
        )
''')
t.write_text(code, encoding="utf-8", newline="\n")
print("Patched CCW-41 code and tests; originals retained under gitignored reports.")
