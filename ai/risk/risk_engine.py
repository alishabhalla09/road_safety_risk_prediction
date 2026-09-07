import datetime
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class IndicatorContribution:
    indicator: str
    normalized_value: float
    weight: float
    contribution: float


@dataclass
class RiskScoreOutput:
    camera_id: str
    timestamp: datetime.datetime
    score: float
    category: str
    contributions: list[IndicatorContribution]
    heatmap_matrix: list[list[float]]  # 10x10 normalized risk grid


class ExplainableRiskEngine:
    """Multi-Factor Explainable Risk Score Engine (0–100 Scale) with Spatial Heatmap Matrix."""

    def __init__(self, risk_config: dict[str, Any]):
        self.weights = risk_config.get("weights", {
            "traffic_density": 0.15,
            "flow_imbalance": 0.10,
            "wrong_way": 0.20,
            "lane_violation": 0.10,
            "red_light": 0.20,
            "helmet_violation": 0.05,
            "triple_riding": 0.05,
            "surrogate_safety_ttc_pet": 0.15
        })
        self.bounds = risk_config.get("indicator_normalization_bounds", {
            "density_max": 1.0,
            "flow_imbalance_max": 1.0,
            "wrong_way_max_count": 5,
            "lane_violation_max_count": 10,
            "red_light_max_count": 5,
            "helmet_violation_max_count": 10,
            "triple_riding_max_count": 5,
            "safety_critical_events_max": 5
        })
        self.categories = risk_config.get("risk_category_thresholds", {
            "LOW": [0, 25],
            "MEDIUM": [25, 55],
            "HIGH": [55, 80],
            "CRITICAL": [80, 100]
        })

    def categorize_score(self, score: float) -> str:
        if score < 25.0:
            return "LOW"
        elif score < 55.0:
            return "MEDIUM"
        elif score < 80.0:
            return "HIGH"
        else:
            return "CRITICAL"

    def compute_risk(
        self,
        camera_id: str,
        density: float,
        flow_in: int,
        flow_out: int,
        violations: list[Any],
        safety_events: list[Any],
        active_tracks: list[Any],
        grid_rows: int = 10,
        grid_cols: int = 10
    ) -> RiskScoreOutput:
        # 1. Compute raw indicator values
        wrong_way_cnt = sum(1 for v in violations if getattr(v, "type", "") == "WRONG_WAY")
        lane_viol_cnt = sum(1 for v in violations if getattr(v, "type", "") == "LANE_VIOLATION")
        red_light_cnt = sum(1 for v in violations if getattr(v, "type", "") == "RED_LIGHT")
        helmet_cnt = sum(1 for v in violations if getattr(v, "type", "") == "HELMET")
        triple_cnt = sum(1 for v in violations if getattr(v, "type", "") == "TRIPLE_RIDING")
        safety_cnt = len(safety_events)

        total_flow = max(flow_in + flow_out, 1)
        flow_imbalance = abs(flow_in - flow_out) / float(total_flow)

        # 2. Normalize each indicator [0.0 - 1.0]
        norm_map = {
            "traffic_density": min(density / self.bounds.get("density_max", 1.0), 1.0),
            "flow_imbalance": min(flow_imbalance / self.bounds.get("flow_imbalance_max", 1.0), 1.0),
            "wrong_way": min(wrong_way_cnt / float(self.bounds.get("wrong_way_max_count", 5)), 1.0),
            "lane_violation": min(lane_viol_cnt / float(self.bounds.get("lane_violation_max_count", 10)), 1.0),
            "red_light": min(red_light_cnt / float(self.bounds.get("red_light_max_count", 5)), 1.0),
            "helmet_violation": min(helmet_cnt / float(self.bounds.get("helmet_violation_max_count", 10)), 1.0),
            "triple_riding": min(triple_cnt / float(self.bounds.get("triple_riding_max_count", 5)), 1.0),
            "surrogate_safety_ttc_pet": min(safety_cnt / float(self.bounds.get("safety_critical_events_max", 5)), 1.0)
        }

        # 3. Apply weights & sum contributions
        contributions: list[IndicatorContribution] = []
        raw_weighted_score = 0.0

        for ind_name, weight in self.weights.items():
            norm_val = norm_map.get(ind_name, 0.0)
            contrib = norm_val * weight * 100.0
            raw_weighted_score += contrib
            contributions.append(
                IndicatorContribution(
                    indicator=ind_name,
                    normalized_value=round(norm_val, 4),
                    weight=weight,
                    contribution=round(contrib, 2)
                )
            )

        final_score = round(min(max(raw_weighted_score, 0.0), 100.0), 2)
        category = self.categorize_score(final_score)

        # 4. Generate 2D Risk Heatmap Matrix (10x10 normalized grid over image dimensions 1920x1080)
        grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
        img_w, img_h = 1920, 1080

        # Accumulate risk intensity from vehicle positions and safety events
        for track in active_tracks:
            cx, cy = track.center
            r = int(min(max(cy / img_h * grid_rows, 0), grid_rows - 1))
            c = int(min(max(cx / img_w * grid_cols, 0), grid_cols - 1))
            grid[r, c] += 0.2

        for se in safety_events:
            # High intensity near safety conflicts
            grid[grid_rows // 2, grid_cols // 2] += 0.5

        # Normalize heatmap grid to [0.0 - 1.0]
        max_grid = np.max(grid)
        if max_grid > 0:
            grid = grid / max_grid

        heatmap_matrix = [[round(float(val), 2) for val in row] for row in grid.tolist()]

        return RiskScoreOutput(
            camera_id=camera_id,
            timestamp=datetime.datetime.utcnow(),
            score=final_score,
            category=category,
            contributions=contributions,
            heatmap_matrix=heatmap_matrix
        )
