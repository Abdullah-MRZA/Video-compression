import subprocess
from textwrap import dedent
from dataclasses import dataclass
from types import TracebackType
from typing import Literal
import json
import os
# from rich import print

from rich.traceback import install

_ = install(show_locals=True)


type video = SVTAV1 | H265 | H264
# TODO add VP9 support when I feel like it
# type bitdepth = Literal["yuv420p10le", "yuv420p"]


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
    tune: Literal["subjective", "PSNR"] = "subjective"

    @dataclass()
    class Filmgrain:
        film_grain: int
        film_grain_denoise: bool

    # -svtav1-params film-grain=X, film-grain-denoise=0
    film_grain: None | Filmgrain = None
    bitdepth: Literal["yuv420p", "yuv420p10le"] = "yuv420p10le"

    # const data
    ACCEPTED_CRF_RANGE: range = range(0, 63 + 1, 1)
    NAME = "SVTAV1"

    def to_subprocess_command(self) -> list[str]:
        # return [f"-crf {}", f"-preset {preset}"] + [f"-svtav1-params film-grain={film-grain[0]}"]
        command = [
            "-c:v libsvtav1",
            f"-preset {self.preset}",
            f"-pix_fmt {self.bitdepth}",
        ]  # , f"-crf {self.crf_value}"]

        if self.film_grain is not None:
            command.append(f"-svtav1-params film-grain={self.film_grain.film_grain}")
            command.append(f"film-grain-denoise={self.film_grain.film_grain_denoise}")

        command.append(f"-svtav1-params tune={["subjective", "PSNR"].index(self.tune)}")

        return command


@dataclass()
class H264:
    ACCEPTED_CRF_RANGE: range = range(0, 51 + 1, 1)
    NAME = "H264"

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
    faststart: bool = False  # does this get translated to final file?
    bitdepth: Literal["yuv420p", "yuv420p10le"] = "yuv420p10le"

    def to_subprocess_command(self) -> list[str]:
        command = [
            "-c:v libx264",
            f"-preset {self.preset}",
            f"-pix_fmt {self.bitdepth}",
        ]

        if self.tune is not None:
            command.append(f"-tune {self.tune}")

        if self.faststart:
            command.append("-movflags +faststart")

        return command


@dataclass()
class H265:
    ACCEPTED_CRF_RANGE: range = range(0, 51 + 1, 1)
    NAME = "H265"

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

    bitdepth: Literal["yuv420p", "yuv420p10le"] = "yuv420p10le"

    def to_subprocess_command(self) -> list[str]:
        command = [
            "-c:v libx265",
            f"-preset {self.preset}",
            f"-pix_fmt {self.bitdepth}",
        ]

        return command


# @dataclass()
# class VP9:
#     ACCEPTED_CRF_RANGE: range = range(0, 50, 1)
#     two_passes: bool = True
#
#     def to_subprocess_command(self) -> list[str]: ...


class ffms2seek:
    def __init__(
        self, video_filename_with_extension: str, filename_vpy_without_extension: str
    ) -> None:
        self.filename_of_vpy = f"{filename_vpy_without_extension.replace('.', '')}.vpy"
        # for seeking
        with open(self.filename_of_vpy, "w") as f:
            _ = f.write(
                dedent(f"""
                import vapoursynth as vs
                core = vs.core
                clip = core.ffms2.Source(source="{video_filename_with_extension}")
                clip.set_output(0)
            """)
            )
        # _ = input("NOTE MADE FILE")

    def command(self, start_frame: int | None, end_frame: int | None) -> str:
        start = (
            f"-s {start_frame}"
            if (start_frame is not None and start_frame != 0)
            else ""
        )
        end = f"-e {end_frame - 1}" if end_frame is not None else ""
        return f"vspipe {start} {end} -c y4m {self.filename_of_vpy} - |"

    def __exit__(self):
        try:
            os.remove(self.filename_of_vpy)
        except Exception as _:
            print(f"WARNING: Unable to delete file: {self.filename_of_vpy}")


@dataclass()
class FfmpegCommand:
    input_filename: str
    codec_information: video

    start_frame: int
    end_frame: int

    output_filename: str
    ffmpeg_path: str

    crop_black_bars_size: str | None
    # bit_depth: bitdepth
    keyframe_placement: int | None

    input_file_script_seeking: ffms2seek | None

    def __enter__(self):
        return self

    def run_ffmpeg_command(
        self, crf_value: int, override_output_file_name: str | None = None
    ) -> None:
        # self.end_time_frame -= (
        #     0  # TO PREVENT OVERLAP BETWEEN FRAMES --> prevent duplication
        # )

        # framerate: float = get_frame_rate(self.input_filename)
        framerate: float = get_video_metadata(self.input_filename).frame_rate
        # start_time_seconds = self.start_frame / framerate
        # end_time_seconds = self.end_frame / framerate
        command: list[str] = [  # ADD -r COMMANDD!!
            self.input_file_script_seeking.command(self.start_frame, self.end_frame)
            if self.input_file_script_seeking is not None
            else "",
            self.ffmpeg_path,
            "-hide_banner -loglevel error",
            # "-accurate_seek",
            f"-r {framerate}",
            # f"-ss {start_time_seconds}",  # NOTE: IS THIS OKAY??? (SEEMS SO??) + IS FASTER?
            # f"-to {end_time_seconds}",
            # f'-i "{self.input_filename}"',
            "-i -"
            if self.input_file_script_seeking is not None
            else f"-i {self.input_filename}",
            # f"-ss {start_time_seconds}",  # -ss After is **very important** for accuracy!!
            # f"-to {end_time_seconds}",
            # f"-vf trim={self.start_time_seconds}:{self.end_time_seconds},setpts=PTS-STARTPTS",  # is this faster + as accurate?
            *self.codec_information.to_subprocess_command(),
            "-an",
            # f"-pix_fmt {self.bit_depth}",
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

        # try:
        #     os.remove(script_name)
        # except FileNotFoundError:
        #     print("Error removing script")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None: ...


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
    print(
        f'RUNNING COMMAND: {ffmpeg_path} -f concat -i video_list.txt -c copy -y "{output_filename_with_extension}"'
    )
    _ = subprocess.run(  # -safe 0 (has some wierd effect of changing DTS values)
        f'{ffmpeg_path} -f concat -i video_list.txt -c copy -y "{output_filename_with_extension}"',
        shell=True,
        check=True,
    )

    try:
        os.remove("video_list.txt")
    except FileNotFoundError:
        print("File Not found error: video_list.txt can't be deleted")


# concatenate_video_files([f"out{x}.mp4" for x in range(3)], "TEST.mkv", "ffmpeg")

# concatenate_video_files(
#     [f"{x}-part.mkv" for x in range(0, 6)], "utasjldfkajs.mkv", "ffmpeg"
# )


@dataclass()
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
    bitrate: int
    # is_HDR: bool


def get_video_metadata(
    filename: str, print_raw: bool = False, ffprobe_path: str = "ffprobe"
) -> VideoMetadata:
    # another command: % ffprobe -i small-trim.mp4 -print_format json -loglevel fatal -show_streams -count_frames
    data = subprocess.run(
        f'{ffprobe_path} -v quiet -print_format json -show_format -show_streams -count_frames "{filename}"',
        check=True,
        shell=True,
        capture_output=True,
    ).stdout.decode()

    json_data = json.loads(data)

    if print_raw:
        print(json_data)

    return VideoMetadata(
        file_name=json_data["format"]["filename"],  # same as `filename`...
        width=int(json_data["streams"][0]["width"]),
        height=int(json_data["streams"][0]["height"]),
        # frame rate info
        frame_rate=float(
            eval(json_data["streams"][0]["r_frame_rate"])
        ),  # FRACTION OR DECIMAL --> WARNING: may be unsafe
        total_frames=int(json_data["streams"][0]["nb_read_frames"]),
        # pixel info
        pix_fmt=json_data["streams"][0]["pix_fmt"],
        codec=json_data["streams"][0]["codec_name"],
        # timings
        start_time=float(json_data["format"]["start_time"]),
        duration=float(json_data["format"]["duration"]),
        # other data
        contains_audio=any(
            True for x in json_data["streams"] if x["codec_type"] == "audio"
        ),
        file_size=int(json_data["format"]["size"]),
        bitrate=int(json_data["format"]["bit_rate"]),
        # is_HDR=(json_data["streams"][0]["color_space"] == "bt2020nc") # https://video.stackexchange.com/questions/22059/how-to-identify-hdr-video
        # and (json_data["streams"][0]["color_transfer"] == "smpte2084")
        # and (json_data["streams"][0]["color_primaries"] == "bt2020"),
    )

    # ffprobe -v quiet -print_format json -show_format -show_streams short.mp4


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
    source_video_path: str,
    encoded_video_path: str,
    ffmpeg_path: str,
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
    ffmpeg_command: list[str] = [f"{ffmpeg_path} -hide_banner -loglevel error "]
    # frame_rate = get_frame_rate(source_video_path)

    # if encode_start_end_frame is not None:
    #     ffmpeg_command.extend(["-ss", str(encode_start_end_frame[0] / frame_rate)])
    #     ffmpeg_command.extend(["-to", str(encode_start_end_frame[1] / frame_rate)])
    ffmpeg_command.extend(["-i", encoded_video_path])

    # if source_start_end_frame is not None:
    #     ffmpeg_command.extend(["-ss", str(source_start_end_frame[0] / frame_rate)])
    #     ffmpeg_command.extend(["-to", str(source_start_end_frame[1] / frame_rate)])
    ffmpeg_command.extend(["-i", source_video_path])

    # ffmpeg_command.append('-filter_complex "blend=all_mode=difference"')
    ffmpeg_command.append(
        "-filter_complex '[0:v]setpts=PTS-STARTPTS[first];[1:v]setpts=PTS-STARTPTS[second];[first][second]blend=all_mode=difference'"  # [out]
    )

    ffmpeg_command.append(
        f'-c:v libx264 -y -crf {quality_crf_h264} -an "{output_filename_with_extension}"'
    )
    try:
        # + '-filter_complex "[1:v]setpts=PTS-STARTPTS[reference];[0:v]setpts=PTS-STARTPTS[distorted];[distorted][reference]blend=all_mode=difference" -c:v libx264 -y -crf 18 ' # this is actually harmful?? because the "start_time" in ffprobe don't line up, and this also causes them to not line up
        # f"{ffmpeg_path} -i {encoded_video_path} -i {source_video_path} -hide_banner -loglevel error "
        print(" ".join(ffmpeg_command))
        _ = subprocess.run(
            " ".join(ffmpeg_command),
            shell=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("ERROR FAILED TO OUTPUT VISUAL COMPARISON (with blend filter)")


def combine_audio_and_subtitle_streams_from_another_video(
    input_file_name_with_extension: str,
    output_file_name_with_extension: str,
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
            f"ffmpeg -i {input_file_name_with_extension} -i {output_file_name_with_extension} -map 1:v -map 0:a? -map 0:s? -c:v copy {' '.join(commands)} {intermediate_file}",
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


# # Is this necessary? --> Now legacy
# def get_frame_rate(filename: str) -> float:
#     data = subprocess.run(
#         f"ffprobe -i {filename} -print_format json -loglevel fatal -show_streams -count_frames -select_streams v | grep r_frame_rate",
#         shell=True,
#         check=True,
#         capture_output=True,
#     ).stdout.decode()
#     return float(
#         eval(data.strip().split(":")[1].replace(",", "").replace('"', "").strip())
#     )


# ffmpeg -i video1.mkv -i video2.mkv -filter_complex "[0:V:0]crop=960:1080:0:0[v1];[1:V:0]crop=960:1080:960:0[v2];[v1][v2]hstack=2[out]" -map "[out]" output.mkv
# https://old.reddit.com/r/ffmpeg/comments/15jlm93/how_to_achieve_side_by_screen_split_screen_from/

# visual_comparison_of_video_with_blend_filter(
#     "input.mov", "input-copy.mov", "ffmpeg", "TESTTEST.mkv"
# )

# visual_comparison_of_video_with_blend_filter(
#     "short-smallest.mp4", "TEST.mkv", "ffmpeg", "TESTTEST.mkv"
# )
#
# print(
#     os.system(
#         "ffprobe -i short-smallest.mp4 -print_format json -loglevel fatal -show_streams -count_frames -select_streams v | grep start_tim"
#     )
# )
# print(
#     os.system(
#         "ffprobe -i TEST.mkv -print_format json -loglevel fatal -show_streams -count_frames -select_streams v | grep start_tim"
#     )
# )
