import ffmpeg
import v2_target_videoCRF
import ffmpeg_heuristics
import file_cache

# Vapoursynth scripts: https://www.l33tmeatwad.com/vapoursynth101/using-filters-functions#h.p_WmOexl9b_-mc

vapoursynth_script: str = "\n".join(
    [
        # "clip = core.fft3dfilter.FFT3DFilter(clip, sigma=1.5)",  # (Spatio-Temporal Denoisers)
        "clip = clip[::2]",  # (half frame rate)
        # "clip = core.f3kdb.Deband(clip)",  # (Banding Reduction)
    ]
)


def main() -> None:
    v2_target_videoCRF.compressing_video(
        v2_target_videoCRF.videoData(
            "moana.mp4",
            "OUTPUT-TEMP.mkv",
            vapoursynth_script,
            # ffmpeg.APPLE_HWENC_H265(bitdepth="p010le"),
            # ffmpeg.H265(preset="medium"),
            ffmpeg.H264(preset="fast"),
            # ffmpeg.SVTAV1(preset=6),
            ffmpeg_heuristics.VMAF(90),
            minimum_scene_length_seconds=4,
            audio_commands="-c:a copy",
            multithreading_threads=1,
            scenes_length_sort="smallest first",
            make_comparison_with_blend_filter=False,  # fix
            crop_black_bars=True,
        )
    )


if __name__ == "__main__":
    main()
    file_cache.cache_cleanup()
