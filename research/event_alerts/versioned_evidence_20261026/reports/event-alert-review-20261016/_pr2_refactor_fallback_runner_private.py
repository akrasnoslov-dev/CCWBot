from pathlib import Path
p=Path(r'D:\Projects\CCWBot\scripts\multi_provider_event_significance_benchmark.py')
s=p.read_text(encoding='utf8')
changes=[
('from scripts.live_event_significance_benchmark import (  # noqa: E402\n    eligible_replay_cases, load_reviewer_a, maximum_possible_quality,\n    save_state,\n)', 'from scripts.live_event_significance_benchmark import (  # noqa: E402\n    VARIANTS, eligible_replay_cases, load_reviewer_a, maximum_possible_quality,\n    save_state,\n)'),
('def configuration(provider: str) -> dict:', 'def configuration(provider: str, model_override: str | None = None) -> dict:'),
('    model = config.model_for(provider, "event_analysis")','    model = model_override or config.model_for(provider, "event_analysis")'),
('def new_state(dataset: dict, cfg: dict) -> dict:', 'def new_state(dataset: dict, cfg: dict, variant: str = VARIANT) -> dict:'),
('candidate_prompt({"symbol": None}, VARIANT)', 'candidate_prompt({"symbol": None}, variant)'),
('"attempted_requests": 0, "runs": {VARIANT: []}', '"attempted_requests": 0, "runs": {variant: []}'),
('async def run(provider: str, *, max_requests: int, delay: float,\n              stop_on_impossible_gates: bool = True) -> dict:', 'async def run(provider: str, *, max_requests: int, delay: float,\n              variant: str = VARIANT, model_override: str | None = None,\n              stop_on_impossible_gates: bool = True) -> dict:'),
('    cfg = configuration(provider)', '    cfg = configuration(provider, model_override)'),
('    directory = PRIVATE / "merged_pilots_private" / ("fallback_" + provider + "_" + VARIANT)', '    suffix = ("_" + cfg["model"].replace("/", "_").replace("@", "")) if model_override else ""\n    directory = PRIVATE / "merged_pilots_private" / ("fallback_" + provider + "_" + variant + suffix)'),
('    expected = new_state(dataset, cfg)', '    expected = new_state(dataset, cfg, variant)'),
('state["runs"][VARIANT]', 'state["runs"][variant]'),
('maximum_possible_quality(\n                    dataset, labels, state, VARIANT)', 'maximum_possible_quality(\n                    dataset, labels, state, variant)'),
('candidate_prompt(case["input"], VARIANT)', 'candidate_prompt(case["input"], variant)'),
('maximum_possible_quality(dataset, labels, state, VARIANT)', 'maximum_possible_quality(dataset, labels, state, variant)'),
('    parser.add_argument("--provider", choices=PROVIDERS, required=True)', '    parser.add_argument("--provider", choices=PROVIDERS, required=True)\n    parser.add_argument("--variant", choices=VARIANTS, default=VARIANT)\n    parser.add_argument("--model-override", default=None)'),
('    print(json.dumps(asyncio.run(run(args.provider, max_requests=args.max_requests,\n                                     delay=args.delay_seconds)), sort_keys=True))', '    print(json.dumps(asyncio.run(run(args.provider, max_requests=args.max_requests,\n                                     delay=args.delay_seconds, variant=args.variant,\n                                     model_override=args.model_override)), sort_keys=True))'),
]
for old,new in changes:
 n=s.count(old)
 if n<1:raise RuntimeError(f'cannot find {old[:80]!r}')
 s=s.replace(old,new)
 print('patched',n,old[:65])
p.write_text(s,encoding='utf8')
