
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Locate the government service dataset
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "services.json"


def load_services():
    """Load government services from the JSON knowledge base."""

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"Knowledge base error: {error}")
        return []


def search_services(query, top_k=3):
    """
    Tool 1:
    Search government services using TF-IDF similarity.
    """

    services = load_services()

    if not services:
        return []

    documents = []

    for service in services:
        text = (
            service["name"] + " " +
            service["category"] + " " +
            service["description"] + " " +
            " ".join(service["keywords"])
        )

        documents.append(text)

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english"
    )

    service_vectors = vectorizer.fit_transform(documents)
    query_vector = vectorizer.transform([query])

    similarities = cosine_similarity(
        query_vector,
        service_vectors
    ).flatten()

    ranked_indices = similarities.argsort()[::-1]

    results = []

    for index in ranked_indices[:top_k]:

        score = float(similarities[index])

        if score > 0:

            results.append({
                "id": services[index]["id"],
                "name": services[index]["name"],
                "category": services[index]["category"],
                "similarity_score": round(score, 3)
            })

    return results


def get_service_details(service_id):
    """
    Tool 2:
    Retrieve complete details of a government service.
    """

    services = load_services()

    for service in services:

        if service["id"] == service_id:
            return service

    return {
        "error": "Service not found."
    }


# Test the tools independently
if __name__ == "__main__":

    print("\nSearching for passport services...")

    results = search_services("I want to apply for a passport")

    print(results)

    if results:

        print("\nRetrieving service details...")

        details = get_service_details(results[0]["id"])

        print(json.dumps(details, indent=4))
