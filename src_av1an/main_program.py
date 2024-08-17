# This is a simple program to make vapoursynth scripts used for Av1an

import time
import subprocess
from pathlib import Path
import os
from typing import Literal


def crop_black_bars_size(input_video: Path) -> str:
    try:
        ffmpeg_output = subprocess.run(
            f"ffmpeg -i {input_video} -t 10 -vf cropdetect -f null -",
            check=True,
            shell=True,
            capture_output=True,
        ).stderr.decode()
    except Exception as e:
        print("UNABLE TO FIND crop_black_bars_size DATA")
        raise e
    data = [x for x in ffmpeg_output.splitlines() if "crop=" in x][-1]
    return data.rsplit(maxsplit=1)[-1]


def make_vapoursynth_script(INPUT_FILE: Path, ACCURATE_SEEK_METHOD: str):
    vapoursynth_script: list[str] = [
        "import vapoursynth as vs",
        "core = vs.core",
        f"clip = core.{ACCURATE_SEEK_METHOD}.Source(source={INPUT_FILE})",
        # "clip = clip[::2]", # Half frame rate
        # "clip = core.fft3dfilter.FFT3DFilter(clip, sigma=1.5)",  # (Spatio-Temporal Denoisers)
        # "clip = core.f3kdb.Deband(clip)",  # (Banding Reduction)
    ]

    vapoursynth_script.append(
        f"\nclip = core.std.CropAbs(clip, {crop_black_bars_size(INPUT_FILE).split("=")[-1].replace(":", ", ")})\n"
    )

    # Last command
    vapoursynth_script.append("clip.set_output(0)")

    with open("seeking.vpy", "w") as f:
        _ = f.write("\n".join(vapoursynth_script))


def get_av1an_script(
    workers: int,
    target_quality: float,
    raw_command_video: str,
    ffmpeg_audio_command: str,
    output_file: Path,
    encoder: Literal[
        "aomenc",
        "rav1e",
        "svt-av1",
        "x265",
        "x264",
        "vpx",
    ],
    minimum_scene_len_frames: int,
    number_of_passes: Literal["1", "2"],
    ffmpeg_filter_options: str,
    pixel_format: str,
) -> str:
    if ffmpeg_filter_options != "":
        ffmpeg_filter_options = f'-f "{ffmpeg_filter_options}"'

    av1an_script: str = f'av1an -i seeking.vpy -e {encoder} -p {number_of_passes} {ffmpeg_filter_options} --pix-format {pixel_format} -v "{raw_command_video}" -w {workers} --target-quality {target_quality} -a {ffmpeg_audio_command} --min-scene-len {minimum_scene_len_frames} -l log_for_video --vmaf -r -o {output_file}'
    return av1an_script


def main():
    INPUT_FILE = Path()
    OUTPUT_FILE = Path()
    ACCURATE_SEEK_METHOD = "ffms2"

    make_vapoursynth_script(INPUT_FILE, ACCURATE_SEEK_METHOD)
    _ = os.system(
        get_av1an_script(
            workers=0,
            target_quality=93.5,
            raw_command_video="--rc 0 --crf 24 --preset 6 --input-depth 10 --tune 0 --film-grain 10 --film-grain-denoise 0 --lookahead 120 --keyint 240",  # SVTAV1
            ffmpeg_audio_command="-c:a libopus",
            output_file=OUTPUT_FILE,
            encoder="svt-av1",
            minimum_scene_len_frames=24,
            number_of_passes="1",
            ffmpeg_filter_options="",
            pixel_format="yuv420p10le",
        )
    )


if __name__ == "__main__":
    start = time.perf_counter()
    main()
    print(f"Elapsed time: {time.perf_counter() - start}")
