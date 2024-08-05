from dataclasses import dataclass
from pathlib import Path
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
import time

from rich.console import Console
# import pickle

rich_console = Console()
progress = Progress(
    *Progress.get_default_columns(),
    TimeElapsedColumn(),
)


@dataclass
class videoInputData:
    videodata: videodata.RawVideoData
    codec: ffmpeg.VideoCodec
    heuristic: ffmpeg_heuristics.heuristic
    minimum_scene_length_seconds: float
    audio_commands: str = "-c:a copy"
    subtitle_commands: str = "-c:s copy"
    multithreading_threads: int = 2
    scenes_length_sort: Literal["chronological", "largest first", "smallest first"] = (
        "largest first"  # ensures that CPU always being used
    )
    make_comparison_with_blend_filter: bool = False
    render_final_video: bool = False


def compressing_video(video: videoInputData) -> None:
    with rich_console.status(
        f"Getting metadata of input file ({video.videodata.input_filename})"
    ):
        input_filename_data = ffmpeg.get_video_metadata(
            video.videodata, video.videodata.input_filename
        )
        print(input_filename_data)

    with rich_console.status("Calculating scenes"):
        raw_video_scenes = scene_detection.find_scenes(
            video.videodata, video.minimum_scene_length_seconds
        )
        scale_factor = raw_video_scenes[-1].end_frame / input_filename_data.total_frames
        raw_video_scenes = [
            scene_detection.SceneData(
                int(x.start_frame / scale_factor), int(x.end_frame / scale_factor)
            )
            for x in raw_video_scenes
        ]
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

    optimal_crf_list: list[
        tuple[scene_detection.SceneData, compress_video_section_data]
    ] = []

    def compress_video_section_call(
        section: int, video_section: scene_detection.SceneData
    ) -> tuple[int, scene_detection.SceneData, compress_video_section_data]:
        video_section_data = identify_videosection_optimal_crf(
            video.videodata,
            # temporary_video_file_names(section, video.videodata.input_filename.parent),
            # input_filename_data,
            video.codec,
            video.heuristic,
            video_section.start_frame,
            video_section.end_frame,
            # min(
            #     video_section.end_frame,
            #     video_section.start_frame + round(10 * input_filename_data.frame_rate),
            # ),
            # video.videodata.vapoursynth_script.vapoursynth_seek,
        )

        # TODO: add section for rendering video
        if video.render_final_video:
            _ = ffmpeg.run_ffmpeg_command(
                video.videodata,
                Path(
                    temporary_video_file_names(
                        section,
                        Path(),
                    ),
                ),
                video_section_data.crf,
                video.codec,
                video_section.start_frame,
                video_section.end_frame,
                300,
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

    # with rich_console.status("Concatenating intermediate files"):
    #     ffmpeg.concatenate_video_files(
    #         [
    #             temporary_video_file_names(x, video.videodata.input_filename.parent)
    #             for x in range(len(video_scenes))
    #         ],
    #         video.videodata.output_filename,
    #     )

    with rich_console.status("Generating graph of data"):
        with graph_generate.LinegraphImage(
            filename="video_graph",
            x_axis_name="frames",
            title_of_graph=f"CRF & {video.heuristic.NAME} - {video.videodata.raw_input_filename} to {video.videodata.output_filename} ({video.codec.NAME})",
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
                        y for x in optimal_crf_list for y in x[1].heuristic_throughout
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
                    for y in (x[0].start_frame, x[0].end_frame)
                ],
                y_data=[y[1].heuristic for x in optimal_crf_list for y in (x, x)],
                name_of_axes=f"target {video.heuristic.NAME}",
                y_axis_range=video.heuristic.RANGE,
                marker="x",
                colour="blue",
            )

    if video.render_final_video:
        ffmpeg.concatenate_video_files(
            [
                temporary_video_file_names(x, Path())
                for x in range(len(raw_video_scenes))
            ],
            video.videodata.output_filename,
        )

        try:
            _ = [
                os.remove(temporary_video_file_names(x, Path()))
                for x in range(len(raw_video_scenes))
            ]
        except Exception:
            print("Error deleting temp files")

    # for x in range(len(video_scenes)):
    #     print(temporary_video_file_names(x))
    #     print(ffmpeg.get_video_metadata(temporary_video_file_names(x)))
    #     os.remove(temporary_video_file_names(x))

    # with rich_console.status("Combining audio+subtitles from source video"):
    #     ffmpeg.combine_audio_and_subtitle_streams_from_another_video(
    #         video.full_input_filename,
    #         video.full_output_filename,
    #         video.audio_commands,
    #         video.subtitle_commands,
    #     )

    # if video.make_comparison_with_blend_filter:
    #     with rich_console.status("Making a visual comparison with blend filter"):
    #         ffmpeg.visual_comparison_of_video_with_blend_filter(
    #             seeking_data_input_file,
    #             video.full_output_filename,
    #             "visual_comparison.mp4",
    #         )

    print(optimal_crf_list)

    print(ffmpeg.get_video_metadata(video.videodata, video.videodata.input_filename))
    if video.render_final_video:
        print(
            ffmpeg.get_video_metadata(video.videodata, video.videodata.output_filename)
        )
    # print(ffmpeg.get_video_metadata(video.full_output_filename))


def temporary_video_file_names(position: int, filepath_for_render: Path) -> Path:
    # , extension: str = "mkv"
    return filepath_for_render / Path(f"temp-{position}.mkv")


@dataclass()
class compress_video_section_data:
    crf: int
    heuristic: float
    heuristic_throughout: list[float]


@file_cache.cache(
    sub_directory=Path("videosection_crf"),
    persistent_after_termination=True,  # False
)
def identify_videosection_optimal_crf(
    video: videodata.RawVideoData,
    codec: ffmpeg.VideoCodec,
    heuristic: ffmpeg_heuristics.heuristic,
    frame_start: int,
    frame_end: int,
) -> compress_video_section_data:
    """
    This function finds the optimal CRF value for a target quality heuristic
    This does not render the video itself, and is thus a pure function
    """
    bottom_crf_value = min(codec.ACCEPTED_CRF_RANGE)
    top_crf_value = max(codec.ACCEPTED_CRF_RANGE)

    all_heuristic_crf_values: dict[int, float] = {}

    # if not os.path.exists(
    #     f"{full_input_filename_part}-{frame_start}-{frame_end}-{codec}.tempfile"
    # ):

    # def expect[T](data: T) -> T:
    #     assert data is not None, "Should never be None"
    #     return data

    def expect_str(data: str | None) -> str:
        assert data is not None, "Should never be None"
        return data

    @file_cache.cache()
    def _render_for_certain_crf(crf: int) -> float:
        crf_ffmpeg_command = ffmpeg.run_ffmpeg_command(
            video,
            None,
            current_crf,
            codec,
            frame_start,
            frame_end,
            300,
        )
        current_heuristic = heuristic.summary_of_overall_video(
            video,
            expect_str(crf_ffmpeg_command),
            source_start_end_frame=(frame_start, frame_end),
            subsample=2,
        )
        print(current_heuristic)
        return current_heuristic

    while (
        current_crf := (top_crf_value + bottom_crf_value) // 2
    ) not in all_heuristic_crf_values.keys():
        while os.path.isfile("STOP.txt"):
            time.sleep(1)

        current_heuristic = _render_for_certain_crf(current_crf)

        all_heuristic_crf_values.update({current_crf: current_heuristic})

        # if round(current_heuristic) == heuristic.target_score:
        if abs(current_heuristic - heuristic.target_score) <= 0:
            print(f"Exact match (of {heuristic.NAME} heuristic)")
            break
        elif current_heuristic > heuristic.target_score:
            bottom_crf_value = current_crf
        elif current_heuristic < heuristic.target_score:
            top_crf_value = current_crf

        # _ = input()

    closest_value = min(
        all_heuristic_crf_values.items(),
        key=lambda x: abs(x[1] - heuristic.target_score),
    )

    heuristic_throughout = heuristic.throughout_video(
        video,
        expect_str(
            ffmpeg.run_ffmpeg_command(
                video,
                None,
                current_crf,
                codec,
                frame_start,
                frame_end,
                300,
            )
        ),
        source_start_end_frame=(frame_start, frame_end),
        subsample=1,
    )

    return compress_video_section_data(*closest_value, heuristic_throughout)


if __name__ == "__main__":
    start_time = time.perf_counter()
    end_time = time.perf_counter()
    print(f"Total time elapsed: {end_time - start_time}")
