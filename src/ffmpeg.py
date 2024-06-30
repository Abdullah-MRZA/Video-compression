import subprocess
import ffmpeg_heuristics
from dataclasses import dataclass
from types import TracebackType
from typing import Literal
import os


type video = SVTAV1 | H265 | H264
# TODO add VP9 support when I feel like it
type bitdepth = Literal["yuv420p10le", "yuv420p"]


# @dataclass()
# class SVTAV1PSY:
#     crf_range: range = range(0, 50, 1)
#     preset: int = 5
#
#     def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class SVTAV1:
    # crf_value: int
    preset: int = 8

    # -svtav1-params film-grain=X, film-grain-denoise=0
    film_grain: None | tuple[int, bool] = None
    tune: Literal["subjective", "PSNR"] = "subjective"

    # const data
    ACCEPTED_CRF_RANGE: range = range(0, 63 + 1, 1)

    def to_subprocess_command(self) -> list[str]:
        # return [f"-crf {}", f"-preset {preset}"] + [f"-svtav1-params film-grain={film-grain[0]}"]
        command = [
            "-c:v libsvtav1",
            f"-preset {self.preset}",
        ]  # , f"-crf {self.crf_value}"]

        if self.film_grain is not None:
            command.append(f"-svtav1-params film-grain={self.film_grain[0]}")
            command.append(f"film-grain-denoise={self.film_grain[1]}")

        command.append(f"-svtav1-params tune={["subjective", "PSNR"].index(self.tune)}")

        return command


@dataclass()
class H264:
    ACCEPTED_CRF_RANGE: range = range(0, 40, 1)

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
    faststart: bool = True

    def to_subprocess_command(self) -> list[str]:
        command = [
            "-c:v libx264",
            f"-preset {self.preset}",
        ]

        if self.tune is not None:
            command.append(f"-tune {self.tune}")

        if self.faststart:
            command.append("-movflags +faststart")

        return command


@dataclass()
class H265:
    ACCEPTED_CRF_RANGE: range = range(0, 40, 1)
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

    def to_subprocess_command(self) -> list[str]:
        command = [
            "-c:v libx265",
            f"-preset {self.preset}",
        ]

        return command


# @dataclass()
# class VP9:
#     ACCEPTED_CRF_RANGE: range = range(0, 50, 1)
#     two_passes: bool = True
#
#     def to_subprocess_command(self) -> list[str]: ...


@dataclass()
class FfmpegCommand:
    input_filename: str
    codec_information: video

    start_time_seconds: str
    end_time_seconds: str

    output_filename: str
    ffmpeg_path: str

    crop_black_bars_size: str | None
    bit_depth: bitdepth
    keyframe_placement: int | None

    def __enter__(self):
        return self

    def run_ffmpeg_command(
        self, crf_value: int, override_output_file_name: str | None = None
    ) -> None:
        command: list[str] = [
            self.ffmpeg_path,
            "-hide_banner -loglevel error",
            f'-i "{self.input_filename}"',
            f"-ss {self.start_time_seconds}",  # -ss After is **very important** for accuracy!!
            f"-to {self.end_time_seconds}",
            *self.codec_information.to_subprocess_command(),
            "-an",
            f"-pix_fmt {self.bit_depth}",
            "-y",
            f"-crf {crf_value}",
            # f'"intermediate-{self.output_filename}"',
            f'"{self.output_filename}"'
            if override_output_file_name is None
            else override_output_file_name,
        ]

        if self.crop_black_bars_size is not None:
            command.insert(-1, f"-vf {self.crop_black_bars_size}")

        if self.keyframe_placement is not None:
            command.insert(-1, f"-g {self.keyframe_placement}")

        print(" ".join(command))
        # _ = os.system(" ".join(command))
        _ = subprocess.run(" ".join(command), shell=True, check=True)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        pass


def concatenate_video_files(
    list_of_video_files: list[str],
    output_filename_with_extension: str,
    ffmpeg_path: str,
):
    """
    NOTE THE CODEC OF THE VIDEO FILES MUST BE THE SAME!
    This combines the video files together
    """
    # New method using concat demuxer
    with open("video_list.txt", "w") as file:
        _ = file.write("\n".join(f"file '{x}'" for x in list_of_video_files))

    # _ = os.system(
    #     f'ffmpeg -f concat -safe 0 -i video_list.txt -c copy -y "{output_filename_with_extension}"'  # -hide_banner -loglevel error
    # )
    _ = subprocess.run(
        f'{ffmpeg_path} -f concat -safe 0 -i video_list.txt -c copy -y "{output_filename_with_extension}"',
        shell=True,
        check=True,
    )

    try:
        os.remove("video_list.txt")
    except FileNotFoundError:
        print("File Not found error: video_list.txt can't be deleted")
