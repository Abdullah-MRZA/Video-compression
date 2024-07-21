import ffmpeg
from rich import print
import os
import ffmpeg_heuristics
import graph_generate
import scene_detection
import subprocess
# from rich import print

"""
Program to test separating a video file, and then to recombine it together?
"""

# input_file = "short-smallest.mp4"
INPUT_FILE = "input.mkv"
OUTPUT_FILE_NAME = "temp.mp4"

accurate_seek = ffmpeg.ffms2seek(INPUT_FILE, INPUT_FILE)


def split_usual_method(
    scenes: list[scene_detection.SceneData], output_file_names: list[str]
) -> None:
    for i, scene in enumerate(scenes):
        with ffmpeg.FfmpegCommand(
            INPUT_FILE,
            # ffmpeg.SVTAV1(),
            ffmpeg.H264(preset="fast"),
            scene.start_frame,
            scene.end_frame,
            output_file_names[i],
            "ffmpeg",
            None,
            "yuv420p10le",
            300,
            accurate_seek,
        ) as command:
            command.run_ffmpeg_command(
                # 2,  # lossless
                30,
            )
    with ffmpeg.FfmpegCommand(
        INPUT_FILE,
        # ffmpeg.SVTAV1(),
        ffmpeg.H264(preset="fast"),
        0,
        ffmpeg.get_video_metadata(INPUT_FILE).total_frames,
        OUTPUT_FILE_NAME,
        "ffmpeg",
        None,
        "yuv420p10le",
        300,
        accurate_seek,
    ) as command:
        command.run_ffmpeg_command(
            # 2,  # lossless
            30,
        )
    _ = subprocess.run(
        f'ffmpeg -hide_banner -loglevel error -r 30.0 -i {INPUT_FILE} -c:v libx264 -preset fast -an -pix_fmt yuv420p10le -y -crf 30 -g 300 "no_ffms2.mp4"',
        shell=True,
        check=True,
    )


def draw_vmaf_graph(
    input_file: str,
    output_file_names: list[str],
    scenes_frames: list[scene_detection.SceneData],
) -> None:
    vmaf_values: list[float] = []
    vmaf_overall_end: list[float] = []
    vmaf_overall_end_withoutffms2: list[float] = []

    for scene_frame, output_file_name in zip(scenes_frames, output_file_names):
        vmaf_values.extend(
            ffmpeg_heuristics.VMAF(90).throughout_video_vapoursynth(
                input_file,
                output_file_name,
                "ffmpeg",
                accurate_seek,
                subsample=1,
                # encode_start_end_frame=(10, 100),
                source_start_end_frame=(scene_frame.start_frame, scene_frame.end_frame),
            )
        )

    vmaf_overall_end = ffmpeg_heuristics.VMAF(90).throughout_video_vapoursynth(
        input_file,
        OUTPUT_FILE_NAME,
        "ffmpeg",
        accurate_seek,
        subsample=1,
        # encode_start_end_frame=(10, 100),
        source_start_end_frame=(
            0,
            ffmpeg.get_video_metadata(input_file).total_frames,
        ),
    )

    vmaf_overall_end_withoutffms2 = ffmpeg_heuristics.VMAF(
        90
    ).throughout_video_vapoursynth(
        input_file,
        "no_ffms2.mp4",
        "ffmpeg",
        accurate_seek,
        subsample=1,
        # encode_start_end_frame=(10, 100),
        source_start_end_frame=(
            0,
            ffmpeg.get_video_metadata(input_file).total_frames,
        ),
    )

    with graph_generate.LinegraphImage(
        "comparison_graph",
        "png",
        "TEST - compare VMAF with almost lossless",
        "frames",
    ) as graph:
        graph.add_linegraph(
            list(range(len(vmaf_values))),
            vmaf_values,
            "vmaf",
            "lines",
            "left",
            ffmpeg_heuristics.VMAF.RANGE,
        )
        graph.add_linegraph(
            list(range(len(vmaf_values))),
            vmaf_overall_end,
            "vmaf at end",
            "lines",
            "right",
            ffmpeg_heuristics.VMAF.RANGE,
        )
        graph.add_linegraph(
            list(range(len(vmaf_values))),
            vmaf_overall_end_withoutffms2,
            "vmaf without ffms2",
            "lines",
            "right",
            ffmpeg_heuristics.VMAF.RANGE,
        )

    ffmpeg.visual_comparison_of_video_with_blend_filter(
        INPUT_FILE,
        "combined_video.mkv",
        "ffmpeg",
        "TEST - compare with virtually lossless.mp4",
    )


scenes = scene_detection.find_scenes(INPUT_FILE, 0)
OUTPUT_FILE_NAMES = [f"{x}-{OUTPUT_FILE_NAME}" for x in range(len(scenes))]

split_usual_method(scenes, OUTPUT_FILE_NAMES)
ffmpeg.concatenate_video_files(OUTPUT_FILE_NAMES, "combined_video.mkv", "ffmpeg")
draw_vmaf_graph(INPUT_FILE, OUTPUT_FILE_NAMES, scenes)


for file in OUTPUT_FILE_NAMES:
    os.remove(file)
# os.remove(OUTPUT_FILE_NAME)

print(ffmpeg.get_video_metadata(INPUT_FILE))
print(ffmpeg.get_video_metadata(OUTPUT_FILE_NAME))
