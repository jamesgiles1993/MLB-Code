# U05. Models
# This imports models used to simulate games
# Type: Utility
# Run Frequency: Frequent
# Created: 11/1/2023
# Updated: 8/20/2025

# Note: This has been removed from C01Simulations.py, preferring to just pass in the models

### Imports
from U01Imports import *   
from U02Functions import *
from U03Classes import *

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

import __main__
__main__.MedianCenterer = MedianCenterer
__main__.NumpyPredict = NumpyPredict


### M01. Batted Balls.ipynb
# This predicts the probability of events given batted ball data
batted_ball_date = "20260702"

# Encode 
encode_outcome = pickle.load(open(os.path.join(model_path, "M01. Park and Weather Factors", batted_ball_date, "encode_outcome.pkl"), 'rb'))

# Scale
scale_inputs = pickle.load(open(os.path.join(model_path, "M01. Park and Weather Factors", batted_ball_date, "scale_inputs.pkl"), 'rb'))

# Predict
predict_outcome = keras.models.load_model(os.path.join(model_path, "M01. Park and Weather Factors", batted_ball_date, 'predict_outcome.keras'))



### M01. Weather Factors.ipynb
# This creates weather factors
wfx_date = "20260702"

# Scale
scale_wfx = pickle.load(open(os.path.join(model_path, "M01. Park and Weather Factors", wfx_date, "scale_wfx.pkl"), 'rb'))

# Predict
class WeatherNet(nn.Module):
    def __init__(self, n_inputs, n_outputs, hidden_layers, dropout):
        super().__init__()
        layers = []
        in_dim = n_inputs
        for h in hidden_layers:
            layers += [nn.Linear(in_dim, h), nn.ReLU()]
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            in_dim = h
        layers.append(nn.Linear(in_dim, n_outputs))
        self.net = nn.Sequential(*layers)
    def forward(self, x):
        return self.net(x)

class TorchEnsemble:
    def __init__(self, models, device):
        self.models = models
        self.device = device
    def predict(self, X):
        X_t = torch.tensor(X, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            preds = torch.stack([m(X_t) for m in self.models])
        return preds.mean(dim=0).cpu().numpy()

model_folder = os.path.join(model_path, "M01. Park and Weather Factors", wfx_date)
cfg = pickle.load(open(os.path.join(model_folder, 'predict_wfx_config.pkl'), 'rb'))
hidden_layers, dropout, lr, batch_size, weight_decay = cfg['config']
n_inputs, n_outputs = cfg['n_inputs'], cfg['n_outputs']

loaded_models = []
for i in range(cfg['n_models']):
    m = WeatherNet(n_inputs, n_outputs, hidden_layers, dropout).to(device)
    m.load_state_dict(torch.load(os.path.join(model_folder, f'predict_wfx_{i}.pt'), map_location=device))
    m.eval()
    loaded_models.append(m)

predict_wfx = TorchEnsemble(loaded_models, device)



### M02. Stat Imputations
# This imputes the player stats used as model inputs using Steamer projections
stat_imputations_date = "20260702"

# Scale batter API stats
scale_batter_stats = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "scale_batter_stats.pkl"), "rb"))

# Scale pitcher API stats
scale_pitcher_stats = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "scale_pitcher_stats.pkl"), "rb"))

# Scale batter Steamer stats
scale_batter_stats_steamer = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "scale_batter_stats_steamer.pkl"), "rb"))

# Scale pitcher Steamer stats
scale_pitcher_stats_steamer = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "scale_pitcher_stats_steamer.pkl"), "rb"))

# Impute batter stats (deprecated)
# impute_batter_stats = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "impute_batter_stats.sav"), "rb"))
impute_batter_stats = None

# Imputer pitcher stats (deprecated)
# impute_pitcher_stats = pickle.load(open(os.path.join(model_path, "M02. Stat Imputations", stat_imputations_date, "impute_pitcher_stats.sav"), "rb"))
impute_pitcher_stats = None


### M03. Plate Appearances
# This predicts the outcome of PAs
### All Output Approach
# all_filename = "predict_all_512256_A_512x256_LowLR_Reg1e4_88830_20260702"
all_filename = "predict_all_512256_A_512x256_LowLR_Reg1e4_23964_20260720"


# Load the PredictAll wrapper
with open(os.path.join(model_path, "M03. Plate Appearances", f"{all_filename}_wrapper.pkl"), "rb") as f:
    predict_all = pickle.load(f)

# All - Adjusted with WFX (deprecated)
all_adjusted_filename = "predict_all_adjusted_32_87308_20251211"

# Load the PredictAll wrapper
with open(os.path.join(model_path, "M03. Plate Appearances", f"{all_adjusted_filename}_wrapper.pkl"), "rb") as f:
    predict_all_adjusted = pickle.load(f)



### M04. Pulls
# This predicts if a pitcher will be pulled from the game
pulls_date = "20260702"
with open(os.path.join(model_path, "M04. Pulls", pulls_date, "predict_pulls.sav"), "rb") as f:
    predict_pulls = pickle.load(f)



### M05. Leverage
# This predicts the leverage of relief pitcher that will come into the game
leverage_date = "20260702"
with open(os.path.join(model_path, "M05. Leverage", leverage_date, "predict_leverage.sav"), "rb") as f:
    predict_leverage = pickle.load(f)



### M06. Base Running
# This predicts errors, double plays, outs bases, and advances
base_running_date = "20260702"

# Errors
with open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_errors.sav"), "rb") as f:
    predict_errors = pickle.load(f)

# Double Plays
with open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_dp.sav"), "rb") as f:
    predict_dp = pickle.load(f)

# Out Bases
with open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_out_bases.sav"), "rb") as f:
    predict_out_bases = pickle.load(f)

# Events
with open(os.path.join(model_path, "M06. Base Running", base_running_date, "predict_advances.sav"), "rb") as f:
    predict_advances = pickle.load(f)

# This predicts steals
steal_date = "20260702"

# 2B Attempt
with open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sba_2b.sav"), "rb") as f:
    predict_sba_2b = pickle.load(f)

# 3B Attempt
with open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sba_3b.sav"), "rb") as f:
    predict_sba_3b = pickle.load(f)

# 2B Success
with open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sb_2b.sav"), "rb") as f:
    predict_sb_2b = pickle.load(f)

# 3B Success
with open(os.path.join(model_path, "M06. Base Running", steal_date, "predict_sb_3b.sav"), "rb") as f:
    predict_sb_3b = pickle.load(f)


models_dict = {
    'predict_all': predict_all,
    'predict_pulls': predict_pulls,
    'predict_leverage': predict_leverage,
    'predict_errors': predict_errors,
    'predict_dp': predict_dp,
    'predict_out_bases': predict_out_bases,
    'predict_advances': predict_advances,
    'predict_sba_2b': predict_sba_2b,
    'predict_sba_3b': predict_sba_3b,
    'predict_sb_2b': predict_sb_2b,
    'predict_sb_3b': predict_sb_3b,
}


__all__ = [name for name in globals() if not name.startswith("_")]