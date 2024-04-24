# sync happens
# base metadata.json file is updated
# MT happens on exec docs
# localization of metadata.json file happens
# 

import os
import json
import yaml

def update_metadata(directory, metadata):
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if os.path.isdir(path):
            # If it's a directory, process it recursively
            update_metadata(path, metadata)
        else:
            # If it's a file, check if it's a README file
            if '.md' in name.lower():
                # Process the README file
                with open(path, 'r') as f:
                    metadata_lines = []
                    collecting = False
                    for line in f:
                        if line.strip() == '---':
                            if collecting:
                                break
                            else:
                                collecting = True
                                continue
                        if collecting:
                            metadata_lines.append(line)
                    
                    # Join the lines together into a single string
                    metadata_str = '\n'.join(metadata_lines).strip('---').strip('\n')

                    # Parse the metadata from the string
                    readme_metadata = yaml.safe_load(metadata_str)
                    readme_metadata = json.loads(json.dumps(readme_metadata, ensure_ascii=False))
                    # Get the key for this file
                    key = '/'.join(path.split('/')[1:])
                    # Find the item in metadata with this key
                    
                    for item in metadata:
                        if item['key'] == key:
                            break
                    else:
                        # If the key was not found, add a new item to metadata
                        item = {'status': 'active', 'key': key}
                        metadata.append(item)
                    
                    # Update the item with the metadata from the README file
                    item['title'] = readme_metadata.get('title', item.get('title', ''))
                    item['description'] = readme_metadata.get('description', item.get('description', ''))
                    item['stackDetails'] = readme_metadata.get('stackDetails', item.get('stackDetails', ''))
                    if not item.get('sourceUrl', ''):
                        item['sourceUrl'] = "https://raw.githubusercontent.com/MicrosoftDocs/executable-docs/main/scenarios/"+key
                    if not item.get('documentationUrl', ''):
                        item['documentationUrl'] = ''
                    if not item.get('configurations', ''):
                        item['configurations'] = {}

    return metadata

# Load the base metadata.json file
if os.path.isfile('scenarios/metadata.json'):
    with open('scenarios/metadata.json', 'r') as f:
        metadata = json.load(f)

    # Update the metadata with the README files in the scenarios directory
    metadata = update_metadata('scenarios', metadata)

    # Write the updated metadata.json file
    with open('scenarios/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=4)