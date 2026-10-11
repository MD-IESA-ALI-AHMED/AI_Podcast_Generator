# Svara backend

FastAPI service that creates a two-host script with Gemini, synthesizes each
turn with Sarvam Bulbul v4 Flash, and returns an MP3. If
`background_music.mp3` is present in this directory, it is looped, lowered in
volume, faded, and mixed under the speech. Without a track, the service returns
the generated dialogue without music.

## Setup

From this directory, create the virtual environment and install dependencies
through its Python executable. This avoids invoking the separate `pip.exe`
launcher:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `.env` does not exist, copy `.env.example` to `.env`, then add your
`GEMINI_API_KEY`. The supplied Sarvam key is in this workspace's local `.env`,
which is ignored by Git. Optionally, place an MP3 named
`background_music.mp3` in this directory or set `BACKGROUND_MUSIC_PATH` in
`.env`.

Start the API with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The frontend sends `POST http://localhost:8000/generate` with
`{"text":"...","language_code":"en-IN"}`. The response is an `audio/mpeg` file.
`GET /health` is available as a simple readiness check. FFmpeg must be
installed and available on `PATH` for MP3 mixing and export.

The API supports the nine languages with Bulbul v4 Flash personas: English,
Hindi, Bengali, Gujarati, Kannada, Marathi, Punjabi, Tamil, and Telugu.

Run the focused backend checks from this directory with
`.\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
