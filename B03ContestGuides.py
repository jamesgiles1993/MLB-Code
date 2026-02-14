from U01Imports import *
from U02Functions import *

# %%
# Identify DraftKings slate name
def pick_slate(Name):
    if "(Early)" in Name:
        slate = "Early"
    elif "(Late Night)" in Name:
        slate = "Late Night"
    elif "Night" in Name:
        slate = "Night"
    elif "Afternoon" in Name:
        slate = "Afternoon"
    else:
        slate = "All"

    
    return slate


# %%
# Build contest guides from Contests.csv (one time run for historical contests)
def historic_contest_guide(all_games_df, contestKey):
    # Selected contest
    selected_contest = contests.query(f'contestKey == {contestKey}').reset_index(drop=True)

    # Identify slate name (Early, Afternoon, Night, Late Night, All)
    selected_contest['slate'] = selected_contest['name'].apply(pick_slate)
    
    # Extract date and slate name
    date = selected_contest['date'][0]
    slate = selected_contest['slate'][0]
    
    # Identify slate IDs
    # DFF
    # Can be missing, might need to use date-based slates
    try:
        # Read in slates
        dff_slates = pd.read_csv(os.path.join(baseball_path, "A08. Projections", "1. DFF", "1. Slates", f"DFF Slates {int(date)}.csv"))

        # Identify slate ID
        slateID = dff_slates.loc[(dff_slates['date'] == date) & (dff_slates['Slate Type'] == slate), 'URL'].values[0]

        # Make it an integer, if possible
        try:
            slateID = int(slateID)
        except:
            pass
    except:
        slateID = np.nan

        
    # Assign
    selected_contest['dff_slate'] = slateID
    
    # RotoWire
    # Shouldn't really be missing, but allow for it.
    try:
        # Read in Roto slates
        roto_slates = pd.read_csv(os.path.join(baseball_path, "A08. Projections", "2. RotoWire", "1. Slates", f"RotoWire Slates {int(date)}.csv"))

        # Identify slate ID
        slateID = roto_slates.loc[(roto_slates['date'] == date) & (roto_slates['name'] == slate), 'slateID'].values[0]
    except:
        slateID = np.nan

    # Assign
    selected_contest['roto_slate'] = slateID
    
    
    # Determine matchups
    # Extract draftGroupId
    draftGroupId = selected_contest['draftGroupId'][0]
    # Read in draftable players
    draftables = pd.read_csv(os.path.join(baseball_path, "A09. DraftKings", "2. Draftables", f'Draftables {int(draftGroupId)}.csv'), encoding='iso-8859-1')
    # Identify matchups
    slate_matchups = draftables[['Game Info', 'draftGroupId']].drop_duplicates('Game Info', keep='first')

    # Merge matchups onto contest
    selected_contest = selected_contest.merge(slate_matchups, on='draftGroupId', how='inner')

    # Identify away team
    selected_contest['DKTEAM'] = selected_contest['Game Info'].str.split("@", expand=True)[0]

    # Merge on BBREFTEAM ID for merging with all_game_df
    selected_contest = selected_contest.merge(team_map[['DKTEAM', 'BBREFTEAM']], on='DKTEAM', how='left')
    
    # Merge with all_games_df for more game information (game_id, in particular)
    selected_contest = selected_contest.merge(all_games_df[['date', 'away_team', 'game_id', 'game_type', 'status', 'game_num', 'away_score', 'home_score']], left_on=['BBREFTEAM', 'date'], right_on=['away_team', 'date'], how='inner')

    # Handle doubleheaders
    # If there are multiple instances of a team, we want to keep the first if it's an early slate or the second if it's a later slate.
    if slate in ['Early', 'Afternoon']:
        selected_contest.drop_duplicates('DKTEAM', keep='first', inplace=True)
    else:
        selected_contest.drop_duplicates('DKTEAM', keep='last', inplace=True)
        
    selected_contest['date'] = selected_contest['date'].astype('int')
    selected_contest['draftGroupId'] = selected_contest['draftGroupId'].astype('int')

    
    return selected_contest[['contestKey', 'draftGroupId', 'date', 'entryFee', 'name', 'slate', 'dff_slate', 'roto_slate', 'Game Info', 'game_id', 'game_type', 'game_num', 'away_score', 'home_score']]


# %%
# Build contest guides from subset_df (present contests)
def contest_guide(game_df, subset_df, contestKey):  
    # Copy game_df 
    game_df_copy = game_df.copy()
    # Convert date to int
    game_df_copy['date'] = game_df_copy['date'].astype(int)

    # Selected contest
    selected_contest = subset_df.query(f'contestKey == {contestKey}').reset_index(drop=True)

    # Identify slate name (Early, Afternoon, Night, Late Night, All)
    selected_contest['slate'] = selected_contest['Name'].apply(pick_slate)   
    
    # Extract date and slate name
    date = selected_contest['date'][0]
    slate = selected_contest['slate'][0]


    # Identify slate IDs
    # DFF
    # Can be missing, might need to use date-based slates for older records
    try:
        # Read in slates
        dff_slates = pd.read_csv(os.path.join(baseball_path, "A08. Projections", "1. DFF", "1. Slates", f"DFF Slates {int(date)}.csv"))

        # Identify slate ID
        slateID = dff_slates.loc[(dff_slates['date'] == date) & (dff_slates['Slate Type'] == slate), 'URL'].values[0]

        # Make it an integer, if possible
        try:
            slateID = int(slateID)
        except:
            pass
    except:
        slateID = np.nan

        
    # Assign DFF slate
    selected_contest['dff_slate'] = slateID
    
    # RotoWire
    # Shouldn't really be missing, but allow for it.
    try:
        # Read in Roto slates
        roto_slates = pd.read_csv(os.path.join(baseball_path, "A08. Projections", "2. RotoWire", "1. Slates", f"RotoWire Slates {int(date)}.csv"))

        # Identify slate ID
        slateID = roto_slates.loc[(roto_slates['date'] == date) & (roto_slates['name'] == slate), 'slateID'].values[0]
    except:
        slateID = np.nan

    # Assign RotoWire slate
    selected_contest['roto_slate'] = slateID
    
    # Determine matchups
    # Extract draftGroupId
    draftGroupId = selected_contest['draftGroupId'][0]
    # Read in draftable players
    draftables = pd.read_csv(os.path.join(baseball_path, "A09. DraftKings", "2. Draftables", f'Draftables {int(draftGroupId)}.csv'), encoding='iso-8859-1')
    # Identify matchups
    slate_matchups = draftables[['Game Info', 'draftGroupId']].drop_duplicates('Game Info', keep='first')

    # Merge matchups onto contest
    selected_contest = selected_contest.merge(slate_matchups, on='draftGroupId', how='inner')
    
    # Identify away team
    selected_contest['DKTEAM'] = selected_contest['Game Info'].str.split("@", expand=True)[0]
    selected_contest['BBREFTEAM'] = selected_contest['DKTEAM'].map(team_dict)
    
    # Merge with game_df_copy for more game information (game_id, in particular)
    selected_contest = selected_contest.merge(game_df_copy[['date', 'away_team', 'game_id', 'game_type', 'status', 'game_num', 'away_score', 'home_score']], left_on=['BBREFTEAM', 'date'], right_on=['away_team', 'date'], how='inner')

    # Handle doubleheaders
    # If there are multiple instances of a team, we want to keep the first if it's an early slate or the second if it's a later slate.
    if slate in ['Early', 'Afternoon']:
        selected_contest.drop_duplicates('DKTEAM', keep='first', inplace=True)
    else:
        selected_contest.drop_duplicates('DKTEAM', keep='last', inplace=True)
        
    selected_contest['date'] = selected_contest['date'].astype('int')
    selected_contest['draftGroupId'] = selected_contest['draftGroupId'].astype('int')

    # Rename to match previous naming conventions from when guides were built using Contest history, not subset_df
    selected_contest.rename(columns={'Name':'name', 'Entry Fee': 'entryFee'}, inplace=True)

    
    return selected_contest[['contestKey', 'draftGroupId', 'date', 'entryFee', 'name', 'slate', 'dff_slate', 'roto_slate', 'Game Info', 'game_id', 'game_type', 'game_num', 'away_score', 'home_score']]


# %%
__all__ = [name for name in globals() if not name.startswith("_")]