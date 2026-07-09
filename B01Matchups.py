from U01Imports import *
from U02Functions import *
from U04Datasets import *
# from U05Models import *

# Creates matchup files for all games in game_df
def create_all_matchups(game_df, baseball_path, team_dict,
                        batter_inputs, pitcher_inputs, start_date, n_jobs=-2):

    start_dt = pd.to_datetime(start_date, format='%Y%m%d')

    # Keep records >= start_dt, plus each id's most recent pre-cutoff record as a
    # fallback so merge_asof never loses a player whose latest data predates the cutoff.
    # Result is identical to no filtering, but drops the bulk of old history.
    def filter_recent(df, start_dt):
        recent = df[df['date_time'] >= start_dt]
        last_before = df[df['date_time'] < start_dt].drop_duplicates('id', keep='last')
        return pd.concat([recent, last_before]).sort_values('date_time')

    # ---------------------------
    # 1️⃣ Read big datasets once
    # ---------------------------
    complete_dataset = pd.read_csv(os.path.join(baseball_path, "PA Dataset.csv"))
    complete_dataset = complete_dataset.replace([float('inf'), float('-inf')], 0)

    steamer_hitters_df = pd.read_csv(os.path.join(baseball_path, "A03. Steamer", "Hitters", "Steamer Hitters Dataset.csv"), encoding='iso-8859-1')
    steamer_pitchers_df = pd.read_csv(os.path.join(baseball_path, "A03. Steamer", "Pitchers", "Steamer Pitchers Dataset.csv"), encoding='iso-8859-1')

    steamer_hitters_df = clean_steamer_hitters(steamer_hitters_df)

    steamer_pitchers_df = clean_steamer_pitchers(steamer_pitchers_df)
    steamer_pitchers_df.dropna(subset=['mlbamid'], inplace=True)

    # ---------------------------
    # 2️⃣ Prepare vs_ datasets
    # ---------------------------

    # Batter splits (keyed on batter)
    vs_lhp_bat = complete_dataset[complete_dataset['pitchHand'] == "L"].copy()
    vs_rhp_bat = complete_dataset[complete_dataset['pitchHand'] == "R"].copy()
    vs_lhp_bat['id'] = vs_lhp_bat['batter'].astype(str)
    vs_rhp_bat['id'] = vs_rhp_bat['batter'].astype(str)

    # Pitcher splits (keyed on pitcher)
    vs_lhb_pit = complete_dataset[complete_dataset['batSide'] == "L"].copy()
    vs_rhb_pit = complete_dataset[complete_dataset['batSide'] == "R"].copy()
    vs_lhb_pit['id'] = vs_lhb_pit['pitcher'].astype(str)
    vs_rhb_pit['id'] = vs_rhb_pit['pitcher'].astype(str)

    for df_tmp in [vs_lhp_bat, vs_rhp_bat, vs_lhb_pit, vs_rhb_pit]:
        df_tmp.drop_duplicates(subset=['id', 'date'], keep='last', inplace=True)
        df_tmp['date_time'] = pd.to_datetime(df_tmp['date'], format='%Y%m%d')
        df_tmp.sort_values('date_time', inplace=True)

    # Filter (done after the loop because rebinding df_tmp inside the loop
    # wouldn't affect the original frames)
    vs_lhp_bat = filter_recent(vs_lhp_bat, start_dt)
    vs_rhp_bat = filter_recent(vs_rhp_bat, start_dt)
    vs_lhb_pit = filter_recent(vs_lhb_pit, start_dt)
    vs_rhb_pit = filter_recent(vs_rhb_pit, start_dt)

    steamer_hitters_df['date_time'] = pd.to_datetime(steamer_hitters_df['date'], format='%Y%m%d')
    steamer_hitters_df['id'] = steamer_hitters_df['mlbamid'].astype(int).astype(str)
    steamer_hitters_df.sort_values('date_time', inplace=True)
    steamer_hitters_df = filter_recent(steamer_hitters_df, start_dt)

    steamer_pitchers_df['date_time'] = pd.to_datetime(steamer_pitchers_df['date'], format='%Y%m%d')
    steamer_pitchers_df['id'] = steamer_pitchers_df['mlbamid'].astype(int).astype(str)
    steamer_pitchers_df.sort_values('date_time', inplace=True)
    steamer_pitchers_df = filter_recent(steamer_pitchers_df, start_dt)

    # ---------------------------
    # 3️⃣ Inner function: single game
    # ---------------------------
    def process_single_game(row):
        game_id = game_df.loc[row, 'game_id']
        away_id = game_df.loc[row, 'away_id']
        home_id = game_df.loc[row, 'home_id']
        game_date = game_df.loc[row, 'game_date'].replace("-", "")
        utc_datetime = game_df.loc[row, 'game_datetime']
        est_datetime = utc_datetime.tz_convert("US/Eastern")
        formatted_time = est_datetime.strftime("%H%M")

        away_starter = game_df.loc[row, 'away_probable_pitcher']
        home_starter = game_df.loc[row, 'home_probable_pitcher']

        away_team = team_dict[away_id]
        home_team = team_dict[home_id]

        def build_team_df(team_id):

            team = team_dict[team_id]

            roster_df = pd.read_csv(os.path.join(baseball_path, "A05. Rosters", "2. Rosters", f"Rosters {game_date}", f"Roster {team} {game_date}.csv"), encoding='iso-8859-1', dtype=str)
            order_df = pd.read_csv(os.path.join(baseball_path, "A05. Rosters", "1. Batting Orders", f"Batting Orders {game_date}", f"Batting Order {team} {game_id}.csv"), encoding='iso-8859-1', dtype=str)
            bullpen_df = pd.read_csv(os.path.join(baseball_path, "A04. Bullpens", f"Bullpens {game_date}", f"Bullpen {team} {game_date}.csv"), encoding='iso-8859-1', dtype=str)

            bullpen_df['id'] = bullpen_df['id'].apply(lambda x: x.replace('.0', '') if isinstance(x, str) else x)
            bullpen_df = bullpen_df[bullpen_df['id'].notna() & (bullpen_df['id'] != "")]

            # Only keep one observation per player (weirdly necessary - team depth charts are weird)
            bullpen_df = bullpen_df.drop_duplicates('id', keep='first')

            team_df = pd.merge(roster_df, order_df[['id', 'fullName', 'position', 'status', 'order']], on='id', how='outer', suffixes=("", "2"))

            team_df['batSide'].fillna('Right', inplace=True)
            team_df['pitchHand'].fillna('Right', inplace=True)
            team_df['fullName'].fillna(team_df['fullName2'], inplace=True)
            team_df['position'].fillna(team_df['position2'], inplace=True)
            team_df['fullName'] = team_df['fullName'].apply(remove_accents)

            team_df.drop(columns=['fullName2', 'position2'], inplace=True)

            team_df['away_starter'] = away_starter
            team_df['home_starter'] = home_starter

            team_df['away_starter'] = team_df['away_starter'].apply(remove_accents)
            team_df['home_starter'] = team_df['home_starter'].apply(remove_accents)

            # Merge in RP Leverage
            team_df = pd.merge(team_df, bullpen_df[['id', 'Leverage']], on='id', how='left')


            # Assign Leverage of 1 to starting pitcher
            team_df['Leverage'] = pd.to_numeric(team_df['Leverage'], errors='coerce')
            team_df['Leverage'] = np.where((team_df['fullName'] == team_df['away_starter']) | (team_df['fullName'] == team_df['home_starter']), 1, team_df['Leverage'])

            team_df['venue_id'] = game_df.loc[row, 'venue_id']

            team_df['order'] = pd.to_numeric(team_df['order'], errors='coerce')
            team_df['batting_order'] = np.nan
            for i in range(9):
                team_df['batting_order'] = np.where(
                    team_df['order'] == (i + 1) * 100,
                    i + 1,
                    team_df['batting_order']
                )

            batter_df = team_df[team_df['position'] != "Pitcher"].copy()
            pitcher_df = team_df[
                (team_df['position'] == "Pitcher") |
                (team_df['position'] == "Two-Way Player")
            ].copy()

            batter_df['date_time'] = pd.to_datetime(batter_df['date'], format='%Y%m%d')
            batter_df['date_time'].fillna(batter_df['date_time'].min(), inplace=True)
            batter_df = batter_df.sort_values('date_time').reset_index(drop=True)

            batter_df = pd.merge_asof(
                batter_df,
                vs_lhp_bat[['id','date_time'] + batter_inputs + ['imp_b','pa_b']],
                on='date_time', by='id', direction='backward'
            )

            batter_df = pd.merge_asof(
                batter_df,
                vs_rhp_bat[['id','date_time'] + batter_inputs + ['imp_b','pa_b']],
                on='date_time', by='id', direction='backward',
                suffixes=('_l','_r')
            )

            batter_df = pd.merge_asof(
                batter_df,
                steamer_hitters_df.drop(columns=['date']),
                on='date_time', by='id', direction='backward'
            )

            pitcher_df['date_time'] = pd.to_datetime(pitcher_df['date'], format='%Y%m%d')
            pitcher_df['date_time'].fillna(pitcher_df['date_time'].min(), inplace=True)
            pitcher_df = pitcher_df.sort_values('date_time').reset_index(drop=True)

            pitcher_df = pd.merge_asof(
                pitcher_df,
                vs_lhb_pit[['id','date_time'] + pitcher_inputs + ['imp_p','pa_p']],
                on='date_time', by='id', direction='backward'
            )

            pitcher_df = pd.merge_asof(
                pitcher_df,
                vs_rhb_pit[['id','date_time'] + pitcher_inputs + ['imp_p','pa_p']],
                on='date_time', by='id', direction='backward',
                suffixes=('_l','_r')
            )

            pitcher_df = pd.merge_asof(
                pitcher_df,
                steamer_pitchers_df.drop(columns=['date']),
                on='date_time', by='id', direction='backward'
            )

            return batter_df.sort_values('batting_order').reset_index(drop=True), pitcher_df.sort_values('Leverage').reset_index(drop=True)

        away_batter_df, away_pitcher_df = build_team_df(away_id)
        home_batter_df, home_pitcher_df = build_team_df(home_id)

        matchup_dir = os.path.join(baseball_path, "B01. Matchups", f"Matchups {game_date}")
        os.makedirs(matchup_dir, exist_ok=True)

        matchup_path = os.path.join(matchup_dir, f"{away_team}@{home_team} {game_id} {formatted_time}.xlsx")

        with pd.ExcelWriter(matchup_path, engine="xlsxwriter") as writer:
            away_batter_df.to_excel(writer, sheet_name="AwayBatters", index=False)
            home_batter_df.to_excel(writer, sheet_name="HomeBatters", index=False)
            away_pitcher_df.to_excel(writer, sheet_name="AwayPitchers", index=False)
            home_pitcher_df.to_excel(writer, sheet_name="HomePitchers", index=False)

        return matchup_path

    # ---------------------------
    # 4️⃣ Parallel execution
    # ---------------------------
    Parallel(n_jobs=n_jobs, verbose=True)(delayed(process_single_game)(row) for row in range(len(game_df)))
    

__all__ = [name for name in globals() if not name.startswith("_")]



