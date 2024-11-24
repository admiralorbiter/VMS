import csv

# Input and output file paths
input_file = 'data-scripts/Session_Participant__c.csv'
output_file = 'data-scripts/Session_Participant__c - volunteers.csv'

# Read input CSV and write filtered rows to output CSV
with open(input_file, 'r', encoding='utf-8') as infile, \
     open(output_file, 'w', encoding='utf-8', newline='') as outfile:
    
    # Create CSV reader and writer
    reader = csv.reader(infile)
    writer = csv.writer(outfile)
    
    # Write header row
    header = next(reader)
    writer.writerow(header)
    
    # Filter and write volunteer rows
    for row in reader:
        # Check if Participant_Type__c (index 20) is "Volunteer"
        if row[20] == "Volunteer":
            writer.writerow(row)

print(f"Created volunteer CSV file at: {output_file}") 