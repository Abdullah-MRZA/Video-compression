import matplotlib.pyplot as plt


def make_linegraph(
    title: str,
    x_title: str,
    y_title: str,
    linedata: list[tuple[str, list[float], list[float]]],
    size: tuple[int, int] | None = None,
    show: bool = False,
    grid: bool = True,
    opacity: float = 0.8,
    save_to_file: tuple[str, int] | None = None,
) -> None:
    """
    Makes a graph using matplotlib
    linedata --> list of multiple lines --> str of line name + tuple of (x list, y list)
    save_to_file --> tuple of filename + dpi to use (600 recommended)
    """

    if size is not None:
        plt.figure(figsize=size)

    for data in linedata:
        plt.plot(*data[1:], label=data[0], alpha=opacity)  # scatter

    plt.title(title)
    plt.xlabel(x_title)
    plt.ylabel(y_title)

    if len(linedata) > 1:
        plt.legend()
    if grid:
        plt.grid()
    if save_to_file is not None:
        plt.savefig(save_to_file[0], dpi=save_to_file[1])
    if show:
        plt.show()

    plt.close()
    plt.clf()
    plt.cla()


# made from: https://matplotlib.org/stable/gallery/text_labels_and_annotations/legend.html#sphx-glr-gallery-text-labels-and-annotations-legend-py
def make_better_linegraph(
    heuristic_list: list[float], crf_list: list[int], heuristic_name: str
):
    fig, ax = plt.subplots()

    a = len(heuristic_list)

    ax.plot(a, crf_list, "k--", label=heuristic_name)
    ax.plot(a, heuristic_list, "k:", label="CRF")
    # ax.plot(a, c + d, "k", label="Total message length")

    # legend = ax.legend(loc='upper center', shadow=True, fontsize='x-large')
    legend = ax.legend(shadow=True, fontsize="x-small")

    # Put a nicer background color on the legend.
    legend.get_frame().set_facecolor("C0")

    ax.set_title("CRF + heuristic over time")

    plt.show()
