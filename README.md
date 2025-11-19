# 📈 FinSight: Autonomous Financial Analyst Agent

## Executive Summary
FinSight is an autonomous AI agent designed to replace manual market research. Unlike standard chatbots, FinSight utilizes a **ReAct (Reason + Act)** architecture with **Python Sandbox execution**. It does not guess financial metrics; it retrieves live data and calculates them mathematically.

**Core Capabilities:**
* **Live Market Data:** Connects to real-time search indices via Tavily.
* **Mathematical Precision:** Writes and executes Python code to calculate volatility and ratios.
* **Self-Correction:** Automatically detects code errors and fixes them before reporting to the user.

---

## 🛠 Technical Architecture
* **Orchestration:** LangGraph (State Machine)
* **LLM:** GPT-4o (Reasoning Engine)
* **Compute:** Python REPL (Sandboxed Code Execution)
* **Frontend:** Next.js 14 (React Server Components)
* **Backend:** FastAPI (High-performance Async API)

---

## 🚀 Installation & Setup

### Prerequisites
* Python 3.11+
* Node.js 18+
* OpenAI API Key

### 1. Backend Setup (The Brain)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt

# Create .env file with your keys
cp .env.example .env

# Start the API Server
python server.py