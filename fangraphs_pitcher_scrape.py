import requests
import brotli  # You may need to install this: pip install brotli
import os
import pandas as pd  # Add pandas import
import json

def scrape_fangraphs_pitcher_data(season="2025"):
    """
    Scrape pitcher data from Fangraphs.
    
    Args:
        season (str): Season year
    
    Returns:
        pandas.DataFrame or None: The scraped data as DataFrame, or None if the request failed
    """
    # Set default values for removed parameters
    start_date = f"{season}-03-01"
    end_date = f"{season}-11-01"
    position = "all"
    league = "all"
    qualified = "y"
    team = "0"
    sort_stat = "WAR"
    verbose = False
    
    url = "https://www.fangraphs.com/api/leaders/major-league/data"
    params = {
        "age": "",
        "pos": position,
        "stats": "pit",
        "lg": league,
        "qual": qualified,
        "season": season,
        "season1": season,
        "startdate": start_date,
        "enddate": end_date,
        "month": "0",
        "hand": "",
        "team": team,
        "pageitems": "2000000000",
        "pagenum": "1",
        "ind": "0",
        "rost": "0",
        "players": "",
        "type": "8",
        "postseason": "",
        "sortdir": "default",
        "sortstat": sort_stat,
        "download": "1"
    }

    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1.1 Safari/605.1.15",
        "Referer": "https://www.fangraphs.com/leaders/major-league?pos=all&stats=pit&lg=all&qual=y&type=8&season=2023&month=0&season1=2023&ind=0&pagenum=1&pageitems=2000000000",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",  # Removed 'br' to avoid Brotli compression
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Cookie": "fg_is_member=true; _ga_757YGY2LKP=GS1.1.1743699031.25.1.1743699622.0.0.0; _ga=GA1.1.992374810.1740781484; fg_feature_flag=failed; wordpress_logged_in_0cae6f5cb929d209043cb97f8c2eee44=jackrwerner%7C1772338413%7CX3gZHV1jY5mjMTso0Oxp4O8dIJxld1KpCEtiWs12nfc%7C3e41998c235e105b1814269c3e6c559514f16ad754ef8a64a97752d342661f82; usprivacy=1N--; __qca=P0-895368166-1740781483756; _sharedid=7e119dbe-ee25-4ff1-a9ac-6f9b71aedc2d; _sharedid_cst=VyxHLMwsHQ%3D%3D; fg_uuid=4b9803c8-526f-40a9-9bce-f5f9654d4630"
    }

    if verbose:
        print("Sending request without Brotli compression...")
    response = requests.get(url, headers=headers, params=params)

    if verbose:
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Content length: {len(response.content)}")

    df = None  # Initialize DataFrame

    # Check for compression type
    if 'content-encoding' in response.headers:
        encoding = response.headers['content-encoding']
        if verbose:
            print(f"Response is compressed with: {encoding}")
        
        # If still getting brotli despite our request
        if encoding == 'br':
            try:
                # Save the compressed data for debugging if needed
                if verbose:
                    with open("compressed_data.br", "wb") as f:
                        f.write(response.content)
                    print("Saved compressed data to compressed_data.br")
                
                # Try to decompress with brotli
                try:
                    decompressed_content = brotli.decompress(response.content)
                    if verbose:
                        print(f"Decompressed content length: {len(decompressed_content)}")
                        print("First 500 characters of decompressed response:")
                        print(decompressed_content[:500].decode('utf-8', errors='replace'))
                    
                    # Parse the decompressed JSON
                    data = decompressed_content.decode('utf-8', errors='replace')
                    json_data = requests.models.json.loads(data)
                    
                    if verbose:
                        print("JSON data successfully parsed")
                        print(f"Number of records: {len(json_data) if isinstance(json_data, list) else 'N/A'}")
                    
                    # Convert to DataFrame if applicable
                    if isinstance(json_data, dict) and 'data' in json_data and isinstance(json_data['data'], list):
                        df = pd.DataFrame(json_data['data'])
                    elif isinstance(json_data, list):
                        df = pd.DataFrame(json_data)
                    
                except brotli.error as e:
                    if verbose:
                        print(f"Brotli decompression error: {e}")
                        print("Trying an alternative way to request the data...")
                    
                    # Try to use a different URL or approach
                    csv_url = f"https://www.fangraphs.com/leaders/major-league/data?pos={position}&stats=pit&lg={league}&qual={qualified}&type=8&season={season}&month=0&season1={season}&ind=0&team={team}&rost=0&age=0&filter=&players=0&startdate={start_date}&enddate={end_date}&sort=4,d"
                    
                    if verbose:
                        print(f"Trying to fetch data as CSV instead from: {csv_url}")
                    csv_headers = headers.copy()
                    csv_headers["Accept"] = "text/csv"
                    
                    csv_response = requests.get(csv_url, headers=csv_headers)
                    if verbose:
                        print(f"CSV response status: {csv_response.status_code}")
                    if csv_response.ok:
                        if verbose:
                            print("First 500 characters of CSV response:")
                            print(csv_response.text[:500])
                        
                        df = pd.read_csv("temp_fangraphs_data.csv")
                        if os.path.exists("temp_fangraphs_data.csv"):
                            os.remove("temp_fangraphs_data.csv")
            except Exception as e:
                if verbose:
                    print(f"Error processing compressed data: {e}")
                return None
        else:
            # Handle other compression types (gzip, deflate)
            try:
                if verbose:
                    print("First 500 characters of response:")
                    print(response.text[:500])
                
                if response.ok:
                    data = response.json()
                    if verbose:
                        print("JSON data successfully parsed")
                    
                    # Check if data is a dictionary with a 'data' key containing the records
                    if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                        if verbose:
                            print(f"Number of records: {len(data['data'])}")
                            print(f"First record preview: {data['data'][0]['Name'] if data['data'] else 'No data'}")
                        
                        # Convert to DataFrame
                        df = pd.DataFrame(data['data'])
                        if verbose:
                            print(f"DataFrame shape: {df.shape}")
                            print("DataFrame columns:")
                            print(df.columns.tolist())
                    else:
                        if verbose:
                            print(f"Number of records: N/A (unexpected data structure)")
                    
            except requests.exceptions.JSONDecodeError as e:
                if verbose:
                    print(f"JSON decode error: {e}")
                    print("The response doesn't contain valid JSON data.")
                return None
    else:
        # Handle uncompressed responses
        try:
            if verbose:
                print("First 500 characters of response:")
                print(response.text[:500])
            
            if response.ok:
                data = response.json()
                if verbose:
                    print("JSON data successfully parsed")
                
                # Check if data is a dictionary with a 'data' key containing the records
                if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                    if verbose:
                        print(f"Number of records: {len(data['data'])}")
                        print(f"First record preview: {data['data'][0]['Name'] if data['data'] else 'No data'}")
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(data['data'])
                    if verbose:
                        print(f"DataFrame shape: {df.shape}")
                        print("DataFrame columns:")
                        print(df.columns.tolist())
                else:
                    if verbose:
                        print(f"Number of records: N/A (unexpected data structure)")
                
        except requests.exceptions.JSONDecodeError as e:
            if verbose:
                print(f"JSON decode error: {e}")
                print("The response doesn't contain valid JSON data.")
            return None
        
    return df

# Example usage
if __name__ == "__main__":
    # This code will only run when the script is executed directly, not when imported
    df = scrape_fangraphs_pitcher_data(season="2025")
    
    if df is not None:
        print(f"Successfully retrieved {len(df)} pitcher records")
    else:
        print("Failed to retrieve data")
