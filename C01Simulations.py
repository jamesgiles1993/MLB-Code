# %%
from U01Imports import *
from U02Functions import *
from U03Classes import *
from U05Models import *

# %%
# Creates batting order dataframe from MLB API
def create_order_api(date, team, game_id):
    # Read in MLB API Batting Order CSV
    order_api_df = pd.read_csv(os.path.join(baseball_path, "A05. Rosters", "1. Batting Orders", f"Batting Orders {date}", f"Batting Order {team} {game_id}.csv"), encoding='iso-8859-1')

    # Clean and create new columns
    order_api_df.sort_values('order', ascending=True, inplace=True)
    order_api_df['batting_order'] = order_api_df['order'] // 100
    order_api_df.drop_duplicates(subset=['batting_order'], inplace=True, keep='first')
    order_api_df.dropna(subset='batting_order', inplace=True)
    order_api_df['batting_order'] = order_api_df['batting_order'].astype(int)
    order_api_df['confirmed'] = "Y"
    # Keep relevant columns
    order_api_df = order_api_df[['id', 'confirmed', 'batting_order']].reset_index(drop=True)
    # Confirm batting_order adds up to 45
    if order_api_df['batting_order'].sum() != 45:
        print(f"{team} MLB API batting orders do not add up to 45")


    return order_api_df


# %%
# Creates batting order dataframe from Baseball Monster projected lineups
def create_order_bm(daily_order_bm_df, team, game_num):
    if daily_order_bm_df is None:
        order_bm_df = None
        print("Missing Baseball Monster order.")
        return order_bm_df
        
    # Baseball Monster
    order_bm_df = daily_order_bm_df[(daily_order_bm_df['BBREFTEAM'] == team) & (daily_order_bm_df['game_number'] == game_num)][['id', 'confirmed', 'batting_order']]
    # Clean and keep only batters
    order_bm_df['batting_order'] = pd.to_numeric(order_bm_df['batting_order'], errors='coerce')
    order_bm_df = order_bm_df.dropna(subset=['batting_order']).reset_index(drop=True)
    order_bm_df['batting_order'] = order_bm_df['batting_order'].astype(int)
    # Confirm batting_order adds up to 45
    if order_bm_df['batting_order'].sum() != 45:
        print(f"{team} Baseball Monster batting orders do not add up to 45")
    
    
    return order_bm_df


# %%
# Creates batting order dataframe from RotoGrinders projected lineups
def create_order_rg(projected_lineup_df, team, game_num):
    if projected_lineup_df is None:
        order_rg_df = None
        print("Missing RotoGrinders order.")
        return order_rg_df

     # Generate compatible team abbreviation
    projected_lineup_df['BBREFTEAM'] = projected_lineup_df['TeamCode'].map(team_dict)

    # Subset for current game
    order_rg_df = projected_lineup_df[(projected_lineup_df['BBREFTEAM'] == team) & (projected_lineup_df['game_number'] == game_num)][['Name', 'confirmed', 'batting_order']]
    
    # Clean and keep only batters
    order_rg_df['batting_order'] = pd.to_numeric(order_rg_df['batting_order'], errors='coerce')
    order_rg_df = order_rg_df.dropna(subset=['batting_order']).reset_index(drop=True)
    order_rg_df['batting_order'] = order_rg_df['batting_order'].astype(int)
    # Confirm batting_order adds up to 45
    if order_rg_df['batting_order'].sum() != 45:
        print(f"{team} RotoGrinders batting orders do not add up to 45")

    
    return order_rg_df


# %%
# Impute missing batting orders as a last resort
def fill_missing_batting_order(df):
    # Identify missing batting order numbers
    all_orders = set(range(1, 10))
    existing_orders = set(df['batting_order'].dropna().unique())
    missing_orders = sorted(all_orders - existing_orders)

    # Filter rows with missing batting_order and sort them
    missing_rows = df[df['batting_order'].isna()].copy()
    missing_rows = missing_rows.sort_values(by=['pa_b_long_r', 'b1_b_long_r'], ascending=False)

    # Assign missing numbers to sorted rows sequentially
    for idx, missing_order in zip(missing_rows.index, missing_orders):
        df.loc[idx, 'batting_order'] = missing_order

    df.sort_values('batting_order', ascending=True, inplace=True)

    
    return df


# %%
# Imputation Option 1 - Steamer
def impute_batters(batter_df, impute_batter_stats):
    # Assume imputed if missing
    batter_df['imp_b_l'] = batter_df['imp_b_l'].fillna(1)
    batter_df['imp_b_r'] = batter_df['imp_b_r'].fillna(1)
    
    ### Vs. RHP
    # Create is lefty dummy (this will include switch hitters against righties)
    batter_df['b_L'] = (batter_df['batSide'] != 'Right').astype('int')
    # Vs. RHP
    batter_df['p_L'] = 0    
    
    # Impute
    try:
        prediction = impute_batter_stats.predict(batter_df.loc[batter_df['imp_b_r'] == 1, batter_stats_fg_imp])
    except:
        prediction = None
        # print("No batter imputations vs RHP")
    # Impute missing values in pitcher_stats with the predicted values
    batter_df.loc[batter_df['imp_b_r'] == 1, batter_stats_r] = prediction
    
    
    ### Vs. LHP
    # Create is lefty dummy (this will not include switch hitters against righties)
    batter_df['b_L'] = (batter_df['batSide'] == 'Left').astype('int')
    # Vs. RHP
    batter_df['p_L'] = 1  
    
    # Impute
    try:
        prediction = impute_batter_stats.predict(batter_df.loc[batter_df['imp_b_l'] == 1, batter_stats_fg_imp])
    except:
        prediction = None
        # print("No batter imputations vs LHP")
    # Impute missing values in pitcher_stats with the predicted values
    batter_df.loc[batter_df['imp_b_l'] == 1, batter_stats_l] = prediction
    
    # Fill in missings
    batter_df[batter_stats_l] = batter_df[batter_stats_l].fillna(0)
    batter_df[batter_stats_r] = batter_df[batter_stats_r].fillna(0)

    batter_df[batter_stats_fg] = batter_df[batter_stats_fg].fillna(0)
    
    batter_df = batter_df.fillna(0)

    
    return batter_df


# %%
# Imputation Option 1 - Steamer
def impute_pitchers(pitcher_df, impute_pitcher_stats):
    # Assume imputed if missing
    pitcher_df['imp_p_l'] = pitcher_df['imp_p_l'].fillna(1)
    pitcher_df['imp_p_r'] = pitcher_df['imp_p_r'].fillna(1)

    
    ### Vs. RHB
    # Create is lefty dummy 
    pitcher_df['p_L'] = (pitcher_df['pitchHand'] == 'Left').astype('int')
    # Vs. RHB
    pitcher_df['b_L'] = 0    
    
    # Impute
    try:
        prediction = impute_pitcher_stats.predict(pitcher_df.loc[pitcher_df['imp_p_r'] == 1, pitcher_stats_fg_imp])
    except:
        prediction = None
        # print("No pitcher imputations vs RHB")
    # Impute missing values in pitcher_stats with the predicted values
    pitcher_df.loc[pitcher_df['imp_p_r'] == 1, pitcher_stats_r] = prediction

    
    ### Vs. LHB
    # Create is lefty dummy 
    pitcher_df['p_L'] = (pitcher_df['pitchHand'] == 'Left').astype('int')
    # Vs. RHB
    pitcher_df['b_L'] = 1  
      
    # Impute
    try:
        prediction = impute_pitcher_stats.predict(pitcher_df.loc[pitcher_df['imp_p_l'] == 1, pitcher_stats_fg_imp])
    except:
        prediction = None
        # print("No pitcher imputations vs LHB")        
    # Impute missing values in pitcher_stats with the predicted values
    pitcher_df.loc[pitcher_df['imp_p_l'] == 1, pitcher_stats_l] = prediction
    
    # Fill in missings
    pitcher_df[pitcher_stats_l] = pitcher_df[pitcher_stats_l].fillna(0)
    pitcher_df[pitcher_stats_r] = pitcher_df[pitcher_stats_r].fillna(0)

    pitcher_df[pitcher_stats_fg] = pitcher_df[pitcher_stats_fg].fillna(0)
    
    pitcher_df = pitcher_df.fillna(0)

    
    return pitcher_df


# %%
# Imputation Option 2 - Middle
def impute_batters2(batter_df, batter_imputations_model): 
    # Assume imputed if missing
    batter_df['imp_b_l'] = batter_df['imp_b_l'].fillna(1)
    batter_df['imp_b_r'] = batter_df['imp_b_r'].fillna(1)
    
    # Fill in missings
    batter_df[batter_stats_l] = batter_df[batter_stats_l].fillna(0)
    batter_df[batter_stats_r] = batter_df[batter_stats_r].fillna(0)
    batter_df[['pa_b_l', 'pa_b_r']].fillna(0, inplace=True)
    
    # Take weighted average of existing values and 0 
    # This can be simplified but I want to spell it out for clarity
    for col in batter_stats_l:
        batter_df[col] = (batter_df[col] * batter_df['pa_b_l'] + 0.0 * (50 - batter_df['pa_b_l'])) / 50
    for col in batter_stats_r:
        batter_df[col] = (batter_df[col] * batter_df['pa_b_r'] + 0.0 * (50 - batter_df['pa_b_r'])) / 50


    batter_df[batter_stats_fg] = batter_df[batter_stats_fg].fillna(0)
    
    # If still missing, fill with 0
    batter_df = batter_df.fillna(0)


    return batter_df


# %%
# Imputation Option 2 - Middle
def impute_pitchers2(pitcher_df, pitcher_imputations_model): 
    # Assume imputed if missing
    pitcher_df['imp_p_l'] = pitcher_df['imp_p_l'].fillna(1)
    pitcher_df['imp_p_r'] = pitcher_df['imp_p_r'].fillna(1)
    
    # Fill in missings
    pitcher_df[pitcher_stats_l].fillna(0.0, inplace=True)
    pitcher_df[pitcher_stats_r].fillna(0.0, inplace=True)
    pitcher_df[['pa_p_l', 'pa_p_r']].fillna(0, inplace=True)
    
    # Take weighted average of existing values and 0 
    # This can be simplified but I want to spell it out for clarity
    for col in pitcher_stats_l:
        pitcher_df[col] = (pitcher_df[col] * pitcher_df['pa_p_l'] + 0.0 * (50-pitcher_df['pa_p_l']))/50
    for col in pitcher_stats_r:
        pitcher_df[col] = (pitcher_df[col] * pitcher_df['pa_p_r'] + 0.0 * (50-pitcher_df['pa_p_r']))/50

    pitcher_df[pitcher_stats_fg] = pitcher_df[pitcher_stats_fg].fillna(0)
    
    # If still missing, fill with 0
    pitcher_df = pitcher_df.fillna(0)


    return pitcher_df


# %%
# Imputation Option 3 - 0s
def impute_batters3(batter_df, batter_imputations_model): 
    # Assume imputed if missing
    batter_df['imp_b_l'] = batter_df['imp_b_l'].fillna(1)
    batter_df['imp_b_r'] = batter_df['imp_b_r'].fillna(1)
    
    # Replace insufficient values with 0
    batter_df.loc[batter_df['imp_b_l'] == 1, batter_stats_l] = 0
    batter_df.loc[batter_df['imp_b_r'] == 1, batter_stats_r] = 0

    # Fill in batter tendencies with averages
    batter_df.loc[(batter_df['imp_b_r'] == 1) & (batter_df['batSide'] == "Right"), ['to_left_b', 'to_left_b_long']] = -0.283467
    batter_df.loc[(batter_df['imp_b_l'] == 1) & (batter_df['batSide'] == "Left"), ['to_left_b', 'to_left_b_long']] = -0.543105
    
    batter_df.loc[(batter_df['imp_b_r'] == 1) & (batter_df['batSide'] == "Right"), ['to_middle_b', 'to_middle_b_long']] = -0.171325
    batter_df.loc[(batter_df['imp_b_l'] == 1) & (batter_df['batSide'] == "Left"), ['to_middle_b', 'to_middle_b_long']] = -0.222317
    
    batter_df.loc[(batter_df['imp_b_r'] == 1) & (batter_df['batSide'] == "Right"), ['to_right_b', 'to_right_b_long']] = -0.499793
    batter_df.loc[(batter_df['imp_b_l'] == 1) & (batter_df['batSide'] == "Left"), ['to_right_b', 'to_right_b_long']] = -0.191897
    
    # Fill in missings
    batter_df[batter_stats_l] = batter_df[batter_stats_l].fillna(0)
    batter_df[batter_stats_r] = batter_df[batter_stats_r].fillna(0)

    batter_df[batter_stats_fg] = batter_df[batter_stats_fg].fillna(0)
  
    
    return batter_df

# %%
# Imputation Option 3 - 0s
def impute_pitchers3(pitcher_df, pitcher_imputations_model): 
    # Assume imputed if missing
    pitcher_df['imp_p_l'] = pitcher_df['imp_p_l'].fillna(1)
    pitcher_df['imp_p_r'] = pitcher_df['imp_p_r'].fillna(1)
    
    # Replace insufficient values with 0
    pitcher_df.loc[pitcher_df['imp_p_l'] == 1, pitcher_stats_l] = 0
    pitcher_df.loc[pitcher_df['imp_p_r'] == 1, pitcher_stats_r] = 0

    # Fill in pitcher tendencies with averages
    pitcher_df.loc[(pitcher_df['imp_p_r'] == 1) & (pitcher_df['pitchHand'] == "Right"), ['to_left_p', 'to_left_p_long']] = -0.399969
    pitcher_df.loc[(pitcher_df['imp_p_l'] == 1) & (pitcher_df['pitchHand'] == "Left"), ['to_left_p', 'to_left_p_long']] = -0.331084
    
    pitcher_df.loc[(pitcher_df['imp_p_r'] == 1) & (pitcher_df['pitchHand'] == "Right"), ['to_middle_p', 'to_middle_p_long']] = -0.188469
    pitcher_df.loc[(pitcher_df['imp_p_l'] == 1) & (pitcher_df['pitchHand'] == "Left"), ['to_middle_p', 'to_middle_p_long']] = -0.186767
    
    pitcher_df.loc[(pitcher_df['imp_p_r'] == 1) & (pitcher_df['pitchHand'] == "Right"), ['to_right_p', 'to_right_p_long']] = -0.341691
    pitcher_df.loc[(pitcher_df['imp_p_l'] == 1) & (pitcher_df['pitchHand'] == "Left"), ['to_right_p', 'to_right_p_long']] = -0.423187
        
    # Fill in missings
    pitcher_df[pitcher_stats_l] = pitcher_df[pitcher_stats_l].fillna(0)
    pitcher_df[pitcher_stats_r] = pitcher_df[pitcher_stats_r].fillna(0)
    
    pitcher_df[pitcher_stats_fg] = pitcher_df[pitcher_stats_fg].fillna(0)
    

    return pitcher_df

# %%
# Create batter objects
def create_batter_objects(batter_df, order_df, scale_batter_stats, scale_batter_stats_steamer, impute_batter_stats):
    # Merge on id, where possible (MLB API, Baseball Monster (deprecated))
    if order_df is not None and "id" in order_df:
        batter_df = pd.merge(batter_df, order_df, on=['id'], how='left')
    # Otherwise, use Name (RotoGrinders)
    else:
        print("Using RotoGrinders Projected Lineups")
        # take only the 9 hitters in order_df
        order_names = order_df['Name'].tolist()
        
        # build a dict of best matches between order_df.Name and batter_df.fullName
        mapping = {}
        for lineup_name in order_names:
            match = process.extractOne(lineup_name, batter_df['fullName'])
            if match:  # (best_name, score)
                mapping[match[0]] = lineup_name
        
        # filter batter_df down to matched names only
        batter_df['Name_match'] = batter_df['fullName'].map(mapping)
        
        batter_df = pd.merge(batter_df, order_df[['Name', 'confirmed', 'batting_order']], left_on='Name_match', right_on='Name', how='left')
    
    # Fill in missing batting orders, if necessary
    if batter_df['batting_order'].sum() != 45:
        print("Batting orders: imputed")
        batter_df = fill_missing_batting_order(batter_df)

    # Keep starting batters
    batter_df = batter_df[~batter_df['batting_order'].isna()]

    ### Scale stats
    ## Model inputs
    batter_df.rename(columns=dict(zip(batter_stats_l, batter_inputs)), inplace=True)
    batter_df[batter_inputs] = scale_batter_stats.transform(batter_df[batter_inputs])
    batter_df.rename(columns=dict(zip(batter_inputs, batter_stats_l)), inplace=True)

    batter_df.rename(columns=dict(zip(batter_stats_r, batter_inputs)), inplace=True)
    batter_df[batter_inputs] = scale_batter_stats.transform(batter_df[batter_inputs])
    batter_df.rename(columns=dict(zip(batter_inputs, batter_stats_r)), inplace=True)

    ## Steamer inpts
    batter_df[batter_stats_fg] = scale_batter_stats_steamer.transform(batter_df[batter_stats_fg])

    ### Impute stats
    batter_df = impute_batters3(batter_df, impute_batter_stats)

    ### Create player objects
    # Lists of player objects, by Away/Home status and position group
    Batters = []

    # Batters
    for _, row in batter_df.iterrows():
        batter_data = {attr: row[attr] for attr in batter_columns + ['confirmed']}
        Batters.append(Batter(**batter_data))


    return Batters


# %%
# Create pitcher objects
def create_pitcher_objects(pitcher_df, scale_pitcher_stats, scale_pitcher_stats_steamer, impute_pitcher_stats):
    # Drop if missing Leverage
    pitcher_df.dropna(subset=['Leverage'], inplace=True)
    
    # Ensure at least one pitcher at each Leverage
    if 1 not in pitcher_df['Leverage'].values:
        pitcher_df.loc[0, 'Leverage'] = 1
    if 2 not in pitcher_df['Leverage'].values:
        pitcher_df.loc[1, 'Leverage'] = 2
    if 3 not in pitcher_df['Leverage'].values:
        pitcher_df.loc[len(pitcher_df) - 2, 'Leverage'] = 3
    if 4 not in pitcher_df['Leverage'].values:
        pitcher_df.loc[len(pitcher_df) - 1, 'Leverage'] = 4
        
    
    # Assign IP_start if missing
    pitcher_df['IP_start'] = np.where((pitcher_df['IP_start'] < 1) | (pd.isna(pitcher_df['IP_start'])), 4, pitcher_df['IP_start'])

    # Assign relief_IP if missing
    # This is necessary because relievers with empty relief_IP may break the code (won't be able to randomly select any pitchers)
    # A better solution is likely possible, but this is only really going to affect early season data when steamer is wonky
    pitcher_df['relief_IP'] = pitcher_df['relief_IP'].fillna(1)

    
    ### Scale stats
    ## Model inputs
    pitcher_df.rename(columns=dict(zip(pitcher_stats_l, pitcher_inputs)), inplace=True)
    pitcher_df[pitcher_inputs] = scale_pitcher_stats.transform(pitcher_df[pitcher_inputs])
    pitcher_df.rename(columns=dict(zip(pitcher_inputs, pitcher_stats_l)), inplace=True)
    
    pitcher_df.rename(columns=dict(zip(pitcher_stats_r, pitcher_inputs)), inplace=True)
    pitcher_df[pitcher_inputs] = scale_pitcher_stats.transform(pitcher_df[pitcher_inputs])
    pitcher_df.rename(columns=dict(zip(pitcher_inputs, pitcher_stats_r)), inplace=True)
        
    ## Steamer inputs
    pitcher_df[pitcher_stats_fg] = scale_pitcher_stats_steamer.transform(pitcher_df[pitcher_stats_fg])
    
    ### Impute stats
    pitcher_df = impute_pitchers3(pitcher_df, impute_pitcher_stats)
    
    ### Create player objects
    # Lists of player objects, by Away/Home status and position group
    Pitchers = []
    for _, row in pitcher_df.iterrows():
        pitcher_data = {attr: row[attr] for attr in pitcher_columns}
        Pitchers.append(Pitcher(**pitcher_data))
        
    
    return Pitchers


# %%
# Determine if pull occurs for starting pitchers
def determine_pull(game, predict_pulls):
    # Batter vs pitcher score
    if game.top_bot == "Top":        
        batter_score, pitcher_score = game.away_score, game.home_score
    else:
        batter_score, pitcher_score = game.home_score, game.away_score
    
    # Inning dummies (1–10) + special case (>=11)
    inning_dummies = [int(game.inning == i) for i in range(1, 11)]
    inning_dummies.append(int(game.inning >= 11))
    
    # Out dummies (0–2)
    out_dummies = [int(game.outs == o) for o in range(3)]
    
    # Model inputs
    inputs = np.array([
        game.pitching.faced_inning, game.pitching.reached_inning, # Inning totals
        game.pitching.faced, game.pitching.reached, game.pitching.OUT,  # Game totals
        *inning_dummies,
        *out_dummies,
        pitcher_score, batter_score,
        game.onFirst, game.onSecond, game.onThird,
        game.pitching.IP_start, 
        game.pitching.imp_p_either
    ]).reshape(1, -1)
    
    # Pull probability
    pull_prob = predict_pulls.predict_proba(inputs)[0, 1]


    return (random.random() < pull_prob)


# %%
# Determine pitcher to pitch the current half-inning
def determine_pitcher(game, opener_list):
    def choose_pitcher(team_pitchers, starter, starter_pulled_attr, team_score, opp_score, opener_list):
        starter_pulled = getattr(game, starter_pulled_attr)

        # If starter is still in the game, take him
        if not starter_pulled:
            pitcher_up = random.choice([p for p in team_pitchers if p.Leverage == 1]) if team_pitchers else None
            setattr(game, starter_pulled_attr, determine_pull(game, predict_pulls))
            
            # Pull openers after 3 innings
            if game.inning >= 3 and starter and getattr(starter, 'fullName', None) in opener_list:
                setattr(game, starter_pulled_attr, True)
                starter_pulled = True
        else:
            pitcher_up = getattr(game, f"{starter}_up", None)

        # If starter was pulled, choose relief based on leverage
        if getattr(game, starter_pulled_attr):
            pitcher_lead = team_score - opp_score
            is_top = int(game.top_bot == "Top")

            # Inning dummies
            inning_dummies = [int(game.inning == i) for i in range(1, 11)]
            inning_dummies.append(int(game.inning >= 11))

            leverage_inputs = np.array([pitcher_lead, is_top, *inning_dummies]).reshape(1, -1)
            predictions_proba = predict_leverage.predict_proba(leverage_inputs)
            leverage_df = pd.DataFrame(predictions_proba, columns=predict_leverage.classes_)

            # Choose leverage 2,3,4
            leverage_list = [leverage_df.get(l, pd.Series([0]))[0] for l in [2, 3, 4]]
            chosen_leverage = random.choices([2, 3, 4], weights=leverage_list, k=1)[0]

            setattr(game, f"{starter}_leverage", chosen_leverage)

            # Eligible pitchers at chosen leverage
            eligible_pitchers = [p for p in team_pitchers if p.Leverage == chosen_leverage]
            if not eligible_pitchers:
                # fallback to any pitcher
                eligible_pitchers = team_pitchers

            # Select pitcher weighted by relief_IP (or equal if all 0)
            weights = [p.relief_IP for p in eligible_pitchers]
            if sum(weights) == 0:
                weights = None
            pitcher_up = random.choices(eligible_pitchers, weights=weights, k=1)[0] if eligible_pitchers else None

        return pitcher_up

    # Determine scores
    batter_score, pitcher_score = (game.away_score, game.home_score) if game.top_bot == "Top" else (game.home_score, game.away_score)

    # Top of the inning
    if game.top_bot == "Top":
        game.home_pitcher_up = choose_pitcher(
            team_pitchers=game.home_pitchers,
            starter=game.home_starter,
            starter_pulled_attr='home_starter_pulled',
            team_score=game.home_score,
            opp_score=game.away_score,
            opener_list=opener_list
        )
        game.pitching = game.home_pitcher_up

    # Bottom of the inning
    elif game.top_bot == "Bot":
        game.away_pitcher_up = choose_pitcher(
            team_pitchers=game.away_pitchers,
            starter=game.away_starter,
            starter_pulled_attr='away_starter_pulled',
            team_score=game.away_score,
            opp_score=game.home_score,
            opener_list=opener_list
        )
        game.pitching = game.away_pitcher_up

    
    return game


# %%
# Determine event for current PA
def determine_event(game, park_object, wfx_adjustment=True, debug=False):
    ### Batter Attributes
    batter_inputs = ['b1_b', 'b2_b', 'b3_b', 'bb_b', 
                     'fo_b', 'go_b', 'hbp_b', 'hr_b', 
                     'lo_b', 'po_b', 'so_b',
                     'estimated_woba_using_speedangle_b', 'hard_hit_b', 'barrel_b', 
                     'iso_b', 'slg_b', 'obp_b', 'woba_b',
                     'b1_b_long', 'b2_b_long', 'b3_b_long', 'bb_b_long', 
                     'fo_b_long', 'go_b_long', 'hbp_b_long', 'hr_b_long', 
                     'lo_b_long', 'po_b_long', 'so_b_long',
                     'estimated_woba_using_speedangle_b_long', 'hard_hit_b_long', 'barrel_b_long', 
                     'iso_b_long', 'slg_b_long', 'obp_b_long', 'woba_b_long']    
    for stat in batter_inputs + ['imp_b']:
        attr_name = f'{stat}_l' if game.pitching.pitchHand == "Left" else f'{stat}_r'
        setattr(game.ab, stat, getattr(game.ab, attr_name))
    batter_inputs_pa = [getattr(game.ab, stat) for stat in batter_inputs]

    ### Pitcher Attributes
    pitcher_inputs = ['b1_p', 'b2_p', 'b3_p', 'bb_p', 
                      'fo_p', 'go_p', 'hbp_p', 'hr_p', 
                      'lo_p', 'po_p', 'so_p', 
                      'estimated_woba_using_speedangle_p', 'hard_hit_p', 'barrel_p', 
                      'iso_p', 'slg_p', 'obp_p', 'woba_p', 
                      'b1_p_long', 'b2_p_long', 'b3_p_long', 'bb_p_long', 
                      'fo_p_long', 'go_p_long', 'hbp_p_long', 'hr_p_long', 
                      'lo_p_long', 'po_p_long', 'so_p_long',
                      'estimated_woba_using_speedangle_p_long', 'hard_hit_p_long', 'barrel_p_long', 
                      'iso_p_long', 'slg_p_long', 'obp_p_long', 'woba_p_long']
    for stat in pitcher_inputs + ['imp_p']:
        lefty_batter = game.ab.batSide == "Left" or (game.ab.batSide == "Switch" and game.pitching.pitchHand == "Right")
        attr_name = f'{stat}_l' if lefty_batter else f'{stat}_r'
        setattr(game.pitching, stat, getattr(game.pitching, attr_name))
    pitcher_inputs_pa = [getattr(game.pitching, stat) for stat in pitcher_inputs]

    ### Handedness
    game.ab.b_L = int(lefty_batter)
    game.pitching.p_L = int(game.pitching.pitchHand == "Left")
    hand_inputs_pa = [game.pitching.p_L, game.ab.b_L]

    ### Imputation Status
    imp_inputs_pa = [game.ab.imp_b, game.pitching.imp_p]

    ### Starter Status
    starter = int((game.home_starter_pulled == False) if game.top_bot == "Top" else (game.away_starter_pulled == False))
    starter_inputs_pa = [starter]

    ### Cumulative Inning Inputs
    cumulative_inning_inputs = [
        game.pitching.B1_inning, game.pitching.B2_inning, game.pitching.B3_inning, game.pitching.BB_inning,
        game.pitching.FO_inning, game.pitching.GO_inning, game.pitching.HBP_inning, game.pitching.HR_inning,
        game.pitching.LO_inning, game.pitching.PO_inning, game.pitching.SO_inning,        
        game.pitching.H_inning, game.pitching.TB_inning, game.pitching.reached_inning, game.pitching.faced_inning,
        game.pitching.OUT_inning
    ]
    
    ### Cumulative Game Inputs
    cumulative_game_inputs = [
        game.pitching.B1, game.pitching.B2, game.pitching.B3, game.pitching.BB, 
        game.pitching.FO, game.pitching.GO, game.pitching.HBP, game.pitching.HR,
        game.pitching.LO, game.pitching.PO, game.pitching.SO, 
        game.pitching.H, game.pitching.TB, game.pitching.reached, game.pitching.faced,
        game.pitching.OUT
    ]

    ### Game State
    game.onFirst = int(game.on_1b is not None)
    game.onSecond = int(game.on_2b is not None)
    game.onThird = int(game.on_3b is not None)
    game.top = int(game.top_bot == "Top")
    game.score_diff = (game.away_score - game.home_score if game.top_bot == "Top" else game.home_score - game.away_score)
    pitcher_score = game.away_score if game.top_bot == "Bot" else game.home_score
    batter_score = game.away_score if game.top_bot == "Top" else game.home_score
    winning = int(batter_score > pitcher_score)
    winning_big = int(batter_score > pitcher_score + 3)
    times_faced = game.pitching.faced // 9
    game_state_inputs_pa = [game.onFirst, game.onSecond, game.onThird, game.top, game.score_diff,
                            pitcher_score, batter_score, winning, winning_big, times_faced]

    ### Inning
    for inning in range(1, 11):
        globals()[f'inning_{inning}'] = int(game.inning == inning)
    inning_11 = int(game.inning >= 11)
    inning_inputs_pa = [inning_1, inning_2, inning_3, inning_4, inning_5,
                        inning_6, inning_7, inning_8, inning_9, inning_10, inning_11]

    ### Outs
    for out in range(3):
        globals()[f'out_{out}'] = int(game.outs == out)
    out_inputs_pa = [out_0, out_1, out_2]

    ### Park/Weather Multipliers
    suffix = "_wfx_l" if game.ab.b_L else "_wfx_r"
    wfx_inputs_pa = [getattr(park_object, event + suffix) for event in events_list]

    ### Imputation x Starter
    imputed_starter_inputs_pa = [
        game.pitching.imp_p * starter,
        game.pitching.imp_p * (starter == 0),
        (game.pitching.imp_p == 0) * starter,
        (game.pitching.imp_p == 0) * (starter == 0)
    ]

    ### Steamer/FanGraphs
    batter_inputs_fg_pa = [game.ab.b1_rate, game.ab.b2_rate, game.ab.b3_rate, game.ab.hr_rate,
                           game.ab.bb_rate, game.ab.hbp_rate, game.ab.so_rate, game.ab.woba, game.ab.slg, game.ab.obp]
    pitcher_inputs_fg_pa = [game.pitching.H9, game.pitching.HR9, game.pitching.K9, game.pitching.BB9,
                            game.pitching.GBrate, game.pitching.FBrate, game.pitching.LDrate, game.pitching.SIERA]


    ### Testing:
    log_wfx_inputs_pa = [np.log(max(m, 1e-9)) for m in wfx_inputs_pa]


    inputs_pa = (batter_inputs_pa + pitcher_inputs_pa + hand_inputs_pa + imp_inputs_pa +
                 starter_inputs_pa + cumulative_inning_inputs + cumulative_game_inputs +
                 game_state_inputs_pa + inning_inputs_pa + out_inputs_pa +
                 imputed_starter_inputs_pa + batter_inputs_fg_pa + pitcher_inputs_fg_pa + log_wfx_inputs_pa)

    # Choose Event
    event = random.choices(events_list, weights=np.array(predict_all.predict_proba(np.array(inputs_pa, dtype=np.float32).reshape(1, -1))).ravel(), k=1)[0]

    # inputs_pa = (batter_inputs_pa + pitcher_inputs_pa + hand_inputs_pa + imp_inputs_pa +
    #          starter_inputs_pa + cumulative_inning_inputs + cumulative_game_inputs +
    #          game_state_inputs_pa + inning_inputs_pa + out_inputs_pa +
    #          imputed_starter_inputs_pa + batter_inputs_fg_pa + pitcher_inputs_fg_pa)
    
    # ### Testing Second model
    # # Step 1: get raw model probabilities
    # raw_probs = predict_all.predict_proba(np.array(inputs_pa, dtype=np.float32).reshape(1, -1)).ravel().tolist()
 
    # # Step 2: Create new inputs
    # interaction_inputs_pa = [r * w for r, w in zip(raw_probs, wfx_inputs_pa)]
    # logit_raw_inputs_pa = [np.log((p + 1e-9) / (1 - p + 1e-9)) for p in raw_probs]
    # log_wfx_inputs_pa = [np.log(max(m, 1e-9)) for m in wfx_inputs_pa]
    
    # # Step 3: define inputs    
    # inputs_pa_adjusted = raw_probs + wfx_inputs_pa + interaction_inputs_pa + logit_raw_inputs_pa + log_wfx_inputs_pa + imputed_starter_inputs_pa

    # # Step 4: predict again
    # adjusted_probs = predict_all_adjusted.predict_proba(np.array(inputs_pa_adjusted, dtype=np.float32).reshape(1, -1)).ravel()

    # # Step 5: choose event
    # event = random.choices(events_list, weights=adjusted_probs, k=1)[0]
    
    pa_summary = []  # for compatibility/debug (deprecated)


    return event, pa_summary


# %%
# Determine if error occurs on given event
def determine_error(game, event):
    # Event one-hot
    event_dummies = [int(event == e) for e in events_list]
    
    # Model inputs
    inputs = np.array(event_dummies + [game.onFirst, game.onSecond, game.onThird]).reshape(1, -1)
    
    # Error probability
    error_prob = predict_errors.predict_proba(inputs)[0, 1]


    return (random.random() < error_prob)


# %%
# Determine if double play occurs on given event
def determine_dp(game, event):
    # Event one-hot
    event_dummies = [int(event == e) for e in events_list]
    
    # Model inputs
    inputs = np.array(event_dummies + [game.outs, game.onFirst, game.onSecond, game.onThird]).reshape(1, -1)
    
    # DP probability
    dp_prob = predict_dp.predict_proba(inputs)[0, 1]
    

    return (random.random() < dp_prob)


# %%
# Determine out locations for given event
def determine_out_locations(game, event, error, double_play, debug):
    # Helper to compute out probability for a base
    def get_out_prob(base_flag):
        if base_flag is not None:
            input_list = [int(event == e) for e in events_list]  # event dummies
            # Base dummies: [AB, 1B, 2B, 3B]
            base_dummies = [
                1 if base_flag == "AB" else 0,
                1 if base_flag == "1B" else 0,
                1 if base_flag == "2B" else 0,
                1 if base_flag == "3B" else 0,
            ]
            model_inputs = pd.Series(input_list + base_dummies + [game.outs, game.onFirst, game.onSecond, game.onThird,
                                                                  int(error), int(double_play)]).values.reshape(1, -1)
            return predict_out_bases.predict_proba(model_inputs).tolist()[0][1]
        return 0

    # Get probabilities for AB and bases
    out_ab = get_out_prob("AB")
    out_1b = get_out_prob("1B") if game.on_1b else 0
    out_2b = get_out_prob("2B") if game.on_2b else 0
    out_3b = get_out_prob("3B") if game.on_3b else 0

    
    # Probabilities that there will be no outs
    if double_play == True:
        safe_prob = 0
    else:
        safe_prob = max(0, 1 - sum([out_ab, out_1b, out_2b, out_3b]))

    # Probability of outs by location (or of no outs)
    probabilities = [out_ab, out_1b, out_2b, out_3b, safe_prob]
    # Normalize
    probabilities = [p / sum(probabilities) for p in probabilities]

    if debug == True:
        print("Out Probabilities:", probabilities)

    
    # if sum(probabilities) == 0:  # fallback to batter out
    #     probabilities[0] = 1
    # probabilities = [p / sum(probabilities) for p in probabilities]

    # First draw
    chosen_index = random.choices(range(5), weights=probabilities)[0]
    chosen_index2 = None

    # If double play → force two outs
    if double_play:
        # Remove the chosen slot and safe option
        probabilities[chosen_index] = 0
        probabilities[4] = 0  # remove safe outcome
        if sum(probabilities) == 0:  # fallback to batter out
            probabilities[0] = 1
        probabilities = [p / sum(probabilities) for p in probabilities]
        chosen_index2 = random.choices(range(5), weights=probabilities)[0]

    # Assign outs
    out_ab = int(chosen_index == 0 or chosen_index2 == 0)
    out_1b = int(chosen_index == 1 or chosen_index2 == 1)
    out_2b = int(chosen_index == 2 or chosen_index2 == 2)
    out_3b = int(chosen_index == 3 or chosen_index2 == 3)

    
    return out_ab, out_1b, out_2b, out_3b


# %%
# Determine result of given event (where runners end up)
def determine_event_results(game, startInt, event, out_ab, out_1b, out_2b, out_3b, blocked_1b, blocked_2b, blocked_3b, error, double_play):
    # Event dummies
    event_dummies = [int(event == e) for e in events_list]

    # Starting base dummies
    start_dummies = [int(startInt == i) for i in range(4)]

    # Model inputs
    inputs = np.array(
        event_dummies + start_dummies + [
            game.outs, game.onFirst, game.onSecond, game.onThird,
            blocked_1b, blocked_2b, blocked_3b,
            out_ab, out_1b, out_2b, out_3b,
            int(error), int(double_play)
        ]
    ).reshape(1, -1)

    # Predict probabilities
    probs = predict_advances.predict_proba(inputs)[0]

    # Compute cumulative probabilities for base advancement
    cumulative = np.cumsum(probs[:4])
    cumulative[-1] = 1.0  # ensure last category is always reachable

    # Roll to determine base
    base_roll = random.random()
    if base_roll < cumulative[0]:
        return "to_1b"
    elif base_roll < cumulative[1]:
        return "to_2b"
    elif base_roll < cumulative[2]:
        return "to_3b"
    else:
        return "to_score"


# %%
# Calculate batter stats
def calculate_batter(batter, game):
    batter.FP = (
                batter.B1 * 3 +
                batter.B2 * 5 +
                batter.B3 * 8 +
                batter.HR * 10 +
                batter.RBI * 2 +
                batter.R * 2 +
                batter.BB * 2 +
                batter.HBP * 2 +
                batter.SB * 5
                )


    return batter, game

# %%
# Calculate pitcher stats
def calculate_pitcher(pitcher, game):
    # Calculate hits allowed
    pitcher.H = (pitcher.B1 + pitcher.B2 + pitcher.B3 + pitcher.HR)
    # Calculate total bases allowed
    pitcher.TB = (pitcher.B1 * 1 + pitcher.B2 * 2 + pitcher.B3 * 3 + pitcher.HR * 4)
    # Calculate batters allowed to reach
    pitcher.reached = (pitcher.B1 + pitcher.B2 + pitcher.B3 + pitcher.HR + pitcher.BB + pitcher.HBP)

    # Calculate hits allowed that inning
    pitcher.H_inning = (pitcher.B1_inning + pitcher.B2_inning + pitcher.B3_inning + pitcher.HR_inning)
    # Calculate total bases allowed that inning
    pitcher.TB_inning = (pitcher.B1_inning * 1 + pitcher.B2_inning * 2 + pitcher.B3_inning * 3 + pitcher.HR_inning * 4)
    # Calculate batters allowed to reach that inning
    pitcher.reached_inning = (pitcher.B1_inning + pitcher.B2_inning + pitcher.B3_inning + pitcher.HR_inning + pitcher.BB_inning + pitcher.HBP_inning)
    
    # If they're the winning pitcher, they get a win
    if game.winning_pitcher == pitcher:
        pitcher.W = 1
    else:
        pitcher.W = 0

    # Determine CG, CGSO, NH
    if pitcher.OUT == 27:
        pitcher.CG = 1
        if pitcher.ER == 0:
            pitcher.CGSO = 1
        if pitcher.H == 0:
            pitcher.NH = 1

    pitcher.FP = (
                pitcher.OUT * 0.75 +
                pitcher.SO * 2 +
                pitcher.W * 4 +
                pitcher.ER * -2 +
                pitcher.H * -0.6 +
                pitcher.BB * -0.6 +
                pitcher.HBP * -0.6 +
                pitcher.CG * 2.5 +
                pitcher.CGSO * 2.5 +
                pitcher.NH * 5
                )
    
        
    return pitcher, game


# %%
# Create visual for debugging
def debug_visual(game, event):    
    if game.on_1b is None:
        order_1b = 0
    else:
        order_1b = int(game.on_1b.batting_order)
    if game.on_2b is None:
        order_2b = 0
    else:
        order_2b = int(game.on_2b.batting_order)
    if game.on_3b is None:
        order_3b = 0
    else:
        order_3b = int(game.on_3b.batting_order)

    # Calculate batter stats
    game.ab, game = calculate_batter(game.ab, game)
    
    print("\n")
    print(game.top_bot, game.inning, "Outs: ", game.outs)
    print(f"       {order_2b}")
    print("    /     \\")
    print(f"   {order_3b}   {int(game.pitching.Leverage)}   {order_1b}  {game.pitching.position} {game.pitching.fullName}: {round(game.pitching.FP, 2)}")
    print("    \     /         vs.")
    print(f"       {int(game.ab.batting_order)}      {game.ab.position} {game.ab.fullName}: {game.ab.FP}  ")
    print(f"Away {game.away_score} - {game.home_score} Home")

    
    print(f"Event: {event}")


# %%
# Simulate a single plate appearance
def sim_ab(game, opener_list, park_object, wfx_adjustment, debug=False):
    
    start_time = time.time()

    # Choose plate appearance matchup
    # If it's the top of the inning
    if game.top_bot == "Top":
        # And the home starter is still in the game
        if game.home_starter_pulled == False:
            # Consider pulling them
            game = determine_pitcher(game, opener_list)
            # Note: we only assign new relief pitchers to start an inning 

        # Assign batter
        game.ab = next(batter for batter in game.away_batters if batter.batting_order == game.away_order)
        # Assign pitcher to the batter
        game.ab.pitcher = game.pitching
    
    # If it's the bottom of the inning
    if game.top_bot == "Bot":
        # And the away starter is still in the game
        if game.away_starter_pulled == False:
            # Consider pulling them
            game = determine_pitcher(game, opener_list)
        # Note: we only assign new relief pitchers to start an inning

        # Assign batter
        game.ab = next(batter for batter in game.home_batters if batter.batting_order == game.home_order)
        # Assign pitcher to the batter
        game.ab.pitcher = game.pitching    

    
    # Add PA for batter
    game.ab.PA += 1
    game.pitching.PA += 1
    
    # Set the zombie (will be last guy up)
    if game.top_bot == "Top":
        game.away_zombie = game.ab
    else:
        game.home_zombie = game.ab       
 
    # print("Prep", time.time() - start_time)

    # Calculate probabilities
    start_time = time.time()
    event, pa_summary = determine_event(game, park_object, wfx_adjustment, debug)
    # print("Determine Event", time.time() - start_time)
    
    # Debug visual
    if debug == True:
        debug_visual(game, event)
        
    # Carry out event 
    if event == "b1":
        game.ab.B1 += 1
        game.pitching.B1 += 1
        game.pitching.B1_inning += 1
    elif event == "b2":
        game.ab.B2 += 1
        game.pitching.B2 += 1
        game.pitching.B2_inning += 1
    elif event == "b3":
        game.ab.B3 += 1
        game.pitching.B3 += 1
        game.pitching.B3_inning += 1
    elif event == "hr":
        game.ab.HR += 1
        game.pitching.HR += 1
        game.pitching.HR_inning += 1
    elif event == "bb":
        game.ab.BB += 1
        game.pitching.BB += 1
        game.pitching.BB_inning += 1
    elif event == "hbp":
        game.ab.HBP += 1
        game.pitching.HBP += 1
        game.pitching.HBP_inning += 1
    elif event == "so":
        game.pitching.SO += 1
        game.pitching.SO_inning += 1
    elif event == "fo":
        game.pitching.FO += 1
        game.pitching.FO_inning += 1
    elif event == "go":
        game.pitching.GO += 1
        game.pitching.GO_inning += 1
    elif event == "lo":
        game.pitching.LO += 1
        game.pitching.LO_inning += 1
    elif event == "po":
        game.pitching.PO += 1
        game.pitching.PO_inning += 1
        
    # Assume run will be charged to pitcher 
    game.ab.charged = 1
        
    # Determine if there's an error on the play
    error = determine_error(game, event)

    # 
    if debug == True and error == True:
        print ("There is an error.")
    
    # If there is an error
    if error == True:
        # print("There's an error!")
        # And if the event was supposed to be an out
        if event in ['so', 'go', 'fo', 'lo', 'po']:
            # The batter will not be charged to the pitcher 
            game.ab.charged = 0
        
    # If there's an error with two outs and the event would have ended the inning (been an out), all future runs are unearned
    if error == True and event in ['so', 'go', 'fo', 'lo', 'po'] and game.outs == 2:
        game.error_extended = True
        # print("An error has extended the inning.")
    
    # Set charged to pitcher variable for each base runner to 0
    if game.error_extended == True:
        if game.on_3b is not None:
            game.on_3b.charged = 0
        if game.on_2b is not None:
            game.on_2b.charged = 0
        if game.on_1b is not None:
            game.on_1b.charged = 0
        game.ab.charged = 0

    ### TESTING:
    # Aggressive unearned runs: If there's an error in an inning, every runner on base will not be charged (even if they might have scored anyway)
    # Note that if there's an error with less than two outs, baserunners post-error could still be earned.
    if error == True:
        if game.on_3b is not None:
            game.on_3b.charged = 0
        if game.on_2b is not None:
            game.on_2b.charged = 0
        if game.on_1b is not None:
            game.on_1b.charged = 0
        game.ab.charged = 0      
    ### TESTING ENDS

    
    # Determine if there's a double play
    double_play = determine_dp(game, event)
    if debug == True and double_play == True:
        print("There's a double play!")
    
    # Determine where outs occur
    out_ab, out_1b, out_2b, out_3b = determine_out_locations(game, event, error, double_play, debug)
    if debug == True:
        print("Out Locations:", out_ab, out_1b, out_2b, out_3b)
    
    # Outs on play
    outs_on_play = out_ab + out_1b + out_2b + out_3b

    # Runs on play
    runs = 0 

    start_time = time.time()
    # If the inning isn't over (or if it is over, but it was on a hit/bb/hbp so we still have to determine whether runners scored)
    if (game.outs + outs_on_play < 3) or (event in ['b1', 'b2', 'b3', 'hr', 'bb', 'hbp']):
        # Determine where the runners go
        # Runner on 3B
        # If they're out
        if out_3b == 1:
            # Assign out to base variable
            base_3b = "out"
        # If not but they exist
        elif game.on_3b is not None:
            blocked_1b = 0
            blocked_2b = 0
            blocked_3b = 0
            # Figure out their base
            base_3b = determine_event_results(game, 3, event, out_ab, out_1b, out_2b, out_3b, blocked_1b, blocked_2b, blocked_3b, int(error), int(double_play))
        else:
            base_3b = "N/A"

        # Runner on 2B
        # If they're out
        if out_2b == 1:
            # Assign out to base variable
            base_2b = "out"
        # If not but they exist
        elif game.on_2b is not None:
            blocked_1b = 0
            blocked_2b = 0
            blocked_3b = int(base_3b == "to_3b")
            # Figure out their base
            base_2b = determine_event_results(game, 2, event, out_ab, out_1b, out_2b, out_3b, blocked_1b, blocked_2b, blocked_3b, int(error), int(double_play))
        else:
            base_2b = "N/A"

        # Runner on 1B
        # If they're out
        if out_1b == 1:
            # Assign out to base variable
            base_1b = "out"
        # If not but they exist
        elif game.on_1b is not None:
            blocked_1b = 0
            blocked_2b = int(base_2b == "to_2b")
            blocked_3b = int(base_3b == "to_3b" or base_2b == "to_3b")
            # Figure out their base
            base_1b = determine_event_results(game, 1, event, out_ab, out_1b, out_2b, out_3b, blocked_1b, blocked_2b, blocked_3b, int(error), int(double_play))
        else:
            base_1b = "N/A"

        # AB
        # If they're out
        if out_ab == 1:
            # Assign out to base variable
            base_ab = "out"
        # If not but they exist
        elif game.ab is not None:
            blocked_1b = int(base_1b == "to_1b")
            blocked_2b = int(base_2b == "to_2b" or base_1b == "to_2b")
            blocked_3b = int(base_3b == "to_3b" or base_2b == "to_3b" or base_1b == "to_3b")
            # Figure out their base
            base_ab = determine_event_results(game, 0, event, out_ab, out_1b, out_2b, out_3b, blocked_1b, blocked_2b, blocked_3b, int(error), int(double_play))
        else:
            base_ab = "N/A"

        if debug == True:
            print(f"Advancements:  AB: {base_ab}, 1B: {base_1b}, 2B: {base_2b}, 3B: {base_3b}")
            print("----------------------------------------------------")
            
        # Move Runners:
        # Runner on 3B
        if game.on_3b is not None:
            if base_3b == "to_score":
                game.on_3b.R += 1
                game.on_3b.pitcher.ER += (1 * (1-int(error)) * game.on_3b.charged) # Not an ER if event is error, player reached on error, or inning would be over if not for error.
                game.on_3b.pitcher.ER_inning += (1 * (1-int(error)) * game.on_3b.charged) # Not an ER if event is error, player reached on error, or inning would be over if not for error.
                game.ab.RBI += 1 * (1-int(error)) * (1-int(double_play))
                game.on_3b.pitcher.R += 1
                runs += 1
                game.on_3b = None
            elif base_3b == "out":
                game.on_3b = None
    
        # Runner on 2B
        if game.on_2b is not None:
            if base_2b == "to_3b":
                game.on_3b = game.on_2b
                game.on_2b = None
            elif base_2b == "to_score":
                game.on_2b.R += 1
                game.on_2b.pitcher.ER += (1 * (1-int(error)) * game.on_2b.charged)
                game.on_2b.pitcher.ER_inning += (1 * (1-int(error)) * game.on_2b.charged)
                game.ab.RBI += 1 * (1-int(error)) * (1-int(double_play))
                game.on_2b.pitcher.R += 1
                runs += 1
                game.on_2b = None
            elif base_2b == "out":
                game.on_2b = None
    
        # Runner on 1B
        if game.on_1b is not None:
            if base_1b == "to_2b":
                game.on_2b = game.on_1b
                game.on_1b = None
            elif base_1b == "to_3b":
                game.on_3b = game.on_1b
                game.on_1b = None
            elif base_1b == "to_score":
                game.on_1b.R += 1
                game.on_1b.pitcher.ER += (1 * (1-int(error)) * game.on_1b.charged)
                game.on_1b.pitcher.ER_inning += (1 * (1-int(error)) * game.on_1b.charged)
                game.ab.RBI += 1 * (1-int(error)) * (1-int(double_play))
                game.on_1b.pitcher.R += 1 
                runs += 1
                game.on_1b = None
            elif base_1b == "out":
                game.on_1b = None
                
        # AB
        if game.ab is not None:
            if base_ab == "to_1b":
                game.on_1b = game.ab
            elif base_ab == "to_2b":
                game.on_2b = game.ab
            elif base_ab == "to_3b":
                game.on_3b = game.ab
            elif base_ab == "to_score":
                game.ab.R += 1
                game.ab.pitcher.ER += (1 * (1-int(error)) * game.ab.charged)
                game.ab.pitcher.ER_inning += (1 * (1-int(error)) * game.ab.charged)
                game.ab.RBI += 1 * (1-int(error)) * (1-int(double_play))
                game.ab.pitcher.R += 1
                runs += 1
            elif base_ab == "out":
                pass
    
    # Determine bases
    game.onThird = 1 if game.on_3b is not None else 0
    game.onSecond = 1 if game.on_2b is not None else 0
    game.onFirst = 1 if game.on_1b is not None else 0
    
    # Add outs on play
    game.outs += outs_on_play
    game.pitching.OUT += outs_on_play
    game.pitching.OUT_inning += outs_on_play
                
    # Add runs
    # Runs scored
    if game.top_bot == "Top":
        game.away_score += runs
    else:
        game.home_score += runs
        
    # Add to number of batters faced
    game.pitching.faced += 1
    game.pitching.faced_inning += 1

    # Update pitching stats
    game.pitching, game = calculate_pitcher(game.pitching, game)


    ### Determine Next Batter
    # Away
    if game.top_bot == "Top":
        game.away_order += 1
        if game.away_order == 10:
            game.away_order = 1

    # Home
    else:
        game.home_order += 1
        if game.home_order == 10:
            game.home_order = 1

    # Plate appearance summary:
    pa_summary = [event] + pa_summary


    return game


# %%
# Simulate a single inning
def sim_inning(game, opener_list, park_object, innings, wfx_adjustment=True, debug=False):
    # Reset inning
    game.outs = 0
    game.on_1b = None
    game.on_2b = None
    game.on_3b = None
    game.onFirst = 0
    game.onSecond = 0
    game.onThird = 0
    game.error_extended = False

    # Set zombie runner for extra innings
    if game.inning >= 10:
        if game.top_bot == "Top":
            game.on_2b = game.away_zombie
        else:
            game.on_2b = game.home_zombie
        game.on_2b.charged = 0

    # Assign pitcher for inning start
    if game.top_bot == "Top":
        game.pitching = game.home_pitcher_up
        if game.home_starter_pulled:
            game = determine_pitcher(game, opener_list)
    else:
        game.pitching = game.away_pitcher_up
        if game.away_starter_pulled:
            game = determine_pitcher(game, opener_list)

    # Clear inning-specific stats
    for stat in [
        "HBP_inning", "BB_inning", "B1_inning", "B2_inning", "B3_inning", "HR_inning",
        "SO_inning", "PO_inning", "GO_inning", "LO_inning", "FO_inning",
        "H_inning", "faced_inning", "reached_inning", "TB_inning", "OUT_inning"
    ]:
        setattr(game.pitching, stat, 0)

    # Loop for each PA
    while game.outs < 3:        
        ### Steals
        # Third base
        # If third is empty and second is not
        if game.on_3b is None and game.on_2b is not None:
            # Steal model inputs
            sba_imp = game.on_2b.sba / game.on_2b.sbo
            sb_imp = game.on_2b.sb / game.on_2b.sba
            steal_input_list = [game.outs, sba_imp, sb_imp] 
            model_inputs = pd.Series(steal_input_list).values.reshape(1,-1)
            
            # Stolen base attempt roll
            sba_3b_roll = random.random()
            
            # Attempt rate
            sba_3b_rate = predict_sba_3b.predict_proba(model_inputs).tolist()[0][1]
            if debug == True:
                print(f"3B Attempt Rate: {sba_3b_rate}")
            
            # If the roll is less than the attempt rate
            if sba_3b_roll < sba_3b_rate:
                # They attempt to steal 3B
                # Stolen base success roll
                sb_3b_roll = random.random()
                
                # Success rate
                sb_3b_rate = predict_sb_3b.predict_proba(model_inputs).tolist()[0][1]
                if debug == True:
                    print(f"3B Success Rate: {sb_3b_rate}")
                
                # If the roll is less than the success rate
                if sb_3b_roll < sb_3b_rate:
                    # They steal
                    if debug == True:
                        print("Stole 3B")
                    game.on_2b.SB += 1
                    game.on_3b = game.on_2b
                    game.on_2b = None
                    
                # Else
                else:
                    # They're out
                    if debug == True:
                        print("Caught stealing 3B")
                    game.on_2b = None
                    game.pitching.OUT +=1
                    game.pitching.OUT_inning
                    game.outs += 1 
                    
                    # Check outs as this might end the inning
                    if game.outs == 3:
                        break

        # Second base
        # If second is empty and first is not
        if game.on_2b is None and game.on_1b is not None:
            # Steal model inputs
            sba_imp = game.on_1b.sba / game.on_1b.sbo
            sb_imp = game.on_1b.sb / game.on_1b.sba
            steal_input_list = [game.outs, sba_imp, sb_imp]
            if debug == True:
                print("Steal INPUT list", steal_input_list)
            model_inputs = pd.Series(steal_input_list).values.reshape(1,-1)
            
            # Stolen base attempt roll
            sba_2b_roll = random.random()
            
            # Attempt rate
            sba_2b_rate = predict_sba_2b.predict_proba(model_inputs).tolist()[0][1]
            if debug == True:
                print(f"2B Attempt Rate: {sba_2b_rate}")         
            
            # If the roll is less than the attempt rate
            if sba_2b_roll < sba_2b_rate:
                # They attempt to steal 2B
        
                # Stolen base success roll
                sb_2b_roll = random.random()
                
                # Success rate
                sb_2b_rate = predict_sb_2b.predict_proba(model_inputs).tolist()[0][1]
                if debug == True:
                    print(f"2B Success Rate: {sb_2b_rate}")
                
                # If the roll is less than the success rate
                if sb_2b_roll < sb_2b_rate:
                    # They succeed
                    if debug == True:
                        print("Stole 2B")
                    game.on_1b.SB += 1
                    game.on_2b = game.on_1b
                    game.on_1b = None
                    
                # Else
                else:
                    # They're out
                    if debug == True:
                        print("Caught stealing 2B")
                    game.on_1b = None
                    game.pitching.OUT +=1
                    game.pitching.OUT_inning
                    game.outs += 1 
                    
                    # Check outs as this might end the inning
                    if game.outs == 3:
                        break

        # Simulate plate appearance
        start_time = time.time()
        game = sim_ab(game, opener_list, park_object, wfx_adjustment, debug)
        # print("AB", time.time() - start_time)
        
        # Determine winning pitcher
        if (game.away_score > game.home_score) and ((game.inning == 5 and game.top_bot == "Bot") or game.inning >= 6) and (game.winning_pitcher not in game.away_pitchers):
            game.winning_pitcher = game.away_pitcher_up
        elif (game.home_score > game.away_score) and ((game.inning == 5 and game.top_bot == "Bot") or game.inning >= 6) and (game.winning_pitcher not in game.home_pitchers):
            game.winning_pitcher = game.home_pitcher_up
        elif (game.home_score == game.away_score) or game.inning < 5:
            game.winning_pitcher = None

        # Walk-off
        if (game.inning == innings) and (game.top_bot == "Bot") and (game.home_score > game.away_score):
            game.winning_pitcher = game.home_pitcher_up
            break


    return game


# %%
# Simulate a single game
def sim_game(game_template, opener_list, park_object, innings=9, wfx_adjustment=True, debug=False):
    start_time = time.time()

    # Copy game template
    game = deepcopy(game_template)
    
    # Determine starters (Leverage==1)
    game.home_starter = next(p for p in game.home_pitchers if p.Leverage == 1)
    game.away_starter = next(p for p in game.away_pitchers if p.Leverage == 1)

    # Assign starting pitchers
    game.home_pitcher_up = game.home_starter
    game.away_pitcher_up = game.away_starter
    game.pitching = game.home_pitcher_up

    # Loop over innings
    while game.inning <= game.innings:
        # Simulate the half-inning
        game = sim_inning(game, opener_list, park_object, innings, wfx_adjustment, debug)
        
        # Last inning logic
        if game.inning == game.innings:
            # Home team winning after top half
            if game.home_score > game.away_score and game.top_bot == "Top":
                break

            # Any team winning after bottom half
            if game.away_score != game.home_score and game.top_bot == "Bot":
                break

            # Tie after bottom half → extra inning
            if game.home_score == game.away_score and game.top_bot == "Bot":
                game.innings += 1

        # Advance half-inning
        if game.top_bot == "Top":
            game.top_bot = "Bot"
        else:
            game.top_bot = "Top"
            game.inning += 1

    # Calculate final stats for all players
    for batter in game.home_batters:
        batter, game = calculate_batter(batter, game)
    for batter in game.away_batters:
        batter, game = calculate_batter(batter, game)
    for pitcher in game.home_pitchers:
        pitcher, game = calculate_pitcher(pitcher, game)
    for pitcher in game.away_pitchers:
        pitcher, game = calculate_pitcher(pitcher, game)

    print("Game", time.time() - start_time)


    return game


# %%
# Simulate a batch of games
def sim_game_batch(game_template, opener_list, park_object, innings=9, wfx_adjustment=True, debug=False, batch_size=50):
    return [
        sim_game(game_template, opener_list, park_object, innings=innings, wfx_adjustment=wfx_adjustment, debug=debug)
        for _ in range(batch_size)
    ]


# %%
# Retrieve all values for attribute across all players across all simulations
def create_players_dataframe(game_list, attribute='FP', player='batter'):
    # Create a dictionary to store the data
    data = {}

    for i, game in enumerate(game_list):
        data[f'{attribute}{i}'] = []
        if player == 'batter':
            players = game.away_batters + game.home_batters
        elif player == 'pitcher':
            players = game.away_pitchers + game.home_pitchers

        for player_obj in players:
            data[f'{attribute}{i}'].append(getattr(player_obj, attribute))

    # Create the DataFrame from the dictionary
    players_df = pd.DataFrame(data)
    
    # Create columns
    name_list = [getattr(player_obj, 'fullName') for player_obj in players]
    players_df['fullName'] = name_list

    # Reorder columns
    cols = list(players_df.columns)
    cols = ['fullName'] + [col for col in cols if col != 'fullName']
    players_df = players_df[cols]


    return players_df


# %%
# Create dataframe with scores
def extract_scores(game_list):
    # Create the DataFrame
    data = {'away_score': [game.away_score for game in game_list],
            'home_score': [game.home_score for game in game_list]}

    score_df = pd.DataFrame(data)
    

    return score_df


# %%
# Log plate appearance summary to CSV (deprecated)
def log_pa_summary(pa_summary, baseball_path, filename='pa_summary_log.csv'):
    filepath = os.path.join(baseball_path, filename)
    
    # Check if the file already exists
    file_exists = os.path.isfile(filepath)
    
    # Open the file in append mode
    with open(filepath, mode='a', newline='') as file:
        writer = csv.writer(file)
        
        # Write the header only if the file is new
        if not file_exists:
            header = [f'col_{i+1}' for i in range(len(pa_summary))]
            writer.writerow(header)
        
        # Write the new row
        writer.writerow(pa_summary)

# %%
# Display gambling results for a given game
def display_results(away_team, home_team, game_num, odds_df, game_scores_df, display_gambling_info):
    # ANSI colors
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"

    # Base stats
    game_scores_df['home_win'] = (game_scores_df['home_score'] > game_scores_df['away_score']).astype(int)

    away_mean = game_scores_df['away_score'].mean()
    home_mean = game_scores_df['home_score'].mean()
    away_win_pct = (1 - game_scores_df['home_win'].mean()) * 100
    home_win_pct = game_scores_df['home_win'].mean() * 100

    # Helpers
    def colorize_return(val):
        if pd.isna(val):
            return "nan"
        if val > 1:
            return f"{GREEN}{val:.2f}{RESET}"
        if val < 1:
            return f"{RED}{val:.2f}{RESET}"
        return f"{val:.2f}"

    def fmt_odds(odds):
        if pd.isna(odds):
            return " nan"
        odds_int = int(odds)
        return f"{odds_int:>4}" if odds_int < 0 else f" {odds_int:>3}"

    if display_gambling_info:
        r = expected_returns(home_team, game_num, odds_df, game_scores_df)

        away_line = (
            f"{away_team:<4}"
            f"{away_mean:.2f} ({away_win_pct:.2f}%) "
            f"ML {colorize_return(r['ML1']['return'])} ({fmt_odds(r['ML1']['odds'])}) "
            f"Spr {colorize_return(r['Spread1']['return'])} ({fmt_odds(r['Spread1']['odds'])}) "
            f"Ovr {colorize_return(r['Ou1']['return'])} ({fmt_odds(r['Ou1']['odds'])})"
        )

        home_line = (
            f"{home_team:<4}"
            f"{home_mean:.2f} ({home_win_pct:.2f}%) "
            f"ML {colorize_return(r['ML2']['return'])} ({fmt_odds(r['ML2']['odds'])}) "
            f"Spr {colorize_return(r['Spread2']['return'])} ({fmt_odds(r['Spread2']['odds'])}) "
            f"Und {colorize_return(r['Ou2']['return'])} ({fmt_odds(r['Ou2']['odds'])})"
        )
    else:
        away_line = f"{away_team:<4}{away_mean:.2f} ({away_win_pct:.2f}%)"
        home_line = f"{home_team:<4}{home_mean:.2f} ({home_win_pct:.2f}%)"

    print(away_line)
    print(home_line)

# %%
# Calculate expected returns for a given game
def expected_returns(home_team, game_num, odds_df, game_scores_df):
    # Filter to rows for this home team
    home_games = odds_df[odds_df['HomeTeamShort'] == home_team]

    if home_games.empty or game_num > len(home_games):
        raise ValueError(f"No odds found for {home_team} game #{game_num}")

    # Select the correct instance (1-indexed)
    odds = home_games.iloc[game_num - 1]

    spread = odds['Spread']
    ou = odds['OU']

    sm1, sm2 = odds['SpreadMoney1'], odds['SpreadMoney2']
    ou1, ou2 = odds['OuMoney1'], odds['OuMoney2']
    ml1, ml2 = odds['MLMoney1'], odds['MLMoney2']

    def american_return(odds):
        if pd.isna(odds):
            return np.nan
        return 1 + (odds / 100 if odds > 0 else 100 / abs(odds))

    sm1_r, sm2_r = american_return(sm1), american_return(sm2)
    ou1_r, ou2_r = american_return(ou1), american_return(ou2)
    ml1_r, ml2_r = american_return(ml1), american_return(ml2)

    df = game_scores_df.copy()
    margin = df['away_score'] - df['home_score']
    total = df['away_score'] + df['home_score']

    def mean_or_nan(series, odds_val):
        return np.nan if pd.isna(odds_val) else series.mean()

    # ----- Spread -----
    spread1 = (margin > spread) * sm1_r
    spread2 = (margin < spread) * sm2_r
    spread1[margin < spread] = 0
    spread2[margin > spread] = 0
    spread1[margin == spread] = 1
    spread2[margin == spread] = 1

    # ----- Over / Under -----
    ou1_pay = (total > ou) * ou1_r
    ou2_pay = (total < ou) * ou2_r
    ou1_pay[total < ou] = 0
    ou2_pay[total > ou] = 0
    ou1_pay[total == ou] = 1
    ou2_pay[total == ou] = 1

    # ----- Moneyline -----
    ml1_pay = (df['away_score'] > df['home_score']) * ml1_r
    ml2_pay = (df['home_score'] > df['away_score']) * ml2_r
    ml1_pay[df['away_score'] < df['home_score']] = 0
    ml2_pay[df['home_score'] < df['away_score']] = 0

    return {
        'Spread1': {'return': mean_or_nan(spread1, sm1), 'odds': sm1},
        'Spread2': {'return': mean_or_nan(spread2, sm2), 'odds': sm2},
        'Ou1': {'return': mean_or_nan(ou1_pay, ou1), 'odds': ou1},
        'Ou2': {'return': mean_or_nan(ou2_pay, ou2), 'odds': ou2},
        'ML1': {'return': mean_or_nan(ml1_pay, ml1), 'odds': ml1},
        'ML2': {'return': mean_or_nan(ml2_pay, ml2), 'odds': ml2}
    }


# %%
__all__ = [name for name in globals() if not name.startswith("_")]