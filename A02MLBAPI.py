# %%
from U01Imports import *


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


# %%
# Extract relevant data or provide default (helper function)
def extract_field(data, field, default=None):
    try:
        return data[field]
    except:
        return default

# %% [markdown]

# %%
# Extract play-by-play data
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


# %%
# Extract API data
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
# Extract Statcast data
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
__all__ = [name for name in globals() if not name.startswith("_")]