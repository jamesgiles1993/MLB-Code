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
def create_wfx_df(similar_games, date):
    ### Variables
    # Define variable lists
    mlb_weather_variables = ['x_vect', 'y_vect', 'temperature'] # drop weather
    meteo_duplicates_variables = ['meteo_x_vect', 'meteo_y_vect', 'temperature_2m']
    meteo_weather_variables = ['relative_humidity_2m', 'dew_point_2m', 'surface_pressure']
    mlb_park_variables = ['fieldInfo.leftLine', 'fieldInfo.center', 'fieldInfo.rightLine', 'fieldInfo.leftCenter', 'fieldInfo.rightCenter', 'location.elevation'] # drop roof type

    # Define variable dummy list
    venue_dummy_list = ['venue_1', 'venue_2', 'venue_3', 'venue_4', 'venue_5', 'venue_7', 'venue_10', 'venue_12', 'venue_13', 
                    'venue_14', 'venue_15', 'venue_17', 'venue_19', 'venue_22', 'venue_31', 'venue_32', 'venue_680', 
                    'venue_2392', 'venue_2394', 'venue_2395', 'venue_2602', 'venue_2680', 'venue_2681', 'venue_2889', 
                    'venue_3289', 'venue_3309', 'venue_3312', 'venue_3313', 'venue_4169', 'venue_4705', 'venue_5325']
    
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

    # Event Averages
    event_averages = pd.read_csv(os.path.join(baseball_path, "Event Averages.csv"))
    event_averages = event_averages.add_suffix("_pred_batted")
    event_variables = list(event_averages.columns)

    #  Park Latest
    park_latest_df = pd.read_csv(os.path.join(baseball_path, "Park Latest.csv"))

    # Park and Weather Factors
    park_and_weather_df = pd.read_csv(os.path.join(baseball_path, "Park and Weather Factors.csv"))

    # Define pfx variables   
    pfx_variables = [col for col in park_latest_df if col.endswith("pfx")]

    # Define model inputs
    wfx_inputs = event_variables + pfx_variables + meteo_duplicates_variables + meteo_weather_variables + venue_dummy_list + ['b_L']

    def create_wfx_side_df(meteo_df, park_latest_df, event_averages, park_and_weather_df, wfx_inputs, similar_games, batSide):
        # Merge weather data with latest park data, specific to batting side
        wfx_sample = meteo_df.merge(park_latest_df[park_latest_df['batSide'] == batSide], on=['venue_id'], how='left')
        # Merge in event averages
        wfx_sample = wfx_sample.merge(event_averages, how='cross')

        # Create venue dummies
        for venue_dummy in venue_dummy_list:
            wfx_sample[venue_dummy] = (venue_dummy == "venue_" + wfx_sample["venue_id"].astype(str)).astype(int)

        # Create batter is lefty dummy
        wfx_sample['b_L'] = 1

        # Scale weather inputs
        X2 = wfx_sample[wfx_inputs].values
        X2_scaled = scale_wfx.transform(X2)

        # Predict WFX
        predictions2 = predict_wfx.predict(X2_scaled)

        # Create DataFrame for predictions
        prediction_df2 = pd.DataFrame(predictions2, columns=events_list)
        prediction_df2 = prediction_df2.add_suffix('_pred_weather')

        # Concatenate with original data
        wfx_sample = pd.concat([wfx_sample, prediction_df2.reset_index()], axis=1)

        # Calculate unadjusted WFX
        for event in events_list:
            wfx_sample[f'{event}_wfx_unadj'] = wfx_sample[f'{event}_pred_weather'] / wfx_sample[f'{event}_pred_batted']

        # Calibrate
        for event in events_list:
            pred_weather_col = f'{event}_pred_weather'
            ref_pred_weather_col = f'{event}_pred_weather_{str.lower(batSide)}'
            ref_pred_batted_col = f'{event}_pred_batted_{str.lower(batSide)}'
            ref_actual_col = f'{event}_{str.lower(batSide)}'

            pred_batted_output = []
            actual_output = []

            # Pull reference columns as arrays for speed
            pwf_venue = park_and_weather_df['venue_id'].values
            pwf_pred_weather = park_and_weather_df[ref_pred_weather_col].values
            pwf_pred_batted = park_and_weather_df[ref_pred_batted_col].values
            pwf_actual = park_and_weather_df[ref_actual_col].values

            for i, row in wfx_sample.iterrows():
                venue = row['venue_id']
                target_pred_weather = row[pred_weather_col]

                mask = pwf_venue == venue
                pred_weather_vals = pwf_pred_weather[mask]
                pred_batted_vals = pwf_pred_batted[mask]
                actual_vals = pwf_actual[mask]

                if len(pred_weather_vals) == 0 or np.isnan(target_pred_weather):
                    pred_batted_output.append(np.nan)
                    actual_output.append(np.nan)
                    continue

                nearest_idx = np.argsort(np.abs(pred_weather_vals - target_pred_weather))[:similar_games]
                pred_batted_output.append(np.nanmean(pred_batted_vals[nearest_idx]))
                actual_output.append(np.nanmean(actual_vals[nearest_idx]))

            # Save results to wfx_sample
            wfx_sample[f'{event}_pred_batted'] = pred_batted_output
            wfx_sample[event] = actual_output

            # Calculate adjusted wfx
            wfx_sample[f'{event}_wfx_adj'] = wfx_sample[event] / wfx_sample[f'{event}_pred_batted'] 


        return wfx_sample
    
    # Create side-specific WFX dataframes
    l_wfx_df = create_wfx_side_df(meteo_df, park_latest_df[park_latest_df['batSide'] == 'L'], event_averages, park_and_weather_df, wfx_inputs, similar_games, "L")
    r_wfx_df = create_wfx_side_df(meteo_df, park_latest_df[park_latest_df['batSide'] == 'R'], event_averages, park_and_weather_df, wfx_inputs, similar_games, "R")

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



