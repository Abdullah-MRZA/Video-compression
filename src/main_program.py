import ffmpeg
import v2_target_videoCRF
import ffmpeg_heuristics
import file_cache


def main() -> None:
    v2_target_videoCRF.compressing_video(
        v2_target_videoCRF.videoData(
            "medium.mp4",
            "OUTPUT-TEMP.mkv",
            # "clip = clip[::2]",
            "",
            # ffmpeg.APPLE_HWENC_H265(bitdepth="yuv420p"),
            # ffmpeg.H265(preset="medium"),
            ffmpeg.H264(preset="fast"),
            # ffmpeg.SVTAV1(preset=6),
            ffmpeg_heuristics.VMAF(90),
            minimum_scene_length_seconds=4,
            audio_commands="-c:a copy",
            multithreading_threads=4,
            scenes_length_sort="smallest first",
            make_comparison_with_blend_filter=False,  # fix
        )
    )


if __name__ == "__main__":
    main()
    file_cache.cache_cleanup()
