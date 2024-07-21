from dataclasses import dataclass
from typing import Literal
from . import ffmpeg
from . import ffmpeg_heuristics
from . import graph_generate
from . import scene_detection

from rich import print
from rich.progress import Progress, TimeElapsedColumn, track
import concurrent.futures
import os
import time

from rich.console import Console
import pickle

rich_console = Console()
progress = Progress(
    *Progress.get_default_columns(),
    TimeElapsedColumn(),
)


@dataclass
class videoData:
    full_input_filename: str  # could change to Path
    full_output_filename: str
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
    make_comparison_with_blend_filter: bool = True


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
        video.full_input_filename, video.full_input_filename, "ffms2", extra_commands=""
    )

    def compress_video_section_call(
        section: int, video_section: scene_detection.SceneData
    ) -> tuple[int, scene_detection.SceneData, int, float, list[float]]:
        optimal_crf, heuristic_reached, heuristic_throughout = _compress_video_section(
            video.full_input_filename,
            input_filename_data,
            _temporary_video_file_names(section),
            video.codec,
            video.heuristic,
            video_section.start_frame,
            video_section.end_frame,
            seeking_data_input_file,
        )
        return (
            section,
            video_section,
            optimal_crf,
            heuristic_reached,
            heuristic_throughout,
        )

    optimal_crf_list: list[
        tuple[scene_detection.SceneData, int, float, list[float]]
    ] = []

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
            "video_graph",
            "png",
            f"CRF & {video.heuristic.NAME} - {video.full_input_filename} to {video.full_output_filename} ({video.codec.NAME})",
            "frames",
        ) as graph_instance:
            graph_instance.add_linegraph(
                x_data=[
                    y
                    for x in optimal_crf_list
                    for y in (x[0].start_frame, x[0].end_frame)
                ],
                y_data=[y[1] for x in optimal_crf_list for y in (x, x)],
                name="CRF",
                mode="lines+markers",
                on_left_right_side="left",
                y_axis_range=video.codec.ACCEPTED_CRF_RANGE,
            )
            graph_instance.add_linegraph(
                x_data=list(range(len([y for x in optimal_crf_list for y in x[3]]))),
                y_data=[y for x in optimal_crf_list for y in x[3]],
                name=f"found {video.heuristic.NAME}",
                mode="lines",
                on_left_right_side="right",
                y_axis_range=video.heuristic.RANGE,
            )
            graph_instance.add_linegraph(
                x_data=[
                    y
                    for x in optimal_crf_list
                    for y in (x[0].start_frame, x[0].end_frame)
                ],
                y_data=[y[2] for x in optimal_crf_list for y in (x, x)],
                name=video.heuristic.NAME,
                mode="lines+markers",
                on_left_right_side="right",
                y_axis_range=video.heuristic.RANGE,
            )

    for x in range(len(video_scenes)):
        print(_temporary_video_file_names(x))
        print(ffmpeg.get_video_metadata(_temporary_video_file_names(x)))
        # os.remove(_temporary_video_file_names(x))

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

    for tempfile in [
        x
        for x in os.listdir()
        if x.endswith(".tempfile") or x.startswith("cache-") or x.startswith("temp")
    ]:
        os.remove(tempfile)


def _temporary_video_file_names(position: int) -> str:
    # , extension: str = "mkv"
    return f"temp-{position}.mkv"


def _compress_video_section(
    full_input_filename_part: str,
    input_filename_data: ffmpeg.VideoMetadata,
    full_output_filename: str,
    codec: ffmpeg.VideoCodec,
    heuristic: ffmpeg_heuristics.heuristic,
    frame_start: int,
    frame_end: int,
    input_file_script_seeking: ffmpeg.accurate_seek,
) -> tuple[int, float, list[float]]:
    with ffmpeg.FfmpegCommand(
        input_filename=full_input_filename_part,
        codec_information=codec,
        start_frame=frame_start,
        end_frame=frame_end,
        output_filename=full_output_filename,
        ffmpeg_path="ffmpeg",
        crop_black_bars_size=None,
        keyframe_placement=300,
        input_file_script_seeking=input_file_script_seeking,
    ) as video_command:
        bottom_crf_value = min(codec.ACCEPTED_CRF_RANGE)
        top_crf_value = max(codec.ACCEPTED_CRF_RANGE)

        all_heuristic_crf_values: dict[int, float] = {}

        current_crf = None
        if not os.path.exists(
            f"{full_input_filename_part}-{frame_start}-{frame_end}-{codec}.tempfile"
        ):
            while (
                current_crf := (top_crf_value + bottom_crf_value) // 2
            ) not in all_heuristic_crf_values.keys():
                # Will pause execution
                # In case of needing to pause
                while os.path.isfile("STOP.txt"):
                    time.sleep(1)

                video_command.run_ffmpeg_command(current_crf)

                current_heuristic = heuristic.summary_of_overall_video(
                    full_input_filename_part,
                    full_output_filename,
                    "ffmpeg",
                    input_file_script_seeking,
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
        else:
            print("Using data from crash temp file")
            with open(
                f"{full_input_filename_part}-{frame_start}-{frame_end}-{codec}.tempfile",
                "rb",
            ) as file:
                all_heuristic_crf_values = pickle.load(file)

        closest_value = min(
            (abs(x[1] - heuristic.target_score), x)
            for x in all_heuristic_crf_values.items()
        )[1]

        if current_crf is not None and current_crf != closest_value[0]:
            print("DIFFERENCE -> current_crf != closest_value !!!")
            video_command.run_ffmpeg_command(closest_value[0])

        heuristic_throughout = heuristic.throughout_video(
            full_input_filename_part,
            full_output_filename,
            "ffmpeg",
            input_file_script_seeking,
            source_start_end_frame=(frame_start, frame_end),
            subsample=1,
        )

        with open(
            f"{full_input_filename_part}-{frame_start}-{frame_end}-{codec}.tempfile",
            "wb",
        ) as file:
            pickle.dump(all_heuristic_crf_values, file)

        print("done writing the backup data")

        return *closest_value, heuristic_throughout


if __name__ == "__main__":
    start_time = time.perf_counter()
    end_time = time.perf_counter()
    print(f"Total time elapsed: {end_time - start_time}")
