"""Reproduce the five-panel Typhoon Saola forecast-refinement figure."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd
import rasterio

from .paths import OUTPUT, RAW


SID = "2023234N18128"
INIT_TIME = pd.Timestamp("2023-08-31 12:00", tz="UTC")
END_TIME = pd.Timestamp("2023-09-03 12:00", tz="UTC")
DEFAULT_DATA = RAW / "saola"
DEFAULT_OUTPUT = OUTPUT / "Figure_Forecast_Saola.pdf"

MODEL_ORDER = [
    "Physics-based",
    "Deterministic AI",
    "Probabilistic AI",
    "AI Post-Processing",
]
MODEL_STYLE = {
    "Physics-based": {"color": "#ff7f0e", "linestyle": "-"},
    "Deterministic AI": {"color": "#9467bd", "linestyle": "-"},
    "Probabilistic AI": {"color": "#e6b800", "linestyle": "-"},
    "AI Post-Processing": {"color": "#9467bd", "linestyle": "--"},
}


def _column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    lookup = {str(name).strip().lower(): name for name in frame.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def _model_family(label: str) -> str | None:
    value = label.lower().replace("_", " ").replace("-", " ")
    if "postprocess" in value or "post processing" in value or "ann" in value:
        return "AI Post-Processing"
    if "genc" in value or "gen cast" in value or "probabil" in value:
        return "Probabilistic AI"
    if "pangu" in value:
        return "Deterministic AI"
    if (
        "hres" in value
        or "ecmwf" in value
        or "tigge" in value
        or "ifs" in value
        or "physics" in value
    ):
        return "Physics-based"
    for item in MODEL_ORDER:
        if value.strip() == item.lower():
            return item
    return None


def load_observations(data_dir: Path = DEFAULT_DATA) -> pd.DataFrame:
    """Load the Saola subset from raw IBTrACS CSV files without rewriting them."""

    files = sorted((data_dir / "ibtracs").rglob("*.csv"))
    root_file = data_dir / "2023_IBTrACS.csv"
    if root_file.exists():
        files.append(root_file)
    if not files:
        raise FileNotFoundError(
            "No IBTrACS CSV found. Copy the HPC ibtracs directory (or "
            "2023_IBTrACS.csv) under data/raw/saola/."
        )

    pieces: list[pd.DataFrame] = []
    for path in files:
        header = pd.read_csv(path, nrows=0)
        wanted = {
            "sid", "iso_time", "time", "valid_time", "lat", "lon",
            "usa_wind", "wind_kts", "wind", "vmax_kt", "usa_pres",
            "mslp_hpa", "pressure", "pres", "pmin",
        }
        usecols = [column for column in header.columns if column.lower() in wanted]
        frame = pd.read_csv(path, usecols=usecols, low_memory=False)
        sid_col = _column(frame, ["SID", "sid"])
        time_col = _column(frame, ["ISO_TIME", "time", "valid_time"])
        lat_col = _column(frame, ["LAT", "lat"])
        lon_col = _column(frame, ["LON", "lon"])
        wind_col = _column(frame, ["USA_WIND", "wind_kts", "wind", "vmax_kt"])
        pressure_col = _column(
            frame, ["USA_PRES", "mslp_hpa", "pressure", "pres", "pmin"]
        )
        if not all([sid_col, time_col, lat_col, lon_col]):
            continue
        frame = frame.loc[frame[sid_col].astype(str).eq(SID)].copy()
        if frame.empty:
            continue
        subset = pd.DataFrame(
            {
                "sid": frame[sid_col].astype(str),
                "time": pd.to_datetime(
                    frame[time_col],
                    format="%Y-%m-%d %H:%M:%S",
                    errors="coerce",
                    utc=True,
                ),
                "lat": pd.to_numeric(frame[lat_col], errors="coerce"),
                "lon": pd.to_numeric(frame[lon_col], errors="coerce"),
                "wind_kts": pd.to_numeric(
                    frame[wind_col] if wind_col else np.nan, errors="coerce"
                ),
                "mslp_hpa": pd.to_numeric(
                    frame[pressure_col] if pressure_col else np.nan, errors="coerce"
                ),
            }
        )
        pieces.append(subset.loc[subset["sid"].eq(SID)])

    if not pieces or all(piece.empty for piece in pieces):
        raise ValueError(f"No IBTrACS rows found for Saola SID {SID}")
    observations = pd.concat(pieces, ignore_index=True).drop_duplicates()
    return observations.sort_values("time")


def load_forecasts(data_dir: Path = DEFAULT_DATA) -> pd.DataFrame:
    """Normalize the raw 2023 TCBench result CSVs used by the source figure."""

    files = sorted((data_dir / "forecasts").rglob("*.csv"))
    if not files:
        raise FileNotFoundError(
            "No forecast CSVs found under data/raw/saola/forecasts/. Copy the "
            "2023 CSVs from the HPC 'TCBench Results' directory there."
        )

    pieces: list[pd.DataFrame] = []
    for path in files:
        frame = pd.read_csv(path, low_memory=False)
        sid_col = _column(frame, ["SID", "sid"])
        init_col = _column(frame, ["Initial Time", "init_time", "init"])
        valid_col = _column(frame, ["Valid Time", "valid_time"])
        lat_col = _column(frame, ["lat", "LAT"])
        lon_col = _column(frame, ["lon", "LON"])
        wind_col = _column(frame, ["wind max", "vmax_kt", "wind_kts"])
        pressure_col = _column(
            frame, ["pres min", "pressure min", "mslp_hpa", "pmin"]
        )
        member_col = _column(frame, ["ensemble_idx", "member"])
        model_col = _column(frame, ["model", "model_name"])
        if not all([sid_col, init_col, valid_col]):
            continue
        frame = frame.loc[frame[sid_col].astype(str).eq(SID)].copy()
        if frame.empty:
            continue

        if model_col:
            families = frame[model_col].astype(str).map(_model_family)
        else:
            families = pd.Series(_model_family(path.stem), index=frame.index)
        if families.isna().all():
            continue

        member_values = (
            frame[member_col]
            if member_col
            else pd.Series(0, index=frame.index, dtype=float)
        )
        subset = pd.DataFrame(
            {
                "sid": frame[sid_col].astype(str),
                "init_time": pd.to_datetime(frame[init_col], errors="coerce", utc=True),
                "valid_time": pd.to_datetime(
                    frame[valid_col], errors="coerce", utc=True
                ),
                "lat": pd.to_numeric(
                    frame[lat_col] if lat_col else np.nan, errors="coerce"
                ),
                "lon": pd.to_numeric(
                    frame[lon_col] if lon_col else np.nan, errors="coerce"
                ),
                "vmax_kt": pd.to_numeric(
                    frame[wind_col] if wind_col else np.nan, errors="coerce"
                ),
                "mslp_hpa": pd.to_numeric(
                    frame[pressure_col] if pressure_col else np.nan, errors="coerce"
                ),
                "member": pd.to_numeric(
                    member_values, errors="coerce"
                ).fillna(0),
                "model": families,
                "source_file": path.name,
                "is_summary": "results" in path.stem.lower(),
            }
        )
        pieces.append(subset)

    if not pieces:
        raise ValueError("No recognizable TCBench forecast CSV schemas were found")
    forecasts = pd.concat(pieces, ignore_index=True)
    keep = (
        forecasts["sid"].eq(SID)
        & forecasts["init_time"].eq(INIT_TIME)
        & forecasts["valid_time"].between(INIT_TIME, END_TIME)
        & forecasts["model"].notna()
    )
    forecasts = forecasts.loc[keep].copy()
    missing = [model for model in MODEL_ORDER if model not in set(forecasts["model"])]
    if missing:
        raise ValueError(
            "The Saola initialization is missing model families: " + ", ".join(missing)
        )
    return forecasts.sort_values(["model", "valid_time", "member"])


def _mean_series(rows: pd.DataFrame, column: str) -> pd.Series:
    summary = rows.loc[rows["is_summary"] & rows[column].notna()]
    source = summary if not summary.empty else rows.loc[rows[column].notna()]
    return source.groupby("valid_time")[column].mean().sort_index()


def _configure_map(ax, extent: tuple[float, float, float, float], *, dark_ocean: bool):
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from cartopy.mpl.ticker import LatitudeFormatter, LongitudeFormatter

    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#102044", zorder=0)
    ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#e8e6df", zorder=1)
    coast_color = "white" if dark_ocean else "black"
    ax.coastlines("50m", linewidth=0.6, color=coast_color, zorder=4)
    lon_ticks = np.arange(np.ceil(extent[0] / 1.5) * 1.5, extent[1] + 0.01, 1.5)
    lat_ticks = np.arange(np.ceil(extent[2] / 1.5) * 1.5, extent[3] + 0.01, 1.5)
    ax.set_xticks(lon_ticks, crs=ccrs.PlateCarree())
    ax.set_yticks(lat_ticks, crs=ccrs.PlateCarree())
    ax.xaxis.set_major_formatter(LongitudeFormatter(number_format="g"))
    ax.yaxis.set_major_formatter(LatitudeFormatter(number_format="g"))
    ax.grid(True, color="0.7", linewidth=0.5, alpha=0.65)


def _read_tiff(path: Path):
    with rasterio.open(path) as source:
        bands = source.read().astype(float)
        extent = (source.bounds.left, source.bounds.right, source.bounds.bottom, source.bounds.top)
        transform = source.transform
        x = transform.c + np.arange(source.width) * transform.a
        y = transform.f + np.arange(source.height) * transform.e
    if bands.shape[0] >= 3:
        u, v, speed = bands[:3]
    elif bands.shape[0] == 2:
        u, v = bands
        speed = np.hypot(u, v)
    else:
        u = v = None
        speed = bands[0]
    return u, v, speed, extent, x, y


def make_figure(
    data_dir: Path = DEFAULT_DATA,
    output_path: Path = DEFAULT_OUTPUT,
) -> None:
    """Create the five-panel Saola PDF and a PNG preview from raw inputs."""

    import cartopy
    import cartopy.crs as ccrs

    cartopy.config["data_dir"] = str(RAW / "natural_earth")
    observations = load_observations(data_dir)
    forecasts = load_forecasts(data_dir)

    ccmp_path = data_dir / "CCMP_Wind_Analysis_20230901_V03_merge3_3.tif"
    dl_path = data_dir / "Deep_Learning_Wind_20230901_V03_merge3_3.tif"
    station_path = data_dir / "station_loc.txt"
    for path in [ccmp_path, dl_path, station_path]:
        if not path.exists():
            raise FileNotFoundError(path)

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["STIXGeneral", "DejaVu Serif"],
            "mathtext.fontset": "stix",
            # The figure is reduced substantially in the article layout. These
            # sizes are deliberately pushed until the map labels and legend
            # remain separated at full scale.
            "font.size": 20,
            "axes.titlesize": 21,
            "axes.labelsize": 20,
            "xtick.labelsize": 18,
            "ytick.labelsize": 18,
            "legend.fontsize": 18,
        }
    )
    fig = plt.figure(figsize=(16, 18))
    outer = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.12], hspace=0.18)
    top = outer[0].subgridspec(1, 2, wspace=0.10)
    right = top[0, 1].subgridspec(2, 1, hspace=0.18)
    bottom = outer[1].subgridspec(1, 2, wspace=0.09)

    ax_track = fig.add_subplot(top[0, 0], projection=ccrs.PlateCarree())
    ax_wind = fig.add_subplot(right[0, 0])
    ax_pressure = fig.add_subplot(right[1, 0], sharex=ax_wind)
    ax_ccmp = fig.add_subplot(bottom[0, 0], projection=ccrs.PlateCarree())
    ax_dl = fig.add_subplot(bottom[0, 1], projection=ccrs.PlateCarree())
    title_box = {"facecolor": "white", "alpha": 0.9, "boxstyle": "round,pad=0.2"}

    _configure_map(ax_track, (108.0, 118.0, 18.5, 24.6), dark_ocean=False)
    # Fill the same vertical allocation as panels (b) and (c). Cartopy's
    # default equal geographic aspect otherwise compresses this wide domain.
    ax_track.set_aspect("auto")
    obs = observations.loc[observations["time"].between(INIT_TIME, END_TIME)]
    ax_track.plot(obs["lon"], obs["lat"], color="black", linewidth=1.6, zorder=5)
    ax_track.scatter(
        obs["lon"], obs["lat"], s=14, facecolor="white", edgecolor="black", zorder=6
    )
    for model in MODEL_ORDER:
        rows = forecasts.loc[forecasts["model"].eq(model)].dropna(subset=["lat", "lon"])
        track = rows.groupby("valid_time")[["lat", "lon"]].mean().sort_index()
        style = MODEL_STYLE[model]
        ax_track.plot(
            track["lon"], track["lat"], linewidth=2.0, marker="o", markersize=3,
            color=style["color"], linestyle=style["linestyle"], zorder=5,
        )
    ax_track.text(
        0.02, 0.98, "(a)  Tropical Cyclone Track Forecast", transform=ax_track.transAxes,
        ha="left", va="top", fontsize=21, fontweight="bold", bbox=title_box,
    )
    handles = [Line2D([0], [0], color="black", marker="o", label="Observations")]
    handles.extend(
        Line2D([0], [0], linewidth=2, label=model, **MODEL_STYLE[model])
        for model in MODEL_ORDER
    )
    ax_track.legend(handles=handles, loc="lower right", frameon=True)

    def plot_timeseries(ax, observation_column: str, forecast_column: str, ylabel: str):
        ax.plot(observations["time"], observations[observation_column], color="black", linewidth=2.0)
        for model in MODEL_ORDER:
            rows = forecasts.loc[forecasts["model"].eq(model)]
            series = _mean_series(rows, forecast_column)
            style = MODEL_STYLE[model]
            ax.plot(series.index, series.values, linewidth=1.8, **style)
            members = rows.loc[~rows["is_summary"] & rows[forecast_column].notna()]
            if (
                model in {"Probabilistic AI", "AI Post-Processing"}
                and members["member"].nunique() > 1
            ):
                # Match the source figure: shade the full memberwise ensemble
                # range, not a standard-deviation or confidence interval.
                grouped = members.groupby("valid_time")[forecast_column]
                lower = grouped.min().sort_index()
                upper = grouped.max().reindex(lower.index)
                ax.fill_between(
                    lower.index,
                    lower.values,
                    upper.values,
                    color=style["color"], alpha=0.14, linewidth=0,
                )
        ax.set_ylabel(ylabel)
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.spines["left"].set_visible(False)
        ax.grid(True, color="0.82", linewidth=0.5, alpha=0.8)
        ax.set_xlim(INIT_TIME, END_TIME)

    plot_timeseries(ax_wind, "wind_kts", "vmax_kt", "Max wind (kt)")
    plot_timeseries(ax_pressure, "mslp_hpa", "mslp_hpa", "Sea-level pressure (hPa)")
    ax_wind.text(
        0.98, 0.98, "(b)  Intensity Forecast", transform=ax_wind.transAxes,
        ha="right", va="top", fontsize=21, bbox=title_box,
    )
    ax_pressure.text(
        0.02, 0.98, "(c)  Minimum Sea Level Pressure", transform=ax_pressure.transAxes,
        ha="left", va="top", fontsize=21, bbox=title_box,
    )

    tick_times = pd.date_range(INIT_TIME, END_TIME, freq="12h")
    for ax in [ax_wind, ax_pressure]:
        ax.set_xticks(tick_times)

    def time_label(value, _position):
        instant = mdates.num2date(value)
        return "12:00" if instant.hour == 12 else instant.strftime("%b-%d")

    formatter = FuncFormatter(time_label)
    ax_wind.xaxis.set_major_formatter(formatter)
    ax_pressure.xaxis.set_major_formatter(formatter)
    ax_wind.xaxis.tick_top()
    ax_wind.tick_params(labelbottom=False, labeltop=True)
    ax_pressure.xaxis.tick_bottom()
    ax_pressure.tick_params(labelbottom=True)

    stations = np.loadtxt(station_path)
    images = []
    for ax, path, title, vectors in [
        (ax_ccmp, ccmp_path, "(d)  Near Real-Time Coarse Analysis Wind Field", True),
        (ax_dl, dl_path, "(e)  Deep Learning Downscaled Wind Magnitude", False),
    ]:
        u, v, speed, extent, x, y = _read_tiff(path)
        _configure_map(ax, extent, dark_ocean=True)
        if ax is ax_dl:
            # Keep panel (e)'s latitude labels out of panel (d)'s map area.
            ax.yaxis.tick_right()
            ax.tick_params(axis="y", labelleft=False, labelright=True)
        image = ax.imshow(
            speed, extent=extent, origin="upper", transform=ccrs.PlateCarree(),
            cmap="turbo", vmin=0, vmax=38, zorder=2,
        )
        images.append(image)
        if vectors and u is not None and v is not None:
            xx, yy = np.meshgrid(x, y)
            ax.quiver(
                xx[::2, ::2], yy[::2, ::2], u[::2, ::2], v[::2, ::2],
                transform=ccrs.PlateCarree(), color="black", width=0.0025,
                scale=700, zorder=4,
            )
        ax.scatter(
            stations[:, 1], stations[:, 0], s=10, color="black",
            edgecolor="none", transform=ccrs.PlateCarree(), zorder=5,
        )
        ax.text(
            0.02, 0.98, title, transform=ax.transAxes, ha="left", va="top",
            fontsize=21, fontweight="bold", bbox=title_box, zorder=6,
        )

    fig.subplots_adjust(left=0.06, right=0.93, top=0.97, bottom=0.10)
    top_box = ax_wind.get_position()
    bottom_box = ax_pressure.get_position()
    fig.text(
        top_box.x0 + top_box.width / 2,
        bottom_box.y1 + (top_box.y0 - bottom_box.y1) / 2,
        "← Reference (Target) Time →",
        ha="center", va="center", fontweight="bold",
    )
    color_axis = fig.add_axes([0.06, 0.055, 0.87, 0.020])
    colorbar = fig.colorbar(images[-1], cax=color_axis, orientation="horizontal")
    colorbar.set_label("Wind Speed (m/s)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    fig.savefig(output_path.with_suffix(".png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
