from dataclasses import dataclass
import scenedetect as sd
from hashlib import sha256
import os
import ffmpeg
import pickle


@dataclass()
class SceneData:
    start_frame: int
    end_frame: int


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
    with open(video_path, "rb") as f:
        data = f.read() + str.encode(str(minimum_length_scene_seconds))
        sha_value = sha256(data).hexdigest()
        cache_file = f"{video_path}-{sha_value}.pickle"

    if os.path.exists(cache_file):
        print("Recieving from file")
        with open(cache_file, "rb") as f:
            scene_data_from_file: list[SceneData] = pickle.load(f)
            return scene_data_from_file

    video = sd.open_video(video_path)
    scene_manager = sd.SceneManager()
    # scene_manager.add_detector(sd.ContentDetector(threshold=threshold))

    scene_manager.add_detector(sd.ContentDetector())
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

    def scene_len_seconds(scene: SceneData, fps: int) -> float:
        return (scene.end_frame - scene.start_frame) / fps

    while True:
        # WARNING: this will skip first and last chunk from checks
        for i, scene in enumerate(scene_data[1:-1]):
            if (
                scene_len_seconds(scene, video_data.total_frames)
                < minimum_length_scene_seconds
            ):
                if scene_len_seconds(
                    scene_data[i - 1], video_data.total_frames
                ) > scene_len_seconds(scene_data[i + 1], video_data.total_frames):
                    scene_data[i].end_frame = scene_data[i + 1].end_frame
                    del scene_data[i + 1]
                else:
                    scene_data[i].start_frame = scene_data[i - 1].start_frame
                    del scene_data[i - 1]
                break
        else:
            break

    if len(scene_data) == 0:
        scene_data = [SceneData(start_frame=0, end_frame=video_data.total_frames)]

    with open(cache_file, "wb") as f:
        # _ = f.write(pickle.dumps(scene_data))
        pickle.dump(scene_data, f)

    return scene_data
