# %% [markdown]
# # U02. Functions
# - This imports commonly-used functions and maps
# - Type: Utility
# - Run Frequency: Frequent
# - Created: 11/1/2023
# - Updated: 8/20/2025


# %%
from U01Imports import *

# %% [markdown]
# ##### Remove Accents

# %%
def remove_accents(old):
    new = re.sub(r'[àáâãäå]', 'a', old)
    new = re.sub(r'[èéêë]', 'e', new)
    new = re.sub(r'[ìíîï]', 'i', new)
    new = re.sub(r'[òóôõö]', 'o', new)
    new = re.sub(r'[ùúûü]', 'u', new)
    new = re.sub(r'[ñ]', 'n', new)
    return new

# %% [markdown]
# ##### Pause Code

# %%
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

# %% [markdown]
# ##### Identify Pareto-Optimal Observations

# %%
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

# %% [markdown]
# ##### Create Game DataFrame

# %%
def create_games(start_date, end_date, team_dict):
    """
    Fetch game schedules for a given date range.
    
    Parameters:
    - start_date (str): Start date in "YYYYMMDD" format.
    - end_date (str): End date in "YYYYMMDD" format.
    
    Returns:
    - Data Frame: Combined schedule for the specified date range.
    """
    
    # Reformat dates
    start_date = start_date[4:6] + "/" + start_date[6:8] + "/" + start_date[:4] 
    end_date = end_date[4:6] + "/" + end_date[6:8] + "/" + end_date[:4] 

    # Extract year    
    start_year = int(start_date.split("/")[-1])
    end_year = int(end_date.split("/")[-1])
    
    # Initialize an empty list to hold game schedules
    games = []
    
    # Iterate through each year in the range and fetch schedules
    for year in range(start_year, end_year + 1):
        # Determine the bounds for statsapi.schedule
        year_start = start_date if year == start_year else f"01/01/{year}"
        year_end = end_date if year == end_year else f"12/31/{year}"
        
        # Fetch and append the schedules
        games.extend(statsapi.schedule(start_date=year_start, end_date=year_end))
    
    # Create dataframe
    game_df = pd.DataFrame(games)
    # Create date variable
    game_df['date'] = game_df['game_date'].str.replace("-","")
    # Create year variable
    game_df['year'] = game_df['game_date'].str[0:4]
    # Select subsample of games to run (exclude spring training, all-star games, exhibitions, and cancelled games
    game_df = game_df.query('game_type != "S" and game_type != "A" and game_type != "E" and status != "Cancelled" and status != "Postponed"').reset_index(drop=True)

    # Map in team names
    game_df['away_team'] = game_df['away_name'].map(team_dict)
    game_df['home_team'] = game_df['home_name'].map(team_dict)

    # Convert to numeric
    game_df['away_score'] = game_df['away_score'].astype('int')
    game_df['home_score'] = game_df['home_score'].astype('int')
    
    # Drop duplicates
    game_df.drop_duplicates('game_id', inplace=True, keep='last')
    game_df.reset_index(inplace=True, drop=True)
    
    # Drop unnecessary columns
    game_df.drop(columns=['home_pitcher_note', 'away_pitcher_note', 'national_broadcasts', 'series_status', 'summary'], inplace=True)
    
    
    return game_df

# %% [markdown]
# ##### Create Contest Guide DataFrame

# %%
def create_contests(start_date=None, end_date=None, name=None, entryFee=None, exclusions=['vs', 'Turbo', '@']):
    # Get all file paths
    all_files = glob.glob(os.path.join(baseball_path, "B03. Contest Guides", "*.csv"))

    # Parallel read
    df_list = Parallel(n_jobs=-1)(
        delayed(pd.read_csv)(file, dtype='str') for file in all_files
    )

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
    if exclusions != []:
        for exclusion in exclusions:
            contest_df = contest_df[~contest_df['name'].str.contains(exclusion)]

    # Convert date back to string
    contest_df['date'] = contest_df['date'].dt.strftime('%Y%m%d')

    # Calculate slate_size 
    contest_df['slate_size'] = contest_df.groupby('contestKey')['contestKey'].transform('count')

    return contest_df


# %% [markdown]
# ##### MLP with Dropout

# %% [markdown]
# Source: https://datascience.stackexchange.com/questions/117082/how-can-i-implement-dropout-in-scikit-learn

# %%
# # Creating a custom MLPDropout classifier
# from sklearn.neural_network._stochastic_optimizers import AdamOptimizer
# from sklearn.neural_network._base import ACTIVATIONS, DERIVATIVES, LOSS_FUNCTIONS
# from sklearn.utils import shuffle, gen_batches, check_random_state, _safe_indexing
# from sklearn.utils.extmath import safe_sparse_dot
# from sklearn.exceptions import ConvergenceWarning
# from sklearn.base import is_classifier

# class MLPDropout(MLPClassifier):
    
#     def __init__(
#         self,
#         hidden_layer_sizes=(100,),
#         activation="relu",
#         *,
#         solver="adam",
#         alpha=0.0001,
#         batch_size="auto",
#         learning_rate="constant",
#         learning_rate_init=0.001,
#         power_t=0.5,
#         max_iter=200,
#         shuffle=True,
#         random_state=None,
#         tol=1e-4,
#         verbose=False,
#         warm_start=False,
#         momentum=0.9,
#         nesterovs_momentum=True,
#         early_stopping=False,
#         validation_fraction=0.1,
#         beta_1=0.9,
#         beta_2=0.999,
#         epsilon=1e-8,
#         n_iter_no_change=10,
#         max_fun=15000,
#         dropout = None,
#     ):
#         '''
#         Additional Parameters:
#         ----------
#         dropout : float in range (0, 1), default=None
#             Dropout parameter for the model, defines the percentage of nodes
#             to remove at each layer.
            
#         '''
#         self.dropout = dropout
#         super().__init__(
#             hidden_layer_sizes=hidden_layer_sizes,
#             activation=activation,
#             solver=solver,
#             alpha=alpha,
#             batch_size=batch_size,
#             learning_rate=learning_rate,
#             learning_rate_init=learning_rate_init,
#             power_t=power_t,
#             max_iter=max_iter,
#             shuffle=shuffle,
#             random_state=random_state,
#             tol=tol,
#             verbose=verbose,
#             warm_start=warm_start,
#             momentum=momentum,
#             nesterovs_momentum=nesterovs_momentum,
#             early_stopping=early_stopping,
#             validation_fraction=validation_fraction,
#             beta_1=beta_1,
#             beta_2=beta_2,
#             epsilon=epsilon,
#             n_iter_no_change=n_iter_no_change,
#             max_fun=max_fun,
#         )
    
#     def _fit_stochastic(
#         self,
#         X,
#         y,
#         activations,
#         deltas,
#         coef_grads,
#         intercept_grads,
#         layer_units,
#         incremental,
#     ):
#         params = self.coefs_ + self.intercepts_
#         if not incremental or not hasattr(self, "_optimizer"):
#             if self.solver == "sgd":
#                 self._optimizer = SGDOptimizer(
#                     params,
#                     self.learning_rate_init,
#                     self.learning_rate,
#                     self.momentum,
#                     self.nesterovs_momentum,
#                     self.power_t,
#                 )
#             elif self.solver == "adam":
#                 self._optimizer = AdamOptimizer(
#                     params,
#                     self.learning_rate_init,
#                     self.beta_1,
#                     self.beta_2,
#                     self.epsilon,
#                 )

#         # early_stopping in partial_fit doesn't make sense
#         early_stopping = self.early_stopping and not incremental
#         if early_stopping:
#             # don't stratify in multilabel classification
#             should_stratify = is_classifier(self) and self.n_outputs_ == 1
#             stratify = y if should_stratify else None
#             X, X_val, y, y_val = train_test_split(
#                 X,
#                 y,
#                 random_state=self._random_state,
#                 test_size=self.validation_fraction,
#                 stratify=stratify,
#             )
#             if is_classifier(self):
#                 y_val = self._label_binarizer.inverse_transform(y_val)
#         else:
#             X_val = None
#             y_val = None

#         n_samples = X.shape[0]
#         sample_idx = np.arange(n_samples, dtype=int)

#         if self.batch_size == "auto":
#             batch_size = min(200, n_samples)
#         else:
#             if self.batch_size < 1 or self.batch_size > n_samples:
#                 warnings.warn(
#                     "Got `batch_size` less than 1 or larger than "
#                     "sample size. It is going to be clipped"
#                 )
#             batch_size = np.clip(self.batch_size, 1, n_samples)

#         try:
#             for it in range(self.max_iter):
#                 if self.shuffle:
#                     # Only shuffle the sample indices instead of X and y to
#                     # reduce the memory footprint. These indices will be used
#                     # to slice the X and y.
#                     sample_idx = shuffle(sample_idx, random_state=self._random_state)

#                 accumulated_loss = 0.0
#                 for batch_slice in gen_batches(n_samples, batch_size):
#                     if self.shuffle:
#                         X_batch = _safe_indexing(X, sample_idx[batch_slice])
#                         y_batch = y[sample_idx[batch_slice]]
#                     else:
#                         X_batch = X[batch_slice]
#                         y_batch = y[batch_slice]
                    
#                     activations[0] = X_batch
#                     # (DROPOUT ADDITION) layer_units passed forward to help build dropout mask.
#                     batch_loss, coef_grads, intercept_grads = self._backprop(
#                         X_batch,
#                         y_batch,
#                         activations,
#                         layer_units,
#                         deltas,
#                         coef_grads,
#                         intercept_grads,
#                     )
#                     accumulated_loss += batch_loss * (
#                         batch_slice.stop - batch_slice.start
#                     )

#                     # update weights
#                     grads = coef_grads + intercept_grads
#                     self._optimizer.update_params(params, grads)

#                 self.n_iter_ += 1
#                 self.loss_ = accumulated_loss / X.shape[0]

#                 self.t_ += n_samples
#                 self.loss_curve_.append(self.loss_)
#                 if self.verbose:
#                     print("Iteration %d, loss = %.8f" % (self.n_iter_, self.loss_))

#                 # update no_improvement_count based on training loss or
#                 # validation score according to early_stopping
#                 self._update_no_improvement_count(early_stopping, X_val, y_val)

#                 # for learning rate that needs to be updated at iteration end
#                 self._optimizer.iteration_ends(self.t_)

#                 if self._no_improvement_count > self.n_iter_no_change:
#                     # not better than last `n_iter_no_change` iterations by tol
#                     # stop or decrease learning rate
#                     if early_stopping:
#                         msg = (
#                             "Validation score did not improve more than "
#                             "tol=%f for %d consecutive epochs."
#                             % (self.tol, self.n_iter_no_change)
#                         )
#                     else:
#                         msg = (
#                             "Training loss did not improve more than tol=%f"
#                             " for %d consecutive epochs."
#                             % (self.tol, self.n_iter_no_change)
#                         )

#                     is_stopping = self._optimizer.trigger_stopping(msg, self.verbose)
#                     if is_stopping:
#                         break
#                     else:
#                         self._no_improvement_count = 0

#                 if incremental:
#                     break

#                 if self.n_iter_ == self.max_iter:
#                     warnings.warn(
#                         "Stochastic Optimizer: Maximum iterations (%d) "
#                         "reached and the optimization hasn't converged yet."
#                         % self.max_iter,
#                         ConvergenceWarning,
#                     )
#         except KeyboardInterrupt:
#             warnings.warn("Training interrupted by user.")

#         if early_stopping:
#             # restore best weights
#             self.coefs_ = self._best_coefs
#             self.intercepts_ = self._best_intercepts
    
#     def _backprop(self, X, y, activations, layer_units, deltas, coef_grads, intercept_grads):
#         """Compute the MLP loss function and its corresponding derivatives
#         with respect to each parameter: weights and bias vectors.

#         Parameters
#         ----------
#         X : {array-like, sparse matrix} of shape (n_samples, n_features)
#             The input data.

#         y : ndarray of shape (n_samples,)
#             The target values.

#         activations : list, length = n_layers - 1
#             The ith element of the list holds the values of the ith layer.
             
#         layer_units (DROPOUT ADDITION) : list, length = n_layers
#             The layer units of the neural net, this is the shape of the
#             Neural Net model. This is used to build the dropout mask.

#         deltas : list, length = n_layers - 1
#             The ith element of the list holds the difference between the
#             activations of the i + 1 layer and the backpropagated error.
#             More specifically, deltas are gradients of loss with respect to z
#             in each layer, where z = wx + b is the value of a particular layer
#             before passing through the activation function

#         coef_grads : list, length = n_layers - 1
#             The ith element contains the amount of change used to update the
#             coefficient parameters of the ith layer in an iteration.

#         intercept_grads : list, length = n_layers - 1
#             The ith element contains the amount of change used to update the
#             intercept parameters of the ith layer in an iteration.

#         Returns
#         -------
#         loss : float
#         coef_grads : list, length = n_layers - 1
#         intercept_grads : list, length = n_layers - 1
#         """
#         n_samples = X.shape[0]
#         dropout_masks = None
        
#         # Create the Dropout Mask (DROPOUT ADDITION)
#         if self.dropout != None:
#             if 0 < self.dropout < 1:
#                 keep_probability = 1 - self.dropout
#                 dropout_masks = [np.ones(layer_units[0])]
                
#                 # Create hidden Layer Dropout Masks
#                 for units in layer_units[1:-1]:
#                     # Create inverted Dropout Mask, check for random_state
#                     if self.random_state != None:
#                         layer_mask = (self._random_state.random(units) < keep_probability).astype(int) / keep_probability
#                     else:
#                         layer_mask = (np.random.rand(units) < keep_probability).astype(int) / keep_probability
#                     dropout_masks.append(layer_mask)
#             else:
#                 raise ValueError('Dropout must be between zero and one. If Dropout=X then, 0 < X < 1.')
        
#         # Forward propagate
#         # Added dropout_makss to _forward_pass call (DROPOUT ADDITION)
#         activations = self._forward_pass(activations, dropout_masks)
        
#         # Get loss
#         loss_func_name = self.loss
#         if loss_func_name == "log_loss" and self.out_activation_ == "logistic":
#             loss_func_name = "binary_log_loss"
#         loss = LOSS_FUNCTIONS[loss_func_name](y, activations[-1])
#         # Add L2 regularization term to loss
#         values = 0
#         for s in self.coefs_:
#             s = s.ravel()
#             values += np.dot(s, s)
#         loss += (0.5 * self.alpha) * values / n_samples

#         # Backward propagate
#         last = self.n_layers_ - 2

#         # The calculation of delta[last] here works with following
#         # combinations of output activation and loss function:
#         # sigmoid and binary cross entropy, softmax and categorical cross
#         # entropy, and identity with squared loss
#         deltas[last] = activations[-1] - y
        
#         # Compute gradient for the last layer
#         self._compute_loss_grad(
#             last, n_samples, activations, deltas, coef_grads, intercept_grads
#         )

#         inplace_derivative = DERIVATIVES[self.activation]
#         # Iterate over the hidden layers
#         for i in range(self.n_layers_ - 2, 0, -1):
#             deltas[i - 1] = safe_sparse_dot(deltas[i], self.coefs_[i].T)
#             inplace_derivative(activations[i], deltas[i - 1])
            
#             self._compute_loss_grad(
#                 i - 1, n_samples, activations, deltas, coef_grads, intercept_grads
#             )
        
#         # Apply Dropout Masks to the Parameter Gradients (DROPOUT ADDITION)
#         if dropout_masks != None:
#             for layer in range(len(coef_grads)-1):
#                 mask = (~(dropout_masks[layer+1] == 0)).astype(int)
#                 coef_grads[layer] = coef_grads[layer] * mask[None, :]
#                 coef_grads[layer+1] = (coef_grads[layer+1] * mask.reshape(-1, 1))
#                 intercept_grads[layer] = intercept_grads[layer] * mask
        
#         return loss, coef_grads, intercept_grads
    
#     def _forward_pass(self, activations, dropout_masks=None):
#         """Perform a forward pass on the network by computing the values
#         of the neurons in the hidden layers and the output layer.

#         Parameters
#         ----------
#         activations : list, length = n_layers - 1
#             The ith element of the list holds the values of the ith layer.
#         dropout_mask : list, length = n_layers - 1
#             The ith element of the list holds the dropout mask for the ith
#             layer.
#         """
#         hidden_activation = ACTIVATIONS[self.activation]
#         # Iterate over the hidden layers
#         for i in range(self.n_layers_ - 1):
#             activations[i + 1] = safe_sparse_dot(activations[i], self.coefs_[i])
#             activations[i + 1] += self.intercepts_[i]
            
#             # For the hidden layers
#             if (i + 1) != (self.n_layers_ - 1):
#                 hidden_activation(activations[i + 1])
            
#             # Apply Dropout Mask (DROPOUT ADDITION)
#             if (i + 1) != (self.n_layers_ - 1) and dropout_masks != None:
#                 check1 = activations[i].copy()
#                 activations[i+1] = activations[i+1] * dropout_masks[i+1][None, :]

#         # For the last layer
#         output_activation = ACTIVATIONS[self.out_activation_]
#         output_activation(activations[i + 1])
#         return activations

# %%


# %%


# %%


# %% [markdown]
# ##### MLPClassifier with string outcome support (compatible with recent sklearn versions)

# %%
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


# %% [markdown]
# ##### Create Universal Team Map Dictionary

# %%
import pandas as pd
import os
team_map = pd.read_csv(os.path.join(baseball_path, "Utilities", "Team Map.csv"))

# %%
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

# %% [markdown]
# ##### Create Venue Map DataFrame

# %%
def create_venue_map(write=False):
    # Fetch JSON data from the URL
    response = requests.get(url)
    data = response.json()
    
    # Extract venue details 
    venues = data.get("venues", data)  
    
    # Normalize the JSON into a DataFrame
    df = pd.json_normalize(venues)
    
    # Save to CSV
    if write == True:
        df.sort_values('id').to_csv(os.path.join(baseball_path, "Utilities", "Venue Map.csv"), index=False)


    return df

# %% [markdown]
# ##### Add Missing Values

# %%
# Read in Venue Map
venue_map_df = pd.read_csv(os.path.join(baseball_path, "Utilities", "Venue Map.csv"))

# George M. Steinbrenner
venue_map_df.loc[venue_map_df['id'] == 2523, ['fieldInfo.leftCenter', 'fieldInfo.rightCenter']] = [399.0, 385.0] # Yankee Stadium dimensions
# Sutter Health Park
venue_map_df.loc[venue_map_df['id'] == 2529, ['fieldInfo.leftCenter', 'fieldInfo.rightCenter']] = [375.0, 368.0] # https://x.com/JonPgh/status/1875224135573594599

# %% [markdown]
# ##### Log Print Statements

# %%
def log_print(text, sep, end, file, flush, write=False):
    if write == True:
        with open(os.path.join(baseball_path, f"{todaysdate} Sim Log.txt"), "w") as f:
            print(text, file=f)

# %% [markdown]
# ##### Median Scaler

# %%
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


# %% [markdown]
# ##### PyTorch MLP

# %%
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

# %% [markdown]
# ##### NumpyPrediction with sklearn wrapper

# %%
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


# %%
__all__ = [name for name in globals() if not name.startswith("_")]