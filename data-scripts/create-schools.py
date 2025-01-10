import pandas as pd

# Attempt to load the CSV file with a specified encoding
try:
    df = pd.read_csv('data-scripts/Account.csv', encoding='utf-8')
except UnicodeDecodeError:
    # If utf-8 encoding fails, try a different encoding
    df = pd.read_csv('data-scripts/Account.csv', encoding='ISO-8859-1')

# Filter for rows where Type is 'School'
schools_df = df[df['Type'] == 'School']

# Save the filtered data to a new CSV file
schools_df.to_csv('data-scripts/Schools.csv', index=False)

print("School data saved as 'Schools.csv'") 