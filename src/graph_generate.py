# import plotly.express as px
from types import TracebackType
from typing import Literal

import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    ) -> None:
        # self.fig = go.Figure()
        self.fig = make_subplots(specs=[[{"secondary_y": True}]])
        self.filename = filename_without_extension
        self.title_of_graph = title_of_graph
        self.fileformat = fileformat
        self.x_axis_name = x_axis_name

    def __enter__(self):
        return self

    def add_linegraph(
        self,
        x_data: list[int | float],
        y_data: list[int | float],
        name: str,
        mode: Literal["lines", "lines+markers"],
        on_left_right_side: Literal["left", "right"],
    ) -> None:
        _ = self.fig.add_trace(
            go.Scatter(
                x=x_data,
                y=y_data,
                mode=mode,
                name=name,
            ),
            secondary_y=(on_left_right_side == "left"),
        )
        _ = self.fig.update_yaxes(
            title_text=name, secondary_y=(on_left_right_side == "left")
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

        self.fig.write_image(self.filename + "." + self.fileformat)
