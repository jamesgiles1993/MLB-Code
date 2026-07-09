# %%
from U01Imports import *
from U02Functions import *
from U04Datasets import *
# from U05Models import *

# %%
# Columns from game_df
game_columns = ['game_id', 'game_datetime', 'game_date', 'date', 'year', 'game_type', 'status', 'away_team', 'home_team', 'doubleheader', 'game_num', 'venue_id', 'venue_name']
# Columns Venue Map
venue_columns = ['location.defaultCoordinates.latitude', 'location.defaultCoordinates.longitude',
                 'fieldInfo.leftLine', 'fieldInfo.center', 'fieldInfo.rightLine', 'fieldInfo.leftCenter',
                 'fieldInfo.rightCenter', 'location.elevation', 'location.azimuthAngle', 'fieldInfo.roofType', 'active']
# Columns from Open Mateo 
weather_columns = ['temperature_2m', 'relative_humidity_2m', 'dew_point_2m', 'surface_pressure', 'wind_speed_10m', 'wind_direction_10m', 'weather_code']
# Forecast-only columns from Open Meteo
forecast_only_columns = ['precipitation_probability']


tzf = TimezoneFinder()


def create_historic_weather_df(openmeteo, game_df):

    weather_columns = [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m",
        "weather_code", "surface_pressure", "wind_speed_10m", "wind_direction_10m"
    ]

    game_df = game_df.copy()

    # --- Step 1: Determine local date per game ---
    def get_local_date(row):
        tz_str = tzf.timezone_at(
            lat=row["location.defaultCoordinates.latitude"],
            lng=row["location.defaultCoordinates.longitude"]
        )
        local_tz = pytz.timezone(tz_str)
        return row["game_datetime"].tz_convert(local_tz).date()

    game_df["local_date"] = game_df.apply(get_local_date, axis=1)

    # --- Step 2: Get unique fetch combinations ---
    unique_keys = game_df[
        ["location.defaultCoordinates.latitude",
         "location.defaultCoordinates.longitude",
         "local_date"]
    ].drop_duplicates()

    all_weather = []

    # --- Step 3: Fetch weather once per key ---
    for _, row in unique_keys.iterrows():
        lat = row["location.defaultCoordinates.latitude"]
        lon = row["location.defaultCoordinates.longitude"]
        local_date = row["local_date"]

        start_date = str(local_date)
        end_date = str(local_date + pd.Timedelta(days=1))

        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": weather_columns,
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC"
        }

        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        hourly = response.Hourly()

        df = pd.DataFrame({
            "datetime": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
            "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
            "dew_point_2m": hourly.Variables(2).ValuesAsNumpy(),
            "weather_code": hourly.Variables(3).ValuesAsNumpy(),
            "surface_pressure": hourly.Variables(4).ValuesAsNumpy(),
            "wind_speed_10m": hourly.Variables(5).ValuesAsNumpy(),
            "wind_direction_10m": hourly.Variables(6).ValuesAsNumpy(),
        })

        df["location.defaultCoordinates.latitude"] = lat
        df["location.defaultCoordinates.longitude"] = lon
        df["local_date"] = local_date

        all_weather.append(df)

    weather_df = pd.concat(all_weather, ignore_index=True)

    # --- Step 4: Sort for merge_asof ---
    game_df = game_df.sort_values("game_datetime")
    weather_df = weather_df.sort_values("datetime")

    # --- Step 5: Merge nearest timestamp ---
    merged = pd.merge_asof(
        game_df,
        weather_df,
        left_on="game_datetime",
        right_on="datetime",
        by=["location.defaultCoordinates.latitude",
            "location.defaultCoordinates.longitude",
            "local_date"],
        direction="nearest"
    )

    # --- Cleanup ---
    merged.drop(columns=["datetime", "local_date"], inplace=True)

    
    return merged


def create_daily_weather_df(openmeteo, game_df):

    weather_columns = [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m",
        "precipitation_probability", "surface_pressure",
        "wind_speed_10m", "wind_direction_10m", "weather_code"
    ]

    game_df = game_df.copy()

    # --- Step 1: Create fetch windows ---
    game_df["start"] = game_df["game_datetime"] - pd.Timedelta(hours=1)
    game_df["end"]   = game_df["game_datetime"] + pd.Timedelta(hours=1)

    unique_keys = game_df[
        ["location.defaultCoordinates.latitude",
         "location.defaultCoordinates.longitude",
         "start",
         "end"]
    ].drop_duplicates()

    all_weather = []

    for _, row in unique_keys.iterrows():
        lat = row["location.defaultCoordinates.latitude"]
        lon = row["location.defaultCoordinates.longitude"]
        start = row["start"].isoformat()
        end = row["end"].isoformat()

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": weather_columns,
            "start": start,
            "end": end,
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "past_days": 2
        }

        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
        hourly = response.Hourly()

        df = pd.DataFrame({
            "datetime": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            ),
            "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
            "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
            "dew_point_2m": hourly.Variables(2).ValuesAsNumpy(),
            "precipitation_probability": hourly.Variables(3).ValuesAsNumpy(),
            "surface_pressure": hourly.Variables(4).ValuesAsNumpy(),
            "wind_speed_10m": hourly.Variables(5).ValuesAsNumpy(),
            "wind_direction_10m": hourly.Variables(6).ValuesAsNumpy(),
            "weather_code": hourly.Variables(7).ValuesAsNumpy(),
        })

        df["location.defaultCoordinates.latitude"] = lat
        df["location.defaultCoordinates.longitude"] = lon

        all_weather.append(df)

    weather_df = pd.concat(all_weather, ignore_index=True)

    # --- Merge ---
    game_df = game_df.sort_values("game_datetime")
    weather_df = weather_df.sort_values("datetime")

    merged = pd.merge_asof(
        game_df,
        weather_df,
        left_on="game_datetime",
        right_on="datetime",
        by=["location.defaultCoordinates.latitude",
            "location.defaultCoordinates.longitude"],
        direction="nearest"
    )

    merged.drop(columns=["datetime", "start", "end"], inplace=True)

    return merged


# %%
# Scrapes Kevin's weather forecast
def kevin(date_dash):
    # PropFinder URL
    url = f"https://api.propfinder.app/mlb/weather-games?date={date_dash}"

    # Call API
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    # Handle case where API returns a single dict vs list
    if isinstance(data, dict):
        data = [data]

    # Extract fields
    rows = []
    for game in data:
        rows.append({
            "gameId": game.get("id"),
            "gameDate": game.get("gameDate"),
            "ballparkId": game.get("ballpark", {}).get("id"),
            "homeTeamCode": game.get("homeTeam", {}).get("code"),
            "awayTeamCode": game.get("visitorTeam", {}).get("code"),
            "weatherIndicator": game.get("weatherIndicator")
        })

    # Convert to DataFrame
    df = pd.DataFrame(rows)

    # Use standardized team codes
    df['home'] = df['homeTeamCode'].map(team_dict)
    df['away'] = df['awayTeamCode'].map(team_dict)

    
    # Convert to EST    
    df['gameDate'] = (
        pd.to_datetime(df['gameDate'], utc=True)
          .dt.tz_convert('America/New_York')
          .dt.strftime('%Y-%m-%d %I:%M %p')
    )

    
    # --- Add notes ---
    notes_url = "https://api.propfinder.app/mlb/weather-notes"
    notes_response = requests.get(notes_url)
    notes_response.raise_for_status()
    notes_data = notes_response.json()

    if isinstance(notes_data, dict):
        notes_data = [notes_data]

    if len(notes_data) > 0:
        notes_df = pd.DataFrame(notes_data)

        # Keep latest note per gameId
        notes_df = (
            notes_df
            .sort_values("createdAt")
            .drop_duplicates("gameId", keep="last")
        )

        notes_df = notes_df[["gameId", "content"]].rename(columns={"content": "weatherNote"})

        # Merge
        df = df.merge(notes_df, on="gameId", how="left")
    else:
        df["weatherNote"] = ""

    df['weatherNote'] = df['weatherNote'].fillna(" ")

    
    return df


# %%
# Color-code Kevin
def color_rows(row):
    color_map = {
        "Green": "background-color: #b6f2b6",
        "Yellow": "background-color: #fff3b0",
        "Orange": "background-color: #ffd6a5",
        "Red": "background-color: #ffadad"
    }
    return [color_map.get(row["weatherIndicator"], "")] * len(row)


# %%
__all__ = [name for name in globals() if not name.startswith("_")]