# Bhutan Citizen Service Guidance Agent

An AI-powered government service guidance system designed to help citizens find information about government services in Bhutan through natural language conversations.

## 1. Project Overview

The Bhutan Citizen Service Guidance Agent is a custom AI agent developed to simplify access to government service information in Bhutan. It allows users to ask questions in natural language and receive relevant guidance about available government services.

The system uses a locally running Large Language Model (LLM), LangGraph workflow orchestration, a searchable government service knowledge base, and SQLite-based memory to provide contextual responses.

The project is developed as part of the DAT404 Custom AI Agent assignment.

## 2. Problem Statement

Citizens may find it difficult to locate relevant information about government services because information can be spread across different websites and official platforms.

This project aims to provide a centralized conversational interface where citizens can ask questions and receive relevant guidance about government services without manually searching through multiple sources.

## 3. Project Objectives

- Develop a conversational AI agent for Bhutanese government service guidance.
- Retrieve relevant government services based on natural language queries.
- Use an LLM to understand citizen requests and generate responses.
- Implement memory to maintain conversational context.
- Collect citizen feedback and adapt response behaviour.
- Evaluate retrieval performance and visualize results.
- Implement safety mechanisms to reduce irrelevant or unsupported responses.

## 4. Main Features

### 4.1 Natural Language Understanding
Citizens can ask questions using everyday language rather than predefined commands.

### 4.2 Government Service Search
Uses TF-IDF vectorization and cosine similarity to identify relevant services from the knowledge base.

### 4.3 LLM-Based Reasoning
Uses Ollama with the Qwen3 1.7B model to interpret citizen requests and generate guidance.

### 4.4 LangGraph Workflow
Organizes the agent's reasoning, planning, retrieval, and response-generation stages.

### 4.5 Conversation Memory
Uses SQLite to store previous interactions and retrieve recent conversation history.

### 4.6 Citizen Feedback
Allows users to rate responses and provide comments.

### 4.7 Feedback-Based Adaptation
Uses stored feedback to adjust response-generation instructions and improve response behaviour.

### 4.8 Safety and Guardrails
Includes input validation, retrieval confidence checks, safe fallback responses, and output validation.

### 4.9 Evaluation and Visualization
Evaluates service retrieval performance and citizen feedback using Python, Pandas, and Matplotlib.

## 5. Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| LangGraph | Agent workflow orchestration |
| Ollama | Local LLM execution |
| Qwen3 1.7B | Language model |
| Scikit-learn | TF-IDF and cosine similarity |
| SQLite | Conversation memory and feedback storage |
| Streamlit | User interface |
| Pandas | Evaluation and data processing |
| Matplotlib | Evaluation visualizations |

## 6. System Architecture

The agent follows this workflow:

1. Citizen submits a question through Streamlit.
2. Input validation checks the submitted query.
3. The LLM interprets the citizen's request.
4. The service search tool retrieves relevant government services.
5. The planning stage checks retrieval confidence.
6. Relevant service information is retrieved.
7. The LLM generates a response based on the available service information.
8. The interaction is stored in SQLite.
9. The citizen can submit feedback.
10. Feedback is used to adapt future response-generation instructions.

If the input is invalid or the system cannot confidently identify a relevant service, it returns a safe fallback response.

## 7. Project Structure

```text
Bhutan-Citizen-Service-Agent/
│
├── agent/
│   ├── __init__.py
│   └── workflow.py
│
├── data/
│   └── services.json
│
├── evaluation/
│   ├── evaluate.py
│   └── results/
│       ├── retrieval_results.png
│       ├── feedback_ratings.png
│       ├── retrieval_evaluation.csv
│       └── evaluation_metrics.csv
│
├── memory/
│   └── database.py
│
├── safety/
│   ├── __init__.py
│   └── guardrails.py
│
├── tools/
│   ├── __init__.py
│   └── service_tools.py
│
├── utils/
│   └── llm_client.py
│
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## 8. Installation and Setup

### Prerequisites

- Python 3.10 or later
- Ollama
- Git (optional)

### Step 1: Clone the repository

```bash
git clone <your-github-repository-url>
cd Bhutan-Citizen-Service-Agent
```

### Step 2: Create a virtual environment

```powershell
python -m venv .venv
```

### Step 3: Activate the environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 5: Install and run the language model

Install Ollama from:

https://ollama.com/

Download the required model:

```powershell
ollama pull qwen3:1.7b
```

Make sure Ollama is running before starting the application.

## 9. Running the Application

From the project root directory, run:

```powershell
streamlit run app.py
```

The application will open in your browser, normally at:

```text
http://localhost:8501
```

## 10. Running the Evaluation

Run the evaluation module from the project root:

```powershell
python -m evaluation.evaluate
```

The evaluation script measures retrieval accuracy, retrieval coverage, and citizen feedback statistics.

The generated graphs and CSV files are saved inside:

```text
evaluation/results/
```

## 11. Evaluation Results

The latest preliminary evaluation produced the following results:

| Metric | Result |
|---|---:|
| Total test questions | 4 |
| Correct retrievals | 4 |
| Retrieval accuracy | 100% |
| Retrieval coverage | 100% |
| Total citizen feedback | 16 |
| Average feedback rating | 4.25/5 |
| Positive feedback | 12 |
| Neutral feedback | 1 |
| Negative feedback | 3 |

The retrieval evaluation achieved 100% accuracy and coverage across the four test questions. These results are preliminary because the test dataset is small.

## 12. Limitations

- The current knowledge base contains a limited number of government services.
- The quality of responses depends on the accuracy and completeness of the stored service information.
- Retrieval performance may decrease when users submit misspelled or ambiguous queries.
- The system requires Ollama and a locally available language model.
- The evaluation dataset is relatively small and requires further testing.
- The system provides guidance and does not replace official government services or decisions.

## 13. Future Improvements

- Expand the knowledge base to cover more Bhutanese government services.
- Improve spelling correction and query understanding.
- Add multilingual support, including Dzongkha.
- Improve retrieval using semantic embeddings.
- Expand the evaluation dataset.
- Improve feedback-based adaptation using more citizen interactions.
- Add links to verified official sources and regularly update service information.

## 14. Disclaimer

This agent is an educational project developed for government service information guidance. It is not an official government platform. Citizens should verify important requirements, procedures, fees, and eligibility conditions through the relevant official government sources.

## 15. Author

Developed as an individual project for the DAT404 Custom AI Agent assignment.