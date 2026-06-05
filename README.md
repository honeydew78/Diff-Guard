# 🛡️ Diff-Guard: Stateless AST-Based Architectural Risk Engine

Diff-Guard is a stateless, high-performance static analyzer and developer tool designed to run in continuous integration (CI) environments, webhook containers, or as a local dashboard. By translating source code into Abstract Syntax Trees (ASTs) rather than parsing raw text differences, Diff-Guard resolves modified semantic entities (like functions) and calculates their exact architectural "blast radius" upward through your codebase using a directed dependency call graph.

---

## ✨ Features
- **In-Memory Operations:** Bypasses disk-heavy git clones. It streams gzipped code archives directly into memory buffers, making it lightweight and highly scalable.
- **AST Change Intersection:** Maps changed code coordinates directly to tree-sitter AST nodes to find altered semantic functions.
- **Transitive Impact Graph:** Reconstructs your repository's dependency graph in-memory using `networkx` to run upstream BFS queries.
- **Automated PR Reviewer:** Posts clear, structured feedback reports containing a calculated risk score directly to the developer's GitHub Pull Request.
- **Interactive React Dashboard:** A visually stunning, glassmorphic UI built with React and Cytoscape.js. It allows developers to visualize the blast radius of any two commits and keeps a history of past analyses using local storage.

---

## 📸 Dashboard & Reports

### Interactive Dependency Graph
The Diff-Guard dashboard provides an interactive network graph of your codebase. It highlights modified files (orange) and impacted downstream consumers (purple) so you can instantly see the architectural impact of a change.

![Diff-Guard Dashboard](dashboard.png)
<img width="2940" height="1594" alt="image" src="https://github.com/user-attachments/assets/f06a03e5-5815-4a82-ba46-66286007763a" />


### Automated PR Comments
When integrated via GitHub webhooks, Diff-Guard automatically posts a detailed markdown report directly on your Pull Requests, listing the affected downstream modules and functions at risk.

---

## 🚦 Understanding the Risk Score

Diff-Guard calculates a **Risk Score (0-100)** to quantify the *architectural fragility* of a change. It doesn't measure code quality (like a linter), but rather how interconnected the modified code is. This helps teams prioritize code review time and testing resources.

- 🟢 **Low Risk (0 - 49%) - *Isolated Change*:** 
  The modified files are "leaf nodes" (e.g., standalone scripts, tests, isolated features) and have few downstream dependents.
  - *Context:* Junior/mid-level engineers can confidently approve. Minimal regression testing needed.
  
- 🟡 **Medium Risk (50 - 79%) - *Moderate Dependency*:**
  The change modifies components imported by multiple downstream modules, but isn't core infrastructure.
  - *Context:* Reviewers should check the interfaces. QA should write or run integration tests specifically for the impacted downstream modules.

- 🔴 **High Risk (80 - 100%) - *Core Infrastructure Change*:**
  The modified code is highly centralized (e.g., database connection handler, core authentication module). A bug here will cascade through the entire system.
  - *Context:* Requires a Senior Engineer or Tech Lead review. Meticulous backward compatibility checks and exhaustive regression test suites are justified.

---

## 🛠️ Architecture

```text
                       [GitHub PR Event / Local Form Submit]
                                   │
                                   ▼
      ┌────────────────────────────┴────────────────────────────┐
      │ Concurrent Stream Capture (Base vs. Head commit)        │
      │   ├─► Stream Base Tarball into RAM                      │
      │   └─► Stream Head Tarball into RAM                      │
      └────────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
      ┌────────────────────────────┴────────────────────────────┐
      │ AST parsing (Tree-sitter) & Dependency Graph Builder    │
      └────────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
      ┌────────────────────────────┴────────────────────────────┐
      │ Diff Intersection & BFS Traversal                       │
      │   ├─► Intersect line diffs with AST ranges             │
      │   └─► Trace impact paths upward using networkx          │
      └────────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
      ┌────────────────────────────┴────────────────────────────┐
      │ Formatted JSON Response / Automated PR Comment          │
      └─────────────────────────────────────────────────────────┘
```

---

## 🚀 Setup & Execution

### 1. Requirements
Ensure you are running Python 3.9+ and have installed the required dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Local Test Suite
To verify the parsing and graph reachability engine works end-to-end:
```bash
python sandbox_test.py
```

### 3. Start the Web Dashboard and API
Start the Uvicorn-based FastAPI app locally:
```bash
# Set your GitHub token to increase API rate limits or dispatch PR comments
export GITHUB_TOKEN="your_personal_access_token"

# Run Uvicorn dev server
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Once running, open your browser and navigate to **`http://localhost:8000/dashboard/`** to access the interactive web interface.

---

## 🕸️ API Endpoints
- **Webhook Endpoint:** `POST /webhook` (For automated GitHub PR analysis)
- **Local Analysis Endpoint:** `POST /api/analyze` (For ad-hoc analysis via the dashboard)

---

## 📦 Directory Structure
- `frontend/`: React + Cytoscape UI (`App.js`, `style.css`, `index.html`).
- `parser.py`: Tree-sitter parsing wrappers and function coordinate extractor.
- `graph_engine.py`: Dependency graph assembly and BFS tracer using networkx.
- `streaming_client.py`: In-memory sequential streaming and tar archive extractor.
- `app.py`: FastAPI web server and webhook/dashboard pipeline controller.
- `cli.py`: Command line interface for testing analyses locally.
