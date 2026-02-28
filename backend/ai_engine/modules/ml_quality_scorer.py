"""ml_quality_scorer — backward-compatible stub. Real code lives in scoring.py."""
from ai_engine.modules.scoring import (  # noqa: F401
    extract_features, train_model, predict_quality,
    get_model_info, _load_model,
    MODEL_DIR, MODEL_PATH, META_PATH, MIN_TRAINING_SAMPLES,
)
