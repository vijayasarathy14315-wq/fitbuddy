import json
import re
from functools import lru_cache

from .config import get_settings


class AIServiceError(RuntimeError):
    pass


@lru_cache
def get_client():

    settings = get_settings()

    if not settings.gemini_api_key:
        return None

    try:
        from google import genai

        return genai.Client(
            api_key=settings.gemini_api_key
        )

    except Exception as exc:
        raise AIServiceError(
            f"Could not initialize Gemini client: {exc}"
        ) from exc


def _clean_text(text: str) -> str:

    text = (text or "").strip()

    text = re.sub(
        r"^```(?:json|text)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    return text.strip()


def _generate(
    model: str,
    prompt: str,
    *,
    temperature: float = 0.6,
    json_output: bool = False,
) -> str:

    settings = get_settings()

    if settings.allow_mock_ai:
        return mock_response(prompt)

    client = get_client()

    # Local development without API key.
    if client is None:

        raise AIServiceError(
            "GEMINI_API_KEY is not configured."
        )

    try:

        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=7000,
        )

        if json_output:
            config.response_mime_type = "application/json"

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        text = _clean_text(
            response.text
        )

        if not text:
            raise AIServiceError(
                "Gemini returned an empty response."
            )

        return text

    except AIServiceError:
        raise

    except Exception as exc:

        raise AIServiceError(
            f"Gemini request failed: {exc}"
        ) from exc


def _profile(user) -> str:

    return (
        f"Name: {user.name}\n"
        f"Age: {user.age}\n"
        f"Weight: {user.weight} kg\n"
        f"Goal: {user.goal}\n"
        f"Intensity: {user.intensity}\n"
        f"Experience: {user.experience_level}"
    )


def generate_workout_gemini(user) -> str:

    settings = get_settings()

    prompt = f"""
You are FitBuddy, a cautious fitness-planning assistant.

Create a safe, practical 7-day fitness plan for this user.

USER PROFILE:
{_profile(user)}

Return ONLY valid JSON.

The JSON must have exactly these keys:

{{
  "overview": "short overview",
  "days": [
    {{
      "day": "Day 1",
      "focus": "workout focus",
      "warm_up": "warm-up instructions",
      "main_workout": [
        "exercise details",
        "exercise details"
      ],
      "cool_down": "cool-down instructions",
      "notes": "helpful notes"
    }}
  ]
}}

The days array MUST contain exactly 7 days.

Requirements:

- Adapt difficulty to intensity.
- Adapt exercises to experience level.
- Include warm-up.
- Include the main workout.
- Include cool-down/recovery.
- Include rest or recovery where appropriate.
- Use accessible exercises.
- Give exercise alternatives when useful.
- Do not prescribe starvation.
- Do not prescribe dehydration.
- Do not suggest dangerous challenges.
- Do not provide medical treatment.
- Do not diagnose medical conditions.
- If injury or medical conditions are mentioned, recommend professional guidance.
- Keep the output practical and easy to follow.
"""

    return _generate(
        settings.workout_model,
        prompt,
        temperature=0.55,
        json_output=True,
    )


def generate_nutrition_tip_with_flash(user) -> str:

    settings = get_settings()

    prompt = f"""
You are FitBuddy's nutrition and recovery assistant.

Give ONE concise general wellness tip for this user.

USER PROFILE:
{_profile(user)}

The answer must be 80 words or fewer.

Focus on:

- balanced meals
- hydration
- sleep
- recovery
- sensible protein/fiber sources

depending on the user's goal.

Do not prescribe:

- restrictive dieting
- starvation
- calorie targets
- supplements
- medical treatment
"""

    return _generate(
        settings.nutrition_model,
        prompt,
        temperature=0.4,
    )


def update_workout_plan(
    user,
    original_plan: str,
    feedback: str,
) -> str:

    settings = get_settings()

    prompt = f"""
You are FitBuddy.

Revise the existing 7-day workout plan according to the
user's feedback.

USER:
{_profile(user)}

ORIGINAL PLAN:
{original_plan}

USER FEEDBACK:
{feedback}

Return ONLY valid JSON.

Use exactly this structure:

{{
  "overview": "short overview",
  "days": [
    {{
      "day": "Day 1",
      "focus": "workout focus",
      "warm_up": "warm-up",
      "main_workout": [
        "exercise"
      ],
      "cool_down": "cool-down",
      "notes": "notes"
    }}
  ]
}}

The days array must contain exactly 7 days.

Preserve useful parts of the original plan.

Incorporate reasonable user feedback.

Keep the plan safe.

Do not create:

- extreme exercise
- dangerous challenges
- starvation
- dehydration
- medical treatment
"""

    return _generate(
        settings.workout_model,
        prompt,
        temperature=0.55,
        json_output=True,
    )


def pretty_plan(plan_text: str) -> str:

    try:

        data = json.loads(plan_text)

        lines = []

        lines.append(
            data.get(
                "overview",
                "Personalized 7-day plan",
            )
        )

        lines.append("")

        for day in data.get("days", []):

            lines.append(
                f"{day.get('day', '')} — "
                f"{day.get('focus', '')}"
            )

            lines.append(
                f"Warm-up: {day.get('warm_up', '')}"
            )

            lines.append(
                "Main workout:"
            )

            for item in day.get(
                "main_workout",
                [],
            ):

                lines.append(
                    f"• {item}"
                )

            lines.append(
                f"Cooldown: "
                f"{day.get('cool_down', '')}"
            )

            if day.get("notes"):

                lines.append(
                    f"Notes: {day['notes']}"
                )

            lines.append("")

        return "\n".join(lines).strip()

    except (
        json.JSONDecodeError,
        TypeError,
    ):

        return plan_text


def mock_response(prompt: str) -> str:

    normalized_prompt = (prompt or "").lower()

    if (
        "days array must contain exactly 7 objects" in normalized_prompt
        or "days array must contain exactly 7 days" in normalized_prompt
        or "exactly 7 days" in normalized_prompt
    ):

        days = []

        for i in range(1, 8):

            if i in (1, 5):

                focus = "Full-body mobility"

            elif i == 7:

                focus = "Recovery / rest"

            else:

                focus = "Moderate full-body strength"

            days.append(
                {
                    "day": f"Day {i}",
                    "focus": focus,
                    "warm_up": (
                        "5–10 minutes of easy movement "
                        "and dynamic mobility."
                    ),
                    "main_workout": [
                        "Bodyweight squats: 2–3 sets of 8–12",
                        "Incline push-ups: 2–3 sets of 6–12",
                        "Easy walking: 10–20 minutes",
                    ],
                    "cool_down": (
                        "5 minutes of gentle walking "
                        "and relaxed stretching."
                    ),
                    "notes": (
                        "Adjust range and repetitions to "
                        "a comfortable level. Stop if you "
                        "feel pain or become unwell."
                    ),
                }
            )

        return json.dumps(
            {
                "overview": (
                    "Demo plan generated locally "
                    "because Gemini is not configured."
                ),
                "days": days,
            }
        )

    return (
        "Demo nutrition/recovery tip: Build balanced "
        "meals, drink water regularly, and prioritize "
        "adequate sleep and recovery."
    )