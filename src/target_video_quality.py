from rich import print
from rich.progress import track
import ffmpeg
import ffmpeg_heuristics
import graph_generate
import os
import scene_detection


class Compress_video:
    @staticmethod
    def compress_video(
        input_filename_with_extension: str,
        ffmpeg_codec_information: ffmpeg.video,
        heuristic_type: ffmpeg_heuristics.heuristic,
        output_filename_with_extension: str | None = None,
        # start_time_seconds: int = 0,
        # end_time_seconds: int = 0,
        crop_black_bars: bool = True,
        bit_depth: ffmpeg.bitdepth = "yuv420p10le",
        keyframe_placement: int | None = 200,
        ffmpeg_path: str = "ffmpeg",
        # draw_matplotlib_graph: bool = True,
        extra_current_crf_itterate_amount: int = 1,
        delete_tempoary_files: bool = True,
        scene_detection_threshold: float = 27.0,
        recombine_audio_from_input_file: bool = True,
    ):
        """
        This does practically all of the calculations
        This splits the video files into scenes, and then compresses them,
        targeting a specific video heuristic
        This also recombines the video at the end
        """

        video_scenes = scene_detection.find_scenes(
            video_path=input_filename_with_extension,
            threshold=scene_detection_threshold,
        )
        print(f"{video_scenes=}")
        print(f"Total Scenes in input file: {len(video_scenes[0])}")

        video_data_crf_heuristic: list[tuple[int, float]] = []

        for i, scenes in track(
            list(enumerate(video_scenes[0])),  # doesn't work with just enumerate
            description="[yellow]Processing scenes[/yellow]",
        ):
            print(f"RUNNING SECTION {i} OF SCENE")
            optimal_crf_value, heuristic_value_of_encode = (
                Compress_video._compress_video_part(
                    input_filename=input_filename_with_extension,
                    output_filename=f"{i}-{input_filename_with_extension}",
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
            filename_without_extension="Video_information",
            title_of_graph=f"CRF and {heuristic_type.NAME} throughout video",
            x_axis_name="Frames",
        ) as graph:
            graph.add_linegraph(
                x_data=[x[0] for x in video_scenes[1]],
                y_data=[x[0] for x in video_data_crf_heuristic],
                name="CRF",
                mode="lines+markers",
                on_left_right_side="left",
            )
            graph.add_linegraph(
                x_data=[x[0] for x in video_scenes[1]],
                y_data=[x[1] for x in video_data_crf_heuristic],
                name=heuristic_type.NAME,
                mode="lines+markers",
                on_left_right_side="right",
                # testing_y_axis_range=dict(range=[0, 100]),
            )

        # graph = graph_generate.linegraph()
        # graph.add_linegraph()

        if output_filename_with_extension is None:
            output_filename_with_extension = (
                f"RENDERED - {input_filename_with_extension}"
            )

        ffmpeg.concatenate_video_files(
            [
                f"{x}-{input_filename_with_extension}"
                for x in range(len(video_scenes[0]))
            ],
            output_filename_with_extension,
        )

        if recombine_audio_from_input_file:
            _ = os.system(
                " ".join(
                    [
                        ffmpeg_path,
                        f"-i {output_filename_with_extension}",
                        f"-i {input_filename_with_extension}",
                        "-c copy",
                        "-map 0:v:1",
                        "-map 1:a:1",
                        f"TEMP-{output_filename_with_extension}",
                    ]
                )
            )
            os.remove(output_filename_with_extension)
            os.rename(
                f"TEMP-{output_filename_with_extension}", output_filename_with_extension
            )

        if delete_tempoary_files:
            for x in range(len(video_scenes)):
                os.remove(f"{x}-{input_filename_with_extension}")

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
        ffmpeg_path: str,
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
                print(f"RUNNING CRF VALUE {current_crf}")

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
                    break  # very unlikely to get here

                print(
                    f"    FINISHED RUNNING {current_crf} -> {current_crf_heuristic} compared to {heuristic_type.target_score} | {all_heuristic_crf_data}"
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

            print(f"OPTIMAL CRF VALUE IS {closest_crf_value_to_target_heuristic}")

            command.run_ffmpeg_command(
                closest_crf_value_to_target_heuristic,
                override_output_file_name=output_filename,
            )

            all_crf_heuristic_data = {v: k for k, v in all_heuristic_crf_data.items()}
            return closest_crf_value_to_target_heuristic, all_crf_heuristic_data[
                closest_crf_value_to_target_heuristic
            ]
            # return closest_crf_value_to_target_heuristic
