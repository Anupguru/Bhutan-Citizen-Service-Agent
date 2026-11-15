
# ==========================================
# BHUTAN CITIZEN SERVICE AGENT
# SAFETY AND GUARDRAILS
# ==========================================

MAX_QUERY_LENGTH = 500

# Topics outside the current agent's purpose
OUT_OF_SCOPE_TOPICS = [
    "weather",
    "football",
    "cricket",
    "movie",
    "music",
    "stock market",
    "cryptocurrency",
    "recipe",
    "dating",
    "video game"
]


# ==========================================
# 1. INPUT VALIDATION
# ==========================================

def validate_input(query):

    if not isinstance(query, str):
        return False, "Please enter a valid text question."

    query = query.strip()

    if not query:
        return False, "Please enter a question."

    if len(query) > MAX_QUERY_LENGTH:
        return False, (
            "Your question is too long. "
            "Please keep it within 500 characters."
        )

    return True, ""


# ==========================================
# 2. SCOPE VALIDATION
# ==========================================

def check_scope(query):

    normalized_query = query.lower()

    for topic in OUT_OF_SCOPE_TOPICS:

        if topic in normalized_query:

            return False, (
                "I am designed to provide guidance about "
                "government services in Bhutan. "
                "Please ask me about a relevant government service."
            )

    return True, ""


# ==========================================
# 3. RETRIEVAL CONFIDENCE CHECK
# ==========================================

def check_retrieval_confidence(
    search_results,
    threshold=0.25
):

    if not search_results:
        return False

    best_result = search_results[0]

    score = float(
        best_result.get("similarity_score", 0)
    )

    return score >= threshold


# ==========================================
# 4. SAFE FALLBACK RESPONSE
# ==========================================

def safe_fallback_response():

    return (
        "I could not confidently identify the government "
        "service related to your question.\n\n"
        "Please provide more details about the service "
        "you are looking for.\n\n"
        "You can also consult the official Bhutan Citizen "
        "Services portal:\n"
        "https://www.citizenservices.gov.bt/"
    )


# ==========================================
# 5. OUTPUT VALIDATION
# ==========================================

def validate_output(response):

    if not isinstance(response, str):
        return False

    if not response.strip():
        return False

    return True
