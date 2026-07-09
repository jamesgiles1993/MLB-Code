# U01. Imports-Sim
# This provides a lighter selection of imports, minimizing load required by joblib works
# Type: Utility
# Run Frequency: Frequent
# Created: 11/1/2023
# Updated: 8/20/2025



### Packages
import csv
import glob
import math
import numpy as np
import os
import pandas as pd
import pickle
import pytz
import random
import re
import shutil
import statsapi
import time
import torch.nn as nn
import warnings
import datetime

from copy import deepcopy
from joblib import Parallel, delayed
from sklearn.neural_network import MLPClassifier, MLPRegressor
from thefuzz import process



### Display Options
warnings.simplefilter(action="ignore")

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)
pd.set_option('display.float_format', '{:.6f}'.format)



### Paths
model_path = r"C:\Users\James\Documents\MLB\Models"
baseball_path = r"C:\Users\James\Documents\MLB\Data"
download_path = r"C:\Users\James\Downloads"



### Dates
# Today
todaysdate_dt = datetime.date.today()

todaysdate = todaysdate_dt.strftime("%Y%m%d")
todaysdate_dash = todaysdate_dt.strftime("%Y-%m-%d")
todaysdate_slash = todaysdate_dt.strftime("%m/%d/%Y")

# Yesterday
yesterdaysdate_dt = datetime.datetime.now() - datetime.timedelta(days=1)

yesterdaysdate = yesterdaysdate_dt.strftime("%Y%m%d")
yesterdaysdate_dash = yesterdaysdate_dt.strftime("%Y-%m-%d")
yesterdaysdate_slash = yesterdaysdate_dt.strftime("%m/%d/%Y")



### Venue Lists
# Maintained Venues
# Logic: All active venues and all recent venues with all major alterations treated separately. (Current Camden Yards is 2, recent versions are 2A and 2B)
venue_nums = ['1', '2', '2A', '2B', '3', '4', '5', '7', '7A', '10', '12', '13', '14', '15', '17', '19', '22', '31', '32', '680', '2392',
              '2394', '2395', '2523', '2529', '2602', '2680', '2681', '2889', '3289', '3309', '3312', '3313', '4169', '4705', '5325']  # Taken from M01. Weather Factors.ipynb

# Dummies
venue_dummy_list = [f"venue_{num}" for num in venue_nums]



### Stat Lists
# Events
events_list = ['b1', 'b2', 'b3', 'bb', 'fo', 'go', 'hbp', 'hr', 'lo', 'po', 'so']

# MLB API-Derived Stats
calc_list = ['iso', 'slg', 'obp', 'woba']

# Statcast List
statcast_list = ['estimated_woba_using_speedangle', 'to_left', 'to_middle', 'to_right', 'hard_hit', 'barrel']

# Short-Period Stats
batter_stats_short = ([f"{stat}_b" for stat in events_list] + 
                    [f"{stat}_b" for stat in calc_list] + 
                    [f"{stat}_b" for stat in statcast_list])

pitcher_stats_short = ([f"{stat}_p" for stat in events_list] + 
                    [f"{stat}_p" for stat in calc_list] + 
                    [f"{stat}_p" for stat in statcast_list])

# Long-Period Stats
batter_stats_long = ([f"{stat}_b_long" for stat in events_list] + 
                    [f"{stat}_b_long" for stat in calc_list] + 
                    [f"{stat}_b_long" for stat in statcast_list])

pitcher_stats_long = ([f"{stat}_p_long" for stat in events_list] + 
                    [f"{stat}_p_long" for stat in calc_list] + 
                    [f"{stat}_p_long" for stat in statcast_list])

# Batter Stats
batter_inputs = batter_stats_short + batter_stats_long

batter_stats_l = [f'{stat}_l' for stat in batter_inputs]
batter_stats_r = [f'{stat}_r' for stat in batter_inputs]

# Pitcher Stats
pitcher_inputs = pitcher_stats_short + pitcher_stats_long

pitcher_stats_l = [f'{stat}_l' for stat in pitcher_inputs]
pitcher_stats_r = [f'{stat}_r' for stat in pitcher_inputs]

# Steamer Batter Stats
batter_stats_fg = ['b1_rate', 'b2_rate', 'b3_rate', 'hr_rate', 'bb_rate', 'hbp_rate', 'so_rate', 'woba', 'slg', 'obp']

# Steamer Pitcher Stats
pitcher_stats_fg = ['H9', 'HR9', 'K9', 'BB9', 'GBrate', 'FBrate', 'LDrate', 'SIERA']


### Create Universal Team Map Dictionary
team_map = pd.read_csv(os.path.join(baseball_path, "Utilities", "Team Map.csv"))

# Initialize an empty dictionary
team_dict = {}

# Filter columns that end with "TEAM"
team_columns = [col for col in team_map.columns if col.endswith("TEAM") or col.endswith("NAME") or col.endswith("Id")]

# Iterate over each row in the dataframe
for _, row in team_map.iterrows():
    bbref_team = row['BBREFTEAM']  # Get the BBREFTEAM value
    # Iterate over filtered columns in the row
    for column in team_columns:
        value = row[column]
        if pd.notna(value):  # Skip NaN values
            team_dict[value] = bbref_team




### Create Venue Map DataFrame
def create_venue_map(write=False):
    # Fetch JSON data from the URL
    response = requests.get('https://statsapi.mlb.com/api/v1/venues?hydrate=location,fieldInfo,timezone')
    data = response.json()
    
    # Extract venue details 
    venues = data.get("venues", data)  
    
    # Normalize the JSON into a DataFrame
    df = pd.json_normalize(venues)

    # Save to CSV
    if write == True:
        df.sort_values('id').to_csv(os.path.join(baseball_path, "Utilities", "Venue Map.csv"), index=False)


    return df

### Add Missing Stadium Dimension Values
# Read in Venue Map
venue_map_df = pd.read_csv(os.path.join(baseball_path, "Utilities", "Venue Map.csv"))

# George M. Steinbrenner
venue_map_df.loc[venue_map_df['id'] == 2523, ['fieldInfo.leftCenter', 'fieldInfo.rightCenter']] = [399.0, 385.0] # Yankee Stadium dimensions
# Sutter Health Park
venue_map_df.loc[venue_map_df['id'] == 2529, ['fieldInfo.leftCenter', 'fieldInfo.rightCenter']] = [375.0, 368.0] # https://x.com/JonPgh/status/1875224135573594599
# Estadio Alfredo Harp Helu
venue_map_df.loc[venue_map_df['id'] == 5340, ['location.defaultCoordinates.latitude', 'location.defaultCoordinates.longitude']] = [19.4042918, -99.0857851] # https://bw.maptons.com/p/9338059849



__all__ = [name for name in globals() if not name.startswith("_")]