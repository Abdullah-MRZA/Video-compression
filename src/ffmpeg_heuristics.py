from dataclasses import dataclass
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
        source_start_end_time: None | tuple[str, str] = None,
        encode_start_end_time: None | tuple[str, str] = None,
        ffmpeg_path: str = "ffmpeg",
        threads_to_use: int = 6,
        subsample: int = 2,  # Calculate per X frames
    ) -> float:
        ffmpeg_output = subprocess.getoutput(
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
                        f'-lavfi libvmaf="n_threads={threads_to_use}:n_subsample={subsample}" -f null -'
                    ),
                ]
            )
        )
        # This approach *could* be error prone to changes in FFMPEG?
        print(
            f"{[x for x in ffmpeg_output.splitlines() if "VMAF score" in x][0].split()[-1]=}"
        )
        return float(
            [x for x in ffmpeg_output.splitlines() if "VMAF score" in x][0].split()[-1]
        )

    # def throughout_video(
    #     self,
    #     source_video_path: str,
    #     encoded_video_path: str,
    #     ffmpeg_path: str = "ffmpeg",
    # ) -> int:
    #     ffmpeg_output = subprocess.getoutput(
    #         f'{ffmpeg_path} -hide_banner -loglevel error -i "{encoded_video_path}" -i "{source_video_path}" -lavfi libvmaf -f null -'
    #     )


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
#     """
#
#     target_score: int
#     NAME: str = "ssimulacra2_rs"
#     RANGE: range = range(0, 100 + 1)  # CHECK IF THIS IS TRUE
#
#     def overall(
#         self,
#         source_video_path: str,
#         encoded_video_path: str,
#         ffmpeg_path: str = "ffmpeg",
#         threads_to_use: int = 4,
#     ) -> int:
#         ...
#         # https://wiki.x266.mov/docs/metrics/SSIMULACRA2
#
#     def throughout_video(
#         self, source_video_path: str, encoded_video_path: str
#     ) -> int: ...


def crop_black_bars(source_video_path: str) -> str:
    # print("CROPPING BLACK BARS")
    ffmpeg_output = subprocess.getoutput(
        f'ffmpeg -i "{source_video_path}" -t 10 -vf cropdetect -f null -'
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
