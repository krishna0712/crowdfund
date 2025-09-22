#!/usr/bin/env python3
"""
MySQL database connection test script
Run this before starting your Flask app to verify database connectivity
"""

import pymysql
import sys

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'krishna',
    'password': 'mysql@123',
    'database': 'crowdfund',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def test_mysql_connection():
    """Test direct MySQL connection"""
    print("🔍 Testing MySQL connection...")
    
    try:
        # Connect to MySQL
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("✅ MySQL connection successful!")
        
        # Test basic query
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"📊 MySQL version: {version['VERSION()']}")
        
        # Check current database
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()
        print(f"📁 Current database: {current_db['DATABASE()']}")
        
        # List all tables in the database
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if tables:
            table_names = [list(table.values())[0] for table in tables]
            print(f"📋 Tables found: {table_names}")
            
            # Check data in each table
            for table in tables:
                table_name = list(table.values())[0]
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()
                print(f"   - {table_name}: {count['count']} rows")
                
                # Show sample data for users table
                if table_name == 'users':
                    cursor.execute("SELECT id, username, email, is_admin FROM users LIMIT 5")
                    users = cursor.fetchall()
                    print(f"   📝 Sample users:")
                    for user in users:
                        print(f"      ID: {user['id']}, Username: {user['username']}, Email: {user['email']}, Admin: {user['is_admin']}")
                
                # Show sample data for contributions table
                elif table_name == 'contributions':
                    cursor.execute("SELECT id, amount, user_id, project_id FROM contributions LIMIT 5")
                    contributions = cursor.fetchall()
                    print(f"   💰 Sample contributions:")
                    for contrib in contributions:
                        print(f"      ID: {contrib['id']}, Amount: ${contrib['amount']}, User: {contrib['user_id']}, Project: {contrib['project_id']}")
        else:
            print("⚠️  No tables found in database")
        
        cursor.close()
        connection.close()
        return True
        
    except pymysql.Error as e:
        print(f"❌ MySQL connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_flask_sqlalchemy():
    """Test Flask-SQLAlchemy connection"""
    print("\n🔍 Testing Flask-SQLAlchemy connection...")
    
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        # Create engine with the same URI as Flask app
        engine = create_engine("mysql+pymysql://krishna:mysql%40123@localhost:3306/crowdfund")
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Flask-SQLAlchemy connection successful!")
            
            # Test if tables exist
            result = connection.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            
            if tables:
                table_names = [row[0] for row in tables]
                print(f"📋 Tables accessible via SQLAlchemy: {table_names}")
            else:
                print("⚠️  No tables accessible via SQLAlchemy")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask-SQLAlchemy connection failed: {e}")
        return False

def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    print("\n🔧 Checking if database exists...")
    
    try:
        # Connect without specifying database
        config_without_db = DB_CONFIG.copy()
        config_without_db.pop('database', None)
        
        connection = pymysql.connect(**config_without_db)
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"✅ Database '{DB_CONFIG['database']}' ensured to exist")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def main():
    print("🚀 Starting MySQL connectivity tests...\n")
    
    # Test 1: Create database if needed
    db_created = create_database_if_not_exists()
    
    # Test 2: Direct MySQL connection
    mysql_success = test_mysql_connection()
    
    # Test 3: Flask-SQLAlchemy connection
    flask_success = test_flask_sqlalchemy()
    
    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY:")
    print(f"   Database Creation: {'✅ PASS' if db_created else '❌ FAIL'}")
    print(f"   MySQL Direct:     {'✅ PASS' if mysql_success else '❌ FAIL'}")
    print(f"   Flask-SQLAlchemy:  {'✅ PASS' if flask_success else '❌ FAIL'}")
    
    if db_created and mysql_success and flask_success:
        print("\n🎉 All tests passed! Your MySQL database is ready.")
        print("\n💡 Next steps:")
        print("   1. Run your Flask app: python app.py")
        print("   2. Visit: http://localhost:5000/debug/db-info (as admin)")
        print("   3. Create new users and test functionality")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues before running your Flask app.")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Check if MySQL is running: sudo systemctl status mysql")
        print("   2. Start MySQL if needed: sudo systemctl start mysql")
        print("   3. Verify user exists and has permissions:")
        print("      mysql -u root -p")
        print("      CREATE USER 'krishna'@'localhost' IDENTIFIED BY 'mysql@123';")
        print("      GRANT ALL PRIVILEGES ON crowdfund.* TO 'krishna'@'localhost';")
        print("      FLUSH PRIVILEGES;")
        print("   4. Install required packages: pip install PyMySQL cryptography")

if __name__ == "__main__":
    main()