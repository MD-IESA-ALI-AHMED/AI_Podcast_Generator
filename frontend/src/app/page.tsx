"use client";

import { ChangeEvent, FormEvent, useRef, useState } from "react";

type EpisodeResponse = {
  audio_url?: string;
  episode_url?: string;
  audio_base64?: string;
  audio_content_type?: string;
  title?: string;
  detail?: string;
  message?: string;
};

const languages = [
  { code: "en-IN", label: "English", native: "English" },
  { code: "hi-IN", label: "Hindi", native: "हिन्दी" },
  { code: "bn-IN", label: "Bengali", native: "বাংলা" },
  { code: "ta-IN", label: "Tamil", native: "தமிழ்" },
  { code: "te-IN", label: "Telugu", native: "తెలుగు" },
  { code: "kn-IN", label: "Kannada", native: "ಕನ್ನಡ" },
  { code: "mr-IN", label: "Marathi", native: "मराठी" },
  { code: "gu-IN", label: "Gujarati", native: "ગુજરાતી" },
  { code: "pa-IN", label: "Punjabi", native: "ਪੰਜਾਬੀ" },
];

function SparkleIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <path d="m12 2 1.7 6.3L20 10l-6.3 1.7L12 18l-1.7-6.3L4 10l6.3-1.7L12 2Z" />
      <path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" />
    </svg>
  );
}

function WaveIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 28 28" fill="none">
      <path d="M3 11v6M8 7v14m5-18v22m5-17v12m5-9v6m4-4v2" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4" />
    </svg>
  );
}

export default function Home() {
  const [text, setText] = useState("");
  const [language, setLanguage] = useState("en-IN");
  const [fileName, setFileName] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [episodeTitle, setEpisodeTitle] = useState("Your new episode");
  const fileInput = useRef<HTMLInputElement>(null);

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".txt")) {
      setError("Please choose a plain text (.txt) file.");
      event.target.value = "";
      return;
    }

    try {
      setText(await file.text());
      setFileName(file.name);
      setError("");
    } catch {
      setError("This text file could not be read. Please try another file.");
    }
    event.target.value = "";
  };

  const clearFile = () => {
    setFileName("");
    if (fileInput.current) fileInput.current.value = "";
  };

  const generateEpisode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!text.trim()) {
      setError("Add a topic or some source text to get started.");
      return;
    }

    setIsGenerating(true);
    setError("");
    setAudioUrl("");

    try {
      const apiBase = (
        process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
      ).replace(/\/$/, "");
      const response = await fetch(`${apiBase}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim(), language_code: language }),
      });

      if (!response.ok) {
        const body = await response.text();
        let message = body || `The server returned ${response.status}.`;
        try {
          const parsed = JSON.parse(body) as EpisodeResponse;
          message = parsed.detail || parsed.message || message;
        } catch {
          // Keep the server's plain-text error when its response is not JSON.
        }
        throw new Error(message);
      }

      const contentType = response.headers.get("content-type") ?? "";
      if (contentType.startsWith("audio/")) {
        setAudioUrl(URL.createObjectURL(await response.blob()));
        setEpisodeTitle("Your new episode");
        return;
      }

      const result = (await response.json()) as EpisodeResponse;
      setEpisodeTitle(result.title || "Your new episode");
      if (result.audio_base64) {
        const bytes = Uint8Array.from(atob(result.audio_base64), (char) =>
          char.charCodeAt(0),
        );
        const blob = new Blob([bytes], {
          type: result.audio_content_type || "audio/mpeg",
        });
        setAudioUrl(URL.createObjectURL(blob));
      } else if (result.audio_url || result.episode_url) {
        const url = result.audio_url || result.episode_url || "";
        setAudioUrl(
          url.startsWith("http://") || url.startsWith("https://")
            ? url
            : `${apiBase}${url.startsWith("/") ? "" : "/"}${url}`,
        );
      } else {
        throw new Error("The server completed the request but returned no audio.");
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Something went wrong while creating your episode.",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#" aria-label="Svara home">
          <span className="brand-mark">
            <WaveIcon />
          </span>
          <span>svara<span className="brand-period">.</span></span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <a className="nav-link nav-link-active" href="#create">
          <span className="nav-icon nav-create">✳</span>
          Create episode
        </a>
        <a className="nav-link" href="#how-it-works">
          <span className="nav-icon">◷</span>
          How it works
        </a>

        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <div className="note-icon"><SparkleIcon /></div>
            <p>Good ideas deserve<br />to be heard.</p>
            <span>Make something memorable.</span>
          </div>
          <div className="profile">
            <div className="profile-avatar">S</div>
            <div className="profile-copy">
              <strong>Your studio</strong>
              <span>Personal workspace</span>
            </div>
            <span className="profile-menu" aria-hidden="true">···</span>
          </div>
        </div>
      </aside>

      <section className="main-panel" id="create">
        <header className="topbar">
          <div className="breadcrumb">Studio <span>/</span> <strong>New episode</strong></div>
          <div className="status-pill"><span /> Studio is ready</div>
        </header>

        <div className="content-wrap">
          <div className="intro">
            <div className="eyebrow"><span /> YOUR IDEAS, IN CONVERSATION</div>
            <h1>Turn a thought into<br /><span>something you can hear.</span></h1>
            <p>Give us a topic, a note, or a little reading. We&apos;ll make it a two-host podcast worth listening to.</p>
          </div>

          <form className="creator-card" onSubmit={generateEpisode}>
            <div className="form-heading">
              <div>
                <span className="step-label">01 <span>—</span> THE STARTING POINT</span>
                <h2>What should we talk about?</h2>
              </div>
              <span className="private-label"><span /> PRIVATE</span>
            </div>

            <label className="sr-only" htmlFor="source-text">Topic or source text</label>
            <textarea
              id="source-text"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="A topic, an idea, or paste in something you’ve been reading..."
              rows={6}
              disabled={isGenerating}
            />
            <div className="input-meta">
              <div className="upload-row">
                <input
                  ref={fileInput}
                  className="sr-only"
                  type="file"
                  accept=".txt,text/plain"
                  onChange={handleFile}
                  aria-label="Upload a text file"
                />
                {fileName ? (
                  <span className="file-chip">
                    <span className="file-type">TXT</span>
                    {fileName}
                    <button type="button" onClick={clearFile} aria-label="Remove uploaded file">×</button>
                  </span>
                ) : (
                  <button
                    className="upload-button"
                    type="button"
                    onClick={() => fileInput.current?.click()}
                    disabled={isGenerating}
                  >
                    <UploadIcon />
                    <span>Add a text file</span>
                    <span className="file-hint">.TXT</span>
                  </button>
                )}
              </div>
              <span className="character-count">{text.length.toLocaleString()} characters</span>
            </div>

            <div className="form-divider" />

            <div className="options-row">
              <div className="language-field">
                <label htmlFor="language">EPISODE LANGUAGE</label>
                <div className="select-wrap">
                  <span className="language-globe" aria-hidden="true">◎</span>
                  <select
                    id="language"
                    value={language}
                    onChange={(event) => setLanguage(event.target.value)}
                    disabled={isGenerating}
                  >
                    {languages.map((option) => (
                      <option key={option.code} value={option.code}>
                        {option.label} · {option.native}
                      </option>
                    ))}
                  </select>
                  <span className="select-chevron" aria-hidden="true">⌄</span>
                </div>
              </div>
              <div className="host-preview">
                <div className="host-avatars" aria-hidden="true">
                  <span>A</span><span>M</span>
                </div>
                <span>Two hosts, one great conversation</span>
              </div>
            </div>

            {error && <p className="error-message" role="alert">{error}</p>}

            <button className="generate-button" type="submit" disabled={isGenerating || !text.trim()}>
              {isGenerating ? (
                <>
                  <span className="spinner" />
                  Making your episode...
                </>
              ) : (
                <>
                  <SparkleIcon />
                  Generate my podcast
                  <span className="button-arrow" aria-hidden="true">↗</span>
                </>
              )}
            </button>
            <p className="generate-caption">Usually ready in about a minute <span>·</span> No editing needed</p>
          </form>

          {audioUrl && (
            <section className="episode-card" aria-live="polite">
              <div className="episode-art"><WaveIcon /></div>
              <div className="episode-details">
                <span className="episode-kicker">YOUR EPISODE IS READY</span>
                <h2>{episodeTitle}</h2>
                <audio controls src={audioUrl}>Your browser does not support audio playback.</audio>
              </div>
              <a className="download-button" href={audioUrl} download="episode.mp3">
                Download <span aria-hidden="true">↓</span>
              </a>
            </section>
          )}

          <div className="footnote" id="how-it-works">
            <span className="footnote-sparkle"><SparkleIcon /></span>
            <span><strong>A little magic, a lot of listening.</strong> Your source becomes a lively script, voiced naturally in your chosen language.</span>
          </div>
        </div>
      </section>
    </main>
  );
}
