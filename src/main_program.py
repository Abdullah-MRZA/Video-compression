import time
import ffmpeg_heuristics
import ffmpeg
import target_video_quality


# TODO: Add these features
# - Ability to restore from a crash (caching)
# - Custom piping of ffmpeg
# - multithreading rendering? (though I probably won't benefit from this)


def main() -> None:
    # check if FFMPEG is installed

    # video_path: str = "input_small.mkv"
    # video_path: str = "input_test.mkv"
    video_path: str = "input.mov"
    # video_path: str = "input_long.mp4"

    target_video_quality.Compress_video.compress_video(
        input_filename_with_extension=video_path,
        output_filename_with_extension="OUTPUT_FILE.mkv",  # reccomended MKV
        # ffmpeg_codec_information=ffmpeg.H264(
        #     preset="ultrafast", faststart=False
        # ),  # 'fast' prototyping
        ffmpeg_codec_information=ffmpeg.SVTAV1(preset=6),
        heuristic_type=ffmpeg_heuristics.VMAF(target_score=90),
        # other parameters
        crop_black_bars=False,
        extra_current_crf_itterate_amount=2,  # probably speeds up by a **very small** amount
        scene_detection_threshold=40,  # 27 or 40
        recombine_audio_from_input_file=True,  # need to detect if source has audio
        keyframe_placement=300,
    )


if __name__ == "__main__":
    start_time = time.perf_counter()
    try:
        main()
    # except Exception as e:
    #     print(f"EXCEPTION: {e}")
    finally:
        end_time = time.perf_counter()
        print(f"\n\nTotal elapsed time: {end_time - start_time} seconds")
