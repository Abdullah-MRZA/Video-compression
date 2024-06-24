import time
import ffmpeg_heuristics
import ffmpeg
import target_video_quality
# import subprocess
# import logging


def main() -> None:
    # check if FFMPEG is installed

    video_path: str = "output-small.mkv"

    target_video_quality.Compress_video.compress_video(
        input_filename_with_extension=video_path,
        output_filename_with_extension="OUTPUT FILE.mkv",
        # ffmpeg_codec_information=ffmpeg.H264(preset="ultrafast"), # 'fast' prototyping
        ffmpeg_codec_information=ffmpeg.SVTAV1(preset=8),
        heuristic_type=ffmpeg_heuristics.VMAF(target_score=90),
        crop_black_bars=False,
        extra_current_crf_itterate_amount=1,  # probably speeds up by a very small amount
        scene_detection_threshold=40,  # 27
        recombine_audio_from_input_file=True,
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
