from dataclasses import dataclass
from pathlib import Path


@dataclass()
class libx264:
    RANGE = range(0, 50)


type VideoCodec = libx264


@dataclass()
class inputVideoData:
    raw_video_path: Path
    raw_output_video_path: Path

    codec: VideoCodec


def main(): ...


if __name__ == "__main__":
    main()
