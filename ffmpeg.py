import subprocess
from dataclasses import dataclass


type video = SVTAV1 | SVTAV1PSY | H265 | H264


@dataclass()
class SVTAV1PSY:
    crf_range: range = range(0, 50, 1)

    def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class SVTAV1:
    crf_range: range = range(0, 50, 1)

    def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class H264:
    crf_range: range = range(0, 40, 1)

    def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class H265:
    crf_range: range = range(0, 40, 1)

    def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class VP9:
    crf_range: range = range(0, 50, 1)

    def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class FfmpegCommand:
    input_filename: str
    codec_information: SVTAV1 | H264 | H265 | VP9
    ffmpeg_path: str = "ffmpeg"
    start_time_seconds: int = 0
    output_filename: str | None = None

    def run_ffmpeg_command(self) -> None:
        if self.output_filename is None:
            self.output_filename = f"OUTPUT - {self.input_filename}"

        _ = subprocess.run(
            [
                f"{self.ffmpeg_path}",
                f'-i "{self.input_filename}"',
                f'-ss "{self.start_time_seconds}"',
                *self.codec_information.to_subprocess_command(),
                f'"{self.output_filename}"',
            ]
        )
