# import plotly.express as px
from types import TracebackType
from typing import Literal
import plotly.graph_objects as go
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
    ) -> None:
        self.fig = go.Figure()
        self.filename = filename_without_extension
        self.fileformat = fileformat

    def __enter__(self):
        return self

    def add_linegraph(
        self,
        x_data: list[int | float],
        y_data: list[int | float],
        name: str,
        mode: Literal["lines", "lines+markers"],
    ) -> None:
        _ = self.fig.add_trace(
            go.Scatter(
                x=x_data,
                y=y_data,
                mode=mode,
                name=name,
            )
        )

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        self.fig.write_image(self.filename + "." + self.fileformat)
