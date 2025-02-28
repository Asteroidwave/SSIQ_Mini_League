import os
import math
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Mini League", page_icon=":horse_racing:", layout="wide")

# ---------------- Global Settings ----------------
initial_balances = {"Hans": 0, "Rich": 80, "Ralls": -80}
if 'players' not in st.session_state:
    st.session_state.players = list(initial_balances.keys())

# ---------------- Custom CSS ----------------
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap');

body {
    font-family: 'Montserrat', sans-serif;
    background: linear-gradient(135deg, #f0f2f6, #ffffff);
    color: #333;
    margin: 0;
    padding: 0;
}

/* Headers */
h1, h2, h3, h4 {
    font-weight: 600;
}

/* Home page header - Let the Racing Begin! */
.home-header {
    color: #2C3E50;
}

/* Container spacing */
.stApp {
    padding: 2rem;
}

/* DataFrame font size */
[data-testid="stDataFrameContainer"] * {
    font-size: 16px !important;
}

/* Buttons */
div.stButton > button {
    background-color: #2C3E50 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 0.8em 1.2em !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    margin-bottom: 0.8em;
    transition: background-color 0.2s ease;
}
div.stButton > button:hover {
    background-color: #34495E !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #f0f0f0;
    padding: 1rem;
}
[data-testid="stSidebar"] h1 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
    color: #2C3E50;
}

/* Contest History single table container */
.history-table-container {
    max-width: 25%;
    margin: 0 auto;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    border: 1px solid #ccc;
    padding: 1rem;
    background-color: #fff;
}

/* Single table with days as sub-sections */
.history-table {
    width: 100%;
    border-collapse: collapse;
}
.history-table td, .history-table th {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: center;
    font-size: 15px;
    white-space: nowrap;
}
.history-table th {
    background-color: #f7f7f7;
}
.history-date-header {
    font-weight: 600;
    text-align: left;
    padding: 6px;
    background-color: #eaeaea;
}
.subtotal-row {
    background-color: #ffe8a6;
    font-weight: 600;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
    body {
        background: linear-gradient(135deg, #1a1a1a, #333);
        color: #ccc;
    }
    .home-header {
        color: #ADD8E6;
    }
    [data-testid="stSidebar"] {
        background-color: #222222;
    }
    [data-testid="stSidebar"] h1 {
        color: #ADD8E6;
    }
    .history-table-container {
        background-color: #333;
        border: 1px solid #555;
    }
    .history-table {
        background-color: #444;
        color: #ddd;
    }
    .history-table th {
        background-color: #555;
    }
    .history-date-header {
        background-color: #555;
    }
    .subtotal-row {
        background-color: #666;
    }
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ---------------- Google Sheets Helper Functions ----------------
def get_gsheets_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = st.secrets["gcp"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client


def load_data():
    client = get_gsheets_client()
    try:
        sheet = client.open("MiniLeagueData").sheet1
    except Exception as e:
        st.error(f"Error opening Google Sheet: {e}")
        cols = ["Date", "Track"] + st.session_state.players
        return pd.DataFrame(columns=cols)
    data = sheet.get_all_values()
    if not data:
        cols = ["Date", "Track"] + st.session_state.players
        return pd.DataFrame(columns=cols)
    header = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=header)
    for p in st.session_state.players:
        if p in df.columns:
            df[p] = pd.to_numeric(df[p], errors='coerce').fillna(0)
        else:
            df[p] = 0
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    return df


def save_data(df):
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.strftime("%Y-%m-%d")
    client = get_gsheets_client()
    try:
        sheet = client.open("MiniLeagueData").sheet1
    except Exception as e:
        st.error(f"Error opening Google Sheet: {e}")
        return
    data = [df.columns.tolist()] + df.astype(str).values.tolist()
    sheet.clear()
    sheet.update("A1", data)
    st.success("Data updated in Google Sheets!")


# ---------------- Data Handling Functions ----------------
def get_initial_balance(player):
    return initial_balances.get(player, 0)


def calculate_result(participants, winner):
    result = {p: 0 for p in st.session_state.players}
    if len(participants) == 2:
        profit = 40
    elif len(participants) == 3:
        profit = 80
    else:
        profit = 0
    for p in participants:
        if p == winner:
            result[p] = profit
        else:
            result[p] = -40
    return result


def compute_balances(df):
    balance = {}
    for p in st.session_state.players:
        balance[p] = get_initial_balance(p) + df[p].sum()
    return balance


def format_money(val):
    return f"$ {val:,.2f}"


def format_date_long(d):
    return d.strftime("%b %-d")


def build_history_table_html(df, page=1, days_per_page=5):
    """
    Build a single HTML table that includes all days in df, but only
    the subset for the current page. Each day is a 'section' within the table.
    """
    df["DateOnly"] = df["Date"].dt.date
    unique_dates = sorted(df["DateOnly"].unique(), reverse=True)
    total_pages = math.ceil(len(unique_dates) / days_per_page)

    start_idx = (page - 1) * days_per_page
    end_idx = start_idx + days_per_page
    dates_to_show = unique_dates[start_idx:end_idx]

    # Build one big table
    html = '<div class="history-table-container">'
    html += '<table class="history-table">'

    for date_val in dates_to_show:
        day_data = df[df["DateOnly"] == date_val].copy()

        # Build the day header row
        html += f'<tr><th colspan="{2 + len(st.session_state.players)}" class="history-date-header">{date_val.strftime("%b %d")}</th></tr>'

        # Build the column header row
        html += "<tr><th>Track</th>"
        for p in st.session_state.players:
            html += f"<th>{p}</th>"
        html += "</tr>"

        # Fill table rows
        # If a participant has 0, that means they didn't play => display "N"
        # Otherwise format as money
        day_data.sort_values(by="Track", inplace=True)
        day_subtotals = {p: 0 for p in st.session_state.players}

        for idx, row in day_data.iterrows():
            track = row["Track"]
            html += f"<tr><td>{track}</td>"
            for p in st.session_state.players:
                val = row[p]
                day_subtotals[p] += val
                if val == 0:
                    # Means they didn't participate => "N"
                    # but if val is actually 0 from a 2-person scenario, it's ambiguous
                    # We'll assume 2-person scenario => -40 or +40 => never 0
                    # So 0 means no entry
                    html += "<td>N</td>"
                else:
                    html += f"<td>{format_money(val)}</td>"
            html += "</tr>"

        # Sub-total row
        html += f'<tr class="subtotal-row"><td>Sub-Total</td>'
        for p in st.session_state.players:
            html += f"<td>{format_money(day_subtotals[p])}</td>"
        html += "</tr>"

    html += "</table></div>"
    return html, total_pages


# ---------------- Navigation (Vertical Sidebar Buttons) ----------------
st.sidebar.title("Navigation")
if st.sidebar.button("Home"):
    st.session_state.current_page = "Home"
if st.sidebar.button("Statistics"):
    st.session_state.current_page = "Statistics"
if st.sidebar.button("Data Entry"):
    st.session_state.current_page = "Data Entry"

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"


# ---------------- Page Functions ----------------
def home_page():
    st.title("Welcome to the Mini League")
    st.markdown('<h3 class="home-header">Let the Racing Begin!</h3>', unsafe_allow_html=True)

    current_date = datetime.date.today().strftime("%Y-%m-%d")
    st.markdown(f"<div style='text-align: right; font-size: 18px;'><b>Date:</b> {current_date}</div>",
                unsafe_allow_html=True)

    df = load_data()

    # --- Current Balances Table with Rank (Remove blank column) ---
    st.subheader("Current Balances")
    balances = compute_balances(df)
    balance_df = pd.DataFrame([
        {"Player": p, "Balance": balances[p]}
        for p in st.session_state.players
    ])
    # Sort descending by Balance
    balance_df = balance_df.sort_values("Balance", ascending=False).reset_index(drop=True)
    # Insert rank column (1-based)
    balance_df.index = balance_df.index + 1
    balance_df.insert(0, "Rank", balance_df.index)
    # Format currency
    balance_df["Balance"] = balance_df["Balance"].apply(format_money)
    st.dataframe(balance_df, use_container_width=True)

    st.subheader("Contest History (Paginated)")
    df_all = load_data()
    if df_all.empty:
        st.write("No contest history available.")
        return
    # Pagination
    if "history_page" not in st.session_state:
        st.session_state.history_page = 1
    page = st.number_input("Page", min_value=1, value=st.session_state.history_page, step=1)

    table_html, total_pages = build_history_table_html(df_all, page=page, days_per_page=5)
    st.markdown(table_html, unsafe_allow_html=True)

    # If user changes the page number, store it
    if page != st.session_state.history_page:
        st.session_state.history_page = page

    st.write(f"Total Pages: {total_pages}")


def statistics_page():
    st.title("Statistics")
    df = load_data()
    if df.empty:
        st.write("No contest data available to display statistics.")
        return

    # 1. Detailed Win/Loss by Track (ranked by highest win %)
    st.subheader("Detailed Win/Loss by Track (Ranked by Win %)")
    track_groups = df.groupby("Track")
    all_tracks = sorted(track_groups.groups.keys())

    # We'll store totalWins, totalLoss, totalContests, winPct for each player
    data_rows = []
    for p in st.session_state.players:
        # Sum up total wins and losses across all tracks
        total_wins = 0
        total_losses = 0
        for track in all_tracks:
            group = track_groups.get_group(track)
            p_rows = group[group[p] != 0]
            wins = (p_rows[p] > 0).sum()
            losses = (p_rows[p] < 0).sum()
            total_wins += wins
            total_losses += losses
        total_contests = total_wins + total_losses
        win_pct = (total_wins / total_contests * 100) if total_contests > 0 else 0
        data_rows.append({"Player": p, "Wins": total_wins, "Losses": total_losses, "Win %": f"{win_pct:.0f}%"})
    df_winloss = pd.DataFrame(data_rows)
    # Sort by highest Win % (need numeric sort)
    df_winloss["NumericWinPct"] = df_winloss["Win %"].str.replace("%", "").astype(float)
    df_winloss = df_winloss.sort_values(by="NumericWinPct", ascending=False).reset_index(drop=True)
    df_winloss.index = df_winloss.index + 1
    df_winloss.insert(0, "Rank", df_winloss.index)
    df_winloss.drop(columns="NumericWinPct", inplace=True)
    st.dataframe(df_winloss, use_container_width=True)

    # 2. Contest Participation & Win Ratio (ranked by highest ratio)
    st.subheader("Contest Participation & Win Ratio (Ranked by Win Ratio)")
    data_rows2 = []
    for p in st.session_state.players:
        df_player = df[df[p] != 0]
        total_contests = len(df_player)
        wins = (df_player[p] > 0).sum()
        losses = (df_player[p] < 0).sum()
        win_ratio = (wins / total_contests * 100) if total_contests > 0 else 0
        data_rows2.append({
            "Player": p,
            "Total Contests": total_contests,
            "Wins": wins,
            "Losses": losses,
            "Win Ratio": f"{win_ratio:.1f}%"
        })
    df_participation = pd.DataFrame(data_rows2)
    df_participation["NumericWinRatio"] = df_participation["Win Ratio"].str.replace("%", "").astype(float)
    df_participation = df_participation.sort_values(by="NumericWinRatio", ascending=False).reset_index(drop=True)
    df_participation.index = df_participation.index + 1
    df_participation.insert(0, "Rank", df_participation.index)
    df_participation.drop(columns="NumericWinRatio", inplace=True)
    st.dataframe(df_participation, use_container_width=True)

    # 3. Detailed Financial Stats
    st.subheader("Detailed Financial Stats (Ranked by Net Profit)")
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    financial_stats = []
    for p in st.session_state.players:
        df_player = df[df[p] != 0]
        total_bet = len(df_player) * 40
        winnings = df_player[df_player[p] > 0][p].sum()
        losses_sum = abs(df_player[df_player[p] < 0][p].sum())
        net = df[p].sum()
        daily_sums = df.groupby(df["Date"].dt.date)[p].sum()
        if not daily_sums.empty:
            best_day_value = daily_sums.max()
            best_day = daily_sums.idxmax()
            best_day_dt = datetime.datetime.combine(best_day, datetime.datetime.min.time())
            best_day_str = best_day_dt.strftime("%b %-d")
        else:
            best_day_value = 0
            best_day_str = "N/A"
        financial_stats.append({
            "Player": p,
            "Total Bet": total_bet,
            "Winnings": winnings,
            "Losses": losses_sum,
            "Net Profit": net,
            "Highest Daily Win": best_day_value,
            "Highest Win Day": best_day_str
        })
    df_financial = pd.DataFrame(financial_stats)
    # Format currency columns
    for col in ["Total Bet", "Winnings", "Losses", "Net Profit", "Highest Daily Win"]:
        if col == "Highest Daily Win":  # numeric, but for day usage we keep
            df_financial[col] = df_financial[col].apply(lambda x: format_money(x) if isinstance(x, (int, float)) else x)
        else:
            df_financial[col] = df_financial[col].apply(format_money)

    # Sort by Net Profit descending
    # Need to parse Net Profit from string to float
    def parse_money(s):
        # s is like '$ 1,234.00'
        return float(s.replace("$", "").replace(",", "").strip())

    df_financial["NumericNet"] = df_financial["Net Profit"].apply(parse_money)
    df_financial.sort_values(by="NumericNet", ascending=False, inplace=True)
    df_financial.drop(columns="NumericNet", inplace=True)
    df_financial.reset_index(drop=True, inplace=True)
    df_financial.index = df_financial.index + 1
    df_financial.insert(0, "Rank", df_financial.index)
    st.dataframe(df_financial, use_container_width=True)

    # 4. Charts & Graphs
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("Charts & Graphs")
    # Wins by Track
    win_data = []
    for idx, row in df.iterrows():
        for p in st.session_state.players:
            if row[p] > 0:
                win_data.append({"Track": row["Track"], "Player": p})
    if win_data:
        win_df = pd.DataFrame(win_data)
        win_count = win_df.groupby(["Track", "Player"]).size().reset_index(name="Wins")
        fig_bar = px.bar(
            win_count,
            x="Track",
            y="Wins",
            color="Player",
            barmode="group",
            title="Wins by Track (Interactive Bar Chart)"
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.write("No wins recorded yet for bar chart.")

    # Net Profit Over Time
    df_line = df.copy()
    df_line["Date"] = pd.to_datetime(df_line["Date"], errors='coerce')
    df_line["Date"] = df_line["Date"].dt.date
    daily_player_sums = df_line.groupby("Date")[st.session_state.players].sum().cumsum()
    if not daily_player_sums.empty:
        daily_player_sums = daily_player_sums.reset_index()
        melted = daily_player_sums.melt(id_vars="Date", var_name="Player", value_name="Net")
        fig_line = px.line(
            melted,
            x="Date",
            y="Net",
            color="Player",
            title="Net Profit Over Time (Line Chart)"
        )
        fig_line.update_xaxes(tickformat="%b %d")
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.write("No data for line chart yet.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("Player Comparison")
    compare_option = st.radio("Compare:", ("Select Two Players", "Compare to Group Average"))
    if compare_option == "Select Two Players":
        player_list = st.session_state.players.copy()
        if len(player_list) < 2:
            st.write("Not enough players to compare.")
            return
        player1 = st.selectbox("Player 1", player_list, key="comp1")
        remaining = [p for p in player_list if p != player1]
        player2 = st.selectbox("Player 2", remaining, key="comp2")
        if player1 and player2:
            comp_data = [
                {"Player": player1, "Total Contests": len(df[df[player1] != 0]), "Net Profit": df[player1].sum()},
                {"Player": player2, "Total Contests": len(df[df[player2] != 0]), "Net Profit": df[player2].sum()}
            ]
            df_comp = pd.DataFrame(comp_data).reset_index(drop=True)
            st.dataframe(df_comp, use_container_width=True)
    else:
        if len(st.session_state.players) == 0:
            st.write("No players available.")
            return
        player = st.selectbox("Select Player", st.session_state.players, key="comp_single")
        overall_net = {p: df[p].sum() for p in st.session_state.players}
        group_avg = sum(overall_net.values()) / len(st.session_state.players)
        st.write(f"Overall Group Average Net Profit: $ {group_avg:.2f}")
        st.write(f"{player}'s Net Profit: $ {df[player].sum():.2f}")


def data_entry_page():
    st.title("Data Entry")
    st.write("Enter contest data for a specific date, track, and then select participants and the winner.")

    st.subheader("Enter Contest Details")
    if 'participants_confirmed' not in st.session_state:
        st.session_state['participants_confirmed'] = False
    if 'participants' not in st.session_state:
        st.session_state['participants'] = []
    if 'contest_date' not in st.session_state:
        st.session_state['contest_date'] = datetime.date.today()
    if 'track' not in st.session_state:
        st.session_state['track'] = "PARX"

    st.markdown("#### Step 1: Contest Details & Participants")
    with st.form(key="entry_form_part1"):
        contest_date = st.date_input("Contest Date", datetime.date.today())
        track_options = sorted(["PARX", "TP", "DD", "GP", "PENN", "AQU", "SA", "LRL", "OP"])
        track = st.selectbox("Select Track", track_options)
        participants = st.multiselect("Select Participants", st.session_state.players)
        submitted1 = st.form_submit_button(label="Confirm Participants")

    if submitted1:
        if not participants or len(participants) < 2:
            st.error("Please select at least two participants.")
        else:
            st.session_state['participants_confirmed'] = True
            st.session_state['participants'] = participants
            st.session_state['contest_date'] = contest_date
            st.session_state['track'] = track
            st.success("Participants confirmed. Now select the winner.")

    if st.session_state.get('participants_confirmed', False):
        st.markdown("#### Step 2: Choose the Winner")
        with st.form(key="entry_form_part2"):
            winner = st.selectbox("Select Winner", st.session_state['participants'])
            submitted2 = st.form_submit_button(label="Submit Contest Data")
        if submitted2:
            result = calculate_result(st.session_state['participants'], winner)
            new_entry = {
                "Date": st.session_state['contest_date'].strftime("%Y-%m-%d"),
                "Track": st.session_state['track'],
            }
            for p in st.session_state.players:
                new_entry[p] = result.get(p, 0)
            df = load_data()
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            save_data(df)
            st.success("Data updated successfully!")
            st.write("New Entry:", new_entry)
            st.session_state['participants_confirmed'] = False


def main():
    page = st.session_state.get("current_page", "Home")
    if page == "Home":
        home_page()
    elif page == "Statistics":
        statistics_page()
    elif page == "Data Entry":
        data_entry_page()


if __name__ == "__main__":
    main()
