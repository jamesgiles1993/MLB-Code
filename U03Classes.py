#!/usr/bin/env python
# coding: utf-8

# # U03. Classes
# - This imports classes used to construct objects used in simulating games
# - Type: Utility
# - Run Frequency: Frequent
# - Created: 11/1/2023
# - Updated: 8/20/2025

# %%
from U01Imports import *
from U02Functions import *

# ### Player Attributes

# Read in any matchup file to identify columns with player attributes

# In[1]:


# import pandas as pd
# test_path = r"C:\Users\James\Documents\MLB\Data\B01. Matchups\Matchups 20240609\COL@STL 745167 1415.xlsx"

# batter_df = pd.read_excel(test_path, sheet_name = "AwayBatters")
# batter_columns = batter_df.columns.tolist()

# pitcher_df = pd.read_excel(test_path, sheet_name = "AwayPitchers")
# pitcher_columns = pitcher_df.columns.tolist()

# del batter_df, pitcher_df


# In[6]:
# from U01Imports import *
# model_path = r"C:\Users\james\Documents\MLB\Models"
# baseball_path = r"C:\Users\james\Documents\MLB\Database"
# download_path = r"C:\Users\james\Downloads"


venue_nums = ['1', '2', '3', '4', '5', '7', '10', '12', '13', '14', '15', '16', '17', '19', '22', '31', '32', 
              '680', '2392', '2394', '2395', '2535', '2536', '2602', '2680', '2681', '2701', '2735', '2756', 
              '2889', '3289', '3309', '3312', '3313', '4169', '4705', '5010', '5325', '5365', '5381', '5445']

venue_inputs = [f"venue_{num}" for num in venue_nums]



batter_columns = ['id', 'fullName', 'firstName', 'lastName', 'position', 'batSide', 'pitchHand', 'date', 'teamId', 'status', 'order', 'batting_order', 'Leverage', 'weather', 'wind', 'park', 'temperature', 'windSpeed', 'windDirection', 'y_vect', 'x_vect', 'venue_id', 'away_starter', 'home_starter', 'date_time', 'b1_b_l', 'b2_b_l', 'b3_b_l', 'bb_b_l', 'fo_b_l', 'go_b_l', 'hbp_b_l', 'hr_b_l', 'lo_b_l', 'po_b_l', 'so_b_l', 'estimated_woba_using_speedangle_b_l', 'to_left_b_l', 'to_middle_b_l', 'to_right_b_l', 'hard_hit_b_l', 'barrel_b_l', 'iso_b_l', 'slg_b_l', 'obp_b_l', 'woba_b_l', 'totalDistance_b_l', 'launchSpeed_b_l', 'b1_b_long_l', 'b2_b_long_l', 'b3_b_long_l', 'bb_b_long_l', 'fo_b_long_l', 'go_b_long_l', 'hbp_b_long_l', 'hr_b_long_l', 'lo_b_long_l', 'po_b_long_l', 'so_b_long_l', 'estimated_woba_using_speedangle_b_long_l', 'to_left_b_long_l', 'to_middle_b_long_l', 'to_right_b_long_l', 'hard_hit_b_long_l', 'barrel_b_long_l', 'iso_b_long_l', 'slg_b_long_l', 'obp_b_long_l', 'woba_b_long_l', 'totalDistance_b_long_l', 'launchSpeed_b_long_l', 'imp_b_l', 'pa_b_l', 'pa_b_long_l', 'b1_b_r', 'b2_b_r', 'b3_b_r', 'bb_b_r', 'fo_b_r', 'go_b_r', 'hbp_b_r', 'hr_b_r', 'lo_b_r', 'po_b_r', 'so_b_r', 'estimated_woba_using_speedangle_b_r', 'to_left_b_r', 'to_middle_b_r', 'to_right_b_r', 'hard_hit_b_r', 'barrel_b_r', 'iso_b_r', 'slg_b_r', 'obp_b_r', 'woba_b_r', 'totalDistance_b_r', 'launchSpeed_b_r', 'b1_b_long_r', 'b2_b_long_r', 'b3_b_long_r', 'bb_b_long_r', 'fo_b_long_r', 'go_b_long_r', 'hbp_b_long_r', 'hr_b_long_r', 'lo_b_long_r', 'po_b_long_r', 'so_b_long_r', 'estimated_woba_using_speedangle_b_long_r', 'to_left_b_long_r', 'to_middle_b_long_r', 'to_right_b_long_r', 'hard_hit_b_long_r', 'barrel_b_long_r', 'iso_b_long_r', 'slg_b_long_r', 'obp_b_long_r', 'woba_b_long_r', 'totalDistance_b_long_r', 'launchSpeed_b_long_r', 'imp_b_r', 'pa_b_r', 'pa_b_long_r', 'date_steamer', 'steamerid', 'sb', 'sba', 'sbo', 'obp', 'slg', 'woba', 'b1_rate', 'b2_rate', 'b3_rate', 'hr_rate', 'bb_rate', 'hbp_rate', 'so_rate']
batter_columns = ['id', 'fullName', 'firstName', 'lastName', 'position', 'batSide', 'pitchHand', 'date', 'teamId', 'status', 'order', 'Leverage', 'venue_id', 'batting_order', 'date_time', 'b1_b_l', 'b2_b_l', 'b3_b_l', 'bb_b_l', 'fo_b_l', 'go_b_l', 'hbp_b_l', 'hr_b_l', 'lo_b_l', 'po_b_l', 'so_b_l', 'iso_b_l', 'slg_b_l', 'obp_b_l', 'woba_b_l', 'estimated_woba_using_speedangle_b_l', 'to_left_b_l', 'to_middle_b_l', 'to_right_b_l', 'hard_hit_b_l', 'barrel_b_l', 'b1_b_long_l', 'b2_b_long_l', 'b3_b_long_l', 'bb_b_long_l', 'fo_b_long_l', 'go_b_long_l', 'hbp_b_long_l', 'hr_b_long_l', 'lo_b_long_l', 'po_b_long_l', 'so_b_long_l', 'iso_b_long_l', 'slg_b_long_l', 'obp_b_long_l', 'woba_b_long_l', 'estimated_woba_using_speedangle_b_long_l', 'to_left_b_long_l', 'to_middle_b_long_l', 'to_right_b_long_l', 'hard_hit_b_long_l', 'barrel_b_long_l', 'imp_b_l', 'pa_b_l', 'b1_b_r', 'b2_b_r', 'b3_b_r', 'bb_b_r', 'fo_b_r', 'go_b_r', 'hbp_b_r', 'hr_b_r', 'lo_b_r', 'po_b_r', 'so_b_r', 'iso_b_r', 'slg_b_r', 'obp_b_r', 'woba_b_r', 'estimated_woba_using_speedangle_b_r', 'to_left_b_r', 'to_middle_b_r', 'to_right_b_r', 'hard_hit_b_r', 'barrel_b_r', 'b1_b_long_r', 'b2_b_long_r', 'b3_b_long_r', 'bb_b_long_r', 'fo_b_long_r', 'go_b_long_r', 'hbp_b_long_r', 'hr_b_long_r', 'lo_b_long_r', 'po_b_long_r', 'so_b_long_r', 'iso_b_long_r', 'slg_b_long_r', 'obp_b_long_r', 'woba_b_long_r', 'estimated_woba_using_speedangle_b_long_r', 'to_left_b_long_r', 'to_middle_b_long_r', 'to_right_b_long_r', 'hard_hit_b_long_r', 'barrel_b_long_r', 'imp_b_r', 'pa_b_r', 'firstname', 'lastname', 'mlbamid', 'steamerid', 'sb', 'sba', 'sbo', 'obp', 'slg', 'woba', 'b1_rate', 'b2_rate', 'b3_rate', 'hr_rate', 'bb_rate', 'hbp_rate', 'so_rate']

# In[8]:

pitcher_columns = ['id', 'fullName', 'firstName', 'lastName', 'position', 'batSide', 'pitchHand', 'date', 'teamId', 'status', 'order', 'batting_order', 'Leverage', 'weather', 'wind', 'park', 'temperature', 'windSpeed', 'windDirection', 'y_vect', 'x_vect', 'venue_id', 'away_starter', 'home_starter', 'date_time', 'b1_p_l', 'b2_p_l', 'b3_p_l', 'bb_p_l', 'fo_p_l', 'go_p_l', 'hbp_p_l', 'hr_p_l', 'lo_p_l', 'po_p_l', 'so_p_l', 'estimated_woba_using_speedangle_p_l', 'to_left_p_l', 'to_middle_p_l', 'to_right_p_l', 'hard_hit_p_l', 'barrel_p_l', 'iso_p_l', 'slg_p_l', 'obp_p_l', 'woba_p_l', 'maxSpeed_p_l', 'maxSpin_p_l', 'b1_p_long_l', 'b2_p_long_l', 'b3_p_long_l', 'bb_p_long_l', 'fo_p_long_l', 'go_p_long_l', 'hbp_p_long_l', 'hr_p_long_l', 'lo_p_long_l', 'po_p_long_l', 'so_p_long_l', 'estimated_woba_using_speedangle_p_long_l', 'to_left_p_long_l', 'to_middle_p_long_l', 'to_right_p_long_l', 'hard_hit_p_long_l', 'barrel_p_long_l', 'iso_p_long_l', 'slg_p_long_l', 'obp_p_long_l', 'woba_p_long_l', 'maxSpeed_p_long_l', 'maxSpin_p_long_l', 'imp_p_l', 'pa_p_l', 'pa_p_long_l', 'b1_p_r', 'b2_p_r', 'b3_p_r', 'bb_p_r', 'fo_p_r', 'go_p_r', 'hbp_p_r', 'hr_p_r', 'lo_p_r', 'po_p_r', 'so_p_r', 'estimated_woba_using_speedangle_p_r', 'to_left_p_r', 'to_middle_p_r', 'to_right_p_r', 'hard_hit_p_r', 'barrel_p_r', 'iso_p_r', 'slg_p_r', 'obp_p_r', 'woba_p_r', 'maxSpeed_p_r', 'maxSpin_p_r', 'b1_p_long_r', 'b2_p_long_r', 'b3_p_long_r', 'bb_p_long_r', 'fo_p_long_r', 'go_p_long_r', 'hbp_p_long_r', 'hr_p_long_r', 'lo_p_long_r', 'po_p_long_r', 'so_p_long_r', 'estimated_woba_using_speedangle_p_long_r', 'to_left_p_long_r', 'to_middle_p_long_r', 'to_right_p_long_r', 'hard_hit_p_long_r', 'barrel_p_long_r', 'iso_p_long_r', 'slg_p_long_r', 'obp_p_long_r', 'woba_p_long_r', 'maxSpeed_p_long_r', 'maxSpin_p_long_r', 'imp_p_r', 'pa_p_r', 'pa_p_long_r', 'date_steamer', 'steamerid', 'H9', 'HR9', 'K9', 'BB9', 'GBrate', 'FBrate', 'LDrate', 'SIERA', 'reliability', 'IP_start', 'IP', 'relief_IP']
pitcher_columns = ['id', 'fullName', 'firstName', 'lastName', 'position', 'batSide', 'pitchHand', 'date', 'teamId', 'status', 'order', 'Leverage', 'venue_id', 'batting_order', 'date_time', 'b1_p_l', 'b2_p_l', 'b3_p_l', 'bb_p_l', 'fo_p_l', 'go_p_l', 'hbp_p_l', 'hr_p_l', 'lo_p_l', 'po_p_l', 'so_p_l', 'iso_p_l', 'slg_p_l', 'obp_p_l', 'woba_p_l', 'estimated_woba_using_speedangle_p_l', 'to_left_p_l', 'to_middle_p_l', 'to_right_p_l', 'hard_hit_p_l', 'barrel_p_l', 'b1_p_long_l', 'b2_p_long_l', 'b3_p_long_l', 'bb_p_long_l', 'fo_p_long_l', 'go_p_long_l', 'hbp_p_long_l', 'hr_p_long_l', 'lo_p_long_l', 'po_p_long_l', 'so_p_long_l', 'iso_p_long_l', 'slg_p_long_l', 'obp_p_long_l', 'woba_p_long_l', 'estimated_woba_using_speedangle_p_long_l', 'to_left_p_long_l', 'to_middle_p_long_l', 'to_right_p_long_l', 'hard_hit_p_long_l', 'barrel_p_long_l', 'imp_p_l', 'pa_p_l', 'b1_p_r', 'b2_p_r', 'b3_p_r', 'bb_p_r', 'fo_p_r', 'go_p_r', 'hbp_p_r', 'hr_p_r', 'lo_p_r', 'po_p_r', 'so_p_r', 'iso_p_r', 'slg_p_r', 'obp_p_r', 'woba_p_r', 'estimated_woba_using_speedangle_p_r', 'to_left_p_r', 'to_middle_p_r', 'to_right_p_r', 'hard_hit_p_r', 'barrel_p_r', 'b1_p_long_r', 'b2_p_long_r', 'b3_p_long_r', 'bb_p_long_r', 'fo_p_long_r', 'go_p_long_r', 'hbp_p_long_r', 'hr_p_long_r', 'lo_p_long_r', 'po_p_long_r', 'so_p_long_r', 'iso_p_long_r', 'slg_p_long_r', 'obp_p_long_r', 'woba_p_long_r', 'estimated_woba_using_speedangle_p_long_r', 'to_left_p_long_r', 'to_middle_p_long_r', 'to_right_p_long_r', 'hard_hit_p_long_r', 'barrel_p_long_r', 'imp_p_r', 'pa_p_r', 'firstname', 'lastname', 'mlbamid', 'steamerid', 'H9', 'HR9', 'K9', 'BB9', 'GBrate', 'FBrate', 'LDrate', 'SIERA', 'reliability', 'IP_start', 'IP', 'relief_IP']

# ### Batters

# In[34]:


class Batter:
    def __init__(self, **kwargs):
        for column in batter_columns + ['confirmed']:
            setattr(self, column, kwargs.get(column, None))

        # DK stats    
        self.HBP = 0
        self.BB = 0
        self.B1 = 0
        self.B2 = 0
        self.B3 = 0
        self.HR = 0
        self.SB = 0
        self.R = 0
        self.RBI = 0
        self.FP = 0

        # Other
        self.PA = 0

        # Pitcher that allowed batter to reach
        # Will be none for anyone reaching on error or that would otherwise be unearned
        self.pitcher = None
        # Unearned runs scored
        # When a runner reaches on an error, we don't want to charge the pitcher with their ER, so we just assign it to the batter (where it won't matter)
        self.ER = 0
        # Whether the run is charged to the pitcher or not
        self.charged = 1

    def keep_selected_attributes(self):
        # List of attributes to keep
        keep_attributes = ['PA', 'HBP', 'BB', 'B1', 'B2', 'B3', 'HR', 'SB', 'R', 'RBI', 'FP', 'fullName', 'id', 'imp_b_l', 'imp_b_r', 'batting_order', 'confirmed']

        # Remove attributes not in the keep list
        for attr in list(self.__dict__.keys()):
            if attr not in keep_attributes or attr == '__class__':
                self.__dict__.pop(attr, None)


# In[ ]:





# ### Pitchers

# In[2]:


class Pitcher:
    def __init__(self, **kwargs):
        for column in pitcher_columns + ['confirmed']:
            setattr(self, column, kwargs.get(column, None))

        # DK stats
        self.winning = False
        self.OUT = 0
        self.SO = 0
        self.HBP = 0
        self.BB = 0
        self.B1 = 0
        self.B2 = 0
        self.B3 = 0
        self.HR = 0
        self.H = 0
        self.CS = 0
        self.R = 0
        self.ER = 0
        self.W = 0
        self.CG = 0
        self.CGSO = 0
        self.NH = 0
        self.FP = 0
        self.PA = 0

        self.PO = 0
        self.GO = 0
        self.LO = 0
        self.FO = 0

        self.faced = 0
        self.reached = 0
        self.TB = 0

        self.SO_inning = 0
        self.HBP_inning = 0
        self.HBP_inning = 0
        self.BB_inning = 0
        self.B1_inning = 0
        self.B2_inning = 0
        self.B3_inning = 0
        self.HR_inning = 0
        self.H_inning = 0

        self.PO_inning = 0
        self.GO_inning = 0
        self.LO_inning = 0
        self.FO_inning = 0

        self.ER_inning = 0
        self.faced_inning = 0
        self.reached_inning = 0
        self.TB_inning = 0
        self.OUT_inning = 0 

        self.last_PA = None

        self.imp_p_either = max(self.imp_p_l, self.imp_p_r)
        self.starter = 0

    def keep_selected_attributes(self):
        # List of attributes to keep
        keep_attributes = ['PA', 'OUT', 'SO', 'HBP', 'BB', 'B1', 'B2', 'B3', 'HR', 'H', 'R', 'ER', 'W', 'CG', 'CGSO', 'NH', 'FP', 'fullName', 'id', 'imp_p_l', 'imp_p_r', 'leverage', 'confirmed']

        # Remove attributes not in the keep list
        for attr in list(self.__dict__.keys()):
            if attr not in keep_attributes or attr == '__class__':
                self.__dict__.pop(attr, None)


# In[ ]:





# ### Games

# In[1]:


class Scoreboard:
    def __init__(self, away_batters, home_batters, away_pitchers, home_pitchers, innings):
        # Player objects
        self.away_batters = away_batters
        self.home_batters = home_batters
        self.away_pitchers = away_pitchers
        self.home_pitchers = home_pitchers

        # Score
        self.away_score = 0
        self.home_score = 0
        self.winning_team = "Tie"

        # Inning state
        self.innings = innings
        self.inning = 1
        self.top_bot = "Top"
        self.outs = 0
        self.faced_inning = 0 # deprecated
        self.br_inning = 0 # deprecated
        self.error_extended = False

        # Current player vs player matchup
        self.ab = None
        self.pitching = None

        # Base states
        # Player
        self.on_1b = None
        self.on_2b = None
        self.on_3b = None
        # Binary
        self.onFirst = 0
        self.onSecond = 0
        self.onThird = 0

        # Batter order
        self.away_order = 1
        self.home_order = 1

        # Pitcher leverage
        self.away_leverage = 1
        self.home_leverage = 1
        # Pitchers currently up
        self.away_pitcher_up = None
        self.home_pitcher_up = None
        # Starters have been pulled
        self.away_starter_pulled = False
        self.home_starter_pulled = False
        # Starters
        self.away_starter = None
        self.home_starter = None
        # Pitcher currently in line for win
        self.winning_pitcher = None
        # Zombies
        self.away_zombie = None
        self.home_zombie = None


        # Create venue binaries
        for venue in venue_inputs:
            setattr(self, f'{venue}', 0)

    def keep_selected_attributes(self):
        # List of attributes to keep
        keep_attributes = ['away_batters', 'home_batters', 'away_pitchers', 'home_pitchers', 'away_score', 'home_score', 'innings']

        # Remove attributes not in the keep list
        for attr in list(self.__dict__.keys()):
            if attr not in keep_attributes or attr == '__class__':
                self.__dict__.pop(attr, None)


# In[ ]:





# ### Parks

# In[ ]:


class Park:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f"Park({', '.join(f'{k}={v}' for k, v in vars(self).items())})"

# %%
__all__ = [name for name in globals() if not name.startswith("_")]