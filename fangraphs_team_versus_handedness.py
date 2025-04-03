import requests
import pandas as pd
import time


class FangraphsTeamVersusHandednessScraper:
    """Scraper for retrieving team statistics versus LHP and RHP from Fangraphs."""

    BASE_URL = "https://www.fangraphs.com/api/leaders/major-league/data"
    HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Dest": "empty",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Mode": "cors",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15",
        "Referer": "https://www.fangraphs.com/leaders/major-league"
    }
    
    # Month parameter values for splits
    VS_LHP_MONTH = 13  # vs LHP split
    VS_RHP_MONTH = 14  # vs RHP split
    
    def __init__(self, cookies=None):
        """
        Initialize the scraper.
        
        Args:
            cookies (dict, optional): Cookies for authenticated requests
        """
        self.cookies = cookies or {}
    
    def get_team_stats_vs_handedness(self, season=2025, handedness=None):
        """
        Get team statistics versus specified pitcher handedness.
        
        Args:
            season (int): The season to get data for
            handedness (str, optional): 'L' for vs LHP, 'R' for vs RHP, None for both
            
        Returns:
            dict: Dictionary with keys 'vs_lhp' and 'vs_rhp' containing pandas DataFrames
        """
        result = {}
        
        if handedness is None or handedness.upper() == 'L':
            lhp_data = self._fetch_data(season, self.VS_LHP_MONTH)
            result['vs_lhp'] = self._process_data(lhp_data)
        
        if handedness is None or handedness.upper() == 'R':
            rhp_data = self._fetch_data(season, self.VS_RHP_MONTH)
            result['vs_rhp'] = self._process_data(rhp_data)
        
        return result
    
    def _fetch_data(self, season, month):
        """
        Fetch data from Fangraphs API.
        
        Args:
            season (int): Season to retrieve data for
            month (int): Month parameter value (13 for vs LHP, 14 for vs RHP)
            
        Returns:
            dict: JSON response from API
        """
        params = {
            "pos": "all",
            "stats": "bat",
            "lg": "all",
            "qual": "y",
            "season": str(season),
            "season1": str(season),
            "startdate": f"{season}-03-01",
            "enddate": f"{season}-11-01",
            "month": str(month),
            "team": "0,ts",  # Team splits
            "pageitems": "30",
            "pagenum": "1",
            "ind": "0",
            "rost": "0",
            "type": "8",
            "sortdir": "default",
            "sortstat": "WAR"
        }
        
        response = requests.get(
            self.BASE_URL,
            params=params,
            headers=self.HEADERS,
            cookies=self.cookies
        )
        
        response.raise_for_status()
        return response.json()
    
    def _process_data(self, json_data):
        """
        Process JSON data into a pandas DataFrame.
        
        Args:
            json_data (dict): JSON response from API
            
        Returns:
            pandas.DataFrame: Processed data
        """
        if not json_data.get('data'):
            return pd.DataFrame()
        
        df = pd.DataFrame(json_data['data'])
        return df


if __name__ == "__main__":
    # Example usage
    scraper = FangraphsTeamVersusHandednessScraper()
    
    # Optional: Add your cookies for authenticated requests
    # cookies = {
    #     "fg_is_member": "true",
    #     "wordpress_logged_in_0cae6f5cb929d209043cb97f8c2eee44": "your_cookie_value"
    # }
    # scraper = FangraphsTeamVersusHandednessScraper(cookies=cookies)
    
    # Get data for both handedness
    data = scraper.get_team_stats_vs_handedness(season=2025)
    
    # Print the results
    print("Teams vs LHP:")
    if 'vs_lhp' in data and not data['vs_lhp'].empty:
        print(data['vs_lhp'][['TeamName', 'PA', 'AVG', 'OBP', 'SLG', 'wOBA', 'wRC+']].head())
    else:
        print("No data available")
    
    print("\nTeams vs RHP:")
    if 'vs_rhp' in data and not data['vs_rhp'].empty:
        print(data['vs_rhp'][['TeamName', 'PA', 'AVG', 'OBP', 'SLG', 'wOBA', 'wRC+']].head())
    else:
        print("No data available")
