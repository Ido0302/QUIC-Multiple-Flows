# compareFiles.py

def compare_files(file1_path, file2_path):
    """
    Compare two binary files and report if they are the same or where they differ.

    Args:
        file1_path (str): Path to the first binary file.
        file2_path (str): Path to the second binary file.

    Returns:
        bool: True if the files are identical, False if they differ.
    """
    with open(file1_path, 'rb') as file1, open(file2_path, 'rb') as file2:
        chunk_size = 4096  # Size of chunks to read from each file
        offset = 0  # Track the byte offset in the files

        while True:
            data1 = file1.read(chunk_size)
            data2 = file2.read(chunk_size)

            if not data1 and not data2:
                # Both files reached EOF and no differences found
                print("The files are identical.")
                break
            elif data1 != data2:
                # Find the exact position of the first difference
                for i in range(min(len(data1), len(data2))):
                    if data1[i] != data2[i]:
                        print(f"Difference found at byte {offset + i}: {file1_path} has {data1[i]} and {file2_path} has {data2[i]}")
                        return False

                if len(data1) != len(data2):
                    print(f"Difference found: files have different lengths.")
                    return False

            offset += chunk_size

        return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare two binary files.")
    parser.add_argument("file1", help="Path to the first binary file")
    parser.add_argument("file2", help="Path to the second binary file")
    
    args = parser.parse_args()
    
    compare_files(args.file1, args.file2)
