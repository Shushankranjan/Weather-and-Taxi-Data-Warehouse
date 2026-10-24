"""
Analysis Chart Generator.

Executes business queries against the data warehouse and generates
publication-quality charts saved to docs/charts/.
Implements FR-35.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from src.utils.db import get_connection, get_project_root
from src.utils.logger import get_logger, log_stage
from src.utils.config import load_config

logger = get_logger(__name__)


def setup_plot_style():
    """Configure clean, modern aesthetics for charts."""
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.autolayout": True,
    })


@log_stage("Generate Charts")
def generate_all_charts(output_dir: Path = None):
    """
    Run analytics queries and save visual figures.

    Args:
        output_dir: Path to directory where charts will be saved.
    """
    root = get_project_root()
    if output_dir is None:
        output_dir = root / "docs" / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config()
    db_path = config["paths"]["database"]

    setup_plot_style()

    with get_connection(db_path) as conn:
        # Chart 1: Rain vs Dry Trip Demand
        logger.info("Generating Chart 1: Rain vs. Dry trip demand...")
        q2_sql = (root / "sql" / "analysis" / "q2_rain_vs_dry.sql").read_text(encoding="utf-8")
        df_weather = conn.execute(q2_sql).fetchdf()

        if not df_weather.empty:
            fig, ax = plt.subplots(figsize=(8, 5))
            colors = ["#4C78A8", "#F58518", "#E45756", "#72B7B2"][:len(df_weather)]
            bars = ax.bar(df_weather["weather_category"], df_weather["trip_count"], color=colors, width=0.5)
            ax.set_title("Total Taxi Trips by Weather Condition")
            ax.set_xlabel("Weather Condition")
            ax.set_ylabel("Number of Trips")
            ax.yaxis.set_major_formatter(lambda x, pos: f"{int(x):,}")

            for bar in bars:
                height = bar.get_height()
                ax.annotate(f"{int(height):,}",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 4),
                            textcoords="offset points",
                            ha="center", va="bottom", fontsize=10, fontweight="bold")

            fig_path = output_dir / "q2_rain_vs_dry.png"
            fig.savefig(fig_path, dpi=300)
            plt.close(fig)
            logger.info(f"  ✔ Saved: {fig_path}")

        # Chart 2: Top Pickup Zones by Trips & Total Revenue
        logger.info("Generating Chart 2: Top 10 pickup zones...")
        q4_sql = (root / "sql" / "analysis" / "q4_top_zones.sql").read_text(encoding="utf-8")
        df_zones = conn.execute(q4_sql).fetchdf().head(10)

        if not df_zones.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            y_pos = range(len(df_zones))
            labels = [f"{z} ({b})" for z, b in zip(df_zones["zone"], df_zones["borough"])]
            bars = ax.barh(y_pos, df_zones["trip_count"], color="#2B5C8F", height=0.6)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels)
            ax.invert_yaxis()
            ax.set_title("Top 10 NYC Taxi Pickup Zones by Trip Volume")
            ax.set_xlabel("Trip Count")
            ax.xaxis.set_major_formatter(lambda x, pos: f"{int(x):,}")

            for bar in bars:
                width = bar.get_width()
                ax.annotate(f"{int(width):,}",
                            xy=(width, bar.get_y() + bar.get_height() / 2),
                            xytext=(5, 0),
                            textcoords="offset points",
                            ha="left", va="center", fontsize=9)

            fig_path = output_dir / "q4_top_pickup_zones.png"
            fig.savefig(fig_path, dpi=300)
            plt.close(fig)
            logger.info(f"  ✔ Saved: {fig_path}")

        # Chart 3: Tip Percentage by Payment Type
        logger.info("Generating Chart 3: Tip percentage by payment type...")
        q5_sql = (root / "sql" / "analysis" / "q5_tip_by_payment.sql").read_text(encoding="utf-8")
        df_tip = conn.execute(q5_sql).fetchdf()

        if not df_tip.empty:
            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(df_tip["payment_type_description"], df_tip["avg_tip_percentage"], color="#59A14F", width=0.45)
            ax.set_title("Average Tip Percentage by Payment Method")
            ax.set_xlabel("Payment Method")
            ax.set_ylabel("Average Tip (%)")
            plt.xticks(rotation=15, ha="right")

            for bar in bars:
                height = bar.get_height()
                ax.annotate(f"{height:.1f}%",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 4),
                            textcoords="offset points",
                            ha="center", va="bottom", fontsize=10, fontweight="bold")

            fig_path = output_dir / "q5_tip_by_payment.png"
            fig.savefig(fig_path, dpi=300)
            plt.close(fig)
            logger.info(f"  ✔ Saved: {fig_path}")

        # Chart 4: Temperature Effect on Average Fare and Distance
        logger.info("Generating Chart 4: Temperature effect...")
        q3_sql = (root / "sql" / "analysis" / "q3_temperature_effect.sql").read_text(encoding="utf-8")
        df_temp = conn.execute(q3_sql).fetchdf()

        if not df_temp.empty:
            fig, ax1 = plt.subplots(figsize=(9, 5))

            color1 = "#1F77B4"
            ax1.set_xlabel("Temperature Band (°C)")
            ax1.set_ylabel("Avg Distance (Miles)", color=color1)
            line1 = ax1.plot(df_temp["temp_range"], df_temp["avg_distance_miles"], color=color1, marker="o", linewidth=2, label="Avg Distance")
            ax1.tick_params(axis="y", labelcolor=color1)
            plt.xticks(rotation=25, ha="right")

            ax2 = ax1.twinx()
            color2 = "#E15759"
            ax2.set_ylabel("Avg Fare ($)", color=color2)
            line2 = ax2.plot(df_temp["temp_range"], df_temp["avg_fare"], color=color2, marker="s", linewidth=2, linestyle="--", label="Avg Fare")
            ax2.tick_params(axis="y", labelcolor=color2)

            plt.title("Impact of Temperature on Taxi Trip Distance and Fare")
            fig_path = output_dir / "q3_temperature_effect.png"
            fig.savefig(fig_path, dpi=300)
            plt.close(fig)
            logger.info(f"  ✔ Saved: {fig_path}")


if __name__ == "__main__":
    generate_all_charts()
