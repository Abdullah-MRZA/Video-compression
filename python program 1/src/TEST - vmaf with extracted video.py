import ffmpeg
from rich import print
import random
import ffmpeg_heuristics

# input_file = "small-trim.mp4"
input_file = "input-tiny.mp4"
# input_file = "large-trim.mp4"
# input_file = "original.mp4"

temp_compare_file = "temp-input.mp4"
video_data = ffmpeg.get_video_metadata("ffprobe", input_file)

"""
    This test passes
"""

accurate_seek = ffmpeg.ffms2seek(input_file, input_file)


with ffmpeg.FfmpegCommand(
    input_file,
    ffmpeg.H264(),
    0,
    video_data.total_frames,
    temp_compare_file,
    "ffmpeg",
    None,
    "yuv420p10le",
    300,
    # accurate_seek,
    None,
) as ffmpeg_command:
    ffmpeg_command.run_ffmpeg_command(crf_value=20)


minimum_expected_vmaf = int(
    min(
        ffmpeg_heuristics.VMAF(90).throughout_video(
            input_file, temp_compare_file, "ffmpeg", accurate_seek, subsample=1
        )
    )
)

# _ = input(minimum_expected_vmaf)

video_data_other = ffmpeg.get_video_metadata("ffprobe", temp_compare_file)

print(video_data)
# _ = input()
print(video_data_other)
# _ = input()
print(f"{minimum_expected_vmaf=}")


def mean(x: list[int | float]) -> float:
    return sum(x) / len(x)


total_tests = 0
test_samples: list[float] = []

try:
    while True:
        start_frame, end_frame = sorted(
            [
                int(random.random() * video_data.total_frames),
                int(random.random() * video_data.total_frames),
            ]
        )

        # found this in experimentation to be an issue :grin:
        if (end_frame - start_frame) < 0.05:
            continue

        test_samples.append(end_frame - start_frame)

        with ffmpeg.FfmpegCommand(
            input_file,
            ffmpeg.H264(),
            start_frame,
            end_frame,
            temp_compare_file,
            "ffmpeg",
            None,
            "yuv420p10le",
            300,
            accurate_seek,
        ) as ffmpeg_command:
            ffmpeg_command.run_ffmpeg_command(crf_value=20)

        vmaf_got = ffmpeg_heuristics.VMAF(90).summary_of_overall_video(
            input_file,
            temp_compare_file,
            "ffmpeg",
            accurate_seek,
            source_start_end_frame=(start_frame, end_frame),
        )

        print(f"{vmaf_got=}")

        # vmaf_got_throughout = mean(
        #     ffmpeg_heuristics.VMAF(90).throughout_video(
        #         input_file,
        #         compare_file,
        #         "ffmpeg",
        #         source_start_end_frame=(start_frame, end_frame),
        #     )
        # )

        total_tests += 1
        assert vmaf_got >= minimum_expected_vmaf, "VMAF IS TOO LOW"
        # assert round(vmaf_got) == round(vmaf_got_throughout), "VMAF is different!"
finally:
    print(f"Total: {total_tests}")
    print(f"Total tests: {sorted(test_samples)}")
