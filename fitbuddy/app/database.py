from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from .config import get_settings


settings = get_settings()


connect_args = {}

if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}


engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    goal: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    intensity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    experience_level: Mapped[str] = mapped_column(
        String(40),
        default="beginner",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    plans: Mapped[list["Plan"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    original_plan: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    updated_plan: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    nutrition_tip: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )

    user: Mapped[User] = relationship(
        back_populates="plans",
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def save_user(db: Session, data):
    user = (
        db.query(User)
        .filter(User.user_id == data.user_id)
        .first()
    )

    if user:
        user.name = data.name
        user.age = data.age
        user.weight = data.weight
        user.goal = data.goal
        user.intensity = data.intensity
        user.experience_level = data.experience_level

    else:
        user = User(
            **data.model_dump()
        )

        db.add(user)

    db.commit()
    db.refresh(user)

    return user


def save_plan(
    db: Session,
    user_id: str,
    original_plan: str,
    nutrition_tip: str,
):
    # Mark previous plans as old.
    (
        db.query(Plan)
        .filter(Plan.user_id == user_id)
        .update({"is_current": False})
    )

    plan = Plan(
        user_id=user_id,
        original_plan=original_plan,
        nutrition_tip=nutrition_tip,
        is_current=True,
    )

    db.add(plan)

    db.commit()
    db.refresh(plan)

    return plan


def get_current_plan(
    db: Session,
    user_id: str,
):
    return (
        db.query(Plan)
        .filter(
            Plan.user_id == user_id,
            Plan.is_current.is_(True),
        )
        .order_by(Plan.id.desc())
        .first()
    )


def update_plan(
    db: Session,
    plan: Plan,
    updated_plan: str,
    feedback: str,
    nutrition_tip: str | None = None,
):
    plan.updated_plan = updated_plan
    plan.feedback = feedback

    if nutrition_tip:
        plan.nutrition_tip = nutrition_tip

    db.commit()
    db.refresh(plan)

    return plan


def get_all_users(db: Session):
    return (
        db.query(User)
        .order_by(User.created_at.desc())
        .all()
    )


def get_all_plans(db: Session):
    return (
        db.query(Plan)
        .order_by(Plan.created_at.desc())
        .all()
    )


def get_user(
    db: Session,
    user_id: str,
):
    return (
        db.query(User)
        .filter(User.user_id == user_id)
        .first()
    )