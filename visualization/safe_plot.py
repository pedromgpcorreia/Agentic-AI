"""Plot component for SolaraViz that is safe while the model is running.

Mesa's make_plot_component reads the DataCollector while the model may still be stepping in
another thread; with a fast model it can read the reporters halfway through a collection and
fail with "Length of values does not match length of index". This component copies the data
first and cuts every series to the same length.
"""
import pandas as pd
import solara
from matplotlib.figure import Figure


def make_safe_plot_component(measures, post_process=None, xlabel="Step"):
    """measures: {reporter name: colour}, as in mesa.visualization.make_plot_component."""
    if isinstance(measures, str):
        measures = {measures: "#1a1a1a"}

    def SafePlot(model):
        data = model.datacollector.model_vars
        cols = {m: list(data.get(m, [])) for m in measures}
        n = min((len(v) for v in cols.values()), default=0)
        df = pd.DataFrame({m: v[:n] for m, v in cols.items()})
        fig = Figure(figsize=(6, 3), layout="constrained")   # keeps the axis labels inside
        ax = fig.subplots()
        for m, colour in measures.items():
            ax.plot(df.index, df[m], color=colour, label=m)
        ax.set_xlabel(xlabel)
        if post_process is not None:
            post_process(ax)
        elif len(measures) > 1:
            ax.legend(fontsize=7)
        return solara.FigureMatplotlib(fig, format="png", dpi=72)

    return SafePlot
