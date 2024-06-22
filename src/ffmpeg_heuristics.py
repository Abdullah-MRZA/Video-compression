import subprocess
# from rich import print

type heuristic = VMAF


class VMAF:
    def overall(
        self,
        source_video_path: str,
        encoded_video_path: str,
        ffmpeg_path: str = "ffmpeg",
        threads_to_use: int = 5,
        subsample: int = 2,  # Calculate per X frames
    ) -> float:
        ffmpeg_output = subprocess.getoutput(
            f'{ffmpeg_path} -hide_banner -i "{encoded_video_path}" -i "{source_video_path}"'
            + " "
            + f'-lavfi libvmaf="n_threads={threads_to_use}:n_subsample={subsample}" -f null -'
        )
        # This approach *could* be error prone to changes in FFMPEG?
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


# class ssimulacra2_rs:
#     def overall(
#         self,
#         source_video_path: str,
#         encoded_video_path: str,
#         ffmpeg_path: str = "ffmpeg",
#     ) -> int: ...
#
#     def throughout_video(
#         self, source_video_path: str, encoded_video_path: str
#     ) -> int: ...


# TESTS:
# print(VMAF().overall("test.mp4", "lowquality.mp4"))
