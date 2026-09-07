import datetime
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models import domain as models


class ChallanService:
    """Simulated e-Challan lifecycle management service (Academic Simulation Only)."""

    @classmethod
    def generate_challan_from_violation(
        cls,
        violation_id: int,
        vehicle_number: str,
        db: Session,
        notes: str | None = None
    ) -> models.Challan:
        violation = db.query(models.Violation).filter(models.Violation.id == violation_id).first()
        if not violation:
            raise HTTPException(status_code=404, detail="Source violation record not found")

        # Check if challan already exists
        existing = db.query(models.Challan).filter(models.Challan.violation_id == violation_id).first()
        if existing:
            return existing

        challan_num = f"CH-{int(datetime.datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:4].upper()}"

        db_challan = models.Challan(
            violation_id=violation_id,
            challan_number=challan_num,
            vehicle_number=vehicle_number,
            type=violation.type,
            status="GENERATED",
            notes=notes or "ACADEMIC SIMULATION ONLY - NO LEGAL VALIDITY"
        )
        db.add(db_challan)
        db.commit()
        db.refresh(db_challan)
        return db_challan

    @classmethod
    def update_challan_status(cls, challan_id: int, new_status: str, db: Session) -> models.Challan:
        allowed = {"GENERATED", "UNDER_REVIEW", "RESOLVED", "CANCELLED"}
        if new_status not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid status '{new_status}'. Allowed: {allowed}")

        challan = db.query(models.Challan).filter(models.Challan.id == challan_id).first()
        if not challan:
            raise HTTPException(status_code=404, detail="Challan record not found")

        challan.status = new_status
        db.commit()
        db.refresh(challan)
        return challan

    @classmethod
    def list_challans(cls, db: Session, status: str | None = None) -> list[models.Challan]:
        query = db.query(models.Challan)
        if status:
            query = query.filter(models.Challan.status == status)
        return query.order_by(models.Challan.timestamp.desc()).all()
