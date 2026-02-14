# %%
from U01Imports import *
from U02Functions import *

# %%
# Combine player simulation CSVs into one dataframe
def concat_player_sims(folder_path: str, position: str, n_jobs: int = -1) -> pd.DataFrame:
    ### Read in data
    # Select columns to read
    if position == "batter":
        columns = ['id', 'fullName', 'batting_order', 'imp_b_l', 'imp_b_r', 'confirmed', 'FP', 'team']
    else:
        columns = ['id', 'fullName', 'imp_p_l', 'imp_p_r', 'confirmed', 'FP', 'team']

    # Specify files
    folder = Path(folder_path)
    file_paths = [file for file in folder.iterdir() if file.is_file() and file.suffix == '.csv' and file.name.startswith(position)]

    # Read in CSVs, but only the specified columns 
    dfs = Parallel(n_jobs=n_jobs)(delayed(pd.read_csv)(file, usecols=columns) for file in file_paths)

    # Concatenate dataframes together
    df = pd.concat(dfs, ignore_index=True)

    ### Create new columns
    # Identify home and away teams
    away_team = folder_path.split("\\")[-1].split("@")[0]
    home_team = (folder_path.split("\\")[-1]).split("@")[1].split(" ")[0]
    # Identify game_id
    game_id = folder_path.split(" ")[-2]

    # Create team columns
    df['away_team'] = away_team
    df['home_team'] = home_team
    df['TeamAbbrev'] = np.where(df['team'] == "away", df['away_team'], df['home_team'])
    df['game_id'] = game_id


    return df


# %%
# Creates player input file for optimization
def create_player_file(contestKey, guide, draftGroupId, roto_slate, max_exposure_pitchers, max_exposure_batters, projections='roto', rostership='roto', ownership_spread=0.25):
    ### Step 1) Read in Draftables
    draftable_df = pd.read_csv(os.path.join(baseball_path, "A09. DraftKings", "2. Draftables", f"Draftables {draftGroupId}.csv"), dtype='str', encoding='iso-8859-1')

    # Create clean TEAM column
    draftable_df['TEAM'] = draftable_df['TeamAbbrev'].map(team_dict)
    
    # Remove postponed games
    if "alertType" in draftable_df.columns:
        draftable_df = draftable_df[draftable_df['alertType'] != "Postponed Game Alert"].reset_index(drop=True)
    
    ### Step 2) Read in Sims
    sim_dfs = []
    for folder in os.listdir(os.path.join(baseball_path, "C01. Simulations", "2. Player Sims", f"Matchups {guide['date'][0]}")):
        # Check if folder name contains any game_id
        if not any(game in folder for game in list(guide['game_id'].astype(str))):
            print(f"Excluding: {folder}")
            continue

        folder_path = os.path.join(baseball_path, "C01. Simulations", "2. Player Sims", f"Matchups {guide['date'][0]}", folder)
        print(f"Folder: {folder}")
        # Batters
        position = 'batter'
        batter_df = concat_player_sims(folder_path, position, n_jobs=-1)
        batter_df['Position'] = position
        batter_df.rename(columns={'imp_b_l': 'imp_l', 'imp_b_r': 'imp_r'}, inplace=True)
        # Pitchers
        position = 'pitcher'
        pitcher_df = concat_player_sims(folder_path, position, n_jobs=-1)
        pitcher_df['Position'] = position
        pitcher_df.rename(columns={'imp_p_l': 'imp_l', 'imp_p_r': 'imp_r'}, inplace=True)
        pitcher_df['batting_order'] = -99
        pitcher_df['confirmed'].fillna("Y", inplace=True)

        df = pd.concat([batter_df, pitcher_df], ignore_index=True, axis=0)

        sim_dfs.append(df)


    # Concatenate all player sims together
    sim_df = pd.concat(sim_dfs, ignore_index=True, axis=0)
    

    # Pivot
    # Create a new index for each FP instance within each `id`
    sim_df['FP_index'] = sim_df.groupby(['Position', 'id']).cumcount()

    # Pivot the DataFrame, using the `FP_index` to spread `FP` values into columns
    wide_df = sim_df.pivot_table(index=[col for col in sim_df.columns if col != 'FP' and col != 'FP_index'],
                             columns='FP_index', 
                             values='FP', 
                             aggfunc='first')

    # Rename the columns to FP_0, FP_1, etc.
    wide_df.columns = [f"FP_{col}" for col in wide_df.columns]

    # Reset index to get a flat DataFrame
    wide_df.reset_index(inplace=True)

    # Create clean TEAM variable
    wide_df['TEAM'] = wide_df['TeamAbbrev'].map(team_dict)

    # Drop duplicate Ohtanis, keeping pitcher Ohtani
    wide_df.sort_values(['Position', 'id'], inplace=True)
    wide_df.drop_duplicates('id', inplace=True, keep='last')
    

    ### Step 3) Read in RotoWire Projections
    try:
        roto_df = pd.read_csv(os.path.join(baseball_path, "A08. Projections", "2. RotoWire", "2. Projections", f"RotoWire Projections {roto_slate}.csv"))

        # Create clean columns
        roto_df['fullName'] = roto_df['firstName'] + " " + roto_df['lastName']
        roto_df['roto_projection'] = roto_df['points']
        roto_df['TEAM'] = roto_df['teamAbbr'].map(team_dict)

        # Keep relevant columns
        roto_df = roto_df[['fullName', 'TEAM', 'roto_projection', 'rostership']]
    except:
        print("No Roto file")
        rostership = None
        roto_df = pd.DataFrame(columns=['fullName', 'TEAM', 'roto_projection', 'rostership'])


    ### Step 4) Merge
    # Merge draftables, sims (wide), and RotoWire dataframes
    player_df = pd.merge(draftable_df, wide_df, left_on=['Name', 'TEAM'], right_on=['fullName', 'TEAM'], how='inner', suffixes=("", "2"))
    player_df["fullName_cut"] = (player_df["fullName"].str.replace(r"\s+(jr\.|sr\.|II|III|IV)$", "", case=False, regex=True))
    player_df = pd.merge(player_df, roto_df, left_on=['fullName_cut', 'TEAM'], right_on=['fullName', 'TEAM'], how='left')


    ### Step 5) Create New Fields
    ## Projections
    # Identify FP columns
    fp_columns = [col for col in player_df.columns if "FP_" in col]
    # RotoWire
    if projections == 'roto':
        player_df['AvgPointsPerGame'] = player_df['roto_projection'].fillna(0)
    # My projections
    elif projections == "robot":
        player_df['AvgPointsPerGame'] = player_df[fp_columns].mean(axis=1)
    
    ## Exposure
    # Set exposure range
    # RotoWire ownership projections   
    if rostership == "roto":
        # Multiplier
        # Sometimes rostership doesn't add up to 1000
        multiplier = 1000 / player_df['rostership'].sum(axis=0)
        player_df['rostership'] = player_df['rostership'] * multiplier
        player_df['rostership'].fillna(0, inplace=True)

        # Minimum
        # Shouldn't be below 0
        player_df['Min Exposure'] = np.maximum(player_df['rostership'] * (1 - ownership_spread) / 100, 0)
        # Very low values (0.01, for instance) make solving difficult. Replace with minimum of 0.
        player_df['Min Exposure'] = np.where(player_df['Min Exposure'] < 0.1, 0, player_df['Min Exposure'])
        # Maximum
        player_df['Max Exposure'] = np.where(player_df['Position2'] == "batter",
                                             np.minimum(player_df['rostership'] * (1 + ownership_spread) / 100, max_exposure_batters),
                                             np.minimum(player_df['rostership'] * (1 + ownership_spread) / 100, max_exposure_pitchers))
    # No ownership projections
    else:
        player_df['Min Exposure'] = 0
        player_df['Max Exposure'] = np.where(player_df['Position2'] == "batter", max_exposure_batters, max_exposure_pitchers)

    ## Roster information
    player_df['Confirmed Starter'] = (player_df['confirmed'].isin(["Y",1])).astype(int)
    player_df['Roster Order'] = player_df['batting_order'].astype(int)


    # Relevant columns
    player_columns = ['Position', 'Name + ID', 'Name', 'ID', 'Roster Position', 'Salary', 'Game Info', 'TeamAbbrev', 'AvgPointsPerGame', 'playerId', 'draftGroupId', 'game_id', 'Position2', 'imp_l', 'imp_r', 'confirmed', 'batting_order'] + fp_columns + ['rostership', 'roto_projection', 'Roster Order', 'Confirmed Starter', 'Min Exposure', 'Max Exposure']

    
    return player_df[player_columns].sort_values(['AvgPointsPerGame'], ascending=False)


# %%
# Uses optimizer to create DFS lineups
def create_lineups(contestKey, min_salary=49000, min_projection=5, stack_list=[5, 2, 1], excluded_teams=[],
                   min_starters=10, strategy=None, max_deviation=0.2, progressive_growth=0.01, num_lineups=200, parameters='Max'):

    class GLPKPuLPSolver(PuLPSolver):
        LP_SOLVER = GLPK_CMD(path=r"C:\Users\James\anaconda3\envs\torch_nightly\Library\bin\glpsol.exe", msg=False)
    
    ### Load in DraftKings baseball optimizer
    optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASEBALL, solver=GLPKPuLPSolver)
    
    ### Load in player sims
    optimizer.load_players_from_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv"))

    ### Settings
    # Set minimum salary
    optimizer.set_min_salary_cap(min_salary)
    # Stacks
    for stack in stack_list:
        optimizer.add_stack(TeamStack(size=stack, for_positions=['C', '1B', '2B', '3B', 'SS', 'OF'])) # removed spacing= argument because it's slow
    # Position Restrictions (may be incompatible with GLPK)
    # optimizer.restrict_positions_for_opposing_team(['SP', 'RP'], ['C', '1B', '2B', '3B', 'SS', 'OF']) 
    # Team Exclusions
    optimizer.player_pool.exclude_teams(excluded_teams)
    # Confirmed Starters
    optimizer.set_min_starters(min_starters)
    # Minimum Projection
    optimizer.player_pool.add_filters(PlayerFilter(from_value=min_projection),)
    # Set strategy (default is to use the same projections each simulation)
    if strategy == "Random":
        optimizer.set_fantasy_points_strategy(RandomFantasyPointsStrategy(max_deviation=max_deviation))  # set random strategy with custom max_deviation
    elif strategy == "Progressive":
        optimizer.set_fantasy_points_strategy(ProgressiveFantasyPointsStrategy(progressive_growth))  # Set progressive strategy that increase player points by 1%

    # Set exposure overwrite
    for player in optimizer.player_pool.get_players():
        player.min_exposure = 0
        # if parameters == 'Min'
        player.max_exposure = 1

    ### Optimizer
    i = 0
    for lineup_num in optimizer.optimize(num_lineups, exposure_strategy=AfterEachExposureStrategy):
        if i % 50 == 0 or i in [1, num_lineups - 1]:
            sys.stdout.write(f"\r{stack_list}: {i}/{num_lineups}   ")  # \r moves to the beginning of the line
            sys.stdout.flush()
        i += 1

    print(f"{stack_list}: {num_lineups}/{num_lineups} - Finished!")

    
    return optimizer


# %%
from concurrent.futures import ThreadPoolExecutor, as_completed
# Run optimizers in parallel
def run_parallel(params_list):
    """
    Runs create_lineups in parallel but *preserves the original order*
    of params_list, regardless of completion order.
    """

    results = [None] * len(params_list)

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(create_lineups, *params): i
            for i, params in enumerate(params_list)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = f"Error: {e}"


    return results


# %%
# Applies minimum-parameter fallback simulation results when maximum-parameter results fail
def apply_minimum_fallback(optimizers, maximum_constraints):
    """
    Takes optimizers list (max + min) and collapses it to only max entries,
    using min fallback where max fails.
    If both max and min fail, inserts an informative error object.
    """
    n_max = len(maximum_constraints)
    final = []

    for i in range(n_max):
        max_result = optimizers[i]
        min_result = optimizers[n_max + i]

        max_failed = (
            isinstance(max_result, str) or
            (isinstance(max_result, dict) and "error" in max_result)
        )

        min_failed = (
            isinstance(min_result, str) or
            (isinstance(min_result, dict) and "error" in min_result)
        )

        if not max_failed:
            # Max OK → use it
            final.append(max_result)

        elif max_failed and not min_failed:
            # Max failed but Min OK → fallback
            final.append(min_result)

        else:
            # BOTH failed → insert failure info
            final.append({
                "error": f"Both max and min constraints failed for index {i}",
                "max_error": max_result,
                "min_error": min_result
            })


    return final


# %%
# Write lineups to CSV
def write_lineups(optimizers, contestKey):
    dfs = []
    temp_files = []

    for i, opt in enumerate(optimizers):
        if isinstance(opt, (str, dict)):
            continue
        temp_file = f'optimizer_{i}.csv'
        opt.export(temp_file)
        temp_files.append(temp_file)
        dfs.append(pd.read_csv(temp_file))

    combined_df = pd.concat(dfs, ignore_index=True).drop_duplicates().sort_values('FPPG', ascending=False)
    combined_df.to_csv(os.path.join(baseball_path, "C02. Optimization", "2. Lineups", f"Lineups {contestKey}.csv"), index=False)

    for f in temp_files:
        try: os.remove(f)
        except: pass


# %%
# Rank lineups by sortby criteria
def choose_lineups(contestKey, roto_slate, pareto_set, sense_list, sort_by, ascending_list):
    # Read in players
    player_sims = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv"))

    # Keep relevant variables
    player_sims.drop(columns={"Position", "Name", "ID", "Roster Position", "Salary", "Game Info", "TeamAbbrev", 'playerId', 'draftGroupId', 'game_id', 'Position2', 'imp_l', 'imp_r', "AvgPointsPerGame"}, inplace=True)

    # Clean Name + ID variable to remove space (this is for consistency for merging)
    player_sims['Name + ID'] = player_sims['Name + ID'].str.replace(r'\s*\(', '(', regex=True, flags=re.IGNORECASE)
        
    # Determine number of game simulations
    num_sims = sum('FP_' in column_name for column_name in player_sims.columns)

    
    # Read in daily lineups
    lineup_sims = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "2. Lineups", f"Lineups {contestKey}.csv"))
    
    # Merge stats onto lineups
    lineup_sims = lineup_sims.merge(player_sims, left_on="P", right_on="Name + ID", how='left', validate="m:1")
    lineup_sims = lineup_sims.merge(player_sims, left_on="P.1", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_P.1"))
    lineup_sims = lineup_sims.merge(player_sims, left_on="C", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_C"))
    lineup_sims = lineup_sims.merge(player_sims, left_on="1B", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_1B"))
    lineup_sims = lineup_sims.merge(player_sims, left_on="2B", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_2B"))
    lineup_sims = lineup_sims.merge(player_sims, left_on="3B", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_3B"))
    lineup_sims = lineup_sims.merge(player_sims, left_on="SS", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_SS"))
    lineup_sims = lineup_sims.merge(player_sims, left_on="OF", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_OF"))
    lineup_sims = lineup_sims.merge(player_sims, left_on="OF.1", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_OF.1"))
    lineup_sims = lineup_sims.merge(player_sims, left_on="OF.2", right_on="Name + ID", how='left', validate="m:1", suffixes=(None, "_OF.2"))
    
    # Add up player performances
    i=0
    # Where i is the number of simulations
    while i < num_sims:
        sim = f"FP_{i}"
        P1 = sim
        P2 = sim + "_P.1"
        C = sim + "_C"
        B1 = sim + "_1B"
        B2 = sim + "_2B"
        B3 = sim + "_3B"
        SS = sim + "_SS"
        OF1 = sim + "_OF"
        OF2 = sim + "_OF.1"
        OF3 = sim + "_OF.2"

        game = f"Sim {i}"

        lineup_sims[game] = lineup_sims[P1] + lineup_sims[P2] + lineup_sims[C] + lineup_sims[B1] + lineup_sims[B2] + lineup_sims[B3] + lineup_sims[SS] + lineup_sims[OF1] + lineup_sims[OF2] + lineup_sims[OF3]

        i+=1

    
    lineup_sims.rename(columns={'FPPG':'AvgPointsPerGame'}, inplace=True)
        
    
    ### Calculate summary statistics
    column_list = [col for col in lineup_sims if col.startswith("Sim")]

    ### Points
    lineup_sims['AVG'] = lineup_sims[column_list].mean(axis=1)
    lineup_sims['P50'] = lineup_sims[column_list].median(axis=1)
    lineup_sims['P75'] = lineup_sims[column_list].quantile(.75, axis=1)
    lineup_sims['P90'] = lineup_sims[column_list].quantile(.90, axis=1)
    lineup_sims['P95'] = lineup_sims[column_list].quantile(.95, axis=1)
    lineup_sims['P99'] = lineup_sims[column_list].quantile(.99, axis=1)
    lineup_sims['P100'] = lineup_sims[column_list].max(axis=1)

    
    ### Tail 
    lineup_sims['Tail'] = 0 
    for column in column_list:
        for i in range(len(lineup_sims)):
            if lineup_sims[column][i] >= lineup_sims['P95'][i]:
                lineup_sims['Tail'][i] = lineup_sims['Tail'][i] + lineup_sims[column][i]

    lineup_sims['Sim STD'] = lineup_sims[lineup_sims.columns[lineup_sims.columns.str.startswith('Sim')]].std(axis=1)

    # Standard deviations from mean 
    lineup_sims['Plus2'] = lineup_sims['AvgPointsPerGame'] + 2 * lineup_sims['Sim STD']
    lineup_sims['Plus3'] = lineup_sims['AvgPointsPerGame'] + 3 * lineup_sims['Sim STD']
    
    
    ### Ownership
    # Pitcher ownership 
    lineup_sims.rename(columns={'rostership': 'rostership_P'}, inplace=True)
    lineup_sims['pitcher rostership'] = lineup_sims[['rostership_P', 'rostership_P.1']].sum(axis=1)
    # Batter ownership 
    lineup_sims['batter rostership'] = lineup_sims[['rostership_C', 'rostership_1B', 'rostership_2B', 'rostership_3B', 'rostership_SS', 'rostership_OF', 'rostership_OF.1', 'rostership_OF.2']].sum(axis=1)
    # Total
    lineup_sims['rostership'] = lineup_sims[['pitcher rostership', 'batter rostership']].sum(axis=1)


    # Identify pareto optimal lineups
    lineup_sims['pareto'] = paretoset(lineup_sims[pareto_set], sense=sense_list).astype('int')


    # Filter columns starting with 'Sim '
    sim_columns = [col for col in lineup_sims.columns if col.startswith('Sim ')]

    # Initialize the Wins and Top1% columns
    lineup_sims['Wins'] = 0
    lineup_sims['Top1%'] = 0
    lineup_sims['Top5%'] = 0
    lineup_sims['Top10%'] = 0
    lineup_sims['Top20%'] = 0
    lineup_sims['Top50%'] = 0

    # Iterate over each 'Sim ' column
    for col in sim_columns:
        # Find the maximum value in the column
        max_value = lineup_sims[col].max()
        # Increment the 'Wins' count for rows with the maximum value in this column
        lineup_sims.loc[lineup_sims[col] == max_value, 'Wins'] += 1

        # Calculate the top 1% threshold for the current column
        top_1_percent_threshold = lineup_sims[col].quantile(0.99)
        top_5_percent_threshold = lineup_sims[col].quantile(0.95)
        top_10_percent_threshold = lineup_sims[col].quantile(0.90)
        top_20_percent_threshold = lineup_sims[col].quantile(0.80)
        top_50_percent_threshold = lineup_sims[col].quantile(0.50)
        # Increment the 'Top1%' count for rows with values in the top 1%
        lineup_sims.loc[lineup_sims[col] >= top_1_percent_threshold, 'Top1%'] += 1
        lineup_sims.loc[lineup_sims[col] >= top_5_percent_threshold, 'Top5%'] += 1
        lineup_sims.loc[lineup_sims[col] >= top_10_percent_threshold, 'Top10%'] += 1
        lineup_sims.loc[lineup_sims[col] >= top_20_percent_threshold, 'Top20%'] += 1
        lineup_sims.loc[lineup_sims[col] >= top_50_percent_threshold, 'Top50%'] += 1

    # Convert the Top1% count to a percentage
    lineup_sims['Top1%'] = (lineup_sims['Top1%'] / len(sim_columns)) * 100
    lineup_sims['Top5%'] = (lineup_sims['Top5%'] / len(sim_columns)) * 100
    lineup_sims['Top10%'] = (lineup_sims['Top10%'] / len(sim_columns)) * 100
    lineup_sims['Top20%'] = (lineup_sims['Top20%'] / len(sim_columns)) * 100
    lineup_sims['Top50%'] = (lineup_sims['Top50%'] / len(sim_columns)) * 100

    # Sort (descending - Note that DK will read this the wrong way)
    lineup_sims.sort_values(by=sort_by, ascending=ascending_list, inplace=True)


    # Delete excess variables
    lineup_sims = lineup_sims.loc[:, ~lineup_sims.columns.str.contains('FP', case=False)]
    lineup_sims = lineup_sims.loc[:, ~lineup_sims.columns.str.contains('Name', case=False)]
    lineup_sims = lineup_sims.loc[:, ~lineup_sims.columns.str.contains('Order', case=False)]
    lineup_sims = lineup_sims.loc[:, ~lineup_sims.columns.str.contains('Exposure', case=False)]
    lineup_sims = lineup_sims.loc[:, ~lineup_sims.columns.str.contains('onfirmed', case=False)]
    lineup_sims = lineup_sims.loc[:, ~lineup_sims.columns.str.contains('rostership_', case=False)]
    lineup_sims = lineup_sims.loc[:, ~lineup_sims.columns.str.contains('roto_projection', case=False)]

    
    return lineup_sims


# %%
# Create upload file for DraftKings
def create_upload_file(contestKey, sort_by='Plus3'):
    # Read in lineup sims
    lineup_ranked = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "3. Lineups Ranked", f"Lineups Ranked {contestKey}.csv"))
    # # Sort (ascending because DK will put the bottom lineups at the top)
    # lineup_ranked.sort_values(by=sort_by, ascending=True, inplace=True)
    # Keep just the players
    lineup_ranked = lineup_ranked[['P', 'P.1', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF.1', 'OF.2']]
    
    # Rename variables to appease DK's upload
    lineup_ranked.rename(columns={'P.1':'P', 'OF.1':'OF', 'OF.2':'OF'}, inplace=True)


    return lineup_ranked


# %%
# Create entry file for DraftKings
def create_entry_file(draftGroupId, contestKey):
    # Download entry file for draftGroupId
    url = f"https://www.draftkings.com/bulkentryedit/getentriescsv?draftGroupId={draftGroupId}"

    javascript_code = f"window.open('{url}', '_blank');"
    display(Javascript(javascript_code))
    
    time.sleep(5)
    
    # Get the list of files in the downloads folder
    files = os.listdir(download_path)

    # Get the most recently modified file (entry sheet)
    most_recent_file = max(files, key=lambda x: os.path.getctime(os.path.join(download_path, x)))
    most_recent_file_path = os.path.join(download_path, most_recent_file)
    df = pd.read_csv(most_recent_file_path, usecols=['Entry ID','Contest Name','Contest ID','Entry Fee'])
    df.dropna(inplace=True)

    # Read in Upload file
    lineup_sims = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "4. Uploads", f"Upload {contestKey}.csv"), encoding='iso-8859-1')

    # Keep just the players
    lineup_sims = lineup_sims[['P', 'P.1', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF.1', 'OF.2']]
    # Rename variables to appease DK's upload
    lineup_sims.rename(columns={'P.1':'P', 'OF.1':'OF', 'OF.2':'OF'}, inplace=True)
    lineup_sims.reset_index(inplace=True, drop=True)
    
    # Merge entry sheet with lineups
    entry_df = df.merge(lineup_sims, how='inner', left_index=True, right_index=True)
    
    # Convert to numeric
    entry_df['Entry ID'] = entry_df['Entry ID'].astype('int64')


    return entry_df


# %%
# Main function to create contest lineups and derived files
def create_contest_lineups(contestKey, sort_by, min_salary, min_projection, major_stack, minor_stack, max_exposure_batters, max_exposure_pitchers, excluded_teams, min_starters, lineups, historic):
    # Read in Contest Guide
    guide = pd.read_csv(os.path.join(baseball_path, "B03. Contest Guides", f"Contest Guide {contestKey}.csv"))

    # Identify draftGroupId
    draftGroupId = guide['draftGroupId'][0]

    # Identify date
    date = guide['date'][0]

    # Identify RotoWire slate
    roto_slate = guide['roto_slate'][0]
    
    # 1. Players
    # This creates player files to be used as inputs in optimizer
    draftables_with_sims = create_player_file(contestKey, guide, draftGroupId, date, roto_slate)    
    draftables_with_sims.to_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv"), index=False, encoding='iso-8859-1')
    
    # 2. Lineups
    # This creates optimal lineups
    create_lineups(contestKey, min_salary, min_projection, major_stack, minor_stack, excluded_teams, min_starters, lineups)
    
    # 3. Lineups Ranked
    # This adds stats based on score distributions to assess which lineups to choose
    lineups_ranked = choose_lineups(contestKey, roto_slate, sort_by)
    lineups_ranked.to_csv(os.path.join(baseball_path, "C02. Optimization", "3. Lineups Ranked", f"Lineups Ranked {contestKey}.csv"), index=False)
    
    # 4. Uploads
    # This creates a file to upload lineups to DraftKings in the proper order
    if historic == False:
        # Create upload file
        upload = create_upload_file(contestKey, sort_by)
        upload.to_csv(os.path.join(baseball_path, "C02. Optimization", "4. Uploads", f"Upload {contestKey}.csv"), index=False)

    # 5. Entries
    # This creates a file to upload entry-specific lineups
    if historic == False:
        entry = create_entry_file(draftGroupId, contestKey)
        entry.to_csv(os.path.join(baseball_path, "C02. Optimization", "5. Entries", f"Entries {draftGroupId}.csv"), index=False, encoding='iso-8859-1')


# %%
# This returns contestKeys that do not work
def create_contest_lineups2(contestKey, sort_by, min_salary, min_projection, major_stack, minor_stack, max_exposure_batters, max_exposure_pitchers, excluded_teams, min_starters, lineups, historic):
    try:
        return create_contest_lineups(contestKey, sort_by, min_salary, min_projection, major_stack, minor_stack, max_exposure_batters, max_exposure_pitchers, excluded_teams, min_starters, lineups, historic)
    except Exception as e:
        print(f"Error processing contestKey: {contestKey}. Exception: {e}")
        return contestKey


# %%
# Email upload and entry files
def email_upload_file(draftGroupId, contestKey, contestTime):    
    message = f"""\
    contestTime: {contestTime}
    draftGroupId: {draftGroupId}
    contestKey: {contestKey}

    Entries: https://www.draftkings.com/entry/upload
    Uploads: https://www.draftkings.com/lineup/upload
    """
lkasjdf 
    sender_email = os.getenv("EMAIL_ADDRESS")
    receiver_emails = [os.getenv("EMAIL_ADDRESS")]
    smtp_server = 'smtp.gmail.com'
    port = 465  # Port for SSL
    password = os.getenv("EMAIL_PASSWORD")

    # Create a multipart message object
    msg = MIMEMultipart()
    msg['Subject'] = f'Lineups: {contestKey}'
    msg['From'] = sender_email
    msg['To'] = ', '.join(receiver_emails)  # Join list into comma-separated string

    # Attach the message to the email
    msg.attach(MIMEText(message, 'plain'))

    # Add Entry and Upload files as attachments
    entry_path = os.path.join(baseball_path, "C02. Optimization", "5. Entries", f"Entries {draftGroupId}.csv")
    upload_path = os.path.join(baseball_path, "C02. Optimization", "4. Uploads", f"Upload {contestKey}.csv")

    def attach_file(file_path):
        with open(file_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            filename = os.path.basename(file_path)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

    attach_file(entry_path)
    attach_file(upload_path)

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Send the email
    try:
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_emails, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")


# %%
# Automate upload of entry file to DraftKings
def upload_entries(draftGroupId):
    # Open entry page
    webbrowser.open(f"https://www.draftkings.com/entry/upload")
    time.sleep(5)

    # Search for "UPLOAD CSV" and get its position
    upload_csv_button = pyautogui.locateOnScreen(os.path.join(baseball_path, "UPLOAD CSV.png"), confidence=0.8)
    
    # Check if the button is found
    if upload_csv_button is not None:
        # If found, click on it
        pyautogui.click(upload_csv_button)
    else:
        print("Button not found.")
    
    # Access directory bar
    pyautogui.hotkey('alt', 'd')
    time.sleep(3)

    # Copy and paste the file path
    filepath = rf"C:\Users\James\Documents\MLB\Data\C02. Optimization\5. Entries\Entries {draftGroupId}.csv"
    pyperclip.copy(filepath)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(3)
    pyautogui.press("enter")


# %%
# Create clickable button to open Excel file
def excel_button(file_path):
    file_path = os.path.abspath(file_path)

    def open_excel(b):
        subprocess.Popen(['start', 'excel', file_path], shell=True)

    button = widgets.Button(description=f"Open {os.path.basename(file_path)} in Excel 📊")
    button.on_click(open_excel)
    display(button)


# %%
__all__ = [name for name in globals() if not name.startswith("_")]


