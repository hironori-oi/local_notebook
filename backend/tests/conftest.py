"""
Pytest configuration and fixtures for the test suite.
"""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Set test environment before importing app
os.environ["ENV"] = "development"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-purposes-only-32chars"

from app.main import app
from app.db.base import Base
from app.core.deps import get_db
from app.models.user import User
from app.services.auth import get_password_hash, create_access_token


# Use SQLite for testing (in-memory)
SQLALCHEMY_TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///./test.db"
)

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_TEST_DATABASE_URL else {},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""

    def override_get_db_with_session():
        """Return the test database session."""
        yield db

    app.dependency_overrides[get_db] = override_get_db_with_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("TestPassword123!"),
        display_name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user."""
    token = create_access_token(
        data={"sub": str(test_user.id), "username": test_user.username}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def authenticated_client(client: TestClient, auth_headers: dict) -> TestClient:
    """Create an authenticated test client."""
    client.headers.update(auth_headers)
    return client


@pytest.fixture
def test_notebook(db: Session, test_user: User):
    """Create a test notebook for the test user."""
    from app.models.notebook import Notebook

    notebook = Notebook(
        title="Test Notebook",
        description="A test notebook for testing",
        owner_id=test_user.id,
    )
    db.add(notebook)
    db.commit()
    db.refresh(notebook)
    return notebook


@pytest.fixture
def other_user(db: Session) -> User:
    """Create another test user."""
    user = User(
        username="otheruser",
        hashed_password=get_password_hash("OtherPassword123!"),
        display_name="Other User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user_notebook(db: Session, other_user: User):
    """Create a notebook owned by another user."""
    from app.models.notebook import Notebook

    notebook = Notebook(
        title="Other User's Notebook",
        description="A notebook owned by another user",
        owner_id=other_user.id,
    )
    db.add(notebook)
    db.commit()
    db.refresh(notebook)
    return notebook


@pytest.fixture
def test_source(db: Session, test_notebook):
    """Create a test source for the test notebook."""
    from app.models.source import Source

    source = Source(
        notebook_id=test_notebook.id,
        filename="test_document.txt",
        file_type="txt",
        file_size=100,
        content="This is test content for the source document.",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
