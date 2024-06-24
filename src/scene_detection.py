import scenedetect as sd
from scenedetect.frame_timecode import FrameTimecode


def find_scenes(
    video_path: str, threshold: float = 27.0
) -> tuple[
    list[tuple[str, str]], list[tuple[float, float]]
]:  # list[tuple[FrameTimecode, FrameTimecode]]:
    """
    Function that gets the frames of the different scenes in the video
    """
    video = sd.open_video(video_path)
    scene_manager = sd.SceneManager()
    scene_manager.add_detector(sd.ContentDetector(threshold=threshold))

    # Detect all scenes in video from current position to end.
    _ = scene_manager.detect_scenes(video)

    # `get_scene_list` returns a list of start/end timecode pairs
    # for each scene that was found.
    # return scene_manager.get_scene_list()

    # (x[0].get_frames(), x[1].get_frames()) for x in scene_manager.get_scene_list()
    return (
        [
            (x[0].get_timecode(), x[1].get_timecode())
            for x in scene_manager.get_scene_list()
        ],
        [
            (x[0].get_frames(), x[1].get_frames())
            for x in scene_manager.get_scene_list()
        ],
    )


# data = find_scenes("test.mp4")
# print(f"{data=}")
#
# print([x[0].get_seconds() for x in data])


# print(find_scenes("test.mp4"))
