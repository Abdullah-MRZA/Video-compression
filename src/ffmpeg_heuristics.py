from dataclasses import dataclass
import os
import json
import subprocess
# from rich import print

type heuristic = VMAF


@dataclass()
class VMAF:
    """
    the VMAF heuristic. A score of like 90 is usually good
    """

    target_score: int
    NAME: str = "VMAF"
    RANGE: range = range(0, 100 + 1)

    def overall(
        self,
        source_video_path: str,
        encoded_video_path: str,
        ffmpeg_path: str,
        source_start_end_time: None | tuple[str, str] = None,
        encode_start_end_time: None | tuple[str, str] = None,
        threads_to_use: int = 6,
        subsample: int = 2,  # Calculate per X frames
    ) -> float:
        print("Running FFMPEG COMMAND for vmaf")
        ffmpeg_command: list[str] = [ffmpeg_path, "-hide_banner"]

        if encode_start_end_time is not None:
            ffmpeg_command.extend(["-ss", encode_start_end_time[0]])
            ffmpeg_command.extend(["-to", encode_start_end_time[1]])
        ffmpeg_command.extend(["-i", encoded_video_path])

        if source_start_end_time is not None:
            ffmpeg_command.extend(["-ss", source_start_end_time[0]])
            ffmpeg_command.extend(["-to", source_start_end_time[1]])
        ffmpeg_command.extend(["-i", source_video_path])

        ffmpeg_command.extend(
            [
                "-lavfi",
                f'libvmaf="n_threads={threads_to_use}:n_subsample={subsample}"',
                "-f",
                "null",
                "-",
            ]
        )

        print(f"FFMPEG COMMAND: {' '.join(ffmpeg_command)}")
        try:
            # ffmpeg_output = subprocess.run(ffmpeg_command).stdout
            output_data = subprocess.run(
                " ".join(ffmpeg_command), shell=True, check=True, capture_output=True
            )
            ffmpeg_output: str = output_data.stderr.decode()
            # input(f"FFMPEG OUTPUT: {ffmpeg_output}")
        except FileNotFoundError as e:
            print("WARNING: FFMPEG NOT FOUND ON SYSTEM!!")
            raise e
        except subprocess.CalledProcessError as e:
            print("Process failed because did not return a successful return code.")
            raise e

        # This approach *could* be error prone to changes in FFMPEG?
        print(
            # f"{[x for x in ffmpeg_output.splitlines() if "VMAF score" in x][0].split()[-1]=}"
            f"FFMPEG OUTPUT: {ffmpeg_output}"
        )
        return float(
            [x for x in ffmpeg_output.splitlines() if "VMAF score" in x][0].split()[-1]
        )

    # ffmpeg -i input_small.mkv -i input_small.mkv -lavfi libvmaf="n_threads=4:n_subsample=1:log_fmt=json:log_path=log.json" -f null -
    # ^^^
    def throughout_video(
        self,
        source_video_path: str,
        encoded_video_path: str,
        ffmpeg_path: str,
        source_start_end_time: None | tuple[str, str] = None,
        encode_start_end_time: None | tuple[str, str] = None,
        threads_to_use: int = 6,
        subsample: int = 2,  # Calculate per X frames
    ) -> list[float]:
        _ = subprocess.getoutput(
            " ".join(
                [
                    ffmpeg_path,
                    "-hide_banner",
                    (
                        f"-ss {encode_start_end_time[0]}"
                        if encode_start_end_time is not None
                        else ""
                    ),
                    (
                        f"-to {encode_start_end_time[1]}"
                        if encode_start_end_time is not None
                        else ""
                    ),
                    f'-i "{encoded_video_path}"',
                    (
                        f"-ss {source_start_end_time[0]}"
                        if source_start_end_time is not None
                        else ""
                    ),
                    (
                        f"-to {source_start_end_time[1]}"
                        if source_start_end_time is not None
                        else ""
                    ),
                    f'-i "{source_video_path}"',
                    (
                        f'-lavfi libvmaf="n_threads={threads_to_use}:n_subsample={subsample}:log_fmt=json:log_path=log.json" -y -f null -'
                    ),
                ]
            )
        )

        with open("log.json", "r") as file:
            json_of_file: dict[str, list[dict[str, dict[str, int]]]] = json.loads(
                file.read()
            )
            # This type-hints are not accurate --> but works for this

            vmaf_data: list[float] = []

            for frame in json_of_file["frames"]:
                vmaf_data.append(frame["metrics"]["vmaf"])

        # print(f"{vmaf_data=}")
        try:
            os.remove("log.json")
        except FileNotFoundError:
            print("FileNotFoundError for removing log.json")
        return vmaf_data


# class SSIM:
#     def overall(
#         self,
#         source_video_path: str,
#         encoded_video_path: str,
#         ffmpeg_path: str = "ffmpeg",
#     ) -> int: ...
#
#     def throughout_video(
#         self,
#         source_video_path: str,
#         encoded_video_path: str,
#         ffmpeg_path: str = "ffmpeg",
#     ) -> int: ...


# class PSNR:
#     def overall(
#         self,
#         source_video_path: str,
#         encoded_video_path: str,
#         ffmpeg_path: str = "ffmpeg",
#     ) -> int: ...
#
#     def throughout_video(
#         self,
#         source_video_path: str,
#         encoded_video_path: str,
#         ffmpeg_path: str = "ffmpeg",
#     ) -> int: ...


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


def crop_black_bars(source_video_path: str, ffmpeg_path: str) -> str:
    # print("CROPPING BLACK BARS")
    ffmpeg_output = subprocess.getoutput(
        f'{ffmpeg_path} -i "{source_video_path}" -t 10 -vf cropdetect -f null -'
    ).splitlines()
    data = [x for x in ffmpeg_output if "crop=" in x][-1]
    # _ = input(data.rsplit(maxsplit=1)[-1])

    # get the last data point? (does the crop size ever change?) --> Need to test
    return data.rsplit(maxsplit=1)[-1]


class ffprobe_information:
    @staticmethod
    def check_contains_any_audio(
        input_filename_with_extension: str, ffprobe_path: str
    ) -> bool:
        """Determines if the input file contains audio (is this robust??)"""
        ffprobe_output = subprocess.getoutput(
            f"{ffprobe_path} {input_filename_with_extension}"
        )
        return any(
            True
            for x in ffprobe_output.splitlines()
            if x.strip().startswith("Stream") and "Audio" in x
        )


# TESTS:
# print(VMAF(target_score=90).overall("test.mp4", "lowquality.mp4"))
