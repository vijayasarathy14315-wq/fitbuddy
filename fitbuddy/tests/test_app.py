import os


# Test database
os.environ["DATABASE_URL"] = (
    "sqlite:///./test_fitbuddy.db"
)

# Use mock AI during tests
os.environ["ALLOW_MOCK_AI"] = "true"


from fastapi.testclient import TestClient

from app.main import app

from app.database import init_db


init_db()


client = TestClient(app)


def test_home():

    response = client.get("/")

    assert response.status_code == 200

    assert "FitBuddy" in response.text


def test_health():

    response = client.get(
        "/api/v1/health"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"


def test_create_plan_with_mock_ai():

    payload = {
        "user_id": "TEST001",
        "name": "Test User",
        "age": 20,
        "weight": 65,
        "goal": "general wellness",
        "intensity": "low",
        "experience_level": "beginner",
    }

    response = client.post(
        "/api/v1/plans",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == "TEST001"

    assert "Day 1" in data["workout_plan"]

    assert data["nutrition_tip"]


def test_get_plan():

    response = client.get(
        "/api/v1/plans/TEST001"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user"]["user_id"] == "TEST001"


def test_feedback_with_mock_ai():

    payload = {
        "user_id": "TEST001",
        "feedback": (
            "Please make it easier "
            "and add more recovery."
        ),
    }

    response = client.post(
        "/api/v1/plans/TEST001/feedback",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert "Day 7" in data["workout_plan"]