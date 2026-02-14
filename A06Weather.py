# %%
from U01Imports import *
from U02Functions import *
from U04Datasets import *
from U05Models import *

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

# %%
# Fetch historical weather data for a given game datetime and location
def fetch_historical_weather_data(openmeteo, latitude, longitude, game_datetime):
    game_date = game_datetime.strftime("%Y-%m-%d")
    next_day = (game_datetime + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": game_date,
        "end_date": next_day,  # include next day to cover all 24 hours
        "hourly": [
            "temperature_2m", "relative_humidity_2m", "dew_point_2m", 
            "weather_code", "surface_pressure", "wind_speed_10m", "wind_direction_10m"
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "UTC"  # important!
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    hourly = response.Hourly()
    hourly_data = {
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
        "wind_direction_10m": hourly.Variables(6).ValuesAsNumpy()
    }

    
    return pd.DataFrame(hourly_data)

# %%
# Create historic weather dataframe
def create_historic_weather_df(openmeteo, game_df):
    """Append weather data to each game in game_df based on game_datetime."""

    # Convert game_datetime to UTC
    game_df["game_datetime"] = pd.to_datetime(game_df["game_datetime"], utc=True)

    # Lists to store the matched weather data
    weather_columns = [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m",
        "weather_code", "surface_pressure", "wind_speed_10m", "wind_direction_10m"
    ]
    weather_data_lists = {col: [] for col in weather_columns}

    # Loop through each game in the DataFrame
    for _, row in game_df.iterrows():
        latitude = row["location.defaultCoordinates.latitude"]
        longitude = row["location.defaultCoordinates.longitude"]
        game_datetime = row["game_datetime"]

        # Fetch historical weather data for that day
        weather_data = fetch_historical_weather_data(openmeteo, latitude, longitude, game_datetime)
        
        # Find the closest weather timestamp to game_datetime (typically, first top of the hour after game starts)
        closest_weather_row = weather_data.iloc[
            (weather_data["datetime"] - game_datetime).abs().argsort()[0]
        ]

        # Append the closest weather data to lists
        for col in weather_columns:
            weather_data_lists[col].append(closest_weather_row[col])

    # Add the weather data as new columns in game_df
    for col in weather_columns:
        game_df[col] = weather_data_lists[col]


    return game_df


# %%
# Fetch today's weather data for a given game datetime and location
def fetch_weather_data(openmeteo, latitude, longitude, start, end):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": [
            "temperature_2m", "relative_humidity_2m", "dew_point_2m", 
            "precipitation_probability", "surface_pressure", 
            "wind_speed_10m", "wind_direction_10m", "weather_code"
        ],
        "start": start,  # ISO 8601
        "end": end,      # ISO 8601
        "wind_speed_unit": "mph",
        "temperature_unit": "fahrenheit",
        "precipitation_unit": "inch",
        "timezone": "UTC",       # ✅ Ensure UTC so hourly timestamps align
        "past_days": 2           # ✅ Include recent data in case game time is recent past
    }

    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    hourly = response.Hourly()

    hourly_data = {
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
    }

    df = pd.DataFrame(hourly_data)

    # Filter the data to only include the requested window
    df = df[(df["datetime"] >= pd.to_datetime(start, utc=True)) &
            (df["datetime"] <= pd.to_datetime(end, utc=True))]

    
    return df

# %%
# Create daily weather dataframe
def create_daily_weather_df(openmeteo, game_df):
    """Append hourly weather data (forecast or recent) to each game."""
    weather_columns = [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m",
        "precipitation_probability", "surface_pressure",
        "wind_speed_10m", "wind_direction_10m", "weather_code"
    ]
    weather_data_lists = {col: [] for col in weather_columns}

    for _, row in game_df.iterrows():
        latitude = row["location.defaultCoordinates.latitude"]
        longitude = row["location.defaultCoordinates.longitude"]
        game_datetime = pd.to_datetime(row["game_datetime"], utc=True)

        # Fetch 2 hours around game start to ensure coverage
        start = (game_datetime - pd.Timedelta(hours=1)).isoformat()
        end = (game_datetime + pd.Timedelta(hours=1)).isoformat()

        try:
            weather_data = fetch_weather_data(openmeteo, latitude, longitude, start, end)
            if not weather_data.empty:
                # Find record closest to game time
                closest = weather_data.iloc[(weather_data["datetime"] - game_datetime).abs().argsort()[0]]
                for col in weather_columns:
                    weather_data_lists[col].append(closest[col])
            else:
                # If API returned no data, append NaN
                for col in weather_columns:
                    weather_data_lists[col].append(np.nan)
        except Exception as e:
            print(f"⚠️ Weather fetch failed for {latitude},{longitude} at {game_datetime}: {e}")
            for col in weather_columns:
                weather_data_lists[col].append(np.nan)

    # Add the weather columns
    for col in weather_columns:
        game_df[col] = weather_data_lists[col]

    
    return game_df


# %%
# Scrapes Rotogrinders weather forecast
def rotogrinders_weather(date, team_map):
    # Send a GET request to the URL and retrieve the response
    response = requests.get("https://rotogrinders.com/weather/mlb")

    # Check if the response is successful (status code 200)
    if response.status_code == 200:
        # Get the HTML content from the response
        html_content = response.text

        soup = BeautifulSoup(html_content, "html.parser")

        # Find all <li> elements within the <ul>
        li_elements = soup.find_all("li", class_="weather-blurb")

        # Create an empty list to store the data
        data = []

        for li_element in li_elements:
            # Extract the tag colors from the <span> elements
            tag_elements = li_element.find_all("span", class_=["green", "yellow", "orange", "red"])
        
            # Extract the first tag color
            tag = tag_elements[0].text.strip() if tag_elements else None
        
            # Extract the second tag color if it exists
            tag2 = tag_elements[1].text.strip() if len(tag_elements) > 1 else None
        
            # Extract the matchup from the <span> element with class "bold"
            matchup_span = li_element.find("span", class_="bold")
            matchup = matchup_span.text.strip() if matchup_span else None
        
            # Extract the description if it exists
            if matchup_span:
                description_span = matchup_span.find_next_sibling("span")
                description = description_span.text.strip() if description_span else None
            else:
                description = None
        
            # Append the data to the list
            data.append({"Tag": tag, "Tag2": tag2, "Matchup": matchup, "Description": description})


        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(data)

        df[['away', 'home']] = df['Matchup'].str.split(" @ ", expand=True)

        # Add in DK team abbreviations 
        df = df.merge(team_map[['ROTOGRINDERSTEAM', 'DKTEAM']], left_on=['away'], right_on=['ROTOGRINDERSTEAM'], how='left', suffixes=("", "_away"))
        df = df.merge(team_map[['ROTOGRINDERSTEAM', 'DKTEAM']], left_on=['home'], right_on=['ROTOGRINDERSTEAM'], how='left', suffixes=("", "_home"))
        df = df[['Tag', 'Tag2', 'Matchup', 'DKTEAM', 'DKTEAM_home', 'Description']]
        df.rename(columns={'DKTEAM':'Away', 'DKTEAM_home': 'Home'}, inplace=True)
        
        # Add the date column to the DataFrame
        df['date'] = date

        return df
    else:
        # Return an error message if the response is not successful
        return "Failed to retrieve data. Response status code: {}".format(response.status_code)


# %%
__all__ = [name for name in globals() if not name.startswith("_")]