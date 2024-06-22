import ffmpeg
import os
import ffmpeg_heuristics
import scene_detection
# import matplotlib


class Compress_video:
    @staticmethod
    def compress_video(
        input_filename: str,
        ffmpeg_codec_information: ffmpeg.video,
        heuristic_type: ffmpeg_heuristics.heuristic,
        output_filename: str | None = None,
        start_time_seconds: int = 0,
        end_time_seconds: int = 0,
        crop_black_bars: bool = True,
        bit_depth: ffmpeg.bitdepth = "yuv420p10le",
        keyframe_placement: int | None = 200,
        ffmpeg_path: str = "ffmpeg",
        draw_matplotlib_graph: bool = True,
    ):
        """
        This does practically all of the calculations
        This splits the video files into scenes, and then compresses them,
        targeting a specific video heuristic
        This also recombines the video at the end
        """
        # with ffmpeg.FfmpegCommand(
        #     input_filename=input_filename,
        #     codec_information=ffmpeg_codec_information,
        #     output_filename=output_filename,
        #     start_time_seconds=start_time_seconds,
        #     end_time_seconds=end_time_seconds,
        #     crop_black_bars=crop_black_bars,
        #     bit_depth=bit_depth,
        #     keyframe_placement=keyframe_placement,
        #     ffmpeg_path=ffmpeg_path,
        # ) as command:
        video_scenes = scene_detection.find_scenes(input_filename)

        for i, scenes in enumerate(video_scenes):
            _ = Compress_video._compress_video_part(
                input_filename,
                f"{i}-{input_filename}",
                *scenes,
                heuristic_type,
                crop_black_bars,
                bit_depth,
                keyframe_placement,
                ffmpeg_codec_information,
            )

    @staticmethod
    def _compress_video_part(
        input_filename: str,
        output_filename: str,
        part_beginning: int,
        part_end: int,
        heuristic_type: ffmpeg_heuristics.heuristic,
        crop_black_bars: bool,
        bit_depth: ffmpeg.bitdepth,
        keyframe_placement: int | None,
        ffmpeg_codec_information: ffmpeg.video,
        ffmpeg_path: str = "ffmpeg",
    ) -> float:
        """
        Using a binary search approach on the whole range of CRF
        Would identify the ideal CRF for the closest heuristic value??
        Returns the heuristic value of the result
        """
        # use a 'binary search' approach? Is this optimal? (doubt it, but definitely functional)

        with ffmpeg.FfmpegCommand(
            input_filename=input_filename,
            output_filename=f"TEMP-{input_filename}",
            codec_information=ffmpeg_codec_information,
            start_time_seconds=part_beginning,
            end_time_seconds=part_end,
            crop_black_bars=crop_black_bars,
            bit_depth=bit_depth,
            keyframe_placement=keyframe_placement,
            ffmpeg_path=ffmpeg_path,
        ) as command:
            bottom_crf_value = min(ffmpeg_codec_information.ACCEPTED_CRF_RANGE)
            top_crf_value = max(ffmpeg_codec_information.ACCEPTED_CRF_RANGE)

            all_heuristic_crf_data: dict[float, int] = {}

            # at the end point, we would be doing the same calculation twice
            while (
                current_crf := (top_crf_value + bottom_crf_value) // 2
            ) not in all_heuristic_crf_data:
                command.run_ffmpeg_command(current_crf)
                current_crf_heuristic = heuristic_type.overall(
                    input_filename, f"TEMP-{input_filename}"
                )
                all_heuristic_crf_data.update({current_crf_heuristic: current_crf})

            closest_crf_value_to_target_heuristic = min(
                (x - heuristic_type.target_score, i)
                for i, x in enumerate(all_heuristic_crf_data)
            )[1]

            os.remove(f"TEMP-{input_filename}")

            command.run_ffmpeg_command(
                closest_crf_value_to_target_heuristic,
                override_output_file_name=output_filename,
            )

            all_crf_heuristic_data = {v: k for k, v in all_heuristic_crf_data.items()}
            return all_crf_heuristic_data[closest_crf_value_to_target_heuristic]
