# %%
from U01Imports import *

# %%
# FanGraphs API
def fangraphs_api(url):
    data = requests.get(url).json()

    for row in data:
        val = row.get("xMLBAMID")  # Some players have null xMLBAMID values, so we need to handle that case
        row["xMLBAMID"] = "" if val is None else str(val)  # Convert to string for consistency, even if it's an empty string

    df = pd.DataFrame(data)
    df['date'] = todaysdate

    
    return df


# %%
__all__ = [name for name in globals() if not name.startswith("_")]