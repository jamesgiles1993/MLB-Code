from U01Imports import *
from U05Models import *


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WOBA_WEIGHTS = {'b1': 0.882, 'b2': 1.254, 'b3': 1.590, 'hr': 2.050, 'bb': 0.689, 'hbp': 0.720}

WEATHER_CODE_MAP = {
    0: 'Clear.', 1: 'Sunny.', 2: 'Partly Cloudy.', 3: 'Overcast.',
    45: 'Cloudy.', 48: 'Cloudy.',
    51: 'Drizzle.', 53: 'Drizzle.', 55: 'Drizzle.', 56: 'Drizzle.', 57: 'Drizzle.',
    61: 'Rain.', 63: 'Rain.', 65: 'Rain.', 80: 'Rain.', 81: 'Rain.', 82: 'Rain.',
    71: 'Snow.', 73: 'Snow.', 75: 'Snow.', 77: 'Snow.', 85: 'Snow.', 86: 'Snow.',
    95: 'Rain.', 96: 'Rain.', 99: 'Rain.',
}
BAD_WEATHER_LIST = ['Rain.', 'Drizzle.', 'Snow.']
VENUE_TEMP_RANGE = {
    14: {'min_temp': 60, 'max_temp': 90},
    15: {'min_temp': 60, 'max_temp': 90},
    32: {'min_temp': 65, 'max_temp': 95},
    2392: {'min_temp': 55, 'max_temp': 65},
    5325: {'min_temp': 65, 'max_temp': 70},
}

DIST_ANGLE_MAP = {
    'LF_Dim': -45, 'SLF_Dim': -36, 'LFA_Dim': -27, 'LC_Dim': -18, 'LCC_Dim': -9, 'CF_Dim': 0,
    'RCC_Dim': 9, 'RC_Dim': 18, 'RFA_Dim': 27, 'SRF_Dim': 36, 'RF_Dim': 45,
}
HEIGHT_ANGLE_MAP = {
    'LF_W': -45, 'LC_W': -18, 'CF_W': 0, 'RC_W': 18, 'RF_W': 45,
}

# Manual park-dimension overrides for park-years where ParkConfig.csv is known
# wrong or missing. Rows marked LOW CONFIDENCE are placeholders to verify
# against an official source before fully trusting.
DIMENSION_OVERRIDES = [
    # --- Camden Yards "Walltimore" era (2022-2024) ---
    # ParkConfig.csv incorrectly carries pre-2022 numbers through these years.
    {'parkID': 'BAL12', 'Year': 2022, 'LF_Dim': 333, 'LC_Dim': 384, 'LCC_Dim': 398, 'CF_Dim': 400,
     'RC_Dim': 373, 'RF_Dim': 318, 'LF_W': 13, 'LC_W': 13, 'CF_W': 7, 'RC_W': 7, 'RF_W': 21},
    {'parkID': 'BAL12', 'Year': 2023, 'LF_Dim': 333, 'LC_Dim': 384, 'LCC_Dim': 398, 'CF_Dim': 400,
     'RC_Dim': 373, 'RF_Dim': 318, 'LF_W': 13, 'LC_W': 13, 'CF_W': 7, 'RC_W': 7, 'RF_W': 21},
    {'parkID': 'BAL12', 'Year': 2024, 'LF_Dim': 333, 'LC_Dim': 384, 'LCC_Dim': 398, 'CF_Dim': 400,
     'RC_Dim': 373, 'RF_Dim': 318, 'LF_W': 13, 'LC_W': 13, 'CF_W': 7, 'RC_W': 7, 'RF_W': 21},

    # --- Camden Yards, second change (2025-present) ---
    {'parkID': 'BAL12', 'Year': 2025, 'LF_Dim': 333, 'LC_Dim': 374, 'LCC_Dim': 410, 'CF_Dim': 400,
     'RC_Dim': 373, 'RF_Dim': 318, 'LF_W': 8, 'LC_W': 7, 'CF_W': 7, 'RC_W': 7, 'RF_W': 21},
    {'parkID': 'BAL12', 'Year': 2026, 'LF_Dim': 333, 'LC_Dim': 374, 'LCC_Dim': 410, 'CF_Dim': 400,
     'RC_Dim': 373, 'RF_Dim': 318, 'LF_W': 8, 'LC_W': 7, 'CF_W': 7, 'RC_W': 7, 'RF_W': 21},

    # --- Kauffman Stadium, 2026 change ---
    # HIGH CONFIDENCE: cross-checked across MLB.com, ESPN, Royals Review, WKZO, KWCH, AOL.
    # Corners in 9ft, straightaway in 9ft, gaps in ~8-10ft (sources vary slightly on gap amount),
    # center unchanged at 410. Height 10ft -> 8.5ft (see note below on the historical height gap).
    {'parkID': 'KAN06', 'Year': 2026, 'LF_Dim': 347, 'SLF_Dim': 364, 'LC_Dim': 379, 'CF_Dim': 410,
     'RC_Dim': 379, 'SRF_Dim': 364, 'RF_Dim': 344,
     'LF_W': 8.5, 'LC_W': 8.5, 'CF_W': 8.5, 'RC_W': 8.5, 'RF_W': 8.5},

    # NOTE: multiple independent sources describe Kauffman's PRE-2026 height as 10ft, but
    # ParkConfig.csv has it at 8.0 for every year 2001-2025. That's a likely-wrong historical
    # baseline this override does not yet fix -- would affect every pre-2026 Kauffman row's
    # wall_height feature, not just 2026, if patched.

    # --- Sutter Health Park (Athletics' temporary home, 2025-2027) --- (LOW CONFIDENCE on height)
    {'parkID': 'SAC01', 'Year': 2025, 'LF_Dim': 330, 'CF_Dim': 403, 'RF_Dim': 325,
     'LF_W': 9, 'CF_W': 9, 'RF_W': 9},
    {'parkID': 'SAC01', 'Year': 2026, 'LF_Dim': 330, 'CF_Dim': 403, 'RF_Dim': 325,
     'LF_W': 9, 'CF_W': 9, 'RF_W': 9},
]


def _angle_points(row, angle_map):
    points = [(angle, row[col]) for col, angle in angle_map.items()
              if col in row.index and pd.notna(row[col])]
    points.sort(key=lambda p: p[0])
    return points


def _venue_min_max(row):
    return VENUE_TEMP_RANGE.get(row['venue_id'], {'min_temp': float('inf'), 'max_temp': float('-inf')})


# ---------------------------------------------------------------------------
# Auxiliary state: neutral sample + baselines + park dimensions.
# Independent of which model version is loaded, so this is a single cached
# instance (not keyed by model_date the way model loading used to be).
# ---------------------------------------------------------------------------

class _AuxState:
    def __init__(self):
        # --- Neutral sample + baselines ---
        self.sim_sample = pd.read_csv(os.path.join(baseball_path, "Weather Sample.csv"))
        self.sim_sample['date'] = pd.to_datetime(self.sim_sample['date'])
        self.sim_sample_L = self.sim_sample[self.sim_sample['batSide'] == 'L'].reset_index(drop=True)
        self.sim_sample_R = self.sim_sample[self.sim_sample['batSide'] == 'R'].reset_index(drop=True)
        self.n_sample_L = len(self.sim_sample_L)
        self.n_sample_R = len(self.sim_sample_R)
        print(f"Sample: {len(self.sim_sample):,} ({self.n_sample_L:,} L, {self.n_sample_R:,} R)")

        self.baseline_rates_L = self._compute_actual_rates(self.sim_sample_L)
        self.baseline_rates_R = self._compute_actual_rates(self.sim_sample_R)
        self.baseline_counts_L = self.sim_sample_L['eventsModel'].value_counts().reindex(events_classes).fillna(0)
        self.baseline_counts_R = self.sim_sample_R['eventsModel'].value_counts().reindex(events_classes).fillna(0)

        # League-wide carry signal is already attached to each historical row in the sample --
        # just take the most recent known value rather than re-deriving from full weather_dataset
        self.latest_carry = self.sim_sample.sort_values('date')['rolling_carry_365d'].dropna().iloc[-1]
        print(f"Latest rolling_carry_365d: {self.latest_carry:.2f}")

        # --- Park dimensions ---
        park_config = pd.read_csv(os.path.join(baseball_path, "Utilities", "ParkConfig.csv"))
        self.park_venue_crosswalk = pd.read_csv(os.path.join(baseball_path, "Utilities", "Venue Crosswalk.csv"))
        print(f"ParkConfig: {len(park_config):,} park-year rows, {park_config['parkID'].nunique()} parks")
        print(f"Crosswalk: {len(self.park_venue_crosswalk)} parks mapped to venue_id")

        dimension_overrides_df = pd.DataFrame(DIMENSION_OVERRIDES)
        override_keys = set(zip(dimension_overrides_df['parkID'], dimension_overrides_df['Year']))
        mask_overridden = park_config.apply(lambda r: (r['parkID'], r['Year']) in override_keys, axis=1)

        self.park_config_patched = pd.concat(
            [park_config[~mask_overridden], dimension_overrides_df],
            ignore_index=True
        ).sort_values(['parkID', 'Year']).reset_index(drop=True)
        self.park_year_index = self.park_config_patched.set_index(['parkID', 'Year'])

    def _compute_actual_rates(self, sample_df):
        rates = sample_df['eventsModel'].value_counts(normalize=True).reindex(events_classes).fillna(0.0).to_dict()
        rates['wOBA'] = sample_df['eventsModel'].map(WOBA_WEIGHTS).fillna(0.0).mean()
        return rates

    def _lookup_park_year_row(self, parkID, year):
        available_years = self.park_config_patched.loc[self.park_config_patched['parkID'] == parkID, 'Year']
        if len(available_years) == 0:
            return None
        if year not in available_years.values:
            candidates = available_years[available_years <= year]
            year = candidates.max() if len(candidates) else available_years.max()
        row = self.park_year_index.loc[(parkID, year)]
        if isinstance(row, pd.DataFrame):  # duplicate (parkID, Year) rows -- take the first
            row = row.iloc[0]
        return row

    def get_wall_geometry_vectorized(self, parkID, year, spray_angles):
        """Looks up the park-year row once, then interpolates an entire array
        of spray angles at once -- avoids a per-ball Python loop when replaying
        the same game against thousands of sample balls."""
        row = self._lookup_park_year_row(parkID, year)
        if row is None:
            nan_arr = np.full(len(spray_angles), np.nan)
            return nan_arr, nan_arr
        dist_points = _angle_points(row, DIST_ANGLE_MAP)
        height_points = _angle_points(row, HEIGHT_ANGLE_MAP)
        distance = (np.interp(spray_angles, [p[0] for p in dist_points], [p[1] for p in dist_points])
                    if dist_points else np.full(len(spray_angles), np.nan))
        height = (np.interp(spray_angles, [p[0] for p in height_points], [p[1] for p in height_points])
                  if height_points else np.full(len(spray_angles), np.nan))
        return distance, height


_aux_state = None


def _get_aux_state():
    global _aux_state
    if _aux_state is None:
        _aux_state = _AuxState()
    return _aux_state


# ---------------------------------------------------------------------------
# Simulation (uses distance_best_model / scaler / events_best_model / events_scaler /
# venue_cat_dtype / events_venue_cat_dtype / events_classes / device from
# U05Models.py -- not defined in this module)
# ---------------------------------------------------------------------------

def simulate_game(aux, sample_df, game_row, direction):
    n = len(sample_df)
    if n == 0:
        return None

    # Recompute wind_push: sample's own flight direction + this game's wind vectors
    wind_push_sim = (
        game_row['meteo_x_vect'] * sample_df['ball_dir_x'].values +
        game_row['meteo_y_vect'] * sample_df['ball_dir_y'].values
    )

    # --- Model 1: simulate distance under this game's venue + weather ---
    X_cont_m1 = np.column_stack([
        sample_df['launch_speed'].values,
        sample_df['launch_angle'].values,
        np.full(n, game_row['temperature_2m']),
        np.full(n, game_row['dew_point_2m']),
        np.full(n, game_row['surface_pressure']),
        wind_push_sim,
        np.full(n, game_row['rolling_carry_365d']),
    ]).astype(np.float32)
    X_cont_m1 = scaler.transform(X_cont_m1).astype(np.float32)

    venue_code_m1 = pd.Series(
        [game_row['venue_id']], dtype=venue_cat_dtype.categories.dtype
    ).astype(venue_cat_dtype).cat.codes.iloc[0]
    X_cat_m1 = np.full(n, venue_code_m1, dtype=np.int64)

    with torch.no_grad():
        sim_distance = distance_best_model(
            torch.tensor(X_cont_m1).to(device), torch.tensor(X_cat_m1).to(device)
        ).cpu().numpy().flatten()

    # --- Model 2: simulate event odds using simulated distance + this game's venue ---
    wall_distance_sim, wall_height_sim = aux.get_wall_geometry_vectorized(
        game_row['parkID'], game_row['year'], sample_df['spray_angle'].values
    )
    distance_past_wall_sim = sim_distance - wall_distance_sim

    X_cont_m2 = np.column_stack([
        sample_df['launch_angle'].values,
        sample_df['spray_angle'].values,
        sim_distance,
        np.full(n, 1.0 if direction == 'L' else 0.0),
        wall_distance_sim,
        wall_height_sim,
        distance_past_wall_sim,
    ]).astype(np.float32)
    X_cont_m2 = events_scaler.transform(X_cont_m2).astype(np.float32)

    venue_code_m2 = pd.Series(
        [game_row['venue_id']], dtype=events_venue_cat_dtype.categories.dtype
    ).astype(events_venue_cat_dtype).cat.codes.iloc[0]
    X_cat_m2 = np.full(n, venue_code_m2, dtype=np.int64)

    with torch.no_grad():
        logits = events_best_model(
            torch.tensor(X_cont_m2).to(device), torch.tensor(X_cat_m2).to(device)
        )
        probs = torch.softmax(logits, dim=1).cpu().numpy()

    mean_probs = probs.mean(axis=0)
    result = dict(zip(events_classes, mean_probs))
    result['wOBA'] = float(np.array([WOBA_WEIGHTS.get(c, 0.0) for c in events_classes]) @ mean_probs)
    return result


def _build_today_games(aux, forecast_date):
    weather_df = pd.read_csv(
        os.path.join(baseball_path, "A06. Weather", "1. Open Meteo", f"Open Meteo {forecast_date}.csv")
    )
    today_weather = weather_df[weather_df['date'].astype(str) == forecast_date].reset_index()
    today_weather['gamePk'] = today_weather['game_id'].copy()

    today_weather['weather'] = today_weather['weather_code'].map(WEATHER_CODE_MAP).fillna('Cloudy.')
    today_weather.loc[today_weather['fieldInfo.roofType'].eq('Dome'), 'weather'] = 'Dome.'

    for idx, row in today_weather.iterrows():
        if row['fieldInfo.roofType'] == 'Retractable':
            temps = _venue_min_max(row)
            if (row['weather'] in BAD_WEATHER_LIST or
                    row['temperature_2m'] < temps['min_temp'] or
                    row['temperature_2m'] > temps['max_temp']):
                today_weather.at[idx, 'weather'] = 'Roof Closed.'

    # Roof override -- matches the historical weather_dataset roof-closed logic exactly,
    # including the manual Tropicana inclusion
    roof_mask = (
        today_weather['weather'].str.contains('Roof|Dome', case=False, na=False) |
        (today_weather['venue_id'].astype(str) == '12')  # Manual Tropicana inclusion
    )
    today_weather.loc[roof_mask, 'temperature_2m'] = 70
    today_weather.loc[roof_mask, 'dew_point_2m'] = 57
    if 'relative_humidity_2m' in today_weather.columns:
        today_weather.loc[roof_mask, 'relative_humidity_2m'] = 60

    # Wind vectors (park-relative)
    blowing_to_rad = np.radians((today_weather['wind_direction_10m'] + 180) % 360)
    raw_north = today_weather['wind_speed_10m'] * np.cos(blowing_to_rad)
    raw_east = today_weather['wind_speed_10m'] * np.sin(blowing_to_rad)
    theta = np.radians(today_weather['location.azimuthAngle'])
    today_weather['meteo_y_vect'] = raw_east * np.sin(theta) + raw_north * np.cos(theta)
    today_weather['meteo_x_vect'] = raw_east * np.cos(theta) - raw_north * np.sin(theta)

    today_weather.loc[roof_mask, 'meteo_x_vect'] = 0
    today_weather.loc[roof_mask, 'meteo_y_vect'] = 0

    today_weather['rolling_carry_365d'] = aux.latest_carry
    today_weather['date'] = forecast_date

    today_games = today_weather[
        ['gamePk', 'date', 'venue_id', 'venue_name', 'temperature_2m', 'dew_point_2m',
         'surface_pressure', 'meteo_x_vect', 'meteo_y_vect', 'rolling_carry_365d']
    ].dropna(subset=['temperature_2m', 'dew_point_2m', 'surface_pressure', 'meteo_x_vect', 'meteo_y_vect'])

    unrecognized = today_games[
        ~today_games['venue_id'].isin(venue_cat_dtype.categories) |
        ~today_games['venue_id'].isin(events_venue_cat_dtype.categories)
    ]
    if len(unrecognized):
        print(f"Dropping {len(unrecognized)} games at venues unseen in training:")
        print(unrecognized[['venue_id', 'venue_name']].drop_duplicates())

    today_games = today_games[
        today_games['venue_id'].isin(venue_cat_dtype.categories) &
        today_games['venue_id'].isin(events_venue_cat_dtype.categories)
    ].reset_index(drop=True)

    # Attach parkID + year for wall-geometry lookups
    today_games = today_games.merge(aux.park_venue_crosswalk[['parkID', 'venue_id']], on='venue_id', how='left')
    today_games['year'] = pd.to_datetime(today_games['date']).dt.year

    missing_park = today_games[today_games['parkID'].isna()]
    if len(missing_park):
        print(f"Dropping {len(missing_park)} games at venues missing from the park/venue crosswalk:")
        print(missing_park[['venue_id', 'venue_name']].drop_duplicates())
    today_games = today_games.dropna(subset=['parkID']).reset_index(drop=True)

    assert today_games['gamePk'].is_unique, "Duplicate gamePk in today_games — check upstream merge"

    print(f"Simulating {len(today_games):,} games")
    return today_games


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def get_daily_multipliers(date):
    """
    Returns a DataFrame of WFX multipliers for every recognized game on `date`.

    date: the date of the Open Meteo weather file to simulate (format matching
        your weather files, e.g. '20260720'). Usually today's date, but any
        date with a corresponding Open Meteo CSV works.

    Uses whichever distance/events models are currently loaded via
    U05Models.py -- this function does not select or load a model itself.
    """
    aux = _get_aux_state()
    today_games = _build_today_games(aux, date)

    today_sim_rows = []
    for _, game in today_games.iterrows():
        row = {'gamePk': game['gamePk'], 'venue_id': game['venue_id'], 'venue_name': game['venue_name']}
        for side, sample_df in [('L', aux.sim_sample_L), ('R', aux.sim_sample_R)]:
            sim = simulate_game(aux, sample_df, game, direction=side)
            if sim:
                for cls, val in sim.items():
                    row[f'{side}_{cls}_sim'] = val
        today_sim_rows.append(row)

    today_sim_df = pd.DataFrame(today_sim_rows)

    for cls in events_classes:
        today_sim_df[f'{cls}_wfx_unadj_l'] = (today_sim_df[f'L_{cls}_sim'] * aux.n_sample_L) / aux.baseline_counts_L[cls]
        today_sim_df[f'{cls}_wfx_unadj_r'] = (today_sim_df[f'R_{cls}_sim'] * aux.n_sample_R) / aux.baseline_counts_R[cls]

    today_sim_df['woba_wfx_unadj_l'] = today_sim_df['L_wOBA_sim'] / aux.baseline_rates_L['wOBA']
    today_sim_df['woba_wfx_unadj_r'] = today_sim_df['R_wOBA_sim'] / aux.baseline_rates_R['wOBA']

    today_multipliers = today_sim_df.merge(
        today_games[['gamePk', 'date', 'temperature_2m', 'dew_point_2m', 'surface_pressure',
                     'meteo_x_vect', 'meteo_y_vect', 'rolling_carry_365d']],
        on='gamePk'
    )[['gamePk', 'date', 'venue_id', 'venue_name', 'temperature_2m', 'dew_point_2m', 'surface_pressure',
       'meteo_x_vect', 'meteo_y_vect', 'rolling_carry_365d']
      + [c for c in today_sim_df.columns if 'wfx' in c]]

    return today_multipliers


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python Weather_Factors_Daily.py <date, e.g. 20260720>")

    result = get_daily_multipliers(sys.argv[1])
    print(result)
