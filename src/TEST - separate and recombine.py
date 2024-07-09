import ffmpeg
import os
from rich import print
import ffmpeg_heuristics
import graph_generate
import scene_detection
# import subprocess

"""
Program to test separating a video file, and then to recombine it together?
"""

# input_file = "short-smallest.mp4"
input_file = "large-trim.mp4"
output_file = "temp.mp4"

accurate_seek = ffmpeg.ffms2seek(input_file, input_file)


class SplitRejoinOnScenesTest:
    def __init__(self) -> None:
        # scenes = scene_detection.find_scenes(input_file, threshold=50)
        scenes = scene_detection.find_scenes(input_file, 0)
        output_file_names = [f"{x}-{output_file}" for x in range(len(scenes))]

        self.split_usual_method(scenes, output_file_names)
        # self.split_using_segment_muxer_fragile_implementation(scenes, output_file_names)

        ffmpeg.concatenate_video_files(output_file_names, output_file, "ffmpeg")

        for file in output_file_names:
            os.remove(file)

        del output_file_names

        # vmaf = ffmpeg_heuristics.VMAF(90).throughout_video(
        #     input_file, output_file, "ffmpeg", subsample=1
        # )
        vmaf = ffmpeg_heuristics.VMAF(90).throughout_video(
            input_file,
            output_file,
            "ffmpeg",
            accurate_seek,
            subsample=1,
            encode_start_end_frame=(10, 100),
            source_start_end_frame=(10, 100),
        )

        with graph_generate.LinegraphImage(
            "comparison_graph",
            "png",
            "TEST - compare VMAF with almost lossless",
            "frames",
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

        print_frames_count(input_file, input_file)
        print_frames_count(output_file, output_file)

    ########## Spliting methods

    def split_usual_method(
        self, scenes: list[scene_detection.SceneData], output_file_names: list[str]
    ) -> None:
        for i, scene in enumerate(scenes):
            with ffmpeg.FfmpegCommand(
                input_file,
                # ffmpeg.SVTAV1(),
                ffmpeg.H264(preset="fast"),
                scene.start_frame,
                scene.end_frame,
                output_file_names[i],
                "ffmpeg",
                None,
                "yuv420p10le",
                300,
            ) as command:
                command.run_ffmpeg_command(
                    2,  # lossless
                )

    def split_using_segment_muxer_fragile_implementation(
        self, scenes: list[scene_detection.SceneData], output_file_names: list[str]
    ):
        # for scene, filename in zip(scenes, output_file_names):
        segment_times = ",".join(str(x.start_timecode) for x in scenes)
        _ = os.system(
            f"ffmpeg -i {input_file} -c copy -reset_timestamps 1 -segment_times {segment_times} -y -f segment %02d-{output_file}"
        )
        _ = input(
            f"ffmpeg -i {input_file} -c copy -reset_timestamps 1 -segment_times {segment_times} -y -f segment %02d-{output_file}"
        )
        _ = input(len([str(x.start_timecode) for x in scenes]))


def main() -> None:
    """Running tests to ensure functions are working"""
    _ = (
        SplitRejoinOnScenesTest()
    )  # This has shown that it is definitely a video splitting problem


if __name__ == "__main__":
    main()
