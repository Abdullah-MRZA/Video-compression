import ffmpeg
from rich import print
import os
import ffmpeg_heuristics
import scene_detection
import graph_generate


class Compress_video:
    @staticmethod
    def compress_video(
        input_filename: str,
        ffmpeg_codec_information: ffmpeg.video,
        heuristic_type: ffmpeg_heuristics.heuristic,
        output_filename: str | None = None,
        # start_time_seconds: int = 0,
        # end_time_seconds: int = 0,
        crop_black_bars: bool = True,
        bit_depth: ffmpeg.bitdepth = "yuv420p10le",
        keyframe_placement: int | None = 200,
        ffmpeg_path: str = "ffmpeg",
        # draw_matplotlib_graph: bool = True,
        extra_current_crf_itterate_amount: int = 1,
    ):
        """
        This does practically all of the calculations
        This splits the video files into scenes, and then compresses them,
        targeting a specific video heuristic
        This also recombines the video at the end
        """

        video_scenes = scene_detection.find_scenes(input_filename)
        print(f"{video_scenes=}")

        video_data_crf_heuristic: list[tuple[int, float]] = []

        for i, scenes in enumerate(video_scenes):
            print(f"RUNNING SECTION {i} OF SCENE")
            optimal_crf_value, heuristic_value_of_encode = (
                Compress_video._compress_video_part(
                    input_filename=input_filename,
                    output_filename=f"{i}-{input_filename}",
                    part_beginning=scenes[0],
                    part_end=scenes[1],
                    heuristic_type=heuristic_type,
                    crop_black_bars=crop_black_bars,
                    bit_depth=bit_depth,
                    keyframe_placement=keyframe_placement,
                    ffmpeg_codec_information=ffmpeg_codec_information,
                    ffmpeg_path=ffmpeg_path,
                    extra_current_crf_itterate_amount=extra_current_crf_itterate_amount,
                )
            )
            video_data_crf_heuristic.append(
                (optimal_crf_value, heuristic_value_of_encode)
            )

        with graph_generate.linegraph_image(
            filename_without_extension="Video_information"
        ) as graph:
            graph.add_linegraph(
                x_data=list(range(len(video_data_crf_heuristic))),
                y_data=[x[0] for x in video_data_crf_heuristic],
                name="CRF",
                mode="lines+markers",
            )
            graph.add_linegraph(
                x_data=list(range(len(video_data_crf_heuristic))),
                y_data=[x[1] for x in video_data_crf_heuristic],
                name=heuristic_type.NAME,
                mode="lines+markers",
            )

        # graph = graph_generate.linegraph()
        # graph.add_linegraph()

        if output_filename is None:
            output_filename = f"RENDERED - {input_filename}"

        ffmpeg.concatenate_video_files(
            [f"{x}-test.mp4" for x in range(len(video_scenes))], output_filename
        )
        [os.remove(f"{x}-test.mp4") for x in range(len(video_scenes))]

    @staticmethod
    def _compress_video_part(
        input_filename: str,
        output_filename: str,
        part_beginning: str,
        part_end: str,
        heuristic_type: ffmpeg_heuristics.heuristic,
        crop_black_bars: bool,
        bit_depth: ffmpeg.bitdepth,
        keyframe_placement: int | None,
        ffmpeg_codec_information: ffmpeg.video,
        ffmpeg_path: str = "ffmpeg",
        extra_current_crf_itterate_amount: int = 1,
    ) -> tuple[int, float]:
        """
        Using a binary search approach on the whole range of CRF
        Would identify the ideal CRF for the closest heuristic value??
        Returns the heuristic value of the result
        """
        # use a 'binary search' approach? Is this optimal? (doubt it, but definitely functional)

        tempoary_video_file_name: str = f"TEMP-{input_filename}"

        with ffmpeg.FfmpegCommand(
            input_filename=input_filename,
            output_filename=tempoary_video_file_name,
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
                current_crf := (
                    (top_crf_value + bottom_crf_value)
                    // (2 * extra_current_crf_itterate_amount)
                )
                * extra_current_crf_itterate_amount
            ) not in all_heuristic_crf_data.values():
                # current_crf = (
                #     current_crf // extra_current_crf_itterate_amount
                # ) * extra_current_crf_itterate_amount

                print(f"RUNNING CRF VALUE {current_crf}")  # BUG HERE!!!
                # _ = input(
                #     f"{current_crf} - {current_crf in all_heuristic_crf_data.values()}"
                # )

                command.run_ffmpeg_command(current_crf)

                current_crf_heuristic = heuristic_type.overall(
                    source_video_path=input_filename,
                    encoded_video_path=tempoary_video_file_name,
                    source_start_end_time=(part_beginning, part_end),
                    encode_start_end_time=None,
                )

                all_heuristic_crf_data.update({current_crf_heuristic: current_crf})

                # ASSUMPTION THAT BIGGER IS BETTER (WARNING)
                if current_crf_heuristic > heuristic_type.target_score:
                    bottom_crf_value = current_crf
                elif current_crf_heuristic < heuristic_type.target_score:
                    top_crf_value = current_crf
                elif current_crf_heuristic == heuristic_type.target_score:
                    break
                print(
                    f"FINISHED RUNNING {current_crf} -> {current_crf_heuristic} compared to {heuristic_type.target_score} | {all_heuristic_crf_data}"
                )
                # _ = input("continue?")

            closest_crf_value_to_target_heuristic = min(
                (abs(x[0] - heuristic_type.target_score), x[1])
                for x in all_heuristic_crf_data.items()
            )[1]
            # print(closest_crf_value_to_target_heuristic)

            # closest_crf_value_to_target_heuristic = (
            #     closest_crf_value_to_target_heuristic[1]
            # )

            os.remove(tempoary_video_file_name)

            # _ = input(
            #     f"OPTIMAL CRF VALUE IS {closest_crf_value_to_target_heuristic} (continue?)"
            # )

            command.run_ffmpeg_command(
                closest_crf_value_to_target_heuristic,
                override_output_file_name=output_filename,
            )

            all_crf_heuristic_data = {v: k for k, v in all_heuristic_crf_data.items()}
            return closest_crf_value_to_target_heuristic, all_crf_heuristic_data[
                closest_crf_value_to_target_heuristic
            ]
            # return closest_crf_value_to_target_heuristic
