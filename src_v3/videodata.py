from hashlib import sha256
from dataclasses import dataclass
from typing import Literal, override
import ffmpeg

# import ffmpeg_heuristics
from pathlib import Path
import subprocess
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
        self.raw_input_filename: Path = input_filename
        self.output_filename: Path = output_filename
        # self.vapoursynth_script: str = vapoursynth_script
        # self.vapoursynth_seek_method = vapoursynth_seek_method
        # self.crop_black_bars: bool = crop_black_bars

        # def __post_init__(self):
        with open(self.input_filename, "rb") as f:
            self.sha256_of_input = calculate_sha(f.read())

        if isinstance(vapoursynth_script, vapoursynth_data):
            if vapoursynth_script.crop_black_bars:
                vapoursynth_script.vapoursynth_script += f"\nclip = core.std.CropAbs(clip, {crop_black_bars_size(self.input_filename).split("=")[-1].replace(":",", ")})\n"

            self.input_filename = ffmpeg.accurate_seek(
                str(self.input_filename),
                str(self.input_filename),
                vapoursynth_script.vapoursynth_seek_method,
                extra_commands=vapoursynth_script.vapoursynth_script,
            )

    @override
    def __str__(self) -> str:
        return f"RawVideoData('{self.input_filename}', '{self.raw_input_filename}', '{self.output_filename}')"


# def crop_black_bars_size(input_video_data: videodata.RawVideoData) -> str:
def crop_black_bars_size(input_video: Path) -> str:
    # source_video_path_data = ffmpeg.get_video_metadata(input_video_data)

    try:
        # command = (
        #     f'cat "{input_video_data.input_filename}"'
        #     if isinstance(input_video_data.input_filename, Path)
        #     else f"{input_video_data.input_filename}"
        # )

        ffmpeg_output = subprocess.run(
            # f'ffmpeg -i <("{command}") -t 10 -vf cropdetect -f null -',
            f"ffmpeg -i {input_video} -t 10 -vf cropdetect -f null -",
            check=True,
            shell=True,
            capture_output=True,
        ).stderr.decode()
        # _ = input(ffmpeg_output.stdout.decode())
        # _ = input(ffmpeg_output.stderr.decode())
    except Exception as e:
        print("UNABLE TO FIND crop_black_bars_size DATA")
        raise e
    # if isinstance(input_video_data.input_filename, str)
    # else (
    #     input_video_data.vapoursynth_accurate_seek.command(
    #         None,
    #         round(source_video_path_data.frame_rate * 20),  # 20 seconds in
    #     )
    #     + "ffmpeg -i - -vf cropdetect -f null -"
    # )

    data = [x for x in ffmpeg_output.splitlines() if "crop=" in x][-1]

    # get the last data point? (does the crop size ever change?) --> Need to test
    return data.rsplit(maxsplit=1)[-1]
