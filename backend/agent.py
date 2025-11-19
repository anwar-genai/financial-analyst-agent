import os
from typing import TypedDict, Annotated, List, Optional, Tuple
import operator
from langgraph.graph import StateGraph, END

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_experimental.utilities import PythonREPL

# --- CONFIGURATION ---
# os.environ["OPENAI_API_KEY"] = "sk-..."
# os.environ["TAVILY_API_KEY"] = "tvly-..."

# --- 1. DEFINE THE STATE ---
# This is the memory that gets passed between nodes
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    # Optional fields - use .get() to access safely
    data_context: Optional[str]  # Contextual data for the report
    intermediate_steps: Annotated[List[Tuple[str, str]], operator.add]
    code: Optional[str]  # Generated Python code
    code_output: Optional[str]  # Output from code execution
    iterations: Optional[int]  # Number of retry iterations

# --- 2. INITIALIZE TOOLS ---
llm = ChatOpenAI(model="gpt-4o", temperature=0)
search_tool = TavilySearchResults(max_results=3)
python_repl = PythonREPL()

# --- 3. DEFINE THE NODES ---

def research_node(state: AgentState):
    """Finds live data using search."""
    print("--- RESEARCHING ---")
    question = state["messages"][-1].content
    
    # We ask the LLM to act as a researcher using the tool
    search_result = search_tool.invoke(question)
    
    # We store the result in the state
    return {"data_context": str(search_result), "iterations": 0}

def coder_node(state: AgentState):
    """Writes Python code to analyze the data."""
    print("--- WRITING CODE ---")
    data = state.get("data_context", "")
    question = state["messages"][-1].content
    prev_error = state.get("code_output", "")

    # Prompt includes data AND previous errors (for self-correction)
    error_context = f"\n\nPREVIOUS ERROR: {prev_error[:500]}\nFix this error." if prev_error and "Error" in prev_error else ""
    # Limit data context to avoid token limits
    data_summary = data[:500] if len(data) > 500 else data
    
    prompt = f"""Write Python code to answer: {question}
{error_context}

REQUIREMENTS:
- Use yfinance, pandas, numpy, matplotlib
- Validate data exists before accessing (check empty, length)
- Convert Series to float() before f-string formatting
- Create visualizations for comparisons (bar/line charts)
- Use matplotlib.use('Agg'), save to BytesIO, encode base64
- Print: [VISUALIZATION_BASE64_START]\\n<base64>\\n[VISUALIZATION_BASE64_END]
- Use try-except, validate before iloc[-1]
- Output ONLY code, no markdown

Pattern:
import yfinance as yf, pandas as pd, numpy as np, matplotlib.pyplot as plt, matplotlib, io, base64
matplotlib.use('Agg')
# Get data with yf.download(), validate, calculate metrics, create plot, encode, print
"""
    
    response = llm.invoke(prompt)
    # Clean up the response - remove markdown code blocks if present
    code = response.content.strip()
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    code = code.strip()
    
    return {"code": code}

def execute_node(state: AgentState):
    """Runs the code in a sandbox."""
    print("--- EXECUTING CODE ---")
    code = state.get("code", "")
    
    if not code:
        return {"code_output": "Error: No code to execute", "iterations": state.get("iterations", 0) + 1}
    
    try:
        # Provides the code to the Python REPL
        output = python_repl.run(code)
        # If output is empty or None, it might have printed instead
        if not output or output.strip() == "":
            output = "Code executed successfully (check for print statements in code)"
        return {"code_output": output, "iterations": state.get("iterations", 0) + 1}
    except Exception as e:
        error_msg = str(e)
        # Provide more detailed error information
        import traceback
        tb = traceback.format_exc()
        return {"code_output": f"Error: {error_msg}\nTraceback: {tb}", "iterations": state.get("iterations", 0) + 1}

def report_node(state: AgentState):
    """Synthesizes the final answer."""
    print("--- REPORTING ---")
    question = state["messages"][-1].content
    code_output = state.get("code_output", "No output available")
    
    # Limit code_output to avoid token limits (keep last 2000 chars which usually has the results)
    code_output_summary = code_output[-2000:] if len(code_output) > 2000 else code_output
    
    prompt = f"""Write a financial analysis based on these results:

Question: {question}
Results: {code_output_summary}

Requirements:
- Use ACTUAL numbers from results above
- Be direct and factual, no templates/placeholders
- Include specific metrics and percentages
- Mention if visualizations were created
- Start with analysis, no email formatting

Analysis:"""
    
    response = llm.invoke(prompt)
    return {"messages": [response]}

# --- 4. DEFINE THE LOGIC (EDGES) ---

def should_retry(state: AgentState):
    """Decides if we need to fix the code or move to report."""
    output = state.get("code_output", "")
    iters = state.get("iterations", 0)
    
    # If there is an error or empty output, and we haven't tried too many times
    if output and ("Error" in output or "traceback" in output.lower()) and iters < 3:
        print("--- ERROR DETECTED: RETRYING ---")
        return "coder_node" # Loop back to fix code
    return "report_node"

# --- 5. BUILD THE GRAPH ---

workflow = StateGraph(AgentState)

workflow.add_node("research_node", research_node)
workflow.add_node("coder_node", coder_node)
workflow.add_node("execute_node", execute_node)
workflow.add_node("report_node", report_node)

workflow.set_entry_point("research_node")
workflow.add_edge("research_node", "coder_node")
workflow.add_edge("coder_node", "execute_node")

# The Conditional Edge: The "Smart" Part
workflow.add_conditional_edges(
    "execute_node",
    should_retry,
    {
        "coder_node": "coder_node",
        "report_node": "report_node"
    }
)
workflow.add_edge("report_node", END)

app = workflow.compile()

# --- 6. RUN IT ---
if __name__ == "__main__":
    request = "Compare the stock price volatility of Apple vs Microsoft over the last week using data you find online."
    inputs = {"messages": [HumanMessage(content=request)]}
    
    result = app.invoke(inputs)
    print("\nFINAL ANSWER:\n", result["messages"][-1].content)