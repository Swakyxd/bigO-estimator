# 🚀 Roadmap — Big-O Complexity Analyzer

Future improvements planned for the project, organized by effort level.

---

## 🟢 Quick Wins

### 1. Complexity Visualization Graph
Plot theoretical growth curves (`O(1)`, `O(log N)`, `O(N)`, `O(N²)`, `O(2^N)`) using Plotly and highlight where the analyzed code falls. Makes results instantly intuitive.

### 2. Analysis History
Store past analyses in `st.session_state` or SQLite. Let users scroll through previous results without re-running the LLM every time.

### 3. Code Syntax Highlighting
Replace the plain `text_area` with [`streamlit-ace`](https://github.com/okld/streamlit-ace) or [`streamlit-code-editor`](https://github.com/bouzidanas/streamlit-code-editor) for proper syntax-highlighted input with line numbers.

### 4. Confidence Score
Add a `confidence: 0.0–1.0` field to the LLM output. Display as a progress bar — clean bubble sort = 0.95, obfuscated code = 0.4.

### 5. Export Results
Add buttons to download analysis as PDF or Markdown report.

---

## 🟡 Medium Effort

### 6. AST + LLM Hybrid Analysis
Use Python's `ast` module (or `tree-sitter` for multi-language) to extract loop depth, recursion patterns, and function call graphs **before** sending to the LLM.

```
Code → AST Parser → Extract loops/recursion → LLM (with AST context) → Resultabout:blank#blocked
```

Accuracy increases dramatically with structural pre-analysis.

### 7. Side-by-Side Comparison
Let users paste two code snippets and compare their complexities. Perfect for answering: *"Is my optimization actually better?"*

### 8. Batch File Analysis
Upload a `.py` / `.cpp` file and analyze **all functions** in it. Display a table of function names with their individual complexities.

### 9. Streaming Output
Use Ollama's streaming API to show the LLM's reasoning token-by-token instead of waiting 30–60s. Much better UX for local models.

### 10. Multiple Model Support
Add a model selector dropdown (`qwen2.5-coder:7b`, `codellama:13b`, `deepseek-coder:6.7b`). Let users compare how different models analyze the same code.

---

## 🔴 Serious Engineering

### 11. VSCode Extension
Build a VSCode extension: highlight code → right-click → **Analyze Complexity**. Communicates with a local FastAPI backend running the same pipeline.

### 12. Complexity Diff on Git Commits
Analyze complexity of changed functions between two commits. Flag regressions:
> *"This PR increased `sort_users()` from O(N log N) to O(N²)"*

### 13. Benchmark Validation
Actually **run** the code with increasing input sizes (N = 10, 100, 1K, 10K), measure real execution time, and compare against the LLM's theoretical estimate. Plot both curves.

### 14. Multi-Function Call Graph
For complex files, build a function call graph and analyze **composed** complexity. If `A()` calls `B()` inside a loop and `B()` is O(N), then `A()` is at least O(N²).

### 15. CI/CD Integration
GitHub Action that runs complexity analysis on every PR and posts a comment with metrics. Block merges if complexity exceeds thresholds.

---

## 💎 Killer Feature

### 16. Interactive "What If" Mode
Modify code in the editor and re-analyze instantly with a **before/after comparison**. Combined with the complexity visualization graph, this becomes a **live algorithm optimization workspace** — watch the curve flatten as you improve your code.

---

## Contributing

Pick any item above and start building! Each improvement is designed to be independently implementable on top of the existing codebase.
