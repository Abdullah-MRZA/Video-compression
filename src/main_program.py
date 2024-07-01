import time
import ffmpeg_heuristics
import ffmpeg
import target_video_quality
from rich import print


# TODO: Add these features
# - Ability to restore from a crash (caching)
# - Custom piping of ffmpeg
# - multithreading rendering? (though I probably won't benefit from this)
# - Add a separate audio encoding parameters?
# - Better time --> Shows how much time spent in encoding/VMAF/etc (and shows at end of render)


def main() -> None:
    # check if FFMPEG is installed

    # video_path: str = "input_small.mkv"
    # video_path: str = "input_test.mkv"
    # video_path: str = "input.mov"
    # video_path: str = "input-copy.mov"
    # video_path: str = "input_long_5mins.mp4"
    video_path: str = "short.mp4"
    # video_path: str = "short-smallest.mp4"
    # video_path: str = "test.mkv"

    time_data = target_video_quality.compress_video(
        input_filename_with_extension=video_path,
        output_filename_with_extension="OUTPUT_FILE.mkv",  # reccomended MKV
        # ffmpeg_codec_information=ffmpeg.H264(
        #     preset="ultrafast", faststart=False
        # ),  # 'fast' prototyping
        # ffmpeg_codec_information=ffmpeg.SVTAV1(preset=6),
        ffmpeg_codec_information=ffmpeg.H265(preset="faster"),
        heuristic_type=ffmpeg_heuristics.VMAF(target_score=85),
        # other parameters
        crop_black_bars=False,
        extra_current_crf_itterate_amount=2,  # probably speeds up by a **very small** amount
        scene_detection_threshold=27,  # 27 or 40
        recombine_audio_from_input_file=True,  # need to detect if source has audio
        keyframe_placement=300,
        # for testing
        # delete_tempoary_files=False,
    )

    print()
    print(time_data)


if __name__ == "__main__":
    start_time = time.perf_counter()
    try:
        main()
    # except Exception as e:
    #     print(f"EXCEPTION: {e}")
    finally:
        end_time = time.perf_counter()
        print(f"\n\nTotal elapsed time: {end_time - start_time} seconds")
