from U01Imports import *

# %% 
# Determine HBP counts for batters and pitchers
def extract_hbp_counts(box_df):
    hbp_row = box_df[box_df['label'] == 'HBP']

    if hbp_row.empty:
        return pd.DataFrame(columns=['name', 'hbp']), pd.DataFrame(columns=['name', 'hbp'])

    hbp_values = hbp_row['value'].iloc[0]
    hbp_matches = re.findall(r'([^;(]+?)\s*\(by\s+([^)]+)\)', hbp_values)

    batter_names = []
    pitcher_names = []
    for match in hbp_matches:
        batter_names.append(match[0].strip())
        pitcher_names.append(match[1].strip())

    batter_hbp_count = pd.DataFrame({'name': batter_names})['name'].value_counts().reset_index()
    batter_hbp_count.columns = ['name', 'hbp']

    pitcher_hbp_count = pd.DataFrame({'name': pitcher_names})['name'].value_counts().reset_index()
    pitcher_hbp_count.columns = ['name', 'hbp']

    return batter_hbp_count, pitcher_hbp_count


# %%
# Determine PA counts for pitchers
def extract_pa_counts(box_df):
    # Filter rows where label is "Batters faced"
    pa_row = box_df[box_df['label'] == 'Batters faced']
    
    
    if pa_row.empty:
        return pd.DataFrame(columns=['name', 'count']), pd.DataFrame(columns=['name', 'count'])

    # Extract pitcher names and pa
    pa_values = pa_row['value'].iloc[0]

    pa_names = re.findall(r'\b[A-Za-zÀ-ÿ,. ]+(?= \d+)', pa_values)
    pa_matches = re.findall(r'\d+', pa_values)
    
    pitcher_pa_count = pd.DataFrame({'name': pa_names, 'pa': pa_matches})

    
    return pitcher_pa_count


# %%
# Create results DataFrame for batters
def create_batters(json, batter_hbp_df, team='away'):
    # Convert json to DataFrame
    batters_df = pd.DataFrame(json[f'{team}Batters'])

    # Drop first row (it's useless)
    batters_df = batters_df.drop(batters_df.index[0]).reset_index(drop=True)

    # Convert to numeric, where possible
    batters_df = batters_df.apply(pd.to_numeric, errors='ignore')

    # Add in HBP info
    try:
        batters_df = batters_df.merge(batter_hbp_df, on='name', how='left')
        batters_df['hbp'].fillna(0, inplace=True)
    except:
        batters_df['hbp'] = 0
    batters_df['hbp'] = batters_df['hbp'].astype('int')
    
    # Calculate fantasy points
    batters_df['fp'] = batters_df['h'] * 3 + batters_df['doubles'] * 2 + batters_df['triples'] * 5 + batters_df['hr'] * 7 + batters_df['rbi'] * 2 + batters_df['r'] * 2 + batters_df['bb'] * 2 + batters_df['hbp'] * 2 + batters_df['sb'] * 5

    # Keep relevant columns
    batters_df = batters_df[['name', 'personId', 'substitution', 'battingOrder', 'ab', 'h', 'doubles', 'triples', 'hr', 'bb', 'hbp', 'rbi', 'r', 'sb', 'fp']]

    
    return batters_df


# %%
# Create results DataFrame for pitchers 
def create_pitchers(json, pitcher_hbp_df, pitcher_pa_df, team='away'):
    # Convert json to DataFrame
    pitchers_df = pd.DataFrame(json[f'{team}Pitchers'])

    # Drop first row (it's useless)
    pitchers_df = pitchers_df.drop(pitchers_df.index[0]).reset_index(drop=True)

    # Convert to numeric, where possible
    pitchers_df = pitchers_df.apply(pd.to_numeric, errors='ignore')

    # Assign wins and losses
    pitchers_df['w'] = pitchers_df['note'].str.contains('W').astype(int)
    pitchers_df['l'] = pitchers_df['note'].str.contains('L').astype(int)

    # Add in HBP info
    try:
        pitchers_df = pitchers_df.merge(pitcher_hbp_df, on='name', how='left')
        pitchers_df['hbp'].fillna(0, inplace=True)
    except:
        pitchers_df['hbp'] = 0
    pitchers_df['hbp'] = pitchers_df['hbp'].astype('int')

    # Add in PA info
    pitchers_df = pitchers_df.merge(pitcher_pa_df, on='name', how='left')
    

    # Calculate outs
    pitchers_df['outs'] = pitchers_df['ip'].astype(float).apply(lambda x: int(x) * 3 + round((x % 1) * 10))

    # Create cg column
    pitchers_df['cg'] = 0
    if len(pitchers_df) == 1:
        pitchers_df['cg'] = 1
    
    # Create cgso column
    pitchers_df['cgso'] = 0
    if len(pitchers_df) == 1 and pitchers_df['r'].iloc[0] == 0:
        pitchers_df['cgso'] = 1

    # Create nh column
    pitchers_df['nh'] = 0
    if len(pitchers_df) == 1 and pitchers_df['h'].iloc[0] == 0:
        pitchers_df['nh'] = 1

    # Calculate fantasy points
    pitchers_df['fp'] = pitchers_df['outs'] * 0.75 + pitchers_df['k'] * 2 + pitchers_df['w'] * 4 + pitchers_df['er'] * -2 + pitchers_df['h'] * -0.6 + pitchers_df['bb'] * -0.6 + pitchers_df['hbp'] * -0.6 + pitchers_df['cg'] * 2.5 + pitchers_df['cgso'] * 2.5 + pitchers_df['nh'] * 5

    # Identify starting pitchers
    pitchers_df.reset_index(inplace=True)
    pitchers_df['starter'] = (pitchers_df['index'] == 0).astype('int')

    # Keep relevant columns
    pitchers_df = pitchers_df[['name', 'personId', 'starter', 'ip', 'pa', 'outs', 'h', 'r', 'er', 'bb', 'k', 'hr', 'hbp', 'w', 'l', 'cg', 'cgso', 'nh', 'fp']]


    return pitchers_df


# %%
# Create results dataframes for a given game
def create_results_dfs(gamePk):
    # Read in json
    json = statsapi.boxscore_data(gamePk, timecode=None)

    # Read in box score (for HBP info)
    box_df = pd.DataFrame(json['gameBoxInfo'])

    # Extract HBP info
    batter_hbp_df, pitcher_hbp_df = extract_hbp_counts(box_df)
    # Extract PA info
    pitcher_pa_df = extract_pa_counts(box_df)

    # Batters:
    away_batters_df = create_batters(json, batter_hbp_df, "away")
    home_batters_df = create_batters(json, batter_hbp_df, "home")

    # Pitchers:
    away_pitchers_df = create_pitchers(json, pitcher_hbp_df, pitcher_pa_df, "away")
    home_pitchers_df = create_pitchers(json, pitcher_hbp_df, pitcher_pa_df, "home")


    return away_batters_df, home_batters_df, away_pitchers_df, home_pitchers_df

# %%
# Run player results for group of games in game_df
def run_player_results(game_df, row):
    print(game_df['game_id'][row])
    # Create dataframes
    away_batters_df, home_batters_df, away_pitchers_df, home_pitchers_df = create_results_dfs(game_df['game_id'][row])

    # Add info
    for df in away_batters_df, home_batters_df, away_pitchers_df, home_pitchers_df:
        df['gamePk'] = game_df['game_id'][row]
        df['date'] = game_df['date'][row]
        df['year'] = game_df['year'][row]
        df['venue_id'] = game_df['venue_id'][row]
        
    for df in away_batters_df, away_pitchers_df:
        df['team'] = "away"
        df['teamabbrev'] = game_df['away_team'][row]
    for df in home_batters_df, home_pitchers_df:
        df['team'] = "home"
        df['teamabbrev'] = game_df['home_team'][row]

    # Create folder
    os.makedirs(os.path.join(baseball_path, "A01. Player Results", f"Player Results {game_df['game_id'][row]}"), exist_ok=True)

    # Write to CSV
    away_batters_df.to_csv(os.path.join(baseball_path, "A01. Player Results", f"Player Results {game_df['game_id'][row]}", f"away batters {game_df['game_id'][row]}.csv"), index=False, encoding='iso-8859-1')
    home_batters_df.to_csv(os.path.join(baseball_path, "A01. Player Results", f"Player Results {game_df['game_id'][row]}", f"home batters {game_df['game_id'][row]}.csv"), index=False, encoding='iso-8859-1')
    away_pitchers_df.to_csv(os.path.join(baseball_path, "A01. Player Results", f"Player Results {game_df['game_id'][row]}", f"away pitchers {game_df['game_id'][row]}.csv"), index=False, encoding='iso-8859-1')
    home_pitchers_df.to_csv(os.path.join(baseball_path, "A01. Player Results", f"Player Results {game_df['game_id'][row]}", f"home pitchers {game_df['game_id'][row]}.csv"), index=False, encoding='iso-8859-1')


# %%
__all__ = [name for name in globals() if not name.startswith("_")]