import ffmpeg
import ffmpeg_heuristics
import scene_detection
import graph_generate

from rich.progress import Progress, TimeElapsedColumn
from rich import print
import concurrent.futures
# import os

progress = Progress(
    *Progress.get_default_columns(),
    TimeElapsedColumn(),
)


def compressing_video(
    full_input_filename: str,
    full_output_filename: str,
    codec: ffmpeg.video,
    heuristic: ffmpeg_heuristics.heuristic,
    # scene_detection_threshold: int = 27,
    minimum_scene_length_seconds: float,
    multithreading_threads: int = 2,
) -> None:
    video_scenes = scene_detection.find_scenes(
        full_input_filename, minimum_scene_length_seconds
    )

    print(video_scenes)

    input_filename_data = ffmpeg.get_video_metadata("ffprobe", full_input_filename)

    seeking_data_input_file = ffmpeg.ffms2seek(full_input_filename, full_input_filename)

    # for i, video_section in enumerate(video_scenes):
    # with progress:
    #     for i, video_section in progress.track(list(enumerate(video_scenes))):
    def compress_video_section_call(
        section: int, video_section: scene_detection.SceneData
    ) -> tuple[int, int, int, float, list[float]]:
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
            video_section.start_frame,
            optimal_crf,
            heuristic_reached,
            heuristic_throughout,
        )

    # for i, video_section in enumerate(video_scenes):
    #     optimal_crf_list.append(
    #         (video_section.start_frame, *compress_video_section_call(i, video_section))
    #     )

    optimal_crf_list: list[tuple[int, int, float, list[float]]] = []

    with concurrent.futures.ThreadPoolExecutor(multithreading_threads) as executor:
        results = list(
            executor.map(
                compress_video_section_call, range(len(video_scenes)), video_scenes
            )
        )
        results = sorted(results)
        optimal_crf_list = [x[1:] for x in results]

    ffmpeg.concatenate_video_files(
        [_temporary_file_names(x) for x in range(len(video_scenes))],
        full_output_filename,
        "ffmpeg",
    )

    # with open("concat.vpy", "w") as f:
    #     clips = [f"clip{x}" for x in range(len(video_scenes))]
    #     clips_text = [
    #         f'{clips[x]} = core.ffms2.Source(source="{_temporary_file_names(x)}")'
    #         for x in range(len(video_scenes))
    #     ]
    #     text = "import vapoursynth as vs\ncore = vs.core\n"
    #     text += "\n".join(clips_text)
    #     text += f"\ntotal_clip = {' + '.join(clips)}\n"
    #     text += "total_clip.set_output(0)"
    #     _ = f.write(text)
    #
    #     print(
    #         f"vspipe -c y4m concat.vpy - | ffmpeg -i - -y -c copy {full_output_filename}"
    #     )
    #     _ = os.system(
    #         f"vspipe -c y4m concat.vpy - | ffmpeg -i - -y -c copy {full_output_filename}"
    #     )

    with graph_generate.LinegraphImage(
        "video_graph",
        "png",
        f"CRF & {heuristic.NAME} - {full_input_filename} to {full_output_filename}",
        "frames",
    ) as graph_instance:
        graph_instance.add_linegraph(
            x_data=[x[0] for x in optimal_crf_list],
            y_data=[x[1] for x in optimal_crf_list],
            name="CRF",
            mode="lines+markers",
            on_left_right_side="left",
            y_axis_range=codec.ACCEPTED_CRF_RANGE,
        )
        # graph_instance.add_linegraph(
        #     x_data=list(range(input_filename_data.total_frames)),
        #     y_data=heuristic.throughout_video(
        #         full_input_filename,
        #         # "TEMP-1.mkv",
        #         full_output_filename,
        #         "ffmpeg",
        #         seeking_data_input_file,
        #         subsample=1,
        #     ),
        #     name=f"found {heuristic.NAME}",
        #     mode="lines",
        #     on_left_right_side="right",
        #     y_axis_range=heuristic.RANGE,
        # )
        graph_instance.add_linegraph(
            x_data=list(range(len([y for x in optimal_crf_list for y in x[3]]))),
            y_data=[y for x in optimal_crf_list for y in x[3]],
            name=f"found {heuristic.NAME}",
            mode="lines",
            on_left_right_side="right",
            y_axis_range=heuristic.RANGE,
        )
        graph_instance.add_linegraph(
            x_data=[x[0] for x in optimal_crf_list],
            y_data=[x[2] for x in optimal_crf_list],
            name=heuristic.NAME,
            mode="lines+markers",
            on_left_right_side="right",
            y_axis_range=heuristic.RANGE,
        )

    for x in range(len(video_scenes)):
        print(_temporary_file_names(x))
        print(ffmpeg.get_video_metadata("ffprobe", _temporary_file_names(x), False))

    # for x in range(len(video_scenes)):
    #     os.remove(_temporary_file_names(x))

    # if input_filename_data.contains_audio:
    #     ...

    ffmpeg.visual_comparison_of_video_with_blend_filter(
        full_input_filename, full_output_filename, "ffmpeg", "visual_comparison.mkv"
    )

    print(ffmpeg.get_video_metadata("ffprobe", full_input_filename, False))
    print(ffmpeg.get_video_metadata("ffprobe", full_output_filename, False))


def _temporary_file_names(position: int) -> str:
    return f"TEMP-{position}.mkv"


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
        full_input_filename_part,
        codec,
        frame_start,
        frame_end,
        full_output_filename,
        "ffmpeg",
        None,
        "yuv420p10le",
        300,
        input_file_script_seeking,
    ) as video_command:
        bottom_crf_value = min(codec.ACCEPTED_CRF_RANGE)
        top_crf_value = max(codec.ACCEPTED_CRF_RANGE)

        all_heuristic_crf_values: dict[int, float] = {}

        # temp_first_done = False
        while (
            current_crf := (top_crf_value + bottom_crf_value) // 2
        ) not in all_heuristic_crf_values.keys():
            # while not temp_first_done:
            #     temp_first_done = True
            video_command.run_ffmpeg_command(current_crf)
            # video_command.run_ffmpeg_command(40)

            current_heuristic = heuristic.summary_of_overall_video(
                full_input_filename_part,
                full_output_filename,
                "ffmpeg",
                input_file_script_seeking,
                source_start_end_frame=(frame_start, frame_end),
            )

            print(current_heuristic)

            all_heuristic_crf_values.update({current_crf: current_heuristic})
            # all_heuristic_crf_values.update({40: current_heuristic})

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
            video_command.run_ffmpeg_command(closest_value[0])

        heuristic_throughout = heuristic.throughout_video(
            full_input_filename_part,
            full_output_filename,
            "ffmpeg",
            input_file_script_seeking,
            source_start_end_frame=(frame_start, frame_end),
            subsample=1,
        )

        return *closest_value, heuristic_throughout


compressing_video(
    # "input_mov.mp4",
    # "input-tiny.mp4",
    "big.mp4",
    "temp.mkv",
    # ffmpeg.H264(tune="animation", preset="veryfast"),
    ffmpeg.SVTAV1(preset=6),
    ffmpeg_heuristics.VMAF(94),
    # scene_detection_threshold=40,
    minimum_scene_length_seconds=0,
    multithreading_threads=2,
)
