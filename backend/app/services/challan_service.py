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
            # Auto-create violation record if ID is not in DB (e.g. sample items)
            violation = models.Violation(
                id=violation_id,
                camera_id="CAM_DIRECT_ISSUE",
                track_id=101,
                type="RED_LIGHT",
                timestamp=datetime.datetime.utcnow(),
                confidence=0.95,
                reason="Traffic violation detected by RoadGuard AI engine.",
                evidence_id=f"ev_auto_{uuid.uuid4().hex[:6]}"
            )
            db.add(violation)
            db.commit()
            db.refresh(violation)

        # Check if challan already exists
        existing = db.query(models.Challan).filter(models.Challan.violation_id == violation.id).first()
        if existing:
            return existing

        challan_num = f"CH-{int(datetime.datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:4].upper()}"

        db_challan = models.Challan(
            violation_id=violation.id,
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
    def issue_direct_challan(
        cls,
        vehicle_number: str,
        violation_type: str,
        db: Session,
        camera_id: str = "CAM_MANUAL_ISSUE",
        notes: str | None = None
    ) -> models.Challan:
        """Issue an e-Challan directly for any vehicle plate number."""
        violation = models.Violation(
            camera_id=camera_id,
            track_id=int(datetime.datetime.utcnow().timestamp()) % 1000,
            type=violation_type,
            timestamp=datetime.datetime.utcnow(),
            confidence=0.95,
            reason=f"Direct traffic infraction ({violation_type}) reported for vehicle {vehicle_number}.",
            evidence_id=f"ev_dir_{uuid.uuid4().hex[:6]}"
        )
        db.add(violation)
        db.commit()
        db.refresh(violation)

        challan_num = f"CH-{int(datetime.datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:4].upper()}"
        db_challan = models.Challan(
            violation_id=violation.id,
            challan_number=challan_num,
            vehicle_number=vehicle_number.upper(),
            type=violation_type,
            status="GENERATED",
            notes=notes or "MANUAL / AI ISSUED TRAFFIC E-CHALLAN NOTICE"
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
