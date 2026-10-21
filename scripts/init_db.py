import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import init_db, check_connection
from app.core.logging import logger


def main():
    print("Checking database connection...")
    if check_connection():
        print("Connected to database successfully.")
    else:
        print("Warning: Initial connection check reported issues. Proceeding with table creation...")

    init_db()
    print("All tables (Bronze, Silver, Gold, Operations, ML) created successfully.")


if __name__ == "__main__":
    main()
