from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import tool

# --- TOOL 1: WEB SEARCH ---
# This connects to the Tavily API to fetch live financial news/data
# It returns a list of URLs and snippets.
search_tool = TavilySearchResults(max_results=3)

# --- TOOL 2: PYTHON SANDBOX ---
# This allows the agent to execute code. 
# We instantiate it here so we can import it in agent.py
repl = PythonREPL()

@tool
def python_interpreter(code: str):
    """
    A Python shell. Use this to execute python commands. 
    Input should be a valid python script. 
    If you want to see the output of a value, you should print it out with `print(...)`.
    """
    try:
        result = repl.run(code)
        return result
    except Exception as e:
        return f"Failed to execute. Error: {repr(e)}"

# List of tools to export
tools = [search_tool, python_interpreter]