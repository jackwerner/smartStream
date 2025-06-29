import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_ac_data():
    """Load all data files from ac_data folder and combine them"""
    ac_data_path = Path('ac_data')
    
    all_data = []
    
    # Get all CSV files in the ac_data folder
    csv_files = sorted(ac_data_path.glob('*.csv'))
    
    for file in csv_files:
        try:
            # Extract date from filename
            date_str = file.stem.split('_')[0]
            player_type = 'batter' if 'batters' in file.name else 'pitcher'
            
            # Load the data
            df = pd.read_csv(file)
            df['date'] = pd.to_datetime(date_str)
            df['player_type'] = player_type
            
            all_data.append(df)
            print(f"Loaded {file.name}: {len(df)} records")
            
        except Exception as e:
            print(f"Error loading {file.name}: {e}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        print(f"\nTotal combined records: {len(combined_df)}")
        return combined_df
    else:
        print("No data loaded!")
        return None

def clean_player_names(df):
    """Clean and standardize player names"""
    # Extract clean name from the HTML-style Name column
    df['clean_name'] = df['Name'].str.extract(r'>([^<]+)<')
    
    # Use PlayerName as backup if clean_name extraction fails
    df['clean_name'] = df['clean_name'].fillna(df['PlayerName'])
    
    return df

def calculate_changes(df):
    """Calculate changes from first date to most recent date for each player"""
    df = clean_player_names(df)
    
    # Sort by player and date
    df = df.sort_values(['clean_name', 'player_type', 'date'])
    
    # Calculate changes for each player
    changes = []
    
    for (name, ptype), group in df.groupby(['clean_name', 'player_type']):
        if len(group) < 2:
            continue
            
        group = group.sort_values('date')
        
        # Get first and last records
        first_row = group.iloc[0]
        last_row = group.iloc[-1]
        
        # Skip if same date (no change period)
        if first_row['date'] == last_row['date']:
            continue
            
        pa_change = last_row['PA'] - first_row['PA']
        pts_change = last_row['PTS'] - first_row['PTS']
        
        # Calculate percentage changes
        pa_pct_change = (pa_change / first_row['PA'] * 100) if first_row['PA'] > 0 else 0
        pts_pct_change = (pts_change / first_row['PTS'] * 100) if first_row['PTS'] > 0 else 0
        
        # Calculate PTS change rate relative to PA change
        pts_per_pa_change = pts_change / pa_change if pa_change != 0 else 0
        
        # Calculate days between measurements
        days_diff = (last_row['date'] - first_row['date']).days
        
        change_record = {
            'player_name': name,
            'player_type': ptype,
            'first_date': first_row['date'],
            'last_date': last_row['date'],
            'days_tracked': days_diff,
            'first_PA': first_row['PA'],
            'last_PA': last_row['PA'],
            'first_PTS': first_row['PTS'],
            'last_PTS': last_row['PTS'],
            'pa_change': pa_change,
            'pts_change': pts_change,
            'pa_pct_change': pa_pct_change,
            'pts_pct_change': pts_pct_change,
            'pts_per_pa_change': pts_per_pa_change,
            'pa_change_per_day': pa_change / days_diff if days_diff > 0 else 0,
            'pts_change_per_day': pts_change / days_diff if days_diff > 0 else 0,
            'team': last_row['Team'],
            'position': last_row.get('POS', last_row.get('aPOS', ''))
        }
        
        changes.append(change_record)
    
    return pd.DataFrame(changes)

def identify_anomalies(changes_df):
    """Identify the three types of anomalies"""
    
    # 1. Major changes in projected PA (>= 15% change or >= 30 PA change)
    # Using higher thresholds since we're looking at total period changes
    major_pa_changes = changes_df[
        (abs(changes_df['pa_pct_change']) >= 15) | 
        (abs(changes_df['pa_change']) >= 30)
    ].copy()
    major_pa_changes['anomaly_type'] = 'Major PA Change'
    
    # 2. Major changes in PTS without significant PA change 
    # (PTS change >= 10% but PA change < 8%)
    pts_only_changes = changes_df[
        (abs(changes_df['pts_pct_change']) >= 10) & 
        (abs(changes_df['pa_pct_change']) < 8)
    ].copy()
    pts_only_changes['anomaly_type'] = 'PTS Change Without PA Change'
    
    # 3. Unusual PTS drop rate compared to PA change
    # Find cases where PTS drops much faster than expected given PA change
    # We'll look for cases where PTS drops more than 1.5x what you'd expect from PA alone
    
    # First, establish baseline PTS/PA ratios for each player type
    # Filter to only cases where both are declining (normal seasonal pattern)
    declining_cases = changes_df[
        (changes_df['pa_change'] < 0) & 
        (changes_df['pts_change'] < 0)
    ]
    
    if not declining_cases.empty:
        batter_baseline = declining_cases[declining_cases['player_type'] == 'batter']['pts_per_pa_change'].median()
        pitcher_baseline = declining_cases[declining_cases['player_type'] == 'pitcher']['pts_per_pa_change'].median()
        
        unusual_pts_drops = []
        for _, row in declining_cases.iterrows():
            baseline = batter_baseline if row['player_type'] == 'batter' else pitcher_baseline
            expected_pts_change = row['pa_change'] * baseline
            
            # If actual PTS drop is more than 1.5x expected drop (more conservative for period analysis)
            if abs(row['pts_change']) > abs(expected_pts_change * 1.5):
                unusual_pts_drops.append(row)
        
        if unusual_pts_drops:
            unusual_drops_df = pd.DataFrame(unusual_pts_drops)
            unusual_drops_df['anomaly_type'] = 'Unusual PTS Drop Rate'
        else:
            unusual_drops_df = pd.DataFrame()
    else:
        unusual_drops_df = pd.DataFrame()
    
    # Combine all anomalies
    all_anomalies = []
    if not major_pa_changes.empty:
        all_anomalies.append(major_pa_changes)
    if not pts_only_changes.empty:
        all_anomalies.append(pts_only_changes)
    if not unusual_drops_df.empty:
        all_anomalies.append(unusual_drops_df)
    
    if all_anomalies:
        return pd.concat(all_anomalies, ignore_index=True)
    else:
        return pd.DataFrame()

def create_summary_report(anomalies_df, changes_df):
    """Create a summary report of all anomalies"""
    print("=" * 80)
    print("SMART STREAM PROJECTION CHANGE REPORT")
    print("First Date to Most Recent Analysis")
    print("=" * 80)
    
    if not changes_df.empty:
        min_date = changes_df['first_date'].min().strftime('%Y-%m-%d')
        max_date = changes_df['last_date'].max().strftime('%Y-%m-%d')
        print(f"Analysis Period: {min_date} to {max_date}")
        print(f"Total Players Analyzed: {len(changes_df)}")
        print()
    
    if anomalies_df.empty:
        print("No significant anomalies detected in the data.")
        return
    
    # Group by anomaly type
    for anomaly_type, group in anomalies_df.groupby('anomaly_type'):
        print(f"\n{anomaly_type.upper()}:")
        print("-" * 50)
        
        # Sort by magnitude of change
        if 'PA' in anomaly_type:
            group = group.reindex(group['pa_pct_change'].abs().sort_values(ascending=False).index)
        else:
            group = group.reindex(group['pts_pct_change'].abs().sort_values(ascending=False).index)
        
        for _, row in group.head(15).iterrows():  # Show top 15
            first_date = row['first_date'].strftime('%Y-%m-%d')
            last_date = row['last_date'].strftime('%Y-%m-%d')
            print(f"  {row['player_name']} ({row['team']}) - {first_date} to {last_date}")
            print(f"    PA: {row['first_PA']:.0f} → {row['last_PA']:.0f} "
                  f"({row['pa_change']:+.0f}, {row['pa_pct_change']:+.1f}%)")
            print(f"    PTS: {row['first_PTS']:.1f} → {row['last_PTS']:.1f} "
                  f"({row['pts_change']:+.1f}, {row['pts_pct_change']:+.1f}%)")
            print(f"    Days Tracked: {row['days_tracked']}")
            print()

def create_visualizations(changes_df, anomalies_df):
    """Create visualizations of the changes and anomalies"""
    
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Smart Stream Projection Changes Analysis\n(First Date to Most Recent)', 
                 fontsize=16, fontweight='bold')
    
    # 1. Distribution of PA changes
    axes[0, 0].hist(changes_df['pa_change'], bins=50, alpha=0.7, edgecolor='black')
    axes[0, 0].axvline(0, color='red', linestyle='--', alpha=0.7)
    axes[0, 0].set_xlabel('Total PA Change')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Distribution of PA Changes')
    
    # 2. Distribution of PTS changes
    axes[0, 1].hist(changes_df['pts_change'], bins=50, alpha=0.7, edgecolor='black')
    axes[0, 1].axvline(0, color='red', linestyle='--', alpha=0.7)
    axes[0, 1].set_xlabel('Total PTS Change')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Distribution of PTS Changes')
    
    # 3. PA vs PTS change relationship
    scatter_alpha = 0.6 if len(changes_df) > 1000 else 0.8
    colors = ['blue' if ptype == 'batter' else 'red' for ptype in changes_df['player_type']]
    axes[0, 2].scatter(changes_df['pa_change'], changes_df['pts_change'], 
                      alpha=scatter_alpha, s=20, c=colors)
    axes[0, 2].axhline(0, color='red', linestyle='--', alpha=0.7)
    axes[0, 2].axvline(0, color='red', linestyle='--', alpha=0.7)
    axes[0, 2].set_xlabel('Total PA Change')
    axes[0, 2].set_ylabel('Total PTS Change')
    axes[0, 2].set_title('PA vs PTS Change Relationship\n(Blue=Batters, Red=Pitchers)')
    
    # 4. Anomalies by type (if any exist)
    if not anomalies_df.empty:
        anomaly_counts = anomalies_df['anomaly_type'].value_counts()
        bars = axes[1, 0].bar(range(len(anomaly_counts)), anomaly_counts.values)
        axes[1, 0].set_xticks(range(len(anomaly_counts)))
        axes[1, 0].set_xticklabels(anomaly_counts.index, rotation=45, ha='right')
        axes[1, 0].set_ylabel('Count')
        axes[1, 0].set_title('Anomalies by Type')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            axes[1, 0].text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}', ha='center', va='bottom')
    else:
        axes[1, 0].text(0.5, 0.5, 'No Anomalies\nDetected', 
                       ha='center', va='center', transform=axes[1, 0].transAxes,
                       fontsize=14)
        axes[1, 0].set_title('Anomalies by Type')
    
    # 5. PA Change by Player Type
    if 'player_type' in changes_df.columns:
        batter_changes = changes_df[changes_df['player_type'] == 'batter']['pa_change']
        pitcher_changes = changes_df[changes_df['player_type'] == 'pitcher']['pa_change']
        
        axes[1, 1].hist([batter_changes, pitcher_changes], 
                       bins=30, alpha=0.7, label=['Batters', 'Pitchers'], 
                       edgecolor='black')
        axes[1, 1].axvline(0, color='red', linestyle='--', alpha=0.7)
        axes[1, 1].set_xlabel('Total PA Change')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].set_title('PA Changes by Player Type')
        axes[1, 1].legend()
    
    # 6. PTS Change by Player Type
    if 'player_type' in changes_df.columns:
        batter_pts = changes_df[changes_df['player_type'] == 'batter']['pts_change']
        pitcher_pts = changes_df[changes_df['player_type'] == 'pitcher']['pts_change']
        
        axes[1, 2].hist([batter_pts, pitcher_pts], 
                       bins=30, alpha=0.7, label=['Batters', 'Pitchers'], 
                       edgecolor='black')
        axes[1, 2].axvline(0, color='red', linestyle='--', alpha=0.7)
        axes[1, 2].set_xlabel('Total PTS Change')
        axes[1, 2].set_ylabel('Frequency')
        axes[1, 2].set_title('PTS Changes by Player Type')
        axes[1, 2].legend()
    
    plt.tight_layout()
    plt.savefig('ac_projection_changes_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

def save_detailed_report(anomalies_df, changes_df):
    """Save detailed reports to CSV files"""
    
    # Save anomalies
    if not anomalies_df.empty:
        anomalies_df.to_csv('projection_anomalies.csv', index=False)
        print(f"Saved {len(anomalies_df)} anomalies to 'projection_anomalies.csv'")
    
    # Save all changes
    changes_df.to_csv('all_projection_changes.csv', index=False)
    print(f"Saved {len(changes_df)} total changes to 'all_projection_changes.csv'")
    
    # Create summary statistics
    summary_stats = {
        'Metric': ['Total Players', 'Total Anomalies', 'Avg PA Change', 'Avg PTS Change',
                  'Max PA Increase', 'Max PA Decrease', 'Max PTS Increase', 'Max PTS Decrease',
                  'Avg Days Tracked', 'Players with PA Increases', 'Players with PTS Increases'],
        'Value': [
            len(changes_df),
            len(anomalies_df) if not anomalies_df.empty else 0,
            changes_df['pa_change'].mean(),
            changes_df['pts_change'].mean(),
            changes_df['pa_change'].max(),
            changes_df['pa_change'].min(),
            changes_df['pts_change'].max(),
            changes_df['pts_change'].min(),
            changes_df['days_tracked'].mean(),
            (changes_df['pa_change'] > 0).sum(),
            (changes_df['pts_change'] > 0).sum()
        ]
    }
    
    summary_df = pd.DataFrame(summary_stats)
    summary_df.to_csv('projection_summary_stats.csv', index=False)
    print("Saved summary statistics to 'projection_summary_stats.csv'")

def main():
    """Main function to run the analysis"""
    print("Smart Stream Projection Change Analysis")
    print("First Date to Most Recent Analysis")
    print("=" * 50)
    
    # Load data
    print("\n1. Loading data...")
    df = load_ac_data()
    
    if df is None or df.empty:
        print("No data to analyze!")
        return
    
    # Calculate changes
    print("\n2. Calculating first-to-last changes...")
    changes_df = calculate_changes(df)
    
    if changes_df.empty:
        print("No changes detected!")
        return
    
    print(f"Found {len(changes_df)} players with trackable changes")
    
    # Identify anomalies
    print("\n3. Identifying anomalies...")
    anomalies_df = identify_anomalies(changes_df)
    
    if not anomalies_df.empty:
        print(f"Found {len(anomalies_df)} anomalies")
    else:
        print("No significant anomalies detected")
    
    # Create reports
    print("\n4. Generating reports...")
    create_summary_report(anomalies_df, changes_df)
    
    # Create visualizations
    print("\n5. Creating visualizations...")
    create_visualizations(changes_df, anomalies_df)
    
    # Save detailed reports
    print("\n6. Saving detailed reports...")
    save_detailed_report(anomalies_df, changes_df)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main()
