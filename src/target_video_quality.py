from typing import Literal
import ffmpeg
import ffmpeg_heuristics
import matplotlib
import scene_detection


def compress_video(
    input_filename: str,
    ffmpeg_codec_information: ffmpeg.video,
    heuristic_type: ffmpeg_heuristics.heuristic,
    output_filename: str | None = None,
    start_time_seconds: int = 0,
    end_time_seconds: int = 0,
    crop_black_bars: bool = True,
    bit_depth: Literal["yuv420p10le", "yuv420p"] = "yuv420p10le",
    keyframe_placement: int | None = 200,
    ffmpeg_path: str = "ffmpeg",
    draw_matplotlib_graph: bool = True,
):
    """
    This does practically all of the calculations
    This splits the video files into scenes, and then compresses them,
    targeting a specific video heuristic
    This also recombines the video at the end
    """
    with ffmpeg.FfmpegCommand(
        input_filename=input_filename,
        codec_information=ffmpeg_codec_information,
        output_filename=output_filename,
        start_time_seconds=start_time_seconds,
        end_time_seconds=end_time_seconds,
        crop_black_bars=crop_black_bars,
        bit_depth=bit_depth,
        keyframe_placement=keyframe_placement,
        ffmpeg_path=ffmpeg_path,
    ) as command:
        video_scenes = scene_detection.find_scenes(input_filename)
