import time
import ffmpeg_heuristics
import ffmpeg
import target_video_quality
from rich import print


# TODO: Add these features
# - Ability to restore from a crash (caching)
# - Custom piping of ffmpeg?
# - Add a separate audio encoding parameters?
# - Better time --> Shows how much time spent in encoding/VMAF/etc (and shows at end of render)
# - Smallest possible time for splitting

# BUG: These are known bugs:
# - the VMAF calculation sometimes crashes, reaching even zero (while the
#    final VMAF calculation done independantly says otherwise --> that it's actually very high)


def main() -> None:
    video_path: str = "small-trim.mp4"
    # video_path: str = "large-trim.mp4"

    time_data = target_video_quality.compress_video(
        input_filename_with_extension=video_path,
        output_filename_with_extension="temp.mkv",
        # ffmpeg_codec_information=ffmpeg.H264(
        #     preset="ultrafast", faststart=False
        # ),  # 'fast' prototyping
        ffmpeg_codec_information=ffmpeg.SVTAV1(preset=8),
        # ffmpeg_codec_information=ffmpeg.H264(preset="faster"),
        heuristic_type=ffmpeg_heuristics.VMAF(target_score=90),
        # other parameters
        crop_black_bars=False,
        extra_current_crf_itterate_amount=2,  # probably speeds up by a **very small** amount
        scene_detection_threshold=100,  # 27 or 40
        recombine_audio_from_input_file=True,  # need to detect if source has audio
        keyframe_placement=300,
        # for testing
        # delete_tempoary_files=False,
        multithreading_threads=4,
    )

    print()
    print(time_data)


if __name__ == "__main__":
    start_time = time.perf_counter()
    try:
        main()
    finally:
        end_time = time.perf_counter()
        print(f"\n\nTotal elapsed time: {end_time - start_time} seconds")
