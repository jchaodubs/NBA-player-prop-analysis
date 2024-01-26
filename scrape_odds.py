import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re


def combine_prop_with_odds(row, prop_col, odds_col):
        prop_value = row[prop_col]
        odds_value = row[odds_col]
        if pd.isna(odds_value) or odds_value == 'NaN':
            return '-'
        else:
            return f"{prop_value} ({odds_value})"

# URL of the webpage to scrape
url = 'https://www.rotowire.com/betting/nba/player-props.php'
response = requests.get(url)

# List to hold each DataFrame
dfs = []

if response.status_code == 200:
    soup = BeautifulSoup(response.content, 'html.parser')
    script_tags = soup.find_all('script', text=re.compile('rwjs:ready'))

    for script in script_tags:
        js_code = script.string
        json_like_object = re.search(r'data: (\[.*\])', js_code)
        if json_like_object:
            json_str = json_like_object.group(1)
            # Convert JSON string to DataFrame
            data = json.loads(json_str)
            df = pd.DataFrame(data)
            dfs.append(df)

    # Concatenate all DataFrames
    master_df = pd.concat(dfs, ignore_index=True)
    master_df['PlayerName'] = master_df['firstName'] + ' ' + master_df['lastName']
    master_df.drop(['firstName', 'lastName'], axis =1, inplace = True)

    sportsbooks = ['draftkings', 'fanduel', 'mgm', 'pointsbet']
    props = ['pts', 'reb', 'ast', 'ptsrebast', 'ptsreb', 'ptsast', 'rebast']

    # Flatten each prop for each sportsbook into separate DataFrames
    flattened_dfs = []
    for prop in props:
        for sportsbook in sportsbooks:
            # Create a DataFrame for each prop and sportsbook
            cols = [f'{sportsbook}_{prop}Under', f'{sportsbook}_{prop}Over']
            temp_df = master_df[['PlayerName', 'team', 'opp'] + cols].copy()
            temp_df['Prop'] = prop
            temp_df['Sportsbook'] = sportsbook
            temp_df = temp_df.melt(id_vars=['PlayerName', 'team', 'opp', 'Prop', 'Sportsbook'], 
                                value_vars=cols, 
                                var_name='Over_Under', 
                                value_name='Odds')
            # Clean the Over_Under column
            temp_df['Over_Under'] = temp_df['Over_Under'].apply(lambda x: 'Over' if 'Over' in x else 'Under')
            flattened_dfs.append(temp_df)

    # Step 2: Create a Unified Prop Column
    consolidated_df = pd.concat(flattened_dfs)

    # Step 3: Consolidate Sportsbook Odds
    # This step may require further clarification. If you want to have one row per player per prop with a column for each sportsbook's odds, you'll need to pivot the table
    pivot_df = consolidated_df.pivot_table(index=['PlayerName', 'team', 'opp', 'Prop', 'Over_Under'], 
                                        columns='Sportsbook', 
                                        values='Odds', 
                                        aggfunc='first').reset_index()

    prop_mapping = {
        'pts': 'Points',
        'reb': 'Rebounds',
        'ast': 'Assists',
        'ptsast': 'Pts+Asts',
        'ptsreb': 'Pts+Rebs',
        'ptsrebast': 'Pts+Rebs+Asts',
        'rebast': 'Rebs+Asts'
    }

    # Step 2: Apply the Mapping
    pivot_df['Prop'] = pivot_df['Prop'].replace(prop_mapping)
    pivot_df.drop(['team'], axis = 1, inplace = True)
    pivot_df.reset_index(drop=True, inplace=True)
    pivot_df.to_csv('over_under_odds.csv', index = False)