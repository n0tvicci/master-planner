import sys
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_root: Path = Path(__file__).parent.parent

    model_config = {
        "env_prefix": "YT_",
        "env_file": str(Path(__file__).parent.parent / ".env"),
    }


settings = Settings()

if str(settings.project_root) not in sys.path:
    sys.path.insert(0, str(settings.project_root))
