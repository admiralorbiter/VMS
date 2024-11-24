import csv

def split_volunteers():
    # First, load the fixed volunteers into a dictionary using ID as key
    fixed_volunteers = {}
    try:
        with open('data-scripts/Volunteers-fixed.csv', 'r', encoding='latin-1') as fixed_file:
            fixed_reader = csv.DictReader(fixed_file)
            for row in fixed_reader:
                fixed_volunteers[row['Id']] = row
    except FileNotFoundError:
        print("Warning: Volunteers-fixed.csv not found. Proceeding with original data only.")
    
    # Open the input and output files using latin-1 encoding
    with open('data-scripts/Contact.csv', 'r', encoding='latin-1') as input_file, \
         open('data-scripts/Volunteers.csv', 'w', encoding='latin-1', newline='') as output_file:
        
        # Create CSV reader and writer
        reader = csv.reader(input_file)
        writer = csv.writer(output_file)
        
        # Write header row
        header = next(reader)
        writer.writerow(header)
        
        # Filter and write volunteer rows
        for row in reader:
            # Look for "Volunteer" in the role/type field
            if "Volunteer" in row:
                # Check if we have fixed data for this volunteer
                volunteer_id = row[0]  # Assuming ID is the first column
                if volunteer_id in fixed_volunteers:
                    # Use the fixed data, maintaining the original CSV structure
                    fixed_data = fixed_volunteers[volunteer_id]
                    fixed_row = [fixed_data.get(h, '') for h in header]
                    writer.writerow(fixed_row)
                else:
                    # Use the original data
                    writer.writerow(row)

if __name__ == "__main__":
    split_volunteers() 