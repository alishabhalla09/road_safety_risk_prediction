# ROADGUARD AI — Road Safety & Traffic Intelligence Platform

RoadGuard AI is an AI-powered road safety and traffic intelligence platform that converts raw road/CCTV video into structured traffic, violation, vehicle-identification, safety, and risk intelligence.

## Core Capabilities
- **Video Ingestion & Frame Processing:** High-throughput resilient video decoding.
- **Multi-Class Object Detection:** Ultralytics YOLO detecting cars, buses, trucks, motorcycles, auto-rickshaws, pedestrians, bicycles, traffic signals, and license plates.
- **Multi-Object Tracking:** ByteTrack / BoT-SORT persistent tracking.
- **Trajectory & Kinematics:** Center-point trajectory extraction and velocity estimation.
- **Traffic Density & Flow:** ROI polygon occupancy and directional line-crossing counting.
- **Scene-Aware Violation Detection:** Wrong-way driving, illegal lane usage, and red-light violations using configurable camera geometries and temporal persistence.
- **Helmet & Triple Riding Detection:** Motorcyclist safety compliance analysis.
- **ANPR (Automatic Number Plate Recognition):** OCR multi-frame temporal consensus and plate text extraction (privacy-minimized).
- **Simulated e-Challan Generation:** Academic simulation lifecycle management (`GENERATED` -> `UNDER_REVIEW` -> `RESOLVED` / `CANCELLED`).
- **Surrogate Safety Measures (TTC & PET):** Time-to-Collision and Post-Encroachment Time near-miss conflict estimation.
- **Explainable 0–100 Risk Score Engine:** Interpretable multi-factor safety index with component contribution breakdown.
- **Risk Heatmap Visualization:** Spatiotemporal risk density mapping.
- **Research & Benchmark Suite:** Comparative experiment tracking and benchmark metrics.

---

## Technical Stack
- **AI / CV:** Python 3.10+, PyTorch, Ultralytics YOLO, OpenCV, NumPy, ByteTrack / BoT-SORT
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.0, PostgreSQL, Alembic
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons
- **Infrastructure & Testing:** Docker, Docker Compose, Pytest, Ruff

---

## Directory Structure
```
roadguard-ai/
├── ai/                     # Computer Vision & Risk AI Micro-modules
│   ├── detection/          # YOLO object detection
│   ├── tracking/           # ByteTrack / BoT-SORT tracking
│   ├── trajectory/         # Trajectory calculation & kinematics
│   ├── traffic/            # Density & flow computation
│   ├── violations/         # Scene-aware rule engine (Wrong-way, Lane, Red light)
│   ├── anpr/               # Number plate recognition & temporal consensus
│   ├── safety/             # TTC / PET safety indicators & conflict detection
│   ├── risk/               # Explainable 0-100 risk score engine
│   └── common/             # Config loaders & geometry utils
├── backend/                # FastAPI Backend Service
│   └── app/
│       ├── api/            # REST API Endpoint routes
│       ├── core/           # App configuration & settings
│       ├── db/             # SQLAlchemy DB engine & session
│       ├── models/         # SQLAlchemy ORM domain models
│       ├── schemas/        # Pydantic schemas
│       └── services/       # Business logic & pipeline orchestrator
├── frontend/               # React + Vite + TypeScript Dashboard
├── configs/                # Camera scene configs, YOLO configs, Risk weights
├── data/                   # Video samples, model weights, dataset annotations
├── docker/                 # Backend & Frontend Dockerfiles
├── docs/                   # System architecture, DB schema, API spec, setup guide
├── experiments/            # Benchmark tracking & experiment logs
├── tests/                  # Pytest unit & integration tests
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## Disclaimer
> **Academic Simulation Only:** The e-Challan, ANPR, and risk scoring modules are designed strictly for academic research and traffic safety analysis. This system does NOT connect to police/government databases, issue legal penalties, process payments, or perform facial recognition.
