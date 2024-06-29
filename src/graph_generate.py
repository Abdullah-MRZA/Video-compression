# import plotly.express as px
from types import TracebackType
from typing import Literal

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# import matplotlib.pyplot as plt
# import numpy as np

# import pandas as pd
# import matplotlib_graphs


# matplotlib_graphs.make_better_linegraph(
#     heuristic_list=[x[1] for x in video_data_crf_heuristic],
#     crf_list=[x[0] for x in video_data_crf_heuristic],
#     # heuristic_name=heuristic_type.NAME,
#     heuristic_name="VMAF",
# )

# df = px.data.gapminder().query("continent=='Oceania'")
# df = pd.DataFrame(
#     {
#         "heuristic": [x[0] for x in video_data_crf_heuristic],
#         "crf": [x[1] for x in video_data_crf_heuristic],
#         "time": list(range(len(video_data_crf_heuristic))),
#     }
# )

# fig = px.line(df, x="year", y="lifeExp", color="country")
# fig.write_image(".png")


class linegraph_image:
    def __init__(
        self,
        filename_without_extension: str,
        fileformat: Literal["png", "jpeg", "webp", "svg", "pdf"] = "png",
        title_of_graph: str | None = None,
        x_axis_name: str | None = None,
        save_data_to_file: bool = True,
    ) -> None:
        self.fig = go.Figure()
        self.fig = make_subplots(specs=[[{"secondary_y": True}]])
        self.filename_without_extension = filename_without_extension
        self.title_of_graph = title_of_graph
        self.fileformat = fileformat
        self.x_axis_name = x_axis_name
        self.save_data_to_file = save_data_to_file

    def __enter__(self):
        return self

    def add_linegraph(
        self,
        x_data: list[int | float],
        y_data: list[int | float],
        name: str,
        mode: Literal["lines", "lines+markers"],
        on_left_right_side: Literal["left", "right"],
        y_axis_range: range,
    ) -> None:
        _ = self.fig.add_trace(
            go.Scatter(
                x=x_data,
                y=y_data,
                mode=mode,
                name=name,  # , yaxis=testing_y_axis_range
            ),
            secondary_y=(on_left_right_side == "right"),
        )

        # changing range of y axis: https://stackoverflow.com/questions/55704058/set-the-range-of-the-y-axis-in-plotly
        _ = self.fig.update_yaxes(
            title_text=name,
            secondary_y=(on_left_right_side == "right"),
            range=[
                min(y_axis_range),
                max(y_axis_range),
            ],  # check if works (ALSO CHECK IF CAN BE REPLACED WITH NONE)
        )

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        _ = self.fig.update_layout(title_text=self.title_of_graph)

        if self.x_axis_name is not None:
            _ = self.fig.update_xaxes(title_text=self.x_axis_name)

        if self.save_data_to_file:
            self.fig.write_image(
                self.filename_without_extension + "." + self.fileformat
            )
        else:
            self.fig.show()


# class matplotlib_graphs:
#     def __init__(
#         self, filename_without_extension: str, filename_extension: Literal["png", "pdf"]
#     ) -> None:
#         self.fig, self.ax = plt.subplots()
#
#     def __enter__(self):
#         return self
#
#     def add_linegraph(
#         self, x_axis_data: list[float | int], y_axis_data: list[float | int]
#     ):
#         self.ax.plot(x_axis_data, y_axis_data)
#
#     def __exit__(
#         self,
#         exc_type: type[BaseException] | None,
#         exc_value: BaseException | None,
#         exc_traceback: TracebackType | None,
#     ) -> None:
#         self.plt.savefig(filename_without_extension + "." + filename_extension)
#
#     x = np.array([1, 2, 3, 4])
#     y = x * 2
#
#     # first plot with X and Y data
#     plt.plot(x, y)
#
#     x1 = [2, 4, 6, 8]
#     y1 = [3, 5, 7, 9]
#
#     # second plot with x1 and y1 data
#     plt.plot(x1, y1, "-.")
#
#     plt.xlabel("X-axis data")
#     plt.ylabel("Y-axis data")
#     plt.title("multiple plots")
#     plt.show()
