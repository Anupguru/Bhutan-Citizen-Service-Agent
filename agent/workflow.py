
import json

from utils.llm_client import generate_llm_response
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, START, END

from tools.service_tools import (
    search_services,
    get_service_details
)

from safety.guardrails import (
    validate_input,
    check_retrieval_confidence,
    safe_fallback_response,
    validate_output
)

from memory.database import (
    init_db,
    save_interaction,
    get_recent_interactions,
    save_feedback,
    get_adaptation_guidance
)

# ==========================================
# 1. DEFINE AGENT STATE
# ==========================================

class AgentState(TypedDict, total=False):

    query: str
    original_query: str

    session_id: str

    recent_history: list

    search_results: list

    selected_service_id: Optional[int]

    service_details: dict

    response: str

    next_action: str

    tools_used: list

    llm_reasoning: str
    
    llm_available: bool

    agent_steps: list

    input_error: str


# ==========================================
# 2. UNDERSTAND CITIZEN REQUEST
# ==========================================




def understand_request(state: AgentState):

    print("\n[AGENT] Understanding citizen request...")

    current_query = state.get(
        "original_query",
        state.get("query", "")
    )

    history = state.get("recent_history", [])

    # Validate citizen input
    is_valid, error_message = validate_input(current_query)

    if not is_valid:

        print("[SAFETY] Invalid citizen input.")

        return {
            "query": "",
            "original_query": current_query,
            "input_error": error_message,
            "agent_steps": state.get("agent_steps", []) + [
                "Rejected invalid citizen input"
            ]
        }

    # Preserve the original question
    current_query = current_query.strip()
    combined_query = current_query

    follow_up_phrases = [
        "what about",
        "tell me more",
        "where can i",
        "what documents",
        "which documents",
        "how much",
        "what is the procedure",
        "can you explain",
        "how long",
        "where do i"
    ]

    is_follow_up = any(
        phrase in current_query.lower()
        for phrase in follow_up_phrases
    )

    if is_follow_up and history:

        previous_query = ""

        for interaction in history:

            old_query = interaction.get(
                "query", ""
            ).strip().lower()

            if any(
                word in old_query
                for word in [
                    "passport",
                    "birth",
                    "death",
                    "driving licence"
                ]
            ):

                previous_query = interaction.get(
                    "query", ""
                ).strip()

                break

        if previous_query:

            combined_query = (
                previous_query + " " + current_query
            )

            print("[MEMORY] Previous conversation found.")
            print("[MEMORY] Previous request:", previous_query)
            print("[MEMORY] Follow-up request:", current_query)

    print("[AGENT] Processing:", combined_query)

    return {
        "query": combined_query,
        "original_query": current_query,
        "input_error": "",
        "agent_steps": state.get("agent_steps", []) + [
            "Understood citizen request",
            "Checked recent conversation memory",
            "Validated citizen input"
        ]
    }



def llm_reasoning_node(state: AgentState):
    print("\n[LLM] Interpreting citizen request...")

    current_query = state.get("query", "")
    original_query = state.get("original_query", current_query)

    history = state.get("recent_history", [])

    system_prompt = """
You are an intent-understanding component for a
Bhutan Citizen Service Guidance Agent.

Your task is to interpret a citizen's question and
produce a concise search query for a government
service knowledge base.

Rules:
1. Use previous conversation context when relevant.
2. Identify the government service being discussed.
3. Preserve the actual intent of the latest question.
4. Do not invent government service information.
5. Return only the search keywords or phrase.
6. Never return commands such as /search.
7. Do not answer the citizen's question.
8. If the service is not clear, preserve the original
   question rather than guessing.
"""

    user_prompt = f"""
Previous conversation:
{json.dumps(history[:3], ensure_ascii=False)}

Current citizen question:
{original_query}

Context-enriched question:
{current_query}

Produce the best concise search query.
"""

    try:
        reasoning = generate_llm_response(
            system_prompt,
            user_prompt
        )

        reasoning = reasoning.strip()
        if reasoning.lower().startswith("/search"):
            reasoning = reasoning[7:].strip()
            if not reasoning:
                raise ValueError("Empty LLM reasoning result.")

        print("[LLM] Interpreted search query:", reasoning)

        return {
            "query": reasoning,
            "llm_reasoning": reasoning,
            "llm_available": True,
            "agent_steps": state.get("agent_steps", []) +
                           ["Used LLM to interpret citizen intent"]
        }

    except Exception as error:
        print("[LLM ERROR]", error)
        print("[LLM] Falling back to the original search query.")

        return {
            "query": current_query,
            "llm_reasoning": "LLM unavailable; used original query.",
            "llm_available": False,
            "agent_steps": state.get("agent_steps", []) +
                           ["LLM unavailable; used existing search logic"]
        }



# ==========================================
# 3. SEARCH GOVERNMENT SERVICES
# ==========================================

def search_services_node(state: AgentState):

    print("\n[TOOL] Executing search_services...")

    query = state["query"]

    results = search_services(query, top_k=3)

    tools_used = state.get("tools_used", []) + [
        "search_services"
    ]

    print(f"[TOOL] Search results: {results}")

    return {
        "search_results": results,
        "tools_used": tools_used,
        "agent_steps": state.get("agent_steps", []) + [
            "Searched government service knowledge base"
        ]
    }


# ==========================================
# 4. AGENT PLANNING AND DECISION MAKING
# ==========================================



def plan_next_action(state: AgentState):

    print("\n[AGENT] Planning next action...")

    # Check whether the input was rejected
    input_error = state.get("input_error", "")

    if input_error:

        print("[SAFETY] Input validation failed.")

        return {
            "next_action": "fallback",
            "agent_steps": state.get("agent_steps", []) + [
                "Stopped processing invalid input"
            ]
        }

    results = state.get("search_results", [])

    if not results:

        print("[AGENT] No relevant service found.")

        return {
            "next_action": "fallback",
            "agent_steps": state.get("agent_steps", []) + [
                "No relevant service found"
            ]
        }

    best_match = results[0]

    print("[AGENT] Best match:", best_match["name"])

    score = best_match.get("similarity_score", 0)

    print("[AGENT] Similarity score:", round(score, 3))

    # Check retrieval confidence
    confidence_passed = check_retrieval_confidence(
        results,
        threshold=0.25
    )

    if confidence_passed:

        print("[AGENT] Relevant service identified.")

        return {
            "selected_service_id": best_match["id"],
            "next_action": "retrieve",
            "agent_steps": state.get("agent_steps", []) + [
                "Relevant government service identified",
                "Retrieval confidence check passed"
            ]
        }

    print("[SAFETY] Retrieval confidence too low.")

    return {
        "next_action": "fallback",
        "agent_steps": state.get("agent_steps", []) + [
            "Retrieval confidence check failed",
            "Requested clarification due to low match confidence"
        ]
    }


# ==========================================
# 5. ROUTE AGENT TO THE NEXT ACTION
# ==========================================



def route_agent(state: AgentState):

    # Stop invalid inputs before retrieval
    if state.get("input_error"):
        return "fallback"

    next_action = state.get("next_action", "fallback")

    if next_action == "retrieve":
        return "retrieve"

    return "fallback"




# ==========================================
# 6. RETRIEVE SERVICE INFORMATION
# ==========================================

def retrieve_service(state: AgentState):

    print("\n[TOOL] Executing get_service_details...")

    service_id = state["selected_service_id"]

    details = get_service_details(service_id)

    tools_used = state.get("tools_used", []) + [
        "get_service_details"
    ]

    if "error" in details:

        return {
            "service_details": {},
            "next_action": "fallback",
            "tools_used": tools_used
        }

    print(f"[TOOL] Retrieved: {details['name']}")

    return {
        "service_details": details,
        "tools_used": tools_used,
        "agent_steps": state.get("agent_steps", []) + [
            "Retrieved detailed government service information"
        ]
    }


# ==========================================
# 7. GENERATE CITIZEN GUIDANCE
# ==========================================




def generate_guidance(state: AgentState):

    print("\n[LLM] Generating citizen service guidance...")

    service = state.get("service_details", {})
    original_query = state.get("original_query", "")

    # ==========================================
    # 1. RETRIEVE FEEDBACK-BASED ADAPTATION
    # ==========================================

    print("\n[ADAPTATION] Analysing citizen feedback...")

    try:
        adaptation = get_adaptation_guidance()

        adaptation_active = adaptation.get(
            "adaptation_active", False
        )

        adaptation_instruction = adaptation.get(
            "guidance",
            "Provide clear and accurate guidance."
        )

        if adaptation_active:
            print("[ADAPTATION] Feedback-based adaptation is active.")
            print("[ADAPTATION] Guidance:", adaptation_instruction)

        else:
            print("[ADAPTATION] Not enough feedback for adaptation.")
            print("[ADAPTATION] Reason:", adaptation.get("reason"))

    except Exception as error:

        print("[ADAPTATION ERROR]", error)

        adaptation_active = False

        adaptation_instruction = (
            "Provide clear, simple and accurate guidance."
        )

    # ==========================================
    # 2. DEFINE LLM INSTRUCTIONS
    # ==========================================

    system_prompt = f"""
You are the response-generation component of the
Bhutan Citizen Service Guidance Agent.

Your responsibility is to provide helpful and accurate
government service guidance to citizens.

IMPORTANT ACCURACY AND SAFETY RULES:

1. Use only the supplied government service information.
2. Never invent documents, fees, eligibility rules,
   deadlines, procedures or contact information.
3. If requested information is missing, clearly state
   that it is not available in the knowledge base.
4. Answer the citizen's actual question.
5. Use simple and understandable English.
6. Organize answers with headings and bullet points.
7. Include the official source URL when available.
8. Recommend verifying current requirements with the
   relevant government authority.

FEEDBACK-BASED ADAPTATION:

The following instructions are generated from previous
citizen feedback:

{adaptation_instruction}

Apply these instructions to improve the clarity,
detail and usefulness of your response.

IMPORTANT:
Feedback-based instructions must never override the
accuracy and safety rules above.
Never add unsupported government information merely
to make an answer more detailed.
"""

    # ==========================================
    # 3. PREPARE CITIZEN QUESTION AND SERVICE DATA
    # ==========================================

    user_prompt = f"""
Citizen's question:

{original_query}

Retrieved government service information:

{json.dumps(service, indent=2, ensure_ascii=False)}

Prepare a helpful and accurate response using the
provided service information and adaptation guidance.
"""

    # ==========================================
    # 4. GENERATE RESPONSE
    # ==========================================

    try:

        response = generate_llm_response(
            system_prompt,
            user_prompt
        )

        if not validate_output(response):
            raise ValueError("The LLM returned an invalid response.")

        if not response:
            raise ValueError("The LLM returned an empty response.")

        source_url = service.get("source_url")

        if source_url and source_url not in response:

            response += (
                "\n\nOfficial information source: "
                + source_url
            )

        response += (
            "\n\nPlease verify current requirements with "
            "the relevant government authority before "
            "taking action."
        )

        print("[LLM] Response generated successfully.")

        return {
            "response": response,
            "agent_steps": state.get("agent_steps", []) + [
                "Retrieved previous citizen feedback",
                "Applied feedback-based response adaptation"
                if adaptation_active
                else "Generated response using default instructions",
                "Generated guidance using LLM reasoning"
            ]
        }

    except Exception as error:

        print("[LLM ERROR]", error)

        source_url = service.get(
            "source_url",
            "https://www.citizenservices.gov.bt/"
        )

        return {
            "response": safe_fallback_response(),
            "agent_steps": state.get("agent_steps", []) + [
                "LLM response validation failed; used safe fallback"
                ]
        }


# ==========================================
# 8. HANDLE UNKNOWN REQUESTS
# ==========================================


def fallback_response(state: AgentState):

    print("\n[AGENT] Executing fallback response...")

    input_error = state.get("input_error", "")

    if input_error:

        response = input_error

        print("[SAFETY] Returning input validation message.")

    else:

        response = safe_fallback_response()

        print("[AGENT] Asking citizen for clarification.")

    return {
        "response": response,
        "agent_steps": state.get("agent_steps", []) + [
            "Returned a safe fallback response"
        ]
    }


# ==========================================
# 9. BUILD LANGGRAPH WORKFLOW
# ==========================================



def route_after_understanding(state: AgentState):

    if state.get("input_error"):
        return "fallback"

    return "continue"


def build_agent():

    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node(
        "understand_request",
        understand_request
    )

    workflow.add_node(
        "llm_reasoning",
        llm_reasoning_node
    )

    workflow.add_node(
        "search_services",
        search_services_node
    )

    workflow.add_node(
        "plan_next_action",
        plan_next_action
    )

    workflow.add_node(
        "retrieve_service",
        retrieve_service
    )

    workflow.add_node(
        "generate_guidance",
        generate_guidance
    )

    workflow.add_node(
        "fallback_response",
        fallback_response
    )

    # Initial connection
    workflow.add_edge(
        START,
        "understand_request"
    )

    # Validate input before LLM reasoning
    workflow.add_conditional_edges(
        "understand_request",
        route_after_understanding,
        {
            "continue": "llm_reasoning",
            "fallback": "fallback_response"
        }
    )

    # LLM and retrieval workflow
    workflow.add_edge(
        "llm_reasoning",
        "search_services"
    )

    workflow.add_edge(
        "search_services",
        "plan_next_action"
    )

    # Decide whether to retrieve or fallback
    workflow.add_conditional_edges(
        "plan_next_action",
        route_agent,
        {
            "retrieve": "retrieve_service",
            "fallback": "fallback_response"
        }
    )

    # Generate final guidance
    workflow.add_edge(
        "retrieve_service",
        "generate_guidance"
    )

    workflow.add_edge(
        "generate_guidance",
        END
    )

    workflow.add_edge(
        "fallback_response",
        END
    )

    return workflow.compile()


# ==========================================
# 10. RUN THE AGENT
# ==========================================


def run_agent(query: str, session_id="cli-session"):

    # Initialize database
    init_db()

    # Retrieve recent conversations
    recent_history = get_recent_interactions(
        session_id=session_id,
        limit=5
    )

    print("\n[MEMORY] Retrieved previous interactions:",
          len(recent_history))

    agent = build_agent()

    initial_state = {
        "query": query,
        "original_query": query,
        "session_id": session_id,
        "recent_history": recent_history,
        "search_results": [],
        "tools_used": [],
        "agent_steps": [],
        "input_error": ""
    }

    # Execute agent workflow
    result = agent.invoke(initial_state)

    # Store completed interaction
    response = result.get("response", "")

    interaction_id = save_interaction(
        session_id=session_id,
        query=query,
        response=response,
        tools_used=result.get("tools_used", [])
    )

    result["interaction_id"] = interaction_id

    print("\n[MEMORY] Interaction saved:", interaction_id)

    return result



# ==========================================
# 11. TEST THE AGENT
# ==========================================


if __name__ == "__main__":

    print("=" * 50)
    print("BHUTAN CITIZEN SERVICE GUIDANCE AGENT")
    print("=" * 50)

    init_db()

    user_query = input(
        "\nEnter your government service question: "
    )

    result = run_agent(user_query)

    print("\n" + "=" * 50)
    print("FINAL AGENT RESPONSE")
    print("=" * 50)

    print(result.get("response", ""))

    print("\nTOOLS USED:")
    print(result.get("tools_used", []))

    print("\nAGENT DECISION STEPS:")

    for step in result.get("agent_steps", []):
        print("-", step)

    # Collect citizen feedback
    print("\n" + "=" * 50)
    print("CITIZEN FEEDBACK")
    print("=" * 50)

    print("Rate the response from 1 to 5.")

    try:

        rating = int(input("Your rating: "))

        comment = input(
            "Additional feedback (optional): "
        )

        save_feedback(
            interaction_id=result["interaction_id"],
            rating=rating,
            comment=comment
        )

        print("\nThank you for your feedback!")

    except ValueError:

        print("\nInvalid rating. Please enter a number from 1 to 5.")
