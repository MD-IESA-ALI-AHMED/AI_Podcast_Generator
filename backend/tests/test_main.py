import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydub import AudioSegment
from pydantic import ValidationError

from app.main import LANGUAGES, GenerateRequest, PodcastLine, health, mix_episode


class PodcastBackendTests(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        self.assertEqual(health(), {"status": "ok"})

    def test_generation_rejects_language_without_a_v4_voice(self) -> None:
        with self.assertRaises(ValidationError):
            GenerateRequest.model_validate(
                {"text": "A podcast topic", "language_code": "ur-IN"}
            )

    def test_languages_have_two_v4_voices(self) -> None:
        self.assertEqual(len(LANGUAGES), 9)
        for language_code, (_, speakers) in LANGUAGES.items():
            self.assertEqual(len(speakers), 2, language_code)
            GenerateRequest(text="A short topic", language_code=language_code)

    def test_mixer_exports_an_episode_without_optional_music(self) -> None:
        lines = [
            PodcastLine(speaker="Host 1", text="Hello.", language_code="en-IN"),
            PodcastLine(speaker="Host 2", text="Welcome.", language_code="en-IN"),
        ]
        speech = AudioSegment.silent(duration=250)
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "episode.mp3"
            with patch(
                "app.main.synthesize_line",
                side_effect=[speech, speech],
            ):
                mix_episode(lines, "en-IN", output_path)

            self.assertTrue(output_path.is_file())
            self.assertGreater(len(AudioSegment.from_mp3(str(output_path))), 500)


if __name__ == "__main__":
    unittest.main()
