import subprocess

# from typing_extensions import override
import file_cache

# import ffmpeg_heuristics
# from textwrap import dedent
import textwrap

# from dataclasses import dataclass
import dataclasses

# from typing import Literal
import typing
import json
import os
# from rich.traceback import install

# import v2_target_videoCRF

# from pathlib import Path
import pathlib

import videodata
# from types import TracebackType

# _ = install(show_locals=True)


type VideoCodec = SVTAV1 | H264 | H265 | APPLE_HWENC_H265
# type VideoCodec = SVTAV1 | H264 | H265

"""
there's also "process substitution" in many shells, roughly: `cat input | ffmpeg -i - … - | do_more`
is the same as `ffmpeg -i <(cat some_file) >(do_more)`,
but the <(…) or >(…) can be repeated as
necessary. Upside: no manual creation/cleanup. Downside: unreadable unless you code
generate… at which point named pipes are also on the table.
"""


@dataclasses.dataclass()
class SVTAV1PSY:
    preset: int = 8
    tune: typing.Literal["2", "3"] = "2"

    @dataclasses.dataclass()
    class Filmgrain:
        film_grain: int
        film_grain_denoise: bool

    film_grain: None | Filmgrain = None
    bitdepth: typing.Literal["yuv420p", "yuv420p10le"] = "yuv420p10le"

    ACCEPTED_CRF_RANGE: range = range(0, 63 + 1, 1)
    NAME = "SVTAV1-PSY"
    BETTER_QUALITY = -1

    # BUG: TODO complete these functions
    def to_subprocess_command(self, crf: int) -> list[str]:
        command = [
            "-c:v libsvtav1",
            f"-preset {self.preset}",
            f"-pix_fmt {self.bitdepth}",
            f"-crf {crf}",
        ]

        if self.film_grain is not None:
            command.append(f"-svtav1-params film-grain={self.film_grain.film_grain}")
            command.append(f"film-grain-denoise={self.film_grain.film_grain_denoise}")

        command.append(f"-svtav1-params tune={["subjective", "PSNR"].index(self.tune)}")

        return command

    # TODO: pipe into standalone encoder
    def output_file(self, output_filename: str) -> str:
        return f'"{output_filename}"'


@dataclasses.dataclass()
class SVTAV1:
    preset: int = 8
    tune: typing.Literal["subjective", "PSNR"] = "subjective"

    @dataclasses.dataclass()
    class Filmgrain:
        film_grain: int
        film_grain_denoise: bool

    film_grain: None | Filmgrain = None
    bitdepth: typing.Literal["yuv420p", "yuv420p10le"] = "yuv420p10le"

    ACCEPTED_CRF_RANGE: range = range(0, 63 + 1, 1)
    NAME = "SVTAV1"
    BETTER_QUALITY = -1

    def to_subprocess_command(self, crf: int) -> list[str]:
        command = [
            "-c:v libsvtav1",
            f"-preset {self.preset}",
            f"-pix_fmt {self.bitdepth}",
            f"-crf {crf}",
        ]

        if self.film_grain is not None:
            command.append(f"-svtav1-params film-grain={self.film_grain.film_grain}")
            command.append(f"film-grain-denoise={self.film_grain.film_grain_denoise}")

        command.append(f"-svtav1-params tune={["subjective", "PSNR"].index(self.tune)}")

        return command

    def output_file(self, output_filename: str) -> str:
        return f'"{output_filename}"'


@dataclasses.dataclass()
class H264:
    ACCEPTED_CRF_RANGE: range = range(0, 51 + 1, 1)
    NAME = "H264"
    BETTER_QUALITY = -1

    preset: typing.Literal[
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
    tune: typing.Literal[
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
    faststart: bool = False  # does this get translated to final file?

    bitdepth: typing.Literal[
        "yuv420p",
        "yuvj420p",
        "yuv422p",
        "yuvj422p",
        "yuv444p",
        "yuvj444p",
        "nv12",
        "nv16",
        "nv21",
        "yuv420p10le",
        "yuv422p10le",
        "yuv444p10le",
        "nv20le",
        "gray",
        "gray10le",
    ] = "yuv420p10le"

    def to_subprocess_command(self, crf: int) -> list[str]:
        command = [
            "-c:v libx264",
            f"-preset {self.preset}",
            f"-pix_fmt {self.bitdepth}",
            f"-crf {crf}",
        ]

        if self.tune is not None:
            command.append(f"-tune {self.tune}")

        if self.faststart:
            command.append("-movflags +faststart")

        return command

    def output_file(self, output_filename: str) -> str:
        return f'"{output_filename}"'


@dataclasses.dataclass()
class H265:
    ACCEPTED_CRF_RANGE: range = range(0, 51 + 1, 1)
    NAME = "H265"
    BETTER_QUALITY = -1

    preset: typing.Literal[
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

    bitdepth: typing.Literal[
        "yuv420p",
        "yuvj420p",
        "yuv422p",
        "yuvj422p",
        "yuv444p",
        "yuvj444p",
        "gbrp",
        "yuv420p10le",
        "yuv422p10le",
        "yuv444p10le",
        "gbrp10le",
        "yuv420p12le",
        "yuv422p12le",
        "yuv444p12le",
        "gbrp12le",
        "gray",
        "gray10le",
        "gray12le",
    ] = "yuv420p10le"

    def to_subprocess_command(self, crf: int) -> list[str]:
        command = [
            "-c:v libx265",
            f"-preset {self.preset}",
            f"-pix_fmt {self.bitdepth}",
            f"-crf {crf}",
        ]

        return command

    def output_file(self, output_filename: str) -> str:
        return f'"{output_filename}"'


@dataclasses.dataclass()
class APPLE_HWENC_H265:  # BUG: Faulty concatenation of video files --> unusable
    ACCEPTED_CRF_RANGE: range = range(-100, 0 + 1, 1)
    # ACCEPTED_CRF_RANGE: range = range(0, 100 + 1, 1)
    NAME = "APPLE HWENC H265"
    BETTER_QUALITY = 1

    bitdepth: typing.Literal[
        "videotoolbox_vld",
        "nv12",
        "yuv420p",
        "bgra",
        "p010le",
    ] = "p010le"

    make_apple_standard: bool = True

    def to_subprocess_command(self, crf: int) -> list[str]:
        command = [
            "-c:v hevc_videotoolbox",
            f"-pix_fmt {self.bitdepth}",
            f"-q:v {-crf}",
            # f"-q:v {max(self.ACCEPTED_CRF_RANGE) - crf}",
        ]

        if self.make_apple_standard:
            command.append("-tag:v hvc1")

        return command

    def output_file(self, output_filename: str) -> str:
        return f'"{output_filename}"'


class accurate_seek:
    def __init__(
        self,
        video_filename_with_extension: str,
        filename_vpy_without_extension: str,
        accurate_seek_method: typing.Literal["ffms2", "bs"],
        # video: v2_target_videoCRF.RawVideoData
        extra_commands: str = "",
    ) -> None:
        self.filename_of_vpy = f"{filename_vpy_without_extension.replace('.', '')}.vpy"
        with open(self.filename_of_vpy, "w") as f:
            text = textwrap.dedent(f"""
                import vapoursynth as vs
                core = vs.core
                clip = core.{accurate_seek_method}.Source(source="{video_filename_with_extension}")
            """)
            text += extra_commands
            text += "\nclip.set_output(0)"
            _ = f.write(text)

    def command(self, start_frame: int | None, end_frame: int | None) -> str:
        start = (
            f"-s {start_frame}"
            if (start_frame is not None and start_frame != 0)
            else ""
        )
        end = f"-e {end_frame - 1}" if end_frame is not None else ""
        return f"vspipe {start} {end} -c y4m {self.filename_of_vpy} -"

    # @override  # INFO: CHECK IF THIS IS GOOD
    @typing.override
    def __str__(self) -> str:
        return self.command(None, None)

    def __exit__(self):
        try:
            os.remove(self.filename_of_vpy)
        except Exception as _:
            print(f"WARNING: Unable to delete file: {self.filename_of_vpy}")


def run_ffmpeg_command(
    # video data
    input_file: videodata.RawVideoData,
    output_file: pathlib.Path | None,
    # CRF used
    crf_value: int,
    # compression data
    codec_information: VideoCodec,
    start_frame: int,
    end_frame: int,
    # crop_black_bars: bool,
    keyframe_placement: int | None,
    # input_file_script_seeking: accurate_seek,
) -> None | str:
    framerate: float = get_video_metadata(
        input_file, input_file.input_filename
    ).frame_rate
    command: list[str] = []

    assert isinstance(
        input_file.input_filename, accurate_seek
    ), "Can't use 'run_ffmpeg_command' with without full data (must be accurate_seek, not Path)"

    command.append(input_file.input_filename.command(start_frame, end_frame))

    command.extend(
        [
            "| ffmpeg",
            "-hide_banner -loglevel error",
            f"-r {framerate}",
        ]
    )

    command.append("-i -")

    command.extend(
        [
            *codec_information.to_subprocess_command(crf_value),
            "-an",
            "-y",
        ]
    )

    if keyframe_placement is not None:
        command.append(f"-g {keyframe_placement}")

    if output_file is None:
        command.append("-f matroska -")
        return " ".join(command)

    command.append(codec_information.output_file(str(output_file)))

    print("FFMPEG COMMAND --> " + " ".join(command))
    _ = subprocess.run(" ".join(command), shell=True, check=True)


def concatenate_video_files(
    list_of_video_files: list[pathlib.Path],
    output_filename_with_extension: pathlib.Path,
):
    """
    NOTE THE CODEC OF THE VIDEO FILES MUST BE THE SAME!
    This combines the video files together
    """
    with open("video_list.txt", "w") as file:
        _ = file.write("\n".join(f"file '{x}'" for x in list_of_video_files))

    print(
        f'RUNNING COMMAND: ffmpeg -f concat -i video_list.txt -c copy -y "{output_filename_with_extension.name}"'
    )
    _ = subprocess.run(
        f'ffmpeg -f concat -i video_list.txt -c copy -y "{output_filename_with_extension.name}"',
        shell=True,
        check=True,
    )

    try:
        os.remove("video_list.txt")
    except FileNotFoundError:
        print("File Not found error: video_list.txt can't be deleted")


@dataclasses.dataclass()
class VideoMetadata:
    file_name: str
    width: int
    height: int
    # frame rate info
    frame_rate: float
    total_frames: int
    # pixel info
    pix_fmt: str
    codec: str  # change to codec?
    # timings
    start_time: float
    duration: float
    # other data
    contains_audio: bool
    file_size: int
    # bitrate: int
    # is_HDR: bool


# BUG: this function needs porting over (haven't done yet because cyclic import needs fixing)
@file_cache.cache()
def get_video_metadata(
    # filename: str,
    # input_file_vapoursynth: accurate_seek | str,
    video_data: videodata.RawVideoData,
    video_for_metadata: pathlib.Path | accurate_seek,
) -> VideoMetadata:
    def make_video_metadata(json_data: dict[str, dict]) -> VideoMetadata:
        first_stream_with_video: dict[str, str | int] = [
            x for x in json_data["streams"] if x["codec_type"] == "video"
        ][0]

        # from rich import print
        #
        # print(first_stream_with_video)

        try:
            duration = float(json_data["format"]["duration"])
        except Exception:
            duration = float(first_stream_with_video["duration"])

        return VideoMetadata(
            file_name=json_data["format"]["filename"],  # same as `filename`...
            width=int(first_stream_with_video["width"]),
            height=int(first_stream_with_video["height"]),
            frame_rate=float(eval(first_stream_with_video["r_frame_rate"])),
            total_frames=int(first_stream_with_video["nb_read_frames"]),
            pix_fmt=first_stream_with_video["pix_fmt"],
            codec=first_stream_with_video["codec_name"],
            start_time=float(json_data["format"]["start_time"]),
            # duration=float(json_data["format"]["duration"]),
            # duration=float(first_stream_with_video["duration"]),
            duration=duration,
            contains_audio=any(
                True for x in json_data["streams"] if x["codec_type"] == "audio"
            ),
            file_size=int(json_data["format"]["size"]),
            # bitrate=int(json_data["format"]["bit_rate"]),
        )

    assert isinstance(video_data, videodata.RawVideoData), "video_data is incorrect"

    assert isinstance(video_for_metadata, accurate_seek) or isinstance(
        video_for_metadata, pathlib.Path
    ), "INCORRECT INPUT DATA"

    # command = video_data.input_filename
    if isinstance(video_for_metadata, accurate_seek):
        command = f"{video_for_metadata.command(None, None)}"
    # elif isinstance(command, Path):
    else:
        command = f'cat "{video_for_metadata}"'

    data = subprocess.run(
        f"zsh -c 'ffprobe -v quiet -print_format json -show_format -show_streams -count_frames <({command})'",
        # if isinstance(input_file_vapoursynth, str)
        # else f"{input_file_vapoursynth.command(None, None)} ffprobe -v quiet -print_format json -show_format -show_streams -count_frames -",
        check=True,
        shell=True,
        capture_output=True,
    ).stdout.decode()

    json_data: dict = json.loads(data)
    # print("json data")
    # print(json_data)

    return make_video_metadata(json_data)


# {
#    "streams": [
#        {
#            "index": 0,
#            "codec_name": "h264",
#            "codec_long_name": "H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
#            "profile": "High",
#            "codec_type": "video",
#            "codec_tag_string": "avc1",
#            "codec_tag": "0x31637661",
#            "width": 1816,
#            "height": 1080,
#            "coded_width": 1816,
#            "coded_height": 1080,
#            "closed_captions": 0,
#            "film_grain": 0,
#            "has_b_frames": 1,
#            "sample_aspect_ratio": "1:1",
#            "display_aspect_ratio": "227:135",
#            "pix_fmt": "yuv420p",
#            "level": 40,
#            "color_range": "tv",
#            "color_space": "bt709",
#            "color_transfer": "bt709",
#            "color_primaries": "bt709",
#            "chroma_location": "left",
#            "field_order": "progressive",
#            "refs": 1,
#            "is_avc": "true",
#            "nal_length_size": "4",
#            "id": "0x1",
#            "r_frame_rate": "24000/1001",
#            "avg_frame_rate": "24000/1001",
#            "time_base": "1/24000",
#            "start_pts": 0,
#            "start_time": "0.000000",
#            "duration_ts": 721152,
#            "duration": "30.048000",
#            "bit_rate": "748023",
#            "bits_per_raw_sample": "8",
#            "nb_frames": "751",
#            "extradata_size": 44,
#            "disposition": {
#                "default": 1,
#                "dub": 0,
#                "original": 0,
#                "comment": 0,
#                "lyrics": 0,
#                "karaoke": 0,
#                "forced": 0,
#                "hearing_impaired": 0,
#                "visual_impaired": 0,
#                "clean_effects": 0,
#                "attached_pic": 0,
#                "timed_thumbnails": 0,
#                "non_diegetic": 0,
#                "captions": 0,
#                "descriptions": 0,
#                "metadata": 0,
#                "dependent": 0,
#                "still_image": 0
#            },
#            "tags": {
#                "language": "und",
#                "handler_name": "ISO Media file produced by Google Inc.",
#                "vendor_id": "[0][0][0][0]"
#            }
#        },
#        {
#            "index": 1,
#            "codec_name": "aac",
#            "codec_long_name": "AAC (Advanced Audio Coding)",
#            "profile": "LC",
#            "codec_type": "audio",
#            "codec_tag_string": "mp4a",
#            "codec_tag": "0x6134706d",
#            "sample_fmt": "fltp",
#            "sample_rate": "44100",
#            "channels": 2,
#            "channel_layout": "stereo",
#            "bits_per_sample": 0,
#            "initial_padding": 0,
#            "id": "0x2",
#            "r_frame_rate": "0/0",
#            "avg_frame_rate": "0/0",
#            "time_base": "1/44100",
#            "start_pts": 0,
#            "start_time": "0.000000",
#            "duration_ts": 1323000,
#            "duration": "30.000000",
#            "bit_rate": "128036",
#            "nb_frames": "1349",
#            "extradata_size": 16,
#            "disposition": {
#                "default": 1,
#                "dub": 0,
#                "original": 0,
#                "comment": 0,
#                "lyrics": 0,
#                "karaoke": 0,
#                "forced": 0,
#                "hearing_impaired": 0,
#                "visual_impaired": 0,
#                "clean_effects": 0,
#                "attached_pic": 0,
#                "timed_thumbnails": 0,
#                "non_diegetic": 0,
#                "captions": 0,
#                "descriptions": 0,
#                "metadata": 0,
#                "dependent": 0,
#                "still_image": 0
#            },
#            "tags": {
#                "language": "eng",
#                "handler_name": "ISO Media file produced by Google Inc.",
#                "vendor_id": "[0][0][0][0]"
#            }
#        }
#    ],
#    "format": {
#        "filename": "short.mp4",
#        "nb_streams": 2,
#        "nb_programs": 0,
#        "nb_stream_groups": 0,
#        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
#        "format_long_name": "QuickTime / MOV",
#        "start_time": "0.000000",
#        "duration": "30.048000",
#        "size": "3454463",
#        "bit_rate": "919718",
#        "probe_score": 100,
#        "tags": {
#            "major_brand": "isom",
#            "minor_version": "512",
#            "compatible_brands": "isomiso2avc1mp41",
#            "encoder": "Lavf61.1.100"
#        }
#    }
# }


def visual_comparison_of_video_with_blend_filter(
    source_video_path_vapoursynth: accurate_seek,
    encoded_video_path: str,
    output_filename_with_extension: str,
    # source_start_end_frame: None | tuple[int, int] = None,
    # encode_start_end_frame: None | tuple[int, int] = None,
    quality_crf_h264: int = 20,
) -> None:
    """
    ffmpeg -i original.mkv -i encoded.mkv \
    -filter_complex "blend=all_mode=difference" \
    -c:v libx264 -crf 18 -c:a copy output.mkv
    """
    print("RUNNING visual_comparison_of_video_with_blend_filter")
    ffmpeg_command: list[str] = [
        source_video_path_vapoursynth.command(None, None),
        "ffmpeg -hide_banner -loglevel error ",
    ]
    ffmpeg_command.extend(["-i", encoded_video_path])
    # ffmpeg_command.extend(["-i", source_video_path])
    ffmpeg_command.extend(["-i", "-"])
    ffmpeg_command.append(
        "-filter_complex '[0:v]setpts=PTS-STARTPTS[first];[1:v]setpts=PTS-STARTPTS[second];[first][second]blend=all_mode=difference'"
    )

    ffmpeg_command.append(
        f'-c:v libx264 -y -crf {quality_crf_h264} -an "{output_filename_with_extension}"'
    )
    try:
        print(" ".join(ffmpeg_command))
        _ = subprocess.run(
            " ".join(ffmpeg_command),
            shell=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("ERROR FAILED TO OUTPUT VISUAL COMPARISON (with blend filter)")


def combine_audio_and_subtitle_streams_from_another_video(
    input_file_name_with_extension: videodata.input_file_type,
    output_file_name_with_extension: pathlib.Path,
    audio_commands: str | None = None,
    subtitle_commands: str | None = None,
) -> None:
    """
    Allows you to combine non-video streams from an input video (ie subtitles or audio) in a safe way
    """
    intermediate_file = "TEMP-INTERMEDIATE.mkv"
    try:
        commands: list[str] = []
        if audio_commands is not None:
            commands.append(audio_commands)
        if subtitle_commands is not None:
            commands.append(subtitle_commands)

        _ = subprocess.run(
            f"ffmpeg -i <(cat \"{input_file_name_with_extension}\") -i <(cat \"{output_file_name_with_extension}\") -map 1:v -map 0:a? -map 0:s? -c:v copy {' '.join(commands)} {intermediate_file}",
            shell=True,
            check=True,
        )

        os.remove(output_file_name_with_extension)
        os.rename(intermediate_file, output_file_name_with_extension)
        os.remove(intermediate_file)
    except Exception:
        print(
            "ERROR IN combine_audio_and_subtitle_streams_from_another_video() function"
        )
