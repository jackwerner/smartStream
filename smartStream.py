import csv
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode
from collections import defaultdict
import os
from fangraphs_team_versus_handedness import FangraphsTeamVersusHandednessScraper
from fangraphs_pitcher_scrape import scrape_fangraphs_pitcher_data
import json
import dotenv

dotenv.load_dotenv()

def get_games_for_week(start_date):
    base_url = "https://statsapi.mlb.com/api/v1/schedule"
    games_for_week = []
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        params = {
            "sportId": 1,
            "date": current_date.strftime("%Y-%m-%d"),
            "leagueId": "103,104",
            "hydrate": "team,linescore,flags,liveLookin,review,probablePitcher",
            "useLatestGames": "false",
            "language": "en"
        }
        full_url = f"{base_url}?{urlencode(params)}"
        response = requests.get(full_url)
        data = response.json()
        games_for_week.extend(data.get("dates", []))
    
    return games_for_week

def find_matchups(start_date):
    matchups_by_day = defaultdict(list)
    games_data = get_games_for_week(start_date)
    
    for date_data in games_data:
        date = datetime.strptime(date_data["date"], "%Y-%m-%d")
        day_name = date.strftime("%A")
        for game in date_data["games"]:
            away_team = game["teams"]["away"]["team"]["name"]
            home_team = game["teams"]["home"]["team"]["name"]
            away_pitcher = game["teams"]["away"].get("probablePitcher", {}).get("fullName", "TBD")
            home_pitcher = game["teams"]["home"].get("probablePitcher", {}).get("fullName", "TBD")
            matchups_by_day[day_name].append((away_team, home_team, away_pitcher, home_pitcher))
    
    return matchups_by_day

def get_espn_pitchers():
    url = 'https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/seasons/2025/segments/0/leagues/27130'
    params = {
        'scoringPeriodId': 18,
        'view': 'kona_player_info'
    }
    
    # Updated headers to match the actual request
    headers = {
        'Accept': 'application/json',
        'X-Fantasy-Source': 'kona',
        'X-Fantasy-Platform': 'kona-PROD-4fa5f6c941eda92739ac3bfa4c3fa99a35109148',
        'X-Fantasy-Filter': json.dumps({
            "players": {
                "filterStatus": {"value": ["FREEAGENT", "WAIVERS"]},
                "filterSlotIds": {"value": [14]},
                "filterRanksForScoringPeriodIds": {"value": [18]},
                "limit": 50,
                "offset": 0,
                "sortPercOwned": {"sortAsc": False, "sortPriority": 1},
                "sortDraftRanks": {"sortPriority": 100, "sortAsc": True, "value": "STANDARD"},
                "filterRanksForRankTypes": {"value": ["STANDARD"]},
                "filterStatsForTopScoringPeriodIds": {
                    "value": 5,
                    "additionalValue": ["002025", "102025", "002024", "012025", "022025", "032025", "042025", "062025", "010002025"]
                }
            }
        }),
        'Referer': 'https://fantasy.espn.com/',
        'Origin': 'https://fantasy.espn.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15'
    }
    
    # Method 1: Use just the essential cookies (with proper formatting)
    cookies = {
        'espn_s2': os.getenv('ESPN_S2'),
        'SWID': os.getenv('ESPN_SWID')
    }

    response = requests.get(url, params=params, headers=headers, cookies=cookies)
    
    if response.status_code != 200:
        print(f"ESPN API request failed with status code: {response.status_code}")
        print(f"Response: {response.text[:500]}...")
        return []
        
    data = response.json()
    if 'players' not in data:
        print(f"API response missing 'players' key. Response: {str(response.text)[:500]}...")
        return []
        
    print(f"Found {len(data.get('players', []))} players in API response")

    pitchers = []
    for player_data in data.get('players', []):
        player = player_data.get('player', {})
        team_id = player.get('proTeamId')
        full_name = player.get('fullName')
        
        if team_id and full_name:
            team_name = get_team_name(team_id)
            pitchers.append((full_name, team_name))

    return pitchers

def get_team_name(team_id):
    team_map = {
        1: "Baltimore Orioles", 2: "Boston Red Sox", 3: "Los Angeles Angels", 4: "Chicago White Sox", 5: "Cleveland Guardians",
        6: "Detroit Tigers", 7: "Kansas City Royals", 8: "Milwaukee Brewers", 9: "Minnesota Twins", 10: "New York Yankees",
        11: "Oakland Athletics", 12: "Seattle Mariners", 13: "Texas Rangers", 14: "Toronto Blue Jays", 15: "Atlanta Braves",
        16: "Chicago Cubs", 17: "Cincinnati Reds", 18: "Houston Astros", 19: "Los Angeles Dodgers", 20: "Washington Nationals",
        21: "New York Mets", 22: "Philadelphia Phillies", 23: "Pittsburgh Pirates", 24: "St. Louis Cardinals", 25: "San Diego Padres",
        26: "San Francisco Giants", 27: "Colorado Rockies", 28: "Miami Marlins", 29: "Arizona Diamondbacks", 30: "Tampa Bay Rays"
    }
    return team_map.get(team_id, "Unknown")

def create_team_name_mapping():
    return {
        "Los Angeles Angels": "LAA",
        "Baltimore Orioles": "BAL",
        "Boston Red Sox": "BOS",
        "Chicago White Sox": "CHW",
        "Cleveland Guardians": "CLE",
        "Detroit Tigers": "DET",
        "Kansas City Royals": "KCR",
        "Minnesota Twins": "MIN",
        "New York Yankees": "NYY",
        "Oakland Athletics": "OAK",
        "Seattle Mariners": "SEA",
        "Tampa Bay Rays": "TBR",
        "Texas Rangers": "TEX",
        "Toronto Blue Jays": "TOR",
        "Arizona Diamondbacks": "ARI",
        "Atlanta Braves": "ATL",
        "Chicago Cubs": "CHC",
        "Cincinnati Reds": "CIN",
        "Colorado Rockies": "COL",
        "Houston Astros": "HOU",
        "Los Angeles Dodgers": "LAD",
        "Miami Marlins": "MIA",
        "Milwaukee Brewers": "MIL",
        "New York Mets": "NYM",
        "Philadelphia Phillies": "PHI",
        "Pittsburgh Pirates": "PIT",
        "San Diego Padres": "SDP",
        "San Francisco Giants": "SFG",
        "St. Louis Cardinals": "STL",
        "Washington Nationals": "WSN"
    }

def main():
    # Replace CSV file loading with direct Fangraphs data fetching
    handedness_scraper = FangraphsTeamVersusHandednessScraper()

    team_stats = handedness_scraper.get_team_stats_vs_handedness(season=2025)
    lhp_stats = team_stats['vs_lhp']
    rhp_stats = team_stats['vs_rhp']
    
    # If DataFrame, convert to dictionaries using the TeamNameAbb directly
    if hasattr(lhp_stats, 'columns'):
        print("Converting DataFrames to dictionaries using TeamNameAbb...")
        
        # Create dictionaries with team abbr as key and stats as values
        lhp_stats_dict = {}
        rhp_stats_dict = {}
        
        # Check if needed columns exist
        if 'TeamNameAbb' in lhp_stats.columns and 'wRC+' in lhp_stats.columns and 'K%' in lhp_stats.columns:
            for _, row in lhp_stats.iterrows():
                team_abbr = row['TeamNameAbb']
                # Strip percentage sign and convert to float
                k_pct = float(row['K%'].rstrip('%')) if isinstance(row['K%'], str) else float(row['K%'])
                lhp_stats_dict[team_abbr] = {
                    'wRC+': float(row['wRC+']),
                    'K%': k_pct*100
                }
            
            for _, row in rhp_stats.iterrows():
                team_abbr = row['TeamNameAbb']
                # Strip percentage sign and convert to float
                k_pct = float(row['K%'].rstrip('%')) if isinstance(row['K%'], str) else float(row['K%'])
                rhp_stats_dict[team_abbr] = {
                    'wRC+': float(row['wRC+']),
                    'K%': k_pct*100
                }
            
            # Use these dictionaries instead of the original dataframes
            lhp_stats = lhp_stats_dict
            rhp_stats = rhp_stats_dict
            
        else:
            print("WARNING: Required columns not found in dataframes")
            print("LHP columns:", lhp_stats.columns.tolist())
            print("RHP columns:", rhp_stats.columns.tolist())

    # Replace pitcher handedness file loading with Fangraphs data
    pitcher_df = scrape_fangraphs_pitcher_data(season="2025")
    pitcher_handedness = {}
    
    if pitcher_df is not None and 'PlayerName' in pitcher_df.columns and 'Throws' in pitcher_df.columns:
        print(pitcher_df.columns)
        for _, row in pitcher_df.iterrows():
            pitcher_handedness[row['PlayerName']] = row['Throws']  # Throws column contains 'R' or 'L'
        print(f"Loaded handedness for {len(pitcher_handedness)} pitchers")
    else:
        print("Warning: Failed to retrieve pitcher handedness data from Fangraphs")

    team_name_mapping = create_team_name_mapping()
    print(f"Team name mapping created with {len(team_name_mapping)} teams")

    start_date = datetime.now().date()
    matchups_by_day = find_matchups(start_date)

    pitchers = get_espn_pitchers()
    espn_pitchers = {name.lower(): team for name, team in pitchers}

    with open('smartstream_results.txt', 'w') as f:
        f.write(f"Potential streaming options for the week starting {start_date.strftime('%Y-%m-%d')}:\n\n")
        for day, matchups in matchups_by_day.items():
            day_printed = False
            for away_team, home_team, away_pitcher, home_pitcher in matchups:
                available_pitchers = []
                for pitcher_name in [away_pitcher, home_pitcher]:
                    if pitcher_name != "TBD":
                        pitcher_name_lower = pitcher_name.lower()
                        matching_espn_pitchers = [name for name in espn_pitchers if pitcher_name_lower in name or name in pitcher_name_lower]
                        if matching_espn_pitchers:
                            available_pitchers.append(pitcher_name)
                
                if available_pitchers:
                    potential_streamers = []
                    for pitcher_name in available_pitchers:
                        pitcher_team = away_team if pitcher_name == away_pitcher else home_team
                        handedness = pitcher_handedness.get(pitcher_name, 'Unknown')
                        
                        if handedness == 'Unknown':
                            print(f"Handedness unknown for pitcher: {pitcher_name}")
                        
                        opponent = home_team if pitcher_name == away_pitcher else away_team
                        split_stats = lhp_stats if handedness == 'L' else rhp_stats
                        
                        opponent_abbr = team_name_mapping.get(opponent, opponent)
                        
                        opponent_stats = split_stats.get(opponent_abbr, {})
                        if not opponent_stats:
                            print(f"WARNING: Could not find stats for {opponent_abbr} in {'RHP' if handedness == 'R' else 'LHP'} stats")
                        
                        wrc_plus = opponent_stats.get('wRC+', 0)
                        k_percent = opponent_stats.get('K%', 0)

                        # Check for potential streaming option
                        if wrc_plus < 100 or k_percent > 22:
                            potential_streamers.append((pitcher_name, pitcher_team, handedness, opponent, wrc_plus, k_percent))
                    
                    if potential_streamers:
                        if not day_printed:
                            f.write(f"{day}:\n")
                            day_printed = True
                        
                        # Write game information once per game with streamers
                        f.write(f"  {away_team} @ {home_team}\n")
                        
                        for pitcher_info in potential_streamers:
                            pitcher_name, pitcher_team, handedness, opponent, wrc_plus, k_percent = pitcher_info
                            f.write(f"    • {pitcher_name} ({pitcher_team}, {handedness})\n")
                            f.write(f"      - Opponent: {opponent}\n")
                            # Fix the display of handedness
                            handedness_display = "RHP" if handedness == "R" else "LHP" if handedness == "L" else "UnknownHP"
                            f.write(f"      - Stats vs {handedness_display}: wRC+: {wrc_plus:.1f}, K%: {k_percent:.1f}%\n")
                        
                        f.write("\n")  # Add space between games
            
            if day_printed:
                f.write("\n")  # Add extra space between days

if __name__ == "__main__":
    main()