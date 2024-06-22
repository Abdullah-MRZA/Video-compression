import time
import ffmpeg_heuristics
import ffmpeg
import target_video_quality
# import subprocess
# import logging


def main() -> None:
    # check if FFMPEG is installed

    video_path: str = "test.mp4"

    target_video_quality.Compress_video.compress_video(
        input_filename=video_path,
        output_filename="OUTPUT FILE.mp4",
        ffmpeg_codec_information=ffmpeg.H264(preset="veryfast"),
        heuristic_type=ffmpeg_heuristics.VMAF(target_score=90),
        crop_black_bars=False,
    )


if __name__ == "__main__":
    start_time = time.perf_counter()
    try:
        main()
    except Exception as e:
        raise e
    finally:
        end_time = time.perf_counter()
        print(f"Total elapsed time: {end_time - start_time}")
