from dataclasses import dataclass
from pathlib import Path
import file_cache
import ffmpeg
import os
import json
import subprocess
# from rich import print

import concurrent.futures
from rich.traceback import install

# import v2_target_videoCRF
import videodata

_ = install(show_locals=True)


type heuristic = VMAF | ssimulacra2_rs

# PROGRAM ASSUMPTION --> Bigger heuristic is better!

# def video_to_shell_input(input: Path | str) -> str:
#     if isinstance(input, Path):
#         return f"cat {}"


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
    subsample: int = 2  # Calculate per X frames

    NAME: str = "VMAF"
    RANGE: range = range(0, 100 + 1)
    IMPROVING_DIRECTION = +1
    CERTAIN_RANGE = range(0, 98 + 1)

    # @file_cache.cache()
    @file_cache.store_cumulative_time
    def summary_of_overall_video(
        self,
        video_data: videodata.RawVideoData,
        compressed_video: Path | str,  # | subprocess.CompletedProcess[bytes],
        source_start_end_frame: tuple[int | None, int | None] = (None, None),
        threads_to_use: int = 6,
    ) -> float:
        print("Running FFMPEG COMMAND for vmaf")

        frame_rate = ffmpeg.get_video_metadata(
            video_data, video_data.input_filename
        ).frame_rate

        ffmpeg_command: list[str] = []

        if isinstance(video_data.input_filename, ffmpeg.accurate_seek):
            ffmpeg_command.append(
                video_data.input_filename.command(*source_start_end_frame)
            )

        ffmpeg_command.append(" | ffmpeg")

        ffmpeg_command.append(f"-r {str(frame_rate)}")

        if isinstance(compressed_video, Path):
            command = f'"{compressed_video}"'
        else:  # elif isinstance(compressed_video, str):
            # command = f'<(cat "{compressed_video}")'
            command = f"<({compressed_video})"
        # else:  # CompletedProcess[bytes]
        #     command = "-"

        ffmpeg_command.append(f"-i {command}")

        ffmpeg_command.append(f"-r {str(frame_rate)}")

        # command = (
        #     f"cat {video_data.input_filename}"
        #     if isinstance(video_data.input_filename, Path)
        #     else f"{video_data.input_filename}"
        # )
        ffmpeg_command.append("-i -")

        # https://www.bannerbear.com/blog/how-to-trim-a-video-using-ffmpeg/#:~:text=You%20can%20trim%20the%20input%20video%20to%20a%20specific%20duration,the%20beginning%20of%20the%20video.&text=In%20the%20command%20above%2C%20%2Dvf,the%20duration%20to%203%20seconds.
        # https://stackoverflow.com/questions/67598772/right-way-to-use-vmaf-with-ffmpeg

        # [reference]scale=1920:1080
        # scale = ""
        # if resize_input_black_bars:
        #     scale = crop_black_bars_size(vapoursynth_accurate_seek)
        #     scale = f"[reference]{scale};"

        ffmpeg_command.extend(
            [
                "-hide_banner",  #  -loglevel error --> need to read output!
                "-an",
                "-lavfi",
                f'"[1:v]setpts=PTS-STARTPTS[reference];[0:v]setpts=PTS-STARTPTS[distorted];[distorted][reference]libvmaf=n_threads={threads_to_use}:n_subsample={self.subsample}"',
                # f'"libvmaf=n_threads={threads_to_use}:n_subsample={subsample}"',
                "-f",
                "null",
                "-",
            ]
        )

        print(f"FFMPEG COMMAND: {' '.join(ffmpeg_command)}")
        try:
            output_data = subprocess.run(
                f"zsh -c '{' '.join(ffmpeg_command)}'",
                shell=True,
                check=True,
                capture_output=True,
                # stdin=compressed_video.stdout
                # if isinstance(compressed_video, subprocess.CompletedProcess)
                # else None,
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

    # @file_cache.cache()
    @file_cache.store_cumulative_time
    def throughout_video(
        self,
        video_data: videodata.RawVideoData,
        compressed_video: Path | str,
        source_start_end_frame: tuple[int | None, int | None] = (None, None),
        threads_to_use: int = 6,
    ) -> list[float]:
        print("Running FFMPEG COMMAND for vmaf")

        frame_rate = ffmpeg.get_video_metadata(
            video_data, video_data.input_filename
        ).frame_rate

        ffmpeg_command: list[str] = []

        if isinstance(video_data.input_filename, ffmpeg.accurate_seek):
            ffmpeg_command.append(
                video_data.input_filename.command(*source_start_end_frame)
            )

        ffmpeg_command.append(" | ffmpeg")

        ffmpeg_command.append(f"-r {str(frame_rate)}")

        # command = (
        #     f'cat "{compressed_video}"'
        #     if isinstance(compressed_video, Path)
        #     else f"{compressed_video}"
        # )
        # ffmpeg_command.append(f"-i <({command})")
        if isinstance(compressed_video, Path):
            command = f'"{compressed_video}"'
        else:  # elif isinstance(compressed_video, str):
            command = f"<({compressed_video})"

        ffmpeg_command.append(f"-i {command}")

        ffmpeg_command.append(f"-r {str(frame_rate)}")

        # command = (
        #     f"cat {video_data.input_filename}"
        #     if isinstance(video_data.input_filename, Path)
        #     else f"{video_data.input_filename}"
        # )
        ffmpeg_command.append("-i -")

        LOG_FILE_NAME = f"log-{source_start_end_frame}.json".replace(" ", "").replace(
            ",", ""
        )

        ffmpeg_command.extend(
            [
                "-hide_banner -loglevel error",
                "-an",  # Remove audio
                "-lavfi",
                f'"[1:v]setpts=PTS-STARTPTS[reference];[0:v]setpts=PTS-STARTPTS[distorted];[distorted][reference]libvmaf=n_threads={threads_to_use}:n_subsample={self.subsample}:log_fmt=json:log_path={LOG_FILE_NAME}"',
                # f'"libvmaf=n_threads={threads_to_use}:n_subsample={subsample}:log_fmt=json:log_path=log.json"',
                "-f",
                "null",
                "-",
            ]
        )

        try:
            print(f"RUNNNING COMMAND: {" ".join(ffmpeg_command)}")
            _ = subprocess.run(
                f"zsh -c '{' '.join(ffmpeg_command)}'", shell=True, check=True
            )
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


@dataclass()
class ssimulacra2_cpp:
    """
    - 30 = low quality. This corresponds to the p10 worst output of mozjpeg -quality 30.

    - 50 = medium quality. This corresponds to the average output of cjxl -q 40 or
            mozjpeg -quality 40, or the p10 output of cjxl -q 50 or mozjpeg -quality 60.

    - 70 = high quality. This corresponds to the average output of cjxl -q 65 or
            mozjpeg -quality 70, p10 output of cjxl -q 75 or mozjpeg -quality 80.

    - 90 = very high quality. Likely impossible to distinguish from the original when viewed
            at 1:1 from a normal viewing distance. This corresponds to the average output
            of mozjpeg -quality 95 or the p10 output of cjxl -q
    """

    target_score: int
    subsample: int = 2  # Calculate per X frames

    NAME: str = "ssimulacra2_cpp"
    RANGE: range = range(0, 100 + 1)  # NOTE this is MOSTLY true

    IMPROVING_DIRECTION = +1
    CERTAIN_RANGE = range(0, 100 + 1)

    def throughout_video(
        self,
        video_data: videodata.RawVideoData,
        compressed_video: Path | str,  # | subprocess.CompletedProcess[bytes],
        source_start_end_frame: tuple[int | None, int | None] = (None, None),
        threads_to_use: int = 6,
    ) -> list[float]:
        if isinstance(compressed_video, Path):
            _ = subprocess.run(
                f'ffmpeg -i "{compressed_video}" -y "TEMP-COMPRESSED-{source_start_end_frame}-%5d.png"',
                shell=True,
                check=True,
            )
        else:
            _ = subprocess.run(
                f'{compressed_video} | ffmpeg -i - -y "TEMP-COMPRESSED-{source_start_end_frame}-%5d.png"',
                shell=True,
                check=True,
            )

        if isinstance(video_data.input_filename, Path):
            _ = subprocess.run(
                f'ffmpeg -i "{video_data.input_filename}" -y "TEMP-INPUT-{source_start_end_frame}-%5d.png"',
                shell=True,
                check=True,
            )
        else:
            _ = subprocess.run(
                f'{video_data.input_filename.command(*source_start_end_frame)} | ffmpeg -i - -y "TEMP-INPUT-{source_start_end_frame}-%5d.png"',
                shell=True,
                check=True,
            )

        source_images: list[str] = [
            x
            for x in os.listdir()
            if os.path.isfile(x)
            and x.startswith(f"TEMP-INPUT-{source_start_end_frame}")
        ]
        encode_images: list[str] = [
            x
            for x in os.listdir()
            if os.path.isfile(x)
            and x.startswith(f"TEMP-COMPRESSED-{source_start_end_frame}")
        ]

        def get_score(source_frame: str, encode_frame: str) -> float:
            output = subprocess.run(
                f'ssimulacra2 "{source_frame}" "{encode_frame}"',
                shell=True,
                check=True,
                capture_output=True,
            )
            return float(output.stdout)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results_future = list(
                executor.submit(get_score, source_frame, encode_frame)
                for source_frame, encode_frame in zip(source_images, encode_images)
            )
            ssimulacra2_scores = [x.result() for x in results_future]
            ssimulacra2_scores = [max(x, 0) for x in ssimulacra2_scores]  # removes -inf

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = [
                executor.submit(os.remove, img) for img in encode_images + source_images
            ]
            for x in future:
                try:
                    x.result()
                except Exception:
                    pass

        return ssimulacra2_scores

    # https://wiki.x266.mov/docs/metrics/SSIMULACRA2
    def summary_of_overall_video(
        self,
        video_data: videodata.RawVideoData,
        compressed_video: Path | str,
        source_start_end_frame: tuple[int | None, int | None] = (None, None),
        threads_to_use: int = 6,
    ) -> float:
        val = self.throughout_video(
            video_data,
            compressed_video,
            source_start_end_frame,
            threads_to_use,
        )

        return sum(val) / len(val)


@dataclass()
class ssimulacra2_rs:
    """
    - 30 = low quality. This corresponds to the p10 worst output of mozjpeg -quality 30.

    - 50 = medium quality. This corresponds to the average output of cjxl -q 40 or
            mozjpeg -quality 40, or the p10 output of cjxl -q 50 or mozjpeg -quality 60.

    - 70 = high quality. This corresponds to the average output of cjxl -q 65 or
            mozjpeg -quality 70, p10 output of cjxl -q 75 or mozjpeg -quality 80.

    - 90 = very high quality. Likely impossible to distinguish from the original when viewed
            at 1:1 from a normal viewing distance. This corresponds to the average output
            of mozjpeg -quality 95 or the p10 output of cjxl -q
    """

    target_score: int
    subsample: int = 10  # Calculate per X frames

    NAME: str = "ssimulacra2_rs"
    RANGE: range = range(0, 100 + 1)  # NOTE this is MOSTLY true

    IMPROVING_DIRECTION = +1
    CERTAIN_RANGE = range(0, 100 + 1)

    def throughout_video(
        self,
        video_data: videodata.RawVideoData,
        compressed_video: Path | str,  # | subprocess.CompletedProcess[bytes],
        source_start_end_frame: tuple[int | None, int | None] = (None, None),
        threads_to_use: int = 6,
    ) -> list[float]:
        delete_file_list: list[Path] = []

        if isinstance(compressed_video, str):
            filename = Path(
                f"TEMP-SSIMULACRA2_RS-FILEOUTPUT-{source_start_end_frame}-.mkv"
            )
            delete_file_list.append(filename)
            _ = subprocess.run(
                f"{compressed_video} | ffmpeg -i - -c copy -y {filename}",
                shell=True,
                check=True,
            )
            compressed_video = filename

        input_video_name = video_data.input_filename
        if isinstance(video_data.input_filename, ffmpeg.accurate_seek):
            filename = Path(
                f"TEMP-SSIMULACRA2_RS-FILEINPUT-{source_start_end_frame}-.mkv"
            )
            delete_file_list.append(filename)
            _ = subprocess.run(
                f"{video_data.input_filename.command(*source_start_end_frame)} | ffmpeg -i - -y {filename}",
                shell=True,
                check=True,
            )
            input_video_name = filename

        output = subprocess.run(
            " ".join(
                [
                    f'ssimulacra2_rs video "{input_video_name}" "{compressed_video}"',
                    "-v",  # per frame printing
                    f"-f {threads_to_use}",  # how many threads
                    f"-i {self.subsample}",
                ],
            ),
            shell=True,
            check=True,
            capture_output=True,
        )

        ssimulacra2_scores = [
            max(float(x.split(":")[1].strip()), 0)
            for x in str(output.stdout).splitlines()
            if x.startswith("Frame") and not x.endswith("skip")
        ]

        for file in delete_file_list:
            try:
                os.remove(file)
            except FileNotFoundError:
                print(f"unable to delete {file}")
        return ssimulacra2_scores

    # https://wiki.x266.mov/docs/metrics/SSIMULACRA2
    def summary_of_overall_video(
        self,
        video_data: videodata.RawVideoData,
        compressed_video: Path | str,
        source_start_end_frame: tuple[int | None, int | None] = (None, None),
        threads_to_use: int = 6,
    ) -> float:
        val = self.throughout_video(
            video_data,
            compressed_video,
            source_start_end_frame,
            threads_to_use,
        )

        return sum(val) / len(val)
