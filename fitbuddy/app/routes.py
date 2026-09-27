import secrets

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)

from fastapi.responses import HTMLResponse

from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
)

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from .ai_service import (
    AIServiceError,
    generate_nutrition_tip_with_flash,
    generate_workout_gemini,
    pretty_plan,
    update_workout_plan,
)

from .config import (
    BASE_DIR,
    get_settings,
)

from .database import (
    get_current_plan,
    get_db,
    get_user,
    get_all_users,
    save_plan,
    save_user,
    update_plan,
)

from .schemas import (
    FeedbackRequest,
    PlanResponse,
    UserInput,
)


templates = Jinja2Templates(
    directory=str(
        BASE_DIR / "templates"
    )
)


router = APIRouter()

security = HTTPBasic()


def admin_guard(
    credentials: HTTPBasicCredentials = Depends(security),
):
    settings = get_settings()

    valid_username = secrets.compare_digest(
        credentials.username,
        settings.admin_username,
    )

    valid_password = secrets.compare_digest(
        credentials.password,
        settings.admin_password,
    )

    if not (
        valid_username
        and valid_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={
                "WWW-Authenticate": "Basic"
            },
        )

    return credentials


def render_error(
    request: Request,
    message: str,
):

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "message": message
        },
        status_code=400,
    )


@router.get(
    "/",
    response_class=HTMLResponse,
)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@router.post(
    "/generate-workout",
    response_class=HTMLResponse,
)
def generate_workout(
    request: Request,

    user_id: str = Form(...),

    name: str = Form(...),

    age: int = Form(...),

    weight: float = Form(...),

    goal: str = Form(...),

    intensity: str = Form(...),

    experience_level: str = Form(
        "beginner"
    ),

    db: Session = Depends(get_db),
):

    try:

        data = UserInput(
            user_id=user_id,
            name=name,
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity,
            experience_level=experience_level,
        )

        user = save_user(
            db,
            data,
        )

        workout = generate_workout_gemini(
            user
        )

        nutrition = (
            generate_nutrition_tip_with_flash(
                user
            )
        )

        save_plan(
            db,
            user.user_id,
            workout,
            nutrition,
        )

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "user": user,
                "workout_plan": pretty_plan(
                    workout
                ),
                "nutrition_tip": nutrition,
                "plan_json": workout,
                "message": (
                    "Your personalized plan "
                    "is ready."
                ),
            },
        )

    except (
        ValueError,
        AIServiceError,
    ) as exc:

        return render_error(
            request,
            str(exc),
        )


@router.post(
    "/submit-feedback",
    response_class=HTMLResponse,
)
def submit_feedback(
    request: Request,

    user_id: str = Form(...),

    feedback: str = Form(...),

    db: Session = Depends(get_db),
):

    try:

        settings = get_settings()

        data = FeedbackRequest(
            user_id=user_id,
            feedback=feedback,
        )

        if len(data.feedback) > settings.max_feedback_length:

            raise ValueError(
                "Feedback is too long."
            )

        user = get_user(
            db,
            data.user_id,
        )

        plan = get_current_plan(
            db,
            data.user_id,
        )

        if not user or not plan:

            raise ValueError(
                "No current plan found for "
                "that User ID."
            )

        current_plan = (
            plan.updated_plan
            or plan.original_plan
        )

        revised = update_workout_plan(
            user,
            current_plan,
            data.feedback,
        )

        update_plan(
            db,
            plan,
            revised,
            data.feedback,
        )

        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={
                "user": user,
                "workout_plan": pretty_plan(
                    revised
                ),
                "nutrition_tip": plan.nutrition_tip,
                "plan_json": revised,
                "message": (
                    "Your plan has been "
                    "updated using your feedback."
                ),
            },
        )

    except (
        ValueError,
        AIServiceError,
    ) as exc:

        return render_error(
            request,
            str(exc),
        )


@router.get(
    "/view-all-users",
    response_class=HTMLResponse,
)
def view_all_users(
    request: Request,

    _admin=Depends(admin_guard),

    db: Session = Depends(get_db),
):

    users = get_all_users(db)

    rows = []

    for user in users:

        plan = get_current_plan(
            db,
            user.user_id,
        )

        rows.append(
            {
                "user": user,
                "plan": plan,
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="all_users.html",
        context={
            "rows": rows
        },
    )


# =========================================================
# REST API
# =========================================================

api = APIRouter(
    prefix="/api/v1",
    tags=["FitBuddy API"],
)


@api.get("/health")
def health():

    settings = get_settings()

    return {
        "status": "ok",
        "ai_configured": bool(
            settings.gemini_api_key
        ),
        "mock_mode": (
            settings.allow_mock_ai
            and not bool(
                settings.gemini_api_key
            )
        ),
    }


@api.post(
    "/plans",
    response_model=PlanResponse,
)
def api_create_plan(
    payload: UserInput,
    db: Session = Depends(get_db),
):

    try:

        user = save_user(
            db,
            payload,
        )

        workout = generate_workout_gemini(
            user
        )

        nutrition = (
            generate_nutrition_tip_with_flash(
                user
            )
        )

        save_plan(
            db,
            user.user_id,
            workout,
            nutrition,
        )

        return PlanResponse(
            user_id=user.user_id,
            name=user.name,
            goal=user.goal,
            intensity=user.intensity,
            experience_level=(
                user.experience_level
            ),
            workout_plan=pretty_plan(
                workout
            ),
            nutrition_tip=nutrition,
        )

    except AIServiceError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )


@api.post(
    "/plans/{user_id}/feedback",
    response_model=PlanResponse,
)
def api_feedback(
    user_id: str,
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
):

    if payload.user_id != user_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "Path user_id and payload "
                "user_id must match."
            ),
        )

    user = get_user(
        db,
        user_id,
    )

    plan = get_current_plan(
        db,
        user_id,
    )

    if not user or not plan:

        raise HTTPException(
            status_code=404,
            detail=(
                "User or current plan "
                "not found."
            ),
        )

    try:

        current_plan = (
            plan.updated_plan
            or plan.original_plan
        )

        revised = update_workout_plan(
            user,
            current_plan,
            payload.feedback,
        )

        update_plan(
            db,
            plan,
            revised,
            payload.feedback,
        )

        return PlanResponse(
            user_id=user.user_id,
            name=user.name,
            goal=user.goal,
            intensity=user.intensity,
            experience_level=(
                user.experience_level
            ),
            workout_plan=pretty_plan(
                revised
            ),
            nutrition_tip=plan.nutrition_tip,
        )

    except AIServiceError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )


@api.get(
    "/plans/{user_id}"
)
def api_get_plan(
    user_id: str,
    db: Session = Depends(get_db),
):

    user = get_user(
        db,
        user_id,
    )

    plan = get_current_plan(
        db,
        user_id,
    )

    if not user or not plan:

        raise HTTPException(
            status_code=404,
            detail=(
                "User or current plan "
                "not found."
            ),
        )

    return {
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
            "experience_level": (
                user.experience_level
            ),
        },
        "original_plan": (
            plan.original_plan
        ),
        "updated_plan": (
            plan.updated_plan
        ),
        "nutrition_tip": (
            plan.nutrition_tip
        ),
        "feedback": plan.feedback,
    }