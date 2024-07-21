from . import ffmpeg
from . import v2_target_videoCRF
from . import ffmpeg_heuristics
from . import file_cache


def main() -> None:
    v2_target_videoCRF.compressing_video(
        v2_target_videoCRF.videoData(
            "input.mp4",
            "output-temp.mkv",
            ffmpeg.APPLE_HWENC_H265(bitdepth="yuv420p"),
            # ffmpeg.H265(preset="medium"),
            # ffmpeg.SVTAV1(preset=6),
            ffmpeg_heuristics.VMAF(90),
            minimum_scene_length_seconds=3,
            audio_commands="-c:a copy",
            multithreading_threads=5,
            scenes_length_sort="chronological",
            make_comparison_with_blend_filter=False,
        )
    )


if __name__ == "__main__":
    main()
    file_cache.cache_cleanup()
