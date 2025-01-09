import csv

def split_students():
    # First, load the fixed students into a dictionary using ID as key
    fixed_students = {}
    try:
        with open('data-scripts/Students-fixed.csv', 'r', encoding='latin-1') as fixed_file:
            fixed_reader = csv.DictReader(fixed_file)
            for row in fixed_reader:
                fixed_students[row['Id']] = row
    except FileNotFoundError:
        print("Warning: Students-fixed.csv not found. Proceeding with original data only.")
    
    # Open the input and output files using latin-1 encoding
    with open('data-scripts/Contact.csv', 'r', encoding='latin-1') as input_file, \
         open('data-scripts/Students.csv', 'w', encoding='latin-1', newline='') as output_file:
        
        # Create CSV reader and writer
        reader = csv.reader(input_file)
        writer = csv.writer(output_file)
        
        # Write header row
        header = next(reader)
        writer.writerow(header)
        
        # Filter and write student rows
        for row in reader:
            # Look for "Student" in the role/type field
            if "Student" in row:
                # Check if we have fixed data for this student
                student_id = row[0]  # Assuming ID is the first column
                if student_id in fixed_students:
                    # Use the fixed data, maintaining the original CSV structure
                    fixed_data = fixed_students[student_id]
                    fixed_row = [fixed_data.get(h, '') for h in header]
                    writer.writerow(fixed_row)
                else:
                    # Use the original data
                    writer.writerow(row)

if __name__ == "__main__":
    split_students() 