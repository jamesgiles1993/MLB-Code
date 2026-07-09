# U02. Functions
# This imports commonly-used functions and maps
# Type: Utility
# Run Frequency: Frequent
# Created: 11/1/2023
# Updated: 8/20/2025

### Imports
from U01Imports_Sim import *



### Remove Accents
def remove_accents(old):
    new = re.sub(r'[àáâãäå]', 'a', old)
    new = re.sub(r'[èéêë]', 'e', new)
    new = re.sub(r'[ìíîï]', 'i', new)
    new = re.sub(r'[òóôõö]', 'o', new)
    new = re.sub(r'[ùúûü]', 'u', new)
    new = re.sub(r'[ñ]', 'n', new)
    return new
    

### Pause Code
def pause_code(start_time='2023-08-09T07:24:30', timezone='EST'):
    est_timezone = pytz.timezone('America/New_York')  # Eastern Standard Time (EST)
    
    # Convert start_time to datetime object in EST timezone
    naive_datetime = datetime.datetime.fromisoformat(start_time)
    est_start_time = est_timezone.localize(naive_datetime)

    # Convert EST time to UTC
    utc_start_time = est_start_time.astimezone(pytz.utc)

    time_difference = utc_start_time - datetime.datetime.now(pytz.utc)
    total_seconds = time_difference.total_seconds()
    
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    est_time_str = est_start_time.strftime("%I:%M%p")
    time_until_str = f"{est_time_str}. {hours} hours, {minutes} minutes, and {seconds} seconds."
    
    print("Time until", time_until_str)

    # Loop with a small sleep interval, checking for interruption
    try:
        while total_seconds > 0:
            time.sleep(1)  # Sleep for 1 second
            total_seconds -= 1
    except KeyboardInterrupt:
        print("Program interrupted by user.")
        return


    ### Set date (may be different in morning)
    # Today's Date
    # YYYY-MM-DD (datetime)
    todaysdate_dt = datetime.date.today()
    
    # YYYY-MM-DD (string)
    todaysdate_dash = str(todaysdate_dt)
    
    # MM/DD/YYYY
    todaysdate_slash = todaysdate_dash.split("-")
    todaysdate_slash = todaysdate_slash[1] + "/" + todaysdate_slash[2] + "/" + todaysdate_slash[0]
    
    # YYYYMMDD
    todaysdate = todaysdate_dash.replace("-", "")
    
    ## MM-DD-YYYY
    todaysdate_dash = todaysdate[:4] + "-" + todaysdate[4:6] + "-" + todaysdate[6:]


    # Get the current date
    current_date = datetime.datetime.now()
    
    # Subtract one day from the current date to get yesterday's date
    yesterday_dt = current_date - datetime.timedelta(days=1)
    
    # Format yesterday's date as "YYYYMMDD"
    yesterdaysdate = yesterday_dt.strftime("%Y%m%d")
    
    # MM/DD/YYYY
    yesterdaysdate_slash = yesterdaysdate[4:6] + "/" + yesterdaysdate[6:8] + "/" + yesterdaysdate[0:4] 
    
    ## MM-DD-YYYY
    yesterdaysdate_dash = yesterdaysdate[:4] + "-" + yesterdaysdate[4:6] + "-" + yesterdaysdate[6:]


### Identify Pareto-Optimal Observations
def pareto_optimal(df, objectives, directions):
    data = df[objectives].values
    num_points = data.shape[0]

    # Convert objectives based on direction
    for i, direction in enumerate(directions):
        if direction == "Maximize":
            data[:, i] *= -1

    # Pareto front mask
    pareto_mask = np.ones(num_points, dtype=bool)

    # Check for dominance
    for i in range(num_points):
        for j in range(num_points):
            if i != j:
                # Row j dominates row i if it's better in at least one objective and not worse in others
                if np.all(data[j] <= data[i]) and np.any(data[j] < data[i]):
                    pareto_mask[i] = False
                    break

    # Return the Pareto-optimal rows
    return df[pareto_mask].drop_duplicates()



### Create Game DataFrame
# def create_games(start_date, end_date, team_dict):
#     """
#     Fetch game schedules for a given date range.
    
#     Parameters:
#     - start_date (str): Start date in "YYYYMMDD" format.
#     - end_date (str): End date in "YYYYMMDD" format.
    
#     Returns:
#     - Data Frame: Combined schedule for the specified date range.
#     """
    
#     # Reformat dates
#     start_date = start_date[4:6] + "/" + start_date[6:8] + "/" + start_date[:4] 
#     end_date = end_date[4:6] + "/" + end_date[6:8] + "/" + end_date[:4] 

#     # Extract year    
#     start_year = int(start_date.split("/")[-1])
#     end_year = int(end_date.split("/")[-1])
    
#     # Initialize an empty list to hold game schedules
#     games = []
    
#     # Iterate through each year in the range and fetch schedules
#     for year in range(start_year, end_year + 1):
#         # Determine the bounds for statsapi.schedule
#         year_start = start_date if year == start_year else f"01/01/{year}"
#         year_end = end_date if year == end_year else f"12/31/{year}"
        
#         # Fetch and append the schedules
#         games.extend(statsapi.schedule(start_date=year_start, end_date=year_end))
    
#     # Create dataframe
#     game_df = pd.DataFrame(games)
#     # Create date variable
#     game_df['date'] = game_df['game_date'].str.replace("-","")
#     # Create year variable
#     game_df['year'] = game_df['game_date'].str[0:4]
#     # Select subsample of games to run (exclude spring training, all-star games, exhibitions, and cancelled games
#     game_df = game_df.query('game_type != "S" and game_type != "A" and game_type != "E" and status != "Cancelled" and status != "Postponed"').reset_index(drop=True)

#     # Map in team names
#     game_df['away_team'] = game_df['away_name'].map(team_dict)
#     game_df['home_team'] = game_df['home_name'].map(team_dict)

#     # Convert to numeric
#     game_df['away_score'] = game_df['away_score'].astype('int')
#     game_df['home_score'] = game_df['home_score'].astype('int')
    
#     # Drop duplicates
#     game_df.drop_duplicates('game_id', inplace=True, keep='last')
#     game_df.reset_index(inplace=True, drop=True)
    
#     # Drop unnecessary columns
#     game_df.drop(columns=['home_pitcher_note', 'away_pitcher_note', 'national_broadcasts', 'series_status', 'summary'], inplace=True)
    
    
#     return game_df


def create_games(team_dict, baseball_path, venue_map_df, refresh_start_date=None, refresh_end_date=None):
    """
    Build full game dataframe.
    Optionally refresh a date range from API, then return entire dataset.
    """

    def _fetch_games(start_date, end_date):
        start_fmt = f"{start_date[4:6]}/{start_date[6:8]}/{start_date[:4]}"
        end_fmt   = f"{end_date[4:6]}/{end_date[6:8]}/{end_date[:4]}"

        start_year = int(start_date[:4])
        end_year   = int(end_date[:4])

        games = []
        for year in range(start_year, end_year + 1):
            year_start = start_fmt if year == start_year else f"01/01/{year}"
            year_end   = end_fmt   if year == end_year   else f"12/31/{year}"
            games.extend(statsapi.schedule(start_date=year_start, end_date=year_end))

        df = pd.DataFrame(games)

        df['date'] = df['game_date'].str.replace("-", "")
        df['year'] = df['game_date'].str[:4]

        df = df.query(
            'game_type not in ["S","A","E"] and '
            'status not in ["Cancelled","Postponed"]'
        ).copy()

        df['away_team'] = df['away_name'].map(team_dict)
        df['home_team'] = df['home_name'].map(team_dict)

        df['away_score'] = df['away_score'].astype(int)
        df['home_score'] = df['home_score'].astype(int)

        df = df.drop_duplicates('game_id', keep='last').reset_index(drop=True)

        df = df.drop(columns=[
            'home_pitcher_note', 'away_pitcher_note',
            'national_broadcasts', 'series_status', 'summary'
        ], errors='ignore')

        return df

    file_path = os.path.join(baseball_path, "game_df.csv")

    if os.path.exists(file_path):
        all_df = pd.read_csv(file_path)
    else:
        all_df = pd.DataFrame()

    # -------------------------
    # OPTIONAL REFRESH
    # -------------------------
    if refresh_start_date and refresh_end_date:
        refresh_df = _fetch_games(refresh_start_date, refresh_end_date)

        if not all_df.empty:
            all_df = all_df[
                ~all_df['date'].astype(str).isin(refresh_df['date'].astype(str))
            ]

        all_df = pd.concat([all_df, refresh_df], ignore_index=True)
        all_df.to_csv(file_path, index=False)

    # -------------------------
    # MERGE VENUE DATA
    # -------------------------
    all_df = all_df.merge(
        venue_map_df[[
            'id',
            'location.defaultCoordinates.latitude',
            'location.defaultCoordinates.longitude',
            'fieldInfo.leftLine', 'fieldInfo.center',
            'fieldInfo.rightLine', 'fieldInfo.leftCenter',
            'fieldInfo.rightCenter',
            'location.elevation', 'location.azimuthAngle',
            'fieldInfo.roofType', 'active'
        ]],
        left_on='venue_id',
        right_on='id',
        how='left'
    )

    # Convert to datetime
    all_df["game_datetime"] = pd.to_datetime(all_df["game_datetime"])


    return all_df


### Create Contest Guide DataFrame
def create_contests(start_date=None, end_date=None, name=None, entryFee=None, exclusions=['vs', 'Turbo', '@']):
    # Get all file paths
    all_files = glob.glob(os.path.join(baseball_path, "B03. Contest Guides", "*.csv"))

    # Parallel read
    df_list = Parallel(n_jobs=-1)(delayed(pd.read_csv)(file, dtype='str') for file in all_files)

    # Concatenate
    contest_df = pd.concat(df_list, ignore_index=True)

    # Convert data types
    contest_df['game_id'] = contest_df['game_id'].astype(int)
    contest_df['date'] = pd.to_datetime(contest_df['date'].astype(str), format='%Y%m%d')

    # Apply filters
    if start_date is not None:
        contest_df = contest_df[contest_df['date'] >= pd.to_datetime(start_date, format='%Y%m%d')]
    if end_date is not None:
        contest_df = contest_df[contest_df['date'] <= pd.to_datetime(end_date, format='%Y%m%d')]
    if name is not None:
        contest_df = contest_df[contest_df['name'].str.contains(name)]
    if entryFee is not None:
        contest_df = contest_df[contest_df['entryFee'].astype(float) == entryFee]
    if exclusions != []:
        for exclusion in exclusions:
            contest_df = contest_df[~contest_df['name'].str.contains(exclusion)]

    # Convert date back to string
    contest_df['date'] = contest_df['date'].dt.strftime('%Y%m%d')

    # Convert contestKey to numeric
    contest_df['contestKey'] = contest_df['contestKey'].astype(int)


    # Calculate slate_size 
    contest_df['slate_size'] = contest_df.groupby('contestKey')['contestKey'].transform('count')

    
    return contest_df


### MLPClassifier with string outcome support (compatible with recent sklearn versions)
class SafeMLPClassifier(MLPClassifier):
    def _score(self, X, y):
        """Override sklearn's _score to avoid np.isnan on string predictions."""
        y_pred = self._predict(X, check_input=False)
        # If predictions are numeric, check for NaN/inf normally
        if np.issubdtype(np.array(y_pred).dtype, np.number):
            if np.isnan(y_pred).any() or np.isinf(y_pred).any():
                return np.nan
        # Otherwise just compute accuracy directly
        return (y_pred == y).mean()

    def _score_with_function(self, X, y, score_function):
        """Same fix for newer sklearn versions using _score_with_function."""
        y_pred = self._predict(X, check_input=False)
        # Handle numeric vs string safely
        if np.issubdtype(np.array(y_pred).dtype, np.number):
            if np.isnan(y_pred).any() or np.isinf(y_pred).any():
                return np.nan
        return score_function(y, y_pred)


### Log Print Statements
def log_print(text, sep, end, file, flush, write=False):
    if write == True:
        with open(os.path.join(baseball_path, f"{todaysdate} Sim Log.txt"), "w") as f:
            print(text, file=f)


### Median Scaler
from sklearn.base import BaseEstimator, TransformerMixin

class MedianCenterer(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        # store column-wise medians
        self.medians_ = np.median(X, axis=0)
        return self
    
    def transform(self, X):
        return X - self.medians_
    
    def inverse_transform(self, X):
        return X + self.medians_


### PyTorch MLP
class MLP(nn.Module):
    def __init__(self, input_size, hidden_layers, output_size):
        super().__init__()
        layers = []
        prev_size = input_size
        for h in hidden_layers:
            layers.append(nn.Linear(prev_size, h))
            layers.append(nn.ReLU())
            prev_size = h
        layers.append(nn.Linear(prev_size, output_size))
        self.net = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.net(x)


### NumpyPrediction with sklearn wrapper
class NumpyPredict:
    def __init__(self, ensemble_numpy, input_columns, classes, metadata=None):
        """
        ensemble_numpy: list of models, each a list of [W1, b1, W2, b2, ..., Wn, bn]
        input_columns: list of feature names used during training (order matters!)
        classes: list of class labels (same order as in training)
        metadata: optional dict with additional info (hidden_layers, num_classifiers, etc.)
        """
        self.ensemble = ensemble_numpy
        self.input_columns = input_columns
        self.classes_ = classes
        self.metadata = metadata or {}

    @staticmethod
    def _softmax(x):
        e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
        return e_x / e_x.sum(axis=1, keepdims=True)

    @staticmethod
    def _forward(model_layers, x):
        """
        Forward pass for a single model.
        model_layers: [W1, b1, W2, b2, ..., Wn, bn]
        x: numpy array of shape [n_samples, n_features]
        """
        n_layers = len(model_layers) // 2
        h = x
        for i in range(n_layers - 1):
            W = model_layers[2*i]
            b = model_layers[2*i + 1]
            h = np.maximum(0, h @ W + b)  # ReLU
        # final layer
        W = model_layers[-2]
        b = model_layers[-1]
        logits = h @ W + b
        return NumpyPredict._softmax(logits)

    def predict_proba(self, X):
        """
        X: pandas DataFrame, Series, or NumPy array
        Returns: numpy array [n_samples, n_classes] with probabilities
        """
        # Convert DataFrame or Series to NumPy array
        if isinstance(X, pd.DataFrame):
            # Reorder columns to match training
            x_np = X[self.input_columns].to_numpy(dtype=np.float32)
        elif isinstance(X, pd.Series):
            # Single row
            x_np = X[self.input_columns].to_numpy(dtype=np.float32).reshape(1, -1)
        else:
            x_np = np.array(X, dtype=np.float32)
            if x_np.ndim == 1:
                x_np = x_np.reshape(1, -1)

        # Check input size
        expected_size = self.ensemble[0][0].shape[0]
        if x_np.shape[1] != expected_size:
            raise ValueError(
                f"Input feature size ({x_np.shape[1]}) does not match model first layer ({expected_size})"
            )

        # Run all models in ensemble
        probs_list = [self._forward(model, x_np) for model in self.ensemble]

        # Average probabilities
        avg_probs = np.mean(probs_list, axis=0)
        return avg_probs

    def predict(self, X):
        """
        Returns predicted class labels (argmax), like sklearn's predict()
        """
        probs = self.predict_proba(X)
        return np.array([self.classes_[i] for i in np.argmax(probs, axis=1)])


__all__ = [name for name in globals() if not name.startswith("_")]