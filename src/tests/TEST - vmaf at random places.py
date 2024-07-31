import ffmpeg
from rich import print
import random
import ffmpeg_heuristics

input_file = "small-trim.mp4"
compare_file = "small-trim-crf.mp4"

# input_file = "large-trim.mp4"
# compare_file = "large-trim-crf.mp4"

accurate_seek = ffmpeg.ffms2seek(input_file, input_file)

minimum_expected_vmaf = min(
    ffmpeg_heuristics.VMAF(90).throughout_video(
        input_file, compare_file, "ffmpeg", accurate_seek, subsample=1
    )
)

# _ = input(minimum_expected_vmaf)

video_data = ffmpeg.get_video_metadata("ffprobe", input_file)
video_data_other = ffmpeg.get_video_metadata("ffprobe", compare_file)

print(f"{minimum_expected_vmaf=}")

print(video_data)
# _ = input()
print(video_data_other)
# _ = input()


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

        vmaf_got = ffmpeg_heuristics.VMAF(90).summary_of_overall_video(
            input_file,
            compare_file,
            "ffmpeg",
            accurate_seek,
            encode_start_end_frame=(start_frame, end_frame),
            source_start_end_frame=(start_frame, end_frame),
        )

        vmaf_got_throughout = mean(
            ffmpeg_heuristics.VMAF(90).throughout_video(
                input_file,
                compare_file,
                "ffmpeg",
                accurate_seek,
                encode_start_end_frame=(start_frame, end_frame),
                source_start_end_frame=(start_frame, end_frame),
            )
        )

        total_tests += 1
        assert vmaf_got >= minimum_expected_vmaf, "VMAF IS TOO LOW"
        # assert round(vmaf_got) == round(vmaf_got_throughout), "VMAF is different!"
        assert abs(vmaf_got - vmaf_got_throughout) <= 1, "VMAF is different!"
finally:
    print(f"Total: {total_tests}")
    print(f"Total tests: {sorted(test_samples)}")

    # ffmpeg.visual_comparison_of_video_with_blend_filter(
    #     input_file,
    #     compare_file,
    #     "ffmpeg",
    #     "INCORRECT.mp4",
    #     (start_frame, end_frame),
    #     (start_frame, end_frame),
    # )
