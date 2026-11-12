<div align="center">

# NecroCD 👻⚡
### Autonomous SRE Control Room & Git Graveyard Pipeline
*Built for Kiroween 2026*

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js_14-black?style=flat&logo=next.js)](https://nextjs.org/)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=flat&logo=supabase)](https://supabase.com/)
[![Three.js](https://img.shields.io/badge/3D-Three.js-black?style=flat&logo=three.js)](https://three.js0org/)
[![Kiro](https://img.shields.io/badge/Powered_by-Kiro_AI-7c3aed?style=flat)](https://kiro.dev/)

[Core Architecture](#-core-architecture) • [Kiro Integration](#-kiro-integration) • [Getting Started](#-getting-started) • [License](#-license)

</div>

---

## 💀 Overview

**NecroCD** is an elite autonomous SRE control room and git graveyard pipeline that treats stale, abandoned repositories and corrupt branches as haunted graves. By combining advanced Abstract Syntax Tree (AST) analysis (`libcst`), secure Docker sandboxing, and an immersive Three.js gothic cemetery dashboard, NecroCD automatically diagnoses legacy code rot, performs surgical refactoring into modern FastAPI/Next.js services, and executes automated exorcisms on broken builds.

---

## 🏛️ Core Architecture

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Engine** | FastAPI, Python `libcst`, Docker | Async ingestion pipeline, AST parsing for legacy syntax rot, and isolated container execution. |
| **3D Cemetery Dashboard** | Next.js App Router, Three.js, Tailwind CSS | Real-time 3D interactive graveyard where branches are rendered as glowing gravestones. |
| **Telemetry & State** | Supabase (PostgreSQL), WebSockets | Tracks ghost telemetry, active exorcism logs, pull request resurrection metrics, and audit trails. |
| **Agentic Core** | Kiro AI, MCP Server, Specs (`/.kiro/`) | Design-first contracts, local model context protocol routing, and pre-commit automation hooks. |

---

## 🕯️ Key Features

* **Interactive 3D Cemetery Canvas:** Stale branches and abandoned PRs appear as 3D gravestones—glowing spectral blue if restable, or pulsing crimson red if corrupted by syntax rot.
* **Poltergeist Event Handler:** When tests fail or dependencies throw errors during refactoring, the UI triggers an immersive mutation: screen shake, phosphor green terminal bleeding into crimson red, and AI-generated Latin stack-trace translations.
* **Surgical AST Refactoring:** Uses Python's `libcst` to preserve code formatting while safely replacing deprecated imports (`urllib2`, old Queue modules) with modern asynchronous FastAPI routers.
* **Zero-Trust MCP Integration:** Local Model Context Protocol server enabling autonomous agents to safely inspect git refs and daemon logs.

---

## 📂 Project Structure

```text
necrocd/
├── .kiro/
│   ├── hooks/
│   │   └── pre-commit-exorcism.py
│   ├── settings/
│   │   └── mcp.json
│   ├── specs/
│   │   └── 01-ast-refactor-engine.md
│   └── steering/
│       └── tech-stack.md
├── backend/
│   ├── main.py
│   ├── parser/
│   │   └── ast_analyzer.py
│   ├── sandbox/
│   │   └── docker_runner.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── CemeteryCanvas.tsx
│   │   └── PoltergeistOverlay.tsx
│   └── package.json
└── README.md
```

---

## ⚙️ Kiro Integration
NecroCD leverages Kiro for design-first engineering and autonomous execution:
 * Specs (/.kiro/specs/): Enforces strict AST transformation contracts before code generation begins.
 * MCP Server (/.kiro/settings/mcp.json): Grants the Kiro agent secure, sandboxed access to local git repository references.
 * Agent Hooks: Automated pre-commit hooks that trigger exorcism scripts on dead branches.

--- 

## 🚀 Getting Started
Prerequisites
 * Python 3.11+
 * Node.js 18+ & npm
 * Docker Daemon running locally
1. Clone the Repository

```
git clone [https://github.com/brysyl/NecroCD.git](https://github.com/brysyl/NecroCD.git)
cd necrocd
```
3. Run the Backend

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
5. Run the Frontend
```
cd ../frontend
npm install
npm run dev
```
Open http://localhost:3000 to enter the NecroCD SRE Control Room.
---
## 🛡️ License
Distributed under the MIT License. See LICENSE for more information.

<div align="center">
<p>✨ <em>Summoning clean code from the digital netherworld.</em> ✨</p>
</div>

