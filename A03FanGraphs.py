# %%
from U01Imports import *

# %%
# FanGraphs API
def fangraphs_api(url):
    with open(os.path.join(baseball_path, "FanGraphs Headers.txt"), "r") as f:
        content = f.read()

    # Remove the "dictionary =" part
    content = content.split("=", 1)[1].strip()

    headers = ast.literal_eval(content)

    data = requests.get(url, headers=headers).json()
    for row in data:
        val = row.get("xMLBAMID")
        row["xMLBAMID"] = "" if val is None else str(val)
    df = pd.DataFrame(data)
    df['date'] = todaysdate


    return df

# %%
__all__ = [name for name in globals() if not name.startswith("_")]