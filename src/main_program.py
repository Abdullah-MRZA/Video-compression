import time
import ffmpeg_heuristics
import ffmpeg
import target_video_quality
# import subprocess
# import logging


def main() -> None:
    # check if FFMPEG is installed
    # if not subprocess.Popen("ffmpeg"):  # DOESN'T WORK
    #     logging.error("FFMPEG is not installed!!\nExiting..")
    #     return

    video_path: str = "test.mp4"
    # scenes = scene_detection.find_scenes(video_path)
    # commands = ffmpeg.FfmpegCommand() (moved to target_video_quality file)

    # target_video_quality.compress_video(
    #     video_path, ffmpeg.SVTAV1(preset=4), ffmpeg_heuristics.VMAF
    # )

    target_video_quality.Compress_video.compress_video(
        input_filename=video_path,
        ffmpeg_codec_information=ffmpeg.SVTAV1(preset=4),
        heuristic_type=ffmpeg_heuristics.VMAF(target_score=90),
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
