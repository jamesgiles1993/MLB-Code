# %%
from U01Imports import *
from U02Functions import *

# %%
# Scrape Sportsbook Review
def sportsbookreview(bet, date):
    # Raise ValueError if bet is not accepted type
    if bet not in ['pointspread', 'totals', 'moneyline']:
        raise ValueError("Invalid input. Choose one of: 'pointspread', 'totals', 'moneyline'.")

    # Construct URL
    if bet == 'pointspread': 
        url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/pointspread/?date={date}"
    elif bet == "totals":
        url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/totals/?date={date}"
    elif bet == "moneyline":
        url = f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date}"

    try:
        # Make a GET request
        response = requests.get(url)
    
        # Check if the request was successful
        if response.status_code == 200:
            # Print the HTML content of the scraped page
            pass
        else:
            print(f"Failed to scrape URL: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")


    return response    


# %%
# Extract game data from response text
def extract_game_data(response_text):
    game_data_list = []
    start_index = response_text.find('"gameView"')
    
    while start_index != -1:
        end_index = response_text.find('"gameView"', start_index + 1)
        if end_index == -1:
            game_data = response_text[start_index:]
        else:
            game_data = response_text[start_index:end_index]
        
        game_data_list.append(game_data)
        start_index = end_index
    

    return game_data_list


# %%
# Create moneyline dataframe
def create_ml_df(df):
    # Splitting the 'game_data' column into two parts at the first instance of "draftkings" or 'openingLine'
    df[['A', 'B_temp']] = df['game_data'].str.split('openingLine', n=1, expand=True)
    
    # Splitting the 'B_temp' column into B and C at the first instance of "currentLine"
    df[['B', 'C']] = df['B_temp'].str.split('currentLine', n=1, expand=True)
    
    # Extract time
    df['EventDateTime'] = df['A'].str.extract(r'"startDate":"(.*?)"', expand=False)
    df['EventDateTime'] = pd.to_datetime(df['EventDateTime']).dt.tz_localize(None)
    
    # Extract game information
    df['gameId'] = df['A'].str.extract(r'"gameId":(\d+)', expand=False)
    df['VisitorTeamShort'] = df['A'].str.extract(r'"shortName":"(.*?)"(.*?)"shortName":"(.*?)"', expand=False)[0]
    df['HomeTeamShort'] = df['A'].str.extract(r'"shortName":"(.*?)"(.*?)"shortName":"(.*?)"', expand=False)[2]

    # Find the index of the first instance of "currentLine"
    first_current_line_index = df["B"].str.find("currentLine").idxmax()
    
    # Extract payouts
    df.loc[first_current_line_index:, 'MLMoney1'] = df.loc[first_current_line_index:, 'C'].str.extract(r'"awayOdds":(-?\d+)', expand=False)
    df.loc[first_current_line_index:, 'MLMoney2'] = df.loc[first_current_line_index:, 'C'].str.extract(r'"homeOdds":(-?\d+)', expand=False)
    
    # Keep relevant columns
    df = df[['gameId', 'EventDateTime', 'VisitorTeamShort', 'HomeTeamShort', 'MLMoney1', 'MLMoney2']]


    return df


# %%
# Create totals dataframe
def create_totals_df(df):
    # Splitting the 'game_data' column into two parts at the first instance of "draftkings" or 'openingLine'
    df[['A', 'B_temp']] = df['game_data'].str.split('openingLine', n=1, expand=True)
    
    # Splitting the 'B_temp' column into B and C at the first instance of "currentLine"
    df[['B', 'C']] = df['B_temp'].str.split('currentLine', n=1, expand=True)
    
    # Extract time
    df['EventDateTime'] = df['A'].str.extract(r'"startDate":"(.*?)"', expand=False)
    df['EventDateTime'] = pd.to_datetime(df['EventDateTime']).dt.tz_localize(None)
    
    # Extract game information
    df['gameId'] = df['A'].str.extract(r'"gameId":(\d+)', expand=False)
    df['VisitorTeamShort'] = df['A'].str.extract(r'"shortName":"(.*?)"(.*?)"shortName":"(.*?)"', expand=False)[0]
    df['HomeTeamShort'] = df['A'].str.extract(r'"shortName":"(.*?)"(.*?)"shortName":"(.*?)"', expand=False)[2]
    
    # Find the index of the first instance of "currentLine"
    first_current_line_index = df["B"].str.find("currentLine").idxmax()
    
    # # Spread is home spread
    df.loc[first_current_line_index:, 'OU'] = df.loc[first_current_line_index:, 'C'].str.extract(r'"total":(-?\d+(?:\.\d+)?)', expand=False)
    df.loc[first_current_line_index:, 'OuMoney1'] = df.loc[first_current_line_index:, 'C'].str.extract(r'"overOdds":(-?\d+)', expand=False)
    df.loc[first_current_line_index:, 'OuMoney2'] = df.loc[first_current_line_index:, 'C'].str.extract(r'"underOdds":(-?\d+)', expand=False)
    
    # Keep relevant columns
    df = df[['gameId', 'EventDateTime', 'VisitorTeamShort', 'HomeTeamShort', 'OU', 'OuMoney1', 'OuMoney2']]
    
    
    return df


# %%
# Create spread dataframe
def create_spread_df(df):
    # Splitting the 'game_data' column into two parts at the first instance of "draftkings" or 'openingLine'
    df[['A', 'B_temp']] = df['game_data'].str.split('openingLine', n=1, expand=True)
    
    # Splitting the 'B_temp' column into B and C at the first instance of "currentLine"
    df[['B', 'C']] = df['B_temp'].str.split('currentLine', n=1, expand=True)
    
    # Extract time
    df['EventDateTime'] = df['A'].str.extract(r'"startDate":"(.*?)"', expand=False)
    df['EventDateTime'] = pd.to_datetime(df['EventDateTime']).dt.tz_localize(None)
    
    # Extract game information
    df['gameId'] = df['A'].str.extract(r'"gameId":(\d+)', expand=False)
    df['VisitorTeamShort'] = df['A'].str.extract(r'"shortName":"(.*?)"(.*?)"shortName":"(.*?)"', expand=False)[0]
    df['HomeTeamShort'] = df['A'].str.extract(r'"shortName":"(.*?)"(.*?)"shortName":"(.*?)"', expand=False)[2]

    # Find the index of the first instance of "currentLine"
    first_current_line_index = df["B"].str.find("currentLine").idxmax()
    
    # Spread is home spread
    df.loc[first_current_line_index:, 'Spread'] = df.loc[first_current_line_index:, 'C'].str.extract(r'"homeSpread":(-?\d+(?:\.\d+)?)', expand=False)
    df.loc[first_current_line_index:, 'SpreadMoney1'] = df.loc[first_current_line_index:, 'C'].str.extract(r'"awayOdds":(-?\d+)', expand=False)
    df.loc[first_current_line_index:, 'SpreadMoney2'] = df.loc[first_current_line_index:, 'C'].str.extract(r'"homeOdds":(-?\d+)', expand=False)
    
    # Keep relevant columns
    df = df[['gameId', 'EventDateTime', 'VisitorTeamShort', 'HomeTeamShort', 'Spread', 'SpreadMoney1', 'SpreadMoney2']]
    
    
    return df


# %%
# Create odds dataframe
def create_odds_df(date_dash):
    ### Spread
    # Extract text
    response = sportsbookreview('pointspread', date_dash)
    # Extract game data
    spread_df = pd.DataFrame({"game_data": extract_game_data(response.text)})
    # Clean
    spread_df = create_spread_df(spread_df)
    
    ### Totals
    # Extract text
    response = sportsbookreview('totals', date_dash)
    # Extract game data
    totals_df = pd.DataFrame({"game_data": extract_game_data(response.text)})
    # Clean
    totals_df = create_totals_df(totals_df)
    
    ### Moneyline
    # Extract text
    response = sportsbookreview('moneyline', date_dash)
    # Extract game data
    ml_df = pd.DataFrame({"game_data": extract_game_data(response.text)})
    # Clean
    ml_df = create_ml_df(ml_df)
    
    # Concatenate
    odds_df = spread_df.merge(totals_df, on=['gameId'], how='left', suffixes=("", "_drop"))
    odds_df = odds_df.merge(ml_df, on=['gameId'], how='left', suffixes=("", "_drop2"))

    # Create implied runs variable - will need to be figured out later
    odds_df['VisitorVegasRuns'] = np.nan
    odds_df['HomeVegasRuns'] = np.nan

    # Create date column
    date = date_dash.replace("-", "")
    odds_df['date'] = date
    
    # Keep relevant columns
    return odds_df[['VisitorTeamShort', 'HomeTeamShort', 'Spread', 'OU', 'SpreadMoney1', 'SpreadMoney2', 'OuMoney1', 'OuMoney2', 'MLMoney1', 'MLMoney2', 'VisitorVegasRuns', 'HomeVegasRuns', 'EventDateTime', 'date']]


# %%
__all__ = [name for name in globals() if not name.startswith("_")]