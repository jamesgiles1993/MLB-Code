from U01Imports import *
from U02Functions import *
from U04Datasets import *
from U05Models import *

# %%
# Creates matchup files for all games in game_df
def create_all_matchups(game_df, baseball_path, team_dict, year, todaysdate_dash,
                        batter_inputs, pitcher_inputs, n_jobs=-2):

    # ---------------------------
    # 1️⃣ Read big datasets once
    # ---------------------------
    complete_dataset = pd.read_csv(os.path.join(baseball_path, "PA Dataset.csv"))
    complete_dataset = complete_dataset.replace([float('inf'), float('-inf')], 0)

    steamer_hitters_df = pd.read_csv(os.path.join(baseball_path, "A03. Steamer", "steamer_hitters_weekly_log.csv"), encoding='iso-8859-1')
    steamer_hitters_df_current = pd.read_csv(os.path.join(baseball_path, "A03. Steamer", "steamer_hitters.csv"), encoding='iso-8859-1')
    steamer_hitters_df_current['proj_year'] = steamer_hitters_df_current['proj_season']
    steamer_hitters_df = pd.concat([steamer_hitters_df, steamer_hitters_df_current], axis=0)

    steamer_pitchers_df = pd.read_csv(os.path.join(baseball_path, "A03. Steamer", "steamer_pitchers_weekly_log.csv"), encoding='iso-8859-1')
    steamer_pitchers_df_current = pd.read_csv(os.path.join(baseball_path, "A03. Steamer", "steamer_pitchers.csv"), encoding='iso-8859-1')
    steamer_pitchers_df_current['proj_year'] = steamer_pitchers_df_current['proj_season']
    steamer_pitchers_df = pd.concat([steamer_pitchers_df, steamer_pitchers_df_current], axis=0)

    steamer_hitters_df['proj_year'].fillna(year, inplace=True)
    steamer_hitters_df['proj_date'].fillna(todaysdate_dash, inplace=True)
    steamer_hitters_df = clean_steamer_hitters(steamer_hitters_df)

    steamer_pitchers_df['proj_year'].fillna(year, inplace=True)
    steamer_pitchers_df['proj_date'].fillna(todaysdate_dash, inplace=True)
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

    steamer_hitters_df['date_time'] = pd.to_datetime(steamer_hitters_df['date'], format='%Y%m%d')
    steamer_hitters_df.sort_values('date_time', inplace=True)
    steamer_hitters_df['id'] = steamer_hitters_df['mlbamid'].astype(int).astype(str)

    steamer_pitchers_df['date_time'] = pd.to_datetime(steamer_pitchers_df['date'], format='%Y%m%d')
    steamer_pitchers_df.sort_values('date_time', inplace=True)
    steamer_pitchers_df['id'] = steamer_pitchers_df['mlbamid'].astype(int).astype(str)

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

        away_batter_df.to_excel(matchup_path, sheet_name="AwayBatters", index=False)
        with pd.ExcelWriter(matchup_path, mode="a", engine="openpyxl") as writer:
            home_batter_df.to_excel(writer, sheet_name="HomeBatters", index=False)
            away_pitcher_df.to_excel(writer, sheet_name="AwayPitchers", index=False)
            home_pitcher_df.to_excel(writer, sheet_name="HomePitchers", index=False)

        return matchup_path

    # ---------------------------
    # 4️⃣ Parallel execution
    # ---------------------------
    _ = Parallel(n_jobs=n_jobs, verbose=True)(delayed(process_single_game)(row)for row in range(len(game_df)))


# %%
__all__ = [name for name in globals() if not name.startswith("_")]



