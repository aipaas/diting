import pickle
from typing import Any
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PicklePersistentMixin:
    """Mixin class to add pickle persistence functionality to repositories"""

    def __init__(self, pickle_file: str):
        self.pickle_file = Path(pickle_file)
        self.pickle_file.parent.mkdir(parents=True, exist_ok=True)

    def save_to_pickle(self, data: Any) -> None:
        """Save data to pickle file"""
        try:
            with open(self.pickle_file, "wb") as f:
                pickle.dump(data, f)
            logger.info(f"Data saved to {self.pickle_file}")
        except Exception as e:
            logger.error(f"Error saving to pickle file {self.pickle_file}: {e}")
            raise

    def load_from_pickle(self, default_value: Any = None) -> Any:
        """Load data from pickle file"""
        try:
            if self.pickle_file.exists():
                with open(self.pickle_file, "rb") as f:
                    data = pickle.load(f)
                logger.info(f"Data loaded from {self.pickle_file}")
                return data
            else:
                logger.info(
                    f"Pickle file {self.pickle_file} not found, using default value"
                )
                return default_value if default_value is not None else {}
        except Exception as e:
            logger.error(f"Error loading from pickle file {self.pickle_file}: {e}")
            logger.info("Using default value due to loading error")
            return default_value if default_value is not None else {}
