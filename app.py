
import streamlit as st
import uuid

st.write("DEPLOYMENT TEST: Latest app.py is running.")

from agent.workflow import run_agent
from memory.database import init_db, save_feedback


# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Bhutan Citizen Service Guidance Agent",
    page_icon="🇧🇹",
    layout="centered"
)


# ==========================================
# 2. INITIALIZE DATABASE
# ==========================================

init_db()


# ==========================================
# 3. SESSION STATE
# ==========================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_interaction_id" not in st.session_state:
    st.session_state.last_interaction_id = None

if "feedback_submitted_for" not in st.session_state:
    st.session_state.feedback_submitted_for = None


# ==========================================
# 4. APPLICATION HEADER
# ==========================================

st.title("🇧🇹 Bhutan Citizen Service Guidance Agent")

st.write(
    "Welcome! I can help you find guidance about "
    "government services in Bhutan."
)

st.info(
    "Ask a question about a government service, "
    "such as passport applications or birth and "
    "death registration."
)


# ==========================================
# 5. SIDEBAR
# ==========================================

with st.sidebar:
    st.header("About the Agent")

    st.write(
        "This AI agent helps citizens understand "
        "government services by searching its "
        "knowledge base and generating guidance."
    )

    st.divider()

    st.subheader("Example Questions")

    st.write("• How can I apply for a passport?")
    st.write("• What is birth registration?")
    st.write("• Where can I find government service information?")

    st.divider()

    st.caption("Conversation session")

    if st.button("Start New Conversation", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.last_interaction_id = None
        st.session_state.feedback_submitted_for = None
        st.rerun()


# ==========================================
# 6. DISPLAY CONVERSATION HISTORY
# ==========================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ==========================================
# 7. CITIZEN QUESTION INPUT
# ==========================================

user_query = st.chat_input(
    "Ask about a Bhutan government service..."
)


# ==========================================
# 8. EXECUTE THE AI AGENT
# ==========================================

if user_query:

    # Display citizen's question
    st.session_state.messages.append({
        "role": "user",
        "content": user_query
    })

    with st.chat_message("user"):
        st.markdown(user_query)

    # Generate agent response
    with st.chat_message("assistant"):

        with st.spinner("Processing your question..."):

            try:
                result = run_agent(
                    query=user_query,
                    session_id=st.session_state.session_id
                )

                response = result.get(
                    "response",
                    "Sorry, I could not generate a response."
                )

                st.write("DEBUG - Result keys:", list(result.keys()))
                st.write("DEBUG - Response:", repr(response))
                st.write("DEBUG - Agent steps:", result.get("agent_steps", []))

                interaction_id = result.get("interaction_id")

                st.markdown(response)

                # Save interaction information for feedback
                st.session_state.last_interaction_id = interaction_id
                st.session_state.feedback_submitted_for = None

                # Display agent workflow information
                with st.expander("How the agent processed your question"):
                    st.write("**Agent steps:**")

                    for step in result.get("agent_steps", []):
                        st.write(f"- {step}")

                    st.write("**Tools used:**")

                    tools_used = result.get("tools_used", [])

                    if tools_used:
                        for tool in tools_used:
                            st.write(f"- {tool}")
                    else:
                        st.write("No tools were recorded.")

                # Store response in chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })

            except Exception as error:
                error_message = (
                    "Something went wrong while processing "
                    "your question. Please try again."
                )

                st.error(error_message)
                st.exception(error)


# ==========================================
# 9. CITIZEN FEEDBACK
# ==========================================

interaction_id = st.session_state.last_interaction_id

if (
    interaction_id is not None
    and st.session_state.feedback_submitted_for != interaction_id
):

    st.divider()
    st.subheader("Rate the Agent's Response")

    st.write(
        "Your feedback helps improve the quality "
        "of the guidance provided."
    )

    with st.form(key=f"feedback_form_{interaction_id}"):

        rating = st.select_slider(
            "How would you rate this response?",
            options=[1, 2, 3, 4, 5],
            value=5,
            format_func=lambda value: {
                1: "1 - Very poor",
                2: "2 - Poor",
                3: "3 - Average",
                4: "4 - Good",
                5: "5 - Excellent"
            }[value]
        )

        comment = st.text_area(
            "Additional comments (optional)",
            placeholder="Tell us how the response could be improved..."
        )

        submitted = st.form_submit_button(
            "Submit Feedback",
            use_container_width=True
        )

        if submitted:

            try:
                save_feedback(
                    interaction_id=interaction_id,
                    rating=rating,
                    comment=comment
                )

                st.session_state.feedback_submitted_for = interaction_id

                st.success(
                    "Thank you! Your feedback has been recorded."
                )

                st.rerun()

            except Exception as error:
                st.error("Unable to save your feedback.")
                st.exception(error)


# ==========================================
# 10. FOOTER
# ==========================================

st.divider()

st.caption(
    "Bhutan Citizen Service Guidance Agent | "
    "DAT404 Custom AI Agent Project"
)

st.caption(
    "Please verify important government service "
    "requirements with the relevant official authority."
)
