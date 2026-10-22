from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_FILE = PROJECT_ROOT / "data" / "public" / "todays_sog_board.csv"

st.set_page_config(
    page_title="NHL SOG Model",
    page_icon="🏒",
    layout="wide",
)

st.title("🏒 NHL Shots on Goal Model")
st.caption("Daily NHL player shots-on-goal projections and market analysis.")


@st.cache_data(ttl=300)
def load_data():
    return pd.read_csv(DATA_FILE)


if not DATA_FILE.exists():
    st.error("Today's model data is not available.")
    st.stop()

raw_df = load_data()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_best_prices(df):
    """
    Returns one row per player / side / line using the sportsbook
    offering the best American odds.

    Higher American odds are always better:
    +142 > +135
    -110 > -120
    """
    best = df.copy()

    best["_odds_value"] = pd.to_numeric(
        best["odds"],
        errors="coerce"
    )

    best = (
        best.sort_values("_odds_value", ascending=False)
        .drop_duplicates(
            subset=[
                "game_date",
                "player_name",
                "team",
                "opponent",
                "side",
                "line",
            ],
            keep="first",
        )
        .drop(columns="_odds_value")
        .reset_index(drop=True)
    )

    return best


def format_display(df):
    """
    Formats model data for display without changing the source data.
    """
    display = df.copy()

    display["projected_sog"] = display["projected_sog"].round(2)

    display["model_probability"] = (
        display["model_probability"] * 100
    ).round(1)

    display["book_implied_probability"] = (
        display["book_implied_probability"] * 100
    ).round(1)

    display["edge_vs_no_vig"] = (
        display["edge_vs_no_vig"] * 100
    ).round(1)

    display = display.rename(
        columns={
            "player_name": "Player",
            "team": "Team",
            "opponent": "Opponent",
            "sportsbook": "Sportsbook",
            "side": "Side",
            "line": "Line",
            "odds": "Odds",
            "projected_sog": "Projected SOG",
            "model_probability": "Model Probability %",
            "book_implied_probability": "Book Implied %",
            "edge_vs_no_vig": "Edge vs No-Vig %",
            "expected_roi": "Model ROI %",
        }
    )

    return display


DISPLAY_COLUMNS = [
    "Player",
    "Team",
    "Opponent",
    "Projected SOG",
    "Side",
    "Line",
    "Odds",
    "Sportsbook",
    "Model Probability %",
    "Book Implied %",
    "Edge vs No-Vig %",
    "Model ROI %",
]


# =========================================================
# CREATE BEST-PRICE DATASET
# =========================================================

best_df = get_best_prices(raw_df)


# =========================================================
# TABS
# =========================================================

tab1, tab2 = st.tabs([
    "📈 Today's Best Value",
    "🔎 Player Line Shopping",
])


# =========================================================
# TAB 1 — BEST VALUE BOARD
# =========================================================

with tab1:

    st.subheader("Today's Best SOG Values")

    st.caption(
        "Only the best available sportsbook price is shown "
        "for each player, side, and line."
    )

    # -------------------------
    # FILTERS
    # -------------------------

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    teams = sorted(
        best_df["team"].dropna().unique()
    )

    with filter_col1:
        selected_teams = st.multiselect(
            "Team",
            teams,
            key="value_team",
        )

    with filter_col2:
        side = st.selectbox(
            "Bet Type",
            ["All", "Over", "Under"],
            key="value_side",
        )

    with filter_col3:
        min_roi = st.slider(
            "Minimum Model ROI %",
            min_value=0.0,
            max_value=50.0,
            value=0.0,
            step=1.0,
            key="value_roi",
        )

    filtered = best_df.copy()

    if selected_teams:
        filtered = filtered[
            filtered["team"].isin(selected_teams)
        ]

    if side != "All":
        filtered = filtered[
            filtered["side"].str.lower()
            == side.lower()
        ]

    filtered = filtered[
        filtered["expected_roi"] >= min_roi
    ]

    filtered = filtered.sort_values(
        "expected_roi",
        ascending=False,
    )

    # -------------------------
    # SUMMARY METRICS
    # -------------------------

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Players",
        filtered["player_name"].nunique(),
    )

    col2.metric(
        "Markets",
        len(filtered),
    )

    positive_ev = filtered[
        filtered["expected_roi"] > 0
    ]

    col3.metric(
        "Positive EV",
        len(positive_ev),
    )

    if len(filtered):
        col4.metric(
            "Highest Model ROI",
            f"{filtered['expected_roi'].max():.1f}%",
        )
    else:
        col4.metric(
            "Highest Model ROI",
            "—",
        )

    # -------------------------
    # VALUE TABLE
    # -------------------------

    display = format_display(filtered)

    st.dataframe(
        display[DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
    )


# =========================================================
# TAB 2 — PLAYER LINE SHOPPING
# =========================================================

with tab2:

    st.subheader("Player Line Shopping")

    st.caption(
        "Search for a player to compare every available "
        "sportsbook line and price."
    )

    player_search = st.text_input(
        "Search Player",
        placeholder="e.g. Geekie, Boldy, Celebrini...",
        key="player_search",
    )

    if not player_search:

        st.info(
            "Enter a player's name above to view available lines."
        )

    else:

        player_results = raw_df[
            raw_df["player_name"]
            .str.contains(
                player_search,
                case=False,
                na=False,
            )
        ].copy()

        if player_results.empty:

            st.warning(
                "No matching player was found in today's markets."
            )

        else:

            matched_players = sorted(
                player_results["player_name"].unique()
            )

            if len(matched_players) > 1:

                selected_player = st.selectbox(
                    "Matching Players",
                    matched_players,
                )

                player_results = player_results[
                    player_results["player_name"]
                    == selected_player
                ]

            player_name = (
                player_results["player_name"].iloc[0]
            )

            team = (
                player_results["team"].iloc[0]
            )

            opponent = (
                player_results["opponent"].iloc[0]
            )

            projected_sog = (
                player_results["projected_sog"].iloc[0]
            )

            # -------------------------
            # PLAYER SUMMARY
            # -------------------------

            st.markdown(
                f"### {player_name}"
            )

            info1, info2, info3 = st.columns(3)

            info1.metric(
                "Team",
                team,
            )

            info2.metric(
                "Opponent",
                opponent,
            )

            info3.metric(
                "Projected SOG",
                f"{projected_sog:.2f}",
            )

            # -------------------------
            # SORT ALL AVAILABLE LINES
            # -------------------------

            player_results["_odds_value"] = pd.to_numeric(
                player_results["odds"],
                errors="coerce",
            )

            player_results = player_results.sort_values(
                [
                    "line",
                    "side",
                    "_odds_value",
                ],
                ascending=[
                    True,
                    True,
                    False,
                ],
            )

            player_results = player_results.drop(
                columns="_odds_value"
            )

            display = format_display(
                player_results
            )

            st.markdown("#### Available Sportsbook Lines")

            st.dataframe(
                display[DISPLAY_COLUMNS],
                width="stretch",
                hide_index=True,
            )

            # -------------------------
            # BEST PRICE SUMMARY
            # -------------------------

            best_player_prices = get_best_prices(
                player_results
            )

            best_display = format_display(
                best_player_prices
            )

            best_display = best_display.sort_values(
                ["Line", "Side"]
            )

            st.markdown("#### Best Available Prices")

            st.dataframe(
                best_display[DISPLAY_COLUMNS],
                width="stretch",
                hide_index=True,
            )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Model outputs are statistical estimates and do not "
    "guarantee future results."
)