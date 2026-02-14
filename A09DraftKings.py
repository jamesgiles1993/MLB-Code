# %%
from U01Imports import *

# %%
# Scrape DraftKings contests
def contests(date):
    # Extract JSON data
    response = requests.get("https://www.draftkings.com/lobby/getcontests?sport=MLB")
    json_data = response.json()

    # Extract the "Contests" data
    contests_data = json_data["Contests"]

    # Create an empty list to store the extracted data
    rows = []

    # Iterate over each contest
    for contest in contests_data:
        contest_dict = {}

        # Extract the desired fields from the contest
        contest_dict["Name"] = contest["n"]
        contest_dict["Cash Prize"] = contest["pd"].get("Cash", None)
        contest_dict["Entry Fee"] = contest["a"]
        contest_dict["contestKey"] = contest["id"]
        contest_dict["draftGroupId"] = contest["dg"]
        contest_dict['contestDate'] = contest["sd"]
        contest_dict['contestDate'] = contest_dict['contestDate'].replace("/Date(", "").replace(")/","")
        contest_dict['contestTime'] = contest["sdstring"]
        contest_dict['gameType'] = contest['gameType']
        
        # Append the extracted data to the list
        rows.append(contest_dict)

    # Create a DataFrame from the extracted data
    df = pd.DataFrame(rows)
    
    # Fix date
    df['contestDate'] = pd.to_numeric(df['contestDate'])
    df['contestDate'] = df['contestDate'] / 1000  # Convert milliseconds to seconds
    df['contestDate'] = df['contestDate'].apply(datetime.datetime.fromtimestamp)
    
    # Date (without time)
    df['date'] = date
    
    # Sort by date
    df.sort_values('contestDate', ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    
    return df


# %%
# Scrapes Draftables for a given draftGroupId
def draftables(draftGroupId):
    # Extract game info (used to determining away and home teams, date, time)
    def get_game_info(row):
        # Define the time zone conversion
        source_timezone = pytz.timezone('UTC')
        target_timezone = pytz.timezone('America/New_York')

        # Extract competitions
        competitions = row.get('competitions', [])
        if competitions:
            name_display = competitions[0].get('nameDisplay', [])
            if len(name_display) >= 3:
                # Extract team names
                team1 = name_display[0]['value']
                team2 = name_display[2]['value']
                # And start time
                start_time = dateutil.parser.parse(competitions[0]['startTime']).astimezone(target_timezone).strftime('%m/%d/%Y %I:%M%p')
                # Convert to typical away@home datetime ET format
                return f"{team1}@{team2} {start_time} ET"
        return ""
    
    # Extract JSON data
    response = requests.get(f'https://api.draftkings.com/draftgroups/v1/draftgroups/{draftGroupId}/draftables')
    json_data = response.json()
    
    # Access the "draftables" key in the JSON data
    draftables = json_data["draftables"]

    # Convert the "draftables" data to a DataFrame
    df = pd.DataFrame(draftables)


    # Extracting and formatting game information
    df["Game Info"] = df.apply(get_game_info, axis=1)
    df["AvgPointsPerGame"] = df["draftStatAttributes"].apply(lambda x: x[0]["value"])
    df['Name + ID'] = df['displayName'] + " (" + df['draftableId'].astype('str') + ")" 
    df["Roster Position"] = df["position"].apply(lambda x: "P" if x in ["SP", "RP"] else x)
    df["alertType"] = df["draftAlerts"].apply(lambda x: x[0]["alertType"] if isinstance(x, list) and len(x) > 0 else None)
    
    # Rename to match salary download files
    df.rename(columns={'position':'Position', 'displayName': 'Name', 'salary':'Salary', 'teamAbbreviation':'TeamAbbrev', 'draftableId':'ID'}, inplace=True)

    # Select relevant columns
    df = df[['Position', 'Name + ID', 'Name', 'ID', 'Roster Position', 'Salary', 'Game Info', 'TeamAbbrev', 'AvgPointsPerGame', 'playerId', 'alertType']]

    df.drop_duplicates(['Name', 'TeamAbbrev'], inplace=True)
    df.reset_index(inplace=True, drop=True)
    
    df['draftGroupId'] = draftGroupId


    return df


# %%
# Scrapes DraftKings contest payout structure
def payouts(contestKey):
    # Extract JSON data
    response = requests.get(f"https://api.draftkings.com/contests/v1/contests/{contestKey}?format=json")
    json_data = response.json()
    
    # Extract minPosition, maxPosition, and payoutDescription
    payouts = json_data['contestDetail']['payoutSummary']
    data = []
    for payout in payouts:
        min_pos = payout['minPosition']
        max_pos = payout['maxPosition']
        payout_desc = payout['payoutDescriptions'][0]['payoutDescription']
        entry_fee = json_data['contestDetail']['entryFee']
        entries = json_data['contestDetail']['entries']
        max_entries_per_user = json_data['contestDetail']['maximumEntriesPerUser']
        draft_group_id = json_data['contestDetail']['draftGroupId']
        contest_key = json_data['contestDetail']['contestKey']
        contest_start_time = json_data['contestDetail']['contestStartTime']
        name = json_data['contestDetail']['name']
        data.append([min_pos, max_pos, payout_desc, entry_fee, entries, max_entries_per_user, draft_group_id, contest_key, contest_start_time, name])

    # Create a dataframe
    df = pd.DataFrame(data, columns=['minPosition', 'maxPosition', 'payoutDescription', 'entryFee', 'entries', 'maximumEntriesPerUser', 'draftGroupId', 'contestKey', 'contestStartTime', 'name'])

    
    return df


# %%
# Downloads contest results from DraftKings
def results(contestKey, sleep_time=5):
    # Open in a new tab (same window)
    webbrowser.open(f"https://www.draftkings.com/contest/exportfullstandingscsv/{contestKey}")

    # Wait for file to download
    time.sleep(sleep_time)
    
    # Specify the path to the Downloads directory
    downloads_folder = r'C:\Users\james\Downloads'

    # Get a list of all files in the Downloads directory
    files = os.listdir(downloads_folder)


    # Filter the list to include files starting with 'contest-standings' and sort by modification time (most recent first)
    search_term = f'contest-standings-{contestKey}'
    print(search_term)
    relevant_files = [file for file in files if file.startswith(search_term)]
    # print(files)
    sorted_files = sorted(relevant_files, key=lambda x: os.path.getmtime(os.path.join(downloads_folder, x)), reverse=True)

    print(sorted_files)
        
    # Look at relevant files
    if sorted_files:
        # Select the most recent file
        most_recent_file = sorted_files[0]

        # Specify the path to the most recent file
        file_path = os.path.join(downloads_folder, most_recent_file)

        print(file_path)
        
        # Specify the path to the destination folder where you want to save the file
        destination_folder = os.path.join(baseball_path, "A09. DraftKings", "4. Results")

        # If the file is a zip, unpack it; otherwise, copy it over
        if file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                # Extract all files from the zip file to the destination folder
                zip_ref.extractall(destination_folder)
            print('Zip file unpacked successfully!')
        else:
            # Copy the file to the destination folder
            shutil.copy2(file_path, destination_folder)
            print('File copied successfully!')
    else:        
        print('No relevant files found in the Downloads directory.')


# %%
# Create entry results dataframe
def entry_results(results_df):
    # Entry results 
    entry_results_df = results_df[['Rank', 'EntryId', 'EntryName', 'TimeRemaining', 'Points', 'Lineup']].dropna()
        
    entry_results_df['Lineup_Copy'] = entry_results_df['Lineup'].copy()
        
    ### Prep for regular expression divisions 
    # Add space to the beginning    
    entry_results_df['Lineup'] = ' ' + entry_results_df['Lineup']

    # Add spaces around positions
    for position in ['P', 'C', '1B', '2B', '3B', 'SS', 'OF']:
        entry_results_df['Lineup'] = entry_results_df['Lineup'].str.replace(f" {position} ", f"  {position}  ")
    
    # Add space to the end
    entry_results_df['Lineup'] = entry_results_df['Lineup'] + "  "

    ### P
    # Define the regex pattern to match "P  {name}  " and extract {name}
    pattern = r'P\s\s(.*?)\s\s'

    # Create empty columns for "P" and "P.1"
    entry_results_df['P'] = None
    entry_results_df['P.1'] = None

    # Iterate through the DataFrame
    for index, row in entry_results_df.iterrows():
        matches = re.findall(pattern, row['Lineup'])
        if len(matches) >= 2:
            entry_results_df.at[index, 'P'] = matches[0]
            entry_results_df.at[index, 'P.1'] = matches[1]
    
    ### C
    # Define a regex pattern to match "C  {name}  " and extract {name}
    pattern = r'C\s\s(.*?)\s\s'
    
    # Create empty column for "C"
    entry_results_df['C'] = None

    # Iterate through the DataFrame
    for index, row in entry_results_df.iterrows():
        matches = re.findall(pattern, row['Lineup'])
        entry_results_df.at[index, 'C'] = matches[0]
    
    ### 1B
    # Define a regex pattern to match "1B  {name}  " and extract {name}
    pattern = r'1B\s\s(.*?)\s\s'
    
    # Create empty column for "C"
    entry_results_df['1B'] = None

    # Iterate through the DataFrame
    for index, row in entry_results_df.iterrows():
        matches = re.findall(pattern, row['Lineup'])
        entry_results_df.at[index, '1B'] = matches[0]
    
    ### 2B
    # Define a regex pattern to match "2B  {name}  " and extract {name}
    pattern = r'2B\s\s(.*?)\s\s'
    
    # Create empty column for "C"
    entry_results_df['2B'] = None

    # Iterate through the DataFrame
    for index, row in entry_results_df.iterrows():
        matches = re.findall(pattern, row['Lineup'])
        entry_results_df.at[index, '2B'] = matches[0]
    
    ### 3B
    # Define a regex pattern to match "3B  {name}  " and extract {name}
    pattern = r'3B\s\s(.*?)\s\s'
    
    # Create empty column for "C"
    entry_results_df['3B'] = None

    # Iterate through the DataFrame
    for index, row in entry_results_df.iterrows():
        matches = re.findall(pattern, row['Lineup'])
        entry_results_df.at[index, '3B'] = matches[0]
    
    ### SS
     # Define a regex pattern to match "SS  {name}  " and extract {name}
    pattern = r'SS\s\s(.*?)\s\s'
    
    # Create empty column for "C"
    entry_results_df['SS'] = None

    # Iterate through the DataFrame
    for index, row in entry_results_df.iterrows():
        matches = re.findall(pattern, row['Lineup'])
        entry_results_df.at[index, 'SS'] = matches[0]
        
    ### OF
    # Define the regex pattern to match "P  {name}  " and extract {name}
    pattern = r'OF\s\s(.*?)\s\s'

    # Create empty columns for "OF" and "OF.1" and "OF.2"
    entry_results_df['OF'] = None
    entry_results_df['OF.1'] = None
    entry_results_df['OF.2'] = None

    # Iterate through the DataFrame
    for index, row in entry_results_df.iterrows():
        matches = re.findall(pattern, row['Lineup'])
        if len(matches) >= 3:
            entry_results_df.at[index, 'OF'] = matches[0]
            entry_results_df.at[index, 'OF.1'] = matches[1]
            entry_results_df.at[index, 'OF.2'] = matches[2]
            
    entry_results_df['Lineup'] = entry_results_df['Lineup_Copy']
    entry_results_df.drop(columns={'Lineup_Copy'}, inplace=True)
    
    
    return entry_results_df


# %%
# Create player results dataframe
def player_results(results_df):
    # Player results 
    player_results = results_df[['Player', 'Roster Position', '%Drafted', 'FPTS']].dropna()    
    
    
    return player_results


# %%
# Create subset of contests based for which we'll gather data
def create_subset(contest_df, contests_per_draftGroupId=10, entry_fee_max=100, added_contestKeys=[], date_dash=todaysdate_dash):
    # Create copy
    subset_df = contest_df.copy()
    
    # Only keep "Classic" contests
    subset_df = contest_df[contest_df['gameType'] == 'Classic']

    # Always keep certain contests, regardless of cash prizes
    four_seamer_df = subset_df[subset_df['Name'].str.contains("eamer", case=False)]
    knuckleball_df = subset_df[subset_df['Name'].str.contains("nuckleball", case=False)]
    
    # Convert Cash Prize to numeric
    subset_df['Cash Prize'] = subset_df['Cash Prize'].str.replace("$", "").str.replace(",", "").astype('float')
    # Only keep contests from today and those with reasonable entry fees
    subset_df['date_dash'] = subset_df['contestDate'].astype('str').str[:10]
    subset_df['Entry Fee'] = subset_df['Entry Fee'].astype('float')
    subset_df = subset_df[(subset_df['date_dash'] == date_dash) & (subset_df['Entry Fee'] < entry_fee_max)]
    
    # Take the top n highest cash prizes based on draftGroupId
    subset_df = subset_df.sort_values(['draftGroupId', 'Cash Prize'], ascending=[False, False]).groupby('draftGroupId').head(contests_per_draftGroupId).reset_index(drop=True)

    # Append on additional contests
    subset_df = pd.concat([subset_df, four_seamer_df, knuckleball_df], axis=0)

    # Remove one game matchups
    subset_df = subset_df[~subset_df['Name'].str.contains("vs")]

    # Filter contests based on added_contestKeys
    if added_contestKeys != []:
        subset_df = pd.concat([subset_df, contest_df[contest_df['contestKey'].isin(added_contestKeys)]], axis=0)

    # Only keep one dataframe per contest
    subset_df.drop_duplicates('contestKey', inplace=True, keep='first')

    # Reset index
    subset_df.reset_index(drop=True, inplace=True)

    
    return subset_df


# %%
__all__ = [name for name in globals() if not name.startswith("_")]
