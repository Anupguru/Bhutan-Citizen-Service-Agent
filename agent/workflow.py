
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, START, END

from tools.service_tools import (
    search_services,
    get_service_details
)


# ==========================================
# 1. DEFINE AGENT STATE
# ==========================================

class AgentState(TypedDict, total=False):

    query: str
    search_results: list
    selected_service_id: Optional[int]
    service_details: dict
    response: str
    next_action: str
    tools_used: list
    agent_steps: list


# ==========================================
# 2. UNDERSTAND CITIZEN REQUEST
# ==========================================

def understand_request(state: AgentState):

    query = state.get("query", "").strip()

    print("\n[AGENT] Understanding citizen request...")

    if not query:

        return {
            "response": "Please enter a question about a Bhutan government service.",
            "next_action": "stop"
        }

    print(f"[AGENT] Citizen request: {query}")

    return {
        "query": query,
        "agent_steps": ["Understood citizen request"]
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

    results = state.get("search_results", [])

    if not results:

        print("[AGENT] No relevant service found.")

        return {
            "next_action": "fallback"
        }

    best_match = results[0]

    confidence = best_match["similarity_score"]

    print(f"[AGENT] Best match: {best_match['name']}")
    print(f"[AGENT] Similarity score: {confidence}")

    # Similarity threshold
    if confidence >= 0.05:

        print("[AGENT] Relevant service identified.")

        return {
            "selected_service_id": best_match["id"],
            "next_action": "retrieve"
        }

    print("[AGENT] Confidence too low. Asking for clarification.")

    return {
        "next_action": "fallback"
    }


# ==========================================
# 5. ROUTE AGENT TO THE NEXT ACTION
# ==========================================

def route_agent(state: AgentState):

    action = state.get("next_action")

    if action == "retrieve":
        return "retrieve_service"

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

    print("\n[AGENT] Generating citizen guidance...")

    service = state.get("service_details", {})

    if not service:

        return {
            "next_action": "fallback"
        }

    response = f"""
BHUTAN CITIZEN SERVICE GUIDANCE
================================

Service: {service['name']}

Category: {service['category']}

Description:
{service['description']}

Eligibility:
{service['eligibility']}

Application Procedure:
"""

    for number, step in enumerate(
        service["procedure"], start=1
    ):

        response += f"\n{number}. {step}"

    response += f"""

Important Information:
{service['important_note']}

Official Website:
{service['official_website']}

Information Source:
{service['source']}

Source URL:
{service['source_url']}

Last checked in project dataset:
{service['last_checked']}

Please verify current requirements with the relevant
government authority before submitting an application.
"""

    return {
        "response": response,
        "agent_steps": state.get("agent_steps", []) + [
            "Generated citizen service guidance"
        ]
    }


# ==========================================
# 8. HANDLE UNKNOWN REQUESTS
# ==========================================

def fallback_response(state: AgentState):

    print("\n[AGENT] Executing fallback response...")

    response = """
I could not confidently identify the government
service you are looking for.

Please provide more details about your request.

For example:
- I want to apply for a passport.
- I need to register a newborn baby.
- I want information about death registration.

You can also visit the official Bhutan G2C
Citizen Services Portal:

https://www.citizenservices.gov.bt/
"""

    return {
        "response": response,
        "agent_steps": state.get("agent_steps", []) + [
            "Requested clarification because no reliable service match was found"
        ]
    }


# ==========================================
# 9. BUILD LANGGRAPH WORKFLOW
# ==========================================

def build_agent():

    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node(
        "understand_request",
        understand_request
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
        "fallback",
        fallback_response
    )

    # Define workflow connections
    workflow.add_edge(
        START,
        "understand_request"
    )

    workflow.add_conditional_edges(
        "understand_request",
        lambda state: (
            "stop" if state.get("next_action") == "stop"
            else "search"
        ),
        {
            "stop": END,
            "search": "search_services"
        }
    )

    workflow.add_edge(
        "search_services",
        "plan_next_action"
    )

    workflow.add_conditional_edges(
        "plan_next_action",
        route_agent,
        {
            "retrieve_service": "retrieve_service",
            "fallback": "fallback"
        }
    )

    workflow.add_conditional_edges(
        "retrieve_service",
        lambda state: (
            "fallback"
            if not state.get("service_details")
            else "guidance"
        ),
        {
            "fallback": "fallback",
            "guidance": "generate_guidance"
        }
    )

    workflow.add_edge(
        "generate_guidance",
        END
    )

    workflow.add_edge(
        "fallback",
        END
    )

    # Compile the graph
    return workflow.compile()


# ==========================================
# 10. RUN THE AGENT
# ==========================================

def run_agent(query: str):

    agent = build_agent()

    initial_state = {
        "query": query,
        "search_results": [],
        "tools_used": [],
        "agent_steps": []
    }

    result = agent.invoke(initial_state)

    return result


# ==========================================
# 11. TEST THE AGENT
# ==========================================

if __name__ == "__main__":

    print("=" * 50)
    print("BHUTAN CITIZEN SERVICE GUIDANCE AGENT")
    print("=" * 50)

    user_query = input(
        "\nEnter your government service question: "
    )

    result = run_agent(user_query)

    print("\n" + "=" * 50)
    print("FINAL AGENT RESPONSE")
    print("=" * 50)

    print(result.get("response", "No response generated."))

    print("\nTOOLS USED:")
    print(result.get("tools_used", []))

    print("\nAGENT DECISION STEPS:")
    for step in result.get("agent_steps", []):
        print("-", step)
