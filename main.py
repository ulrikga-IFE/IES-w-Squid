"""main should:
- Include necessary python files
- Setup necessary objects and threads/multiprocesses
"""

import multiprocessing
import GUI
import os


current_directory = os.path.dirname(os.path.abspath(__file__))
folder_names = ['Save_folder', 'Total_mm', 'Raw_data_result', 'processed']
for folder_name in folder_names:
    temp_folder_path = os.path.join(current_directory, folder_name)
    if not os.path.exists(temp_folder_path):
        try:
            os.makedirs(temp_folder_path)
            print(f"Folder '{folder_name}' created successfully in {current_directory}.")
        except OSError as e:
            print(f"Error occurred while creating folder '{folder_name}': {e}")
    else:
        print(f"Folder '{folder_name}' already exists in {current_directory}.")


GUI.GUI()