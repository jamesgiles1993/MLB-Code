# %% [markdown]
# # U01. Imports
# - This imports Python packages, display settings, and some common variable and stat lists
# - Type: Utility
# - Run Frequency: Frequent
# - Created: 11/1/2023
# - Updated: 8/20/2025

# %% [markdown]
# ### Packages

# %%
# import sys
# !{sys.executable} -m pip install \
# tensorflow \
# keras \
# opencv-python \
# ipywidgets \
# joblib \
# openmeteo-requests \
# polars \
# plotly \
# pyautogui \
# pyperclip \
# pytz \
# requests \
# requests-cache \
# selenium \
# unidecode \
# xlrd \
# beautifulsoup4 \
# lxml \
# MLB-StatsAPI \
# openpyxl \
# paretoset \
# pulp \
# pybaseball \
# pydfs-lineup-optimizer \
# retry-requests \
# thefuzz \
# tqdm \
# webdriver-manager \
# python-dateutil \
# seaborn \
# scikit-learn \
# sqlalchemy \
# scipy \
# statsmodels \
# sklearn


# %%
import ast
import concurrent.futures
import csv
import cv2
import datetime
import dateutil.parser
import distutils.dir_util
import gc
import glob
import IPython.display
import ipywidgets as widgets
import joblib
import json
import keras
import math
import matplotlib.pyplot as plt
import numpy as np
import openmeteo_requests
import os
import pandas as pd
import pathlib
import pickle
import polars as pl
import plotly.express as px
import pyautogui
import pyperclip
import pytz
import re
import requests
import requests_cache
import seaborn as sns
import selenium
import shutil
import smtplib
import ssl
import sqlite3
import statsapi
import statsmodels.formula.api as smf
import statsmodels.api as sm
import subprocess
import sys
import tensorflow as tf
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import traceback
import unidecode
import warnings
import webbrowser
import xlrd
import random
import urllib
import zipfile
import __main__

from bs4 import BeautifulSoup
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dateutil import parser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from functools import partial
from io import StringIO
from IPython.display import display, Javascript, clear_output
from joblib import Parallel, delayed
from lxml import html
from openpyxl import load_workbook
from paretoset import paretoset
from pathlib import Path
from pulp import GLPK_CMD  
from pybaseball import statcast
from pydfs_lineup_optimizer import get_optimizer, Site, Sport, Player, TeamStack, PlayerFilter, RandomFantasyPointsStrategy, ProgressiveFantasyPointsStrategy, AfterEachExposureStrategy, LineupOptimizer
# from pydfs_lineup_optimizer.solvers.mip_solver import MIPSolver
from pydfs_lineup_optimizer.solvers import PuLPSolver
from retry_requests import retry
from scipy import stats
from scipy.stats import ttest_ind, mannwhitneyu, ttest_1samp
from scipy.stats.mstats import winsorize
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from sklearn.ensemble import VotingClassifier
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, OneHotEncoder, LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.svm import SVC
from statsapi import get
from sqlalchemy import create_engine
from tensorflow.keras.losses import KLDivergence
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, BatchNormalization, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
from thefuzz import process
from tqdm import tqdm
from urllib.request import urlopen, Request
from webdriver_manager.chrome import ChromeDriverManager

# %%


# %% [markdown]
# ### Display Options

# %%
warnings.simplefilter(action="ignore")

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)
pd.set_option('display.float_format', '{:.6f}'.format)

# %%


# %% [markdown]
# ### Paths

# %%
model_path = r"C:\Users\James\Documents\MLB\Models"
baseball_path = r"C:\Users\James\Documents\MLB\Data"
download_path = r"C:\Users\James\Downloads"

# %%


# %% [markdown]
# ### Dates

# %% [markdown]
# ##### Today

# %%
todaysdate_dt = datetime.date.today()

todaysdate = todaysdate_dt.strftime("%Y%m%d")
todaysdate_dash = todaysdate_dt.strftime("%Y-%m-%d")
todaysdate_slash = todaysdate_dt.strftime("%m/%d/%Y")

# %% [markdown]
# ##### Yesterday

# %%
yesterdaysdate_dt = datetime.datetime.now() - datetime.timedelta(days=1)

yesterdaysdate = yesterdaysdate_dt.strftime("%Y%m%d")
yesterdaysdate_dash = yesterdaysdate_dt.strftime("%Y-%m-%d")
yesterdaysdate_slash = yesterdaysdate_dt.strftime("%m/%d/%Y")

# %%


# %% [markdown]
# ### Venue Lists

# %% [markdown]
# Maintained Venues

# %%
venue_nums = ['1', '2', '3', '4', '5', '7', '10', '12', '13', '14', '15', '16', '17', '19', '22', '31', '32', 
              '680', '2392', '2394', '2395', '2535', '2536', '2602', '2680', '2681', '2701', '2735', '2756', 
              '2889', '3289', '3309', '3312', '3313', '4169', '4705', '5010', '5325', '5365', '5381', '5445']

# %% [markdown]
# Dummies

# %%
venue_inputs = [f"venue_{num}" for num in venue_nums]

# %%


# %% [markdown]
# ### Stat Lists

# %% [markdown]
# Events

# %%
events_list = ['b1', 'b2', 'b3', 'bb', 'fo', 'go', 'hbp', 'hr', 'lo', 'po', 'so']

# %% [markdown]
# MLB API-Derived Stats

# %%
calc_list = ['iso', 'slg', 'obp', 'woba']

# %% [markdown]
# Statcast List

# %%
statcast_list = ['estimated_woba_using_speedangle', 'to_left', 'to_middle', 'to_right', 'hard_hit', 'barrel']

# %% [markdown]
# Short-Period Stats

# %%
batter_stats_short = ([f"{stat}_b" for stat in events_list] + 
                    [f"{stat}_b" for stat in calc_list] + 
                    [f"{stat}_b" for stat in statcast_list])

# %%
pitcher_stats_short = ([f"{stat}_p" for stat in events_list] + 
                    [f"{stat}_p" for stat in calc_list] + 
                    [f"{stat}_p" for stat in statcast_list])

# %% [markdown]
# Long-Period Stats

# %%
batter_stats_long = ([f"{stat}_b_long" for stat in events_list] + 
                    [f"{stat}_b_long" for stat in calc_list] + 
                    [f"{stat}_b_long" for stat in statcast_list])

# %%
pitcher_stats_long = ([f"{stat}_p_long" for stat in events_list] + 
                    [f"{stat}_p_long" for stat in calc_list] + 
                    [f"{stat}_p_long" for stat in statcast_list])

# %% [markdown]
# Batter Stats

# %%
batter_inputs = batter_stats_short + batter_stats_long

batter_stats_l = [f'{stat}_l' for stat in batter_inputs]
batter_stats_r = [f'{stat}_r' for stat in batter_inputs]

# %% [markdown]
# Pitcher Stats

# %%
pitcher_inputs = pitcher_stats_short + pitcher_stats_long

pitcher_stats_l = [f'{stat}_l' for stat in pitcher_inputs]
pitcher_stats_r = [f'{stat}_r' for stat in pitcher_inputs]

# %% [markdown]
# Steamer Batter Stats

# %%
batter_stats_fg = ['b1_rate', 'b2_rate', 'b3_rate', 'hr_rate', 'bb_rate', 'hbp_rate', 'so_rate', 'woba', 'slg', 'obp']

# %% [markdown]
# Steamer Pitcher Stats

# %%
pitcher_stats_fg = ['H9', 'HR9', 'K9', 'BB9', 'GBrate', 'FBrate', 'LDrate', 'SIERA']

# %%
__all__ = [name for name in globals() if not name.startswith("_")]