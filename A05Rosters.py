# %%
from U01Imports import *
from U02Functions import *
from U04Datasets import *


# %%
# Creates dataframe of players and their spot in the batting order
def order(gamePk, teamId, date, team="away"):
    list_of_lists = []
    players = statsapi.get("game", {"gamePk": gamePk})['liveData']['boxscore']['teams'][team]['players']
    for player in players:
        id = players[player]['person']['id']
        fullName = players[player]['person']['fullName']
        position = players[player]['position']['name']
        status = players[player]['status']['description']
        try:
            order = statsapi.get("game", {"gamePk": gamePk})['liveData']['boxscore']['teams'][team]['players'][player]['battingOrder']
        except:
            order = np.nan
    
        return_list = [id, fullName, position, status, order]
        list_of_lists.append(return_list)
    
    # Create dataframe
    df = pd.DataFrame(list_of_lists, columns=['id', 'fullName', 'position', 'status', 'order'])
        
    # Game ID
    df['gamePk'] = gamePk
    # Date
    df['date'] = date
    # Team ID #
    df['teamId'] = teamId

    
    return df

# %%
# Writes orders to CSV
def orders(team_map, game_df, row):
    ### Extract info
    # Date
    date = game_df.loc[row]['date']
    # Game ID
    game_id = game_df.loc[row]['game_id']
    # Team IDs
    away_id = game_df.loc[row]['away_id']
    home_id = game_df.loc[row]['home_id']
    
    # Create path
    os.makedirs(os.path.join(baseball_path, "A05. Rosters", "1. Batting Orders", f"Batting Orders {date}"), exist_ok=True)
    time.sleep(1)

    # Loop over teams in matchup
    for team_id in [away_id, home_id]:
        if team_id == away_id:
            team = "away"
        else:
            team = "home"
        # Scrape away team batting order
        order_df = order(game_id, team_id, date, team)
        # Extract team name
        team_name = team_map.loc[team_map['teamId'] == team_id, 'BBREFTEAM'].values[0]
        # To csv
        order_df.to_csv(os.path.join(baseball_path, "A05. Rosters", "1. Batting Orders", f"Batting Orders {date}", f"Batting Order {team_name} {game_id}.csv"), index=False, encoding='iso-8859-1')


# %%
# Creates a roster
def roster(teamId, date, rosterType):
    # Reformat date to fit function
    date = str(int(date))
    date_dash = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    
    # Get roster (rosterType options include active, 40Man, depthChart, fullSeason, allTime, and more)
    roster = statsapi.get("team_roster", {"teamId": teamId, "rosterType": rosterType, "date": date_dash, "hydrate": "person"})['roster']

    # Initialize empty lists to store the extracted values
    id_list = []
    full_name_list = []
    first_name_list = []
    last_name_list = []
    position_list = []
    bat_side_list = []
    pitch_hand_list = []

    # Iterate over the roster data
    for player in roster:
        # Extract the values using .get() method and fill missing values with "Missing"
        id_list.append(player['person'].get('id', 'Missing'))
        full_name_list.append(player['person'].get('fullName', 'Missing'))
        first_name_list.append(player['person'].get('firstName', 'Missing'))
        last_name_list.append(player['person'].get('lastName', 'Missing'))
        position_list.append(player['position'].get('name', 'Missing'))
        bat_side_list.append(player['person'].get('batSide', {}).get('description', 'Missing'))
        pitch_hand_list.append(player['person'].get('pitchHand', {}).get('description', 'Missing'))

    # Create the dataframe
    df = pd.DataFrame({
        'id': id_list,
        'fullName': full_name_list,
        'firstName': first_name_list,
        'lastName': last_name_list,
        'position': position_list,
        'batSide': bat_side_list,
        'pitchHand': pitch_hand_list
    })

    date = date.replace("-", "")
    
    # Date
    df['date'] = date
    # Team ID #
    df['teamId'] = teamId


    return df


# %%
# Writes rosters to CSV
def rosters(team_map, game_df, row):
    ### Extract info
    # Date
    date = game_df.loc[row]['date']
    # Game ID
    game_id = game_df.loc[row]['game_id']
    # Team IDs
    away_id = game_df.loc[row]['away_id']
    home_id = game_df.loc[row]['home_id']
    
    # Create path
    os.makedirs(os.path.join(baseball_path, "A05. Rosters", "2. Rosters", f"Rosters {date}"), exist_ok=True)
    time.sleep(1)
    
    # Loop over teams in matchup
    for team_id in [away_id, home_id]:
        if team_id == away_id:
            team = "away"
        else:
            team = "home"
    
        # Extract team name
        bbrefteam = team_map.loc[team_map['teamId'] == team_id, 'BBREFTEAM'].values[0]
    
        # Scrape rosters
        roster_df = roster(team_id, date, "40Man")
        roster_df.drop_duplicates('id', inplace=True)
        # To CSV
        roster_df.to_csv(os.path.join(baseball_path, "A05. Rosters", "2. Rosters", f"Rosters {date}", f"Roster {bbrefteam} {date}.csv"), index=False, encoding='iso-8859-1')


# %%
# Scrapes Rotogrinders projected lineups
def scrape_rotogrinders_lineups():
    url = 'https://rotogrinders.com/lineups/mlb'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # --- Step 1: Get all team abbreviations in order ---
    team_abbrs = [tag["data-abbr"] for tag in soup.select("span.team-nameplate-title") if "data-abbr" in tag.attrs]
    
    all_players = []
    
    # --- Step 2: Grab all lineup cards ---
    lineup_cards = soup.select("div.lineup-card")
    
    # --- Step 3: Track how many times each team has appeared ---
    team_counts = {}
    
    for team_code, card in zip(team_abbrs, lineup_cards):
        # Assign game number
        team_counts[team_code] = team_counts.get(team_code, 0) + 1
        game_num = team_counts[team_code]

        # Check if lineup is confirmed
        confirmed = "N" if card.select_one("div.lineup-card-unconfirmed") else "Y"
    
        # --- Starting pitcher ---
        sp_tag = card.select_one(".lineup-card-pitcher .player-nameplate-name")
        sp_stats = card.select_one(".lineup-card-pitcher .player-nameplate-stats") if sp_tag else None
    
        if sp_tag:
            salary = sp_stats.select_one(".player-nameplate-salary").get_text(strip=True) if sp_stats else None
            spans = sp_stats.find_all("span", class_="small muted bold") if sp_stats else []
            proj = spans[0].get_text(strip=True) if len(spans) > 0 else None
            own = spans[1].get_text(strip=True) if len(spans) > 1 else None
    
            all_players.append({
                "TeamCode": team_code,
                "game_number": game_num,
                "batting_order": None,  # SP has no batting order
                "Name": sp_tag.get_text(strip=True),
                "Position": "SP",
                "Salary": salary,
                "Projection": proj,
                "Ownership": own,
                "confirmed": confirmed
            })
    
        # --- Hitters ---
        for li in card.select("ul.lineup-card-players li.lineup-card-player"):
            batting_order_tag = li.select_one("span.small")
            batting_order = int(batting_order_tag.get_text(strip=True)) if batting_order_tag else None
    
            name_tag = li.select_one(".player-nameplate-name")
            stats = li.select_one(".player-nameplate-stats")
    
            name = name_tag.get_text(strip=True) if name_tag else None
            pos_tag = stats.find("span", {"class": "small muted"}) if stats else None
            pos = pos_tag.get_text(strip=True) if pos_tag else None
            salary = stats.select_one(".player-nameplate-salary").get_text(strip=True) if stats else None
    
            spans = stats.find_all("span", class_="small muted bold") if stats else []
            proj = spans[0].get_text(strip=True) if len(spans) > 0 else None
            own = spans[1].get_text(strip=True) if len(spans) > 1 else None
    
            all_players.append({
                "TeamCode": team_code,
                "game_number": game_num,
                "batting_order": batting_order,
                "Name": name,
                "Position": pos,
                "Salary": salary,
                "Projection": proj,
                "Ownership": own,
                "confirmed": confirmed
            })
    
    df = pd.DataFrame(all_players)
    
    
    return df


# %%
__all__ = [name for name in globals() if not name.startswith("_")]