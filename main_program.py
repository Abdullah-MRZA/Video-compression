import time
import subprocess
import logging
import ffmpeg
import scene_detection


def main() -> None:
    # check if FFMPEG is installed
    if not subprocess.Popen("ffmpeg"):  # DOESN'T WORK
        logging.error("FFMPEG is not installed!!\nExiting..")
        return

    file: ffmpeg.video = ffmpeg.SVTAV1()


if __name__ == "__main__":
    start_time = time.perf_counter()
    main()
    end_time = time.perf_counter()
    print(f"Total elapsed time: {end_time - start_time}")
