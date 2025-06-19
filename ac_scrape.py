import requests
import json
import pandas as pd
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional

class FanGraphsAuctionScraper:
    """
    A scraper for FanGraphs auction calculator data.
    """
    
    BASE_URL = "https://www.fangraphs.com/api/fantasy/auction-calculator/data"
    
    def __init__(self):
        self.session = requests.Session()
        # Set up headers to mimic a browser request
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.fangraphs.com/fantasy-tools/auction-calculator",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        })
        
        # Create ac_data directory if it doesn't exist
        self.data_dir = "ac_data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"Created directory: {self.data_dir}")
    
    def get_auction_data(self, 
                         player_type: str = "bat", 
                         teams: int = 10,
                         league: str = "MLB",
                         dollars: int = 1000,
                         min_batter: int = 1,
                         min_pitcher: int = 20,
                         min_sp: int = 5,
                         min_rp: int = 5,
                         projection: str = "ratcdc",
                         **kwargs) -> Dict[str, Any]:
        """
        Get auction calculator data from FanGraphs.
        
        Args:
            player_type: 'bat' for batters or 'pit' for pitchers
            teams: Number of teams in the league
            league: League type (MLB, AL, NL)
            dollars: Total auction dollars
            min_batter: Minimum batters
            min_pitcher: Minimum pitchers
            min_sp: Minimum starting pitchers
            min_rp: Minimum relief pitchers
            projection: Projection system to use
            **kwargs: Additional parameters for the request
            
        Returns:
            Dictionary containing the auction calculator data
        """
        params = {
            "teams": teams,
            "lg": league,
            "dollars": dollars,
            "mb": min_batter,
            "mp": min_pitcher,
            "msp": min_sp,
            "mrp": min_rp,
            "type": player_type,
            "players": "",
            "proj": projection,
            "split": "",
            "points": "c|0,1,2,3,4,7,9|0,13,2,3,4",  # Same for both batters and pitchers now
            "rep": 0,
            "drp": 0,
            "pp": "C,SS,2B,3B,OF,1B",
            "pos": "1,1,1,1,5,1,1,1,0,1,5,2,2,5,0",
            "sort": "",
            "view": 0
        }
        
        # Update with any additional parameters
        params.update(kwargs)
                
        response = self.session.get(self.BASE_URL, params=params)
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Print the keys in the response to debug the structure
            return data
        else:
            print(f"Error response content: {response.text}")
            response.raise_for_status()
    
    def save_to_csv(self, data: Dict[str, Any], filename: str) -> None:
        """
        Save the auction calculator data to a CSV file with date in the ac_data folder.
        
        Args:
            data: Dictionary containing the auction calculator data
            filename: Base name of the file to save (date will be added)
        """
        if "data" in data and isinstance(data["data"], list):
            # Add date to filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            dated_filename = f"{date_str}_{filename}"
            filepath = os.path.join(self.data_dir, dated_filename)
            
            df = pd.DataFrame(data["data"])
            # Add date as first column
            df.insert(0, 'date', date_str)
            df.to_csv(filepath, index=False)
            print(f"Data saved to {filepath} with {len(df)} rows")
        else:
            print("No data found or data is not in the expected format")
    
    def get_all_data(self, save_files: bool = True) -> Dict[str, pd.DataFrame]:
        """
        Get both batter and pitcher data from the auction calculator.
        
        Args:
            save_files: Whether to save the data to CSV files
            
        Returns:
            Dictionary containing DataFrames for batters and pitchers
        """
        print("Fetching batter data...")
        batter_data = self.get_auction_data(player_type="bat")
        time.sleep(1)  # Be nice to the server
        
        print("Fetching pitcher data...")
        pitcher_data = self.get_auction_data(player_type="pit")
        
        result = {}
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        if "data" in batter_data and isinstance(batter_data["data"], list):
            result["batters"] = pd.DataFrame(batter_data["data"])
            # Add date as first column
            result["batters"].insert(0, 'date', date_str)
            if save_files:
                batter_filename = f"{date_str}_fangraphs_batters.csv"
                batter_filepath = os.path.join(self.data_dir, batter_filename)
                result["batters"].to_csv(batter_filepath, index=False)
                print(f"Batter data saved to {batter_filepath} with {len(result['batters'])} rows")
        else:
            print("No batter data found or data is not in the expected format")
        
        if "data" in pitcher_data and isinstance(pitcher_data["data"], list):
            result["pitchers"] = pd.DataFrame(pitcher_data["data"])
            # Add date as first column
            result["pitchers"].insert(0, 'date', date_str)
            if save_files:
                pitcher_filename = f"{date_str}_fangraphs_pitchers.csv"
                pitcher_filepath = os.path.join(self.data_dir, pitcher_filename)
                result["pitchers"].to_csv(pitcher_filepath, index=False)
                print(f"Pitcher data saved to {pitcher_filepath} with {len(result['pitchers'])} rows")
        else:
            print("No pitcher data found or data is not in the expected format")
        
        return result

if __name__ == "__main__":
    scraper = FanGraphsAuctionScraper()
    
    # Add more debug information
    print("Testing direct API access...")
    try:
        # Try with explicit parameters that match the example request
        test_data = scraper.get_auction_data(
            player_type="pit",
            teams=10,
            league="MLB", 
            dollars=1000,
            min_batter=1,
            min_pitcher=20,
            min_sp=5,
            min_rp=5,
            projection="ratcdc"
        )
        
        # Print a sample of the data to verify structure
        if isinstance(test_data, dict) and "playerProjections" in test_data and test_data["playerProjections"]:
            print(f"Sample player data: {test_data['playerProjections'][0]}")
        else:
            print(f"Data structure: {type(test_data)}")
            if isinstance(test_data, dict):
                print(f"Available keys: {test_data.keys()}")
    except Exception as e:
        print(f"Error during test: {str(e)}")
    
    # Continue with the original code
    print("\nFetching all data...")
    data = scraper.get_all_data()
    print(f"Fetched {len(data.get('batters', []))} batters and {len(data.get('pitchers', []))} pitchers")
