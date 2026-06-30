"""
Performance benchmarks for all scoring operations.

Run: python scripts/benchmark.py
"""

from __future__ import annotations

import asyncio
import statistics
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.fixtures.demo_data import DEMO_RESUME_TEXT, DEMO_JD_TEXT
from backend.parsers.resume_parser import parse_resume_text
from backend.parsers.jd_parser import parse_jd
from backend.parsers.schemas import Resume, JobDescription


def _resume() -> Resume:
    return parse_resume_text(DEMO_RESUME_TEXT)


def _jd() -> JobDescription:
    return parse_jd(DEMO_JD_TEXT)


def bench_sync(name: str, fn, iterations: int = 100) -> dict:
    # Warmup
    for _ in range(3):
        fn()

    times: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return {
        "name": name,
        "iterations": iterations,
        "avg": statistics.mean(times),
        "p50": statistics.median(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
        "ops_sec": round(1000 / statistics.mean(times)) if statistics.mean(times) > 0 else 0,
    }


def bench_async(name: str, coro_fn, iterations: int = 100) -> dict:
    async def _run():
        # Warmup
        for _ in range(3):
            await coro_fn()

        times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            await coro_fn()
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        return times

    times = asyncio.run(_run())

    return {
        "name": name,
        "iterations": iterations,
        "avg": statistics.mean(times),
        "p50": statistics.median(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
        "ops_sec": round(1000 / statistics.mean(times)) if statistics.mean(times) > 0 else 0,
    }


def main():
    print("=" * 70)
    print("LAND IT — Performance Benchmarks")
    print("=" * 70)
    print()

    resume = _resume()
    jd = _jd()

    results: list[dict] = []

    # 1. Resume parsing
    print("Benchmarking Resume Parse...", end=" ", flush=True)
    r = bench_sync("Resume Parse", lambda: parse_resume_text(DEMO_RESUME_TEXT))
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # 2. JD parsing
    print("Benchmarking JD Parse...", end=" ", flush=True)
    r = bench_sync("JD Parse", lambda: parse_jd(DEMO_JD_TEXT))
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # 3. ATS Score (14 dimensions)
    print("Benchmarking ATS Score (14 dim)...", end=" ", flush=True)
    from backend.agents.tailor.weightage.scorer_engine import score_resume
    r = bench_async("ATS Score (14 dim)", lambda: score_resume(resume, jd))
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # 4. Standout Score (8 dimensions)
    print("Benchmarking Standout Score (8 dim)...", end=" ", flush=True)
    from backend.agents.tailor.standout.engine import score_standout
    r = bench_async("Standout Score (8 dim)", lambda: score_standout(resume, jd))
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # 5. Dual Score (22 dimensions + callback)
    print("Benchmarking Dual Score (22 dim)...", end=" ", flush=True)
    from backend.agents.tailor.agent import TailorAgent
    agent = TailorAgent()
    r = bench_async("Dual Score (22 dim)", lambda: agent.score_dual(resume, jd))
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # 6. A/B Test
    print("Benchmarking A/B Test...", end=" ", flush=True)
    from backend.agents.tailor.ab_testing import ab_test_resumes
    resume_b = parse_resume_text(DEMO_RESUME_TEXT)
    r = bench_async("A/B Test", lambda: ab_test_resumes(resume, resume_b, jd), iterations=50)
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # 7. Skill Gap Analysis
    print("Benchmarking Skill Gap Analysis...", end=" ", flush=True)
    from backend.agents.tailor.skill_gap import analyze_skill_gaps
    r = bench_sync("Skill Gap Analysis", lambda: analyze_skill_gaps(resume, jd))
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # 8. Batch Score (5 JDs)
    print("Benchmarking Batch Score (5 JDs)...", end=" ", flush=True)
    from backend.agents.tailor.batch_scorer import batch_score
    jds_5 = [parse_jd(DEMO_JD_TEXT) for _ in range(5)]
    r = bench_async("Batch Score (5 JDs)", lambda: batch_score(resume, jds_5), iterations=20)
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # 9. Salary Estimate
    print("Benchmarking Salary Estimate...", end=" ", flush=True)
    from backend.agents.scout.salary_intel import estimate_salary
    r = bench_sync("Salary Estimate", lambda: estimate_salary(resume, jd))
    results.append(r)
    print(f"{r['avg']:.1f}ms avg")

    # Print table
    print()
    print("=" * 70)
    print(f"{'Operation':<25} {'Avg':>8} {'P50':>8} {'P95':>8} {'Ops/sec':>10}")
    print("-" * 70)
    for r in results:
        print(
            f"{r['name']:<25} {r['avg']:>7.1f}ms {r['p50']:>7.1f}ms "
            f"{r['p95']:>7.1f}ms {r['ops_sec']:>9,}"
        )
    print("=" * 70)
    print()
    print("All operations are pure heuristic — zero API calls, zero network latency.")


if __name__ == "__main__":
    main()
