"""
Jednorázový skript pro vytvoření prvního uživatele (Admin).

Použití (spouští se uvnitř backend kontejneru):
    docker compose exec backend python create_admin.py

Skript se zeptá na email, jméno a heslo interaktivně.
"""
import getpass
import sys

from app.database import SessionLocal
from app.models.user import User
from app.models.enums import UserRole
from app.core.security import hash_password


def main():
    db = SessionLocal()
    try:
        email = input("Email: ").strip()
        if not email:
            print("Email nesmí být prázdný.")
            sys.exit(1)

        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Uživatel s emailem {email} už existuje.")
            sys.exit(1)

        full_name = input("Celé jméno: ").strip()
        password = getpass.getpass("Heslo: ")
        password_confirm = getpass.getpass("Heslo znovu: ")

        if password != password_confirm:
            print("Hesla se neshodují.")
            sys.exit(1)

        if len(password) < 8:
            print("Heslo musí mít alespoň 8 znaků.")
            sys.exit(1)

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Uživatel {email} (role Admin) byl úspěšně vytvořen.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
