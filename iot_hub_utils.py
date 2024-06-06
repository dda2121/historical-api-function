from requests import Session

import iot_hub_database
import models

def get_db():
    db = iot_hub_database.SessionLocal()
    print("Database connection opened")
    try:
        yield db
    finally:
        db.close()
        print("Database connection closed")

def get_iothub_by_user_id(db: Session, user_id: int):
    return db.query(models.HubDB).filter(models.HubDB.user_id == user_id).first()