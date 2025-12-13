"""
ML Model Registry for production model management.

This module handles:
- Model versioning and promotion to production
- Model metadata tracking
- Model storage and retrieval
- Rollback capabilities
"""

import os
import shutil
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import json

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    model_id: str
    version: str
    created_at: str
    model_type: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    training_samples: Optional[int] = None
    feature_count: Optional[int] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    is_production: bool = False


class MLModelRegistry:
    """
    Registry for managing ML models in production.

    Directory structure:
    models/
      ├── staging/              # Newly trained models
      │   ├── model_rf_20241212_123456.pkl
      │   └── metadata_rf_20241212_123456.json
      ├── production/           # Current production model
      │   ├── production_latest.pkl
      │   └── production_latest_metadata.json
      └── archive/              # Previous production models
          ├── production_v1.0.0.pkl
          └── production_v1.0.0_metadata.json
    """

    def __init__(self, base_path: str = "models"):
        self.base_path = Path(base_path)
        self.staging_dir = self.base_path / "staging"
        self.production_dir = self.base_path / "production"
        self.archive_dir = self.base_path / "archive"

        # Create directories
        for dir_path in [self.staging_dir, self.production_dir, self.archive_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Add .gitkeep to preserve empty directories
        for dir_path in [self.staging_dir, self.production_dir, self.archive_dir]:
            gitkeep = dir_path / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()

    def save_model(
        self,
        model: Any,
        model_id: str,
        metadata: ModelMetadata,
        to_production: bool = False
    ) -> Path:
        """
        Save a model to the registry.

        Args:
            model: The trained model object
            model_id: Unique identifier for the model
            metadata: Model metadata
            to_production: If True, save directly to production

        Returns:
            Path to the saved model file
        """
        target_dir = self.production_dir if to_production else self.staging_dir

        model_filename = f"{model_id}.pkl"
        metadata_filename = f"{model_id}_metadata.json"

        model_path = target_dir / model_filename
        metadata_path = target_dir / metadata_filename

        # Save model
        try:
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, indent=2)

            logger.info(f"Model saved: {model_path}")
            logger.info(f"Metadata saved: {metadata_path}")

            return model_path

        except Exception as e:
            logger.error(f"Failed to save model {model_id}: {e}")
            # Cleanup partial saves
            if model_path.exists():
                model_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            raise

    def promote_to_production(
        self,
        model_id: str,
        version: str = None
    ) -> bool:
        """
        Promote a staging model to production.

        This will:
        1. Archive current production model (if exists)
        2. Copy staging model to production
        3. Update metadata

        Args:
            model_id: ID of the staging model to promote
            version: Version string (defaults to timestamp)

        Returns:
            True if successful
        """
        staging_model = self.staging_dir / f"{model_id}.pkl"
        staging_metadata = self.staging_dir / f"{model_id}_metadata.json"

        if not staging_model.exists():
            logger.error(f"Staging model not found: {model_id}")
            return False

        # Generate version if not provided
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Archive current production model
        current_prod = self.production_dir / "production_latest.pkl"
        if current_prod.exists():
            archive_name = f"production_v{version}.pkl"
            archive_metadata_name = f"production_v{version}_metadata.json"

            shutil.copy(current_prod, self.archive_dir / archive_name)

            prod_metadata = self.production_dir / "production_latest_metadata.json"
            if prod_metadata.exists():
                shutil.copy(prod_metadata, self.archive_dir / archive_metadata_name)

            logger.info(f"Archived production model as: {archive_name}")

        # Promote staging to production
        try:
            # Copy model
            shutil.copy(staging_model, self.production_dir / "production_latest.pkl")

            # Update and copy metadata
            if staging_metadata.exists():
                with open(staging_metadata, 'r') as f:
                    metadata = json.load(f)

                metadata['is_production'] = True
                metadata['promoted_at'] = datetime.now().isoformat()
                metadata['version'] = version

                with open(self.production_dir / "production_latest_metadata.json", 'w') as f:
                    json.dump(metadata, f, indent=2)

            logger.info(f"✅ Model {model_id} promoted to production (v{version})")
            return True

        except Exception as e:
            logger.error(f"Failed to promote model {model_id}: {e}")
            return False

    def load_production_model(self) -> Optional[Any]:
        """Load the current production model."""
        model_path = self.production_dir / "production_latest.pkl"

        if not model_path.exists():
            logger.warning("No production model found")
            return None

        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"Loaded production model from: {model_path}")
            return model
        except Exception as e:
            logger.error(f"Failed to load production model: {e}")
            return None

    def load_model(self, model_id: str, from_archive: bool = False) -> Optional[Any]:
        """Load a specific model by ID."""
        if from_archive:
            model_path = self.archive_dir / f"{model_id}.pkl"
        else:
            # Try staging first, then production
            model_path = self.staging_dir / f"{model_id}.pkl"
            if not model_path.exists():
                model_path = self.production_dir / f"{model_id}.pkl"

        if not model_path.exists():
            logger.error(f"Model not found: {model_id}")
            return None

        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            return model
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            return None

    def get_production_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata for the current production model."""
        metadata_path = self.production_dir / "production_latest_metadata.json"

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load production metadata: {e}")
            return None

    def list_staging_models(self) -> list[str]:
        """List all models in staging."""
        models = []
        for file in self.staging_dir.glob("*.pkl"):
            if not file.name.startswith('.'):
                models.append(file.stem)
        return sorted(models)

    def list_archived_models(self) -> list[str]:
        """List all archived production models."""
        models = []
        for file in self.archive_dir.glob("production_v*.pkl"):
            models.append(file.stem)
        return sorted(models, reverse=True)  # Newest first

    def cleanup_old_staging(self, keep_last_n: int = 10) -> int:
        """
        Clean up old staging models, keeping only the last N.

        Returns:
            Number of models deleted
        """
        models = []
        for file in self.staging_dir.glob("*.pkl"):
            if not file.name.startswith('.'):
                models.append(file)

        # Sort by modification time (newest first)
        models.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        deleted = 0
        for model_file in models[keep_last_n:]:
            try:
                # Delete model and metadata
                model_file.unlink()
                metadata_file = model_file.with_suffix('.json')
                if metadata_file.exists():
                    metadata_file.unlink()
                deleted += 1
                logger.info(f"Deleted old staging model: {model_file.name}")
            except Exception as e:
                logger.error(f"Failed to delete {model_file}: {e}")

        return deleted


# Global registry instance
_registry: Optional[MLModelRegistry] = None


def get_model_registry() -> MLModelRegistry:
    """Get or create the global model registry instance."""
    global _registry
    if _registry is None:
        _registry = MLModelRegistry()
    return _registry
