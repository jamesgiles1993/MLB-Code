# %%
from DataImports import *

# %%
# Calculate x and y wind vectors
def calculate_vectors(row, azimuth_column, wind_column, speed_column):
    angle = row[wind_column] - row[azimuth_column]
    
    # Calculate vectors
    x_vect = round(math.sin(math.radians(angle)), 5) * row[speed_column] * -1
    y_vect = round(math.cos(math.radians(angle)), 5) * row[speed_column] * -1


    return pd.Series([x_vect, y_vect], index=['x_vect', 'y_vect'])


# %%
# Create Daily WFX Data
def create_wfx_df(date):
    ### Variables
    # Define variable lists
    mlb_weather_variables = ['x_vect', 'y_vect', 'temperature']  # Deprecated
    meteo_duplicates_variables = ['meteo_x_vect', 'meteo_y_vect', 'temperature_2m']
    meteo_weather_variables = ['relative_humidity_2m', 'dew_point_2m', 'surface_pressure']
    mlb_park_variables = ['fieldInfo.leftLine', 'fieldInfo.center', 'fieldInfo.rightLine', 'fieldInfo.leftCenter', 'fieldInfo.rightCenter', 'location.elevation']  # Deprecated
    venue_dummy_list  # Defined in U01. Imports 

    ### Data
    # Open Meteo
    # Read in weather data
    meteo_df = pd.read_csv(os.path.join(baseball_path, "A06. Weather", "1. Open Meteo", f"Open Meteo {date}.csv"), encoding='iso-8859-1')
    # Calculate vectors
    meteo_df[['meteo_x_vect', 'meteo_y_vect']] = meteo_df.apply(lambda row: calculate_vectors(row, 'location.azimuthAngle', 'wind_direction_10m', 'wind_speed_10m'), axis=1)
    # Add weather data from boxscore
    meteo_df[['weather', 'wind', 'venue', 'date', 'missing_weather']] = meteo_df['game_id'].apply(lambda game_id: pd.Series(create_box(game_id)))
    # Adjust weather in domes
    mask = meteo_df['weather'].str.contains('Roof|Dome', case=False, na=False)

    meteo_df.loc[mask, 'temperature_2m'] = 68
    meteo_df.loc[mask, 'meteo_x_vect'] = 0
    meteo_df.loc[mask, 'meteo_y_vect'] = 0
    meteo_df.loc[mask, 'relative_humidity_2m'] = 60
    meteo_df.loc[mask, 'dew_point_2m'] = 57

    #  Park Latest
    park_latest_df = pd.read_csv(os.path.join(baseball_path, "Park Latest.csv"))

    # Define pfx variables
    eps = 1e-4

    for event in events_list:
        park_latest_df[f'{event}_log_pfx'] = np.log(park_latest_df[f'{event}_pfx'] + eps)

    pfx_variables = [col for col in park_latest_df if col.endswith("log_pfx")]

    # Define model inputs
    wfx_inputs = pfx_variables + meteo_duplicates_variables + meteo_weather_variables + venue_dummy_list + ['b_L']

    def create_wfx_side_df(meteo_df, park_latest_df, wfx_inputs, batSide):
        # Merge weather data with latest park data, specific to batting side
        park_latest_df['venue_id'] = park_latest_df['venue_id_adj'].str.replace(r'[A-Za-z]', '', regex=True)
        meteo_df['venue_id'] = meteo_df['venue_id'].astype(str)
        wfx_sample = meteo_df.merge(park_latest_df[park_latest_df['batSide'] == batSide], on=['venue_id'], how='left')

        # Create venue dummies
        for venue_dummy in venue_dummy_list:
            wfx_sample[venue_dummy] = (venue_dummy == "venue_" + wfx_sample["venue_id"].astype(str)).astype(int)

        # Create batter is lefty dummy
        wfx_sample['b_L'] = 1

        # Scale weather inputs
        scale_cols = ['meteo_x_vect','meteo_y_vect','temperature_2m','relative_humidity_2m','dew_point_2m','surface_pressure']  # From M01. Weather Factors
        wfx_sample[scale_cols] = scale_wfx.transform(wfx_sample[scale_cols])

        # Predict WFX
        log_multiplier_preds = predict_wfx.predict(wfx_sample[wfx_inputs].values)

        # Calculate WFX
        for i, event in enumerate(events_list):
            # Uncentered log multiplier
            wfx_sample[f'{event}_log_multiplier_pred'] = log_multiplier_preds[:, i]
            
            # Uncentered WFX
            wfx_sample[f'{event}_wfx_unadj'] = np.exp(log_multiplier_preds[:, i])
            
            # Centered log multiplier
            wfx_sample[f'{event}_log_multiplier_pred_centered'] = (wfx_sample[f'{event}_log_multiplier_pred'] - wfx_sample.groupby('batSide')[f'{event}_log_multiplier_pred'].transform('mean'))

            # Centered WFX
            wfx_sample[f'{event}_wfx_adj'] = np.exp(wfx_sample[f'{event}_log_multiplier_pred_centered'])

        return wfx_sample
    
    # Create side-specific WFX dataframes
    l_wfx_df = create_wfx_side_df(meteo_df, park_latest_df[park_latest_df['batSide'] == 'L'], wfx_inputs, "L")
    r_wfx_df = create_wfx_side_df(meteo_df, park_latest_df[park_latest_df['batSide'] == 'R'], wfx_inputs, "R")

    # Merge together
    wfx_df = pd.merge(l_wfx_df, r_wfx_df[["venue_id", "game_num"] + [col for col in r_wfx_df if "wfx" in col]], on=['venue_id', 'game_num'], how='left', suffixes=("_l", "_r"))
    
    # Rename (game_id is generated in historic wfx code)
    wfx_df.rename(columns={'game_id': 'gamePk'}, inplace=True)

    # Keep relevant columns
    keep_columns = ['gamePk', 'game_datetime', 'game_date', 'date', 'year', 'game_type', 'status', 'away_team', 'home_team', 'doubleheader', 'game_num', 'venue_id', 'venue_name', 
                'location.defaultCoordinates.latitude', 'location.defaultCoordinates.longitude', 'fieldInfo.leftLine', 'fieldInfo.center', 'fieldInfo.rightLine', 'fieldInfo.leftCenter', 'fieldInfo.rightCenter', 
                'location.elevation', 'location.azimuthAngle', 'fieldInfo.roofType', 'active', 
                'temperature_2m', 'relative_humidity_2m', 'dew_point_2m', 'surface_pressure', 'wind_speed_10m', 'wind_direction_10m', 'weather_code',
                'meteo_x_vect', 'meteo_y_vect', 'weather', 'wind', 'missing_weather']


    return wfx_df[keep_columns + [col for col in wfx_df if "wfx" in col]]


# %%
__all__ = [name for name in globals() if not name.startswith("_")]