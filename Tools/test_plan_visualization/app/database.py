from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./checkbox_jobs.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, index=True)
    provider = Column(String, index=True)
    category_id = Column(String, index=True)
    environ = Column(Text)  # Stored as JSON string or comma separated
    manifest = Column(
        Text
    )  # Stored as JSON string or comma separated keywords from `requires`
    command = Column(Text)
    summary = Column(Text)
    description = Column(Text)
    unit_type = Column(String)  # 'job', 'test plan', etc.
    data = Column(Text)  # JSON string of all attributes


class TestPlan(Base):
    __tablename__ = "test_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String, index=True)  # e.g. bluetooth-cert-automated
    full_id = Column(
        String, index=True
    )  # e.g. com.canonical.certification::bluetooth-cert-automated
    provider = Column(String, index=True)
    name = Column(Text)
    include = Column(Text)  # JSON list of raw include patterns
    exclude = Column(Text)  # JSON list of raw exclude patterns
    nested_part = Column(Text)  # JSON list of nested test plan IDs
    data = Column(Text)  # JSON of all raw attributes


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
