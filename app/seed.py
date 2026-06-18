from app.database import engine, Base, SessionLocal
from app.models import User
from app.auth import hash_password

Base.metadata.create_all(bind=engine)

SEED_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "doctor", "password": "doctor123", "role": "doctor"},
    {"username": "nurse", "password": "nurse123", "role": "nurse"},
    {"username": "reception", "password": "reception123", "role": "reception"},
]


def seed():
    db = SessionLocal()
    try:
        for u in SEED_USERS:
            exists = db.query(User).filter(User.username == u["username"]).first()
            if not exists:
                db.add(User(username=u["username"], password=hash_password(u["password"]), role=u["role"]))
        db.commit()
        print("Seed completed — 4 default users inserted.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
