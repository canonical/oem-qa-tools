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
    """
    All runnable units: regular jobs (plugin: shell/manual/…),
    resource jobs (plugin: resource), attachment jobs, and their
    also-after-suspend mirror variants.
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, index=True)
    provider = Column(String, index=True)
    category_id = Column(String, index=True)
    environ = Column(Text)    # JSON list of env-var names
    manifest = Column(Text)   # JSON list of manifest keys from `requires`
    command = Column(Text)
    summary = Column(Text)
    description = Column(Text)
    unit_type = Column(String, index=True)  # canonical unit: field value
    plugin = Column(String, index=True)     # plugin: field (shell/manual/resource/…)
    data = Column(Text)       # JSON of all raw PXU attributes


class ManifestEntry(Base):
    """
    Manifest entry units (unit: manifest entry).
    These describe hardware capability flags (e.g. has_bt_adapter).
    """
    __tablename__ = "manifest_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String, index=True)   # bare ID, e.g. has_bt_adapter
    full_id = Column(String, index=True)    # namespace::ID
    provider = Column(String, index=True)
    name = Column(Text)        # _name field
    value_type = Column(String)            # boolean / natural / …
    summary = Column(Text)
    data = Column(Text)                    # JSON of all raw PXU attributes


class TestPlan(Base):
    __tablename__ = "test_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String, index=True)   # bare ID
    full_id = Column(String, index=True)   # namespace::ID
    provider = Column(String, index=True)
    name = Column(Text)
    include = Column(Text)            # JSON list of include patterns
    exclude = Column(Text)            # JSON list of exclude patterns
    nested_part = Column(Text)        # JSON list of nested plan refs
    bootstrap_include = Column(Text)  # JSON list of bootstrap resource refs
    data = Column(Text)               # JSON of all raw PXU attributes


class PlanMembership(Base):
    """
    Precomputed effective job set per test plan (built at DB-update time).
    Enables O(1) compare operations instead of recursive on-the-fly expansion.
    """
    __tablename__ = "plan_membership"

    id = Column(Integer, primary_key=True)
    plan_full_id = Column(String, index=True)
    job_id = Column(String, index=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
