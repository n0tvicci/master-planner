from pathlib import Path
from elevenlabs import ElevenLabs, VoiceSettings
from backend.features.yt_shorts.models.voiceover import Voiceover


def generate_voiceover(
    text: str,
    api_key: str,
    voice_id: str,
    output_path: str,
) -> Voiceover:
    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.70,
            similarity_boost=0.82,
            style=0.37,
            use_speaker_boost=True,
        ),
        output_format="mp3_44100_192",
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in audio:
            if chunk:
                f.write(chunk)
    return Voiceover(audio_path=output_path)
