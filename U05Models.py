# %% [markdown]
# # U05. Models
# - This imports models used to simulate games
# - Type: Utility
# - Run Frequency: Frequent
# - Created: 11/1/2023
# - Updated: 8/20/2025

# %%
from U01Imports import *   
from U02Functions import *
from U03Classes import *

import __main__
__main__.MedianCenterer = MedianCenterer
__main__.NumpyPredict = NumpyPredict


# %% [markdown]
# ### M01. Park and Weather Factors

# %% [markdown]
# ##### Batted-Ball Events

# %% [markdown]
# This predicts the probability of events given batted ball data

# %%
batted_ball_date = "20251104"

# %% [markdown]
# ##### Encode 

# %%
encode_outcome = pickle.load(open(os.path.join(model_path, "M01. Park and Weather Factors", batted_ball_date, "encode_outcome.pkl"), 'rb'))

# %% [markdown]
# ##### Scale

# %%
scale_inputs = pickle.load(open(os.path.join(model_path, "M01. Park and Weather Factors", batted_ball_date, "scale_inputs.pkl"), 'rb'))

# %% [markdown]
# ##### Predict

# %%
predict_outcome = keras.models.load_model(os.path.join(model_path, "M01. Park and Weather Factors", batted_ball_date, 'predict_outcome.keras'))

# %% [markdown]
# ##### WFX

# %% [markdown]
# This creates weather factors

# %%
wfx_date = "20251104"

# %% [markdown]
# ##### Scale

# %%
scale_wfx = pickle.load(open(os.path.join(model_path, "M01. Park and Weather Factors", wfx_date, "scale_wfx.pkl"), 'rb'))

# %% [markdown]
# ##### Predict

# %%
class VotingEnsemble:
    def __init__(self, models):
        self.models = models

    def predict(self, X):
        # Convert to tensor with fixed dtype and shape (except for batch dimension)
        X_tensor = tf.convert_to_tensor(X, dtype=tf.float32)
        predictions = np.array([
            model(X_tensor, training=False).numpy() for model in self.models
        ])
        return np.mean(predictions, axis=0)

# %%
# Directory containing models
model_dir = os.path.join(model_path, "M01. Park and Weather Factors", wfx_date)

# Find all keras model files matching pattern
model_files = sorted(glob.glob(os.path.join(model_dir, "predict_wfx_*.keras")))

# Load all models dynamically
ensemble_models = [keras.models.load_model(f) for f in model_files]

# Re-create predict_wfx ensemble
predict_wfx = VotingEnsemble(ensemble_models)

# %%


# %% [markdown]
# ### M02. Stat Imputations

# %% [markdown]
# This imputes the player stats used as model inputs using Steamer projections

# %%
stat_imputations_date = "20251104"

# %% [markdown]
# #### Stat Scalers

# %% [markdown]
# This scales player stats derived from the MLB Stats API and Statcast

# %% [markdown]
# ##### Batters



# %%
scale_batter_stats = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "scale_batter_stats.pkl"), "rb"))

# %% [markdown]
# ##### Pitchers

# %%
scale_pitcher_stats = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "scale_pitcher_stats.pkl"), "rb"))

# %% [markdown]
# #### Steamer Scalers

# %% [markdown]
# This scales player projections derived from Steamer

# %% [markdown]
# ##### Batters

# %%
scale_batter_stats_steamer = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "scale_batter_stats_steamer.pkl"), "rb"))

# %% [markdown]
# ##### Pitchers

# %%
scale_pitcher_stats_steamer = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "scale_pitcher_stats_steamer.pkl"), "rb"))

# %% [markdown]
# #### Imputations

# %% [markdown]
# This imputes player stats used as PA model inputs using Steamer/FanGraphs when minimal data is available

# %% [markdown]
# ##### Batters

# %%
impute_batter_stats = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "impute_batter_stats.sav"), "rb"))

# %% [markdown]
# ##### Pitchers

# %%
impute_pitcher_stats = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "impute_pitcher_stats.sav"), "rb"))

# %%


# %% [markdown]
# ### M03. Plate Appearances

# %% [markdown]
# ##### Binary

# %% [markdown]
# Out vs. Safe

# %%
# binary_filename = "predict_binary_1954_18081_20250301.sav"
# predict_binary = pickle.load(open(os.path.join(model_path, "M03. Plate Appearances", binary_filename), 'rb'))
predict_binary = None

# %% [markdown]
# ##### Outs

# %% [markdown]
# Lineouts, Groundouts, Popouts, Flyouts, Strikeouts

# %%
# outs_filename = "predict_outs_10_78785_20250226.sav"
# predict_outs = pickle.load(open(os.path.join(model_path, "M03. Plate Appearances", outs_filename), 'rb'))

predict_outs = None

# %% [markdown]
# ##### Safe

# %% [markdown]
# Single, Double, Triple, Home Run, Walk, Hit by Pitch

# %%
# safe_filename = "predict_safe_19510_48778_20250304.sav"
# predict_safe = pickle.load(open(os.path.join(model_path, "M03. Plate Appearances", safe_filename), 'rb'))

predict_safe = None

# %%


# %% [markdown]
# ##### Class

# %% [markdown]
# Class defined in M03. Plate Appearances

# # %%
# class NumpyPredict:
#     def __init__(self, ensemble_numpy, input_columns, classes, metadata=None):
#         """
#         ensemble_numpy: list of models, each a list of [W1, b1, W2, b2, ..., Wn, bn]
#         input_columns: list of feature names used during training (order matters!)
#         classes: list of class labels (same order as in training)
#         metadata: optional dict with additional info (hidden_layers, num_classifiers, etc.)
#         """
#         self.ensemble = ensemble_numpy
#         self.input_columns = input_columns
#         self.classes_ = classes
#         self.metadata = metadata or {}

#     @staticmethod
#     def _softmax(x):
#         e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
#         return e_x / e_x.sum(axis=1, keepdims=True)

#     @staticmethod
#     def _forward(model_layers, x):
#         """
#         Forward pass for a single model.
#         model_layers: [W1, b1, W2, b2, ..., Wn, bn]
#         x: numpy array of shape [n_samples, n_features]
#         """
#         h = x
#         n_layers = len(model_layers) // 2

#         # Apply all hidden layers with ReLU
#         for i in range(n_layers - 1):
#             W = model_layers[2*i]
#             b = model_layers[2*i + 1]
#             h = np.maximum(0, h @ W + b)

#         # Final layer = output
#         W = model_layers[-2]
#         b = model_layers[-1]
#         logits = h @ W + b
#         return NumpyPredict._softmax(logits)

#     def predict_proba(self, X):
#         """
#         X: pandas DataFrame, Series, or NumPy array
#         Returns: numpy array [n_samples, n_classes] with probabilities
#         """
#         # Convert DataFrame or Series to NumPy array
#         if isinstance(X, pd.DataFrame):
#             x_np = X[self.input_columns].to_numpy(dtype=np.float32)
#         elif isinstance(X, pd.Series):
#             x_np = X[self.input_columns].to_numpy(dtype=np.float32).reshape(1, -1)
#         else:
#             x_np = np.array(X, dtype=np.float32)
#             if x_np.ndim == 1:
#                 x_np = x_np.reshape(1, -1)

#         # Check input size against first layer
#         expected_size = self.ensemble[0][0].shape[0]
#         if x_np.shape[1] != expected_size:
#             raise ValueError(
#                 f"Input feature size ({x_np.shape[1]}) does not match model first layer ({expected_size})"
#             )

#         # Run all models in ensemble and average probabilities
#         probs_list = [self._forward(model, x_np) for model in self.ensemble]
#         avg_probs = np.mean(probs_list, axis=0)
#         return avg_probs

#     def predict(self, X):
#         """
#         Returns predicted class labels (argmax), like sklearn's predict()
#         """
#         probs = self.predict_proba(X)
#         return np.array([self.classes_[i] for i in np.argmax(probs, axis=1)])


# %% [markdown]
# ##### All

# %%
all_filename = "predict_all_256128_58081_20260304"

# Load the PredictAll wrapper
with open(os.path.join(model_path, "M03. Plate Appearances", f"{all_filename}_wrapper.pkl"), "rb") as f:
    predict_all = pickle.load(f)

# %% [markdown]
# ##### All - Adjusted with WFX

# %%
all_adjusted_filename = "predict_all_adjusted_32_87308_20251211"

# Load the PredictAll wrapper
with open(os.path.join(model_path, "M03. Plate Appearances", f"{all_adjusted_filename}_wrapper.pkl"), "rb") as f:
    predict_all_adjusted = pickle.load(f)

# %%


# %% [markdown]
# ### M04. Pulls

# %% [markdown]
# This predicts if a pitcher will be pulled from the game

# %%
pulls_date = "20251127"

# %%
# predict_pulls = pickle.load(open(os.path.join(model_path, "M04. Pulls", pulls_date, "predict_pulls.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M04. Pulls", pulls_date, "predict_pulls.sav"), "rb") as f:
    predict_pulls = pickle.load(f)

# %%


# %% [markdown]
# ### M05. Leverage

# %% [markdown]
# This predicts the leverage of relief pitcher that will come into the game

# %%
leverage_date = "20251127"

# %%
# predict_leverage = pickle.load(open(os.path.join(model_path, "M05. Leverage", f"predict_leverage_{leverage_date}.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M05. Leverage", leverage_date, "predict_leverage.sav"), "rb") as f:
    predict_leverage = pickle.load(f)

# %%


# %% [markdown]
# ### M06. Base Running

# %% [markdown]
# ##### Errors, outs, and advances

# %%
base_running_date = "20251124"

# %% [markdown]
# ##### Errors

# %%
# predict_errors = pickle.load(open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_errors.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_errors.sav"), "rb") as f:
    predict_errors = pickle.load(f)

# %% [markdown]
# ##### Double Plays

# %%
# predict_dp = pickle.load(open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_dp.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_dp.sav"), "rb") as f:
    predict_dp = pickle.load(f)

# %% [markdown]
# ##### Out Bases

# %%
# predict_out_bases = pickle.load(open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_out_bases.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_out_bases.sav"), "rb") as f:
    predict_out_bases = pickle.load(f)

# %% [markdown]
# ##### Events

# %%
# predict_events = pickle.load(open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_events.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_advances.sav"), "rb") as f:
    predict_advances = pickle.load(f)

# %% [markdown]
# ##### Steals

# %%
steal_date = "20251124"

# %% [markdown]
# ##### 2B Attempt

# %%
# predict_sba_2b = pickle.load(open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sba_2b.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sba_2b.sav"), "rb") as f:
    predict_sba_2b = pickle.load(f)

# %% [markdown]
# ##### 3B Attempt

# %%
# predict_sba_3b = pickle.load(open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sba_3b.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sba_3b.sav"), "rb") as f:
    predict_sba_3b = pickle.load(f)

# %% [markdown]
# ##### 2B Success

# %%
# predict_sb_2b = pickle.load(open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sb_2b.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sb_2b.sav"), "rb") as f:
    predict_sb_2b = pickle.load(f)

# %% [markdown]
# ##### 3B Success

# %%
predict_sb_3b = pickle.load(open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sb_3b.sav"), 'rb'))

# %%
with open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sb_3b.sav"), "rb") as f:
    predict_sb_3b = pickle.load(f)



# %%
__all__ = [name for name in globals() if not name.startswith("_")]