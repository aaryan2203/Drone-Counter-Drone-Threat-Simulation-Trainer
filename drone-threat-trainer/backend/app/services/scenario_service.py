"""
Procedural Scenario Generator Service.
Generates randomized and reproducible training scenarios with configurable
environments, lighting, visibility, target counts, and difficulty levels (Section 8 & 9).
"""

import random
import time
from typing import Optional
from sqlalchemy.orm import Session

from ..database.models import Scenario
from ..schemas.schemas import ScenarioGenerateRequest


class ScenarioService:
    """Procedurally creates scenarios adhering to difficulty parameters."""

    ENVIRONMENTS = ["urban", "rural", "open_terrain", "industrial"]
    LIGHTING = ["day", "night", "low_light"]
    VISIBILITY = ["clear", "fog", "reduced"]

    DIFFICULTY_PRESETS = {
        "easy": {
            "environment": ["open_terrain", "rural"],
            "lighting": ["day"],
            "visibility": ["clear"],
            "object_count": (2, 3),
            "duration": 120
        },
        "medium": {
            "environment": ["urban", "rural"],
            "lighting": ["day", "low_light"],
            "visibility": ["clear", "fog"],
            "object_count": (3, 5),
            "duration": 180
        },
        "hard": {
            "environment": ["urban", "industrial"],
            "lighting": ["night", "low_light"],
            "visibility": ["reduced", "fog"],
            "object_count": (5, 8),
            "duration": 180
        },
        "expert": {
            "environment": ["urban", "industrial"],
            "lighting": ["night"],
            "visibility": ["reduced"],
            "object_count": (8, 12),
            "duration": 240
        }
    }

    @classmethod
    def generate_scenario(cls, db: Session, req: ScenarioGenerateRequest) -> Scenario:
        """Procedurally generates and persists a new training scenario."""
        seed = req.seed if req.seed is not None else random.randint(100000, 999999)
        rng = random.Random(seed)

        difficulty = req.difficulty.lower() if req.difficulty and req.difficulty.lower() in cls.DIFFICULTY_PRESETS else "medium"
        preset = cls.DIFFICULTY_PRESETS[difficulty]

        env = req.environment if req.environment in cls.ENVIRONMENTS else rng.choice(preset["environment"])
        lighting = req.lighting if req.lighting in cls.LIGHTING else rng.choice(preset["lighting"])
        visibility = req.visibility if req.visibility in cls.VISIBILITY else rng.choice(preset["visibility"])

        if req.object_count is not None:
            obj_count = req.object_count
        else:
            obj_count = rng.randint(preset["object_count"][0], preset["object_count"][1])

        duration = req.duration if req.duration is not None else preset["duration"]

        scenario_code = f"SCN_{seed % 100000:05d}"

        # Ensure unique scenario code in database
        existing = db.query(Scenario).filter(Scenario.scenario_code == scenario_code).first()
        if existing:
            scenario_code = f"SCN_{int(time.time() * 1000) % 100000:05d}"

        scenario = Scenario(
            scenario_code=scenario_code,
            environment=env,
            lighting=lighting,
            visibility=visibility,
            difficulty=difficulty,
            object_count=obj_count,
            seed=seed,
            duration=duration
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return scenario
