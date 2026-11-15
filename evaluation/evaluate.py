
import sqlite3
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from tools.service_tools import search_services


# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "memory" / "agent_memory.db"

OUTPUT_DIR = BASE_DIR / "evaluation" / "results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SIMILARITY_THRESHOLD = 0.25


# ==========================================
# 2. EVALUATION TEST CASES
# ==========================================

TEST_CASES = [
    {
        "question": "How can I apply for a passport?",
        "expected_service": "Passport Application"
    },
    {
        "question": "I need to register the birth of my child.",
        "expected_service": "Birth and Death Registration"
    },
    {
        "question": "How do I register a death?",
        "expected_service": "Birth and Death Registration"
    },
    {
        "question": "What is the process for getting a passport?",
        "expected_service": "Passport Application"
    }
]


# ==========================================
# 3. TEST SERVICE RETRIEVAL
# ==========================================

def evaluate_retrieval():

    results = []

    print("\n========== RETRIEVAL EVALUATION ==========")

    for index, test in enumerate(TEST_CASES, start=1):

        question = test["question"]
        expected = test["expected_service"]

        search_results = search_services(
            query=question,
            top_k=1
        )

        if search_results:

            best_match = search_results[0]

            predicted = best_match.get("name", "Unknown")

            similarity = float(
                best_match.get("similarity_score", 0)
            )

        else:

            predicted = "No match"
            similarity = 0.0

        correct = (
            predicted.strip().lower()
            == expected.strip().lower()
        )

        covered = similarity >= SIMILARITY_THRESHOLD

        results.append({
            "test_number": index,
            "question": question,
            "expected_service": expected,
            "predicted_service": predicted,
            "similarity_score": similarity,
            "correct": correct,
            "above_threshold": covered
        })

        print(f"\nTest {index}")
        print("Question:", question)
        print("Expected:", expected)
        print("Predicted:", predicted)
        print("Similarity score:", round(similarity, 3))
        print("Correct retrieval:", correct)
        print("Above threshold:", covered)

    return pd.DataFrame(results)


# ==========================================
# 4. READ CITIZEN FEEDBACK FROM SQLITE
# ==========================================

def get_feedback_data():

    if not DB_PATH.exists():
        print("\n[WARNING] Database not found.")
        return pd.DataFrame(
            columns=["rating", "comment"]
        )

    try:

        connection = sqlite3.connect(DB_PATH)

        feedback_df = pd.read_sql_query(
            "SELECT * FROM feedback",
            connection
        )

        connection.close()

        if "rating" not in feedback_df.columns:
            return pd.DataFrame(
                columns=["rating", "comment"]
            )

        if "comment" not in feedback_df.columns:
            feedback_df["comment"] = ""

        feedback_df["rating"] = pd.to_numeric(
            feedback_df["rating"],
            errors="coerce"
        )

        feedback_df = feedback_df.dropna(
            subset=["rating"]
        )

        return feedback_df

    except Exception as error:

        print("[FEEDBACK ERROR]", error)

        return pd.DataFrame(
            columns=["rating", "comment"]
        )


# ==========================================
# 5. CALCULATE EVALUATION METRICS
# ==========================================

def calculate_metrics(retrieval_df, feedback_df):

    total_tests = len(retrieval_df)

    correct_retrievals = int(
        retrieval_df["correct"].sum()
    )

    covered_questions = int(
        retrieval_df["above_threshold"].sum()
    )

    retrieval_accuracy = (
        correct_retrievals / total_tests * 100
        if total_tests else 0
    )

    retrieval_coverage = (
        covered_questions / total_tests * 100
        if total_tests else 0
    )

    total_feedback = len(feedback_df)

    average_rating = (
        feedback_df["rating"].mean()
        if total_feedback else 0
    )

    positive_feedback = (
        int((feedback_df["rating"] >= 4).sum())
        if total_feedback else 0
    )

    neutral_feedback = (
        int((feedback_df["rating"] == 3).sum())
        if total_feedback else 0
    )

    negative_feedback = (
        int((feedback_df["rating"] <= 2).sum())
        if total_feedback else 0
    )

    metrics = {
        "total_test_questions": total_tests,
        "correct_retrievals": correct_retrievals,
        "retrieval_accuracy_percent": round(
            retrieval_accuracy, 2
        ),
        "questions_above_threshold": covered_questions,
        "retrieval_coverage_percent": round(
            retrieval_coverage, 2
        ),
        "total_citizen_feedback": total_feedback,
        "average_rating": round(
            float(average_rating), 2
        ),
        "positive_feedback": positive_feedback,
        "neutral_feedback": neutral_feedback,
        "negative_feedback": negative_feedback
    }

    return metrics


# ==========================================
# 6. VISUALIZE RETRIEVAL RESULTS
# ==========================================

def plot_retrieval_results(retrieval_df):

    correct = int(retrieval_df["correct"].sum())

    incorrect = len(retrieval_df) - correct

    plt.figure(figsize=(7, 5))

    plt.bar(
        ["Correct", "Incorrect"],
        [correct, incorrect]
    )

    plt.title("Government Service Retrieval Results")
    plt.xlabel("Retrieval Outcome")
    plt.ylabel("Number of Questions")

    plt.tight_layout()

    output_path = OUTPUT_DIR / "retrieval_results.png"

    plt.savefig(output_path, dpi=300)

    plt.close()

    print("\nSaved:", output_path)


# ==========================================
# 7. VISUALIZE CITIZEN FEEDBACK
# ==========================================

def plot_feedback_results(feedback_df):

    if feedback_df.empty:

        print(
            "\n[INFO] No citizen feedback available "
            "for the feedback chart."
        )

        return

    rating_counts = (
        feedback_df["rating"]
        .value_counts()
        .reindex([1, 2, 3, 4, 5], fill_value=0)
    )

    plt.figure(figsize=(7, 5))

    plt.bar(
        rating_counts.index.astype(str),
        rating_counts.values
    )

    plt.title("Citizen Feedback Rating Distribution")
    plt.xlabel("Rating (1 = Very Poor, 5 = Excellent)")
    plt.ylabel("Number of Responses")

    plt.tight_layout()

    output_path = OUTPUT_DIR / "feedback_ratings.png"

    plt.savefig(output_path, dpi=300)

    plt.close()

    print("Saved:", output_path)


# ==========================================
# 8. SAVE EVALUATION RESULTS
# ==========================================

def save_results(retrieval_df, metrics):

    retrieval_path = OUTPUT_DIR / "retrieval_evaluation.csv"

    retrieval_df.to_csv(
        retrieval_path,
        index=False
    )

    metrics_df = pd.DataFrame(
        list(metrics.items()),
        columns=["Metric", "Value"]
    )

    metrics_path = OUTPUT_DIR / "evaluation_metrics.csv"

    metrics_df.to_csv(
        metrics_path,
        index=False
    )

    print("\nSaved:", retrieval_path)
    print("Saved:", metrics_path)


# ==========================================
# 9. MAIN EVALUATION FUNCTION
# ==========================================

def main():

    print("\n")
    print("=" * 50)
    print("BHUTAN CITIZEN SERVICE AGENT")
    print("EVALUATION AND VISUALIZATION")
    print("=" * 50)

    # Test retrieval
    retrieval_df = evaluate_retrieval()

    # Read feedback
    feedback_df = get_feedback_data()

    # Calculate metrics
    metrics = calculate_metrics(
        retrieval_df,
        feedback_df
    )

    # Display metrics
    print("\n========== EVALUATION SUMMARY ==========")

    for metric, value in metrics.items():

        print(f"{metric}: {value}")

    # Generate graphs
    plot_retrieval_results(retrieval_df)

    plot_feedback_results(feedback_df)

    # Save results
    save_results(
        retrieval_df,
        metrics
    )

    print("\nEvaluation completed successfully!")


if __name__ == "__main__":
    main()
