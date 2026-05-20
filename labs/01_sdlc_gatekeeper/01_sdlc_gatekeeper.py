"""SDLC Gatekeeper — headless CLI eval for GitHub Actions.

SUT: a Claude agent that receives codebase files + SDLC rules and responds
with a structured JSON decision (GO/NO-GO) + list of violations.

The eval compares the agent output against a golden dataset.

Usage:
    python 01_sdlc_gatekeeper.py [--case CASE_ID] [--model MODEL_ID] \\
        [--rules PATH] [--prompt PATH] [--golden PATH] [--output PATH]

Exits with code 1 if overall_pass is False.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ── Pricing ───────────────────────────────────────────────────────────────────

PRICING = {
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
}


def cost_usd(model: str, tin: int, tout: int) -> float:
    pin, pout = PRICING.get(model, (3.00, 15.00))
    return round((tin * pin + tout * pout) / 1_000_000, 6)


# ── JSON extraction ───────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    """Robustly parse JSON from agent output, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        return {
            "decision": "NO-GO",
            "violations": [],
            "reasoning": f"PARSE_ERROR: {text[:200]}",
        }


# ── Loaders ───────────────────────────────────────────────────────────────────

def _find_repo_root(start: Path) -> Path:
    """Walk up from start until config/rules.yaml is found."""
    for candidate in [start, *start.parents]:
        if (candidate / "config" / "rules.yaml").exists():
            return candidate
    return start


def load_rules(rules_path: Path) -> list[dict]:
    with rules_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data["rules"]


def load_golden(golden_path: Path) -> list[dict]:
    with golden_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data["test_cases"]


def load_prompt_template(prompt_path: Path) -> str:
    return prompt_path.read_text(encoding="utf-8")


def read_codebase(repo_path: Path) -> str:
    """Read all .py files in repo_path; serialize as fenced blocks."""
    parts = []
    for py_file in sorted(repo_path.glob("*.py")):
        content = py_file.read_text(encoding="utf-8")
        parts.append(f"## file: {py_file.name}\n```python\n{content}\n```")
    return "\n\n".join(parts)


def serialize_rules(rules: list[dict]) -> str:
    """Format rules as a readable block for the agent prompt."""
    lines = []
    for rule in rules:
        lines.append(f"- id: {rule['id']}")
        lines.append(f"  description: {rule['description']}")
        if "criteria" in rule:
            criteria_lines = rule["criteria"].strip().replace("\n", "\n      ")
            lines.append(f"  criteria: {criteria_lines}")
        if "pattern" in rule:
            lines.append(f"  pattern: {rule['pattern']} (forbidden)")
        if "forbidden_imports" in rule:
            lines.append(f"  forbidden_imports: {rule['forbidden_imports']}")
        if "max_args" in rule:
            lines.append(f"  max_args: {rule['max_args']}")
        lines.append("")
    return "\n".join(lines)


# ── Agent call with streaming ─────────────────────────────────────────────────

def run_agent(client: anthropic.Anthropic, model: str, prompt: str) -> tuple[dict, dict]:
    """Call the agent with streaming; return (agent_output_dict, perf_metrics)."""
    ttft = None
    start = time.perf_counter()

    with client.messages.stream(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for event in stream:
            if ttft is None and event.type == "content_block_start":
                ttft = time.perf_counter() - start
        final_msg = stream.get_final_message()

    ttc = time.perf_counter() - start
    text = "".join(b.text for b in final_msg.content if hasattr(b, "text"))

    usage = final_msg.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    total_tokens = input_tokens + output_tokens

    ttft_ms = round((ttft or ttc) * 1000, 1)
    ttc_ms = round(ttc * 1000, 1)
    delta_s = max((ttc - (ttft or ttc)), 0.001)
    otps = round(output_tokens / delta_s, 1)

    perf = {
        "ttft_ms": ttft_ms,
        "ttc_ms": ttc_ms,
        "otps": otps,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd(model, input_tokens, output_tokens),
    }

    agent_output = extract_json(text)
    return agent_output, perf


# ── Quality metrics ───────────────────────────────────────────────────────────

def compute_quality(agent_output: dict, expected: dict) -> dict:
    """Compute TP/FP/FN and precision/recall/F1 vs expected violations."""
    agent_violations = agent_output.get("violations", [])
    expected_violations = expected.get("expected_violations", [])

    agent_rule_ids = {v["rule_id"] for v in agent_violations}
    expected_rule_ids = {v["rule_id"] for v in expected_violations}

    tp = len(agent_rule_ids & expected_rule_ids)
    fp = len(agent_rule_ids - expected_rule_ids)
    fn = len(expected_rule_ids - agent_rule_ids)

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if tp == 0 and fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    decision_match = agent_output.get("decision") == expected.get("expected_decision")

    return {
        "decision_match": decision_match,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


# ── Evaluators ────────────────────────────────────────────────────────────────

class ExactMatchEvaluator:
    """For each expected_violation.rule_id, verify it appears in agent violations."""

    name = "exact_match"

    def evaluate(self, agent_output: dict, expected: dict) -> dict:
        agent_rule_ids = {v["rule_id"] for v in agent_output.get("violations", [])}
        expected_violations = expected.get("expected_violations", [])

        missing = [
            v["rule_id"]
            for v in expected_violations
            if v["rule_id"] not in agent_rule_ids
        ]

        passed = len(missing) == 0
        return {
            "name": self.name,
            "passed": passed,
            "score": 1.0 if passed else round(
                (len(expected_violations) - len(missing)) / max(len(expected_violations), 1), 4
            ),
            "evidence": (
                "All expected rule_ids present in agent output"
                if passed
                else f"Missing rule_ids: {missing}"
            ),
        }


class RuleBasedEvaluator:
    """Validates the JSON schema of agent output."""

    name = "rule_based"

    def evaluate(self, agent_output: dict, _expected: dict) -> dict:
        errors = []

        decision = agent_output.get("decision")
        if decision not in ("GO", "NO-GO"):
            errors.append(f"decision must be GO or NO-GO, got: {decision!r}")

        violations = agent_output.get("violations")
        if not isinstance(violations, list):
            errors.append(f"violations must be a list, got: {type(violations).__name__}")
        else:
            for i, v in enumerate(violations):
                for field in ("rule_id", "file"):
                    if field not in v:
                        errors.append(f"violations[{i}] missing field '{field}'")

        if "reasoning" not in agent_output:
            errors.append("missing 'reasoning' field")

        passed = len(errors) == 0
        return {
            "name": self.name,
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "evidence": "Schema valid" if passed else "; ".join(errors),
        }


LLM_JUDGE_PROMPT = """\
You are evaluating the reasoning of an SDLC gatekeeper agent.

The agent reviewed code and produced this reasoning:
"{agent_reasoning}"

The agent's decision was: {agent_decision}
The expected decision was: {expected_decision}
The actual violations found vs expected: TP={tp}, FP={fp}, FN={fn}

Rate the reasoning from 0-10 on whether it correctly justifies the decision.
Respond ONLY with JSON: {{"score": <float>, "passed": <bool>, "reason": "..."}}
Pass threshold: score >= 6.0\
"""


class LLMJudgeEvaluator:
    """Uses Claude to evaluate the quality of the agent's reasoning."""

    name = "llm_judge"

    def __init__(self, client: anthropic.Anthropic, model: str):
        self.client = client
        self.model = model

    def evaluate(self, agent_output: dict, expected: dict, quality: dict) -> dict:
        prompt = LLM_JUDGE_PROMPT.format(
            agent_reasoning=agent_output.get("reasoning", ""),
            agent_decision=agent_output.get("decision", ""),
            expected_decision=expected.get("expected_decision", ""),
            tp=quality["true_positives"],
            fp=quality["false_positives"],
            fn=quality["false_negatives"],
        )
        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text
            parsed = extract_json(raw)
            score = float(parsed.get("score", 0.0))
            passed = bool(parsed.get("passed", score >= 6.0))
            reason = str(parsed.get("reason", ""))
        except Exception as exc:  # noqa: BLE001
            return {
                "name": self.name,
                "passed": False,
                "score": 0.0,
                "evidence": f"Judge error: {exc}",
            }

        return {
            "name": self.name,
            "passed": passed,
            "score": round(score, 2),
            "evidence": reason,
        }


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_case(
    client: anthropic.Anthropic,
    model: str,
    case: dict,
    rules: list[dict],
    prompt_template: str,
    repo_root: Path,
) -> dict:
    """Run the agent on one test case and return the full case result."""
    repo_path = repo_root / case["repo_path"]
    codebase = read_codebase(repo_path)
    rules_text = serialize_rules(rules)

    prompt = prompt_template.replace("{rules}", rules_text).replace("{codebase}", codebase)

    print(f"  Running case: {case['case_id']} ...", file=sys.stderr, flush=True)
    agent_output, perf = run_agent(client, model, prompt)

    quality = compute_quality(agent_output, case)

    exact_eval = ExactMatchEvaluator()
    rule_eval = RuleBasedEvaluator()
    llm_eval = LLMJudgeEvaluator(client, model)

    exact_result = exact_eval.evaluate(agent_output, case)
    rule_result = rule_eval.evaluate(agent_output, case)
    llm_result = llm_eval.evaluate(agent_output, case, quality)

    print(
        f"    -> decision_match={quality['decision_match']} "
        f"f1={quality['f1']} "
        f"ttft={perf['ttft_ms']}ms cost=${perf['cost_usd']}",
        file=sys.stderr,
    )

    return {
        "case_id": case["case_id"],
        "agent_output": agent_output,
        "quality": quality,
        "performance": perf,
        "evaluators": [exact_result, rule_result, llm_result],
    }


# ── Aggregation ───────────────────────────────────────────────────────────────

def aggregate(test_cases: list[dict]) -> dict:
    n = len(test_cases)
    if n == 0:
        return {
            "overall_pass": False,
            "avg_precision": 0.0,
            "avg_recall": 0.0,
            "avg_f1": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "total_ttft_ms": 0.0,
        }

    avg_precision = round(sum(c["quality"]["precision"] for c in test_cases) / n, 4)
    avg_recall = round(sum(c["quality"]["recall"] for c in test_cases) / n, 4)
    avg_f1 = round(sum(c["quality"]["f1"] for c in test_cases) / n, 4)
    all_decision_match = all(c["quality"]["decision_match"] for c in test_cases)

    overall_pass = avg_f1 >= 0.7 and all_decision_match

    return {
        "overall_pass": overall_pass,
        "avg_precision": avg_precision,
        "avg_recall": avg_recall,
        "avg_f1": avg_f1,
        "total_input_tokens": sum(c["performance"]["input_tokens"] for c in test_cases),
        "total_output_tokens": sum(c["performance"]["output_tokens"] for c in test_cases),
        "total_cost_usd": round(sum(c["performance"]["cost_usd"] for c in test_cases), 6),
        "total_ttft_ms": round(sum(c["performance"]["ttft_ms"] for c in test_cases), 1),
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="SDLC Gatekeeper — eval a Claude agent against a golden dataset"
    )
    parser.add_argument("--case", default=None, help="Case ID to run (default: all)")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Anthropic model ID")
    parser.add_argument("--rules", default="config/rules.yaml", help="Path to rules YAML")
    parser.add_argument(
        "--prompt",
        default="labs/01_sdlc_gatekeeper/agent_prompt.md",
        help="Path to agent prompt template",
    )
    parser.add_argument(
        "--golden",
        default="examples/test_repos/golden_dataset.yaml",
        help="Path to golden dataset YAML",
    )
    parser.add_argument("--output", default=None, help="Optional path to save JSON result")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ERROR: ANTHROPIC_API_KEY environment variable is not set.",
            file=sys.stderr,
        )
        sys.exit(2)

    client = anthropic.Anthropic(api_key=api_key)
    repo_root = _find_repo_root(Path(args.rules).resolve().parent)

    rules = load_rules(Path(args.rules))
    prompt_template = load_prompt_template(Path(args.prompt))
    all_cases = load_golden(Path(args.golden))

    if args.case:
        cases = [c for c in all_cases if c["case_id"] == args.case]
        if not cases:
            print(
                f"ERROR: Case '{args.case}' not found. "
                f"Available: {[c['case_id'] for c in all_cases]}",
                file=sys.stderr,
            )
            sys.exit(2)
    else:
        cases = all_cases

    print(f"Model: {args.model}", file=sys.stderr)
    print(f"Cases: {[c['case_id'] for c in cases]}", file=sys.stderr)
    print(f"Rules: {len(rules)} loaded", file=sys.stderr)

    results = []
    for case in cases:
        result = run_case(client, args.model, case, rules, prompt_template, repo_root)
        results.append(result)

    agg = aggregate(results)

    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lab": "lab01",
        "model": args.model,
        "test_cases": results,
        "aggregate": agg,
    }

    output_json = json.dumps(report, indent=2)
    print(output_json)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_json, encoding="utf-8")
        print(f"Result saved to: {args.output}", file=sys.stderr)

    if not agg["overall_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
