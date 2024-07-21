from dataclasses import dataclass
import file_cache
import ffmpeg
import os
import json
import subprocess
# from rich import print


from rich.traceback import install

_ = install(show_locals=True)


type heuristic = VMAF

# PROGRAM ASSUMPTION --> Bigger heuristic is better!


@dataclass()
class VMAF:
    """
    the VMAF heuristic. A score of like 90 is usually good

    ffmpeg -ss 10 -t 10 -i short.mp4 \
    -ss 10 -t 10 -i short.mp4 \
    -lavfi "[0:v]setpts=PTS-STARTPTS[reference]; \
            [1:v]setpts=PTS-STARTPTS[distorted]; \
            [distorted][reference]libvmaf=n_threads=8" \
    -f null -
    """

    target_score: int
    NAME: str = "VMAF"
    RANGE: range = range(0, 100 + 1)
    IMPROVING_DIRECTION = +1

    @file_cache.cache()
    def summary_of_overall_video(
        self,
        source_video_path: str,
        encoded_video_path: str,  # | None
        accurate_seek: ffmpeg.accurate_seek,
        source_start_end_frame: None | tuple[int, int] = None,
        threads_to_use: int = 6,
        subsample: int = 2,  # Calculate per X frames
    ) -> float:
        print("Running FFMPEG COMMAND for vmaf")
        frame_rate = ffmpeg.get_video_metadata(encoded_video_path).frame_rate

        ffmpeg_command: list[str] = []

        if source_start_end_frame is not None:
            # total_frames = ffmpeg.get_video_metadata(source_video_path).total_frames

            # if source_start_end_frame[1] == total_frames:
            #     source_start_end_frame = (source_start_end_frame[0], None)

            ffmpeg_command.append(accurate_seek.command(*source_start_end_frame))
            source_video_path = "-"

        ffmpeg_command.append("ffmpeg")

        ffmpeg_command.extend(["-r", str(frame_rate)])
        ffmpeg_command.extend(["-i", encoded_video_path])

        ffmpeg_command.extend(["-r", str(frame_rate)])
        ffmpeg_command.extend(["-i", source_video_path])

        # https://www.bannerbear.com/blog/how-to-trim-a-video-using-ffmpeg/#:~:text=You%20can%20trim%20the%20input%20video%20to%20a%20specific%20duration,the%20beginning%20of%20the%20video.&text=In%20the%20command%20above%2C%20%2Dvf,the%20duration%20to%203%20seconds.
        # https://stackoverflow.com/questions/67598772/right-way-to-use-vmaf-with-ffmpeg

        ffmpeg_command.extend(
            [
                "-hide_banner",  #  -loglevel error --> need to read output!
                "-an",
                "-lavfi",
                f'"[1:v]setpts=PTS-STARTPTS[reference];[0:v]setpts=PTS-STARTPTS[distorted];[distorted][reference]libvmaf=n_threads={threads_to_use}:n_subsample={subsample}"',
                # f'"libvmaf=n_threads={threads_to_use}:n_subsample={subsample}"',
                "-f",
                "null",
                "-",
            ]
        )

        print(f"FFMPEG COMMAND: {' '.join(ffmpeg_command)}")
        try:
            output_data = subprocess.run(
                " ".join(ffmpeg_command), shell=True, check=True, capture_output=True
            )
            ffmpeg_output: str = output_data.stderr.decode()
        except FileNotFoundError as e:
            print("WARNING: FFMPEG NOT FOUND ON SYSTEM!!")
            raise e
        except subprocess.CalledProcessError as e:
            print("Process failed because did not return a successful return code.")
            raise e

        return float(
            [x for x in ffmpeg_output.splitlines() if "VMAF score" in x][0].split()[-1]
        )

    @file_cache.cache()
    def throughout_video(
        self,
        source_video_path: str,
        encoded_video_path: str,  # | None,
        accurate_seek: ffmpeg.accurate_seek,
        source_start_end_frame: None | tuple[int, int] = None,
        # encode_start_end_frame: None | tuple[int, int] = None,
        threads_to_use: int = 6,
        subsample: int = 1,  # Calculate per X frames
    ) -> list[float]:
        print("Running FFMPEG-throughout COMMAND for vmaf")
        # ffmpeg_command: list[str] = [ffmpeg_path]
        frame_rate = ffmpeg.get_video_metadata(encoded_video_path).frame_rate
        LOG_FILE_NAME = f"log-{source_start_end_frame}.json".replace(" ", "").replace(
            ",", ""
        )

        ffmpeg_command: list[str] = []

        if source_start_end_frame is not None:
            # total_frames = ffmpeg.get_video_metadata(source_video_path).total_frames
            #
            # if source_start_end_frame[1] == total_frames:
            #     source_start_end_frame = (source_start_end_frame[0], None)

            ffmpeg_command.append(accurate_seek.command(*source_start_end_frame))
            source_video_path = "-"

        ffmpeg_command.append("ffmpeg")

        ffmpeg_command.extend(["-r", str(frame_rate)])
        ffmpeg_command.extend(["-i", encoded_video_path])

        ffmpeg_command.extend(["-r", str(frame_rate)])
        ffmpeg_command.extend(["-i", source_video_path])

        ffmpeg_command.extend(
            [
                "-hide_banner -loglevel error",
                "-an",  # Remove audio
                "-lavfi",
                f'"[1:v]setpts=PTS-STARTPTS[reference];[0:v]setpts=PTS-STARTPTS[distorted];[distorted][reference]libvmaf=n_threads={threads_to_use}:n_subsample={subsample}:log_fmt=json:log_path={LOG_FILE_NAME}"',
                # f'"libvmaf=n_threads={threads_to_use}:n_subsample={subsample}:log_fmt=json:log_path=log.json"',
                "-f",
                "null",
                "-",
            ]
        )

        try:
            print(f"RUNNNING COMMAND: {" ".join(ffmpeg_command)}")
            _ = subprocess.run(" ".join(ffmpeg_command), shell=True, check=True)
        except FileNotFoundError as e:
            print("WARNING: FFMPEG NOT FOUND ON SYSTEM!!")
            raise e
        except subprocess.CalledProcessError as e:
            print("Process failed because did not return a successful return code.")
            raise e

        with open(LOG_FILE_NAME, "r") as file:
            json_of_file: dict[str, list[dict[str, dict[str, int]]]] = json.loads(
                file.read()
            )
            # This type-hint is not fully accurate --> but works for this

            vmaf_data: list[float] = []

            for frame in json_of_file["frames"]:
                vmaf_data.append(frame["metrics"]["vmaf"])

        # print(f"{vmaf_data=}")
        try:
            os.remove(LOG_FILE_NAME)
        except FileNotFoundError:
            print("FileNotFoundError for removing log.json")

        return vmaf_data


# @dataclass()
# class ssimulacra2_rs:
#     """
#     A very good one apparently
#
#     - 30 = low quality. This corresponds to the p10 worst output of mozjpeg -quality 30.
#
#     - 50 = medium quality. This corresponds to the average output of cjxl -q 40 or
#             mozjpeg -quality 40, or the p10 output of cjxl -q 50 or mozjpeg -quality 60.
#
#     - 70 = high quality. This corresponds to the average output of cjxl -q 65 or
#             mozjpeg -quality 70, p10 output of cjxl -q 75 or mozjpeg -quality 80.
#
#     - 90 = very high quality. Likely impossible to distinguish from the original when viewed
#             at 1:1 from a normal viewing distance. This corresponds to the average output
#             of mozjpeg -quality 95 or the p10 output of cjxl -q
#     """
#
#     target_score: int
#     NAME: str = "ssimulacra2_rs"
#     RANGE: range = range(0, 100 + 1)  # NOTE this is MOSTLY true
#
#     # https://wiki.x266.mov/docs/metrics/SSIMULACRA2
#     def overall(
#         self,
#         source_video_path: str,
#         encoded_video_path: str,
#         ffmpeg_path: str = "ffmpeg",
#         threads_to_use: int = 2,  # "scales badly"
#     ) -> int:
#         ssimulacra2_rs_point = subprocess.getoutput(
#             f"{ffmpeg_path} video {source_video_path} {encoded_video_path} -f {threads_to_use}"
#         )
#         # TODO WARNING CHECK HOW THE OUTPUT IS FORMATTED
#         ...
#
#     def throughout_video(
#         self,
#         source_video_path: str,
#         encoded_video_path: str,
#         ffmpeg_path: str = "ffmpeg",
#         threads_to_use: int = 2,  # "scales badly"
#     ) -> int: ...


def crop_black_bars_size(source_video_path: str) -> str:
    ffmpeg_output = subprocess.getoutput(
        f'ffmpeg -i "{source_video_path}" -t 10 -vf cropdetect -f null -'
    )
    data = [x for x in ffmpeg_output.splitlines() if "crop=" in x][-1]

    # get the last data point? (does the crop size ever change?) --> Need to test
    return data.rsplit(maxsplit=1)[-1]
