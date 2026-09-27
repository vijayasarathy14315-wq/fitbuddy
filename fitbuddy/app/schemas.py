from pydantic import BaseModel, Field, field_validator


ALLOWED_GOALS = {
    "weight loss",
    "muscle gain",
    "general wellness",
    "flexibility",
    "endurance",
}


ALLOWED_INTENSITIES = {
    "low",
    "medium",
    "high",
}


ALLOWED_EXPERIENCE = {
    "beginner",
    "intermediate",
    "advanced",
}


class UserInput(BaseModel):

    user_id: str = Field(
        min_length=2,
        max_length=80,
    )

    name: str = Field(
        min_length=1,
        max_length=120,
    )

    age: int = Field(
        ge=13,
        le=100,
    )

    weight: float = Field(
        gt=20,
        lt=400,
    )

    goal: str = Field(
        min_length=2,
        max_length=80,
    )

    intensity: str = Field(
        min_length=3,
        max_length=20,
    )

    experience_level: str = Field(
        default="beginner",
        max_length=40,
    )

    @field_validator(
        "user_id",
        "name",
        "goal",
        "intensity",
        "experience_level",
    )
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()

    @field_validator("goal")
    @classmethod
    def valid_goal(cls, value: str) -> str:
        normalized = value.lower()

        if normalized not in ALLOWED_GOALS:
            raise ValueError(
                "Goal must be one of: "
                + ", ".join(sorted(ALLOWED_GOALS))
            )

        return normalized

    @field_validator("intensity")
    @classmethod
    def valid_intensity(cls, value: str) -> str:
        normalized = value.lower()

        if normalized not in ALLOWED_INTENSITIES:
            raise ValueError(
                "Intensity must be low, medium, or high"
            )

        return normalized

    @field_validator("experience_level")
    @classmethod
    def valid_experience(cls, value: str) -> str:
        normalized = value.lower()

        if normalized not in ALLOWED_EXPERIENCE:
            raise ValueError(
                "Experience must be beginner, intermediate, or advanced"
            )

        return normalized


class FeedbackRequest(BaseModel):

    user_id: str = Field(
        min_length=2,
        max_length=80,
    )

    feedback: str = Field(
        min_length=3,
        max_length=1200,
    )

    @field_validator("user_id", "feedback")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()


class PlanResponse(BaseModel):

    user_id: str
    name: str
    goal: str
    intensity: str
    experience_level: str
    workout_plan: str
    nutrition_tip: str