#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def parse_int(value):
    try:
        return int(value or 0)
    except ValueError:
        return 0


def parse_float(value):
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def read_attrs(tag):
    return dict(re.findall(r'([A-Za-z_:-]+)="([^"]*)"', tag))


def read_junit_metrics(path):
    metrics = {
        "tests_total": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_errors": 0,
        "tests_skipped": 0,
        "tests_time_seconds": 0.0,
        "junit_available": False,
    }
    if not path.exists():
        return metrics

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        metrics["junit_error"] = str(exc)
        return metrics

    suite_tags = re.findall(r"<testsuite\b[^>]*>", content)
    if not suite_tags:
        metrics["junit_error"] = "testsuite tag not found"
        return metrics

    for suite_tag in suite_tags:
        suite = read_attrs(suite_tag)
        tests = parse_int(suite.get("tests"))
        failures = parse_int(suite.get("failures"))
        errors = parse_int(suite.get("errors"))
        skipped = parse_int(suite.get("skipped"))
        metrics["tests_total"] += tests
        metrics["tests_failed"] += failures
        metrics["tests_errors"] += errors
        metrics["tests_skipped"] += skipped
        metrics["tests_time_seconds"] += parse_float(suite.get("time"))

    metrics["tests_passed"] = max(
        0,
        metrics["tests_total"]
        - metrics["tests_failed"]
        - metrics["tests_errors"]
        - metrics["tests_skipped"],
    )
    metrics["tests_time_seconds"] = round(metrics["tests_time_seconds"], 3)
    metrics["junit_available"] = True
    return metrics


def read_coverage_metrics(path):
    metrics = {"coverage_available": False}
    if not path.exists():
        return metrics

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        metrics["coverage_error"] = str(exc)
        return metrics

    match = re.search(r"<coverage\b[^>]*>", content)
    if not match:
        metrics["coverage_error"] = "coverage tag not found"
        return metrics

    root = read_attrs(match.group(0))
    line_rate = parse_float(root.get("line-rate"))
    metrics.update(
        {
            "coverage_available": True,
            "coverage_line_rate": round(line_rate, 4),
            "coverage_percent": round(line_rate * 100, 2),
            "coverage_lines_valid": parse_int(root.get("lines-valid")),
            "coverage_lines_covered": parse_int(root.get("lines-covered")),
            "coverage_branches_valid": parse_int(root.get("branches-valid")),
            "coverage_branches_covered": parse_int(root.get("branches-covered")),
        }
    )
    return metrics


def write_service_summary(args):
    report_dir = Path(args.report_dir)
    summary = {
        "service": args.service,
        "status": args.status,
        "exit_code": int(args.exit_code),
        "started_at": args.started_at,
        "finished_at": args.finished_at,
        "duration_seconds": int(args.duration_seconds),
    }
    summary.update(read_junit_metrics(report_dir / "junit.xml"))
    summary.update(read_coverage_metrics(report_dir / "coverage.xml"))
    (report_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def aggregate_summaries(args):
    reports_root = Path(args.reports_root)
    service_summaries = []
    for summary_path in sorted(reports_root.glob("*/summary.json")):
        service_summaries.append(json.loads(summary_path.read_text(encoding="utf-8")))

    aggregate = {
        "status": "passed",
        "services_total": len(service_summaries),
        "services_passed": 0,
        "services_failed": 0,
        "tests_total": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_errors": 0,
        "tests_skipped": 0,
        "duration_seconds": 0,
        "services": service_summaries,
    }
    for item in service_summaries:
        if item.get("status") == "passed":
            aggregate["services_passed"] += 1
        else:
            aggregate["services_failed"] += 1
            aggregate["status"] = "failed"
        aggregate["tests_total"] += int(item.get("tests_total", 0))
        aggregate["tests_passed"] += int(item.get("tests_passed", 0))
        aggregate["tests_failed"] += int(item.get("tests_failed", 0))
        aggregate["tests_errors"] += int(item.get("tests_errors", 0))
        aggregate["tests_skipped"] += int(item.get("tests_skipped", 0))
        aggregate["duration_seconds"] += int(item.get("duration_seconds", 0))

    (reports_root / "summary.json").write_text(
        json.dumps(aggregate, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    write_markdown_summary(reports_root / "summary.md", aggregate)


def write_markdown_summary(path, aggregate):
    lines = [
        "## Unit Test Summary",
        "",
        f"- Status: `{aggregate['status']}`",
        f"- Services: {aggregate['services_passed']} passed / {aggregate['services_total']} total",
        f"- Tests: {aggregate['tests_passed']} passed, {aggregate['tests_failed']} failed, {aggregate['tests_errors']} errors, {aggregate['tests_skipped']} skipped / {aggregate['tests_total']} total",
        "",
        "| Service | Status | Tests | Passed | Failed | Errors | Skipped | Coverage | Duration |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in aggregate["services"]:
        coverage = "-"
        if item.get("coverage_available"):
            coverage = f"{item.get('coverage_percent', 0):.2f}%"
        lines.append(
            "| {service} | {status} | {tests_total} | {tests_passed} | {tests_failed} | {tests_errors} | {tests_skipped} | {coverage} | {duration_seconds}s |".format(
                service=item.get("service", ""),
                status=item.get("status", ""),
                tests_total=item.get("tests_total", 0),
                tests_passed=item.get("tests_passed", 0),
                tests_failed=item.get("tests_failed", 0),
                tests_errors=item.get("tests_errors", 0),
                tests_skipped=item.get("tests_skipped", 0),
                coverage=coverage,
                duration_seconds=item.get("duration_seconds", 0),
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    service = subparsers.add_parser("service")
    service.add_argument("--service", required=True)
    service.add_argument("--report-dir", required=True)
    service.add_argument("--status", required=True)
    service.add_argument("--exit-code", required=True)
    service.add_argument("--started-at", required=True)
    service.add_argument("--finished-at", required=True)
    service.add_argument("--duration-seconds", required=True)
    service.set_defaults(func=write_service_summary)

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--reports-root", required=True)
    aggregate.set_defaults(func=aggregate_summaries)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
