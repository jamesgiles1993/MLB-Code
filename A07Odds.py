# %%
from U01Imports import *
from U02Functions import *

# %%
# Extract odds from Sportsbook Review
def scrape_sportsbookreview(date):
    urls = {
        "moneyline": f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date}",
        "pointspread": f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/pointspread/?date={date}",
        "totals": f"https://www.sportsbookreview.com/betting-odds/mlb-baseball/totals/?date={date}"
    }

    games_dict = {}
    opener_dict = {}  # Collect opener lines separately per game

    for bet_type, url in urls.items():
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch {bet_type}: {response.status_code}")
            continue

        match = re.search(r'<script id="__NEXT_DATA__".*?>(.*?)</script>', response.text, re.DOTALL)
        if not match:
            print(f"No data found for {bet_type}")
            continue

        data = json.loads(match.group(1))
        odds_tables = data['props']['pageProps'].get('oddsTables', [])

        for table in odds_tables:
            for game in table['oddsTableModel'].get('gameRows', []):
                gameView = game.get('gameView', {})
                game_id = gameView.get('gameId')
                home = gameView.get('homeTeam', {}).get('displayName')
                away = gameView.get('awayTeam', {}).get('displayName')
                startTime = gameView.get('startDate')

                # --- Process current sportsbook lines ---
                for oddsView in game.get('oddsViews') or []:
                    if not oddsView:
                        continue
                    sportsbook = oddsView.get('sportsbook')
                    current = oddsView.get('currentLine', {})
                    if not sportsbook or not current:
                        continue

                    key = (game_id, sportsbook)
                    if key not in games_dict:
                        games_dict[key] = {
                            'gameId': game_id,
                            'homeTeam': home,
                            'awayTeam': away,
                            'startTime': startTime,
                            'sportsbook': sportsbook,
                            'homeML': None,
                            'awayML': None,
                            'homePS': None,
                            'awayPS': None,
                            'spread': None,
                            'total': None,
                            'overOdds': None,
                            'underOdds': None
                        }

                    if bet_type == 'moneyline':
                        games_dict[key]['homeML'] = current.get('homeOdds')
                        games_dict[key]['awayML'] = current.get('awayOdds')
                    elif bet_type == 'pointspread':
                        games_dict[key]['homePS'] = current.get('homeOdds')
                        games_dict[key]['awayPS'] = current.get('awayOdds')
                        games_dict[key]['spread'] = current.get('homeSpread')
                    elif bet_type == 'totals':
                        games_dict[key]['total'] = current.get('total')
                        games_dict[key]['overOdds'] = current.get('overOdds')
                        games_dict[key]['underOdds'] = current.get('underOdds')

                # --- Collect opener data separately ---
                opener_line = None
                for ov in game.get('oddsViews') or []:
                    if ov and ov.get('openingLine'):
                        opener_line = ov.get('openingLine')
                        break
                if opener_line:
                    if game_id not in opener_dict:
                        opener_dict[game_id] = {
                            'homeML': None,
                            'awayML': None,
                            'homePS': None,
                            'awayPS': None,
                            'spread': None,
                            'total': None,
                            'overOdds': None,
                            'underOdds': None
                        }

                    if bet_type == 'moneyline':
                        opener_dict[game_id]['homeML'] = opener_line.get('homeOdds')
                        opener_dict[game_id]['awayML'] = opener_line.get('awayOdds')
                    elif bet_type == 'pointspread':
                        opener_dict[game_id]['homePS'] = opener_line.get('homeOdds')
                        opener_dict[game_id]['awayPS'] = opener_line.get('awayOdds')
                        opener_dict[game_id]['spread'] = opener_line.get('homeSpread')
                    elif bet_type == 'totals':
                        opener_dict[game_id]['total'] = opener_line.get('total')
                        opener_dict[game_id]['overOdds'] = opener_line.get('overOdds')
                        opener_dict[game_id]['underOdds'] = opener_line.get('underOdds')

    # --- Add opener rows ---
    for game_id, vals in opener_dict.items():
        gameView = next(iter([v for k, v in games_dict.items() if k[0]==game_id]), None)
        if gameView:
            opener_row = {
                'gameId': game_id,
                'homeTeam': gameView['homeTeam'],
                'awayTeam': gameView['awayTeam'],
                'startTime': gameView['startTime'],
                'sportsbook': 'OPENER'
            }
            opener_row.update(vals)
            games_dict[(game_id, 'OPENER')] = opener_row

    
    return pd.DataFrame(list(games_dict.values()))


# %%
# Select sportsbook to use for odds
def select_odds(odds_df, team_dict, sportsbook="draftkings"):
    df = odds_df.copy()

    # Filter sportsbook
    df = df[df['sportsbook'] == sportsbook].copy()

    # Map team names
    df['VisitorTeamShort'] = df['awayTeam'].map(team_dict)
    df['HomeTeamShort'] = df['homeTeam'].map(team_dict)

    # Spread (home spread, matches your old logic)
    df['Spread'] = df['spread']

    # Totals
    df['OU'] = df['total']

    # Spread odds
    df['SpreadMoney1'] = df['awayPS']   # visitor spread odds
    df['SpreadMoney2'] = df['homePS']   # home spread odds

    # Totals odds
    df['OuMoney1'] = df['overOdds']
    df['OuMoney2'] = df['underOdds']

    # Moneyline odds
    df['MLMoney1'] = df['awayML']
    df['MLMoney2'] = df['homeML']

    # Event time
    df['EventDateTime'] = pd.to_datetime(df['startTime']).dt.tz_localize(None)

    # Vegas runs (leave blank as requested)
    df['VisitorVegasRuns'] = ""
    df['HomeVegasRuns'] = ""

    # Final column order
    df = df[
        [
            'VisitorTeamShort', 'HomeTeamShort',
            'Spread', 'OU',
            'SpreadMoney1', 'SpreadMoney2',
            'OuMoney1', 'OuMoney2',
            'MLMoney1', 'MLMoney2',
            'VisitorVegasRuns', 'HomeVegasRuns',
            'EventDateTime', 'date'
        ]
    ]

    return df
    

# %%
__all__ = [name for name in globals() if not name.startswith("_")]