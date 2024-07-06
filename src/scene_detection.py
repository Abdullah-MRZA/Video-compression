from dataclasses import dataclass
import scenedetect as sd
import ffmpeg


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

    video = sd.open_video(video_path)
    scene_manager = sd.SceneManager()
    # scene_manager.add_detector(sd.ContentDetector(threshold=threshold))

    # scene_manager.add_detector(sd.ContentDetector())
    # scene_manager.add_detector(sd.AdaptiveDetector())
    scene_manager.add_detector(sd.HashDetector())

    _ = scene_manager.detect_scenes(video)

    video_data = ffmpeg.get_video_metadata("ffprobe", video_path)

    scene_data = [
        SceneData(
            start_frame=x[0].get_frames(),
            end_frame=x[1].get_frames(),
        )
        for x in scene_manager.get_scene_list()
    ]

    while True:
        for i, scene in enumerate(scene_data[:-1]):
            if (
                (scene.end_frame - scene.start_frame) / video_data.total_frames
            ) < minimum_length_scene_seconds:
                scene_data[i].end_frame = scene_data[i + 1].end_frame
                del scene_data[i + 1]
                break
        else:
            break

    if len(scene_data) == 0:
        scene_data = [SceneData(start_frame=0, end_frame=video_data.total_frames)]

    return scene_data
