from pathlib import Path
import sys
import os
import shutil
import re

def check_and_rename_folders():
    # Get the directory where the script is located
    script_dir = Path(sys.path[0])
    
    # Define the untested folder path
    untested_dir = script_dir / "untested"
    
    if not untested_dir.exists():
        print(f"Error: Untested directory not found at {untested_dir}")
        return
        
    print(f"Checking folders in {untested_dir}")
    
    # Get all subfolders
    subfolders = [f for f in untested_dir.iterdir() if f.is_dir()]
    
    if not subfolders:
        print("No subfolders found in the untested directory.")
        return
    
    print(f"Found {len(subfolders)} subfolders.")
    
    # Process each subfolder
    for folder in subfolders:
        original_name = folder.name
        
        # Check if folder is empty
        files = list(folder.iterdir())
        if not files:
            print(f"⚠️ Empty folder detected: {original_name}")
            continue
            
        # Remove the "..." from folder name if present
        if original_name.endswith("..."):
            new_name = original_name[:-3]  # Remove the trailing "..."
            new_folder_path = folder.parent / new_name
            
            try:
                # Create temporary folder name to avoid potential conflicts
                temp_folder_path = folder.parent / f"temp_{original_name}"
                folder.rename(temp_folder_path)
                temp_folder_path.rename(new_folder_path)
                print(f"✓ Renamed folder: {original_name} → {new_name}")
                # Update the folder reference to the new path
                folder = new_folder_path
            except Exception as e:
                print(f"✗ Error renaming folder {original_name}: {str(e)}")
                continue
        
        # Rename files within the folder to match folder name
        for file_path in folder.iterdir():
            if file_path.is_file():
                file_extension = file_path.suffix
                new_file_name = f"{folder.name}{file_extension}"
                new_file_path = folder / new_file_name
                
                # Skip if the filename already matches
                if file_path.name == new_file_name:
                    continue
                    
                try:
                    file_path.rename(new_file_path)
                    print(f"  ✓ Renamed file: {file_path.name} → {new_file_name}")
                except Exception as e:
                    print(f"  ✗ Error renaming file {file_path.name}: {str(e)}")

if __name__ == "__main__":
    check_and_rename_folders()
    print("Processing complete!")