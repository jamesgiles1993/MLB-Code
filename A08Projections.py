# %%
from U01Imports import *
from U02Functions import *
from U04Datasets import *
from U05Models import *


# %%
# Identify DraftKings slate name
def pick_slate(Name):
    if "(Early)" in Name:
        slate = "Early"
    elif "(Late Night)" in Name:
        slate = "Late Night"
    elif "Night" in Name:
        slate = "Night"
    elif "Afternoon" in Name:
        slate = "Afternoon"
    else:
        slate = "All"
        
        
    return slate


# %%
# Scrape DFF slates
def dff_slates(date):
    url = 'https://www.dailyfantasyfuel.com/data/slates/next/mlb/dk?x=1'
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
    else:
        print(f"Failed to fetch data from {url}. Status code: {response.status_code}")
        return None

    # Extract relevant fields from the data
    formatted_data = []
    for entry in data:
        sport = entry.get('sport')
        team_count = entry.get('team_count')
        game_count = entry.get('game_count')
        slate_type = entry.get('slate_type', '')
        url = entry.get('url')
        start_string = entry.get('start_string')
        future_rank = entry.get('future_rank')
        showdown_flag = entry.get('showdown_flag')

        # Extract time from the "Start Time" string
        time = start_string.split(", ")[1]

        row = {
            'Sport': sport,
            'Team Count': team_count,
            'Game Count': game_count,
            'Slate Type': slate_type,
            'URL': url,
            'Start Time': start_string,
            'Time': time,  # New "Time" column
            'Future Rank': future_rank,
            'Showdown Flag': showdown_flag
            }

        formatted_data.append(row)

    # Create a pandas DataFrame
    df = pd.DataFrame(formatted_data)
    df['date'] = date

    df['Slate Type'] = np.where(df['Slate Type'] == "", "All", df['Slate Type'])
    df['URL'] = df['URL'].astype('str')

    
    return df


# %%
# Scrapes RotoWire slates
def roto_slates(date):
    date_dash = date[0:4] + "-" + date[4:6] + "-" + date[6:]
    url = 'https://www.rotowire.com/daily/mlb/saved-lineups.php?date={}'.format(date_dash)
    
    def fetch_page_source(url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Failed to fetch page source. Status code: {response.status_code}")

    def extract_data_from_page(html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        slates_data = []
        for slate in soup.find_all('a', class_='dfs-slate'):
            date_fragment, time = [text.strip() for text in slate.find('div', class_='dfs-slate-desc').stripped_strings]
            time = time.lower()

            slate_name_parts = [text.strip() for text in slate.find('div', class_='dfs-slate-name').stripped_strings]
            slate_name = slate_name_parts[0]
            num_games = slate_name_parts[-1].split()[0]  # Extract the number of games from the last part

            slate_id = slate['href'].split('slateID=')[1]

            slates_data.append({'date': date, 'slateID': slate_id, 'name': slate_name, 'time': time, 'games': num_games})

        return slates_data

    page_source = fetch_page_source(url)
    data = extract_data_from_page(page_source)
    
    # Create a pandas DataFrame
    df = pd.DataFrame(data)
    
    # Games will be a string of one of the team abbreviations. Fix it.
    df['games'] = pd.to_numeric(df['games'], errors='coerce')
    df['games'].fillna(1, inplace=True)
    df['games'] = df['games'].astype('int') 

    
    return df


# %%
# Scrape DFF projections
def dff_projections(date, code):
    # DFF url
    url = f"https://www.dailyfantasyfuel.com/data/playerdetails/mlb/dk/{code}?x=1"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
    else:
        print(f"Failed to fetch data from {url}. Status code: {response.status_code}")
        return None

    # Create a list to store player data
    formatted_data = []

    # Iterate over each player entry
    for player in data:
        sport = player.get('sport')
        team = player.get('team')
        location = player.get('location')
        opp = player.get('opp')
        first_name = player.get('first_name')
        last_name = player.get('last_name')
        position_detailed = player.get('position_detailed')
        position_code = player.get('position_code')
        hand = player.get('hand')
        player_id = player.get('player_id')
        salary = player.get('salary')
        ppg = player.get('ppg')
        value = player.get('value')
        opp_rank = player.get('opp_rank')
        depth_rank = player.get('depth_rank')
        starter_flag = player.get('starter_flag')
        team_spread = player.get('team_spread')
        projected_team_score = player.get('projected_team_score')
        probable_flag = player.get('probable_flag')

        # Append player data to the list
        formatted_data.append({
            'Sport': sport,
            'Team': team,
            'Location': location,
            'Opponent': opp,
            'First Name': first_name,
            'Last Name': last_name,
            'Position Detailed': position_detailed,
            'Position Code': position_code,
            'Hand': hand,
            'Player ID': player_id,
            'Salary': salary,
            'PPG': ppg,
            'Value': value,
            'Opp Rank': opp_rank,
            'Depth Rank': depth_rank,
            'Starter Flag': starter_flag,
            'Team Spread': team_spread,
            'Projected Team Score': projected_team_score,
            'Probable Flag': probable_flag
        })

    # Create a pandas DataFrame
    df = pd.DataFrame(formatted_data)

    # Calculate fantasy points using Salary and Value (they don't have points for some reason)
    df['Salary'] = df['Salary'].fillna(99999).astype('int')
    
    df['Value'] = df['Value'].astype('float')
    df['FP'] = df['Salary'] / 1000 * df['Value']
    
    df['date'] = date
    df['code'] = code

    
    return df


# %%
# Scrape RotoWire projections
def roto_projections(date, slateID):
    # RotoWire Optimizer URL
    url = f'https://www.rotowire.com/optimizer/api/mlb/players.php?slateID={slateID}'
    
    try:
        # Fetch JSON data from the API
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for unsuccessful responses
        api_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None

    if not api_data:
        print("No data found in API response.")
        return None

    extracted_data = []

    for entry in api_data:
        rwID = entry.get('rwID')
        slate_id = entry.get('slateID')
        first_name = entry.get('firstName')
        last_name = entry.get('lastName')
        roto_pos = entry.get('rotoPos')
        position = ','.join(entry.get('pos', []))
        throws = entry.get('throws')
        bats = entry.get('bats')
        is_pitcher = entry.get('isPitcher')
        is_batter = entry.get('isBatter')
        team_abbr = entry.get('team', {}).get('abbr')
        team_city = entry.get('team', {}).get('city')
        team_nickname = entry.get('team', {}).get('nickname')
        game_date_time = entry.get('game', {}).get('dateTime')
        game_is_dome = entry.get('game', {}).get('isDome')
        salary = entry.get('salary')
        points = entry.get('pts')
        rostership = entry.get('rostership')

        row = {
            'rwID': rwID,
            'slateID': slate_id,
            'firstName': first_name,
            'lastName': last_name,
            'rotoPos': roto_pos,
            'position': position,
            'throws': throws,
            'bats': bats,
            'isPitcher': is_pitcher,
            'isBatter': is_batter,
            'teamAbbr': team_abbr,
            'teamCity': team_city,
            'teamNickname': team_nickname,
            'gameDateTime': game_date_time,
            'gameIsDome': game_is_dome,
            'salary': salary,
            'points': points, 
            'rostership': rostership
        }

        extracted_data.append(row)

    # Create a pandas DataFrame
    df = pd.DataFrame(extracted_data)

    # Assign date
    df['date'] = date

    
    return df


# %%
__all__ = [name for name in globals() if not name.startswith("_")]


