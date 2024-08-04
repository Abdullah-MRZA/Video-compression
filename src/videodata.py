from hashlib import sha256
from dataclasses import dataclass
from typing import Literal, override
import ffmpeg

# import ffmpeg_heuristics
from pathlib import Path
import os


def calculate_sha(text: str | bytes) -> str:
    if isinstance(text, str):
        sha_value = sha256(text.encode()).hexdigest()
    else:
        sha_value = sha256(text).hexdigest()
    return sha_value


@dataclass
class vapoursynth_data:
    vapoursynth_script: str
    vapoursynth_seek_method: Literal["ffms2", "bs"]
    crop_black_bars: bool = True


type input_file_type = Path | ffmpeg.accurate_seek


class RawVideoData:
    def __init__(
        self,
        input_filename: Path,
        output_filename: Path,
        vapoursynth_script: vapoursynth_data | None,
    ) -> None:
        # vapoursynth_seek: ffmpeg.accurate_seek | None = None
        # sha256_of_input: str | None = None

        assert os.path.isfile(
            input_filename
        ), f"CRITICAL ERROR: {input_filename} Does Not Exist!!"

        self.input_filename: Path | ffmpeg.accurate_seek = input_filename
        self.raw_input_filename: Path | ffmpeg.accurate_seek = input_filename
        self.output_filename: Path = output_filename
        # self.vapoursynth_script: str = vapoursynth_script
        # self.vapoursynth_seek_method = vapoursynth_seek_method
        # self.crop_black_bars: bool = crop_black_bars

        # def __post_init__(self):
        with open(self.input_filename, "rb") as f:
            self.sha256_of_input = calculate_sha(f.read())

        if isinstance(vapoursynth_script, vapoursynth_data):
            # if vapoursynth_data.crop_black_bars:
            #     vapoursynth_data.vapoursynth_script += f"\nclip = core.std.CropAbs(clip, {ffmpeg_heuristics.crop_black_bars_size(str(self.input_filename)).split("=")[-1].replace(":",", ")})\n"

            self.input_filename = ffmpeg.accurate_seek(
                str(self.input_filename),
                str(self.input_filename),
                vapoursynth_script.vapoursynth_seek_method,
                extra_commands=vapoursynth_script.vapoursynth_script,
            )

    @override
    def __str__(self) -> str:
        return f"RawVideoData('{self.input_filename}', '{self.raw_input_filename}', '{self.output_filename}')"
