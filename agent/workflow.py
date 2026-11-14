
from typing import TypedDict, Optional, Any

from langgraph.graph import StateGraph, START, END

from tools.service_tools import (
    search_services,
    get_service_details
)


from memory.database import (
    init_db,
    save_interaction,
    get_recent_interactions,
    save_feedback
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

    agent_steps: list


# ==========================================
# 2. UNDERSTAND CITIZEN REQUEST
# ==========================================



def understand_request(state: AgentState):
    print("\n[AGENT] Understanding citizen request...")

    current_query = state.get("original_query", state.get("query", "")).strip()
    history = state.get("recent_history", [])

    if not current_query:
        return {
            "response": "Please enter a government service question.",
            "next_action": "stop"
        }

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
        # Find the most recent previous citizen request
        previous_query = ""
        for interaction in history:
            old_query = interaction.get("query", "").strip().lower()
            if any(
                word in old_query
                for word in ["passport", "birth", "death", "driving licence"]
                ):
                previous_query = interaction.get("query", "").strip()
                break

        if previous_query:
            combined_query = previous_query + " " + current_query

            print("[MEMORY] Previous conversation found.")
            print("[MEMORY] Previous request:", previous_query)
            print("[MEMORY] Follow-up request:", current_query)

    print("[AGENT] Processing:", combined_query)

    return {
        "query": combined_query,
        "original_query": current_query,
        "agent_steps": state.get("agent_steps", []) +
                       ["Understood citizen request",
                        "Checked recent conversation memory"]
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
    original_query = state.get("original_query", "").lower()

    response = f"""
BHUTAN CITIZEN SERVICE GUIDANCE
================================

Service: {service.get('name', 'Unknown')}
Category: {service.get('category', 'Unknown')}

"""

    if "document" in original_query:
        documents = service.get("documents_required", [])

        response += "DOCUMENTS REQUIRED:\n"

        if documents:
            for index, document in enumerate(documents, 1):
                response += f"{index}. {document}\n"
        else:
            response += (
                "The document checklist is not available "
                "in the knowledge base. Please consult the "
                "official government source.\n"
            )

        response += "\n"

    elif "photo" in original_query or "photograph" in original_query:
        photo_requirements = service.get("photo_requirements", [])

        response += "PHOTOGRAPH REQUIREMENTS:\n"

        if photo_requirements:
            for index, requirement in enumerate(photo_requirements, 1):
                response += f"{index}. {requirement}\n"
        else:
            response += "Please consult the official source for photograph requirements.\n"

        response += "\n"

    else:
        response += f"""
Description:
{service.get('description', 'Not available')}

Eligibility:
{service.get('eligibility', 'Please check the official source.')}

Application Procedure:
"""

        for index, step in enumerate(service.get("procedure", []), 1):
            response += f"{index}. {step}\n"

        response += "\n"

    if "child" in original_query or "minor" in original_query:
        child_requirements = service.get("child_requirements", [])

        if child_requirements:
            response += "ADDITIONAL REQUIREMENTS FOR CHILDREN:\n"
            for index, requirement in enumerate(child_requirements, 1):
                response += f"{index}. {requirement}\n"
            response += "\n"

    response += f"""
Official Website:
{service.get('official_website', 'Not available')}

Information Source:
{service.get('source', 'Not available')}

Source URL:
{service.get('source_url', 'Not available')}

Please verify the latest requirements with the
relevant government authority before applying.
"""

    print("[AGENT] Guidance generated successfully.")

    return {
        "response": response,
        "agent_steps": state.get("agent_steps", []) +
                       ["Generated citizen service guidance"]
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
        "agent_steps": []
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
