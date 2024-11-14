import pandas as pd

# Attempt to load the CSV file with a specified encoding
try:
    df = pd.read_csv('Account.csv', encoding='utf-8')
except UnicodeDecodeError:
    # If utf-8 encoding fails, try a different encoding (e.g., ISO-8859-1)
    df = pd.read_csv('Account.csv', encoding='ISO-8859-1')

# Filter out rows where the Type column has 'Household'
filtered_df = df[df['Type'] != 'Household']

# Save the result to a new CSV file
filtered_df.to_csv('Organizations.csv', index=False)

print("Filtered file saved as 'Organizations.csv'")