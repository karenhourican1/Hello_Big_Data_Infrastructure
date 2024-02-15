import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

# Explicitly load environment variables for testing
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_db_connection():
    # Create a new database session
    with TestingSessionLocal() as db:
        # Try to fetch the first row from the 'aircraft' table
        result = db.execute(text("SELECT * FROM aircraft LIMIT 1"))
        aircraft = result.first()

        # Check if a record was found
        assert aircraft is not None, "No aircraft found in the database."
