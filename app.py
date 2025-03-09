import os
import math
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Global configuration for tracks and default bet amount
TRACK_OPTIONS = ["PARX", "TP", "DD", "GP", "PENN", "AQU", "SA", "LRL", "OP", "CT", "MHV"]
DEFAULT_BET_AMOUNT = 40

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

/* Home page header */
.home-header {
    color: #2C3E50;
}

/* Container spacing */
.stApp {
    padding: 2rem;
}

/* Center all dataframes */
[data-testid="stDataFrameContainer"] table {
    margin-left: auto;
    margin-right: auto;
}

/* DataFrame font size */
[data-testid="stDataFrameContainer"] * {
    font-size: 16px !important;
}

/* Buttons */
div.stButton > button {
    background-color: #2C3E50 !important;
    color: #fff !important;
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

/* Contest History container */
.history-grid-container {
    max-width: 85%;
    margin: 0 auto;
    background-color: #fff;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 1rem;
}

/* Main grid: 2 columns x 3 rows (6 days per page) */
.history-grid-table {
    border-collapse: separate;
    border-spacing: 20px;
    width: 100%;
}

/* Each day sub-table, centered */
.history-subtable {
    border-collapse: collapse;
    margin: 0 auto;
    width: auto;
    background-color: #fff;
    color: #333;
}
.history-subtable th, .history-subtable td {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: center;
    font-size: 15px;
    white-space: nowrap;
}
.history-subtable th {
    background-color: #f7f7f7;
}
.history-date-header {
    font-weight: 600;
    text-align: center;
    padding: 6px;
    background-color: #eaeaea;
}
.subtotal-row {
    background-color: #ffe8a6;
    font-weight: 600;
}

/* Pagination container */
.pagination-container {
    text-align: center;
    width: 200px;
    margin: 1rem auto 0;
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
        background-color: #222;
    }
    [data-testid="stSidebar"] h1 {
        color: #ADD8E6;
    }
    .history-grid-container {
        background-color: #333;
        border: 1px solid #555;
    }
    .history-subtable {
        background-color: #444;
        color: #ddd;
    }
    .history-subtable th {
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
initial_balances = {"Hans": 0, "Rich": 80, "Ralls": -80}


def get_initial_balance(player):
    return initial_balances.get(player, 0)


def calculate_result(participants, winner, bet_amount=DEFAULT_BET_AMOUNT):
    result = {p: 0 for p in st.session_state.players}
    if len(participants) == 2:
        profit = bet_amount
    elif len(participants) == 3:
        profit = bet_amount * 2
    else:
        profit = 0
    for p in participants:
        if p == winner:
            result[p] = profit
        else:
            result[p] = -bet_amount
    return result


def compute_balances(df):
    balance = {}
    for p in st.session_state.players:
        balance[p] = get_initial_balance(p) + df[p].sum()
    return balance


def format_money(val):
    return f"$ {val:,.2f}"


# ---------------- Contest History Helper ----------------
def build_day_subtable_html(date_val, day_data):
    day_data = day_data.sort_values(by="Track")
    players = st.session_state.players
    day_subtotals = {p: 0 for p in players}

    html = '<table class="history-subtable">'
    date_str = date_val.strftime("%b %d")
    html += f'<tr><th colspan="{1 + len(players)}" class="history-date-header">{date_str}</th></tr>'
    html += "<tr><th>Track</th>"
    for p in players:
        html += f"<th>{p}</th>"
    html += "</tr>"

    for idx, row in day_data.iterrows():
        track = row["Track"]
        html += f"<tr><td>{track}</td>"
        for p in players:
            val = row[p]
            day_subtotals[p] += val
            # If the player won (positive value), highlight the cell in a muted green (#C8E6C9) with black text
            if val > 0:
                html += f"<td style='background-color: #C8E6C9; color: black;'>{format_money(val)}</td>"
            elif val == 0:
                html += "<td>N</td>"
            else:
                html += f"<td>{format_money(val)}</td>"
        html += "</tr>"

    html += '<tr class="subtotal-row"><td>Sub-Total</td>'
    for p in players:
        html += f"<td>{format_money(day_subtotals[p])}</td>"
    html += "</tr></table>"
    return html


def build_contest_history_table(df, page=1, days_per_page=6):
    df = df.copy()
    df["DateOnly"] = df["Date"].dt.date
    unique_dates = sorted(df["DateOnly"].unique(), reverse=True)
    total_pages = math.ceil(len(unique_dates) / days_per_page)

    start_idx = (page - 1) * days_per_page
    end_idx = start_idx + days_per_page
    dates_to_show = unique_dates[start_idx:end_idx]

    html = '<div class="history-grid-container">'
    html += '<table class="history-grid-table">'
    for row_idx in range(3):
        html += "<tr>"
        for col_idx in range(2):
            day_index = row_idx * 2 + col_idx
            if day_index < len(dates_to_show):
                date_val = dates_to_show[day_index]
                day_data = df[df["DateOnly"] == date_val]
                day_html = build_day_subtable_html(date_val, day_data)
                html += f"<td style='vertical-align: top;'>{day_html}</td>"
            else:
                html += "<td></td>"
        html += "</tr>"
    html += "</table></div>"
    return html, total_pages


def pagination_controls(current_page, total_pages):
    new_page = st.number_input("Page", min_value=1, max_value=total_pages, value=current_page, step=1, key="page_input")
    return new_page


# ---------------- Chart Colors ----------------
PLAYER_COLORS = {
    "Hans": "#93c7fa",
    "Rich": "#2b65c2",
    "Ralls": "#f3afad",
    # "JK": "#a3e8a1"
}

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

    # --- Current Balances Table with Rank ---
    st.subheader("Current Balances")
    balances = compute_balances(df)
    balance_df = pd.DataFrame([{"Player": p, "Balance": balances[p]} for p in st.session_state.players])
    balance_df = balance_df.sort_values("Balance", ascending=False).reset_index(drop=True)
    balance_df.index = balance_df.index + 1
    balance_df.insert(0, "Rank", balance_df.index)
    balance_df["Balance"] = balance_df["Balance"].apply(format_money)
    st.dataframe(balance_df, use_container_width=True)

    # --- Contest History ---
    st.subheader("Contest History")
    df_all = load_data()
    if df_all.empty:
        st.write("No contest history available.")
        return
    df_all["Date"] = pd.to_datetime(df_all["Date"], errors='coerce')
    df_all["DateOnly"] = df_all["Date"].dt.date
    unique_dates = sorted(df_all["DateOnly"].unique(), reverse=True)
    days_per_page = 6
    total_pages = math.ceil(len(unique_dates) / days_per_page)

    if "history_page" not in st.session_state:
        st.session_state.history_page = 1
    current_page = st.session_state.history_page

    table_html, total_pages = build_contest_history_table(df_all, page=current_page, days_per_page=days_per_page)
    st.markdown(table_html, unsafe_allow_html=True)

    new_page = pagination_controls(current_page, total_pages)
    if new_page != current_page:
        st.session_state.history_page = new_page
    st.write(f"Total Pages: {total_pages}")


def statistics_page():
    st.title("Statistics")
    df = load_data()
    if df.empty:
        st.write("No contest data available to display statistics.")
        return

    # 1. Contest Participation & Win Ratio (Ranked by Win Ratio)
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
    df_participation.sort_values(by="NumericWinRatio", ascending=False, inplace=True)
    df_participation.drop(columns="NumericWinRatio", inplace=True)
    df_participation.reset_index(drop=True, inplace=True)
    df_participation.index = df_participation.index + 1
    df_participation.insert(0, "Rank", df_participation.index)
    st.dataframe(df_participation, use_container_width=True)

    # 2. Detailed Financial Stats (Ranked by Net Profit)
    st.subheader("Detailed Financial Stats (Ranked by Net Profit)")
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    financial_stats = []
    for p in st.session_state.players:
        df_player = df[df[p] != 0]
        total_bet = len(df_player) * DEFAULT_BET_AMOUNT
        winnings = df_player[df_player[p] > 0][p].sum()
        losses_sum = abs(df_player[df_player[p] < 0][p].sum())
        net = df[p].sum()
        daily_sums = df.groupby(df["Date"].dt.date)[p].sum()
        if not daily_sums.empty:
            best_day_value = daily_sums.max()
            best_day = daily_sums.idxmax()
            best_day_str = datetime.datetime.combine(best_day, datetime.datetime.min.time()).strftime("%b %-d")
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
    for col in ["Total Bet", "Winnings", "Losses", "Net Profit"]:
        df_financial[col] = df_financial[col].apply(lambda x: f"$ {x:,.2f}")

    def try_money(x):
        try:
            val = float(x)
            return f"$ {val:,.2f}"
        except:
            return str(x)

    df_financial["Highest Daily Win"] = df_financial["Highest Daily Win"].apply(try_money)

    def parse_money(s):
        return float(s.replace("$", "").replace(",", "").strip())

    df_financial["NumericNet"] = df_financial["Net Profit"].apply(parse_money)
    df_financial.sort_values(by="NumericNet", ascending=False, inplace=True)
    df_financial.drop(columns="NumericNet", inplace=True)
    df_financial.reset_index(drop=True, inplace=True)
    df_financial.index = df_financial.index + 1
    df_financial.insert(0, "Rank", df_financial.index)
    st.dataframe(df_financial, use_container_width=True)

    # 3. Per-Player Track Stats (side-by-side, sorted by highest win %)
    st.subheader("Track Stats for Each Player")
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    track_groups = df.groupby("Track")
    all_tracks = sorted(track_groups.groups.keys())
    cols = st.columns(len(st.session_state.players))
    for i, p in enumerate(st.session_state.players):
        with cols[i]:
            st.markdown(f"<div style='text-align:center;'><strong>{p}</strong></div>", unsafe_allow_html=True)
            data_rows = []
            for t in all_tracks:
                group = track_groups.get_group(t)
                p_rows = group[group[p] != 0]
                wins = (p_rows[p] > 0).sum()
                losses = (p_rows[p] < 0).sum()
                total = wins + losses
                win_pct = (wins / total * 100) if total > 0 else 0
                data_rows.append({
                    "Track": t,
                    "Win": wins,
                    "Loss": losses,
                    "Win %": f"{win_pct:.0f}%"
                })
            df_table = pd.DataFrame(data_rows)
            df_table["NumericWinPct"] = df_table["Win %"].str.replace("%", "").astype(float)
            df_table.sort_values(by="NumericWinPct", ascending=False, inplace=True)
            df_table.drop(columns="NumericWinPct", inplace=True)
            df_table.reset_index(drop=True, inplace=True)
            st.dataframe(df_table, use_container_width=True)

    # 4. Charts & Graphs
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("Charts & Graphs")

    # Wins by Track (side-by-side bars). Each bar is the # of wins for that player on that track.
    # We show one bar per (player, track).
    # The color is determined by PLAYER_COLORS.
    # The hover includes Player, track, games played, wins, total bids, money won.
    records = []
    for t in TRACK_OPTIONS:
        for p in st.session_state.players:
            df_subset = df[df["Track"] == t]
            played = (df_subset[p] != 0).sum()
            wins = (df_subset[p] > 0).sum()
            total_bid = played * DEFAULT_BET_AMOUNT
            money_won = df_subset[df_subset[p] > 0][p].sum()
            records.append({
                "Track": t,
                "Player": p,
                "Played": played,
                "Wins": wins,
                "TotalBid": total_bid,
                "MoneyWon": money_won
            })
    bar_df = pd.DataFrame(records)

    fig_bars = go.Figure()
    for p in st.session_state.players:
        df_p = bar_df[bar_df["Player"] == p]
        fig_bars.add_trace(go.Bar(
            x=df_p["Track"],
            y=df_p["Wins"],  # bar height = number of wins
            name=p,
            marker_color=PLAYER_COLORS.get(p, "#888"),
            customdata=df_p[["Played", "TotalBid", "MoneyWon"]],
            hovertemplate=(
                    "Player: " + p +
                    "<br>Track: %{x}" +
                    "<br>Games Played: %{customdata[0]}" +
                    "<br>Wins: %{y}" +
                    "<br>Total Bids: $%{customdata[1]:,.2f}" +
                    "<br>Money Won: $%{customdata[2]:,.2f}<extra></extra>"
            )
        ))
    fig_bars.update_layout(
        barmode="group",
        title="Wins by Track (Side-by-Side Bars)",
        xaxis_title="Track",
        yaxis_title="Number of Wins"
    )
    st.plotly_chart(fig_bars, use_container_width=True)

    # Net Profit Over Time (Line Chart)
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

    # 5. Player Comparison
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("Player Comparison")
    compare_option = st.radio("Compare:", ("Select Two Players", "Compare to Group Average"))
    if compare_option == "Select Two Players":
        player_list = st.session_state.players.copy()
        if len(player_list) < 2:
            st.write("Not enough players to compare.")
            return
        player1 = st.selectbox("Player 1", player_list, key="comp1")
        remaining = [pl for pl in player_list if pl != player1]
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
        overall_net = {pl: df[pl].sum() for pl in st.session_state.players}
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
        st.session_state['track'] = TRACK_OPTIONS[0]
    if 'bet_amount' not in st.session_state:
        st.session_state['bet_amount'] = DEFAULT_BET_AMOUNT

    st.markdown("#### Step 1: Contest Details, Participants & Bet Amount")
    with st.form(key="entry_form_part1"):
        contest_date = st.date_input("Contest Date", datetime.date.today())
        track_options = sorted(TRACK_OPTIONS)
        track = st.selectbox("Select Track", track_options)
        participants = st.multiselect("Select Participants", st.session_state.players)
        bet_amount = st.number_input("Bet Amount", min_value=1, value=DEFAULT_BET_AMOUNT, step=1)
        submitted1 = st.form_submit_button(label="Confirm Participants")

    if submitted1:
        if not participants or len(participants) < 2:
            st.error("Please select at least two participants.")
        else:
            st.session_state['participants_confirmed'] = True
            st.session_state['participants'] = participants
            st.session_state['contest_date'] = contest_date
            st.session_state['track'] = track
            st.session_state['bet_amount'] = bet_amount
            st.success("Participants and Bet Amount confirmed. Now select the winner.")

    if st.session_state.get('participants_confirmed', False):
        st.markdown("#### Step 2: Choose the Winner")
        with st.form(key="entry_form_part2"):
            winner = st.selectbox("Select Winner", st.session_state['participants'])
            submitted2 = st.form_submit_button(label="Submit Contest Data")
        if submitted2:
            result = calculate_result(
                st.session_state['participants'],
                winner,
                bet_amount=st.session_state['bet_amount']
            )
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
