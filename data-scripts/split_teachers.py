import csv

def split_teachers():
    # First, load the fixed teachers into a dictionary using ID as key
    fixed_teachers = {}
    try:
        with open('data-scripts/Teachers-fixed.csv', 'r', encoding='latin-1') as fixed_file:
            fixed_reader = csv.DictReader(fixed_file)
            for row in fixed_reader:
                fixed_teachers[row['Id']] = row
    except FileNotFoundError:
        print("Warning: Teachers-fixed.csv not found. Proceeding with original data only.")
    
    # Open the input and output files using latin-1 encoding
    with open('data-scripts/Contact.csv', 'r', encoding='latin-1') as input_file, \
         open('data-scripts/Teachers.csv', 'w', encoding='latin-1', newline='') as output_file:
        
        # Create CSV reader and writer
        reader = csv.reader(input_file)
        writer = csv.writer(output_file)
        
        # Write header row
        header = next(reader)
        writer.writerow(header)
        
        # Filter and write teacher rows
        for row in reader:
            # Look for "Teacher" in the role/type field
            if "Teacher" in row:
                # Check if we have fixed data for this teacher
                teacher_id = row[0]  # Assuming ID is the first column
                if teacher_id in fixed_teachers:
                    # Use the fixed data, maintaining the original CSV structure
                    fixed_data = fixed_teachers[teacher_id]
                    fixed_row = [fixed_data.get(h, '') for h in header]
                    writer.writerow(fixed_row)
                else:
                    # Use the original data
                    writer.writerow(row)

if __name__ == "__main__":
    split_teachers() 