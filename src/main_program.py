from pathlib import Path
import time
import ffmpeg
import v2_target_videoCRF
import ffmpeg_heuristics
import file_cache
import videodata

# Vapoursynth scripts: https://www.l33tmeatwad.com/vapoursynth101/using-filters-functions#h.p_WmOexl9b_-mc

vapoursynth_script: str = "\n".join(
    [
        # "clip = core.fft3dfilter.FFT3DFilter(clip, sigma=1.5)",  # (Spatio-Temporal Denoisers)
        # "clip = clip[::2]",  # (half frame rate)
        # "clip = core.f3kdb.Deband(clip)",  # (Banding Reduction)
    ]
)

# time_calculating_scenes: float = 0
# time_finding_target_CRF: float = 0
# time_rendering_final_video: float = 0


def main() -> None:
    video_input = videodata.RawVideoData(
        input_filename=Path("small.mp4"),
        output_filename=Path("output-temp.mkv"),
        vapoursynth_script=videodata.vapoursynth_data(
            vapoursynth_script=vapoursynth_script,
            vapoursynth_seek_method="ffms2",
            crop_black_bars=True,
        ),
    )

    video_data = v2_target_videoCRF.videoInputData(
        video_input,
        # ffmpeg.APPLE_HWENC_H265(bitdepth="p010le"),
        # ffmpeg.H265(preset="medium"),
        # ffmpeg.H264(preset="slower"),
        ffmpeg.SVTAV1(preset=6),
        # ffmpeg.SVTAV1(preset=6, film_grain=ffmpeg.SVTAV1(0).Filmgrain(4, False)),
        ffmpeg_heuristics.VMAF(94),
        minimum_scene_length_seconds=1,
        audio_commands="-c:a libopus",
        multithreading_threads=3,
        scenes_length_sort="largest first",
        # make_comparison_with_blend_filter=False,  # fix
        render_final_video=True,
    )

    v2_target_videoCRF.compressing_video(video_data)


if __name__ == "__main__":
    start_time = time.perf_counter()
    main()
    file_cache.cache_cleanup()
    file_cache.print_times_of_functions()
    elapsed_time = time.perf_counter() - start_time

    print(f"\n\nOverall elapsed time: {elapsed_time}")
