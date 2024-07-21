from dataclasses import dataclass
from typing import Literal
import ffmpeg
import ffmpeg_heuristics
import graph_generate
import scene_detection
import file_cache

from rich import print
from rich.progress import Progress, TimeElapsedColumn, track
import concurrent.futures
import os
import time

from rich.console import Console
# import pickle

rich_console = Console()
progress = Progress(
    *Progress.get_default_columns(),
    TimeElapsedColumn(),
)


@dataclass
class videoData:
    full_input_filename: str  # could change to Path
    full_output_filename: str
    vapoursynth_script: str
    codec: ffmpeg.VideoCodec
    heuristic: ffmpeg_heuristics.heuristic
    minimum_scene_length_seconds: float
    audio_commands: str = "-c:a copy"
    subtitle_commands: str = "-c:s copy"
    multithreading_threads: int = 2
    scenes_length_sort: Literal["chronological", "largest first", "smallest first"] = (
        "largest first"  # ensures that CPU always being used
    )
    crop_black_bars: bool = True
    make_comparison_with_blend_filter: bool = False


def compressing_video(video: videoData) -> None:
    assert os.path.isfile(
        video.full_input_filename
    ), f"CRITICAL ERROR: {video.full_input_filename} Does Not Exist!!"

    with rich_console.status(
        f"Getting metadata of input file ({video.full_input_filename})"
    ):
        input_filename_data = ffmpeg.get_video_metadata(video.full_input_filename)

    with rich_console.status("Calculating scenes"):
        raw_video_scenes = scene_detection.find_scenes(
            video.full_input_filename, video.minimum_scene_length_seconds
        )
        print(raw_video_scenes)
        match video.scenes_length_sort:
            case "smallest first":
                video_scenes = sorted(
                    raw_video_scenes,
                    key=lambda x: x.end_frame - x.start_frame,
                )
                print(f"sorted scenes: {video_scenes}")
            case "largest first":
                video_scenes = sorted(
                    raw_video_scenes,
                    key=lambda x: x.end_frame - x.start_frame,
                    reverse=True,
                )
                print(f"sorted scenes: {video_scenes}")
            case "chronological":
                video_scenes = raw_video_scenes
        print(
            f"scene durations (seconds): {[round(scene_detection.scene_len_seconds(x, input_filename_data.frame_rate), 2) for x in video_scenes]}"
        )

    seeking_data_input_file = ffmpeg.accurate_seek(
        video.full_input_filename,
        video.full_input_filename,
        "ffms2",
        extra_commands=video.vapoursynth_script,
    )

    optimal_crf_list: list[
        tuple[scene_detection.SceneData, compress_video_section_data]
    ] = []

    def compress_video_section_call(
        section: int, video_section: scene_detection.SceneData
    ) -> tuple[int, scene_detection.SceneData, compress_video_section_data]:
        video_section_data = _compress_video_section(
            video.full_input_filename,
            _temporary_video_file_names(section),
            input_filename_data,
            video.codec,
            video.heuristic,
            video_section.start_frame,
            video_section.end_frame,
            seeking_data_input_file,
        )
        return (section, video_section, video_section_data)

    with concurrent.futures.ThreadPoolExecutor(
        video.multithreading_threads
    ) as executor:
        results_future = list(
            executor.submit(
                compress_video_section_call,
                raw_video_scenes.index(scene),
                scene,
            )
            for scene in video_scenes
        )

        results = track(
            (x.result() for x in results_future),
            total=len(video_scenes),
            description="Rendering video",
            update_period=1,
        )

        results = sorted(results)
        optimal_crf_list = [x[1:] for x in results]

    with rich_console.status("Concatenating intermediate files"):
        ffmpeg.concatenate_video_files(
            [_temporary_video_file_names(x) for x in range(len(video_scenes))],
            video.full_output_filename,
        )

    with rich_console.status("Generating graph of data"):
        with graph_generate.LinegraphImage(
            filename="video_graph",
            x_axis_name="frames",
            title_of_graph=f"CRF & {video.heuristic.NAME} - {video.full_input_filename} to {video.full_output_filename} ({video.codec.NAME})",
        ) as graph_instance:
            graph_instance.add_linegraph_left(
                x_data=[
                    y
                    for x in optimal_crf_list
                    for y in (x[0].start_frame, x[0].end_frame)
                ],
                y_data=[y[1].crf for x in optimal_crf_list for y in (x, x)],
                name_of_axes="CRF",
                y_axis_range=video.codec.ACCEPTED_CRF_RANGE,
                marker="o",
                colour="red",
            )
            graph_instance.add_linegraph_right(
                y_data=(
                    heuristic_throughout_data
                    := video.heuristic.throughout_video_vapoursynth(
                        seeking_data_input_file, video.full_output_filename
                    )
                ),
                x_data=list(range(len(heuristic_throughout_data))),
                name_of_axes=f"\n+ found (at end) {video.heuristic.NAME}",
                y_axis_range=video.heuristic.RANGE,
                marker="",
                colour="red",
            )
            graph_instance.add_linegraph_right(
                # x_data=list(range(len([y for x in optimal_crf_list for y in x[1]]))),
                x_data=list(
                    range(
                        len(
                            [
                                y
                                for x in optimal_crf_list
                                for y in x[1].heuristic_throughout
                            ]
                        )
                    )
                ),
                y_data=[y for x in optimal_crf_list for y in x[1].heuristic_throughout],
                name_of_axes=f"\n(in section) VMAF throughout {video.heuristic.NAME}",
                y_axis_range=video.heuristic.RANGE,
                marker="",
                colour="blue",
            )
            graph_instance.add_linegraph_right(
                x_data=[
                    y
                    for x in optimal_crf_list
                    for y in (x[0].start_frame, x[0].end_frame)
                ],
                y_data=[y[1].heuristic for x in optimal_crf_list for y in (x, x)],
                name_of_axes=video.heuristic.NAME,
                y_axis_range=video.heuristic.RANGE,
                marker="x",
                colour="blue",
            )

    for x in range(len(video_scenes)):
        print(_temporary_video_file_names(x))
        print(ffmpeg.get_video_metadata(_temporary_video_file_names(x)))
        os.remove(_temporary_video_file_names(x))

    with rich_console.status("Combining audio+subtitles from source video"):
        ffmpeg.combine_audio_and_subtitle_streams_from_another_video(
            video.full_input_filename,
            video.full_output_filename,
            video.audio_commands,
            video.subtitle_commands,
        )

    if video.make_comparison_with_blend_filter:
        with rich_console.status("Making a visual comparison with blend filter"):
            ffmpeg.visual_comparison_of_video_with_blend_filter(
                video.full_input_filename,
                video.full_output_filename,
                "visual_comparison.mp4",
            )

    print(ffmpeg.get_video_metadata(video.full_input_filename))
    print(ffmpeg.get_video_metadata(video.full_output_filename))


def _temporary_video_file_names(position: int) -> str:
    # , extension: str = "mkv"
    return f"temp-{position}.mkv"


@dataclass()
class compress_video_section_data:
    crf: int
    heuristic: float
    heuristic_throughout: list[float]


@file_cache.cache()
def _compress_video_section(
    full_input_filename_part: str,
    full_output_filename: str,
    input_filename_data: ffmpeg.VideoMetadata,
    codec: ffmpeg.VideoCodec,
    heuristic: ffmpeg_heuristics.heuristic,
    frame_start: int,
    frame_end: int,
    input_file_script_seeking: ffmpeg.accurate_seek,
) -> compress_video_section_data:
    bottom_crf_value = min(codec.ACCEPTED_CRF_RANGE)
    top_crf_value = max(codec.ACCEPTED_CRF_RANGE)

    all_heuristic_crf_values: dict[int, float] = {}

    # if not os.path.exists(
    #     f"{full_input_filename_part}-{frame_start}-{frame_end}-{codec}.tempfile"
    # ):

    while (
        current_crf := (top_crf_value + bottom_crf_value) // 2
    ) not in all_heuristic_crf_values.keys():
        while os.path.isfile("STOP.txt"):
            time.sleep(1)

        ffmpeg.run_ffmpeg_command(
            current_crf,
            full_input_filename_part,
            full_output_filename,
            codec,
            frame_start,
            frame_end,
            True,
            300,
            input_file_script_seeking,
        )

        current_heuristic = heuristic.summary_of_overall_video_vapoursynth(
            input_file_script_seeking,
            full_output_filename,
            source_start_end_frame=(frame_start, frame_end),
            subsample=3,
        )

        print(current_heuristic)

        all_heuristic_crf_values.update({current_crf: current_heuristic})

        if round(current_heuristic) == heuristic.target_score:
            print(f"Exact match (of {heuristic.NAME} heuristic)")
            break
        elif current_heuristic > heuristic.target_score:
            bottom_crf_value = current_crf
        elif current_heuristic < heuristic.target_score:
            top_crf_value = current_crf

    closest_value = min(
        (abs(x[1] - heuristic.target_score), x)
        for x in all_heuristic_crf_values.items()
    )[1]

    if current_crf != closest_value[0]:
        print("DIFFERENCE -> current_crf != closest_value !!!")
        ffmpeg.run_ffmpeg_command(
            closest_value[0],
            full_input_filename_part,
            full_output_filename,
            codec,
            frame_start,
            frame_end,
            True,
            300,
            input_file_script_seeking,
        )

    heuristic_throughout = heuristic.throughout_video_vapoursynth(
        input_file_script_seeking,
        full_output_filename,
        source_start_end_frame=(frame_start, frame_end),
        subsample=1,
    )

    return compress_video_section_data(*closest_value, heuristic_throughout)


if __name__ == "__main__":
    start_time = time.perf_counter()
    end_time = time.perf_counter()
    print(f"Total time elapsed: {end_time - start_time}")
