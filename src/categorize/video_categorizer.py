"""Classify incoming videos by their effective display orientation."""

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from src.settings import Settings


@dataclass(frozen=True)
class VideoClassification:
    """Metadata and destination category for one incoming video."""

    file_path: Path
    width: int
    height: int
    rotation: int
    category: str


class VideoCategorizer:
    """Review and move videos placed directly in the project videos folder."""

    SHORTS_MAX_ASPECT_RATIO = 1.05

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.incoming_dir = settings.project_root / "videos"

    def _incoming_files(self) -> list[Path]:
        if not self.incoming_dir.exists():
            return []
        return sorted(
            file_path
            for file_path in self.incoming_dir.iterdir()
            if file_path.is_file()
            and file_path.name.lower().endswith(self.settings.allowed_extensions)
        )

    @staticmethod
    def _rotation(stream: dict[str, Any]) -> int:
        for side_data in stream.get("side_data_list", []):
            rotation = side_data.get("rotation")
            if rotation is not None:
                return int(round(float(rotation)))
        return 0

    def _probe(self, file_path: Path) -> VideoClassification:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise RuntimeError("ffprobe was not found on PATH.")

        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height:stream_side_data=rotation",
                "-of",
                "json",
                str(file_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        streams = payload.get("streams", [])
        if not streams:
            raise ValueError("no video stream found")

        stream = streams[0]
        width = int(stream["width"])
        height = int(stream["height"])
        rotation = self._rotation(stream)
        if abs(rotation) % 180 == 90:
            width, height = height, width

        category = (
            "shorts"
            if width / height <= self.SHORTS_MAX_ASPECT_RATIO
            else "landscape"
        )
        return VideoClassification(file_path, width, height, rotation, category)

    def _classify_files(self) -> tuple[list[VideoClassification], list[str]]:
        classifications = []
        errors = []
        for file_path in self._incoming_files():
            try:
                classifications.append(self._probe(file_path))
            except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
                errors.append(f"{file_path.name}: {error}")
        return classifications, errors

    @staticmethod
    def _print_review(classifications: list[VideoClassification]) -> None:
        print("\nVideo categorization preview:")
        for item in classifications:
            rotation = f", rotation {item.rotation} deg" if item.rotation else ""
            print(
                f"  {item.file_path.name}: {item.width}x{item.height}"
                f"{rotation} -> videos/{item.category}/"
            )

    def run(self) -> None:
        classifications, errors = self._classify_files()
        if not classifications and not errors:
            print("No video files found directly in videos/.")
            return

        self._print_review(classifications)
        if errors:
            print("\nCould not classify these files:")
            for error in errors:
                print(f"  {error}")
            print("No files were moved.")
            return

        destinations = [
            self.settings.video_dirs[item.category] / item.file_path.name
            for item in classifications
        ]
        collisions = [
            destination.name for destination in destinations if destination.exists()
        ]
        if collisions:
            print("\nDestination already exists for: " + ", ".join(collisions))
            print("No files were moved.")
            return

        confirm = input("Move these files to their categories? (y/n): ").strip().lower()
        if confirm != "y":
            print("Categorization cancelled.")
            return

        for item, destination in zip(classifications, destinations):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item.file_path), str(destination))
            print(f"Moved {item.file_path.name} -> videos/{item.category}/")