import subprocess
import os
from dataclasses import dataclass
from types import TracebackType
from typing import Literal


type video = SVTAV1 | H265 | H264
# TODO add VP9 support when I feel like it


# @dataclass()
# class SVTAV1PSY:
#     crf_range: range = range(0, 50, 1)
#     preset: int = 5
#
#     def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class SVTAV1:
    crf_value: int
    preset: int = 8

    # -svtav1-params film-grain=X, film-grain-denoise=0
    film_grain: None | tuple[int, bool] = (0, True)
    tune: Literal["subjective", "PSNR"] = "subjective"

    # const data
    ACCEPTED_CRF_RANGE: range = range(0, 63 + 1, 1)

    def to_subprocess_command(self) -> list[str]:
        # return [f"-crf {}", f"-preset {preset}"] + [f"-svtav1-params film-grain={film-grain[0]}"]
        command = ["-c:v libsvtav1", f"-preset {self.preset}", f"-crf {self.crf_value}"]

        if self.film_grain is not None:
            command.append(f"-svtav1-params film-grain={self.film_grain[0]}")
            command.append(f"film-grain-denoise={self.film_grain[1]}")

        command.append(f"-tune {["subjective", "PSNR"].index(self.tune)}")

        return command


@dataclass()
class H264:
    crf_range: range = range(0, 40, 1)
    preset: Literal[
        "ultrafast",
        "superfast",
        "veryfast",
        "faster",
        "fast",
        "medium",
        "slow",
        "slower",
        "veryslow",
    ] = "slower"
    tune: Literal[
        None,
        "film",
        "animation",
        "grain",
        "stillimage",
        "fastdecode",
        "zerolatency",
        "psnr",
        "ssim",
    ] = None

    def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class H265:
    crf_range: range = range(0, 40, 1)
    preset: Literal[
        "ultrafast",
        "superfast",
        "veryfast",
        "faster",
        "fast",
        "medium",
        "slow",
        "slower",
        "veryslow",
    ] = "slower"

    def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class VP9:
    crf_range: range = range(0, 50, 1)
    two_passes: bool = True

    def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class FfmpegCommand:
    input_filename: str
    codec_information: video
    output_filename: str | None = None

    start_time_seconds: int = 0
    end_time_seconds: int = 0

    crop_black_bars: bool = True
    bit_depth: Literal["yuv420p10le", "yuv420p"] = "yuv420p10le"
    keyframe_placement: int | None = 200
    ffmpeg_path: str = "ffmpeg"

    def __enter__(self):
        if self.output_filename is None:
            self.output_filename = f"OUTPUT - {self.input_filename}"

        # Separate audio from the video file
        _ = subprocess.run(
            [
                self.ffmpeg_path,
                f'-i "{self.input_filename}"',
                "-c:a copy",
                "-vn",
                f'"TEMP-{self.output_filename}.mkv"',  # storing audio only in mkv :woozy_face:
            ]
        )
        return self

    def run_ffmpeg_command(self) -> None:
        command: list[str] = [
            self.ffmpeg_path,
            f'-i "{self.input_filename}"',
            f'-ss "{self.start_time_seconds}"',
            *self.codec_information.to_subprocess_command(),
            f'"intermediate-{self.output_filename}"',
        ]

        if self.crop_black_bars:
            command.insert(-1, "-vf cropdetect")

        if self.keyframe_placement is not None:
            command.insert(-1, f"-g {self.keyframe_placement}")

        _ = subprocess.run(command)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        # recombine audio with the file
        _ = subprocess.run(
            [
                self.ffmpeg_path,
                f'-i "intermediate-{self.output_filename}"',
                "-c:a copy",
                "-vn",
                f"{self.output_filename}",
            ]
        )
        os.remove(f"intermediate-{self.output_filename}")
