from app.auth import hash_password
from app.database import Base, SessionLocal, engine
from app.models import User
from app.simulator import run_simulation_to_completion

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

        count = db.query(User).count()
        print(f"Seed completed — {count} users.")

        print("Clearing existing simulation data to prevent duplicates...")
        from app.models import Alert, Appointment, Event, Medication, Notification, Patient, Review
        db.query(Alert).delete()
        db.query(Appointment).delete()
        db.query(Event).delete()
        db.query(Medication).delete()
        db.query(Notification).delete()
        db.query(Patient).delete()
        db.query(Review).delete()
        db.commit()

        print("Processing simulation events...")
        run_simulation_to_completion(db)
        print("Simulation events processed — all dashboards have data.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
