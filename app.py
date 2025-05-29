import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
from shiny import App, ui, reactive
from shinywidgets import output_widget, render_widget
import matplotlib.pyplot as plt
import matplotlib
import chatlas
import querychat
import re
from scipy import stats
import numpy as np
from posit import connect
from databricks.sdk import WorkspaceClient
from posit.connect.external.databricks import ConnectStrategy, sql_credentials, databricks_config
from posit.workbench.external.databricks import WorkbenchStrategy
from databricks.sdk.core import ApiClient, databricks_cli
from querychat.datasource import SQLAlchemySource
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

matplotlib.use("Agg")  # Use Agg backend for matplotlib

# Set ggplot style for matplotlib
plt.style.use("ggplot")

# Load data
data_path = Path(os.path.join("data", "stages.csv"))
stages = pd.read_csv(data_path)


with open(Path(__file__).parent / "greeting.md", "r") as f:
    greeting = f.read()
with open(Path(__file__).parent / "data_description.md", "r") as f:
    data_desc = f.read()


# Create UI
app_ui = ui.page_sidebar(
    querychat.sidebar("chat"),
    ui.navset_card_tab(
        ui.nav_panel(
            "Overview",
            ui.layout_columns(
                ui.card(
                    ui.card_header("Most Stage Wins"),
                    output_widget("stages_won"),
                    full_screen=True,
                ),
                ui.card(
                    ui.card_header("Most Stages Completed"),
                    output_widget("stages_ridden"),
                    full_screen=True,
                ),
                col_widths=[6, 6],
            ),
            ui.card(
                ui.card_header("Stage Time Distribution"),
                output_widget("stage_time_distribution_plot"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header("Rider Age Distribution"),
                output_widget("age_distribution_plot"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header("TdF Attrition"),
                output_widget("attrition_plot"),
                full_screen=True,
            ),
        )
    ),
    title=ui.tags.div(
        ui.tags.img(
            src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Tour_de_France_logo.svg/193px-Tour_de_France_logo.svg.png",
            height="30px",
            style="margin-right: 15px;",
        ),
        "Tour de France Analysis",
    ),
)


# Define server
def server(input, output, session):
    # Databricks workspace config
    session_token = session.http_conn.headers.get(
        "Posit-Connect-User-Session-Token"
    )
    
    w = WorkspaceClient(
        config = databricks_config(
            posit_default_strategy = databricks_cli,
            posit_workbench_strategy = WorkbenchStrategy(),
            posit_connect_strategy = ConnectStrategy(user_session_token = session_token)
        )
    )

    def databricks_claude(system_prompt: str) -> chatlas.Chat:
        return chatlas.ChatDatabricks(
            model="databricks-claude-3-7-sonnet",
            system_prompt=system_prompt,
            workspace_client = w
        )

    # Add Databricks SQLAlchemy connection
    access_token    = w.tokens.create().token_value
    server_hostname = w.config.hostname
    http_path       = os.getenv("DATABRICKS_HTTP_PATH")
    catalog         = os.getenv("DATABRICKS_CATALOG")
    schema          = os.getenv("DATABRICKS_SCHEMA")

    querychat_config = querychat.init(
        SQLAlchemySource(
            create_engine(
                url=f"databricks://token:{access_token}@{server_hostname}?" +
                    f"http_path={http_path}&catalog={catalog}&schema={schema}"
            ),
        "stages"),
        greeting=greeting,
        data_description=data_desc,
        create_chat_callback=databricks_claude
    )

    # Initialize querychat server object
    chat = querychat.server("chat", querychat_config)

    # Create reactive data frame from chat
    @reactive.Calc
    def stages_data():
        df = chat["df"]()
        return df

    # Most Stage Wins Plot
    @render_widget
    def stages_won():
        stage_wins = (
            stages_data()[stages_data()["rank"] == 1]
            .groupby("rider")
            .size()
            .reset_index(name="count")
        )
        stage_wins = stage_wins.sort_values("count", ascending=False).head(5)

        fig = px.bar(stage_wins, y="rider", x="count", orientation="h", text="count")

        fig.update_traces(textposition="inside", insidetextanchor="end")
        fig.update_layout(
            xaxis_title=None, yaxis_title=None, yaxis=dict(autorange="reversed")
        )

        return fig

    # Most Stages Ridden Plot
    @render_widget
    def stages_ridden():
        stages_completed = (
            stages_data().groupby("rider").size().reset_index(name="count")
        )
        stages_completed = stages_completed.sort_values("count", ascending=False).head(
            5
        )

        fig = px.bar(
            stages_completed, y="rider", x="count", orientation="h", text="count"
        )

        fig.update_traces(textposition="inside", insidetextanchor="end")
        fig.update_layout(
            xaxis_title=None, yaxis_title=None, yaxis=dict(autorange="reversed")
        )

        return fig

    # Stage Time Distribution Plot
    @render_widget
    def stage_time_distribution_plot():
        filtered_data = stages_data()[~stages_data()["elapsed"].isna()]

        # Remove outliers for each year using IQR method
        clean_data = pd.DataFrame()
        for year in sorted(filtered_data["year"].unique()):
            year_data = filtered_data[filtered_data["year"] == year]

            # Calculate IQR for this year's elapsed times
            Q1 = year_data["elapsed"].quantile(0.25)
            Q3 = year_data["elapsed"].quantile(0.75)
            IQR = Q3 - Q1

            # Filter out rows with elapsed time outside 1.5*IQR
            year_clean = year_data[
                (year_data["elapsed"] >= (Q1 - 1.5 * IQR))
                & (year_data["elapsed"] <= (Q3 + 1.5 * IQR))
            ]

            clean_data = pd.concat([clean_data, year_clean])

        # Group by year
        years = sorted(clean_data["year"].unique())

        # Create figure
        fig = go.Figure()

        # Add a trace for each year
        for year in years:
            year_data = clean_data[clean_data["year"] == year]

            # Create kernel density estimate
            kde = stats.gaussian_kde(year_data["elapsed"])
            x_vals = np.linspace(
                min(clean_data["elapsed"]), max(clean_data["elapsed"]), 1000
            )
            y_vals = kde(x_vals)

            # Add line trace (no fill)
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="lines",
                    name=str(year),
                    line=dict(color="black", width=1),
                    opacity=0.5,
                    showlegend=False,
                )
            )

        # Update layout
        fig.update_layout(
            xaxis_title="Stage Time (seconds)",
            yaxis_title=None,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            xaxis=dict(showticklabels=False),
            yaxis=dict(showticklabels=False),
            height=400,
        )

        return fig

    # Ridger age distiribution
    @render_widget
    def age_distribution_plot():
        unique_riders = stages_data().drop_duplicates(subset=["rider", "year"])[
            ["rider", "year", "age"]
        ]

        # Remove rows with missing age values
        unique_riders = unique_riders[~unique_riders["age"].isna()]

        # Group by year
        years = sorted(unique_riders["year"].unique())

        # Create figure
        fig = go.Figure()

        # Add a trace for each year
        for year in years:
            year_data = unique_riders[unique_riders["year"] == year]

            # Skip years with too few riders for meaningful KDE
            if len(year_data) < 5:
                continue

            # Create kernel density estimate
            kde = stats.gaussian_kde(year_data["age"])
            x_vals = np.linspace(
                min(unique_riders["age"]), max(unique_riders["age"]), 1000
            )
            y_vals = kde(x_vals)

            # Add line trace (no fill)
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode="lines",
                    name=str(year),
                    line=dict(color="black", width=1),
                    opacity=0.5,
                    showlegend=False,
                )
            )

        # Update layout
        fig.update_layout(
            xaxis_title="Rider Age (years)",
            yaxis_title=None,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            xaxis=dict(showticklabels=True),  # Show age values on x-axis
            yaxis=dict(showticklabels=False),
            height=400,
        )

        return fig

    # Attrition Plot
    @render_widget
    def attrition_plot():
        # Create a dataframe with finishers per stage and year
        stage_attrition = (
            stages_data()
            .groupby(["year", "stage_results_id"])
            .agg(num_finishers=("rider", "nunique"))
            .reset_index()
        )

        # Calculate the maximum number of finishers for each year (typically the first stage)
        max_finishers = stage_attrition.groupby("year")["num_finishers"].transform(
            "max"
        )
        stage_attrition["pct_finishers"] = (
            stage_attrition["num_finishers"] / max_finishers
        )

        def extract_stage_components(stage_id):
            # Extract stage number and suffix
            match = re.match(r"stage-([0-9]+)([a-z])?", stage_id)
            if not match:
                return 999, ""

            num = int(match.group(1))
            suffix = match.group(2) if match.group(2) else ""
            return num, suffix

        # Generate a properly ordered list of all stages
        all_stages = sorted(
            stage_attrition["stage_results_id"].unique(),
            key=lambda x: extract_stage_components(x),
        )

        # Create figure
        fig = go.Figure()

        # Get all years
        years = sorted(stage_attrition["year"].unique())

        # For each year, create a line with properly ordered stages
        for year in years:
            # Get data for this year
            year_data = stage_attrition[stage_attrition["year"] == year]

            # Extract stage numbers and suffixes for sorting
            stage_info = [
                (stage, *extract_stage_components(stage))
                for stage in year_data["stage_results_id"]
            ]

            # Sort by stage number, then suffix
            sorted_stages = sorted(stage_info, key=lambda x: (x[1], x[2]))

            # Get the sorted stage IDs
            sorted_stage_ids = [s[0] for s in sorted_stages]

            # Create a DataFrame with properly ordered stages for this year
            ordered_data = (
                year_data.set_index("stage_results_id")
                .loc[sorted_stage_ids]
                .reset_index()
            )

            # Add trace with properly ordered x-axis
            fig.add_trace(
                go.Scatter(
                    x=ordered_data["stage_results_id"],
                    y=ordered_data["pct_finishers"],
                    mode="lines",
                    name=str(year),
                    line=dict(color="black", width=1),
                    opacity=0.3,
                    showlegend=False,
                )
            )

        # Set the x-axis category order explicitly to ensure correct display
        fig.update_layout(
            xaxis=dict(
                categoryorder="array",
                categoryarray=all_stages,
                showticklabels=False,  # Hide labels for clarity
            ),
            yaxis=dict(
                tickformat=",.0%",
                range=[0.7, 1.02],  # Adjust as needed for better visualization
            ),
            xaxis_title="Stage",
            yaxis_title="Percentage of Riders Remaining",
            margin=dict(l=10, r=10, t=10, b=10),
            height=400,
            hovermode="closest",
            showlegend=False,
        )

        return fig


# Create and run the Shiny app
app = App(app_ui, server)
