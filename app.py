import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- Global Settings ----------------
# Global dictionary for initial balances
initial_balances = {"Hans": 0, "Rich": 80, "Ralls": -80}

# Store players in session_state so that new players are recognized immediately.
if 'players' not in st.session_state:
    st.session_state.players = list(initial_balances.keys())

# Set page config (title, icon, layout)
st.set_page_config(page_title="Mini League", page_icon=":horse_racing:", layout="wide")

# ---------------- Custom CSS ----------------
custom_css = """
<style>
/* Default (light mode) styling */
.custom-table {
    border-collapse: collapse;
    width: auto;
    margin-bottom: 1rem;
    background-color: #ffffff;
    color: #333;
}
.custom-table th, .custom-table td {
    border: 1px solid #ccc;
    padding: 8px;
    text-align: center;
    white-space: nowrap;
}
.custom-table th {
    background-color: #eaeaea;
}
.subtotal-row {
    background-color: #fff8c6;
    font-weight: bold;
}
.date-header {
    text-align: left;
    font-weight: bold;
    padding: 4px;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
  .custom-table {
      background-color: #333333;
      color: #ddd;
      border: 1px solid #555;
  }
  .custom-table th, .custom-table td {
      border: 1px solid #555;
  }
  .custom-table th {
      background-color: #444444;
  }
  .subtotal-row {
      background-color: #555555;
      font-weight: bold;
  }
  .date-header {
      background-color: #222222;
      color: #ffffff;
  }
}

/* Buttons */
div.stButton > button {
    background-color: #2C3E50 !important;
    color: #ffffff !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 0.6em 1em !important;
    font-weight: 600 !important;
    cursor: pointer !important;
}
div.stButton > button:hover {
    background-color: #34495E !important;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ---------------- Google Sheets Helper Functions ----------------
def load_data():
    """
    Load contest data from the Google Sheet "MiniLeagueData".
    If the sheet is empty or cannot be loaded, return an empty DataFrame with columns: Date, Track, plus one column per player.
    """
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    try:
        sheet = client.open("MiniLeagueData").sheet1
    except Exception as e:
        st.error("Error opening Google Sheet: " + str(e))
        cols = ["Date", "Track"] + st.session_state.players
        return pd.DataFrame(columns=cols)
    data = sheet.get_all_values()
    if not data:
        cols = ["Date", "Track"] + st.session_state.players
        return pd.DataFrame(columns=cols)
    header = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=header)
    # Ensure all player columns exist and convert them to numeric
    for p in st.session_state.players:
        if p in df.columns:
            df[p] = pd.to_numeric(df[p], errors='coerce').fillna(0)
        else:
            df[p] = 0
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    return df


def save_data(df):
    """
    Save the DataFrame to the Google Sheet "MiniLeagueData".
    """
    scope = ["https://spreadsheets.google.com/feeds",
             "https://www.googleapis.com/auth/spreadsheets",
             "https://www.googleapis.com/auth/drive.file",
             "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    try:
        sheet = client.open("MiniLeagueData").sheet1
    except Exception as e:
        st.error("Error opening Google Sheet: " + str(e))
        return
    # Convert DataFrame to a list of lists; convert all entries to strings.
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
    if val < 0:
        return f"$ ({abs(val)})"
    else:
        return f"$ {val}"


def format_date_long(d):
    return d.strftime("%b %-d")


def build_contest_html_table(date_dt, day_df):
    date_str = format_date_long(date_dt)
    players = st.session_state.players
    html = f"""
    <table class="custom-table">
      <tr><th colspan="{1 + len(players)}" class="date-header">{date_str}</th></tr>
      <tr>
        <th>Track</th>
    """
    for p in players:
        html += f"<th>{p}</th>"
    html += "</tr>"
    day_subtotals = {p: 0 for p in players}
    for idx, row in day_df.iterrows():
        track = row["Track"]
        html += f"<tr><td>{track}</td>"
        for p in players:
            val = row[p]
            day_subtotals[p] += val
            html += f"<td>{format_money(val)}</td>"
        html += "</tr>"
    html += '<tr class="subtotal-row"><td>Sub-Total</td>'
    for p in players:
        html += f"<td>{format_money(day_subtotals[p])}</td>"
    html += "</tr></table>"
    return html


# ---------------- Home Page ----------------
def home_page():
    st.title("Welcome to the Mini League")
    st.markdown("<h3 style='color: darkblue;'>Let the Racing Begin!</h3>", unsafe_allow_html=True)
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    st.markdown(f"<div style='text-align: right; font-size: 18px;'><b>Date:</b> {current_date}</div>",
                unsafe_allow_html=True)

    df = load_data()
    balances = compute_balances(df)
    st.subheader("Current Balances")
    balance_data = [{"Player": p, "Balance": balances[p]} for p in st.session_state.players]
    df_balances = pd.DataFrame(balance_data).reset_index(drop=True)
    st.dataframe(df_balances, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Previous Day’s Contests")
    prev_date_dt = datetime.date.today() - datetime.timedelta(days=1)
    if "Date" in df.columns:
        prev_day_data = df[df["Date"].dt.date == prev_date_dt]
    else:
        prev_day_data = pd.DataFrame()
    if prev_day_data.empty:
        st.write("No data for the previous day.")
    else:
        table_html = build_contest_html_table(prev_date_dt, prev_day_data)
        st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Contests from the Last 7 Days")
    seven_days_ago = datetime.date.today() - datetime.timedelta(days=7)
    if "Date" in df.columns:
        last_week_data = df[df["Date"].dt.date >= seven_days_ago]
    else:
        last_week_data = pd.DataFrame()
    if last_week_data.empty:
        st.write("No contests in the last 7 days.")
    else:
        grouped = last_week_data.groupby(last_week_data["Date"].dt.date)
        for date_val, group_df in grouped:
            table_html = build_contest_html_table(date_val, group_df)
            st.markdown(table_html, unsafe_allow_html=True)


# ---------------- Statistics Page ----------------
def statistics_page():
    st.title("Statistics")
    df = load_data()
    if df.empty:
        st.write("No contest data available to display statistics.")
        return

    st.subheader("Detailed Win/Loss by Track")
    track_groups = df.groupby("Track")
    all_tracks = sorted(track_groups.groups.keys())
    track_stats = {p: {} for p in st.session_state.players}
    for track, group in track_groups:
        for p in st.session_state.players:
            p_rows = group[group[p] != 0]
            wins = (p_rows[p] > 0).sum()
            losses = (p_rows[p] < 0).sum()
            total = wins + losses
            win_pct = (wins / total * 100) if total > 0 else 0
            track_stats[p][track] = (wins, losses, f"{win_pct:.0f}%")
    cols = st.columns(len(st.session_state.players))
    for i, p in enumerate(st.session_state.players):
        with cols[i]:
            st.markdown(f"**{p}**")
            data_rows = []
            for t in all_tracks:
                wins, losses, wpct = track_stats[p].get(t, (0, 0, "0%"))
                data_rows.append({"Track": t, "Win": wins, "Loss": losses, "Win %": wpct})
            df_table = pd.DataFrame(data_rows).reset_index(drop=True)
            st.dataframe(df_table, use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("Contest Participation & Win Ratio")
    contest_stats = []
    for p in st.session_state.players:
        df_player = df[df[p] != 0]
        total_contests = len(df_player)
        wins = (df_player[p] > 0).sum()
        losses = (df_player[p] < 0).sum()
        win_ratio = (wins / total_contests * 100) if total_contests > 0 else 0
        contest_stats.append({
            "Player": p,
            "Total Contests": total_contests,
            "Wins": wins,
            "Losses": losses,
            "Win Ratio": f"{win_ratio:.1f}%"
        })
    df_participation = pd.DataFrame(contest_stats).reset_index(drop=True)
    st.dataframe(df_participation, use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("Detailed Financial Stats")
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
            best_day_str = format_date_long(best_day_dt)
        else:
            best_day_value = 0
            best_day_str = "N/A"
        track_profit = df.groupby("Track")[p].sum()
        best_track = track_profit.idxmax() if not track_profit.empty else "N/A"
        worst_track = track_profit.idxmin() if not track_profit.empty else "N/A"
        financial_stats.append({
            "Player": p,
            "Total Bet": total_bet,
            "Winnings": winnings,
            "Losses": losses_sum,
            "Net Profit": net,
            "Highest Daily Win": best_day_value,
            "Highest Win Day": best_day_str,
            "Best Track": best_track,
            "Worst Track": worst_track
        })
    df_financial = pd.DataFrame(financial_stats).reset_index(drop=True)
    st.dataframe(df_financial, use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("Charts & Graphs")
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

    df_line = df.copy()
    df_line["Date"] = pd.to_datetime(df_line["Date"], errors='coerce')
    daily_player_sums = df_line.groupby(df_line["Date"].dt.date)[st.session_state.players].sum().cumsum()
    if not daily_player_sums.empty:
        daily_player_sums = daily_player_sums.reset_index(drop=False)
        melted = daily_player_sums.melt(id_vars="Date", var_name="Player", value_name="Net")
        fig_line = px.line(
            melted,
            x="Date",
            y="Net",
            color="Player",
            title="Net Profit Over Time (Line Chart)"
        )
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


# ---------------- Data Entry Page ----------------
def data_entry_page():
    st.title("Data Entry")
    st.write("Enter contest data for a specific date, track, and then select participants and the winner.")

    st.subheader("Add New Player")
    with st.form(key="new_player_form"):
        new_player = st.text_input("New Player Name")
        new_balance = st.number_input("Initial Balance", value=0)
        new_player_submitted = st.form_submit_button("Add New Player")
    if new_player_submitted:
        if new_player and new_player not in st.session_state.players:
            initial_balances[new_player] = new_balance
            st.session_state.players.append(new_player)
            st.success(f"Player '{new_player}' added with initial balance $ {new_balance}.")
            df = load_data()
            if new_player not in df.columns:
                df[new_player] = 0
                save_data(df)
            st.experimental_rerun()
        else:
            st.error("Invalid name or player already exists.")

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
        track = st.selectbox("Select Track", ["PARX", "TP", "DD", "GP", "PENN", "AQU", "SA", "LRL", "OP"])
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
            st.success("Contest data submitted successfully!")
            st.write("New Entry:", new_entry)
            st.session_state['participants_confirmed'] = False
            st.session_state['participants'] = []


# ---------------- Main Navigation ----------------
def main():
    page = st.sidebar.radio("Go to", ("Home", "Statistics", "Data Entry"))
    if page == "Home":
        home_page()
    elif page == "Statistics":
        statistics_page()
    elif page == "Data Entry":
        data_entry_page()


if __name__ == "__main__":
    main()
