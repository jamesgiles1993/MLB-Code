# %%
from U01Imports import *
from U02Functions import *

# %%
# Scrape Bullpen Data from MLB.com Depth Charts
def scrape_bullpen(mlburl, bbrefteam, historic=False, date=None):
    if historic:
        url = f"https://web.archive.org/web/{date}/https://www.mlb.com/{mlburl}/roster/depth-chart"
    else:
        url = f"https://www.mlb.com/{mlburl}/roster/depth-chart"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest"
    }

    r = requests.get(url, headers=headers)
    time.sleep(1)
    
    # Read tables with pandas
    dfs = pd.read_html(StringIO(r.text), encoding='iso-8859-1')

    # Use BeautifulSoup to get links
    soup = BeautifulSoup(r.text, 'html.parser')
    player_links = {}
    for tag in soup.select('a[href*="/player/"]'):
        name = tag.get_text(strip=True)
        href = tag['href']
        if name:
            # Remove numbers and (CL) just like we do below
            cleaned_name = re.sub(r'\(CL\)|\d+', '', name).strip()
            cleaned_name = remove_accents(cleaned_name)
            player_links[cleaned_name] = f"https://www.mlb.com{href}"

    # Bullpen can be one of two tables
    try:
        df = dfs[2]
        df = df[df["Bullpen.1"].str.contains("IL-") == False].reset_index(drop=True)
        df = df[df["Bullpen.1"].str.contains(" Minors") == False].reset_index(drop=True)
    except:
        df = dfs[1]
        df = df[df["Bullpen.1"].str.contains("IL-") == False].reset_index(drop=True)
        df = df[df["Bullpen.1"].str.contains(" Minors") == False].reset_index(drop=True)

    # Assume leverage = 0 by default
    df['Leverage'] = 0
    for i in range(len(df)):
        if i == 0:
            df.at[i, 'Leverage'] = 4
        elif i < 4:
            df.at[i, 'Leverage'] = 3
        elif i < 11:
            df.at[i, 'Leverage'] = 2

    df.loc[df.index[-1], 'Leverage'] = 2
    if 3 not in list(df['Leverage']):
        df.loc[df.index[-2], 'Leverage'] = 3

    # Extract name and B/T
    df[['Name', 'drop']] = df['Bullpen.1'].str.split("B/T", expand=True)
    df['Name'] = df['Name'].str.replace(r'\d+', '', regex=True)
    df['Name'] = df['Name'].str.replace(r"\(CL\)", '', regex=True)
    df['Name'] = df['Name'].apply(remove_accents).str.strip()

    # Rebuild B/T column
    df['B/T'] = df['drop'].str.extract(r'([LR]+/[LR]+)', expand=False)

    # Add player URLs
    df['URL'] = df['Name'].map(player_links)

    # Extract player's MLB id from URL
    df['id'] = df['URL'].str.split('/').str[-1]
    
    # Final columns
    df = df[['Name', 'B/T', 'Leverage', 'URL', 'id']]
    df['date'] = date
    df['BBREFTEAM'] = bbrefteam

    
    return df


# %%
# Create bullpen dataframe (and csv)
def bullpens(date, team_map, historic):    
    # Create folder, if necessary
    os.makedirs(os.path.join(baseball_path, 'A04. Bullpens', f"Bullpens {date}"), exist_ok=True)
    time.sleep(1)
    
    # Scrape bullpens
    for i in range(len(team_map)):
        # Extract team's website URL
        mlburl = team_map['MLBURL'][i]
        # Extract team's Baseball Reference abbreviation
        bbrefteam = team_map['BBREFTEAM'][i]
        # Scrape bullpens
        bullpen_df = scrape_bullpen(mlburl, bbrefteam, historic, date)
        # To CSV
        bullpen_df.to_csv(os.path.join(baseball_path, "A04. Bullpens", f"Bullpens {date}", f"Bullpen {bbrefteam} {date}.csv"), index=False, encoding='iso-8859-1')


# %%
__all__ = [name for name in globals() if not name.startswith("_")]