import json
import time
import os
import sys
import re

from config import OLLAMA_MODELS, BACKEND
from analyzer import analyze_complexity, unload_model

if BACKEND != "ollama":
    print("WARNING: Benchmarking is designed for the Ollama backend.")

def normalize_complexity(c: str) -> str:
    """Normalize O(N \log N) to O(N log N) to ease comparison."""
    c = c.replace("\\log", "log").replace(" ", "").upper()
    return c

def main():
    print("=" * 60)
    print("[*] Big-O Estimator Benchmark Suite")
    print("=" * 60)

    try:
        with open("benchmark_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading benchmark_data.json: {e}")
        return

    print(f"Loaded {len(data)} algorithms for testing.\n")

    results = {}

    for model in OLLAMA_MODELS:
        print(f"[*] Testing Model: {model}")
        
        success_count = 0
        exact_match_time = 0
        exact_match_space = 0
        total_time = 0.0
        total_chars = 0
        total_tests = len(data)

        for item in data:
            code = item["code"]
            lang = item["language"]
            truth_time = item["truth_time_complexity"]
            truth_space = item["truth_space_complexity"]

            sys.stdout.write(f"  - Analyzing {item['name']}... ")
            sys.stdout.flush()

            t0 = time.time()
            res = analyze_complexity(code, lang, model)
            elapsed = time.time() - t0

            if res["success"]:
                success_count += 1
                total_time += elapsed
                total_chars += res.get("raw_char_count", 0)

                calc_time = res.get("time_complexity", "")
                calc_space = res.get("space_complexity", "")
                
                # Check match
                if normalize_complexity(calc_time) == normalize_complexity(truth_time):
                    exact_match_time += 1
                if normalize_complexity(calc_space) == normalize_complexity(truth_space):
                    exact_match_space += 1
                print(f"[SUCCESS] {elapsed:.1f}s")
            else:
                total_time += elapsed
                print(f"[FAIL] {elapsed:.1f}s - {res.get('reasoning', 'No reason')[:30]}...")

        unload_model(model)

        soc = (success_count / total_tests) * 100
        ema_time = (exact_match_time / total_tests) * 100
        ema_space = (exact_match_space / total_tests) * 100
        
        # Approximate Tokens Per Second: Total chars / 4 / total time
        tps = (total_chars / 4.0) / total_time if total_time > 0 else 0
        
        # Speed-Weighted Accuracy Score
        swas = ema_time * (tps / 10.0)

        results[model] = {
            "soc": soc,
            "ema_time": ema_time,
            "ema_space": ema_space,
            "tps": tps,
            "swas": swas,
            "latency_avg": total_time / total_tests if total_tests > 0 else 0
        }
        
        print(f"   => SOC: {soc:.1f}% | Time Acc: {ema_time:.1f}% | TPS: {tps:.1f} | SWAS: {swas:.1f}\n")

    # Generate Markdown Report
    report = "# 🏆 Big-O Estimator Model Leaderboard\n\n"
    report += "| Model | SWAS | Time Acc | Space Acc | JSON SOC | Avg Latency | Appx TPS |\n"
    report += "|---|---|---|---|---|---|---|\n"
    
    # Sort by SWAS descending
    sorted_models = sorted(results.items(), key=lambda x: x[1]["swas"], reverse=True)
    
    for m, vals in sorted_models:
        report += f"| `{m}` | **{vals['swas']:.1f}** | {vals['ema_time']:.1f}% | {vals['ema_space']:.1f}% | {vals['soc']:.1f}% | {vals['latency_avg']:.1f}s | {vals['tps']:.1f} |\n"
    
    report += "\n**Metrics Glossary:**\n"
    report += "- **SWAS (Speed-Weighted Accuracy Score)**: `(Time Acc %) * (TPS / 10)`. The higher the better. Rewards fast and accurate models.\n"
    report += "- **Time/Space Acc**: Exact Match Accuracy (EMA) against ground truth complexity.\n"
    report += "- **JSON SOC**: Structural Output Compliance (Successful JSON parses).\n"
    report += "- **TPS**: Approximate Tokens Per Second (raw characters / 4).\n"

    with open("BENCHMARK_RESULTS.md", "w", encoding="utf-8") as f:
        f.write(report)
        
    print("[*] Benchmarking Complete! Rankings saved to BENCHMARK_RESULTS.md")

if __name__ == "__main__":
    main()
