import matplotlib.pyplot as plt
import os
import numpy as np

results = {
    'llama3.2:latest': {'swas': 359.6, 'tps': 41.1, 'ema_time': 87.5, 'ema_space': 75.0, 'soc': 100.0, 'latency_avg': 5.6},
    'gemma3:4b': {'swas': 258.6, 'tps': 34.5, 'ema_time': 75.0, 'ema_space': 87.5, 'soc': 100.0, 'latency_avg': 8.0},
    'mistral:latest': {'swas': 102.1, 'tps': 11.7, 'ema_time': 87.5, 'ema_space': 100.0, 'soc': 100.0, 'latency_avg': 17.4},
    'qwen2.5-coder:7b': {'swas': 71.4, 'tps': 9.5, 'ema_time': 75.0, 'ema_space': 87.5, 'soc': 100.0, 'latency_avg': 20.1}
}

sorted_models = sorted(results.items(), key=lambda x: x[1]['swas'], reverse=True)
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
ax.invert_yaxis()  # labels read top-to-bottom
ax.set_xlabel('Average Seconds per Request (Lower is Better)')
ax.set_title('Average Pipeline Latency Response Time')

# Add labels on bars
for bar in bars:
    width = bar.get_width()
    ax.text(width + 0.3, bar.get_y() + bar.get_height()/2, 
            f'{width:.1f}s', ha='left', va='center')

fig.tight_layout()
plt.savefig('assets/benchmark_latency.png', facecolor='white', dpi=150)
plt.close()

print("All graphs successfully generated with white backgrounds!")
