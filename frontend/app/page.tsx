"use client"; // Required for React hooks

import { useState, useRef, useEffect } from "react";

// Define the shape of a message
type Message = {
  role: "user" | "assistant";
  content: string;
};

// Define the API URL using environment variables for deployment
// Fallback to localhost:8000 for local development
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function FinancialAgent() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(scrollToBottom, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    // 1. Add User Message to UI
    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input; // Capture input before clearing
    setInput("");
    setIsLoading(true);

    try {
      // 2. Send to FastAPI Backend (using the robust structure)
      const response = await fetch(`${API_URL}/agent/invoke`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // Payload must match backend expectations: LangServe requires 'input' wrapper
        // LangServe expects LangChain message format with 'type' and 'content' only
        // Also need to provide ALL TypedDict fields with initial values (Pydantic validation)
        body: JSON.stringify({
          input: {
            messages: [
              {
                type: "human",
                content: currentInput
              }
            ],
            data_context: null,
            intermediate_steps: [],
            code: null,
            code_output: null,
            iterations: 0
          }
        }),
      });

      if (!response.ok) {
        // Log status to help debugging
        console.error("API Response Status:", response.status);
        // Try to get error details from response
        let errorMessage = `Network response was not ok. Status: ${response.status}`;
        try {
          const errorData = await response.json();
          console.error("Error details:", errorData);
          errorMessage += `. Details: ${JSON.stringify(errorData)}`;
        } catch (e) {
          // If response is not JSON, just use status
        }
        throw new Error(errorMessage); 
      }

      const data = await response.json();

      // 3. Parse Response
      // LangServe returns the final state. We extract the last message.
      if (data.output && data.output.messages && data.output.messages.length > 0) {
        const aiContent = data.output.messages[data.output.messages.length - 1].content;
        
        // Check if there are images to display
        let contentWithImages = aiContent;
        if (data.images && data.images.length > 0) {
          // Append HTML img tags for base64 images
          const imageHtml = data.images.map((imgBase64: string, idx: number) => 
            `\n\n<img src="data:image/png;base64,${imgBase64}" alt="Chart ${idx + 1}" style="max-width: 100%; height: auto; margin: 10px 0; border-radius: 8px;" />`
          ).join('\n');
          contentWithImages = aiContent + imageHtml;
        }
        
        const aiMessage: Message = { role: "assistant", content: contentWithImages };
        setMessages((prev) => [...prev, aiMessage]);
      } else {
        throw new Error("Invalid response format from server");
      }
      
    } catch (error) {
      console.error("Agent Error:", error);
      
      // Provide more specific error messages
      let errorMessage = "Could not reach the Agent.";
      if (error instanceof TypeError && error.message.includes("fetch")) {
        errorMessage = `⚠️ Connection Error: The backend server at ${API_URL} is not reachable. Please ensure:
1. The backend server is running (check backend terminal)
2. The server is running on port 8000
3. No firewall is blocking the connection`;
      } else if (error instanceof Error) {
        errorMessage = `⚠️ Error: ${error.message}`;
      } else {
        errorMessage = `⚠️ Error: ${String(error)}`;
      }
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: errorMessage },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-gray-100 font-sans">
      {/* --- HEADER --- */}
      <header className="p-4 border-b border-gray-800 bg-gray-900 flex items-center gap-3 shadow-md">
        <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
        <h1 className="text-lg font-bold tracking-wide text-white">
          FinSight <span className="text-blue-400">Agent</span>
        </h1>
      </header>

      {/* --- CHAT AREA --- */}
      <main className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-60">
            <p className="text-xl font-medium">Ready to analyze the markets.</p>
            <p className="text-sm">Try asking: "Compare Apple and Microsoft volatility"</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-2xl p-4 shadow-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-none"
                  : "bg-gray-800 text-gray-100 border border-gray-700 rounded-bl-none"
              }`}
            >
              {msg.role === "assistant" && msg.content.includes("<img") ? (
                <div 
                  className="text-sm leading-relaxed prose prose-invert max-w-none"
                  dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br />') }}
                />
              ) : (
                <p className="whitespace-pre-wrap text-sm leading-relaxed">
                  {msg.content}
                </p>
              )}
            </div>
          </div>
        ))}
        
        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-none p-4 flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-75"></div>
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-150"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* --- INPUT AREA --- */}
      <footer className="p-4 bg-gray-900 border-t border-gray-800">
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto relative flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the analyst..."
            className="flex-1 bg-gray-800 text-white border border-gray-700 rounded-xl px-5 py-4 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-500 shadow-inner transition-all"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg p-2 transition-colors"
          >
            {/* Send Icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-6 h-6"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
              />
            </svg>
          </button>
        </form>
      </footer>
    </div>
  );
}