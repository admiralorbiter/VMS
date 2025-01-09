def split_csv(input_file, rows_per_file=30000):
    print(f"Starting to split {input_file}...")
    
    # Read the header - using latin-1 encoding
    with open(input_file, 'r', encoding='latin-1') as f:
        header = f.readline()
    
    # Read and split the data
    with open(input_file, 'r', encoding='latin-1') as f:
        # Skip the header since we already read it
        next(f)
        
        file_number = 1
        current_rows = 0
        current_file = None
        
        for line in f:
            # Open a new file if needed
            if current_rows % rows_per_file == 0:
                if current_file:
                    current_file.close()
                output_file = f'Students_part{file_number}.csv'
                print(f"Creating file: {output_file}")
                current_file = open(output_file, 'w', encoding='latin-1')
                current_file.write(header)
                file_number += 1
            
            # Write the data line
            current_file.write(line)
            current_rows += 1
        
        # Close the last file
        if current_file:
            current_file.close()
    
    print(f"Finished! Created {file_number-1} files with {rows_per_file} rows each (last file may have fewer rows)")

# Use the function
split_csv('data-scripts/Students.csv')