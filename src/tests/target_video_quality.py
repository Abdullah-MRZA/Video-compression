from dataclasses import dataclass
from rich.console import Console
from rich.progress import Progress, TimeElapsedColumn
import ffmpeg
import ffmpeg_heuristics
import graph_generate
import os
import subprocess
import scene_detection
import logging
from rich.logging import RichHandler
import time
import concurrent.futures
# import pickle

from rich.traceback import install

_ = install(show_locals=True)

# from rich import print

rich_console = Console()

logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)
log: logging.Logger = logging.getLogger("rich")


progress = Progress(
    # progress.SpinnerColumn(),
    *Progress.get_default_columns(),
    TimeElapsedColumn(),
)


def TEMPORARY_FILENAMES(x: int) -> str:
    """Returns the name of an intermediate file, in a centralised place"""
    return f"{x}-part.mkv"


def is_macbook_screen_closed() -> bool:
    result_val = subprocess.run(
        "ioreg -r -k AppleClamshellState -d 4 | grep AppleClamshellState  | head -1",
        shell=True,
        capture_output=True,
    ).stdout.decode()
    return "yes" == result_val.split()[-1].lower()


@dataclass()
class CompressingVideoTimeData:
    total_time_rendering: float = 0
    total_time_in_heuristic_calculation: float = 0


def compress_video(
    input_filename_with_extension: str,
    ffmpeg_codec_information: ffmpeg.video,
    heuristic_type: ffmpeg_heuristics.heuristic,
    output_filename_with_extension: str | None = None,
    # ...
    start_time_seconds: int = 0,
    end_time_seconds: int = 0,
    # ..
    crop_black_bars: bool = True,
    bit_depth: ffmpeg.bitdepth = "yuv420p10le",
    keyframe_placement: int | None = 200,
    ffmpeg_path: str = "ffmpeg",
    # draw_graph: bool = True,
    extra_current_crf_itterate_amount: int = 1,
    delete_tempoary_files: bool = True,
    scene_detection_threshold: float = 27.0,
    recombine_audio_from_input_file: bool = True,
    # extra_ffmpeg_commands: str | None = None,
    multithreading_threads: int = 1,
    # minimum_scene_length_seconds: int | None = 10,
    compare_final_video_using_difference: str | None = "Comparison_difference.mp4",
) -> CompressingVideoTimeData:
    """
    This does practically all of the calculations
    This splits the video files into scenes, and then compresses them,
    targeting a specific video heuristic
    This also recombines the video at the end
    """

    return
    time_data = CompressingVideoTimeData(0, 0)

    if output_filename_with_extension is None:
        output_filename_with_extension = (
            f"RENDERED - {input_filename_with_extension.rsplit('.', 1)[0]}.mkv"
        )

    crop_black_bars_size: str | None = None  # default value
    if crop_black_bars:  # Assumption is that the black bars don't change in size
        crop_black_bars_size = ffmpeg_heuristics.crop_black_bars_size(
            input_filename_with_extension, ffmpeg_path
        )

    with rich_console.status("Calculating scenes"):
        video_scenes: list[scene_detection.SceneData] = scene_detection.find_scenes(
            video_path=input_filename_with_extension,
            threshold=scene_detection_threshold,
        )

    log.debug(f"{video_scenes=}")
    log.debug(f"Total Scenes in input file: {len(video_scenes)}\n")
    log.debug(
        f"scene lengths (in frames): [{', '.join(str(x.end_frame - x.start_frame) for x in video_scenes)}]"
    )

    # FRAMES_PER_SECOND = video_scenes[0]. / video_scenes[0].end_frame

    @dataclass()
    class VideoData:
        optimal_crf: int
        heuristic_value: float

    # video_data_crf_heuristic: list[tuple[int, float]] = []
    video_data_crf_heuristic: list[VideoData] = []

    def compress_video_part(
        part: int, scenes: scene_detection.SceneData
    ) -> tuple[int, VideoData]:
        # print(f"RUNNING SECTION {part} OF SCENE")
        optimal_crf_value, heuristic_value_of_encode, time_in_heuristic = (
            _compress_video_part(
                input_filename=input_filename_with_extension,
                output_filename=TEMPORARY_FILENAMES(part),  # changed to always use mkv
                video_part_frame_data=scenes,
                heuristic_type=heuristic_type,
                unique_identifier=str(part),
                crop_black_bars_size=crop_black_bars_size,
                bit_depth=bit_depth,
                keyframe_placement=keyframe_placement,
                ffmpeg_codec_information=ffmpeg_codec_information,
                ffmpeg_path=ffmpeg_path,
                extra_current_crf_itterate_amount=extra_current_crf_itterate_amount,
            )
        )
        time_data.total_time_in_heuristic_calculation += time_in_heuristic

        return part, VideoData(
            optimal_crf=optimal_crf_value,
            heuristic_value=heuristic_value_of_encode,
        )

    # with progress:
    #     for i, scenes in progress.track(  # progressive, single-threaded approach
    #         list(enumerate(video_scenes)),  # doesn't work with just enumerate
    #         description="[yellow]Processing scenes[/yellow]",
    #     ):
    #         start_time = time.perf_counter()
    #         video_data_crf_heuristic.append(compress_video_part(i, scenes)[1])
    #         time_data.total_time_rendering += time.perf_counter() - start_time

    start_time = time.perf_counter()  # Multithreaded approach
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=multithreading_threads
    ) as executor:
        # processes = []
        results = list(
            executor.map(compress_video_part, range(len(video_scenes)), video_scenes)
        )

        results = sorted(results)
        video_data_crf_heuristic.extend(x[1] for x in results)
    time_data.total_time_rendering += time.perf_counter() - start_time

    with rich_console.status("Concatenating temporary video files to final file"):
        ffmpeg.concatenate_video_files(
            [TEMPORARY_FILENAMES(x) for x in range(len(video_scenes))],
            output_filename_with_extension,
            ffmpeg_path,
        )

    with rich_console.status("Generating graph of data"):
        with graph_generate.LinegraphImage(
            filename_without_extension="Video_information_per_scene",
            title_of_graph=f"CRF and {heuristic_type.NAME} throughout video",
            x_axis_name="Frames",
        ) as graph:
            graph.add_linegraph(
                x_data=[x.start_frame for x in video_scenes],
                y_data=[x.optimal_crf for x in video_data_crf_heuristic],
                name="CRF",
                mode="lines+markers",
                on_left_right_side="right",
                y_axis_range=ffmpeg_codec_information.ACCEPTED_CRF_RANGE,
            )

            subsample_amount = 2

            heuristic_data_throughout_video: list[float] = (
                heuristic_type.throughout_video(
                    source_video_path=input_filename_with_extension,
                    encoded_video_path=output_filename_with_extension,
                    ffmpeg_path=ffmpeg_path,
                    subsample=subsample_amount,
                )
            )

            graph.add_linegraph(
                x_data=list(
                    x * subsample_amount
                    for x in range(len(heuristic_data_throughout_video))
                ),
                # y_data=[x[1] for x in video_data_crf_heuristic], # This is overall from the function of each splitvideo
                y_data=heuristic_data_throughout_video,
                name=heuristic_type.NAME,
                mode="lines",
                on_left_right_side="left",
                y_axis_range=heuristic_type.RANGE,
                # testing_y_axis_range=dict(range=[0, 100]),
            )

            graph.add_linegraph(
                x_data=[x.start_frame for x in video_scenes],
                y_data=[x.heuristic_value for x in video_data_crf_heuristic],
                name=f"{heuristic_type.NAME} target",
                mode="lines+markers",
                on_left_right_side="left",
                y_axis_range=heuristic_type.RANGE,
            )

    # graph = graph_generate.linegraph()
    # graph.add_linegraph()

    if delete_tempoary_files:
        with rich_console.status("Deleting tempoary video files"):
            for x in range(len(video_scenes)):
                try:
                    os.remove(TEMPORARY_FILENAMES(x))
                except FileNotFoundError:
                    log.error("TEMP FILE NOT FOUND...  NOT DELETED")

    if recombine_audio_from_input_file:
        with rich_console.status("Recombining audio from source with rendered video"):
            # Do I need this check?
            if ffmpeg_heuristics.FfprobeInformation.check_contains_any_audio(
                input_filename_with_extension, "ffprobe"
            ):
                try:
                    _ = subprocess.run(
                        " ".join(
                            [
                                ffmpeg_path,
                                f"-i {output_filename_with_extension}",
                                f"-i {input_filename_with_extension}",
                                "-c copy",
                                "-map 0:v:0",  # is there a bug here........?
                                "-map 1:a",  # copy all audio
                                f"TEMP-{output_filename_with_extension}",
                            ]
                        ),
                        shell=True,
                        check=True,
                    )
                    os.remove(output_filename_with_extension)
                    os.rename(
                        f"TEMP-{output_filename_with_extension}",
                        output_filename_with_extension,
                    )
                except FileNotFoundError:
                    print("File not found error for audio combination")
                except subprocess.CalledProcessError:
                    print(
                        "Process failed because did not return a successful return code."
                    )
            else:
                print("NOTICE: INPUT FILE CONTAINED NO AUDIO!! (no audio to transfer)")

    if compare_final_video_using_difference is not None:
        ffmpeg.visual_comparison_of_video_with_blend_filter(
            source_video_path=input_filename_with_extension,
            encoded_video_path=output_filename_with_extension,
            ffmpeg_path=ffmpeg_path,
            output_filename_with_extension=compare_final_video_using_difference,
        )

    return time_data


def _compress_video_part(
    input_filename: str,
    output_filename: str,
    video_part_frame_data: scene_detection.SceneData,
    heuristic_type: ffmpeg_heuristics.heuristic,
    unique_identifier: str,
    crop_black_bars_size: str | None,
    bit_depth: ffmpeg.bitdepth,
    keyframe_placement: int | None,
    ffmpeg_codec_information: ffmpeg.video,
    ffmpeg_path: str,
    extra_current_crf_itterate_amount: int = 1,
) -> tuple[int, float, float]:
    """
    Using a binary search approach on the whole range of CRF
    Would identify the ideal CRF for the closest heuristic value??
    Returns the heuristic value of the result
    """
    # use a 'binary search' approach? Is this optimal? (doubt it, but definitely functional)

    total_time_in_heuristic_calculation_local: float = 0
    tempoary_video_file_name: str = f"TEMPORARY-ENCODE-{unique_identifier}.mkv"

    with ffmpeg.FfmpegCommand(
        input_filename=input_filename,
        output_filename=tempoary_video_file_name,
        codec_information=ffmpeg_codec_information,
        start_frame=video_part_frame_data.start_frame,
        end_frame=video_part_frame_data.end_frame,
        crop_black_bars_size=crop_black_bars_size,
        bit_depth=bit_depth,
        keyframe_placement=keyframe_placement,
        ffmpeg_path=ffmpeg_path,
    ) as video_command:
        bottom_crf_value = min(ffmpeg_codec_information.ACCEPTED_CRF_RANGE)
        top_crf_value = max(ffmpeg_codec_information.ACCEPTED_CRF_RANGE)

        all_heuristic_crf_data: dict[float, int] = {}

        # at the end point, we would be doing the same calculation twice
        while (
            current_crf := (
                (top_crf_value + bottom_crf_value)
                // (2 * extra_current_crf_itterate_amount)
            )
            * extra_current_crf_itterate_amount
        ) not in all_heuristic_crf_data.values():
            # Prevent running when screen is closed
            while is_macbook_screen_closed():
                time.sleep(1)

            log.debug(f"RUNNING CRF VALUE {current_crf}")
            video_command.run_ffmpeg_command(current_crf)

            log.debug(f"Determining heuristic value for CRF value {current_crf}")
            start_time = time.perf_counter()
            # current_crf_heuristic: float = heuristic_type.summary_of_overall_video(
            current_crf_heuristic = heuristic_type.summary_of_overall_video(
                source_video=input_filename,
                compressed_video=tempoary_video_file_name,
                source_start_end_frame=(
                    video_part_frame_data.start_frame,
                    video_part_frame_data.end_frame,
                ),
                encode_start_end_frame=(
                    0,
                    ffmpeg.get_video_metadata(tempoary_video_file_name).total_frames,
                ),
                ffmpeg_path=ffmpeg_path,
            )
            total_time_in_heuristic_calculation_local += (
                time.perf_counter() - start_time
            )

            all_heuristic_crf_data.update({current_crf_heuristic: current_crf})

            # ASSUMPTION THAT BIGGER IS BETTER (WARNING --> MAY NOT ALWAYS BE THE CASE??)
            # Also, is round too imprecise?
            if round(current_crf_heuristic) == heuristic_type.target_score:
                log.debug("EXACT HEURISTIC VALUE MATCHED!")
                break  # very unlikely to get here
            elif current_crf_heuristic > heuristic_type.target_score:
                bottom_crf_value = current_crf
            elif current_crf_heuristic < heuristic_type.target_score:
                top_crf_value = current_crf

            log.debug(
                f"    FINISHED RUNNING {current_crf} -> {current_crf_heuristic} compared "
                + f"to {heuristic_type.target_score} | {all_heuristic_crf_data}"
            )
            # _ = input("continue?")

        closest_crf_value_to_target_heuristic = min(
            (abs(x[0] - heuristic_type.target_score), x[1])
            for x in all_heuristic_crf_data.items()
        )[1]
        # print(closest_crf_value_to_target_heuristic)

        # closest_crf_value_to_target_heuristic = (
        #     closest_crf_value_to_target_heuristic[1]
        # )

        try:
            os.remove(tempoary_video_file_name)
        except FileNotFoundError:
            log.error(f"Failed to remove file '{tempoary_video_file_name}'")

        log.info(f"OPTIMAL CRF VALUE IS {closest_crf_value_to_target_heuristic}")

        video_command.run_ffmpeg_command(
            closest_crf_value_to_target_heuristic,
            override_output_file_name=output_filename,
        )

        all_crf_heuristic_data = {v: k for k, v in all_heuristic_crf_data.items()}
        return (
            closest_crf_value_to_target_heuristic,
            all_crf_heuristic_data[closest_crf_value_to_target_heuristic],
            total_time_in_heuristic_calculation_local,
        )
        # return closest_crf_value_to_target_heuristic
