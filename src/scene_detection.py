from dataclasses import dataclass
import file_cache
import scenedetect as sd
import ffmpeg


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


@file_cache.cache(prefix_name="SceneCache-", persistent_after_termination=True)
def find_scenes(
    video_path: str,
    minimum_length_scene_seconds: float,
    # start_time: float,
    # end_time: float
    # threshold: float,
) -> list[SceneData]:
    """
    Function that gets the frames of the different scenes in the video
    - for threshold, 27.0 is default value
    """
    video = sd.open_video(video_path)
    scene_manager = sd.SceneManager()
    # scene_manager.add_detector(sd.ContentDetector(threshold=threshold))

    scene_manager.add_detector(sd.ContentDetector())
    # scene_manager.add_detector(sd.ThresholdDetector())
    # scene_manager.add_detector(sd.AdaptiveDetector())
    # scene_manager.add_detector(sd.HashDetector())

    _ = scene_manager.detect_scenes(video)

    video_data = ffmpeg.get_video_metadata(video_path)

    scene_data = [
        SceneData(
            start_frame=x[0].get_frames(),
            end_frame=x[1].get_frames(),
        )
        for x in scene_manager.get_scene_list()
    ]

    scene_data = _ensure_scene_length_is_larger_than_minimum_length(
        scene_data, video_data.frame_rate, minimum_length_scene_seconds
    )

    if len(scene_data) == 0:
        scene_data = [SceneData(start_frame=0, end_frame=video_data.total_frames)]

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
