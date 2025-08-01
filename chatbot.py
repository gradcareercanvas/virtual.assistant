import streamlit as st
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
# Import necessary classes for OpenRouter/OpenAI API
from langchain_openai import ChatOpenAI # Requires langchain-openai package
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain import hub
import os
import glob
import re
import math
import datetime
import pytz
from PIL import Image
import pandas as pd
import numpy as np
import requests
import wolframalpha
import wikipediaapi
import pyperclip
import time
from functools import lru_cache

# Initialize Streamlit
st.set_page_config(
    page_title="🤖 Ultimate Virtual Assistant",
    layout="wide",
    page_icon="🤖"
)
st.title("🤖 Ultimate Virtual Assistant")
st.caption("Your AI-powered Swiss Army Knife")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "files" not in st.session_state:
    st.session_state.files = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "selected_provider" not in st.session_state:
    st.session_state.selected_provider = "Groq" # Default provider

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # --- Provider and API Key Selection ---
    provider = st.radio(
        "Select API Provider",
        options=["Groq", "OpenRouter"],
        index=0, # Default to Groq
        key="provider_radio"
    )
    st.session_state.selected_provider = provider

    api_key = None
    openrouter_api_key = None
    model_name = None
    openrouter_model_name = None # Will hold the selected OpenRouter model

    if provider == "Groq":
        api_key = st.text_input(
            "Enter your Groq API Key",
            type="password",
            help="Get from https://console.groq.com"
        )
        model_name = st.selectbox(
            "🧠 Groq AI Model",
            [
                "llama3-70b-8192",
                "llama3-8b-8192",
                "mixtral-8x7b-32768",
                "whisper-large-v3",
                "llama-3.3-70b-versatile",
                "gemma2-9b-it",
                "deepseek-r1-distill-llama-70b",
                "meta-llama/llama-4-maverick-17b-128e-instruct",
                "moonshotai/kimi-k2-instruct",
                "qwen/qwen3-32b"
            ],
            index=0
        )
        # Disable OpenRouter key input when Groq is selected
        st.text_input("OpenRouter API Key", value="", type="password", disabled=True, help="Not needed for Groq")

    elif provider == "OpenRouter":
        # Disable Groq key/model inputs when OpenRouter is selected
        st.text_input("Groq API Key", value="", type="password", disabled=True, help="Not needed for OpenRouter")
        st.selectbox("Groq AI Model", ["N/A"], disabled=True, help="Not needed for OpenRouter")

        openrouter_api_key = st.text_input(
            "Enter your OpenRouter API Key",
            type="password",
            help="Get from https://openrouter.ai/keys"
        )
        # Updated model list with known working/free models (Avoiding the 'api/v1' error)
        # Check OpenRouter website/model list for currently available free models
        openrouter_model_name = st.selectbox(
            "🧠 OpenRouter AI Model",
            [
                "google/gemma-2-9b-it:free",
                "nousresearch/hermes-3-llama-3.1-8b:free",
                "microsoft/phi-3-mini-128k-instruct:free",
                "neversleep/llama-3-lumimaid-8b:free", # Example, check availability
                "sao10k/frieren-v1:free", # Example, check availability
                "openchat/openchat-7b:free", # Example, check availability
                # Add other models you want to offer
                # "meta-llama/llama-3.1-8b-instruct:free", # Example (might be free)
                # "mistralai/mistral-7b-instruct:free",    # Example (might be free)
            ],
            index=0,
            help="Select an OpenRouter model. Check OpenRouter for current free options."
        )
        st.info(f"Selected OpenRouter model: `{openrouter_model_name}`")


    # --- File Tools and Other Configurations remain the same ---
    st.markdown("---")
    st.header("📁 File Tools")
    uploaded_files = st.file_uploader(
        "Upload files",
        accept_multiple_files=True,
        type=["txt", "pdf", "png", "jpg", "jpeg", "csv"]
    )

    st.markdown("---")
    st.header("🔧 Tools Configuration")
    enable_search = st.checkbox("Enable Web Search", True)
    enable_calculator = st.checkbox("Enable Advanced Calculator", True)
    enable_wikipedia = st.checkbox("Enable Wikipedia", True, help="Requires proper user agent configuration")
    enable_clipboard = st.checkbox("Enable Clipboard", True)

# Wikipedia configuration
def setup_wikipedia():
    """Configure Wikipedia API with proper user agent"""
    user_agent = (
        "VirtualAssistant/1.0 "
        "(https://github.com/yourusername/yourrepo; "
        "youremail@domain.com)"
    )
    return wikipediaapi.Wikipedia(
        language='en',
        user_agent=user_agent,
        extract_format=wikipediaapi.ExtractFormat.WIKI
    )

# Initialize tools
tools = []

# Web Search Tool
if enable_search:
    search = DuckDuckGoSearchRun()
    tools.append(Tool(
        name="Search",
        func=search.run,
        description="Useful for finding current information from the web"
    ))

# Calculator Tool
if enable_calculator:
    def calculator(query):
        try:
            # Consider using a safer eval or a library like sympy for production
            return str(eval(query))
        except Exception as e:
            return f"Calculation error: {str(e)}"

    tools.append(Tool(
        name="Calculator",
        func=calculator,
        description="Useful for math calculations and conversions"
    ))

# Wikipedia Tool
if enable_wikipedia:
    try:
        wiki = setup_wikipedia()

        @lru_cache(maxsize=100)
        def wiki_lookup(query):
            time.sleep(1)  # Respect rate limits
            page = wiki.page(query)
            if page.exists():
                return f"Wikipedia Summary: {page.summary[:500]}..."  # Limited to 500 chars
            return "No Wikipedia page found"

        tools.append(Tool(
            name="Wikipedia",
            func=wiki_lookup,
            description="Useful for factual information from Wikipedia"
        ))
    except Exception as e:
        st.sidebar.warning(f"Wikipedia tool disabled: {str(e)}")

# File operations
def file_operations(action, *args):
    """Handle all file operations"""
    try:
        if action == "list":
            # List files in the uploads directory
            files = os.listdir("uploads") if os.path.exists("uploads") else []
            return "\n".join(files) if files else "No files found in uploads directory."

        elif action == "rename_images":
            # Placeholder for rename_images function if it exists elsewhere
            return "Rename images functionality needs implementation."

        elif action == "read":
            file_path = args[0]
            # Basic security check - only allow reading from uploads directory
            if not os.path.abspath(file_path).startswith(os.path.abspath("uploads")):
                 return "Error: Can only read files from the 'uploads' directory."
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            else:
                return f"Error: File {file_path} not found."

        elif action == "delete":
             file_path = args[0]
             # Basic security check - only allow deleting from uploads directory
             if not os.path.abspath(file_path).startswith(os.path.abspath("uploads")):
                 return "Error: Can only delete files from the 'uploads' directory."
             if os.path.exists(file_path):
                 os.remove(file_path)
                 return f"Deleted {file_path}"
             else:
                 return f"Error: File {file_path} not found to delete."

        return "Unknown file operation. Supported actions: list, read <filename>, delete <filename>."
    except Exception as e:
        return f"Error in file operation: {str(e)}"

tools.append(Tool(
    name="FileOperations",
    func=file_operations,
    description="Useful for file management tasks like listing, reading, deleting files in the 'uploads' directory. Actions: list, read <filename>, delete <filename>."
))

# --- Agent Initialization Logic ---
# Check if necessary keys are provided for the selected provider
init_agent = False
llm_config_valid = False
llm = None

if st.session_state.selected_provider == "Groq" and api_key and model_name:
    init_agent = True
    llm_config_valid = True
elif st.session_state.selected_provider == "OpenRouter" and openrouter_api_key and openrouter_model_name:
    init_agent = True
    llm_config_valid = True

# Reset agent if provider or keys change or become invalid
needs_reset = (
    st.session_state.agent and
    ((st.session_state.selected_provider == "Groq" and (not api_key or not model_name)) or
     (st.session_state.selected_provider == "OpenRouter" and (not openrouter_api_key or not openrouter_model_name))) # Check model name for OpenRouter too
)

if needs_reset:
    st.session_state.agent = None
    st.session_state.agent_executor = None
    # Only show reset message if user has interacted with provider selection
    if 'prev_config' in st.session_state:
        st.sidebar.info("Agent reset due to configuration change.")


if init_agent and llm_config_valid and (not st.session_state.agent or st.session_state.get('prev_config', None) != (st.session_state.selected_provider, api_key, model_name, openrouter_api_key, openrouter_model_name)):
    try:
        # Store current config to detect changes
        st.session_state.prev_config = (st.session_state.selected_provider, api_key, model_name, openrouter_api_key, openrouter_model_name)

        if st.session_state.selected_provider == "Groq":
            llm = ChatGroq(
                groq_api_key=api_key,
                model_name=model_name,
                temperature=0.3
            )
            st.sidebar.success(f"✅ Groq Agent initialized with {model_name}!")

        elif st.session_state.selected_provider == "OpenRouter":
             # Use ChatOpenAI to connect to OpenRouter's API
             llm = ChatOpenAI(
                 base_url="https://openrouter.ai/api/v1",
                 api_key=openrouter_api_key,
                 model=openrouter_model_name, # Specify the selected OpenRouter model here
                 temperature=0.3,
                 # Add headers if needed (optional for rankings)
                 # default_headers = {
                 #     "HTTP-Referer": "YOUR_SITE_URL", # Optional
                 #     "X-Title": "YOUR_SITE_NAME",     # Optional
                 # }
             )
             st.sidebar.success(f"✅ OpenRouter Agent initialized with {openrouter_model_name}!")

        if llm:
            # Ensure you have pulled the correct prompt or define it explicitly
            # The 'hwchase17/react' prompt is common for ReAct agents
            prompt = hub.pull("hwchase17/react")
            if prompt is None:
                 st.sidebar.error("Failed to load the ReAct prompt. Please check the LangChain Hub.")
            else:
                st.session_state.agent = create_react_agent(llm, tools, prompt)
                st.session_state.agent_executor = AgentExecutor(
                    agent=st.session_state.agent,
                    tools=tools,
                    verbose=True,
                    handle_parsing_errors=True,
                    # Optional: Increase max iterations if needed for complex tasks
                    # max_iterations=20
                )
                st.sidebar.success("🧠 Agent is ready!")

    except Exception as e:
        st.sidebar.error(f"Agent initialization error: {str(e)}")
        st.session_state.agent = None
        st.session_state.agent_executor = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("How can I help you today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            try:
                # Process uploaded files
                if uploaded_files:
                    os.makedirs("uploads", exist_ok=True)
                    saved_files = []
                    for file in uploaded_files:
                        # Ensure unique filenames if needed, or handle overwrites
                        file_path = os.path.join("uploads", file.name)
                        with open(file_path, "wb") as f:
                            f.write(file.getbuffer())
                        saved_files.append(file.name)
                    st.success(f"Uploaded files: {', '.join(saved_files)}")

                # Use agent for complex tasks
                response = ""
                if st.session_state.agent_executor:
                    agent_response = st.session_state.agent_executor.invoke({
                        "input": prompt,
                        "chat_history": st.session_state.messages
                    })
                    response = agent_response.get("output", "Agent returned no output.")
                else:
                    # Provide a clearer message if the agent isn't ready
                    if st.session_state.selected_provider == "Groq":
                        response = "Please enter your Groq API Key and select a model, then wait for initialization."
                    elif st.session_state.selected_provider == "OpenRouter":
                         response = "Please enter your OpenRouter API Key, select a model, then wait for initialization."
                    else:
                         response = "Agent not configured. Please check settings."

                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                error_msg = f"Error during processing: ```{str(e)}```"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Additional UI components
with st.expander("🛠️ Available Capabilities"):
    st.markdown("""
    ### This assistant can:
    - Answer general knowledge questions
    - Perform web searches
    - Do complex calculations
    - Manage files (upload, list, read, delete - in 'uploads' folder)
    - Look up Wikipedia articles
    - Get current time/date
    - Convert units
    - And much more!
    """)

with st.expander("📝 Example Commands"):
    st.markdown("""
    Try asking:
    - "What's the weather in Paris?"
    - "Calculate 45*89 + sqrt(144)"
    - "List files in the uploads directory"
    - "Read the contents of <filename.txt>" (if it's in uploads)
    - "Tell me about quantum computing"
    - "Rename all images starting from 100" (if implemented)
    """)

# Create necessary directories
os.makedirs("uploads", exist_ok=True)