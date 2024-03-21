from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bdi_api import app
from bdi_api.models import Base
from bdi_api.s8.exercise import get_db

# Configure your database URL for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Create a new engine instance for the test database
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a new SessionLocal class with bind to the engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the test database tables
Base.metadata.create_all(bind=engine)

# Instantiate the test client
client = TestClient(app)


# Dependency override for get_db
def override_get_db():
    global db
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# Now write the tests
def test_list_aircraft():
    response = client.get("/api/s8/aircraft/")
    assert response.status_code == 200
    # Additional assertions as necessary


def test_get_aircraft_co2():
    # You need to have an aircraft with known ICAO and day for this test
    test_icao = 'some_icao'
    test_day = '2023-11-01'
    response = client.get(f"/api/s8/aircraft/{test_icao}/co2?day={test_day}")
    assert response.status_code == 200
    # Additional assertions based on your logic and data

# Additional tests as necessary for other endpoints
