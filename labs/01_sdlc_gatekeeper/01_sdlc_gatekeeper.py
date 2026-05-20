"""SDLC Gatekeeper — headless CLI for GitHub Actions.

Usage:
    python 01_sdlc_gatekeeper.py --file <path> [--model <model_id>] [--rules <path>] [--output <path>]

Exits with code 1 if the decision is NO-GO (any rule fails).
"""
import argparse
import ast
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import anthropic
import yaml

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not required; env vars must be set manually


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    rule_id: str
    type: str
    passed: bool
    evidence: str
    score: float


# ── Exact Match Evaluator ─────────────────────────────────────────────────────

class ExactMatchEvaluator:
    """Checks for forbidden or required literal patterns in source code."""

    def evaluate(self, rule: dict, source_code: str) -> EvalResult:
        pattern = rule["pattern"]
        match_type = rule.get("match_type", "forbidden")
        lines = source_code.splitlines()

        matches = [
            f"Line {i + 1}: {line.strip()}"
            for i, line in enumerate(lines)
            if pattern in line
        ]

        if match_type == "forbidden":
            passed = len(matches) == 0
            evidence = matches[0] if matches else "No violations found"
        else:  # required
            passed = len(matches) > 0
            evidence = matches[0] if matches else f"Required pattern '{pattern}' not found"

        return EvalResult(
            rule_id=rule["id"],
            type="exact_match",
            passed=passed,
            evidence=evidence,
            score=1.0 if passed else 0.0,
        )


# ── AST Visitors ──────────────────────────────────────────────────────────────

class MagicNumberVisitor(ast.NodeVisitor):
    """Collects numeric literals that appear outside named constant assignments."""

    ALLOWED_VALUES = {0, 1, -1}

    def __init__(self):
        self.violations: list[tuple[int, float]] = []
        self._in_assignment = False

    def visit_Assign(self, node: ast.Assign):
        self._in_assignment = True
        self.generic_visit(node)
        self._in_assignment = False

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self._in_assignment = True
        self.generic_visit(node)
        self._in_assignment = False

    def visit_Constant(self, node: ast.Constant):
        if (
            isinstance(node.value, (int, float))
            and not self._in_assignment
            and node.value not in self.ALLOWED_VALUES
        ):
            self.violations.append((node.lineno, node.value))


class ImportVisitor(ast.NodeVisitor):
    """Collects forbidden module imports."""

    def __init__(self, forbidden: list[str]):
        self.forbidden = forbidden
        self.violations: list[tuple[int, str]] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if any(alias.name.startswith(f) for f in self.forbidden):
                self.violations.append((node.lineno, alias.name))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and any(node.module.startswith(f) for f in self.forbidden):
            self.violations.append((node.lineno, node.module))


class BareExceptVisitor(ast.NodeVisitor):
    """Collects bare except clauses (no exception type specified)."""

    def __init__(self):
        self.violations: list[int] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:
            self.violations.append(node.lineno)
        self.generic_visit(node)


class FunctionArgVisitor(ast.NodeVisitor):
    """Collects functions that exceed the maximum allowed argument count."""

    def __init__(self, max_args: int):
        self.max_args = max_args
        self.violations: list[tuple[int, str, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        arg_count = len(node.args.args)
        if arg_count > self.max_args:
            self.violations.append((node.lineno, node.name, arg_count))
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


# ── Rule-Based Evaluator ──────────────────────────────────────────────────────

class RuleBasedEvaluator:
    """Evaluates rules that require AST-level analysis."""

    def evaluate(self, rule: dict, source_code: str) -> EvalResult:
        try:
            tree = ast.parse(source_code)
        except SyntaxError as exc:
            return EvalResult(
                rule_id=rule["id"],
                type="rule_based",
                passed=False,
                evidence=f"Syntax error: cannot parse file — {exc}",
                score=0.0,
            )

        rule_id = rule["id"]

        if rule_id == "no_magic_numbers":
            return self._check_magic_numbers(rule, tree)
        elif rule_id == "use_internal_db":
            return self._check_forbidden_imports(rule, tree)
        elif rule_id == "no_bare_except":
            return self._check_bare_except(rule, tree)
        elif rule_id == "max_function_args":
            return self._check_function_args(rule, tree)
        else:
            return EvalResult(
                rule_id=rule_id,
                type="rule_based",
                passed=True,
                evidence=f"No handler implemented for rule '{rule_id}'",
                score=1.0,
            )

    def _check_magic_numbers(self, rule: dict, tree: ast.AST) -> EvalResult:
        visitor = MagicNumberVisitor()
        visitor.visit(tree)
        passed = len(visitor.violations) == 0
        if passed:
            evidence = "No magic numbers found"
        else:
            line, value = visitor.violations[0]
            evidence = f"Line {line}: magic number {value} found outside named assignment"
        return EvalResult(
            rule_id=rule["id"],
            type="rule_based",
            passed=passed,
            evidence=evidence,
            score=1.0 if passed else 0.0,
        )

    def _check_forbidden_imports(self, rule: dict, tree: ast.AST) -> EvalResult:
        forbidden = rule.get("forbidden_imports", [])
        visitor = ImportVisitor(forbidden)
        visitor.visit(tree)
        passed = len(visitor.violations) == 0
        if passed:
            evidence = "No forbidden imports found"
        else:
            line, name = visitor.violations[0]
            evidence = f"Line {line}: forbidden import '{name}'"
        return EvalResult(
            rule_id=rule["id"],
            type="rule_based",
            passed=passed,
            evidence=evidence,
            score=1.0 if passed else 0.0,
        )

    def _check_bare_except(self, rule: dict, tree: ast.AST) -> EvalResult:
        visitor = BareExceptVisitor()
        visitor.visit(tree)
        passed = len(visitor.violations) == 0
        if passed:
            evidence = "No bare except clauses found"
        else:
            line = visitor.violations[0]
            evidence = f"Line {line}: bare except clause — specify exception type"
        return EvalResult(
            rule_id=rule["id"],
            type="rule_based",
            passed=passed,
            evidence=evidence,
            score=1.0 if passed else 0.0,
        )

    def _check_function_args(self, rule: dict, tree: ast.AST) -> EvalResult:
        max_args = rule.get("max_args", 5)
        visitor = FunctionArgVisitor(max_args)
        visitor.visit(tree)
        passed = len(visitor.violations) == 0
        if passed:
            evidence = f"All functions have {max_args} or fewer arguments"
        else:
            line, name, count = visitor.violations[0]
            evidence = f"Line {line}: function '{name}' has {count} arguments (max {max_args})"
        return EvalResult(
            rule_id=rule["id"],
            type="rule_based",
            passed=passed,
            evidence=evidence,
            score=1.0 if passed else 0.0,
        )


# ── LLM-as-Judge Evaluator ────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """You are a strict code quality reviewer acting as an automated SDLC gate.
You will receive source code and a specific quality criterion to evaluate.
You must respond ONLY with a valid JSON object — no prose, no markdown.

Response schema:
{
  "score": <float 0.0-10.0>,
  "passed": <bool>,
  "evidence": "<one concrete sentence citing line numbers if applicable>"
}

Scoring: 10.0 = zero violations, 0.0 = severe/multiple violations.
The 'passed' field is true when score >= the provided threshold."""


def _build_judge_prompt(rule: dict, source_code: str) -> str:
    return f"""Evaluate the following Python code against this criterion:

CRITERION: {rule['description']}
SCORE_THRESHOLD: {rule['score_threshold']}

DETAILS:
{rule['criteria']}

SOURCE CODE:
```python
{source_code}
```

Respond with the JSON schema only."""


class LLMJudgeEvaluator:
    """Evaluates rules using Claude as a semantic code reviewer."""

    def __init__(self, client: anthropic.Anthropic, model: str = "claude-sonnet-4-6"):
        self.client = client
        self.model = model

    def evaluate(self, rule: dict, source_code: str) -> EvalResult:
        prompt = _build_judge_prompt(rule, source_code)
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                system=JUDGE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text
        except anthropic.RateLimitError:
            time.sleep(30)
            message = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                system=JUDGE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text
        except anthropic.APIError as exc:
            raise RuntimeError(f"Anthropic API error on rule {rule['id']}: {exc}") from exc

        try:
            parsed = json.loads(raw)
            score = float(parsed["score"])
            passed = bool(parsed["passed"])
            evidence = str(parsed["evidence"])
        except (json.JSONDecodeError, KeyError):
            return EvalResult(
                rule_id=rule["id"],
                type="llm_judge",
                passed=False,
                evidence=f"LLM returned non-JSON response: {raw[:100]}",
                score=0.0,
            )

        return EvalResult(
            rule_id=rule["id"],
            type="llm_judge",
            passed=passed,
            evidence=evidence,
            score=score,
        )


# ── Pipeline ──────────────────────────────────────────────────────────────────

class GatekeeperPipeline:
    """Orchestrates all three evaluator types and produces a GO/NO-GO decision."""

    def __init__(self, rules: list[dict], model: str = "claude-sonnet-4-6"):
        self.rules = rules
        self.model = model
        self.exact_evaluator = ExactMatchEvaluator()
        self.rule_evaluator = RuleBasedEvaluator()
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Export it or create a .env file with ANTHROPIC_API_KEY=<your-key>."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self.llm_evaluator = LLMJudgeEvaluator(self._client, model)

    def run(self, file_path: str) -> dict:
        source_code = Path(file_path).read_text(encoding="utf-8")
        results: list[EvalResult] = []

        for rule in self.rules:
            rule_type = rule["type"]
            if rule_type == "exact_match":
                result = self.exact_evaluator.evaluate(rule, source_code)
            elif rule_type == "rule_based":
                result = self.rule_evaluator.evaluate(rule, source_code)
            elif rule_type == "llm_judge":
                result = self.llm_evaluator.evaluate(rule, source_code)
            else:
                result = EvalResult(
                    rule_id=rule["id"],
                    type=rule_type,
                    passed=True,
                    evidence=f"Unknown rule type '{rule_type}' — skipped",
                    score=1.0,
                )
            results.append(result)

        failed = [r for r in results if not r.passed]
        passed_list = [r for r in results if r.passed]
        aggregate_score = sum(r.score for r in results) / len(results) if results else 0.0

        return {
            "run_id": datetime.utcnow().isoformat() + "Z",
            "file": str(file_path),
            "model": self.model,
            "results": [asdict(r) for r in results],
            "decision": "GO" if not failed else "NO-GO",
            "passed_rules": len(passed_list),
            "failed_rules": len(failed),
            "aggregate_score": round(aggregate_score, 2),
        }


# ── CLI entry point ───────────────────────────────────────────────────────────

def _load_rules(rules_path: str) -> list[dict]:
    path = Path(rules_path)
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data["rules"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SDLC Gatekeeper — automated code quality gate for CI/CD pipelines"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the Python source file to evaluate",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        help="Anthropic model ID to use for LLM-as-Judge rules (default: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--rules",
        default="config/rules.yaml",
        help="Path to the rules YAML file (default: config/rules.yaml)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the JSON result (default: print to stdout only)",
    )
    args = parser.parse_args()

    rules = _load_rules(args.rules)
    pipeline = GatekeeperPipeline(rules=rules, model=args.model)
    report = pipeline.run(args.file)

    output_json = json.dumps(report, indent=2)
    print(output_json)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_json, encoding="utf-8")

    if report["decision"] == "NO-GO":
        sys.exit(1)


if __name__ == "__main__":
    main()
