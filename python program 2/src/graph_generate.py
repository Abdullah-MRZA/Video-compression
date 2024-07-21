from types import TracebackType
from typing import Literal

import matplotlib.pyplot as plt


# pyright: reportUnknownMemberType=false

# https://matplotlib.org/stable/gallery/subplots_axes_and_figures/two_scales.html#sphx-glr-gallery-subplots-axes-and-figures-two-scales-py


class LinegraphImage:
    def __init__(
        self,
        filename: str,
        x_axis_name: str,
        title_of_graph: str,
        # save_data_to_file: bool = True,
    ) -> None:
        self.fig, self.ax_left = plt.subplots()
        self.first: bool = True

        self.filename = filename
        self.title_of_graph = title_of_graph
        self.x_axis_name = x_axis_name

    def __enter__(self):
        return self

    def add_linegraph_left(
        self,
        x_data: list[int | float],
        y_data: list[int | float],
        name_of_axes: str,
        y_axis_range: range,
        colour: Literal["red", "blue"],
    ) -> None:
        str_colour = f"tab:{colour}"
        _ = self.ax_left.set_xlabel(self.x_axis_name)
        _ = self.ax_left.set_ylabel(name_of_axes, color=str_colour)
        _ = self.ax_left.set_ylim(min(y_axis_range), max(y_axis_range))
        _ = self.ax_left.plot(x_data, y_data, color=str_colour)
        self.ax_left.tick_params(axis="y", labelcolor=str_colour)

    def add_linegraph_right(
        self,
        x_data: list[int | float],
        y_data: list[int | float],
        name_of_axes: str,
        y_axis_range: range,
        colour: Literal["red", "blue"],
    ) -> None:
        ax_right = self.ax_left.twinx()
        str_colour = f"tab:{colour}"

        _ = ax_right.set_ylabel(name_of_axes, color=str_colour)
        _ = ax_right.set_ylim(min(y_axis_range), max(y_axis_range))
        ax_right.plot(x_data, y_data, color=str_colour)  # this works
        ax_right.tick_params(axis="y", labelcolor=str_colour)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        # self.fig.tight_layout()
        _ = plt.title(self.title_of_graph)
        # _ = plt.legend()
        self.fig.set_size_inches(18.5, 10.5, forward=True)
        plt.savefig(self.filename, dpi=100)


if __name__ == "__main__":
    with LinegraphImage("TEST.png", "frames", "This is a test image") as image:
        x = [float(x) for x in [1, 2, 3, 4]]
        y1 = [float(x) for x in [2, 3, 4, 5]]
        y2 = [float(x) for x in [4, 3, 2, 1]]
        image.add_linegraph_left(x, y1, "first one", range(0, 5), "red")
        image.add_linegraph_right(x, y2, "second one", range(-10, 10), "blue")
