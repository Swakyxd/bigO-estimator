import json
import time
import os
import sys
import re
import matplotlib.pyplot as plt

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

    # Sort by SWAS descending
    sorted_models = sorted(results.items(), key=lambda x: x[1]["swas"], reverse=True)

    # Generate Matplotlib Graphs
    import numpy as np
    
    models = [m.split(':')[0] for m, v in sorted_models]
    raw_models = [m for m, v in sorted_models]
    os.makedirs('assets', exist_ok=True)

    # 1. SWAS & TPS (Speed Chart)
    fig, ax1 = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    ax1.set_facecolor('white')

    x = np.arange(len(models))
    width = 0.35

    ax1.bar(x - width/2, [results[m]['swas'] for m in raw_models], width, label='SWAS Score', color='#2ecc71')
    ax2 = ax1.twinx()
    ax2.bar(x + width/2, [results[m]['tps'] for m in raw_models], width, label='Tokens/Sec', color='#3498db')

    ax1.set_ylabel('Speed-Weighted Accuracy Score (SWAS)', color='#2ecc71')
    ax2.set_ylabel('Generation Speed (TPS)', color='#3498db')
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, rotation=15, ha='right')
    ax1.set_title('Local Model Speed & Efficiency Performance', pad=15)
    fig.legend(loc='upper right', bbox_to_anchor=(0.9, 0.9))
    fig.tight_layout()
    plt.savefig('assets/benchmark_speed.png', facecolor='white', dpi=150)
    plt.close()

    # 2. Accuracy Metrics Chart
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    width = 0.25

    ax.bar(x - width, [results[m]['ema_time'] for m in raw_models], width, label='Time Acc %', color='#9b59b6')
    ax.bar(x, [results[m]['ema_space'] for m in raw_models], width, label='Space Acc %', color='#e67e22')
    ax.bar(x + width, [results[m]['soc'] for m in raw_models], width, label='JSON SOC %', color='#34495e')

    ax.set_ylabel('Percentage Accuracy (%)')
    ax.set_title('Analytical Rigor & JSON Compliance', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=15, ha='right')
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=3)
    fig.tight_layout()
    plt.savefig('assets/benchmark_accuracy.png', facecolor='white', dpi=150)
    plt.close()

    # 3. Latency Chart (Horizontal)
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    y_pos = np.arange(len(models))
    latency = [results[m]['latency_avg'] for m in raw_models]
    bars = ax.barh(y_pos, latency, align='center', color='#e74c3c')
    ax.set_yticks(y_pos, labels=models)
    ax.invert_yaxis()
    ax.set_xlabel('Average Seconds per Request (Lower is Better)')
    ax.set_title('Average Pipeline Latency Response Time')

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.3, bar.get_y() + bar.get_height()/2, 
                f'{w:.1f}s', ha='left', va='center')

    fig.tight_layout()
    plt.savefig('assets/benchmark_latency.png', facecolor='white', dpi=150)
    plt.close()

    # Generate Markdown Report
    report = "# 🏆 Big-O Estimator Model Leaderboard\n\n"
    report += "### ⏱️ Speed & Efficiency\n![Speed Graph](assets/benchmark_speed.png)\n\n"
    report += "### 🎯 Accuracy & Compliance\n![Accuracy Graph](assets/benchmark_accuracy.png)\n\n"
    report += "### 🚀 Latency Profile\n![Latency Graph](assets/benchmark_latency.png)\n\n"
    report += "| Model | SWAS | Time Acc | Space Acc | JSON SOC | Avg Latency | Appx TPS |\n"
    report += "|---|---|---|---|---|---|---|\n"
    
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
