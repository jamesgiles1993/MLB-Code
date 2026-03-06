# %%
from U01Imports import *
from U02Functions import *

# %%
# 1. Players
# Creates player input file for optimization
def create_player_file(contestKey, guide, draftGroupId, roto_slate, max_exposure_pitchers, max_exposure_batters, projections='roto', rostership='roto', ownership_spread=0.25, write_file=True):
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
    

    ### Step 1) Read in Draftables
    draftable_df = pd.read_csv(os.path.join(baseball_path, "A09. DraftKings", "2. Draftables", f"Draftables {draftGroupId}.csv"), dtype='str', encoding='iso-8859-1')

    # Create clean TEAM column
    draftable_df['TEAM'] = draftable_df['TeamAbbrev'].map(team_dict)
    
    # Remove postponed games
    if "alertType" in draftable_df.columns:
        draftable_df = draftable_df[draftable_df['alertType'] != "Postponed Game Alert"].reset_index(drop=True)
    
    ### Step 2) Read in Sims
    # Check if folder exists
    if not os.path.exists(os.path.join(baseball_path, "C01. Simulations", "2. Player Sims", f"Matchups {guide['date'][0]}")):
        print(f"No simulation folder found for date {guide['date'][0]}. Check if simulations have been run for this date.")
        return

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
    try:
        sim_df = pd.concat(sim_dfs, ignore_index=True, axis=0)
    except:
        print("No simulation files found for any matchups on this date.")
        return

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

    # Write to CSV
    if write_file == True:
        player_df[player_columns].sort_values(['AvgPointsPerGame'], ascending=False).to_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv"), index=False, encoding='iso-8859-1')


    return player_df[player_columns].sort_values(['AvgPointsPerGame'], ascending=False)


# %%
# 2. Lineups
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

    optimizer.stack = stack_list

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
        df = pd.read_csv(temp_file)
        # Add stack as string
        df['stack'] = str(opt.stack)

        dfs.append(df)

    combined_df = pd.concat(dfs, ignore_index=True).drop_duplicates().sort_values('FPPG', ascending=False)
    combined_df.to_csv(os.path.join(baseball_path, "C02. Optimization", "2. Lineups", f"Lineups {contestKey}.csv"), index=False)

    for f in temp_files:
        try: os.remove(f)
        except: pass


# %%
# 3. Field Lineups
def simulate_field_lineups(contestKey, 
                           num_lineups=1000, 
                           min_salary=45000, 
                           max_salary=50000,
                           stack_str='5-2-1',
                           pitcher_exp=1.3,
                           max_attempts=10000,
                           write_file=True):
    """
    Generate DFS lineups with generic stack configuration.

    Parameters
    ----------
    df : DataFrame
        Player pool including 'Roster Position', 'TeamAbbrev', 'Salary', 'rostership', 'Name + ID'.
    num_lineups : int
        Number of lineups to generate.
    min_salary, max_salary : int
        Hard salary bounds.
    stack_str : str
        Stack string like '5-2-1' or '4-4'.
    pitcher_exp : float
        Exponent to overweight pitcher rostership.
    max_attempts : int
        Max attempts before giving up.
    write_file : bool
        Whether to write the lineup file to disk.
    """
    
    # Read in player sim results
    try:
        df = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv"), encoding='iso-8859-1')
    except Exception as e:
        print(f"Error reading player file for contestKey: {contestKey}. Check if the file exists and is properly formatted. Error: {e}")
        return pd.DataFrame()

    rng = np.random.default_rng()

    df = df.copy()
    df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce')
    df = df.dropna(subset=['Salary'])
    df = df.sample(frac=1).reset_index(drop=True)  # Shuffle to remove ordering bias

    df['p'] = (df['rostership'] / 100).clip(lower=0)
    total_p = df['p'].sum()
    df['p'] = df['p'] / total_p if total_p > 0 else 1 / len(df)

    df['pos_list'] = df['Roster Position'].str.split('/')
    df['is_pitcher'] = df['Roster Position'] == 'P'

    hitters = df[~df['is_pitcher']].copy()
    pitchers = df[df['is_pitcher']].copy()

    # --- Precompute position masks ---
    position_masks = {pos: hitters['pos_list'].apply(lambda x: pos in x).values
                      for pos in ['C','1B','2B','3B','SS','OF']}

    # Parse stack string into list of stack sizes
    stack_sizes = [int(s) for s in stack_str.split('-')]

    required_positions_template = {
        'C': 1,
        '1B': 1,
        '2B': 1,
        '3B': 1,
        'SS': 1,
        'OF': 3
    }

    lineups = []
    lineup_budgets = []
    attempts = 0

    teams = hitters['TeamAbbrev'].unique()

    while len(lineups) < num_lineups and attempts < max_attempts:
        attempts += 1
        chosen_ids = set()
        lineup_dict = {'P': [], 'C': None, '1B': None, '2B': None,
                       '3B': None, 'SS': None, 'OF': []}
        lineup_salary = 0
        valid = True

        # --- Select stack teams ---
        if len(stack_sizes) > len(teams):
            continue  # cannot pick more teams than available

        selected_teams = rng.choice(teams, size=len(stack_sizes), replace=False)
        stack_counts = dict(zip(selected_teams, stack_sizes))

        # --- Fill hitter positions ---
        for position, count in required_positions_template.items():
            for _ in range(count):
                mask = position_masks[position]
                eligible = hitters[mask]
                # enforce stack counts
                eligible = eligible[eligible['TeamAbbrev'].map(stack_counts).fillna(0) > 0]
                ### TESTING - ensure non-missing weights ###
                eligible['p'].fillna(0.001, inplace=True)
                eligible = eligible[~eligible.index.isin(chosen_ids)]
                if len(eligible) == 0:
                    valid = False
                    break

                # vectorized stack weighting
                weights = eligible['p'].values.copy()
                team_array = eligible['TeamAbbrev'].values

                # Stack boost
                for team, sz in stack_counts.items():
                    mask = (team_array == team)
                    if sz >= 4:
                        weights[mask] *= 1.15
                    else:
                        weights[mask] *= 1.05

                # Guarantee non-negative
                weights = np.clip(weights, 0, None)

                weight_sum = weights.sum()

                if weight_sum <= 0 or not np.isfinite(weight_sum):
                    # fallback to uniform
                    weights = np.ones(len(eligible)) / len(eligible)
                else:
                    weights /= weight_sum

                chosen = rng.choice(eligible.index, p=weights)

                lineup_salary += df.loc[chosen, 'Salary']
                chosen_ids.add(chosen)
                if position == 'OF':
                    lineup_dict['OF'].append(chosen)
                else:
                    lineup_dict[position] = chosen
                stack_counts[df.loc[chosen,'TeamAbbrev']] -= 1
            if not valid:
                break
        if not valid:
            continue

        # --- Select pitchers ---
        eligible_p = pitchers[~pitchers.index.isin(chosen_ids)]
        if len(eligible_p) < 2:
            continue
        pitcher_weights = eligible_p['p'].values ** pitcher_exp
        pitcher_weights /= pitcher_weights.sum()
        chosen_pitchers = rng.choice(eligible_p.index, size=2, replace=False, p=pitcher_weights)
        lineup_dict['P'] = list(chosen_pitchers)
        lineup_salary += df.loc[chosen_pitchers, 'Salary'].sum()

        # --- Hard salary check ---
        if not (min_salary <= lineup_salary <= max_salary):
            continue

        # --- Build ordered lineup ---
        lineup_ordered = [
            lineup_dict['P'][0], lineup_dict['P'][1],
            lineup_dict['C'], lineup_dict['1B'], lineup_dict['2B'], lineup_dict['3B'],
            lineup_dict['SS'], lineup_dict['OF'][0], lineup_dict['OF'][1], lineup_dict['OF'][2]
        ]
        lineups.append(lineup_ordered)
        lineup_budgets.append(lineup_salary)

    if not lineups:
        return pd.DataFrame()

    # --- Convert to DataFrame ---
    columns_order = ['P', 'P.1', 'C', '1B','2B','3B','SS','OF','OF.1','OF.2']
    lineup_df = pd.DataFrame(lineups, columns=columns_order)
    for col in lineup_df.columns:
        lineup_df[col] = lineup_df[col].map(df['Name + ID'])
    lineup_df['Budget'] = lineup_budgets

    # --- FP aggregation ---
    fp_cols = [c for c in df.columns if c.startswith('FP_')]
    fp_mapping = df.set_index('Name + ID')[fp_cols]
    fp_list = [fp_mapping.reindex(lineup_df[pos]).reset_index(drop=True) for pos in lineup_df.columns[:10]]
    fp_concat = pd.concat(fp_list, axis=1)
    fp_sums = fp_concat.T.groupby(level=0).sum().T
    lineup_df = pd.concat([lineup_df, fp_sums], axis=1)
    lineup_df['FPPG'] = fp_sums.mean(axis=1)
    lineup_df = lineup_df[[col for col in lineup_df.columns if not col.startswith('FP_')]]
    lineup_df = lineup_df.replace(r' \(', '(', regex=True)

    print(f"Generated {len(lineups)} lineups in {attempts} attempts.")

    # Write to CSV
    if write_file == True:
        lineup_df.to_csv(os.path.join(baseball_path, "C02. Optimization", "3. Field Lineups", f"Field Lineups {contestKey}.csv"), index=False, encoding='iso-8859-1')


    return lineup_df


# %%
# 4. Porfolio lineups
def choose_portfolio(contestKey, portfolio_size=20, n_iterations=1000, swap_size=2, random_seed=42, optimize_metric="Top_1pct_rate", write_file=True):
    # Payout array
    def build_payout_array(payout_df, contest_size):

        # If contest_size is invalid (0 or None), infer from payout structure
        if not contest_size or contest_size == 0:
            contest_size = int(payout_df['maxPosition'].max())

        payout_array = np.zeros(contest_size, dtype=float)

        payouts = (
            payout_df['payoutDescription']
                .astype(str)
                .str.replace('$', '', regex=False)
                .str.replace(',', '', regex=False)
                .str.strip()
        )

        payouts = pd.to_numeric(payouts, errors='coerce').fillna(0.0)

        for start, end, payout in zip(
            payout_df['minPosition'],
            payout_df['maxPosition'],
            payouts
        ):
            start_idx = max(0, int(start) - 1)
            end_idx = min(contest_size, int(end))
            payout_array[start_idx:end_idx] = payout

        return payout_array
    
    # Score matrix
    def build_score_matrix(lineup_df, player_df_indexed, player_cols):
        sim_cols = [c for c in player_df_indexed.columns if c.startswith('FP_') or c.startswith('sim_')]
        score_matrix = []

        for _, lineup in lineup_df.iterrows():
            player_ids = [lineup[col] for col in player_cols]
            sims = player_df_indexed.loc[player_ids, sim_cols].sum(axis=0).values
            score_matrix.append(sims)

        return np.array(score_matrix)

    # Portfolio evaluation
    def evaluate_portfolio(selected_idx, my_scores, field_scores, payout_array, entry_fee, contest_size):
        n_my = len(selected_idx)
        n_field = field_scores.shape[0]
        n_sims = my_scores.shape[1]

        # Compute how many field lineups we can realistically add
        n_field_needed = min(contest_size - n_my, n_field)
        # n_total_simulated = n_my + n_field_needed

        per_lineup_payouts = np.zeros((n_my, n_sims))
        per_lineup_top1 = np.zeros((n_my, n_sims))
        per_lineup_top5 = np.zeros((n_my, n_sims))

        for s in range(n_sims):
            # Sample field lineups if needed
            if n_field_needed > 0:
                sampled_field = np.random.choice(field_scores[:, s], size=n_field_needed, replace=False)
                all_scores = np.concatenate([my_scores[selected_idx, s], sampled_field])
            else:
                all_scores = my_scores[selected_idx, s]

            ranks = np.argsort(-all_scores).argsort()  # 0 = best
            portfolio_ranks = ranks[:n_my]

            # Use actual number of competitors in simulation to set thresholds
            n_competitors = len(all_scores)
            top1_threshold = max(1, int(np.ceil(0.01 * n_competitors)))
            top5_threshold = max(1, int(np.ceil(0.05 * n_competitors)))

            rank_clipped = np.minimum(portfolio_ranks, len(payout_array) - 1)
            per_lineup_payouts[:, s] = payout_array[rank_clipped]

            per_lineup_top1[:, s] = (portfolio_ranks < top1_threshold).astype(float)
            per_lineup_top5[:, s] = (portfolio_ranks < top5_threshold).astype(float)

        per_lineup_ev = per_lineup_payouts.mean(axis=1)
        per_lineup_top1_rate = per_lineup_top1.mean(axis=1)
        per_lineup_top5_rate = per_lineup_top5.mean(axis=1)

        portfolio_ev = per_lineup_ev.sum() - entry_fee * n_my
        portfolio_roi = portfolio_ev / (entry_fee * n_my) if entry_fee > 0 else 0
        portfolio_std = per_lineup_payouts.sum(axis=0).std()
        portfolio_top1_rate = per_lineup_top1_rate.mean()
        portfolio_top5_rate = per_lineup_top5_rate.mean()

        portfolio_metrics = {
            "EV": portfolio_ev,
            "ROI": portfolio_roi,
            "StdDev": portfolio_std,
            "Top_1pct_rate": portfolio_top1_rate,
            "Top_5pct_rate": portfolio_top5_rate
        }

        return portfolio_metrics, per_lineup_ev, per_lineup_top1_rate, per_lineup_top5_rate

    # Monte Carlo portfolio search
    def monte_carlo_portfolio_search(lineup_df, my_scores, field_scores, payout_array, entry_fee,
                                    contest_size, portfolio_size=20, n_iterations=1000, swap_size=2,
                                    random_seed=42, optimize_metric="Top_1pct_rate"):

        np.random.seed(random_seed)
        n_candidates = len(lineup_df)
        n_field = field_scores.shape[0]

        if n_field + portfolio_size < contest_size:
            print(f"WARNING: Simulated field + portfolio ({n_field + portfolio_size}) < contest size ({contest_size}). EV may be overestimated.")

        projected_fp = lineup_df['FPPG'].values
        top_indices = np.argsort(-projected_fp)[:portfolio_size]
        best_portfolio = top_indices.copy()

        # initial evaluation (no warning needed here)
        metrics, _, _, _ = evaluate_portfolio(best_portfolio, my_scores, field_scores,
                                            payout_array, entry_fee, contest_size)
        best_value = metrics[optimize_metric]

        for it in range(n_iterations):
            swap_out = np.random.choice(best_portfolio, size=min(swap_size, portfolio_size), replace=False)
            remaining_candidates = np.setdiff1d(np.arange(n_candidates), best_portfolio)
            if len(remaining_candidates) == 0:
                continue
            swap_in = np.random.choice(remaining_candidates, size=len(swap_out), replace=False)
            new_portfolio = best_portfolio.copy()
            for o, i in zip(swap_out, swap_in):
                new_portfolio[np.where(new_portfolio == o)[0][0]] = i

            metrics, _, _, _ = evaluate_portfolio(new_portfolio, my_scores, field_scores,
                                                payout_array, entry_fee, contest_size)
            new_value = metrics[optimize_metric]
            if new_value > best_value:
                best_portfolio = new_portfolio
                best_value = new_value
                print(f"Iteration {it+1}: New best {optimize_metric} = {best_value:.4f}")

        portfolio_metrics, per_lineup_ev, per_lineup_top1_rate, per_lineup_top5_rate = evaluate_portfolio(
            best_portfolio, my_scores, field_scores, payout_array, entry_fee, contest_size
        )

        selected_lineups_df = lineup_df.iloc[best_portfolio].copy()
        selected_lineups_df["EV_Payout"] = per_lineup_ev
        selected_lineups_df["Top_1pct_rate"] = per_lineup_top1_rate
        selected_lineups_df["Top_5pct_rate"] = per_lineup_top5_rate

        return best_portfolio, portfolio_metrics, selected_lineups_df

    # Read in necessary datasets
    try:
        player_df = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv"))
        lineup_df = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "2. Lineups", f"Lineups {contestKey}.csv"))
        field_lineup_df = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "3. Field Lineups", f"Field Lineups {contestKey}.csv"))
        payout_df = pd.read_csv(os.path.join(baseball_path, "A09. DraftKings", "3. Payouts", f"Payouts {contestKey}.csv"))
        contest_df = pd.read_csv(os.path.join(baseball_path, "B03. Contest Guides", f"Contest Guide {contestKey}.csv"))
    except Exception as e: 
        print(f"Error reading files for contest {contestKey}: {e}")
        return None, None, None

    print(payout_df)

    # Clean player file Name + IDs to match lineup format
    player_df['Name + ID'] = player_df['Name + ID'].str.replace(" (", "(", regex=False)

    # Index player Name + ID for quick lookup
    player_df_indexed = player_df.set_index('Name + ID')

    # Set player position columns
    player_cols = ['P','P.1','C','1B','2B','3B','SS','OF','OF.1','OF.2']

    # Gather information from contest guide
    contest_size = contest_df['entries'].iloc[0]
    entry_fee = contest_df['entryFee'].iloc[0]

    # Create payout and score arrays
    payout_array = build_payout_array(payout_df, contest_size)
    print(payout_array)

    my_scores = build_score_matrix(lineup_df, player_df_indexed, player_cols)
    field_scores = build_score_matrix(field_lineup_df, player_df_indexed, player_cols)

    # Run portfolio optimization
    best_idx, portfolio_metrics, selected_lineups_df = monte_carlo_portfolio_search(lineup_df, my_scores, field_scores, payout_array, entry_fee, contest_size, portfolio_size, n_iterations, swap_size, random_seed, optimize_metric)

    print(f"Finished running contest {contestKey} portfolio optimization. Best {optimize_metric}: {portfolio_metrics[optimize_metric]:.4f}")

    # Write to CSV
    if write_file == True:
        selected_lineups_df.to_csv(os.path.join(baseball_path, "C02. Optimization", "4. Portfolio Lineups", f"Portfolio Lineups {contestKey}.csv"), index=False)


    return best_idx, portfolio_metrics, selected_lineups_df


# %%
# 5. Lineups Ranked
# Rank lineups by sortby criteria
def rank_lineups(contestKey, pareto_set, sense_list, sort_by, ascending_list, lineup_type='Portfolio', write_file=True):
    # Read in players
    try:
        player_sims = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv"))
    except:
        print(f"Error: Players file not found for contestKey {contestKey}")
        return None

    # Keep relevant variables
    player_sims.drop(columns={"Position", "Name", "ID", "Roster Position", "Salary", "Game Info", "TeamAbbrev", 'playerId', 'draftGroupId', 'game_id', 'Position2', 'imp_l', 'imp_r', "AvgPointsPerGame"}, inplace=True)

    # Clean Name + ID variable to remove space (this is for consistency for merging)
    player_sims['Name + ID'] = player_sims['Name + ID'].str.replace(r'\s*\(', '(', regex=True, flags=re.IGNORECASE)
        
    # Determine number of game simulations
    num_sims = sum('FP_' in column_name for column_name in player_sims.columns)

    
    # Read in daily lineups
    if lineup_type == 'Optimizer':  # If we're ranking all optimized lineups
        try:
            lineup_sims = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "2. Lineups", f"Lineups {contestKey}.csv"))
        except:
            print(f"Error: Lineups file not found for contestKey {contestKey}")
            return None
    elif lineup_type == 'Portfolio':  # If we're ranking only portfolio lineups
        try:
            lineup_sims = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "4. Portfolio Lineups", f"Portfolio Lineups {contestKey}.csv"))
        except:
            print(f"Error: Portfolio Lineups file not found for contestKey {contestKey}")
            return None
    else:
        print("Invalid lineup_type. Must be 'Optimizer' or 'Portfolio'.")
    
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

    
    # Write to CSV
    if write_file == True:
        lineup_sims.to_csv(os.path.join(baseball_path, "C02. Optimization", "5. Lineups Ranked", f"Lineups Ranked {contestKey}.csv"), index=False)
    
    
    return lineup_sims


# %%
# 6. Uploads
# Create upload file for DraftKings
def create_upload_file(contestKey, sort_by='Plus3'):
    # Read in lineup sims
    lineup_ranked = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "5. Lineups Ranked", f"Lineups Ranked {contestKey}.csv"))
    # # Sort (ascending because DK will put the bottom lineups at the top)
    # lineup_ranked.sort_values(by=sort_by, ascending=True, inplace=True)
    # Keep just the players
    lineup_ranked = lineup_ranked[['P', 'P.1', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF.1', 'OF.2']]
    
    # Rename variables to appease DK's upload
    lineup_ranked.rename(columns={'P.1':'P', 'OF.1':'OF', 'OF.2':'OF'}, inplace=True)


    return lineup_ranked


# %%
# 7. Entries
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
# Email upload and entry files
def email_upload_file(draftGroupId, contestKey, contestTime):    
    message = f"""\
    contestTime: {contestTime}
    draftGroupId: {draftGroupId}
    contestKey: {contestKey}

    Entries: https://www.draftkings.com/entry/upload
    Uploads: https://www.draftkings.com/lineup/upload
    """

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
    entry_path = os.path.join(baseball_path, "C02. Optimization", "7. Entries", f"Entries {draftGroupId}.csv")
    upload_path = os.path.join(baseball_path, "C02. Optimization", "6. Uploads", f"Upload {contestKey}.csv")

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
    filepath = rf"C:\Users\James\Documents\MLB\Data\C02. Optimization\7. Entries\Entries {draftGroupId}.csv"
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