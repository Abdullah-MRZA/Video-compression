import time
import ffmpeg_heuristics
import ffmpeg
import target_video_quality
# import subprocess
# import logging

# test


def main() -> None:
    # check if FFMPEG is installed

    # video_path: str = "input_small.mkv"
    video_path: str = "input_test.mkv"

    target_video_quality.Compress_video.compress_video(
        input_filename_with_extension=video_path,
        output_filename_with_extension="OUTPUT_FILE.mkv",  # reccomended MKV
        # ffmpeg_codec_information=ffmpeg.H264(
        #     preset="ultrafast", faststart=False
        # ),  # 'fast' prototyping
        ffmpeg_codec_information=ffmpeg.SVTAV1(preset=6),
        heuristic_type=ffmpeg_heuristics.VMAF(target_score=88),
        crop_black_bars=False,
        extra_current_crf_itterate_amount=1,  # probably speeds up by a **very small** amount
        scene_detection_threshold=35,  # 27 or 40
        recombine_audio_from_input_file=True,  # need to detect if source has audio
        delete_tempoary_files=True,
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
