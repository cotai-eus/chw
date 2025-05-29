"""
Database initialization script
Creates initial data for the application
"""

from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.db.models.company import Company
from app.db.models.user import User
from app.db.models.user_profile import UserProfile
import uuid


def init_db(db: Session) -> None:
    """
    Initialize the database with basic data
    """
    # Check if we already have data
    existing_user = db.query(User).first()
    if existing_user:
        print("Database already initialized, skipping...")
        return

    # Create default company
    default_company = Company(
        id=str(uuid.uuid4()),
        name="Default Company",
        slug="default-company",
        email="admin@defaultcompany.com",
        phone="(11) 99999-9999",
        cnpj="00.000.000/0001-00",
        is_active=True
    )
    db.add(default_company)
    db.flush()

    # Create admin user
    admin_user = User(
        id=str(uuid.uuid4()),
        email="admin@admin.com",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_superuser=True,
        company_id=default_company.id
    )
    db.add(admin_user)
    db.flush()

    # Create admin profile
    admin_profile = UserProfile(
        id=str(uuid.uuid4()),
        user_id=admin_user.id,
        first_name="Admin",
        last_name="User",
        phone="(11) 99999-9999",
        role="admin"
    )
    db.add(admin_profile)

    # Create test user
    test_user = User(
        id=str(uuid.uuid4()),
        email="user@test.com",
        hashed_password=get_password_hash("test123"),
        is_active=True,
        is_superuser=False,
        company_id=default_company.id
    )
    db.add(test_user)
    db.flush()

    # Create test profile
    test_profile = UserProfile(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        first_name="Test",
        last_name="User",
        phone="(11) 88888-8888",
        role="user"
    )
    db.add(test_profile)

    db.commit()
    print("✅ Database initialized with default data!")
    print("Admin user: admin@admin.com / admin123")
    print("Test user: user@test.com / test123")
