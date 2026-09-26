"""Tests for the phone video import transfer stages."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from src.phone_import import PhoneVideoImporter
from src.settings import Settings


class PhoneVideoImporterTests(unittest.TestCase):
    def test_run_copies_video_and_leaves_phone_source_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            phone_videos = root / "phone" / "Camera_Videos"
            phone_videos.mkdir(parents=True)
            source = phone_videos / "holiday.mp4"
            source.write_bytes(b"phone video bytes")
            (phone_videos / "photo.jpg").write_bytes(b"not a video")

            settings = replace(
                Settings.from_project_root(root),
                phone_camera_videos_dir=phone_videos,
            )
            with patch("builtins.input", side_effect=["a", "y"]):
                PhoneVideoImporter(settings).run()

            self.assertTrue(source.exists())
            self.assertEqual(source.read_bytes(), b"phone video bytes")
            self.assertEqual(
                (root / "videos" / "holiday.mp4").read_bytes(), b"phone video bytes"
            )

    def test_run_copies_only_first_requested_number_of_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            phone_videos = root / "phone" / "Camera_Videos"
            phone_videos.mkdir(parents=True)
            for filename in ("01-first.mp4", "02-second.mp4", "03-third.mp4"):
                (phone_videos / filename).write_bytes(filename.encode())
            settings = replace(
                Settings.from_project_root(root),
                phone_camera_videos_dir=phone_videos,
            )
            output = StringIO()
            with patch("builtins.input", side_effect=["2", "y"]):
                with redirect_stdout(output):
                    PhoneVideoImporter(settings).run()

            project_videos = root / "videos"
            self.assertEqual(
                sorted(path.name for path in project_videos.iterdir()),
                ["01-first.mp4", "02-second.mp4"],
            )
            self.assertEqual(
                sorted(path.name for path in phone_videos.glob("*.mp4")),
                ["01-first.mp4", "02-second.mp4", "03-third.mp4"],
            )
            self.assertIn("Selection:   first 2 of 3 files", output.getvalue())
            self.assertIn("Source:      ", output.getvalue())
            self.assertIn("Destination: ", output.getvalue())
            self.assertIn("Selected videos:", output.getvalue())
            self.assertIn("01-first.mp4", output.getvalue())
            self.assertIn("02-second.mp4", output.getvalue())
            selected_listing = output.getvalue().split("Selected videos:\n", 1)[1]
            selected_listing = selected_listing.split("\n  Phone originals", 1)[0]
            self.assertNotIn("03-third.mp4", selected_listing)

    def test_conflicting_destination_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.mp4"
            destination = root / "destination.mp4"
            source.write_bytes(b"original")
            destination.write_bytes(b"different")
            importer = PhoneVideoImporter.__new__(PhoneVideoImporter)

            outcome, _ = importer._transfer(source, destination)

            self.assertEqual(outcome, "skipped")
            self.assertEqual(source.read_bytes(), b"original")
            self.assertEqual(destination.read_bytes(), b"different")

    def test_empty_source_does_not_prompt_for_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            phone_videos = root / "phone" / "Camera_Videos"
            phone_videos.mkdir(parents=True)
            settings = replace(
                Settings.from_project_root(root),
                phone_camera_videos_dir=phone_videos,
            )
            importer = PhoneVideoImporter(settings)

            with patch("builtins.input", side_effect=AssertionError("unexpected prompt")):
                importer._copy_files([], root / "videos")

            for handler in importer.logger.handlers[:]:
                importer.logger.removeHandler(handler)
                handler.close()


if __name__ == "__main__":
    unittest.main()