# Svara frontend

The Next.js app provides the podcast creator UI. It accepts a topic or pasted
source text, can read `.txt` files in the browser, and lets the user choose a
Sarvam language code.

## Run locally

```bash
npm install
npm run dev
```

The UI expects a FastAPI `POST /generate` endpoint. Set
`NEXT_PUBLIC_API_URL` in `.env.local` to the backend origin; it defaults to
`http://localhost:8000`.

Request JSON:

```json
{
  "text": "The source text or topic",
  "language_code": "en-IN"
}
```

The endpoint may return an audio file directly, or JSON containing `audio_url`
or `episode_url` (absolute or backend-relative). It can also return
`audio_base64`, with an optional `audio_content_type` and `title`.

Run `npm run lint` and `npm run build` to validate the frontend.
