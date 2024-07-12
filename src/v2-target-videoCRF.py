from typing import Literal
import ffmpeg
import ffmpeg_heuristics
import graph_generate
import scene_detection

from rich import print
from rich.progress import Progress, TimeElapsedColumn
import concurrent.futures
import os
import time

# from hashlib import sha256
from rich.console import Console
import pickle
# from multiprocessing import Pool

progress = Progress(
    *Progress.get_default_columns(),
    TimeElapsedColumn(),
)

rich_console = Console()


def compressing_video(
    full_input_filename: str,
    full_output_filename: str,
    codec: ffmpeg.video,
    heuristic: ffmpeg_heuristics.heuristic,
    # scene_detection_threshold: int = 27,
    minimum_scene_length_seconds: float,
    audio_commands: None | str = "-c:a copy",  # TODO: Remove None option
    subtitle_commands: None | str = "-c:s copy",
    multithreading_threads: int = 2,
    scenes_length_sort: Literal[
        "chronological", "largest first", "smallest first"
    ] = "chronological",
    # crop_black_bars: bool = True,
) -> None:
    assert os.path.isfile(
        full_input_filename
    ), f"CRITICAL ERROR: {full_input_filename} Does Not Exist!!"

    with rich_console.status("Calculating scenes"):
        video_scenes = scene_detection.find_scenes(
            full_input_filename, minimum_scene_length_seconds
        )
        print(video_scenes)
        match scenes_length_sort:
            case "smallest first":
                video_scenes = sorted(
                    video_scenes,
                    key=lambda x: x.end_frame - x.start_frame,
                )
            case "largest first":
                video_scenes = sorted(
                    video_scenes,
                    key=lambda x: x.end_frame - x.start_frame,
                    reverse=True,
                )
            case "chronological":
                pass

    input_filename_data = ffmpeg.get_video_metadata(full_input_filename)

    seeking_data_input_file = ffmpeg.ffms2seek(full_input_filename, full_input_filename)

    def compress_video_section_call(
        section: int, video_section: scene_detection.SceneData
    ) -> tuple[int, scene_detection.SceneData, int, float, list[float]]:
        optimal_crf, heuristic_reached, heuristic_throughout = _compress_video_section(
            full_input_filename,
            input_filename_data,
            _temporary_file_names(section),
            codec,
            heuristic,
            video_section.start_frame,
            video_section.end_frame,
            seeking_data_input_file,
        )
        return (
            section,
            # video_section.start_frame,
            video_section,
            optimal_crf,
            heuristic_reached,
            heuristic_throughout,
        )

    optimal_crf_list: list[
        tuple[scene_detection.SceneData, int, float, list[float]]
    ] = []

    with rich_console.status("Rendering..."):
        with concurrent.futures.ThreadPoolExecutor(multithreading_threads) as executor:
            results = list(
                executor.map(
                    compress_video_section_call, range(len(video_scenes)), video_scenes
                )
            )
            results = sorted(results)
            optimal_crf_list = [x[1:] for x in results]

    with rich_console.status("Concatenating intermediate files"):
        ffmpeg.concatenate_video_files(
            [_temporary_file_names(x) for x in range(len(video_scenes))],
            full_output_filename,
            "ffmpeg",
        )

    with rich_console.status("Generating graph of data"):
        with graph_generate.LinegraphImage(
            "video_graph",
            "png",
            f"CRF & {heuristic.NAME} - {full_input_filename} to {full_output_filename} ({codec.NAME})",
            "frames",
        ) as graph_instance:
            graph_instance.add_linegraph(
                # x_data=[x[0].start_frame for x in optimal_crf_list],
                x_data=[
                    y
                    for x in optimal_crf_list
                    for y in (x[0].start_frame, x[0].end_frame)
                ],
                y_data=[y[1] for x in optimal_crf_list for y in (x, x)],
                name="CRF",
                mode="lines+markers",
                on_left_right_side="left",
                y_axis_range=codec.ACCEPTED_CRF_RANGE,
            )
            graph_instance.add_linegraph(
                x_data=list(range(len([y for x in optimal_crf_list for y in x[3]]))),
                y_data=[y for x in optimal_crf_list for y in x[3]],
                name=f"found {heuristic.NAME}",
                mode="lines",
                on_left_right_side="right",
                y_axis_range=heuristic.RANGE,
            )
            graph_instance.add_linegraph(
                # x_data=[x[0].start_frame for x in optimal_crf_list],
                x_data=[
                    y
                    for x in optimal_crf_list
                    for y in (x[0].start_frame, x[0].end_frame)
                ],
                y_data=[y[2] for x in optimal_crf_list for y in (x, x)],
                name=heuristic.NAME,
                mode="lines+markers",
                on_left_right_side="right",
                y_axis_range=heuristic.RANGE,
            )

    for x in range(len(video_scenes)):
        print(_temporary_file_names(x))
        print(ffmpeg.get_video_metadata(_temporary_file_names(x)))
        os.remove(_temporary_file_names(x))

    for tempfile in [x for x in os.listdir() if x.endswith(".tempfile")]:
        os.remove(tempfile)

    # ffmpeg.get_video_metadata(full_input_filename).contains_audio and audio_commands is not None --> handled by function
    with rich_console.status("Combining audio+subtitles from source video"):
        ffmpeg.combine_audio_and_subtitle_streams_from_another_video(
            full_input_filename, full_output_filename, audio_commands, subtitle_commands
        )

    with rich_console.status("Making a visual comparison with blend filter"):
        ffmpeg.visual_comparison_of_video_with_blend_filter(
            full_input_filename, full_output_filename, "ffmpeg", "visual_comparison.mp4"
        )

    print(ffmpeg.get_video_metadata(full_input_filename, False))
    print(ffmpeg.get_video_metadata(full_output_filename, False))


# def _temporary_file_names(position: int, iscomplete: bool = True) -> str:
#     return f"TEMP-{position}{'' if iscomplete else '-notcomplete'}.mkv"
# def _temporary_file_names(position: int) -> str:
#     return f"temp-{position}.mkv"


def _temporary_file_names(position: int, extension: str = "mkv") -> str:
    return f"temp-{position}.{extension}"


def _compress_video_section(
    full_input_filename_part: str,
    input_filename_data: ffmpeg.VideoMetadata,
    full_output_filename: str,
    codec: ffmpeg.video,
    heuristic: ffmpeg_heuristics.heuristic,
    frame_start: int,
    frame_end: int,
    input_file_script_seeking: ffmpeg.ffms2seek,
) -> tuple[int, float, list[float]]:  # CRF + heuristic (throughout)
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
                while os.path.isfile("STOP.txt"):  # Will pause execution
                    time.sleep(1)

                video_command.run_ffmpeg_command(current_crf)

                current_heuristic = heuristic.summary_of_overall_video(
                    full_input_filename_part,
                    full_output_filename,
                    "ffmpeg",
                    input_file_script_seeking,
                    source_start_end_frame=(frame_start, frame_end),
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
    compressing_video(
        # "input_mov.mp4",
        "input-tiny.mp4",
        # "big.mp4",
        "output-temp.mkv",
        ffmpeg.H264(tune="animation", preset="veryfast"),
        # ffmpeg.SVTAV1(preset=6),
        ffmpeg_heuristics.VMAF(94),
        # scene_detection_threshold=40,
        minimum_scene_length_seconds=0.2,
        audio_commands="-c:a copy",
        multithreading_threads=4,
        scenes_length_sort="smallest first",
    )
