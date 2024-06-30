from dataclasses import dataclass
import scenedetect as sd
# from scenedetect.frame_timecode import FrameTimecode
# from rich import print


@dataclass()
class scene_data:
    start_frame: int
    start_timecode: str

    end_frame: int
    end_timecode: str


def find_scenes(
    video_path: str,
    threshold: float,
    # ) -> tuple[list[tuple[str, str]], list[tuple[float, float]]]:
) -> list[scene_data]:  # list[tuple[FrameTimecode, FrameTimecode]]:
    """
    Function that gets the frames of the different scenes in the video
    - for threshold, 27.0 is default value
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
    # return (
    #     [
    #         (x[0].get_timecode(), x[1].get_timecode())
    #         for x in scene_manager.get_scene_list()
    #     ],
    #     [
    #         (x[0].get_frames(), x[1].get_frames())
    #         for x in scene_manager.get_scene_list()
    #     ],
    # )

    return [
        scene_data(
            start_frame=x[0].get_frames(),
            end_frame=x[1].get_frames(),
            start_timecode=x[0].get_timecode(),
            end_timecode=x[1].get_timecode(),
        )
        for x in scene_manager.get_scene_list()  # BUG: if len=0 then program will crash!!
    ]


# def scene_data_minimum_size(data: list[scene_data]) -> list[scene_data]:
#     ...

# data = find_scenes("input.mov", threshold=27)
# # print(f"{data=}")
# print(data)

# print([x[0].get_seconds() for x in data])


# print(find_scenes("test.mp4"))
