
from memory.database import (
    init_db,
    save_interaction,
    save_feedback,
    get_recent_interactions,
    get_feedback_summary
)


def test_memory_system():

    print("TESTING MEMORY SYSTEM")
    print("=" * 40)

    init_db()

    # Test 1: Save interaction
    interaction_id = save_interaction(
        session_id="evaluation_session",
        query="I want to apply for a passport",
        response="Passport application guidance.",
        tools_used=["search_services"]
    )

    assert interaction_id > 0

    print("Test 1: Save interaction - PASSED")

    # Test 2: Retrieve interaction
    history = get_recent_interactions(
        "evaluation_session"
    )

    assert len(history) > 0

    print("Test 2: Retrieve memory - PASSED")

    # Test 3: Save feedback
    save_feedback(
        interaction_id=interaction_id,
        rating=5,
        comment="Very helpful."
    )

    print("Test 3: Save feedback - PASSED")

    # Test 4: Feedback statistics
    summary = get_feedback_summary()

    assert summary["total_feedback"] > 0

    print("Test 4: Feedback statistics - PASSED")

    print("\nALL MEMORY TESTS PASSED!")


if __name__ == "__main__":

    test_memory_system()
