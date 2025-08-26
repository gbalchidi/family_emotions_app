#!/usr/bin/env python3
"""Test script to debug PostgreSQL connection issues."""

import sys
import traceback

def test_imports():
    """Test all required database imports."""
    print("🔍 Testing database-related imports...")
    
    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy version: {sqlalchemy.__version__}")
    except ImportError as e:
        print(f"❌ SQLAlchemy import failed: {e}")
        return False
    
    try:
        import psycopg2
        print(f"✅ psycopg2 version: {psycopg2.__version__}")
    except ImportError as e:
        print(f"❌ psycopg2 import failed: {e}")
        return False
    
    try:
        import asyncpg
        print(f"✅ asyncpg version: {asyncpg.__version__}")
    except ImportError as e:
        print(f"❌ asyncpg import failed: {e}")
        return False
    
    return True

def test_sqlalchemy_dialects():
    """Test SQLAlchemy PostgreSQL dialect loading."""
    print("\n🔍 Testing SQLAlchemy PostgreSQL dialects...")
    
    try:
        from sqlalchemy import create_engine
        
        # Test regular postgres dialect
        print("Testing postgres:// URL...")
        engine = create_engine("postgres://user:pass@localhost:5432/test", strategy='mock', executor=lambda sql, *_: None)
        print("✅ postgres:// dialect loaded successfully")
        
        # Test postgresql dialect  
        print("Testing postgresql:// URL...")
        engine = create_engine("postgresql://user:pass@localhost:5432/test", strategy='mock', executor=lambda sql, *_: None)
        print("✅ postgresql:// dialect loaded successfully")
        
        # Test asyncpg dialect
        print("Testing postgresql+asyncpg:// URL...")
        engine = create_engine("postgresql+asyncpg://user:pass@localhost:5432/test", strategy='mock', executor=lambda sql, *_: None)
        print("✅ postgresql+asyncpg:// dialect loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy dialect test failed: {e}")
        traceback.print_exc()
        return False

def test_database_url_parsing():
    """Test parsing of the actual database URL."""
    print("\n🔍 Testing actual database URL parsing...")
    
    # Your actual DATABASE_URL
    database_url = "postgres://postgres:A6llBATJMFjmnTbZ19amTd232paTNdC90r2kdgiVjqwR7kf9dDvf4L29k388BZwR@d0ooscgogskck0wg04w8oo00:5432/postgres"
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.engine.url import make_url
        
        # Parse URL
        url = make_url(database_url)
        print(f"✅ URL parsed: {url.drivername}://{url.username}@{url.host}:{url.port}/{url.database}")
        
        # Convert to asyncpg
        asyncpg_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        url_asyncpg = make_url(asyncpg_url)
        print(f"✅ AsyncPG URL: {url_asyncpg.drivername}://{url_asyncpg.username}@{url_asyncpg.host}:{url_asyncpg.port}/{url_asyncpg.database}")
        
        # Try to create engine (mock mode)
        engine = create_engine(asyncpg_url, strategy='mock', executor=lambda sql, *_: None)
        print("✅ Engine created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Database URL test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all database tests."""
    print("🚀 PostgreSQL Connection Diagnostic Tool")
    print("=" * 50)
    
    success = True
    
    # Test 1: Imports
    if not test_imports():
        success = False
    
    # Test 2: SQLAlchemy dialects
    if not test_sqlalchemy_dialects():
        success = False
    
    # Test 3: Actual URL parsing
    if not test_database_url_parsing():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! Database connection should work.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())