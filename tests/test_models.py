from backend.app.models import domain as models


def test_video_and_detection_creation(db_session):
    video = models.Video(
        camera_id="CAM_TEST_01",
        filename="test_feed.mp4",
        fps=30.0,
        width=1920,
        height=1080,
        duration=10.0
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    assert video.id is not None

    detection = models.Detection(
        video_id=video.id,
        frame_no=1,
        timestamp=0.033,
        class_name="car",
        confidence=0.92,
        x1=100.0,
        y1=150.0,
        x2=300.0,
        y2=350.0
    )
    db_session.add(detection)
    db_session.commit()

    saved_det = db_session.query(models.Detection).filter_by(video_id=video.id).first()
    assert saved_det is not None
    assert saved_det.class_name == "car"


def test_risk_score_and_contribution(db_session):
    risk_score = models.RiskScore(
        camera_id="CAM_TEST_01",
        score=65.0,
        category="HIGH"
    )
    db_session.add(risk_score)
    db_session.commit()

    contrib = models.RiskContribution(
        risk_score_id=risk_score.id,
        indicator="red_light",
        normalized_value=0.8,
        weight=0.20,
        contribution=16.0
    )
    db_session.add(contrib)
    db_session.commit()

    saved_score = db_session.query(models.RiskScore).first()
    assert saved_score is not None
    assert len(saved_score.contributions) == 1
    assert saved_score.contributions[0].indicator == "red_light"
