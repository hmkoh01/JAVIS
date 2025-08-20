"""
Database connection and initialization module
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path for relative imports
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Initialize variables
SQLiteMeta = None
QdrantManager = None

# Try to import SQLiteMeta
try:
    from sqlite_meta import SQLiteMeta
    print("SQLiteMeta imported successfully")
except ImportError as e:
    print(f"Warning: Could not import SQLiteMeta: {e}")
    SQLiteMeta = None

# Try to import QdrantManager (optional)
try:
    from qdrant_client import QdrantManager
    print("QdrantManager imported successfully")
except ImportError as e:
    print(f"Warning: Could not import QdrantManager: {e}")
    print("Qdrant vector database features will be disabled")
    QdrantManager = None

def create_tables():
    """Initialize database tables"""
    try:
        # Initialize SQLite metadata database
        if SQLiteMeta is not None:
            try:
                sqlite_meta = SQLiteMeta()
                print("SQLite metadata tables initialized")
            except Exception as sqlite_error:
                print(f"SQLite initialization failed: {sqlite_error}")
                return False
        else:
            print("SQLiteMeta not available")
            return False
        
        # Try to initialize Qdrant vector database (optional)
        if QdrantManager is not None:
            try:
                qdrant_manager = QdrantManager()
                print("Qdrant vector database initialized")
            except Exception as qdrant_error:
                print(f"Qdrant vector database initialization failed: {qdrant_error}")
                print("Qdrant server is not running. Vector search features will be limited.")
                print("To enable full functionality, start Qdrant server: docker run -p 6333:6333 qdrant/qdrant")
        else:
            print("Qdrant vector database disabled (QdrantManager not available)")
        
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def get_sqlite_meta():
    """Get SQLite metadata instance"""
    if SQLiteMeta is not None:
        return SQLiteMeta()
    else:
        raise ImportError("SQLiteMeta not available")

def get_qdrant_manager():
    """Get Qdrant manager instance"""
    if QdrantManager is not None:
        return QdrantManager()
    else:
        raise ImportError("QdrantManager not available")

# If this file is run directly, initialize the database
if __name__ == "__main__":
    success = create_tables()
    if success:
        print("Database initialization completed successfully")
        exit(0)
    else:
        print("Database initialization failed")
        exit(1)
