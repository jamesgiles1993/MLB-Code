from U01Imports import *
from U02Functions import *
from U03Classes import *


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

        # Add this hard rescale:
        slot_targets = {'C': 100, '1B': 100, '2B': 100, '3B': 100, 'SS': 100, 'OF': 300, 'P': 200}

        player_df['n_positions'] = player_df['Roster Position'].str.split('/').str.len()

        for iteration in range(10):
            for pos, target in slot_targets.items():
                eligible = player_df['Roster Position'].str.contains(
                    f'(?:^|/){pos}(?:/|$)', regex=True
                )
                if not eligible.any():
                    continue
                frac_contrib = player_df.loc[eligible, 'rostership'] / player_df.loc[eligible, 'n_positions']
                current_sum = frac_contrib.sum()
                if current_sum > 0:
                    player_df.loc[eligible, 'rostership'] *= (target / current_sum)

        player_df.drop(columns=['n_positions'], inplace=True)



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


# 2. Lineups
# Create optimizer
def create_optimizer(contestKey, min_salary, stack_tuple, excluded_teams, min_starters, min_projection, strategy, max_deviation, progressive_growth, ignore_exposure=True):
    """
    Create a pydfs LineupOptimizer for a contestKey using a GLPK solver instance.
    stack_tuple: tuple of stack sizes
    """
    player_file = os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv")


    if not os.path.exists(player_file):
        print(f"[SKIP] Player file not found for contestKey={contestKey}")
        return None  # signal to skip        

    # Create Optimizer
    optimizer = get_optimizer(Site.DRAFTKINGS, Sport.BASEBALL, solver=GLPKPuLPSolver)


    # Load players CSV
    optimizer.load_players_from_csv(
        os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv")
    )

    # Minimum salary
    optimizer.set_min_salary_cap(min_salary)

    # Add stacks
    for stack_size in stack_tuple:
        optimizer.add_stack(
            TeamStack(size=stack_size, for_positions=['C', '1B', '2B', '3B', 'SS', 'OF'])
        )
    optimizer.stack = stack_tuple

    # Exclude teams
    optimizer.player_pool.exclude_teams(excluded_teams)

    # Minimum starters
    optimizer.set_min_starters(min_starters)

    # Minimum projection
    optimizer.player_pool.add_filters(PlayerFilter(from_value=min_projection))

    # Strategy
    if strategy == "Random":
        optimizer.set_fantasy_points_strategy(
            RandomFantasyPointsStrategy(max_deviation=max_deviation)
        )
    elif strategy == "Progressive":
        optimizer.set_fantasy_points_strategy(
            ProgressiveFantasyPointsStrategy(progressive_growth)
        )

    # Remove exposure limits
    if ignore_exposure == True:
        for player in optimizer.player_pool.get_players():
            player.min_exposure = 0
            player.max_exposure = 1


    return optimizer

# Run optimizers in parallel
def run_parallel_optimizers(contestKey, stack_dictionary, fallback_rules, num_optimizer_lineups, fallback="failure", ignore_exposure=True):
    """
    Run stack optimizers in parallel and optionally run fallback optimizers.

    fallback options:
        "always"  -> run fallback optimizers immediately
        "failure" -> run fallback only if primary fails
        "never"   -> never run fallback
    """

    player_file = os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv")

    if not os.path.exists(player_file):
        print(f"[SKIP] Player file not found for contestKey={contestKey}")
        return None

    positions_columns = None

    primary_rule = fallback_rules[0] if fallback_rules else {}
    fallback_rule = fallback_rules[1] if fallback_rules and len(fallback_rules) > 1 else None

    # -------------------------
    # Build PRIMARY tasks
    # -------------------------

    primary_tasks = []

    for stack_tuple, share in stack_dictionary.items():

        num_lineups_for_stack = int(num_optimizer_lineups * share)

        primary_tasks.append({
            "stack_tuple": stack_tuple,
            "num_lineups": num_lineups_for_stack,
            "fallback": False,
            "rule": primary_rule
        })

    # -------------------------
    # Optimizer runner
    # -------------------------

    def run_optimizer_task(task):

        nonlocal positions_columns

        stack_tuple = task["stack_tuple"]
        fallback_flag = task["fallback"]
        rule = task["rule"]

        try:
            optimizer = create_optimizer(
                contestKey=contestKey,
                min_salary=rule.get("min_salary", 49000),
                stack_tuple=stack_tuple,
                excluded_teams=rule.get("excluded_teams", []),
                min_starters=rule.get("min_starters", 10),
                min_projection=rule.get("min_projection", 5),
                strategy=rule.get("strategy", None),
                max_deviation=rule.get("max_deviation", 0.2),
                progressive_growth=rule.get("progressive_growth", 0.01),
                ignore_exposure=ignore_exposure
            )
        except Exception as e:
            print(f"[ERROR] Skipping stack {stack_tuple} fallback={fallback_flag} for contestKey={contestKey}: {e}")
            return []

        if positions_columns is None:
            positions_columns = [pos.name for pos in optimizer.settings.positions]

        try:
            start = time.time()
            lineups = list(optimizer.optimize(task["num_lineups"]))
            print(time.time() - start)
        except Exception as e:
            print(f"[ERROR] Optimization failed stack {stack_tuple} fallback={fallback_flag}: {e}")
            return []

        return [{"lineup": l, "stack_tuple": stack_tuple, "fallback": fallback_flag} for l in lineups]

    # -------------------------
    # Run PRIMARY optimizers
    # -------------------------

    with ThreadPoolExecutor() as executor:
        primary_results = list(executor.map(run_optimizer_task, primary_tasks))

    results = primary_results

    # -------------------------
    # Organize primary results
    # -------------------------

    stack_results = {}

    for lineup_dicts in primary_results:
        for d in lineup_dicts:

            st = d["stack_tuple"]

            if st not in stack_results:
                stack_results[st] = {"main": [], "fallback": []}

            stack_results[st]["main"].append(d["lineup"])

    # -------------------------
    # Determine if fallback needed
    # -------------------------

    need_fallback = False

    for stack_tuple, share in stack_dictionary.items():

        expected = int(num_optimizer_lineups * share)

        produced = len(stack_results.get(stack_tuple, {}).get("main", []))

        if produced < expected:
            need_fallback = True
            break

    # -------------------------
    # Run FALLBACK optimizers
    # -------------------------

    if fallback_rule and fallback in ("always", "failure"):

        if fallback == "always" or need_fallback:

            fallback_tasks = []

            for stack_tuple, share in stack_dictionary.items():

                num_lineups_for_stack = int(num_optimizer_lineups * share)

                fallback_tasks.append({
                    "stack_tuple": stack_tuple,
                    "num_lineups": num_lineups_for_stack,
                    "fallback": True,
                    "rule": fallback_rule
                })

            with ThreadPoolExecutor() as executor:
                fallback_results = list(executor.map(run_optimizer_task, fallback_tasks))

            results.extend(fallback_results)

            for lineup_dicts in fallback_results:
                for d in lineup_dicts:

                    st = d["stack_tuple"]

                    if st not in stack_results:
                        stack_results[st] = {"main": [], "fallback": []}

                    stack_results[st]["fallback"].append(d["lineup"])

    # -------------------------
    # Select final lineups
    # -------------------------

    final_lineups = []

    for stack_tuple, data in stack_results.items():

        main_lineups = data["main"]
        fallback_lineups = data["fallback"]

        num_expected = int(num_optimizer_lineups * stack_dictionary[stack_tuple])

        if len(main_lineups) >= num_expected:

            selected = main_lineups[:num_expected]
            fallback_flag = False

        elif len(fallback_lineups) > 0:

            selected = fallback_lineups[:num_expected]
            fallback_flag = True

        else:

            print(f"[WARN] Stack {stack_tuple} could not produce any lineups for contestKey={contestKey}")
            continue

        for l in selected:
            final_lineups.append((l, stack_tuple, fallback_flag))

    # -------------------------
    # Build dataframe
    # -------------------------

    rows = []

    for lineup, stack_tuple, fallback_flag in final_lineups:

        row = [f"{p.full_name}({p.id})" for p in lineup.players]

        row += [
            lineup.salary_costs,
            lineup.fantasy_points_projection,
            stack_tuple,
            fallback_flag
        ]

        rows.append(row)

    if not rows:
        print(f"[INFO] No lineups generated for contestKey={contestKey}")
        df = pd.DataFrame()

    else:
        columns = positions_columns + ["Budget", "FPPG", "Stack", "Fallback"]
        df = pd.DataFrame(rows, columns=columns)

        df.to_csv(os.path.join(baseball_path, "C02. Optimization", "2. Lineups", f"Lineups {contestKey}.csv"), index=False)


    return df


# 3. Field Lineups
def _generate_field_lineups_single(contestKey, num_lineups, min_salary, max_salary,
                                    stack_share_dict, pitcher_exp, team_exp, max_attempts,
                                    player_noise=0.0, team_noise=0.0, min_rostership=0.0,
                                    pitcher_pattern_weights=None, debug_player=None):
    # Default pitcher pattern weights: equal across all 5 patterns
    # 0=bb, 1=ppb, 2=pbp, 3=bpbp, 4=pbpb
    if pitcher_pattern_weights is None:
        pitcher_pattern_weights = [0.20, 0.20, 0.20, 0.20, 0.20]
    pitcher_pattern_weights = np.array(pitcher_pattern_weights, dtype=float)
    pitcher_pattern_weights /= pitcher_pattern_weights.sum()
    """
    Generate field lineups for a single contest.

    Uses a unified cross-stack sequential picker:
    At each step, all open (player, slot) pairs across all stack groups are
    considered simultaneously, weighted by ownership. This means high-ownership
    players are drawn early regardless of which stack they belong to.

    Stack size assignment uses ownership-weighted random sampling so high-ownership
    teams are more likely to get larger stacks but not guaranteed.

    Diversity penalty downweights recently selected players to reduce
    position-monopoly overrepresentation.

    Team stack rate cap prevents low-ownership teams from being over-stacked.

    rostership_noise: std dev of lognormal noise applied to rostership weights
                      before generation. Adds run-to-run variability so the same
                      players aren't always over/underrepresented. Default 0.1 (~10%).
                      Set to 0 for deterministic weights.
    """
    try:
        df = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players",
                                      f"Players {contestKey}.csv"), encoding='iso-8859-1')
    except Exception as e:
        print(f"Error reading player file for {contestKey}: {e}")
        return pd.DataFrame()

    rng = np.random.default_rng()
    df = df.copy()
    df['Salary'] = pd.to_numeric(df['Salary'], errors='coerce')
    df = df.dropna(subset=['Salary'])
    df = df.reset_index(drop=True)

    # Apply two-level multiplicative lognormal noise to rostership:
    # 1. Team-level noise: all players on a team get the same boost/penalty
    #    reflecting correlated ownership shifts (whole stack goes up/down)
    # 2. Player-level noise: independent per-player variation
    # Exclude players below min_rostership threshold
    # Real DFS players almost never roster near-zero ownership players
    df = df[df['rostership'] >= min_rostership].reset_index(drop=True)

    df['p'] = (df['rostership'] / 100).clip(lower=0)

    if team_noise > 0:
        for team in df['TeamAbbrev'].unique():
            team_mask = df['TeamAbbrev'] == team
            team_boost = rng.lognormal(mean=0, sigma=team_noise)
            df.loc[team_mask, 'p'] *= team_boost

    if player_noise > 0:
        player_boost = rng.lognormal(mean=0, sigma=player_noise, size=len(df))
        df['p'] *= player_boost

    df['p'] = df['p'].clip(lower=0)

    total_p = df['p'].sum()
    df['p'] = df['p'] / total_p if total_p > 0 else 1 / len(df)

    df['pos_list'] = df['Roster Position'].str.split('/')
    df['is_pitcher'] = df['Roster Position'] == 'P'

    hitters  = df[~df['is_pitcher']].copy().reset_index(drop=True)
    pitchers = df[df['is_pitcher']].copy().reset_index(drop=True)

    h_salary  = hitters['Salary'].values.astype(float)
    h_team    = hitters['TeamAbbrev'].values
    h_p       = hitters['p'].values
    h_name    = hitters['Name + ID'].values
    h_pos     = hitters['pos_list'].values



    # Build opponent lookup from Game Info: team → opposing team
    # e.g. "PHI@CHC 04/21/2026 07:40PM ET" → PHI plays CHC, CHC plays PHI
    game_opponents = {}
    for game_info in df['Game Info'].dropna().unique():
        try:
            matchup = game_info.split(' ')[0]  # e.g. "PHI@CHC"
            away, home = matchup.split('@')
            game_opponents[away] = home
            game_opponents[home] = away
        except Exception:
            pass



    p_salary  = pitchers['Salary'].values.astype(float)
    p_p       = pitchers['p'].values ** pitcher_exp
    p_name    = pitchers['Name + ID'].values
    p_min_sal = p_salary.min() if len(p_salary) > 0 else 0

    p_p_norm = p_p / p_p.sum() if p_p.sum() > 0 else np.ones(len(p_p)) / len(p_p)

    pos_order      = [('C', 1), ('1B', 1), ('2B', 1), ('3B', 1), ('SS', 1), ('OF', 3)]
    pos_slots      = [pos for pos, cnt in pos_order for _ in range(cnt)]
    n_hitter_slots = len(pos_slots)

    pos_eligible = {
        pos: np.where([pos in pl for pl in hitters['pos_list'].values])[0]
        for pos, _ in pos_order
    }

    h_pos_count = np.array([
        max(1, sum(1 for pos in ['C', '1B', '2B', '3B', 'SS', 'OF'] if pos in pl))
        for pl in hitters['pos_list'].values
    ])

    teams = hitters['TeamAbbrev'].unique()
    team_to_idx = {t: i for i, t in enumerate(teams)}

    # Use geometric mean of top-5 hitter ownerships as team stack weight.
    # This better reflects how often a team gets 5-stacked vs aggregate sum,
    # which over-weights teams with many moderately-owned players.
    def team_stack_weight(team):
        ownerships = np.sort(
            hitters.loc[hitters['TeamAbbrev'] == team, 'rostership'].values
        )[::-1][:5]
        if len(ownerships) == 0:
            return 0.0
        # Geometric mean of top-5 (or fewer) players
        return np.prod(ownerships) ** (1.0 / len(ownerships))

    team_rost = np.array([team_stack_weight(t) for t in teams])
    team_weights = np.clip(team_rost, 0, None) ** team_exp
    tw = team_weights.sum()
    team_weights = team_weights / tw if tw > 0 else np.ones(len(teams)) / len(teams)

    constructions = list(stack_share_dict.keys())
    cw = np.array([stack_share_dict[c] for c in constructions], dtype=float)
    cw /= cw.sum()

    salary_target = (min_salary + max_salary) / 2.0

    # Cumulative appearance tracking only — no diversity window needed
    # for field lineup generation since lineup-to-lineup diversity doesn't matter
    diversity_window = 1  # effectively disabled

    h_appearances     = np.zeros(len(hitters), dtype=float)
    p_appearances     = np.zeros(len(pitchers), dtype=float)

    # Cumulative appearance tracking (boosts chronically underselected players)
    h_appearances_cum = np.zeros(len(hitters), dtype=float)
    p_appearances_cum = np.zeros(len(pitchers), dtype=float)

    # Team stack rate tracking
    avg_stacks_per_lineup = 1.6
    team_target_rate  = {t: team_weights[team_to_idx[t]] * avg_stacks_per_lineup for t in teams}
    team_stack_counts = {t: 0 for t in teams}

    # Team acceptance rate tracking
    # Teams whose lineups fail often (salary floor) get boosted
    # Teams whose lineups always pass get gently penalized
    team_attempts = {t: 0 for t in teams}
    team_accepts  = {t: 0 for t in teams}

    # Team acceptance rate tracking
    # Teams whose lineups fail often get boosted; teams that always pass get penalized
    team_attempts = {t: 0 for t in teams}
    team_accepts  = {t: 0 for t in teams}

    # Debug tracking
    debug_idx        = None
    debug_accepted   = 0
    debug_rej_stack  = 0
    debug_rej_salary = 0
    debug_rej_assign = 0
    debug_not_drawn  = 0

    if debug_player is not None:
        matches = [i for i in range(len(hitters)) if debug_player.lower() in h_name[i].lower()]
        if matches:
            debug_idx = matches[0]
            print(f"Tracking '{debug_player}' → {h_name[debug_idx]} (hitter idx {debug_idx})")
        else:
            print(f"'{debug_player}' not found in hitters")

    reject_stack   = 0
    reject_salary  = 0
    reject_pitcher = 0

    lineups        = []
    lineup_budgets = []
    lineup_stacks  = []
    n_generated    = 0
    total_attempts = 0

    while n_generated < num_lineups and total_attempts < num_lineups * max_attempts:
        total_attempts += 1
        debug_in_attempt = False

        cw = np.nan_to_num(cw, nan=0.0); cw_s = cw.sum(); cw = cw/cw_s if cw_s > 0 else np.ones(len(cw))/len(cw)
        stack_str  = rng.choice(constructions, p=cw)
        all_sizes  = sorted([int(s) for s in stack_str.split('-')], reverse=True)
        true_sizes = [s for s in all_sizes if s >= 2]
        free_count = sum(1 for s in all_sizes if s == 1)

        n_true = len(true_sizes)
        if n_true > len(teams):
            continue

        if n_true > 0:
            adjusted_weights = team_weights.copy()
            global_acceptance = n_generated / max(1, total_attempts)

            for i, t in enumerate(teams):
                # Stack rate cap: prevent over-stacking low-ownership teams
                actual_rate = team_stack_counts[t] / max(1, n_generated)
                target_rate = team_target_rate[t]
                if actual_rate > target_rate:
                    adjusted_weights[i] *= target_rate / actual_rate

                # Acceptance rate adjustment: boost teams that fail often,
                # penalize teams that always pass (salary-driven bias correction)
                team_accept_rate = team_accepts[t] / max(1, team_attempts[t])
                if team_attempts[t] >= 10:  # only adjust after enough data
                    ratio = global_acceptance / max(0.01, team_accept_rate)
                    adjusted_weights[i] *= np.clip(ratio, 0.3, 3.0)

            adjusted_weights = np.nan_to_num(adjusted_weights, nan=0.0, posinf=0.0, neginf=0.0)
            adj_sum = adjusted_weights.sum()
            adjusted_weights = adjusted_weights / adj_sum if adj_sum > 0 else team_weights.copy()

            # Guard: need at least n_true teams with non-zero weight
            nonzero_teams = (adjusted_weights > 0).sum()
            if nonzero_teams < n_true:
                reject_stack += 1
                continue
            sel_idx   = rng.choice(len(teams), size=n_true, replace=False, p=adjusted_weights)
            sel_teams = teams[sel_idx]

            remaining_teams = list(sel_teams)
            assignment = []
            for sz in true_sizes:
                w = np.array([team_rost[team_to_idx[t]] for t in remaining_teams], dtype=float)
                w /= w.sum()
                w = np.nan_to_num(w, nan=0.0); ws = w.sum(); w = w/ws if ws > 0 else np.ones(len(w))/len(w)
                ci = int(rng.choice(len(remaining_teams), p=w))
                assignment.append((remaining_teams[ci], sz))
                remaining_teams.pop(ci)
            stack_counts_orig = dict(assignment)
        else:
            stack_counts_orig = {}

        true_stack_set = set(stack_counts_orig.keys())



        free_pick_min_salary = 0.0  # no salary floor — let salary constraint handle it

        # Track team attempts
        for team in stack_counts_orig:
            team_attempts[team] += 1

        # Unified cross-stack sequential picker
        # Fill order is randomized weighted by stack size so small stacks
        # (including size-1 mini-stacks) occasionally go first, preventing
        # cheap players from always being left to fill last with no salary room.
        # Pitchers are included in the fill pool with their own 2-slot budget.

        stack_remaining   = dict(stack_counts_orig)
        total_stack_picks = sum(stack_remaining.values())

        team_avail = {
            team: list(np.where(h_team == team)[0])
            for team in true_stack_set
        }

        # Pitcher fill pattern — controls when pitchers are selected
        # relative to hitter stacks. Equal weights by default (tunable).
        #
        # 0 = bb:   all hitters first, both pitchers last (original)
        # 1 = ppb:  both pitchers first, then all hitters
        # 2 = pbp:  one pitcher, all hitters, one pitcher
        # 3 = bpbp: primary stack, pitcher, remaining stacks, pitcher
        # 4 = pbpb: pitcher, primary stack, pitcher, remaining stacks
        #
        pitcher_position = rng.choice(5, p=pitcher_pattern_weights)
        pitchers_to_fill = 2  # total pitchers needed

        remaining_slots = list(pos_slots)
        chosen_h_set    = set()
        chosen_h_list   = []
        chosen_p_list   = []
        spent           = 0.0
        valid           = True
        p_spent         = 0.0

        def pick_one_pitcher(spent_so_far):
            """Pick one pitcher given current salary spent.
            Excludes pitchers whose opponent is being stacked in hitter slots.
            Uses loose salary bounds — final validation catches out-of-range lineups.
            """
            # Pitchers still needed after this one
            p_after      = pitchers_to_fill - len(chosen_p_list) - 1
            remaining    = max_salary - spent_so_far
            need_at_least = min_salary - spent_so_far

            p_feas_local = np.where(
                (p_salary >= need_at_least - p_salary.max() * p_after) &
                (p_salary <= remaining - p_min_sal * p_after)
            )[0]
            if len(p_feas_local) == 0:
                p_feas_local = np.arange(len(pitchers))

            # Exclude pitchers whose opponent is in the hitter stack
            # (avoid negative correlation between pitcher and opposing hitters)
            if true_stack_set and game_opponents:
                no_opp_stack = np.array([
                    i for i in p_feas_local
                    if game_opponents.get(pitchers['TeamAbbrev'].iloc[i]) not in true_stack_set
                ])
                if len(no_opp_stack) >= 1:
                    p_feas_local = no_opp_stack


            if len(p_feas_local) == 0:
                return None
            for _ in range(10):
                expected_p = p_p_norm[p_feas_local] * max(1, n_generated)
                p_boost    = np.clip(
                    expected_p / np.maximum(1.0, p_appearances_cum[p_feas_local]),
                    0.5, 3.0
                )
                pw   = p_p_norm[p_feas_local] * p_boost
                pw   = np.nan_to_num(pw, nan=0.0, posinf=0.0, neginf=0.0)
                pw_s = pw.sum()
                if pw_s <= 0 or (pw > 0).sum() == 0:
                    pw = np.ones(len(p_feas_local)) / len(p_feas_local)
                else:
                    pw /= pw_s
                try:
                    pi = int(rng.choice(p_feas_local, p=pw))
                except ValueError:
                    # Fallback: uniform random choice
                    pi = int(rng.choice(p_feas_local))
                if pi not in chosen_p_list:
                    return pi
            return None

        # Helper: fill one pitcher now
        def add_pitcher():
            pi = pick_one_pitcher(spent + sum(p_salary[i] for i in chosen_p_list))
            if pi is None:
                return False
            chosen_p_list.append(pi)
            return True

        # Pattern 1 (ppb): both pitchers first
        if pitcher_position == 1:
            for _ in range(2):
                if not add_pitcher():
                    valid = False; reject_pitcher += 1; break
            if not valid:
                continue

        # Pattern 2 (pbp) or 4 (pbpb): one pitcher first
        elif pitcher_position in (2, 4):
            if not add_pitcher():
                valid = False; reject_pitcher += 1
            if not valid:
                continue

        primary_stack_size = max(stack_counts_orig.values()) if stack_counts_orig else 0
        primary_stack_done = 0  # track when primary stack is complete

        # Precompute reserved slots: if only one player across all stack teams
        # can fill a given slot, reserve that slot for them exclusively.
        # This prevents high-ownership solo-position players (like Arenado at 3B)
        # from being locked out when their slot is taken by another stack first.
        def compute_reserved_slots(remaining_slots, stack_remaining, chosen_h_set):
            slot_eligible = {}  # slot_pos -> list of (pi, team)
            for slot_pos in set(remaining_slots):
                eligible = []
                for team, rem in stack_remaining.items():
                    if rem <= 0:
                        continue
                    for pi in team_avail[team]:
                        if pi not in chosen_h_set and slot_pos in h_pos[pi]:
                            eligible.append((pi, team))
                slot_eligible[slot_pos] = eligible
            # Reserve slots where only one player is eligible
            reserved = {}  # slot_pos -> (pi, team)
            for slot_pos, eligible in slot_eligible.items():
                if len(eligible) == 1:
                    reserved[slot_pos] = eligible[0]
            return reserved

        for pick_num in range(total_stack_picks):
            # Pattern 3 (bpbp): add pitcher after primary stack completes
            # Pattern 4 (pbpb): add second pitcher after primary stack completes
            if pitcher_position in (3, 4) and primary_stack_done == primary_stack_size and len(chosen_p_list) < 2:
                if pitcher_position == 3 and len(chosen_p_list) == 0:
                    if not add_pitcher():
                        valid = False; reject_pitcher += 1; break
                elif pitcher_position == 4 and len(chosen_p_list) == 1:
                    if not add_pitcher():
                        valid = False; reject_pitcher += 1; break

            # Check for reserved slots — force pick if only one player can fill a slot
            reserved = compute_reserved_slots(remaining_slots, stack_remaining, chosen_h_set)
            if reserved:
                # Pick the reserved player with highest ownership first
                best_slot = max(reserved.keys(),
                                key=lambda s: h_p[reserved[s][0]])
                forced_pi, forced_team = reserved[best_slot]
                # Place this player
                chosen_h_set.add(forced_pi)
                chosen_h_list.append(forced_pi)
                spent += h_salary[forced_pi]
                stack_remaining[forced_team] -= 1
                remaining_slots.remove(best_slot)
                if debug_idx is not None and forced_pi == debug_idx:
                    debug_in_attempt = True
                if stack_counts_orig.get(forced_team, 0) == primary_stack_size:
                    primary_stack_done += 1
                continue

            candidates   = []
            seen_players = {}
            for team, rem in stack_remaining.items():
                if rem == 0:
                    continue
                avail = [i for i in team_avail[team] if i not in chosen_h_set]
                for pi in avail:
                    if pi not in seen_players:
                        for slot_i, slot_pos in enumerate(remaining_slots):
                            if slot_pos in h_pos[pi]:
                                seen_players[pi] = (slot_pos, slot_i, team)
                                candidates.append((pi, slot_pos, slot_i, team))
                                break

            if not candidates:
                valid = False
                reject_stack += 1
                if debug_idx is not None:
                    debug_rej_stack += 1
                break

            weights = []
            for pi, slot_pos, slot_i, team in candidates:
                # Boost players who are underselected relative to their expected rate
                expected = h_p[pi] * max(1, n_generated)
                underselect_boost = expected / max(1.0, h_appearances_cum[pi])
                underselect_boost = np.clip(underselect_boost, 0.5, 3.0)
                w = h_p[pi] * underselect_boost
                weights.append(w if np.isfinite(w) else 0.0)

            weights = np.array(weights)
            ws = weights.sum()
            if ws <= 0:
                weights = np.array([h_p[pi] for pi, _, _, _ in candidates])
                ws = weights.sum()
                if ws <= 0:
                    valid = False
                    reject_stack += 1
                    if debug_idx is not None:
                        debug_rej_stack += 1
                    break
            weights /= ws

            weights = np.nan_to_num(np.array(weights, dtype=float), nan=0.0); ws2 = weights.sum(); weights = weights/ws2 if ws2 > 0 else np.ones(len(weights))/len(weights)
            chosen_idx = int(rng.choice(len(candidates), p=weights))
            chosen_pi, chosen_slot_pos, chosen_slot_i, chosen_team = candidates[chosen_idx]

            if debug_idx is not None and chosen_pi == debug_idx:
                debug_in_attempt = True

            chosen_h_set.add(chosen_pi)
            chosen_h_list.append(chosen_pi)
            spent += h_salary[chosen_pi]
            stack_remaining[chosen_team] -= 1
            remaining_slots.remove(chosen_slot_pos)

            # Track primary stack completion for bpbp/pbpb patterns
            if stack_counts_orig.get(chosen_team, 0) == primary_stack_size:
                primary_stack_done += 1

        if not valid:
            continue

        # Free picks
        for _ in range(free_count):
            if not remaining_slots:
                valid = False
                reject_stack += 1
                if debug_idx is not None:
                    debug_rej_stack += 1
                break

            slot_pos = remaining_slots[0]
            eligible = [i for i in pos_eligible[slot_pos]
                        if i not in chosen_h_set and h_team[i] not in true_stack_set]
            if not eligible:
                eligible = [i for i in pos_eligible[slot_pos] if i not in chosen_h_set]
            if not eligible:
                valid = False
                reject_stack += 1
                if debug_idx is not None:
                    debug_rej_stack += 1
                break

            if debug_idx is not None and debug_idx in eligible:
                debug_in_attempt = True

            expected = h_p[eligible] * max(1, n_generated)
            underselect_boosts = np.clip(
                expected / np.maximum(1.0, h_appearances_cum[eligible]),
                0.5, 3.0
            )

            weights = (h_p[eligible] / h_pos_count[eligible]) * underselect_boosts
            weights = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)
            ws = weights.sum()
            weights = weights / ws if ws > 0 else np.ones(len(eligible)) / len(eligible)

            weights = np.nan_to_num(weights, nan=0.0); ws3 = weights.sum(); weights = weights/ws3 if ws3 > 0 else np.ones(len(weights))/len(weights)
            chosen = eligible[int(rng.choice(len(eligible), p=weights))]

            if debug_idx is not None and chosen == debug_idx:
                debug_in_attempt = True

            chosen_h_list.append(chosen)
            chosen_h_set.add(chosen)
            spent += h_salary[chosen]
            remaining_slots.pop(0)

        if not valid or remaining_slots:
            if remaining_slots:
                reject_stack += 1
                if debug_idx is not None:
                    if debug_in_attempt: debug_rej_stack += 1
                    else: debug_not_drawn += 1
            continue

        lineup_salary = spent

        # Final position assignment
        final_assignment = [-1] * n_hitter_slots
        used = set()
        valid_assign = True
        for slot_idx in sorted(range(n_hitter_slots),
                               key=lambda i: sum(1 for pi in chosen_h_list
                                                 if pos_slots[i] in h_pos[pi])):
            slot_pos = pos_slots[slot_idx]
            eligible_for_slot = [pi for pi in chosen_h_list
                                 if pi not in used and slot_pos in h_pos[pi]]
            if not eligible_for_slot:
                valid_assign = False
                break
            chosen_for_slot = max(eligible_for_slot, key=lambda pi: h_p[pi])
            final_assignment[slot_idx] = chosen_for_slot
            used.add(chosen_for_slot)

        if not valid_assign or -1 in final_assignment:
            reject_stack += 1
            if debug_idx is not None:
                if debug_in_attempt: debug_rej_assign += 1
                else: debug_not_drawn += 1
            continue

        # Fill remaining pitchers after hitters
        pitchers_remaining = pitchers_to_fill - len(chosen_p_list)
        for _ in range(pitchers_remaining):
            pi = pick_one_pitcher(lineup_salary + sum(p_salary[i] for i in chosen_p_list))
            if pi is None:
                valid = False; reject_pitcher += 1
                if debug_idx is not None:
                    if debug_in_attempt: debug_rej_salary += 1
                    else: debug_not_drawn += 1
                break
            chosen_p_list.append(pi)

        if not valid:
            continue

        chosen_p = chosen_p_list

        total_salary = lineup_salary + sum(p_salary[i] for i in chosen_p)

        # Final salary validation — catches any edge cases from mid-sequence picks
        if not (min_salary <= total_salary <= max_salary):
            reject_salary += 1
            continue

        lineup_names = (
            [p_name[i] for i in chosen_p] +
            [h_name[final_assignment[i]] for i in range(n_hitter_slots)]
        )

        if len(lineup_names) != len(set(lineup_names)):
            continue

        lineups.append(lineup_names)
        lineup_budgets.append(total_salary)
        lineup_stacks.append(stack_str)
        n_generated += 1

        if debug_idx is not None and debug_in_attempt:
            debug_accepted += 1

        # Update cumulative appearance tracking
        for pi in final_assignment:
            h_appearances_cum[pi] += 1.0
        for pi in chosen_p_list:
            p_appearances_cum[pi] += 1.0

        # Update team stack counts and acceptance tracking
        for team in stack_counts_orig:
            team_stack_counts[team] += 1
            team_accepts[team]      += 1



    # Debug summary
    if debug_idx is not None:
        drawn = debug_accepted + debug_rej_stack + debug_rej_salary + debug_rej_assign
        print(f"\n=== DEBUG: '{debug_player}' ===")
        print(f"  Drawn into attempt:       {drawn:,} / {total_attempts:,} attempts ({drawn/max(1,total_attempts):.1%})")
        print(f"  Accepted lineups:         {debug_accepted:,} ({debug_accepted/max(1,n_generated):.1%} of generated)")
        print(f"  Rejected — stack/pos:     {debug_rej_stack:,}")
        print(f"  Rejected — salary:        {debug_rej_salary:,}")
        print(f"  Rejected — assign:        {debug_rej_assign:,}")
        print(f"  Not drawn at all:         {debug_not_drawn:,}")
        print(f"  Expected ownership:       {hitters['rostership'].iloc[debug_idx]:.1f}%")
        print(f"  Actual ownership:         {debug_accepted/max(1,n_generated)*100:.1f}%")
        print()

    print(f"[{contestKey}] {n_generated} lineups in {total_attempts} attempts. "
          f"Rejections — stack: {reject_stack}, salary: {reject_salary}, pitchers: {reject_pitcher}")

    if not lineups:
        print(f"Warning: No lineups generated for {contestKey}.")
        return pd.DataFrame()

    columns_order = ['P', 'P.1', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF.1', 'OF.2']
    lineup_df = pd.DataFrame(lineups, columns=columns_order)
    lineup_df['Budget'] = lineup_budgets
    lineup_df['Stack']  = lineup_stacks

    fp_cols    = [c for c in df.columns if c.startswith('FP_')]
    fp_mapping = df.set_index('Name + ID')[fp_cols]
    fp_list    = [fp_mapping.reindex(lineup_df[pos]).reset_index(drop=True) for pos in columns_order]
    fp_concat  = pd.concat(fp_list, axis=1)
    fp_sums    = fp_concat.T.groupby(level=0).sum().T
    lineup_df  = pd.concat([lineup_df, fp_sums], axis=1)
    lineup_df['FPPG'] = fp_sums.mean(axis=1)
    lineup_df  = lineup_df[[c for c in lineup_df.columns if not c.startswith('FP_')]]
    lineup_df  = lineup_df.replace(r' \(', '(', regex=True)

    return lineup_df


def _calibrate_ownership(lineup_df, player_df, n_select, player_cols=None):
    """
    Greedily select a subsample of lineups that best matches projected ownership.

    At each step, picks the lineup from the remaining pool that minimizes
    the total squared error between current ownership and projected ownership.

    Parameters
    ----------
    lineup_df  : DataFrame of generated lineups
    player_df  : DataFrame with 'Name + ID' and 'rostership' columns
    n_select   : number of lineups to select
    player_cols: list of player columns in lineup_df (default: P,P.1,C,1B,2B,3B,SS,OF,OF.1,OF.2)

    Returns
    -------
    DataFrame of selected lineups (n_select rows)
    """
    if player_cols is None:
        player_cols = ['P', 'P.1', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF.1', 'OF.2']

    n_available = len(lineup_df)
    n_select    = min(n_select, n_available)

    # Build target ownership dict: name -> fraction (0-1)
    # Handle both "Name (ID)" and "Name(ID)" formats
    target = dict(zip(
        player_df['Name + ID'].str.replace(' (', '(', regex=False),
        player_df['rostership'] / 100.0
    ))
    # Also add original format as fallback
    for name, rost in zip(player_df['Name + ID'], player_df['rostership'] / 100.0):
        if name not in target:
            target[name] = rost

    # Get all unique players and build index
    cols_present = [c for c in player_cols if c in lineup_df.columns]
    all_names    = pd.unique(lineup_df[cols_present].values.ravel())
    all_names    = [str(n) for n in all_names if isinstance(n, str) and n != 'nan']
    player_index = {p: i for i, p in enumerate(all_names)}
    n_players    = len(all_names)

    # Build binary matrix M: M[i,j] = 1 if lineup i contains player j
    M = np.zeros((n_available, n_players), dtype=np.float32)
    for li, (_, row) in enumerate(lineup_df.iterrows()):
        for c in cols_present:
            p = str(row[c])
            if p in player_index:
                M[li, player_index[p]] = 1.0

    # Target ownership vector aligned to all_names
    target_vec = np.array([target.get(p, 0.0) for p in all_names], dtype=np.float32)

    # Greedy selection — fully vectorized inner loop
    current_counts = np.zeros(n_players, dtype=np.float32)
    selected_idx   = []
    remaining_mask = np.ones(n_available, dtype=bool)

    for step in range(n_select):
        n_so_far = float(step + 1)
        # For each remaining lineup, compute SSE if added
        # new_actual[i] = (current_counts + M[i]) / n_so_far
        new_actuals = (current_counts + M[remaining_mask]) / n_so_far  # (n_rem, n_players)
        sses        = ((new_actuals - target_vec) ** 2).sum(axis=1)    # (n_rem,)
        best_rem    = int(np.argmin(sses))
        best_orig   = np.where(remaining_mask)[0][best_rem]

        selected_idx.append(int(best_orig))
        remaining_mask[best_orig] = False
        current_counts += M[best_orig]

    return lineup_df.iloc[selected_idx].reset_index(drop=True)


def _generate_and_calibrate(contestKey, num_lineups, min_salary, max_salary,
                             stack_share_dict, pitcher_exp, team_exp, max_attempts,
                             player_noise, team_noise, min_rostership,
                             pitcher_pattern_weights,
                             calibrate, calibrate_oversample, baseball_path, write_file):
    """Generate, calibrate, and optionally write lineups for a single contest.
    Runs entirely in one worker so everything is parallelized."""
    n_generate = num_lineups * calibrate_oversample if calibrate else num_lineups
    lineup_df  = _safe_generate_field_lineups(
        contestKey, n_generate, min_salary, max_salary,
        stack_share_dict, pitcher_exp, team_exp, max_attempts,
        player_noise, team_noise, min_rostership, pitcher_pattern_weights
    )
    if calibrate and not lineup_df.empty and len(lineup_df) > num_lineups:
        try:
            player_df = pd.read_csv(
                os.path.join(baseball_path, "C02. Optimization", "1. Players",
                             f"Players {contestKey}.csv"), encoding='iso-8859-1'
            )
            print(f"[{contestKey}] Calibrating {len(lineup_df)} → {num_lineups} lineups...")
            lineup_df = _calibrate_ownership(lineup_df, player_df, num_lineups)
        except Exception as e:
            print(f"[{contestKey}] Calibration failed ({e}), using first {num_lineups}")
            lineup_df = lineup_df.head(num_lineups)
    else:
        lineup_df = lineup_df.head(num_lineups)

    # Write immediately after calibration — don't wait for all contests to finish
    if write_file and not lineup_df.empty:
        out_path = os.path.join(baseball_path, "C02. Optimization", "3. Field Lineups",
                                f"Field Lineups {contestKey}.csv")
        lineup_df.to_csv(out_path, index=False, encoding='iso-8859-1')
        print(f"[{contestKey}] Written {len(lineup_df)} lineups.")

    return lineup_df


def _safe_generate_field_lineups(contestKey, num_lineups, min_salary, max_salary,
                                  stack_share_dict, pitcher_exp, team_exp, max_attempts,
                                  player_noise, team_noise, min_rostership,
                                  pitcher_pattern_weights):
    """Wrapper around _generate_field_lineups_single that catches all errors."""
    try:
        return _generate_field_lineups_single(
            contestKey, num_lineups, min_salary, max_salary,
            stack_share_dict, pitcher_exp, team_exp, max_attempts,
            player_noise=player_noise, team_noise=team_noise,
            min_rostership=min_rostership,
            pitcher_pattern_weights=pitcher_pattern_weights,
        )
    except Exception as e:
        print(f"[{contestKey}] ERROR: {e}")
        return pd.DataFrame()


MIN_SALARY_LOOKUP = {
    range(1, 6): 46000,
    range(6, 7): 47000,
    range(7, 9): 48000,
    range(9, 16): 49000,
}

def _resolve_min_salary(contestKey, contest_df):
    slate_size = contest_df[contest_df['contestKey'] == contestKey]['slate_size'].iloc[0]
    min_salary = next(v for k, v in MIN_SALARY_LOOKUP.items() if slate_size in k)
    # print(f"Minimum salary of {min_salary} for slate of {slate_size} games.")
    return min_salary
    


def create_all_field_lineups(contestKeys,
                             contest_df=None,
                             num_lineups=1000,
                             max_salary=50000,
                             stack_share_dict=None,
                             pitcher_exp=1.0,
                             team_exp=1.0,
                             max_attempts=10000,
                             player_noise=0.0,
                             team_noise=0.0,
                             min_rostership=0.0,
                             pitcher_pattern_weights=None,
                             calibrate=False,
                             calibrate_oversample=3,
                             write_file=True,
                             n_jobs=4,
                             debug_player=None):
    """
    Generate DFS field lineups for one or more contests.

    player_noise:            std dev of per-player lognormal noise. Default 0.05 (~5%).
    team_noise:              std dev of per-team lognormal noise. Default 0.1 (~10%).
    min_rostership:          minimum projected ownership % to include a player. Default 1.0%.
    pitcher_pattern_weights: list of 5 weights for pitcher fill patterns.
                             [bb, ppb, pbp, bpbp, pbpb] — default equal [0.2]*5.
                             bb   = both pitchers last (original)
                             ppb  = both pitchers first
                             pbp  = pitcher, all hitters, pitcher
                             bpbp = primary stack, pitcher, rest of hitters, pitcher
                             pbpb = pitcher, primary stack, pitcher, rest of hitters
    debug_player:            optional player name substring to track rejection stats.
    calibrate:               if True, generate calibrate_oversample * num_lineups lineups
                             then greedily select num_lineups that best match projected ownership.
    calibrate_oversample:    how many times more lineups to generate before calibrating. Default 3.
    """

    # Determine actual number to generate (oversample if calibrating)
    n_generate = num_lineups * calibrate_oversample if calibrate else num_lineups
    if calibrate:
        print(f"Calibration enabled: generating {n_generate} lineups, selecting {num_lineups}")

    if len(contestKeys) == 1:
        min_salary = _resolve_min_salary(contestKeys[0], contest_df)
        lineup_df = _safe_generate_field_lineups(
            contestKeys[0], n_generate, min_salary, max_salary,
            stack_share_dict, pitcher_exp, team_exp, max_attempts,
            player_noise, team_noise, min_rostership,
            pitcher_pattern_weights
        )
        if calibrate and not lineup_df.empty and len(lineup_df) > num_lineups:
            try:
                player_df = pd.read_csv(
                    os.path.join(baseball_path, "C02. Optimization", "1. Players",
                                 f"Players {contestKeys[0]}.csv"), encoding='iso-8859-1'
                )
                print(f"[{contestKeys[0]}] Calibrating {len(lineup_df)} → {num_lineups} lineups...")
                lineup_df = _calibrate_ownership(lineup_df, player_df, num_lineups)
            except Exception as e:
                print(f"[{contestKeys[0]}] Calibration failed ({e}), using first {num_lineups}")
                lineup_df = lineup_df.head(num_lineups)
        else:
            lineup_df = lineup_df.head(num_lineups)
        if write_file and not lineup_df.empty:
            lineup_df.to_csv(
                os.path.join(baseball_path, "C02. Optimization", "3. Field Lineups",
                             f"Field Lineups {contestKeys[0]}.csv"),
                index=False, encoding='iso-8859-1'
            )
        return lineup_df

    else:
        dfs = Parallel(n_jobs=min(n_jobs, len(contestKeys)), backend="loky")(
            delayed(_generate_and_calibrate)(
                ck, num_lineups, _resolve_min_salary(ck, contest_df), max_salary,
                stack_share_dict, pitcher_exp, team_exp, max_attempts,
                player_noise, team_noise, min_rostership,
                pitcher_pattern_weights,
                calibrate, calibrate_oversample, baseball_path, write_file
            )
            for ck in contestKeys
        )

        return pd.concat([d for d in dfs if not d.empty], ignore_index=True)


# Analyze Ownership
def analyze_ownership(contestKey):
    PLAYER_COLS = ['P', 'P.1', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF.1', 'OF.2']

    player_df = pd.read_csv(
        os.path.join(baseball_path, "C02. Optimization", "1. Players", f"Players {contestKey}.csv"),
        encoding='iso-8859-1'
    )
    field_df = pd.read_csv(
        os.path.join(baseball_path, "C02. Optimization", "3. Field Lineups", f"Field Lineups {contestKey}.csv"),
        encoding='iso-8859-1'
    )

    player_df['Name + ID'] = player_df['Name + ID'].str.replace(" (", "(", regex=False)

    # Compute actual ownership in generated field
    all_players = field_df[PLAYER_COLS].values.flatten()
    field_own = (
        pd.Series(all_players)
        .value_counts()
        .div(len(field_df))
        .mul(100)
        .rename("field_own_pct")
    )

    # Join with projected rostership
    compare_df = player_df[['Name + ID', 'rostership', 'Roster Position', 'Salary', 'TeamAbbrev']].copy()
    compare_df = compare_df.set_index('Name + ID').join(field_own).fillna(0)
    compare_df['error'] = compare_df['field_own_pct'] - compare_df['rostership']
    compare_df['abs_error'] = compare_df['error'].abs()
    compare_df = compare_df.sort_values('rostership', ascending=False)

    print("=== PROJECTED vs ACTUAL FIELD OWNERSHIP (sorted by projected rostership) ===")
    print(f"{'Player':<35} {'Pos':<6} {'Salary':>7} {'Projected':>10} {'Actual':>8} {'Error':>8}")
    print("-" * 80)
    for name, row in compare_df.head(40).iterrows():
        print(f"{name:<35} {row['Roster Position']:<6} {row['Salary']:>7,.0f} "
              f"{row['rostership']:>9.1f}% {row['field_own_pct']:>7.1f}% {row['error']:>+7.1f}%")

    print(f"\n=== ACCURACY SUMMARY ===")
    print(f"  Mean absolute error (all players) : {compare_df['abs_error'].mean():.2f}%")
    print(f"  Mean absolute error (>5% proj own): {compare_df[compare_df['rostership'] > 5]['abs_error'].mean():.2f}%")
    print(f"  Correlation (projected vs actual) : {compare_df['rostership'].corr(compare_df['field_own_pct']):.4f}")

    pitchers = compare_df[compare_df['Roster Position'] == 'P']
    hitters  = compare_df[compare_df['Roster Position'] != 'P']

    print(f"\n  Pitchers MAE : {pitchers['abs_error'].mean():.2f}%")
    print(f"  Hitters  MAE : {hitters['abs_error'].mean():.2f}%")

    print(f"\n=== BIGGEST MISMATCHES ===")
    print("  Most overrepresented in field (actual >> projected):")
    print(compare_df.nlargest(5, 'error')[['Roster Position', 'TeamAbbrev', 'rostership', 'field_own_pct', 'error']].to_string())
    print("\n  Most underrepresented in field (actual << projected):")
    print(compare_df.nsmallest(5, 'error')[['Roster Position', 'TeamAbbrev', 'rostership', 'field_own_pct', 'error']].to_string())

    # Team-level analysis
    print("\n=== TEAM-LEVEL OWNERSHIP ANALYSIS (hitters only) ===")

    hitters_df = compare_df[compare_df['Roster Position'] != 'P'].copy()

    team_df = hitters_df.groupby('TeamAbbrev').agg(
        projected_sum  = ('rostership',    'sum'),
        actual_sum     = ('field_own_pct', 'sum'),
        projected_max  = ('rostership',    'max'),
        actual_max     = ('field_own_pct', 'max'),
        n_players      = ('rostership',    'count'),
    ).reset_index()

    team_df['sum_error'] = team_df['actual_sum'] - team_df['projected_sum']
    team_df['max_error'] = team_df['actual_max'] - team_df['projected_max']
    team_df['team_weight_sum'] = team_df['projected_sum'] / team_df['projected_sum'].sum()

    team_df = team_df.sort_values('projected_sum', ascending=False)

    print(f"\n{'Team':<6} {'Proj Sum':>9} {'Act Sum':>8} {'Sum Err':>8} {'Proj Max':>9} {'Act Max':>8} {'Max Err':>8} {'Team Wt%':>9}")
    print("-" * 78)
    for _, row in team_df.iterrows():
        print(f"{row['TeamAbbrev']:<6} {row['projected_sum']:>8.1f}% {row['actual_sum']:>7.1f}% "
              f"{row['sum_error']:>+7.1f}% {row['projected_max']:>8.1f}% {row['actual_max']:>7.1f}% "
              f"{row['max_error']:>+7.1f}% {row['team_weight_sum']*100:>8.1f}%")

    # Scatter plot
    ax = compare_df.plot.scatter(
        x='rostership',
        y='field_own_pct',
        figsize=(6, 6)
    )

    min_val = min(compare_df['rostership'].min(), compare_df['field_own_pct'].min())
    max_val = max(compare_df['rostership'].max(), compare_df['field_own_pct'].max())

    ax.set_xlim(min_val, max_val)
    ax.set_ylim(min_val, max_val)
    ax.set_aspect('equal', adjustable='box')
    ax.plot([min_val, max_val], [min_val, max_val])

    return compare_df, team_df


# 4. Porfolio lineups
def choose_portfolio(contestKey, portfolio_size=20, n_iterations=500, swap_size=2,
                     random_seed=42, optimize_metric="Top_1pct_rate", write_file=True):

    # --- Helper functions ---

    def build_payout_array(payout_df, contest_size):
        # Fallback if contest_size is missing or zero
        if not contest_size or pd.isna(contest_size) or int(contest_size) <= 0:
            contest_size = int(payout_df['maxPosition'].max())
        contest_size = int(contest_size)

        payout_array = np.zeros(contest_size, dtype=float)
        payouts = (
            payout_df['payoutDescription']
            .astype(str)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        payouts = pd.to_numeric(payouts, errors='coerce').fillna(0.0)

        for start, end, payout in zip(payout_df['minPosition'], payout_df['maxPosition'], payouts):
            start_idx = max(0, int(start) - 1)
            end_idx   = min(contest_size, int(end))
            if start_idx >= contest_size:
                continue
            payout_array[start_idx:end_idx] = payout

        return payout_array

    def build_score_matrix(lineup_df, player_df_indexed, player_cols):
        sim_cols = [c for c in player_df_indexed.columns if c.startswith('FP_') or c.startswith('sim_')]
        score_matrix = []
        for _, lineup in lineup_df.iterrows():
            player_ids = [lineup[col] for col in player_cols]
            sims = player_df_indexed.loc[player_ids, sim_cols].sum(axis=0).values
            score_matrix.append(sims)
        return np.array(score_matrix)  # (n_lineups, n_sims)

    def build_thresholds(field_scores, payout_array, contest_size):
        # Use payout_array length as ground truth for contest_size
        contest_size = len(payout_array)
        if contest_size <= 0:
            raise ValueError(f"contest_size must be > 0, got {contest_size}")

        thresholds = {
            'top1': np.percentile(field_scores, 99, axis=0),
            'top5': np.percentile(field_scores, 95, axis=0),
        }

        unique_payouts = np.unique(payout_array)
        unique_payouts = unique_payouts[unique_payouts > 0][::-1]

        for payout in unique_payouts:
            idx = np.where(payout_array == payout)[0]
            if len(idx) == 0:
                continue
            worst_rank = idx[-1] + 1  # 1-based
            pct = np.clip(100.0 * (contest_size - worst_rank) / contest_size, 0.0, 100.0)
            thresholds[payout] = np.percentile(field_scores, pct, axis=0)

        return thresholds

    def evaluate_portfolio(selected_idx, my_scores, thresholds, payout_array, entry_fee):
        my_s   = my_scores[selected_idx, :]
        n_my, n_sims = my_s.shape

        hits_1pct = my_s > thresholds['top1']
        hits_5pct = my_s > thresholds['top5']

        per_lineup_top1_rate = hits_1pct.mean(axis=1)
        per_lineup_top5_rate = hits_5pct.mean(axis=1)

        unique_payouts = np.array(sorted(set(payout_array[payout_array > 0]), reverse=True))

        if len(unique_payouts) == 0:
            per_lineup_payouts = np.zeros((n_my, n_sims))
        else:
            thresh_matrix = np.stack([thresholds[p] for p in unique_payouts])
            beats = my_s[:, None, :] > thresh_matrix[None, :, :]
            payout_values = unique_payouts[:, None]
            per_lineup_payouts = (beats * payout_values[None, :, :]).max(axis=1)

        per_lineup_ev = per_lineup_payouts.mean(axis=1)

        portfolio_ev  = per_lineup_ev.sum() - entry_fee * n_my
        portfolio_roi = portfolio_ev / (entry_fee * n_my) if entry_fee > 0 else 0
        portfolio_std = per_lineup_payouts.sum(axis=0).std()

        portfolio_metrics = {
            "EV":            portfolio_ev,
            "ROI":           portfolio_roi,
            "StdDev":        portfolio_std,
            "Top_1pct_avg":  per_lineup_top1_rate.mean(),
            "Top_5pct_avg":  per_lineup_top5_rate.mean(),
            "Top_1pct_any":  hits_1pct.any(axis=0).mean(),
            "Top_5pct_any":  hits_5pct.any(axis=0).mean(),
            "Top_1pct_rate": per_lineup_top1_rate.mean(),
            "Top_5pct_rate": per_lineup_top5_rate.mean(),
        }

        return portfolio_metrics, per_lineup_ev, per_lineup_top1_rate, per_lineup_top5_rate

    def monte_carlo_search(lineup_df, my_scores, thresholds, payout_array, entry_fee,
                           portfolio_size, n_iterations, swap_size, random_seed, optimize_metric):
        np.random.seed(random_seed)
        n_candidates = len(lineup_df)

        best_portfolio = np.argsort(-lineup_df['FPPG'].values)[:portfolio_size].copy()
        metrics, _, _, _ = evaluate_portfolio(
            best_portfolio, my_scores, thresholds, payout_array, entry_fee
        )
        best_value = metrics[optimize_metric]
        print(f"Initial {optimize_metric}: {best_value:.4f}")

        for it in range(n_iterations):
            swap_out  = np.random.choice(best_portfolio, size=min(swap_size, portfolio_size), replace=False)
            remaining = np.setdiff1d(np.arange(n_candidates), best_portfolio)
            if len(remaining) == 0:
                continue
            swap_in = np.random.choice(remaining, size=len(swap_out), replace=False)

            new_portfolio = best_portfolio.copy()
            for o, i in zip(swap_out, swap_in):
                new_portfolio[np.where(new_portfolio == o)[0][0]] = i

            metrics, _, _, _ = evaluate_portfolio(
                new_portfolio, my_scores, thresholds, payout_array, entry_fee
            )
            if metrics[optimize_metric] > best_value:
                best_portfolio = new_portfolio
                best_value     = metrics[optimize_metric]
                print(f"Iteration {it+1}: New best {optimize_metric} = {best_value:.4f}")

        portfolio_metrics, per_lineup_ev, per_lineup_top1_rate, per_lineup_top5_rate = evaluate_portfolio(
            best_portfolio, my_scores, thresholds, payout_array, entry_fee
        )

        selected_df = lineup_df.iloc[best_portfolio].copy()
        selected_df["EV_Payout"]     = per_lineup_ev
        selected_df["Top_1pct_rate"] = per_lineup_top1_rate
        selected_df["Top_5pct_rate"] = per_lineup_top5_rate

        return best_portfolio, portfolio_metrics, selected_df

    # --- Read data ---
    try:
        player_df       = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "1. Players",      f"Players {contestKey}.csv"))
        lineup_df       = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "2. Lineups",       f"Lineups {contestKey}.csv"))
        field_lineup_df = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "3. Field Lineups", f"Field Lineups {contestKey}.csv"))
        payout_df       = pd.read_csv(os.path.join(baseball_path, "A09. DraftKings", "3. Payouts",         f"Payouts {contestKey}.csv"))
        contest_df      = pd.read_csv(os.path.join(baseball_path, "B03. Contest Guides",                   f"Contest Guide {contestKey}.csv"))
    except Exception as e:
        print(f"Error reading files for contest {contestKey}: {e}")
        return None, None, None

    player_df['Name + ID'] = player_df['Name + ID'].str.replace(" (", "(", regex=False)
    player_df_indexed = player_df.set_index('Name + ID')
    player_cols = ['P', 'P.1', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF.1', 'OF.2']

    contest_size = contest_df['entries'].iloc[0]
    entry_fee    = contest_df['entryFee'].iloc[0]

    payout_array = build_payout_array(payout_df, contest_size)
    # Use actual payout_array length as contest_size — handles zero/NaN entries
    contest_size = len(payout_array)

    print(f"[{contestKey}] contest_size={contest_size:,}  entry_fee=${entry_fee}")

    print("Building score matrices...")
    my_scores    = build_score_matrix(lineup_df,       player_df_indexed, player_cols)
    field_scores = build_score_matrix(field_lineup_df, player_df_indexed, player_cols)

    print("Computing field thresholds...")
    thresholds = build_thresholds(field_scores, payout_array, contest_size)

    print("Running portfolio search...")
    best_idx, portfolio_metrics, selected_df = monte_carlo_search(
        lineup_df, my_scores, thresholds, payout_array, entry_fee,
        portfolio_size, n_iterations, swap_size, random_seed, optimize_metric
    )

    print(f"Finished. Best {optimize_metric}: {portfolio_metrics[optimize_metric]:.4f}")

    # --- Payout tier diagnostics ---
    print(f"\n=== PAYOUT TIER DIAGNOSTICS ===")
    print(f"{'Payout':>8}  {'Positions':>12}  {'Top %':>8}  {'Threshold':>10}  {'Hit Rate':>9}")
    print("-" * 65)

    for p in sorted(set(payout_array[payout_array > 0])):
        positions = np.where(payout_array == p)[0] + 1
        min_pos   = positions[0]
        max_pos   = positions[-1]
        top_pct   = max_pos / contest_size * 100
        thresh    = thresholds[p].mean()
        hit_rate  = (my_scores > thresholds[p][None, :]).mean()
        print(f"${p:>7,.0f}  {min_pos:>5}-{max_pos:<5}  {top_pct:>7.2f}%  {thresh:>10.1f}  {hit_rate:>8.2%}")

    print(f"\nMy lineup avg score:    {my_scores.mean():.1f}")
    print(f"Field lineup avg score: {field_scores.mean():.1f}")

    if write_file:
        selected_df.to_csv(
            os.path.join(baseball_path, "C02. Optimization", "4. Portfolio Lineups",
                         f"Portfolio Lineups {contestKey}.csv"),
            index=False
        )

    return best_idx, portfolio_metrics, selected_df


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


# 7. Entries
# Create entry file for DraftKings
def create_entry_file(draftGroupId, contestKey):   
    # Read in entry file from downloads
    entry_df = pd.read_csv(os.path.join(download_path, max([f for f in os.listdir(download_path) if f.startswith("DKEntries")], key=lambda x: os.path.getctime(os.path.join(download_path, x)))), usecols=['Entry ID','Contest Name','Contest ID','Entry Fee'])
    entry_df.dropna(inplace=True)

    # Read in Upload file
    lineup_sims = pd.read_csv(os.path.join(baseball_path, "C02. Optimization", "6. Uploads", f"Upload {contestKey}.csv"), encoding='iso-8859-1')

    # Keep just the players
    lineup_sims = lineup_sims[['P', 'P.1', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF.1', 'OF.2']]
    # Rename variables to appease DK's upload
    lineup_sims.rename(columns={'P.1':'P', 'OF.1':'OF', 'OF.2':'OF'}, inplace=True)
    lineup_sims.reset_index(inplace=True, drop=True)
    
    # Merge entry sheet with lineups
    entry_df = entry_df.merge(lineup_sims, how='inner', left_index=True, right_index=True)
    
    # Convert to numeric
    entry_df['Entry ID'] = entry_df['Entry ID'].astype('int64')


    return entry_df


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


# Upload entry file by launching DraftKings, clicking the Upload button, and selecting the file
def upload_entries(draftGroupId):
    # Open entry page
    webbrowser.open(f"https://www.draftkings.com/entry/upload")
    time.sleep(7)

    # Function to search across all monitors
    def locate_on_any_monitor(image_path, confidence=0.8):
        with mss.mss() as sct:
            for monitor in sct.monitors:  # loop through all monitors
                screenshot = np.array(sct.grab(monitor))

                location = pyautogui.locate(
                    image_path,
                    screenshot,
                    confidence=confidence
                )

                if location:
                    return (
                        location.left + monitor["left"],
                        location.top + monitor["top"],
                        location.width,
                        location.height
                    )
        return None

    # Try multiple times to find the button
    upload_csv_button = None
    for _ in range(5):
        upload_csv_button = locate_on_any_monitor(
            os.path.join(baseball_path, "UPLOAD CSV.png"),
            confidence=0.8
        )
        if upload_csv_button:
            break
        time.sleep(2)

    # Click if found
    if upload_csv_button is not None:
        pyautogui.click(upload_csv_button)
    else:
        print("Button not found.")
        return

    # Access directory bar
    pyautogui.hotkey('alt', 'd')
    time.sleep(3)

    # Copy and paste the file path
    filepath = rf"C:\Users\James\Documents\MLB\Data\C02. Optimization\7. Entries\Entries {draftGroupId}.csv"
    pyperclip.copy(filepath)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(3)
    pyautogui.press("enter")


# Create clickable button to open Excel file
def excel_button(file_path):
    file_path = os.path.abspath(file_path)

    def open_excel(b):
        subprocess.Popen(['start', 'excel', file_path], shell=True)

    button = widgets.Button(description=f"Open {os.path.basename(file_path)} in Excel 📊")
    button.on_click(open_excel)
    display(button)


__all__ = [name for name in globals() if not name.startswith("_")]