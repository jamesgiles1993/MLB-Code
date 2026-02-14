# %% [markdown]
# # U04. Datasets
# - This imports functions used to create commonly-used dataset
# - Type: Utility
# - Run Frequency: Frequent
# - Created: 11/1/2023
# - Updated: 8/20/2025


# %%
from U01Imports import *

# %% [markdown]
# ### MLB Stats API

# %% [markdown]
# ##### Box Score

# %% [markdown]
# Extract game information from boxscore

# %%
# Read in boxscore for weather
def create_box(gamePk):
    # Read in boxscore as json
    box = pd.json_normalize(statsapi.boxscore_data(gamePk, timecode=None), record_path='gameBoxInfo')
    
    # Define default values
    default_weather = "75 degrees, Clear."
    default_wind = "0 mph, L To R."
    default_venue = "Missing Park."
    default_date = "November 30, 1993"
    
    # Extract weather, wind, venue, and date
    weather = box.loc[box['label'] == "Weather", "value"].item() if 'Weather' in box['label'].values else default_weather
    wind = box.loc[box['label'] == "Wind", "value"].item() if 'Wind' in box['label'].values else default_wind
    venue = box.loc[box['label'] == "Venue", "value"].item() if 'Venue' in box['label'].values else default_venue
    
    try:
        date = box.iloc[-1, box.columns.get_loc('label')]
    except:
        date = default_date

    if "Weather" not in list(box['label']):
        missing_weather = True
    else:
        missing_weather = False
        
    
    
    return weather, wind, venue, date, missing_weather

# %% [markdown]
# Extract relevant data or provide default (helper function)

# %%
def extract_field(data, field, default=None):
    try:
        return data[field]
    except:
        return default

# %% [markdown]
# Extract play-by-play data

# %%
def create_play_by_play(gamePk):
    game = statsapi.get('game_playByPlay', {'gamePk': gamePk})
    
    # Create list with relevant variables
    game_data = []
    for play in game['allPlays']:
        about = play['about']
        count = play['count']
        result = play['result']
        matchup = play['matchup']
        runners = play['runners']
        
        atBatIndex = about['atBatIndex']
        inning = about['inning']
        halfInning = about['halfInning']
        outs = count['outs']
        
        type = extract_field(result, 'type')
        event = extract_field(result, 'event')
        eventType = extract_field(result, 'eventType')
        description = extract_field(result, 'description')
        rbi = extract_field(result, 'rbi', 0)
        awayScore = extract_field(result, 'awayScore', 0)
        homeScore = extract_field(result, 'homeScore', 0)
        
        batter = extract_field(matchup['batter'], 'id', 999999)
        batterName = extract_field(matchup['batter'], 'fullName', 'Missing Name')
        batSide = extract_field(matchup['batSide'], 'code', 'R')
        pitcher = extract_field(matchup['pitcher'], 'id', 999999)
        pitcherName = extract_field(matchup['pitcher'], 'fullName', 'Missing Name')
        pitchHand = extract_field(matchup['pitchHand'], 'code', 'R')
        
        # Baserunner on base at the end of the play
        postOnFirst = extract_field(matchup, 'postOnFirst', None)
        postOnSecond = extract_field(matchup, 'postOnSecond', None)
        postOnThird = extract_field(matchup, 'postOnThird', None)
        
        # Extract base runner information
        for runner in runners:
            details = runner['details']
            movement = runner['movement']
            
            runner_id = details['runner']['id']
            start = movement['start']
            end = movement['end']
            movementReason = details['movementReason']
            isScoringEvent = details['isScoringEvent']
            earned = details['earned']
            
            game_data.append([atBatIndex, inning, halfInning, outs, type, runner_id, event, eventType, description, 
                              rbi, awayScore, homeScore, batter, batterName, batSide, pitcher, pitcherName, pitchHand, 
                              postOnFirst, postOnSecond, postOnThird, runner_id, start, end, movementReason, isScoringEvent, earned])
    
    # Create dataframe
    df = pd.DataFrame(game_data, columns=['atBatIndex', 'inning', 'halfInning', 'outs', 'type', 'id', 'event', 'eventType', 'description', 
                                          'rbi', 'awayScore', 'homeScore', 'batter', 'batterName', 'batSide', 'pitcher', 
                                          'pitcherName', 'pitchHand', 'postOnFirst', 'postOnSecond', 'postOnThird', 'runner_id', 'start', 'end', 
                                          'movementReason', 'isScoringEvent', 'earned'])
 
    # Create weather variables
    weather, wind, venue, date, missing_weather = create_box(gamePk)
    df['gamePk'] = gamePk
    df['weather'] = weather
    df['wind'] = wind
    df['venue'] = venue
    df['date'] = date
    
    
    return df

# %% [markdown]
# Extract API data

# %%
def plays_statsapi(start_date, end_date):
    # Extract year
    year = start_date[-4:]
    
    # Read in schedule
    games = statsapi.schedule(start_date=start_date, end_date=end_date)

    # Use a list comprehension to extract unique game_ids
    game_ids = list(game['game_id'] for game in games)
    away_names = list(game['away_name'] for game in games)
    home_names = list(game['home_name'] for game in games)
    game_dates = list(game['game_date'] for game in games)
    game_types = list(game['game_type'] for game in games)
    venue_ids = list(game['venue_id'] for game in games)

    # Run all in parallel
    df_list = Parallel(n_jobs=-1, verbose=0)(delayed(create_play_by_play)(gamePk=game_id) for game_id in game_ids)

    # Add additional information from schedule
    for i in range(len(df_list)):
        df_list[i]['away_name'] = away_names[i]
        df_list[i]['home_name'] = home_names[i]
        df_list[i]['game_date'] = game_dates[i]
        df_list[i]['game_type'] = game_types[i]
        df_list[i]['venue_id'] = venue_ids[i]
    
    # Append all dataframes together
    df = pd.concat(df_list, axis=0)

    
    return df

# %%


# %% [markdown]
# ### Statcast

# %% [markdown]
# Extract Statcast data

# %%
def plays_statcast(start_date, end_date):
    # Extract year
    year = start_date[:4]
    
    # Use pybaseball to read in Statcast data
    data = statcast(start_date, end_date)
    
    # Create atBatIndex compatible with Statsapi
    data['atBatIndex'] = data['at_bat_number'] - 1 
    
    # Highest level during the at bat
    data['maxSpeed'] = data.groupby(['game_pk', 'atBatIndex'])['effective_speed'].transform(max)
    data['maxSpin'] = data.groupby(['game_pk', 'atBatIndex'])['release_spin_rate'].transform(max)
    
    # Convert to numeric for sorting
    data['game_pk'] = data['game_pk'].astype('int')
    data['atBatIndex'] = data['atBatIndex'].astype('int')
    data['pitch_number'] = data['pitch_number'].astype('int')
    
    # Only want the deciding (last) pitch
    data.sort_values(['game_pk', 'atBatIndex', 'pitch_number'], inplace=True)
    data.drop_duplicates(['game_pk', 'atBatIndex'], keep='last', inplace=True)
    
    data.rename(columns={'game_pk':'gamePk'}, inplace=True)
    
    # Keep relevant variables
    keep_list = ['gamePk', 'atBatIndex', 'pitch_number', 'pitch_name', 'game_type',
                 'hc_x', 'hc_y', 'hit_location', 'hit_distance_sc', 'launch_speed', 'launch_angle', 'launch_speed_angle',
                 'woba_value', 'woba_denom', 'estimated_ba_using_speedangle', 'estimated_woba_using_speedangle',
                 'iso_value', 'babip_value',
                 'maxSpeed', 'maxSpin']
                
    data = data[keep_list]

    
    return data

# %%


# %% [markdown]
# ### Complete Dataset

# %% [markdown]
# ##### 1. Merge Datasets

# %%
def process_year(year):
    statsapi_df = pd.read_csv(os.path.join(baseball_path, "A02. MLB API", "1. Stats API", f"Stats API {year}.csv"), encoding='iso-8859-1')
    statcast_df = pd.read_csv(os.path.join(baseball_path, "A02. MLB API", "2. Statcast", f"Statcast {year}.csv"), encoding='iso-8859-1')

    merged_df = pd.merge(statsapi_df, statcast_df, on=['gamePk', 'atBatIndex'], how='left', suffixes=("", "_copy"))
    merged_df.drop_duplicates(['gamePk', 'atBatIndex'], keep='first', inplace=True)
    merged_df.drop(columns={'game_type_copy'}, inplace=True)

    return merged_df

def merge_datasets(start_year=2015, end_year=2025):
    df_list = Parallel(n_jobs=-1)(delayed(process_year)(year) for year in range(start_year, end_year + 1))
    df = pd.concat(df_list, axis=0)
    df.sort_values(['game_date', 'gamePk', 'atBatIndex'], ascending=True, inplace=True)
    df.drop_duplicates(['gamePk', 'atBatIndex'], keep='first', inplace=True)
    # Only keep regular season games
    df = df[df['game_type'] == "R"]
    
    df.reset_index(drop=True, inplace=True)


    return df

# %% [markdown]
# ##### 2. Clean Weather

# %%
def clean_weather(df):
    import numpy as np

    # Split weather into temperature and weather type
    weather_split = df['weather'].str.split(", ", expand=True)
    df['temperature'] = pd.to_numeric(weather_split[0].str.replace(" degrees", ""), errors='coerce')
    df['weather'] = weather_split[1]

    # Split wind into speed and direction
    wind_split = df['wind'].str.split(", ", expand=True)
    df['windSpeed'] = pd.to_numeric(wind_split[0].str.replace(" mph", ""), errors='coerce').fillna(0)
    df['windDirection'] = wind_split[1].fillna('L to R').str.replace(".", "", regex=False)

    wind_speed = df['windSpeed'].to_numpy()
    angled = wind_speed / 2 * np.sqrt(2)
    direction = df['windDirection'].to_numpy()

    # Create lookup tables
    y_lookup = {
        "Out To CF": wind_speed,
        "Out To RF": angled,
        "L To R": np.zeros_like(wind_speed),
        "In From LF": -angled,
        "In From CF": -wind_speed,
        "In From RF": -angled,
        "R To L": np.zeros_like(wind_speed),
        "Out To LF": angled
    }

    x_lookup = {
        "L To R": wind_speed,
        "In From LF": angled,
        "In From CF": np.zeros_like(wind_speed),
        "In From RF": -angled,
        "R To L": -wind_speed,
        "Out To LF": -angled,
        "Out To CF": np.zeros_like(wind_speed),
        "Out To RF": angled
    }

    df['y_vect'] = np.zeros(len(df))
    df['x_vect'] = np.zeros(len(df))

    for key, values in y_lookup.items():
        df.loc[direction == key, 'y_vect'] = values[direction == key]
    for key, values in x_lookup.items():
        df.loc[direction == key, 'x_vect'] = values[direction == key]

    # Overwrite for domes/roofs
    is_dome = df['weather'].str.contains('Roof|Dome', na=False)
    df.loc[is_dome, 'temperature'] = 70
    df.loc[is_dome, ['x_vect', 'y_vect']] = 0

    return df


# %% [markdown]
# ##### 3. Create PA Events

# %%
# Assign play categories to full descriptions
def create_events(df):
    event_mapping = {
        'Strikeout': 'so',
        'Strikeout Double Play': 'so',
        'Groundout': 'go',
        'Fielders Choice': 'go',
        'Fielders Choice Out': 'go',
        'Double Play': 'go',
        'Grounded Into DP': 'go',
        'Triple Play': 'go',
        'Field Error': 'go',
        'Forceout': 'go',
        'Sac Bunt': 'go',
        'Sac Bunt Double Play': 'go', 
        'Bunt Groundout': 'go',
        'Lineout': 'lo',
        'Bunt Lineout': 'lo',
        'Flyout': 'fo',
        'Sac Fly': 'fo',
        'Sac Fly Double Play': 'fo',
        'Pop Out': 'po',
        'Bunt Pop Out': 'po',
        'Hit By Pitch': 'hbp',
        'Walk': 'bb',
        'Intent Walk': 'bb',
        'Single': 'b1',
        'Double': 'b2',
        'Triple': 'b3',
        'Home Run': 'hr'
    }

    df['eventsModel'] = df['event'].map(event_mapping).fillna('Cut')

    
    return df

# %% [markdown]
# ##### 4. Create Variables

# %%
# This turns several variables, including events, venues, hands, and bases into dummies
def create_variables(df):    
    # Events
    event_dummies = pd.get_dummies(df['eventsModel'])
    
    # Hands
    pitcher_dummies = pd.get_dummies(df['pitchHand'], prefix='p')
    batter_dummies = pd.get_dummies(df['batSide'], prefix='b')
    
    # Years
    df['year'] = df['game_date'].str[:4]
    
    # Add dummies to dataframe
    df = pd.concat([df, event_dummies, pitcher_dummies, batter_dummies], axis=1)

    # Identify starting pitcher
    df['startingPitcher'] = df.groupby(['gamePk', 'halfInning'])['pitcherName'].transform('first')
    df['starter'] = (df['startingPitcher'] == df['pitcherName']).astype('int')
    
    # Determine outs coming into PA
    df['outs_pre'] = df.groupby(['gamePk', 'inning', 'halfInning'])['outs'].shift(fill_value=0)
    
    # Determine if PA ended in an out 
    df['is_out'] = df[['so', 'go', 'lo', 'po', 'fo']].sum(axis=1)
    
    # Create compatible date variable
    df['date'] = df['game_date'].str.replace('-', '')
    
    # Convert to numeric for sorting
    df['date'] = df['date'].astype('int')
    df['gamePk'] = df['gamePk'].astype('int')
    df['atBatIndex'] = df['atBatIndex'].astype('int')
    
    # Sort
    df.sort_values(['date', 'gamePk', 'atBatIndex'], ascending=True, inplace=True)
    
    # Create dummy for runners on base
    df['preOnFirst'] = df.groupby(['gamePk', 'inning', 'halfInning'])['postOnFirst'].shift(1)
    df['preOnSecond'] = df.groupby(['gamePk', 'inning', 'halfInning'])['postOnSecond'].shift(1)
    df['preOnThird'] = df.groupby(['gamePk', 'inning', 'halfInning'])['postOnThird'].shift(1)
    
    df['onFirst'] = df['preOnFirst'].apply(lambda x: 1 if isinstance(x, str) and 'id' in x else 0)
    df['onSecond'] = df['preOnSecond'].apply(lambda x: 1 if isinstance(x, str) and 'id' in x else 0)
    df['onThird'] = df['preOnThird'].apply(lambda x: 1 if isinstance(x, str) and 'id' in x else 0)
    
    # Top of the inning dummy
    df['top'] = (df['halfInning'] == "top").astype(int)
    
    # Convert to numeric
    df['awayScore'] = df['awayScore'].astype('int')
    df['homeScore'] = df['homeScore'].astype('int')
    
    # Determine score before PA
    df['preAwayScore'] = df.groupby(['gamePk'])['awayScore'].shift(1)
    df['preHomeScore'] = df.groupby(['gamePk'])['homeScore'].shift(1)
    
    # If it's the first PA, it'll be missing. 
    df['preAwayScore'] = df['preAwayScore'].fillna(0)
    df['preHomeScore'] = df['preHomeScore'].fillna(0)
    
    # Calculate differential
    df['score_diff'] = np.where(df['top'] == 1, df['preAwayScore'] - df['preHomeScore'], df['preHomeScore'] - df['preAwayScore'])
    
    # Determine hitter and pitcher scores
    df['batterScore'] = np.where(df['halfInning'] == 'top', df['awayScore'], df['homeScore'])
    df['pitcherScore'] = np.where(df['halfInning'] == 'top', df['homeScore'], df['awayScore'])
    
    # Determine score before PA
    df['preBatterScore'] = np.where(df['halfInning'] == 'top', df['preAwayScore'], df['preHomeScore'])
    df['prePitcherScore'] = np.where(df['halfInning'] == 'top', df['preHomeScore'], df['preAwayScore'])
    
    # Calculate PAs and ABs
    df['pa'] = np.where(df['eventsModel'] != "Cut", 1, 0)
    df['ab'] = df['pa'] - df['hbp'] - df['bb']           
    
    
    # Fix Guardians name to make uniform
    df['away_name'] = np.where(df['away_name'] == "Cleveland Indians", "Cleveland Guardians", df['away_name'])
    df['home_name'] = np.where(df['home_name'] == "Cleveland Indians", "Cleveland Guardians", df['home_name'])

    
    ### Statcast
    # Convert variables to numeric
    df['launch_speed'] = pd.to_numeric(df['launch_speed'], errors='coerce')
    df['launch_speed_angle'] = pd.to_numeric(df['launch_speed_angle'], errors='coerce')
    df['hc_x'] = pd.to_numeric(df['hc_x'], errors='coerce')
    df['hc_y'] = pd.to_numeric(df['hc_y'], errors='coerce')
    
    # Hard hit dummy
    df['hard_hit'] = (df['launch_speed'] >= 95).astype('int')
    
    # Barrel dummy
    df['barrel'] = (df['launch_speed_angle'] == 6).astype('int')

    # Spray 
    df['spray_angle'] = np.arctan((df['hc_x'] - 125.42) / (198.27 - df['hc_y'])) * 180 / np.pi * 0.75

    # Broad field
    df['to_left'] = np.where(df['spray_angle'].isna(), np.nan,
                             (df['spray_angle'] < -15).astype(int))
    df['to_middle'] = np.where(df['spray_angle'].isna(), np.nan,
                               ((df['spray_angle'] >= -15) & (df['spray_angle'] <= 15)).astype(int))
    df['to_right'] = np.where(df['spray_angle'].isna(), np.nan,
                              (df['spray_angle'] > 15).astype(int))
    
    # Narrow field
    df['to_l'] = np.where(df['spray_angle'].isna(), 0,
                          (df['spray_angle'] < -27).astype(int))
    df['to_lc'] = np.where(df['spray_angle'].isna(), 0,
                           ((df['spray_angle'] >= -27) & (df['spray_angle'] < -9)).astype(int))
    df['to_c'] = np.where(df['spray_angle'].isna(), 0,
                          ((df['spray_angle'] >= -9) & (df['spray_angle'] < 9)).astype(int))
    df['to_rc'] = np.where(df['spray_angle'].isna(), 0,
                           ((df['spray_angle'] >= 9) & (df['spray_angle'] < 27)).astype(int))
    df['to_r'] = np.where(df['spray_angle'].isna(), 0,
                          (df['spray_angle'] > 27).astype(int))


    # Sort
    df.sort_values(['date', 'gamePk', 'atBatIndex'], inplace=True)

    
    return df

# %% [markdown]
# ##### 5. Park Adjustments

# %%
def park_adjustments(df, multiplier_df):       
    # Merge with park factors
    pfx_columns = [col for col in multiplier_df.columns if "pfx" in col]
    wfx_columns = [col for col in multiplier_df.columns if "wfx" in col]
    df = df.merge(multiplier_df[['gamePk'] + pfx_columns + wfx_columns], on=['gamePk'], how='left')

    # If missing, set adjustment to 1
    df[pfx_columns] = df[pfx_columns].fillna(1)
    df[wfx_columns] = df[wfx_columns].fillna(1)

    # Loop over events
    for event in events_list:
        # Adjust based on calculated multiplier
        df[f'{event}_adj'] = np.where(df['batSide'] == "L", df[event].astype(float) / df[f'{event}_wfx_l'].astype(float), df[event].astype(float) / df[f'{event}_wfx_r'].astype(float))
    
    return df

# %% [markdown]
# ##### 6. Starter Stats

# %%
def start_data(df):
    original_index = df.index  # Save the original index
    
    pl_df = pl.from_pandas(df)

    # Calculate hits, total bases, reached, and faced
    pl_df = pl_df.with_columns([
        (pl.col('b1').cast(pl.Float64) + pl.col('b2').cast(pl.Float64) + pl.col('b3').cast(pl.Float64) + pl.col('hr').cast(pl.Float64)).alias('h'),
        (pl.col('b1') * 1 + pl.col('b2') * 2 + pl.col('b3') * 3 + pl.col('hr') * 4).alias('tb'),
        (pl.col('b1').cast(pl.Float64) + pl.col('b2').cast(pl.Float64) + pl.col('b3').cast(pl.Float64) + pl.col('hr').cast(pl.Float64) + pl.col('bb').cast(pl.Float64) + pl.col('hbp').cast(pl.Float64)).alias('reached'),
        pl.lit(1).alias('faced'),
        (((pl.col('inning') - 1) * 3) + pl.col('outs')).alias('outs_total')
    ])

    # Outs per PA
    pl_df = pl_df.sort(['gamePk', 'inning', 'halfInning', 'atBatIndex'])
    pl_df = pl_df.with_columns([
        (pl.col('outs_total') - pl.col('outs_total').shift(1)).over(['gamePk', 'inning', 'halfInning']).alias('outs_pa')
    ]).with_columns([
        pl.when(pl.col('outs_pa').is_null()).then(pl.col('outs')).otherwise(pl.col('outs_pa')).alias('outs_pa')
    ])

    # Sort before cumulative calculations
    pl_df = pl_df.sort(['gamePk', 'pitcher', 'inning', 'atBatIndex'])
    
    # Rolling cumulative stats per inning
    for stat in events_list + ['h', 'tb', 'reached', 'faced', 'rbi', 'outs_pa']:
        pl_df = pl_df.with_columns([
            pl.col(stat).cum_sum().over(['gamePk', 'pitcher', 'inning']).alias(f'{stat}_inning')
        ])

    # Rolling cumulative stats per game
    for stat in events_list + ['h', 'tb', 'reached', 'faced', 'rbi', 'outs_pa']:
        pl_df = pl_df.with_columns([
            pl.col(stat).cum_sum().over(['gamePk', 'pitcher']).alias(f'{stat}_game')
        ])

    # Bottom of the inning flag
    pl_df = pl_df.with_columns([
        (pl.col('top') == 0).cast(pl.Int8).alias('bottom')
    ])

    # Sort to identify starting pitchers
    pl_df = pl_df.sort(['date', 'gamePk', 'bottom', 'atBatIndex'])

    # Identify first at-bat for each bottom
    pl_df = pl_df.with_columns([
        pl.col('atBatIndex').min().over(['gamePk', 'bottom']).alias('atBatIndex_min')
    ]).with_columns([
        (pl.col('atBatIndex') == pl.col('atBatIndex_min')).cast(pl.Int8).alias('first_ab')
    ])

    # Identify pulled pitcher
    pl_df = pl_df.with_columns([
        pl.col('atBatIndex').max().over(['gamePk', 'pitcher']).alias('atBatIndex_max')
    ]).with_columns([
        (pl.col('atBatIndex') == pl.col('atBatIndex_max')).cast(pl.Int8).alias('pulled')
    ])

    # Times faced in game (adjusted for total batters faced)
    pl_df = pl_df.with_columns([
        (pl.col('faced_game') / 9).floor().fill_null(0).alias('times_faced')
    ])

    result = pl_df.to_pandas()
    result.index = original_index  # Restore the original index
    
    return result


# %% [markdown]
# ##### 7. Rolling Stats

# %%
def rolling_pas(df, pa_num, events_list):
    # Renaming columns on df before conversion to Polars
    df.rename(columns={'hit_distance_sc': 'totalDistance', 'launch_speed': 'launchSpeed'}, inplace=True)

    # Convert to Polars after renaming
    pl_df = pl.from_pandas(df)

    # Ensure types are correctly set after converting to Polars
    pl_df = pl_df.with_columns([
        pl.col('date').cast(pl.Int32),
        pl.col('gamePk').cast(pl.Int32),
        pl.col('atBatIndex').cast(pl.Int32),
        pl.col('batter').cast(pl.Int32),
        pl.col('pitcher').cast(pl.Int32)
    ])

    # Sorting is done in Polars
    pl_df = pl_df.sort(['date', 'gamePk', 'atBatIndex'])

    # Create expressions for batter and pitcher stats
    batter_avg_exprs = [
        pl.col(col).rolling_mean(window_size=pa_num, min_periods=1).over(['batter', 'pitchHand']).alias(col + '_b')
        for col in events_list + statcast_list
    ]
    # batter_max_exprs = [
    #     pl.col(col).rolling_max(window_size=pa_num, min_periods=1).over(['batter', 'pitchHand']).alias(col + '_b')
    #     for col in max_list
    # ]
    batter_sum_exprs = [
        pl.col(col).rolling_sum(window_size=pa_num, min_periods=1).over(['batter', 'pitchHand']).alias(col + '_b')
        for col in ['ab', 'pa']
    ]

    pitcher_avg_exprs = [
        pl.col(col).rolling_mean(window_size=pa_num, min_periods=1).over(['pitcher', 'batSide']).alias(col + '_p')
        for col in events_list + statcast_list
    ]
    # pitcher_max_exprs = [
    #     pl.col(col).rolling_max(window_size=pa_num, min_periods=1).over(['pitcher', 'batSide']).alias(col + '_p')
    #     for col in max_list
    # ]
    pitcher_sum_exprs = [
        pl.col(col).rolling_sum(window_size=pa_num, min_periods=1).over(['pitcher', 'batSide']).alias(col + '_p')
        for col in ['ab', 'pa']
    ]

    # Add the computed columns to pl_df
    pl_df = pl_df.with_columns(
        batter_avg_exprs  + batter_sum_exprs +
        pitcher_avg_exprs + pitcher_sum_exprs
    )

    # Create 'imp_b' and 'imp_p' directly in Polars
    pl_df = pl_df.with_columns([
        (pl.col('pa_b') < 40).cast(pl.Int32).alias('imp_b'),
        (pl.col('pa_p') < 40).cast(pl.Int32).alias('imp_p')
    ])

    # Clean up date and other columns directly in Polars
    pl_df = pl_df.with_columns([
        pl.col('game_date').str.replace_all('-', '').cast(pl.Int32).alias('date'),
        pl.col('gamePk').cast(pl.Int32),
        pl.col('atBatIndex').cast(pl.Int32),
        pl.col('batter').cast(pl.Int32),
        pl.col('pitcher').cast(pl.Int32)
    ])

    # Sort the data as needed
    pl_df = pl_df.sort(['date', 'gamePk', 'atBatIndex'])

    # Calculating wOBA, SLG, OBP, and ISO directly in Polars
    pl_df = pl_df.with_columns([
        (0.690 * pl.col('bb_b') + 0.721 * pl.col('hbp_b') +
         0.885 * pl.col('b1_b') + 1.262 * pl.col('b2_b') +
         1.601 * pl.col('b3_b') + 2.070 * pl.col('hr_b')).alias('woba_b'),
        (0.690 * pl.col('bb_p') + 0.721 * pl.col('hbp_p') +
         0.885 * pl.col('b1_p') + 1.262 * pl.col('b2_p') +
         1.601 * pl.col('b3_p') + 2.070 * pl.col('hr_p')).alias('woba_p'),

        ((1 * pl.col('b1_b') + 2 * pl.col('b2_b') + 3 * pl.col('b3_b') + 4 * pl.col('hr_b')) *
         (1 / (1 - (pl.col('bb_b') + pl.col('hbp_b'))))).alias('slg_b'),
        ((1 * pl.col('b1_p') + 2 * pl.col('b2_p') + 3 * pl.col('b3_p') + 4 * pl.col('hr_p')) *
         (1 / (1 - (pl.col('bb_p') + pl.col('hbp_p'))))).alias('slg_p'),

        (pl.col('b1_b') + pl.col('b2_b') + pl.col('b3_b') + pl.col('hr_b') +
         pl.col('bb_b') + pl.col('hbp_b')).alias('obp_b'),
        (pl.col('b1_p') + pl.col('b2_p') + pl.col('b3_p') + pl.col('hr_p') +
         pl.col('bb_p') + pl.col('hbp_p')).alias('obp_p'),

        ((pl.col('b2_b') + 2 * pl.col('b3_b') + 3 * pl.col('hr_b')) *
         (1 / (1 - (pl.col('bb_b') + pl.col('hbp_b'))))).alias('iso_b'),
        ((pl.col('b2_p') + 2 * pl.col('b3_p') + 3 * pl.col('hr_p')) *
         (1 / (1 - (pl.col('bb_p') + pl.col('hbp_p'))))).alias('iso_p')
    ])

    # Convert back to pandas for final operations
    df_copy = pl_df.to_pandas()


    
    return df_copy


# %% [markdown]
# ##### Model Inputs

# %%
def create_pa_inputs(multiplier_df, start_year=2014, end_year=2024, short=50, long=300, adjust=True):
    # If we're creating a new complete dataset
    # if generate == True:
    start_time = time.time()
    df = merge_datasets(start_year, end_year)
    print(f"merge_datasets took {time.time() - start_time:.2f} seconds")

    start_time = time.time()
    df2 = clean_weather(df)
    print(f"clean_weather took {time.time() - start_time:.2f} seconds")

    start_time = time.time()
    df3 = create_events(df2)
    print(f"create_events took {time.time() - start_time:.2f} seconds")

    start_time = time.time()
    df4 = create_variables(df3)
    print(f"create_variables took {time.time() - start_time:.2f} seconds")

    if adjust:
        start_time = time.time()
        df5 = park_adjustments(df4, multiplier_df)
        print(f"park_adjustments took {time.time() - start_time:.2f} seconds")
    else:
        df5 = df4.copy()

    start_time = time.time()
    df6 = start_data(df5)
    print(f"start_data took {time.time() - start_time:.2f} seconds")
    
    ### Rolling stats
    # Short
    start_time = time.time()
    df_short = rolling_pas(df6, short, adjust)
    print(f"Short took {time.time() - start_time:.2f} seconds")

    # Long
    start_time = time.time()
    df_long = rolling_pas(df6, long, adjust)
    df_long = df_long.add_suffix("_long")
    print(f"Long took {time.time() - start_time:.2f} seconds")

        
    # We only need the rolling stats 
    long_stats = batter_stats_long + pitcher_stats_long
    df_long = df_long[long_stats]
    
    # Dataset
    complete_dataset = pd.concat([df_short, df_long], axis=1)

    # Normalize so stats add up to 1
    complete_dataset['sum_b'] = complete_dataset[['b1_b', 'b2_b', 'b3_b', 'hr_b', 'bb_b', 'hbp_b', 'so_b', 'lo_b', 'fo_b', 'go_b', 'po_b']].sum(axis=1)
    for stat in ['b1_b', 'b2_b', 'b3_b', 'hr_b', 'bb_b', 'hbp_b', 'so_b', 'lo_b', 'fo_b', 'go_b', 'po_b']:
        complete_dataset[stat] = complete_dataset[stat] / complete_dataset['sum_b']
    
    complete_dataset['sum_b_long'] = complete_dataset[['b1_b_long', 'b2_b_long', 'b3_b_long', 'hr_b_long', 'bb_b_long', 'hbp_b_long', 'so_b_long', 'lo_b_long', 'fo_b_long', 'go_b_long', 'po_b_long']].sum(axis=1)
    for stat in ['b1_b_long', 'b2_b_long', 'b3_b_long', 'hr_b_long', 'bb_b_long', 'hbp_b_long', 'so_b_long', 'lo_b_long', 'fo_b_long', 'go_b_long', 'po_b_long']:
        complete_dataset[stat] = complete_dataset[stat] / complete_dataset['sum_b_long']
        
    complete_dataset['sum_p'] = complete_dataset[['b1_p', 'b2_p', 'b3_p', 'hr_p', 'bb_p', 'hbp_p', 'so_p', 'lo_p', 'fo_p', 'go_p', 'po_p']].sum(axis=1)
    for stat in ['b1_p', 'b2_p', 'b3_p', 'hr_p', 'bb_p', 'hbp_p', 'so_p', 'lo_p', 'fo_p', 'go_p', 'po_p']:
        complete_dataset[stat] = complete_dataset[stat] / complete_dataset['sum_p']
        
    complete_dataset['sum_p_long'] = complete_dataset[['b1_p_long', 'b2_p_long', 'b3_p_long', 'hr_p_long', 'bb_p_long', 'hbp_p_long', 'so_p_long', 'lo_p_long', 'fo_p_long', 'go_p_long', 'po_p_long']].sum(axis=1)
    for stat in ['b1_p_long', 'b2_p_long', 'b3_p_long', 'hr_p_long', 'bb_p_long', 'hbp_p_long', 'so_p_long', 'lo_p_long', 'fo_p_long', 'go_p_long', 'po_p_long']:
        complete_dataset[stat] = complete_dataset[stat] / complete_dataset['sum_p_long']

    # Reset index
    complete_dataset.reset_index(drop=True, inplace=True)
    
    # Sort
    complete_dataset.sort_values(['date', 'gamePk', 'atBatIndex'], ascending=True, inplace=True)

    
    return complete_dataset

# %%


# %% [markdown]
# ### Steamer

# %% [markdown]
# ##### 1. Hitters

# %%
def clean_steamer_hitters(df):
    # Basic stats
    hit_list = ['1B', '2B', '3B', 'HR', 'BB', 'HBP', 'K']

    # Advance stats
    rate_list = ['OBP', 'SLG', 'wOBA']
    for stat in hit_list:
        rate = stat + "_rate"
        rate_list.append(rate)
        df[rate] = df[stat] / df['PA']

    # Stolen base attempts
    df['SBA'] = df['SB'] + df['CS']
    # Stolen base opportunities (times on first)
    df['SBO'] = df['1B'] + df['BB'] + df['HBP']
    
    # Date
    df['date'] = df['proj_date'].str.replace("-", "")
    df['date'] = df['date'].astype('int')
    
    # Keep relevant variables
    keep_list = ['date', 'firstname', 'lastname', 'mlbamid', 'steamerid'] + ['SB', 'SBA', 'SBO'] + rate_list
    df = df[keep_list]
    
    # Clean up
    df.columns = df.columns.str.lower()
    df.rename(columns={'1b_rate': 'b1_rate', '2b_rate': 'b2_rate', '3b_rate': 'b3_rate', 'k_rate':'so_rate'}, inplace=True)
    df.dropna(inplace=True)
    
    # Drop duplicates
    df.drop_duplicates(subset=['steamerid', 'date'], inplace=True)

    
    return df 

# %% [markdown]
# ##### 2. Pitchers

# %%
def clean_steamer_pitchers(df):
    # Hits per 9 innings
    df['H9'] = df['H'] / df['IP'] * 9
    
    # Calculate average innings per game started
    df['IP_start'] = df['start_IP'] / df['GS']
    df['IP_start'].fillna(0, inplace=True)
    # Replace infinites
    df['IP_start'].replace([np.inf, -np.inf], 3, inplace=True)

    # Date
    df['date'] = df['proj_date'].str.replace("-", "")
    df['date'] = df['date'].astype('int')
    
    # Keep relevant variables
    keep_list = ['date', 'firstname', 'lastname', 'mlbamid', 'steamerid'] + pitcher_stats_fg + ['reliability','IP_start','IP','relief_IP']
    df = df[keep_list]
    
    # Drop duplicates
    df.drop_duplicates(subset=['steamerid', 'date'], inplace=True)

    
    return df


# %%
__all__ = [name for name in globals() if not name.startswith("_")]