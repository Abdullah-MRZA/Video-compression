from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import file_cache
import ffmpeg
import videodata


# import v2_target_videoCRF


@dataclass()
class SceneData:
    start_frame: int
    end_frame: int


def scene_len_seconds(scene: SceneData, fps: float) -> float:
    return (scene.end_frame - scene.start_frame) / fps


def _ensure_scene_length_is_larger_than_minimum_length(
    scene_data: list[SceneData],
    fps: float,
    minimum_length_scene_seconds: float,
) -> list[SceneData]:
    while True:
        # WARNING: this will skip first and last chunk from checks
        # for i, scene in enumerate(scene_data[1:-1]):
        for i, current_scene in enumerate(scene_data):
            if scene_len_seconds(current_scene, fps) < minimum_length_scene_seconds:
                if i != len(scene_data) - 1 and (
                    i == 0
                    or scene_len_seconds(scene_data[i - 1], fps)
                    > scene_len_seconds(scene_data[i + 1], fps)
                ):
                    scene_data[i].end_frame = scene_data[i + 1].end_frame
                    del scene_data[i + 1]
                elif i != 0 and (
                    i == len(scene_data) - 1
                    or scene_len_seconds(scene_data[i - 1], fps)
                    < scene_len_seconds(scene_data[i + 1], fps)
                ):
                    scene_data[i].start_frame = scene_data[i - 1].start_frame
                    del scene_data[i - 1]
                # print(scene_data)
                break
        else:
            break

    return scene_data


@file_cache.store_cumulative_time
@file_cache.cache(
    prefix_name="SceneCache-",
    persistent_after_termination=True,
    sub_directory=Path("scene_data"),
)
def find_scenes(
    # video_path: str,
    video_data: videodata.RawVideoData,
    minimum_length_scene_seconds: float,
) -> list[SceneData]:
    """
    Function that gets the frames of the different scenes in the video
    - for threshold, 27.0 is default value
    """

    try:
        import scenedetect as sd

        video = sd.open_video(str(video_data.raw_input_filename))
        scene_manager = sd.SceneManager()
        # scene_manager.add_detector(sd.ContentDetector(threshold=threshold))

        scene_manager.add_detector(sd.ContentDetector())
        # scene_manager.add_detector(sd.ThresholdDetector())
        # scene_manager.add_detector(sd.AdaptiveDetector())
        # scene_manager.add_detector(sd.HashDetector())

        _ = scene_manager.detect_scenes(video, show_progress=True)

        scene_data = [
            SceneData(
                start_frame=x[0].get_frames(),
                end_frame=x[1].get_frames(),
            )
            for x in scene_manager.get_scene_list()
        ]
    # except ModuleNotFoundError:
    except Exception:
        CSV_FILENAME = f"{video_data.raw_input_filename.stem}-Scenes.csv"
        _ = subprocess.run(
            f"scenedetect --input '{video_data.raw_input_filename.name}' -m {minimum_length_scene_seconds} detect-adaptive list-scenes",
            shell=True,
            check=True,
        )

        with open(CSV_FILENAME, "r") as file:
            scene_data: list[SceneData] = []
            for i, line in enumerate(file.readlines()):
                if i < 2:
                    continue

                linedata = line.split(",")
                scene_data.append(SceneData(int(linedata[1]), int(linedata[4])))

        try:
            os.remove(CSV_FILENAME)
        except:
            print("scenedetect CSV intermediate file didn't delete")
        return scene_data

    video_metadata = ffmpeg.get_video_metadata(video_data, video_data.input_filename)

    scene_data = _ensure_scene_length_is_larger_than_minimum_length(
        scene_data, video_metadata.frame_rate, minimum_length_scene_seconds
    )

    if len(scene_data) == 0:
        scene_data = [SceneData(start_frame=0, end_frame=video_metadata.total_frames)]
    return scene_data


if __name__ == "__main__":
    from itertools import accumulate
    from rich import print

    _times = [0, 1, 20, 0.5, 10, 0.5, 100]
    _times_accumulate = list(accumulate(_times))
    _fps = 30
    _some_data = [
        SceneData(int(x[0] * _fps), int(x[1] * _fps))
        for x in zip(_times_accumulate[:-1], _times_accumulate[1:])
    ]

    print(f"Before modification: {_times}")
    print(_some_data)

    _mod_data = _ensure_scene_length_is_larger_than_minimum_length(
        _some_data, _fps, minimum_length_scene_seconds=1.1
    )

    _mod_time_data = [(x.end_frame - x.start_frame) / _fps for x in _mod_data]

    print(f"After modification: {_mod_time_data}")
    print(_mod_data)
