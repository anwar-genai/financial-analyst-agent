from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langserve import add_routes
from langchain_core.messages import HumanMessage
import uvicorn
import traceback

# Import your agent (make sure agent.py is in the same folder)
from agent import app as agent_app 

app = FastAPI(
    title="Financial Analyst Agent",
    version="1.0",
)

# --- FIX CORS ERROR ---
# IMPORTANT: CORS middleware must be added BEFORE other routes
# This allows your frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Add LangServe Routes (for playground and other features)
add_routes(
    app,
    agent_app,
    path="/agent",
)

# Handle OPTIONS preflight requests explicitly with CORS headers
@app.options("/agent/invoke")
async def options_invoke():
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )

# Custom invoke endpoint for direct access
@app.post("/agent/invoke")
async def invoke_agent(request: dict):
    """
    Direct invoke endpoint for the agent.
    Expects: {"input": {"messages": [...], "data_context": null, "intermediate_steps": []}}
    """
    try:
        # Extract input from request
        input_data = request.get("input", request)
        
        # Convert messages to HumanMessage objects if needed
        if "messages" in input_data:
            messages = input_data["messages"]
            # Convert dict messages to HumanMessage objects
            langchain_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    if msg.get("type") == "human":
                        langchain_messages.append(HumanMessage(content=msg.get("content", "")))
                else:
                    langchain_messages.append(msg)
            input_data["messages"] = langchain_messages
        
        # Ensure ALL TypedDict fields are present with defaults
        # Pydantic validation requires all fields to be present, even if Optional
        if "data_context" not in input_data:
            input_data["data_context"] = None
        if "intermediate_steps" not in input_data:
            input_data["intermediate_steps"] = []
        if "code" not in input_data:
            input_data["code"] = None
        if "code_output" not in input_data:
            input_data["code_output"] = None
        if "iterations" not in input_data:
            input_data["iterations"] = 0
        
        # Invoke the agent
        result = agent_app.invoke(input_data)
        
        # Extract base64 images from code output if present
        images = []
        code_output = result.get("code_output", "")
        if code_output and "[VISUALIZATION_BASE64_START]" in code_output:
            import re
            # Extract all base64 images
            pattern = r'\[VISUALIZATION_BASE64_START\](.*?)\[VISUALIZATION_BASE64_END\]'
            matches = re.findall(pattern, code_output, re.DOTALL)
            images = [match.strip() for match in matches if match.strip()]
        
        # Return with CORS headers, including images if any
        response_data = {"output": result}
        if images:
            response_data["images"] = images
        
        return JSONResponse(
            content=response_data,
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
            }
        )
    except Exception as e:
        # Log the full error for debugging
        error_trace = traceback.format_exc()
        print(f"Error in invoke_agent: {error_trace}")
        
        # Return error with CORS headers so frontend can see it
        return JSONResponse(
            status_code=500,
            content={"detail": str(e), "traceback": error_trace},
            headers={
                "Access-Control-Allow-Origin": "http://localhost:3000",
                "Access-Control-Allow-Credentials": "true",
            }
        )

# Add exception handler to ensure CORS headers are always sent
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Allow-Credentials": "true",
        }
    )

if __name__ == "__main__":
    # The --reload flag is set in the terminal command, not here usually,
    # but we keep this for direct script execution.
    uvicorn.run(app, host="localhost", port=8000)
