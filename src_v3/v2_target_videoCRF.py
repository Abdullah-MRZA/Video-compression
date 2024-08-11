from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess
from typing import Literal

import ffmpeg
import ffmpeg_heuristics
import graph_generate
import scene_detection
import file_cache
import videodata

from rich import print
from rich.progress import Progress, TimeElapsedColumn, track
import concurrent.futures
import os

from rich.console import Console

rich_console = Console()
progress = Progress(
    *Progress.get_default_columns(),
    TimeElapsedColumn(),
)

_SCENES_LENGTH_SORT_VALUES = Literal[
    "chronological", "largest first", "smallest first", "interlaced"
]


@dataclass
class videoInputData:
    videodata: videodata.RawVideoData
    codec: ffmpeg.VideoCodec
    heuristic: ffmpeg_heuristics.heuristic
    minimum_scene_length_seconds: float
    audio_commands: str = "-c:a copy"
    subtitle_commands: str = "-c:s copy"
    multithreading_threads: int = 2
    scenes_length_sort: _SCENES_LENGTH_SORT_VALUES = (
        "largest first"  # ensures that CPU always being used
    )
    make_comparison_with_blend_filter: bool = False
    render_final_video: bool = False


@dataclass
class start_heuristic_crf_jumping:
    start_heuristic: float
    end_crf: int


@dataclass()
class rendered_data:
    crf: int
    heuristic: float
    heuristic_throughout: list[float]
    filepath_of_final: None | Path

    # for quick jumping
    heuristicjump: start_heuristic_crf_jumping


@dataclass
class optimal_crf_data:
    scene: scene_detection.SceneData
    scenedata: rendered_data


def _compress_video_sections_automatically_and_concurrently(
    video: videoInputData,
    raw_video_scenes: list[scene_detection.SceneData],
    video_scenes: list[scene_detection.SceneData],
    crf_ranges_of_video_scenes: list[range],
    description: str,
    prior_calculation_results: list[tuple[int, float]],
) -> list[optimal_crf_data]:
    def compress_video_section_call(
        section: int, video_section: scene_detection.SceneData, crf_range: range
    ) -> tuple[int, scene_detection.SceneData, rendered_data]:
        video_section_data = identify_videosection_optimal_crf(
            video.videodata,
            Path("Temp.mkv") if video.render_final_video else None,
            video.codec,
            video.heuristic,
            video_section.start_frame,
            video_section.end_frame,
            crf_range,
            prior_calculation_results,
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
                current_range,
            )
            for current_range, scene in zip(crf_ranges_of_video_scenes, video_scenes)
        )

        results = track(
            (x.result() for x in results_future),
            total=len(video_scenes),
            description=description,
            update_period=1,
        )

        results = sorted(results)
        optimal_crf_list = [x[1:] for x in results]
    return [optimal_crf_data(x[0], x[1]) for x in optimal_crf_list]


def _save_graph_of_rendered_data(
    video: videoInputData, optimal_crf_list: list[optimal_crf_data]
):
    optimal_crf_list = sorted(optimal_crf_list, key=lambda x: x.scene.start_frame)
    with graph_generate.LinegraphImage(
        filename="video_graph",
        x_axis_name="frames",
        title_of_graph=f"CRF & {video.heuristic.NAME} - {video.videodata.raw_input_filename} to {video.videodata.output_filename} ({video.codec.NAME})",
    ) as graph_instance:
        graph_instance.add_linegraph_left(
            x_data=[
                y
                for x in optimal_crf_list
                for y in (x.scene.start_frame, x.scene.end_frame)
            ],
            y_data=[y.scenedata.crf for x in optimal_crf_list for y in (x, x)],
            name_of_axes="CRF",
            y_axis_range=video.codec.ACCEPTED_CRF_RANGE,
            marker="o",
            colour="red",
        )
        # graph_instance.add_linegraph_right(
        #     y_data=(
        #         heuristic_throughout_data := video.heuristic.throughout_video(
        #             # seeking_data_input_file, video.full_output_filename
        #             video.videodata.vapoursynth_seek,
        #             video.videodata.output_filename,
        #         )
        #     ),
        #     x_data=list(range(len(heuristic_throughout_data))),
        #     name_of_axes=f"\n\n+ found overall (at the end) {video.heuristic.NAME}",
        #     y_axis_range=video.heuristic.RANGE,
        #     marker="",
        #     colour="orange",
        # )
        graph_instance.add_linegraph_right(
            y_data=(
                y_data_values := [
                    y
                    for x in optimal_crf_list
                    for y in x.scenedata.heuristic_throughout
                ]
            ),
            x_data=list(range(len(y_data_values))),
            name_of_axes=f"\n(in section) target {video.heuristic.NAME} throughout",
            y_axis_range=video.heuristic.RANGE,
            marker="",
            colour="cyan",
        )
        graph_instance.add_linegraph_right(
            x_data=[
                y
                for x in optimal_crf_list
                for y in (x.scene.start_frame, x.scene.end_frame)
            ],
            y_data=[y.scenedata.heuristic for x in optimal_crf_list for y in (x, x)],
            name_of_axes=f"target {video.heuristic.NAME}",
            y_axis_range=video.heuristic.RANGE,
            marker="x",
            colour="blue",
        )


def _concatenate_rendered_videos_and_add_audio(
    video: videoInputData,
    optimal_crf_list: list[optimal_crf_data],
    raw_video_scenes: list[scene_detection.SceneData],
):
    filepaths = [x.scenedata.filepath_of_final for x in optimal_crf_list]
    clean_filepaths: list[Path] = []  # to fix lsp

    for path in filepaths:
        assert path is not None
        clean_filepaths.append(path)

    ffmpeg.concatenate_video_files(
        clean_filepaths,
        video.videodata.output_filename,
    )

    try:
        _ = [
            os.remove(temporary_video_filename(x, Path("temporary_cache_dir")))
            for x in range(len(raw_video_scenes))
        ]
    except Exception:
        print("Error deleting temp files")

    if ffmpeg.get_video_metadata(
        video.videodata, video.videodata.input_filename
    ).contains_audio:
        with rich_console.status("Combining audio+subtitles from source video"):
            ffmpeg.combine_audio_and_subtitle_streams_from_another_video(
                video.videodata.raw_input_filename,
                video.videodata.output_filename,
                video.audio_commands,
                video.subtitle_commands,
            )


# def _make_comparison_with_blend_filter() -> None:
#     with rich_console.status("Making a visual comparison with blend filter"):
#         ffmpeg.visual_comparison_of_video_with_blend_filter(
#             seeking_data_input_file,
#             video.full_output_filename,
#             "visual_comparison.mp4",
#         )


def _print_table_of_heuristic_vs_endcrf(
    testing_all_data: list[rendered_data],
):
    sorted_testing_all_data = sorted(
        testing_all_data, key=lambda x: x.heuristicjump.start_heuristic
    )
    print(
        len(
            sorted(
                testing_all_data,
                key=lambda x: x.heuristicjump.start_heuristic,
            )
        )
    )
    with graph_generate.LinegraphImage(
        "VMAF to final CRF comparison test",
        x_axis_name="initial VMAF",
        title_of_graph="VMAF to final CRF comparison test",
    ) as graph_instance:
        graph_instance.add_linegraph_left(
            x_data=[x.heuristicjump.start_heuristic for x in sorted_testing_all_data],
            y_data=[x.heuristicjump.end_crf for x in sorted_testing_all_data],
            name_of_axes="",
            y_axis_range=range(0, 63),
            marker="o",
            colour="red",
        )


def temporary_video_filename(position: int, filepath_for_render: Path) -> Path:
    return filepath_for_render / Path(f"temp-{position}.mkv")


def subpart_video_filename(
    video: videodata.RawVideoData,
    output_video_name: Path,
    crf: int,
    frame_start: int | None,
    frame_end: int | None,
) -> Path:
    file_path = (
        Path("temporary_cache_dir")
        / Path("intermediatefiles")
        / Path(
            f"{crf} - {frame_start} - {frame_end} - {video.sha256_of_input} {output_video_name.name}"
        )
    )
    if not os.path.exists(file_path.parent):
        try:
            os.makedirs(file_path.parent)
        except FileExistsError:
            print("dir already exists")
    return file_path


# @file_cache.cache(
#     extra_info_in_shahash=f"{video}{codec}{heuristic}{frame_start}{frame_end}",
#     persistent_after_termination=True,
#     sub_directory=Path("intermediatefiles"),
# )
@file_cache.store_cumulative_time
def render_scene_for_certain_crf_and_get_heuristic_and_path(
    video: videodata.RawVideoData,
    crf: int,
    codec: ffmpeg.VideoCodec,
    frame_start: int | None,
    frame_end: int | None,
    heuristic: ffmpeg_heuristics.heuristic,
    output_video_name: Path | None,
) -> tuple[float, Path | None]:
    temporary_ffmpeg_command = ffmpeg.run_ffmpeg_command(
        video,
        subpart_video_filename(video, output_video_name, crf, frame_start, frame_end)
        if isinstance(output_video_name, Path)
        else "get ffmpeg string",
        crf,
        codec,
        frame_start,
        frame_end,
        300,
    )

    if temporary_ffmpeg_command is None:
        temporary_ffmpeg_command = ""
    assert isinstance(temporary_ffmpeg_command, str), "SHOULD BE STR OR NONE"

    current_heuristic = heuristic.summary_of_overall_video(
        video,
        subpart_video_filename(video, output_video_name, crf, frame_start, frame_end)
        if isinstance(output_video_name, Path)
        else temporary_ffmpeg_command,
        source_start_end_frame=(frame_start, frame_end),
        subsample=1,
    )

    print(current_heuristic)
    return (
        current_heuristic,
        subpart_video_filename(video, output_video_name, crf, frame_start, frame_end)
        if isinstance(output_video_name, Path)
        else None,
    )


@file_cache.store_cumulative_time
@file_cache.cache(
    sub_directory=Path("videosection_crf"),
    persistent_after_termination=False,  # False
)
def identify_videosection_optimal_crf(
    video: videodata.RawVideoData,
    final_output_video_name: Path | None,
    codec: ffmpeg.VideoCodec,
    heuristic: ffmpeg_heuristics.heuristic,
    frame_start: int,
    frame_end_raw: int,
    crf_range: range,
    prior_calculation_results: list[tuple[int, float]],  # CRF, heuristic
) -> rendered_data:
    """
    This function finds the optimal CRF value for a target quality heuristic
    """
    # testing_data_prediction: testing_data_prediction_data | None = None
    testing_start_VMAF: float | None = None

    frame_end = int(
        min(
            frame_end_raw,
            frame_end_raw
            + round(
                # float("inf")
                15 * ffmpeg.get_video_metadata(video, video.input_filename).frame_rate
            ),
        ),
    )

    # bottom_crf_value = min(codec.ACCEPTED_CRF_RANGE)
    # top_crf_value = max(codec.ACCEPTED_CRF_RANGE)
    bottom_crf_value = crf_range.start
    top_crf_value = crf_range.stop

    for calculation in prior_calculation_results:
        # testing_start_VMAF = calculation[1]
        if calculation[1] > heuristic.target_score:
            bottom_crf_value = calculation[0]
        elif calculation[1] < heuristic.target_score:
            top_crf_value = calculation[0]
        else:  # WARNING: TEST IF THIS WORKS
            top_crf_value = bottom_crf_value = calculation[0]
            top_crf_value += 1

    all_heuristic_crf_values: dict[int, float] = {}

    def expect_str(data: str | CompletedProcess[bytes] | None) -> str:
        if isinstance(data, str):
            return data
        raise ValueError("Should never be None")

    all_temp_files: list[Path] = []

    while (
        current_crf := (top_crf_value + bottom_crf_value) // 2
    ) not in all_heuristic_crf_values.keys():
        current_heuristic, _ = render_scene_for_certain_crf_and_get_heuristic_and_path(
            video,
            current_crf,
            codec,
            frame_start,
            frame_end,
            heuristic,
            subpart_video_filename(
                video, final_output_video_name, current_crf, frame_start, frame_end
            )
            if final_output_video_name is not None
            else None,
        )

        all_heuristic_crf_values.update({current_crf: current_heuristic})

        if testing_start_VMAF is None:
            testing_start_VMAF = current_heuristic

        if abs(current_heuristic - heuristic.target_score) <= 0.1:
            print(f"Exact match (of {heuristic.NAME} heuristic)")
            break
        elif current_heuristic > heuristic.target_score:
            bottom_crf_value = current_crf
        elif current_heuristic < heuristic.target_score:
            top_crf_value = current_crf

    closest_value = min(
        all_heuristic_crf_values.items(),
        key=lambda x: abs(x[1] - heuristic.target_score),
    )

    if (
        final_output_video_name is not None
        and not subpart_video_filename(
            video, final_output_video_name, closest_value[0], frame_start, frame_end_raw
        ).exists()
    ):  # in case of accidental deletion when restarting
        _ = ffmpeg.run_ffmpeg_command(
            video,
            subpart_video_filename(
                video,
                final_output_video_name,
                closest_value[0],
                frame_start,
                frame_end_raw,
            ),
            closest_value[0],
            codec,
            frame_start,
            frame_end,
            300,
        )

    if final_output_video_name is not None:
        final_filepath = subpart_video_filename(
            video,
            final_output_video_name,
            closest_value[0],
            frame_start,
            frame_end_raw,
        )
    else:
        final_filepath = None

    heuristic_throughout = heuristic.throughout_video(
        video,
        expect_str(
            ffmpeg.run_ffmpeg_command(
                video,
                "get ffmpeg string",
                closest_value[0],
                codec,
                frame_start,
                frame_end_raw,
                300,
            )
        ),
        source_start_end_frame=(frame_start, frame_end),
        subsample=1,
    )

    for filepath in all_temp_files:
        if filepath == final_filepath:
            continue

        os.remove(filepath.resolve())
        # except Exception:
        #     print("could not delete other temporary filepaths")

    filepath = final_filepath if final_output_video_name else None

    assert testing_start_VMAF is not None
    return rendered_data(
        *closest_value,
        heuristic_throughout,
        filepath,
        start_heuristic_crf_jumping(testing_start_VMAF, closest_value[0]),
    )


def compressing_video(video: videoInputData) -> None:
    # with rich_console.status(
    #     f"Getting metadata of input file ({video.videodata.input_filename})"
    # ):
    #     _input_filename_data = ffmpeg.get_video_metadata(
    #         video.videodata, video.videodata.input_filename
    #     )

    with rich_console.status("Calculating scenes"):
        raw_video_scenes = scene_detection.find_scenes(
            video.videodata, video.minimum_scene_length_seconds
        )

    middle_crf = (video.heuristic.RANGE.start + video.heuristic.RANGE.stop) // 2

    def get_heuristic_value_test(scene: scene_detection.SceneData):
        return render_scene_for_certain_crf_and_get_heuristic_and_path(
            video=video.videodata,
            crf=middle_crf,
            codec=video.codec,
            frame_start=scene.start_frame,
            frame_end=scene.end_frame,
            heuristic=video.heuristic,
            output_video_name=subpart_video_filename(
                video.videodata,
                video.videodata.output_filename,
                middle_crf,
                scene.start_frame,
                scene.end_frame,
            ),
        )

    video_scenes_data = [
        (scene, *get_heuristic_value_test(scene))
        for scene in track(
            raw_video_scenes, "calculating initial heuristic value of scenes"
        )
    ]
    cacheing_process_video_scenes = sorted(
        (
            (scene[0], scene[1])
            for scene in video_scenes_data
            if int(scene[1]) in video.heuristic.CERTAIN_RANGE
        ),
        key=lambda x: x[1],
    )
    manually_process_video_scenes = [
        (scene[0], scene[1])
        for scene in video_scenes_data
        if int(scene[1]) not in video.heuristic.CERTAIN_RANGE
    ]
    manually_process_video_scenes.extend(
        [cacheing_process_video_scenes[0], cacheing_process_video_scenes[-1]]
    )
    cacheing_process_video_scenes = cacheing_process_video_scenes[1:-1]

    # print(cacheing_process_video_scenes, manually_process_video_scenes)
    # _ = input()

    optimal_crf_list = _compress_video_sections_automatically_and_concurrently(
        video,
        raw_video_scenes,
        [x[0] for x in manually_process_video_scenes],
        description="Rendering compulsory renders",
        crf_ranges_of_video_scenes=[
            video.heuristic.RANGE for _ in range(len(manually_process_video_scenes))
        ],
        prior_calculation_results=[
            (middle_crf, x[1]) for x in manually_process_video_scenes
        ],
    )

    # print(optimal_crf_list)
    # _ = input()

    # item = next((x for x in a), None)
    # item = next(x for x in a)
    # next(x for x in the_iterable if x > 3)

    # optimal_crf_list = sorted(optimal_crf_list, key=lambda x: x.scenedata)
    # while scene := cacheing_process_video_scenes.pop():
    for scene in track(cacheing_process_video_scenes, "Rendering scenes with cache"):
        optimal_crf_list = sorted(optimal_crf_list, key=lambda x: x.scenedata.heuristic)
        index_of_largest, largest = next(
            (i, x)
            for i, x in enumerate(optimal_crf_list)
            if x.scenedata.heuristic > scene[1]
        )
        smallest = optimal_crf_list[index_of_largest - 1]

        # print(scene, smallest, largest)
        # _ = input()

        smallest_crf, largest_crf = sorted(
            [
                smallest.scenedata.heuristicjump.end_crf,
                largest.scenedata.heuristicjump.end_crf,
            ]
        )
        print(smallest_crf, largest_crf)

        optimal_crf_list.append(
            optimal_crf_data(
                scene=scene[0],
                scenedata=identify_videosection_optimal_crf(
                    video.videodata,
                    video.videodata.output_filename,
                    video.codec,
                    video.heuristic,
                    scene[0].start_frame,
                    scene[0].end_frame,
                    # crf_range=range(smallest_crf, largest_crf),
                    crf_range=video.heuristic.RANGE,
                    prior_calculation_results=[(middle_crf, scene[1])],
                ),
            )
        )

        # _print_table_of_heuristic_vs_endcrf([x.scenedata for x in optimal_crf_list])
        # _ = input()

    # optimal_crf_list = _compress_video_sections_automatically(
    #     video,
    #     raw_video_scenes,
    #     [x[0] for x in cacheing_process_video_scenes],
    #     description="Using prediction cache",
    #     crf_ranges_of_video_scenes=[],
    #     prior_calculation_results=[],
    # )

    with rich_console.status("Generating graph of data"):
        _save_graph_of_rendered_data(video, optimal_crf_list)

    if video.render_final_video:
        _concatenate_rendered_videos_and_add_audio(
            video, optimal_crf_list, raw_video_scenes
        )

    _print_table_of_heuristic_vs_endcrf([x.scenedata for x in optimal_crf_list])

    # if video.make_comparison_with_blend_filter:
    #     _make_comparison_with_blend_filter()

    print("Input video metadata")
    print(ffmpeg.get_video_metadata(video.videodata, video.videodata.input_filename))
    print("Raw Input video metadata")
    print(
        ffmpeg.get_video_metadata(video.videodata, video.videodata.raw_input_filename)
    )
    if video.render_final_video:
        print("Output video metadata")
        print(
            ffmpeg.get_video_metadata(video.videodata, video.videodata.output_filename)
        )
