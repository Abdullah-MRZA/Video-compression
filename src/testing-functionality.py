import ffmpeg
import os
from rich import print
import ffmpeg_heuristics
import graph_generate
import scene_detection

input_file = "short-smallest.mp4"
output_file = "testing-functionality-file.mp4"


def split_rejoin_on_scenes_test():
    scenes = scene_detection.find_scenes(input_file, threshold=27)
    output_file_names = [f"{x}-{output_file}" for x in range(len(scenes))]
    for i, scene in enumerate(scenes):
        with ffmpeg.FfmpegCommand(
            input_file,
            ffmpeg.SVTAV1(),
            scene.start_timecode,
            scene.end_timecode,
            output_file_names[i],
            "ffmpeg",
            None,
            "yuv420p10le",
            300,
        ) as command:
            command.run_ffmpeg_command(
                2,  # lossless
            )

    ffmpeg.concatenate_video_files(output_file_names, output_file, "ffmpeg")

    for file in output_file_names:
        os.remove(file)

    del output_file_names

    vmaf = ffmpeg_heuristics.VMAF(90).throughout_video(
        input_file, output_file, "ffmpeg", subsample=1
    )

    with graph_generate.linegraph_image(
        "comparison_graph", "png", "TEST - compare VMAF with almost lossless", "frames"
    ) as graph:
        graph.add_linegraph(
            list(range(len(vmaf))), vmaf, "vmaf", "lines", "left", range(0, 101)
        )

    ffmpeg.visual_comparison_of_video_with_blend_filter(
        input_file,
        output_file,
        "ffmpeg",
        "TEST - compare with virtually lossless.mp4",
    )

    # At the end
    print("vmaf data:")
    print(vmaf)


def main() -> None:
    """Running tests to ensure functions are working"""
    split_rejoin_on_scenes_test()  # This has shown that it is definitely a video splitting problem


if __name__ == "__main__":
    main()
