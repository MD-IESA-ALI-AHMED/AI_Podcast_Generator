import base64
import binascii
import logging
import os
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError, CouldntEncodeError
from starlette.background import BackgroundTask

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

logger = logging.getLogger("svara")
SARVAM_API_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_MODEL = "bulbul:v4-flash"
MAX_SCRIPT_LINES = 16

LANGUAGES = {
    "en-IN": ("English", ("simran_en_conversation", "shubh_en_narration")),
    "hi-IN": ("Hindi", ("kavya_hi_conversational", "amit_hi_conversational")),
    "bn-IN": ("Bengali", ("bappa_bn_conversation", "roopa_bn_conversational")),
    "gu-IN": ("Gujarati", ("bhavik_gu_conversation", "pooja_gu_conversational")),
    "kn-IN": ("Kannada", ("chaitra_kn_conversation", "chetan_kn_conversation")),
    "mr-IN": ("Marathi", ("nilesh_mr_conversation", "ishita_mr_conversational")),
    "pa-IN": ("Punjabi", ("anand_pa_conversation", "harpreet_pa_narration")),
    "ta-IN": ("Tamil", ("gokul_ta_narration", "vijay_ta_narration")),
    "te-IN": ("Telugu", ("pooja_te_conversation", "kavitha_te_conversation")),
}

LanguageCode = Literal[
    "en-IN",
    "hi-IN",
    "bn-IN",
    "gu-IN",
    "kn-IN",
    "mr-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
]


class GenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    language_code: LanguageCode


class PodcastLine(BaseModel):
    speaker: Literal["Host 1", "Host 2"]
    text: str = Field(min_length=1, max_length=1200)
    language_code: str


app = FastAPI(title="Svara Podcast API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def create_script(source_text: str, language_code: str) -> list[PodcastLine]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is missing. Add it to backend/.env.",
        )

    language_name = LANGUAGES[language_code][0]
    prompt = (
        f"Create a lively but accurate podcast conversation between Host 1 and Host 2 "
        f"based only on the source below. Write every spoken line in {language_name} "
        f"({language_code}) using its native writing system, never transliteration. "
        "Return 8 to 12 concise alternating turns as a raw JSON array. Every item must "
        'have exactly these fields: "speaker" (Host 1 or Host 2), "text", and '
        f'"language_code" (exactly "{language_code}"). Keep each text under 1200 '
        "characters, conversational and natural for audio. Do not add markdown.\n\n"
        f"Source:\n{source_text.strip()}"
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[PodcastLine],
                temperature=0.7,
            ),
        )
    except errors.APIError as error:
        logger.exception("Gemini script generation failed")
        raise HTTPException(
            status_code=502, detail="Gemini could not generate the podcast script."
        ) from error

    if not response.text:
        raise HTTPException(status_code=502, detail="Gemini returned an empty script.")

    try:
        lines = TypeAdapter(list[PodcastLine]).validate_json(response.text)
    except (ValidationError, ValueError) as error:
        logger.exception("Gemini returned an invalid podcast script")
        raise HTTPException(
            status_code=502, detail="Gemini returned an invalid podcast script."
        ) from error

    if not 2 <= len(lines) <= MAX_SCRIPT_LINES:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini must return between 2 and {MAX_SCRIPT_LINES} dialogue lines.",
        )
    if any(line.language_code != language_code for line in lines):
        raise HTTPException(
            status_code=502,
            detail="Gemini returned a script with an unexpected language code.",
        )
    return lines


def synthesize_line(line: PodcastLine, language_code: str) -> AudioSegment:
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="SARVAM_API_KEY is missing. Add it to backend/.env.",
        )

    speaker_index = 0 if line.speaker == "Host 1" else 1
    speaker = LANGUAGES[language_code][1][speaker_index]
    try:
        response = requests.post(
            SARVAM_API_URL,
            headers={
                "api-subscription-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "text": line.text,
                "language_code": language_code,
                "model": SARVAM_MODEL,
                "speaker": speaker,
                "output_audio_codec": "wav",
            },
            timeout=(10, 90),
        )
        response.raise_for_status()
    except requests.RequestException as error:
        logger.exception("Sarvam text-to-speech request failed")
        raise HTTPException(
            status_code=502,
            detail="Sarvam could not synthesize a dialogue line. Check the API key and try again.",
        ) from error

    try:
        result = response.json()
        audio_data = base64.b64decode(result["audios"][0], validate=True)
        if not audio_data:
            raise ValueError("Sarvam returned empty audio.")
        return AudioSegment.from_file(BytesIO(audio_data), format="wav")
    except (ValueError, KeyError, IndexError, TypeError, binascii.Error, CouldntDecodeError) as error:
        logger.exception("Sarvam returned an invalid audio response")
        raise HTTPException(
            status_code=502, detail="Sarvam returned an invalid audio response."
        ) from error


def mix_episode(lines: list[PodcastLine], language_code: str, output_path: Path) -> None:
    dialogue = AudioSegment.empty()
    silence = AudioSegment.silent(duration=600)
    for index, line in enumerate(lines):
        dialogue += synthesize_line(line, language_code)
        if index < len(lines) - 1:
            dialogue += silence

    configured_music = os.getenv("BACKGROUND_MUSIC_PATH")
    music_path = Path(configured_music) if configured_music else BACKEND_DIR / "background_music.mp3"
    if configured_music and not music_path.is_absolute():
        music_path = BACKEND_DIR / music_path
    if configured_music and not music_path.is_file():
        raise HTTPException(
            status_code=500,
            detail=f"Background music file was not found: {music_path}",
        )

    if music_path.is_file():
        try:
            music = AudioSegment.from_mp3(str(music_path))
        except (CouldntDecodeError, CouldntEncodeError, OSError) as error:
            logger.exception("Background music could not be loaded")
            raise HTTPException(
                status_code=500, detail="The configured background music could not be loaded."
            ) from error
        if len(music) == 0:
            raise HTTPException(status_code=500, detail="The background music file is empty.")
        while len(music) < len(dialogue):
            music += music
        music = music[: len(dialogue)].apply_gain(-18)
        music = music.fade_in(min(1000, len(music) // 2))
        music = music.fade_out(min(1500, len(music) // 2))
        episode = music.overlay(dialogue)
    else:
        episode = dialogue

    try:
        with episode.export(str(output_path), format="mp3", bitrate="192k"):
            pass
    except (CouldntDecodeError, OSError) as error:
        logger.exception("Final podcast audio could not be exported")
        raise HTTPException(
            status_code=500,
            detail="Could not export the episode. Check that FFmpeg is installed.",
        ) from error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate")
def generate_episode(request: GenerateRequest) -> FileResponse:
    source_text = request.text.strip()
    if not source_text:
        raise HTTPException(status_code=422, detail="Enter a topic or source text.")
    if not os.getenv("SARVAM_API_KEY", "").strip():
        raise HTTPException(
            status_code=500,
            detail="SARVAM_API_KEY is missing. Add it to backend/.env.",
        )

    lines = create_script(source_text, request.language_code)
    temp_dir = Path(tempfile.mkdtemp(prefix="svara-episode-"))
    episode_path = temp_dir / "episode.mp3"
    try:
        mix_episode(lines, request.language_code, episode_path)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return FileResponse(
        episode_path,
        media_type="audio/mpeg",
        filename="episode.mp3",
        background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
    )
