"""Safely transfer phone videos into the project upload workflow."""

from dataclasses import dataclass, field
import hashlib
import logging
from pathlib import Path
import tempfile

from src.settings import Settings


@dataclass
class CopyResult:
    """Outcomes for one confirmed or cancelled phone copy operation."""

    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    not_attempted: int = 0


class PhoneVideoImporter:
    """Copy videos from the connected phone into the project videos folder."""

    CHUNK_SIZE = 1024 * 1024

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger("phone_import")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        if not self.logger.handlers:
            log_dir = settings.project_root / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_dir / "phone_import.log", encoding="utf-8")
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self.logger.addHandler(handler)

    def _video_files(self, directory: Path) -> list[Path]:
        try:
            return sorted(
                path
                for path in directory.iterdir()
                if path.is_file()
                and path.name.lower().endswith(self.settings.allowed_extensions)
            )
        except OSError as error:
            print(f"Cannot scan {directory}: {error}")
            self.logger.error("Cannot scan %s: %s", directory, error)
            return []

    @staticmethod
    def _format_size(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{size} B"
            value /= 1024
        return f"{size} B"

    def _show_files(self, files: list[Path]) -> None:
        print("\nAvailable supported videos:")
        if not files:
            print("  None found.")
            return
        total_size = 0
        for path in files:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            total_size += size
            print(f"  {path.name} ({self._format_size(size)})")
        print(f"  {len(files)} file(s), {self._format_size(total_size)} total")

    def _select_files(self, files: list[Path]) -> tuple[list[Path], str] | None:
        print("\nCopy selection:")
        available_word = "file" if len(files) == 1 else "files"
        print(f"  a. All {len(files)} {available_word}")
        print(f"  1-{len(files)}. First N files (sorted by filename)")
        print("  q. Cancel")
        while True:
            try:
                choice = input("Choose all, enter a number, or q: ").strip().lower()
            except KeyboardInterrupt:
                print("\nCopy cancelled.")
                return None
            if choice in {"a", "all"}:
                return files, f"all {len(files)} {available_word}"
            if choice == "q":
                return None
            if choice.isdecimal() and 1 <= int(choice) <= len(files):
                count = int(choice)
                selected_word = "file" if count == 1 else "files"
                return files[:count], f"first {count} of {len(files)} {selected_word}"
            print(f"Enter a number from 1 to {len(files)}, a, or q.")

    def _confirm_copy(self, files: list[Path], selection: str) -> bool:
        total_size = sum(
            file_path.stat().st_size
            for file_path in files
            if file_path.exists()
        )
        print("\nCopy plan:")
        print(f"  Source:      {self.settings.phone_camera_videos_dir}")
        print(f"  Destination: {self.settings.project_root / 'videos'}")
        print(f"  Selection:   {selection}")
        print(f"  Selected:    {len(files)} file(s), {self._format_size(total_size)}")
        print("  Selected videos:")
        for file_path in files:
            print(f"    {file_path.name}")
        print("  Phone originals will remain unchanged.")
        try:
            return input("Copy these files now? (y/n): ").strip().lower() == "y"
        except KeyboardInterrupt:
            print("\nCopy cancelled.")
            return False

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source_file:
            while chunk := source_file.read(PhoneVideoImporter.CHUNK_SIZE):
                digest.update(chunk)
        return digest.hexdigest()

    def _copy_and_verify(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        expected_size = source.stat().st_size
        digest = hashlib.sha256()
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".partial",
                delete=False,
            ) as target_file:
                temp_path = Path(target_file.name)
                with source.open("rb") as source_file:
                    copied_size = 0
                    while chunk := source_file.read(self.CHUNK_SIZE):
                        target_file.write(chunk)
                        digest.update(chunk)
                        copied_size += len(chunk)
                        progress = (
                            100.0
                            if expected_size == 0
                            else copied_size / expected_size * 100
                        )
                        print(
                            f"\r  Copying {source.name}: {self._format_size(copied_size)}"
                            f" / {self._format_size(expected_size)} ({progress:.0f}%)",
                            end="",
                            flush=True,
                        )
            print()
            if copied_size != expected_size or self._sha256(temp_path) != digest.hexdigest():
                raise OSError("copied file did not pass size and SHA-256 verification")
            if destination.exists():
                raise FileExistsError(destination)
            temp_path.replace(destination)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _transfer(
        self, source: Path, destination: Path
    ) -> tuple[str, str]:
        try:
            if destination.exists():
                return "skipped", "destination already exists; source left unchanged"

            self._copy_and_verify(source, destination)
            return "succeeded", "copied and verified"
        except OSError as error:
            return "failed", str(error)

    def _copy_files(
        self,
        files: list[Path],
        destination_dir: Path,
    ) -> CopyResult:
        result = CopyResult()
        source_dir = self.settings.phone_camera_videos_dir
        print(f"\nSource folder:      {source_dir}")
        print(f"Destination folder: {destination_dir}")
        self._show_files(files)
        self.logger.info(
            "Found %s supported video(s) in %s for copy to %s",
            len(files),
            source_dir,
            destination_dir,
        )
        if not files:
            print("After: No supported videos to copy.")
            self.logger.info("Copy finished: no supported videos found")
            return result

        selection = self._select_files(files)
        if selection is None:
            result.not_attempted = len(files)
            print("After: Copy cancelled; no files copied.")
            self.logger.info("Copy cancelled")
            return result
        selected_files, selection_label = selection
        selected_names = ", ".join(file_path.name for file_path in selected_files)
        self.logger.info("Selected for copy (%s): %s", selection_label, selected_names)
        if not self._confirm_copy(selected_files, selection_label):
            result.not_attempted = len(selected_files)
            print("After: Copy cancelled; no files copied.")
            self.logger.info("Copy cancelled after selection: %s", selection_label)
            return result
        self.logger.info(
            "Copy started; selection=%s; selected=%s of %s",
            selection_label,
            len(selected_files),
            len(files),
        )

        for index, source in enumerate(selected_files, start=1):
            destination = destination_dir / source.name
            print(f"\n[{index}/{len(selected_files)}] {source.name}")
            try:
                outcome, detail = self._transfer(source, destination)
            except KeyboardInterrupt:
                result.not_attempted = len(selected_files) - index + 1
                print("\nCopy interrupted. Phone originals are unchanged.")
                self.logger.warning("Copy interrupted while processing %s", source)
                break
            if outcome == "succeeded":
                result.succeeded += 1
                self.logger.info("Copied %s -> %s (%s)", source, destination, detail)
                print(f"  {detail}.")
            elif outcome == "skipped":
                result.skipped += 1
                self.logger.warning("Skipped %s -> %s: %s", source, destination, detail)
                print(f"  Skipped: {detail}.")
            else:
                result.failed += 1
                self.logger.error("Failed %s -> %s: %s", source, destination, detail)
                print(f"  Failed: {detail}")

        print(
            f"After: Copy complete: {result.succeeded} copied, "
            f"{result.skipped} skipped, {result.failed} failed, "
            f"{result.not_attempted} not attempted."
        )
        self.logger.info(
            "Copy finished; succeeded=%s skipped=%s failed=%s not_attempted=%s",
            result.succeeded,
            result.skipped,
            result.failed,
            result.not_attempted,
        )
        return result

    def run(self) -> None:
        print("\nPhone video import")
        self.logger.info("Phone import started")
        try:
            phone_video_files = self._video_files(self.settings.phone_camera_videos_dir)
            self._copy_files(
                phone_video_files,
                self.settings.project_root / "videos",
            )
            self.logger.info("Phone import finished")
        finally:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
                handler.close()