import os
from pathlib import Path
from dotenv import load_dotenv


def load_config() -> dict:
    load_dotenv()
    required = [
        "ANTHROPIC_API_KEY",
        "ELEVENLABS_API_KEY",
        "ELEVENLABS_VOICE_ID",
        "PEXELS_API_KEY",
        "PIXABAY_API_KEY",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your API keys."
        )
    return {
        "anthropic_api_key": os.environ["ANTHROPIC_API_KEY"],
        "elevenlabs_api_key": os.environ["ELEVENLABS_API_KEY"],
        "elevenlabs_voice_id": os.environ["ELEVENLABS_VOICE_ID"],
        "pexels_api_key": os.environ["PEXELS_API_KEY"],
        "pixabay_api_key": os.environ["PIXABAY_API_KEY"],
    }
