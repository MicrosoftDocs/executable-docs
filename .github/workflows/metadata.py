import os
import json
import yaml
import re
import time

def find_region_value(markdown_text):
    regions_list = ['eastus', 'westus', 'westeurope', 'eastasia', 'southeastasia', 'australiaeast', 'australiasoutheast', 'centralus', 'southcentralus',]
    match = re.search(r'REGION="(.+?)"', markdown_text, re.IGNORECASE)
    if match:
        region = str(match.group(1))
        if region in regions_list:
            regions_list.remove(region)
        regions_list.insert(0, region)
    return regions_list

def update_base_metadata(directory, metadata):
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if os.path.isdir(path):
            # If it's a directory, process it recursively
            update_base_metadata(path, metadata)
        else:
            # If it's a file, check if it's a README file
            if '.md' in name.lower():
                # Process the README file
                with open(path, 'r') as f:
                    readme_content = f.read()
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
                    
                    if metadata:
                        for item in metadata:
                            if item['key'] == key:
                                break
                        else:
                            # If the key was not found, add a new item to metadata
                            item = {'status': 'active', 'key': key}
                            metadata.append(item)
                    else:
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
                        item['configurations'] = {
                            "regions": find_region_value(readme_content)
                        }

    return metadata


def localize_metadata(directory, metadata):
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        
        if os.path.isdir(path):
            # If it's a directory, process it recursively
            localize_metadata(path, metadata)
        else:
            # If it's a file, check if it's a README file
            if '.md' in name.lower():
                # Process the README file
                with open(path, 'r') as f:
                    metadata_lines = []
                    for line in f:
                        if line.strip() == '---':
                            if metadata_lines:
                                break
                        metadata_lines.append(line)

                    # Join the lines together into a single string
                    metadata_str = '\n'.join(metadata_lines).strip('---').strip('\n')

                    # Parse the metadata from the string
                    readme_metadata = yaml.safe_load(metadata_str)
                    readme_metadata = json.loads(json.dumps(readme_metadata, ensure_ascii=False))
                    # Replace the corresponding keys in the metadata.json file
                    for item in metadata:
                        if item['key'] == '/'.join(path.split('/')[3:]):
                            item['title'] = readme_metadata.get('title', item['title'])
                            item['description'] = readme_metadata.get('description', item['description'])
                            item['stackDetails'] = readme_metadata.get('stackDetails', item['stackDetails'])
                            if locale not in item['sourceUrl']:
                                item['sourceUrl'] = item['sourceUrl'].replace('/main/scenarios/', f'/main/localized/{locale}/scenarios/')
                            if locale not in item['documentationUrl']:
                                item['documentationUrl'] = item['documentationUrl'].replace('learn.microsoft.com/azure', f'learn.microsoft.com/{locale}/azure')

    return metadata 

# Load the base metadata.json file
if os.path.isfile('scenarios/metadata.json'):
    with open('scenarios/metadata.json', 'r') as f:
        base_metadata = json.load(f)

    # Update the metadata with the README files in the scenarios directory
    metadata = update_base_metadata('scenarios', base_metadata)

    # Write the updated metadata.json file
    with open('scenarios/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=4)

else:
    with open('scenarios/metadata.json', 'w') as f:
        base_metadata = []

    # Update the metadata with the README files in the scenarios directory
    metadata = update_base_metadata('scenarios', base_metadata)

    # Write the updated metadata.json file
    with open('scenarios/metadata.json', 'w') as f:
        json.dump(metadata, f, indent=4)

# Base directory for localized content
base_dir = 'localized'

# Iterate over each locale directory
for locale in sorted(os.listdir(base_dir)):
    locale_dir = os.path.join(base_dir, locale, 'scenarios')
    metadata_file = os.path.join(locale_dir, 'metadata.json')
    
    # Load the base metadata.json file if it exists, otherwise create an empty dictionary
    metadata = base_metadata.copy()  # Use a copy of the base metadata
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            localized_metadata = json.load(f)
        # Merge the localized metadata with the base metadata
        metadata.extend(localized_metadata)
        
    updated_metadata = localize_metadata(locale_dir, metadata)
    # Write the updated metadata.json file to the locale's scenarios directory
    with open(metadata_file, 'w') as f:
        json.dump(updated_metadata, f, indent=4)
# # Load the base metadata.json file
# if os.path.isfile('scenarios/metadata.json'):
#     with open('scenarios/metadata.json', 'r') as f:
#         metadata = json.load(f)

#     # Update the metadata with the README files in the scenarios directory
#     metadata = update_base_metadata('scenarios', metadata)

#     # Write the updated metadata.json file
#     with open('scenarios/metadata.json', 'w') as f:
#         json.dump(metadata, f, indent=4)

# else:
#     with open('scenarios/metadata.json', 'w') as f:
#         metadata = []

#     # Update the metadata with the README files in the scenarios directory
#     metadata = update_base_metadata('scenarios', metadata)

#     # Write the updated metadata.json file
#     with open('scenarios/metadata.json', 'w') as f:
#         json.dump(metadata, f, indent=4)

# # Base directory for localized content
# base_dir = 'localized'

# # Iterate over each locale directory
# for locale in sorted(os.listdir(base_dir)):
#     locale_dir = os.path.join(base_dir, locale, 'scenarios')
#     metadata_file = os.path.join(locale_dir, 'metadata.json')
    
#     # Load the base metadata.json file if it exists, otherwise create an empty dictionary
#     metadata = {}
#     base_metadata_file = os.path.join('scenarios', 'metadata.json')
#     if os.path.exists(metadata_file):
#         with open(metadata_file, 'r') as f:
#             metadata = json.load(f)
#     else:
#         with open(base_metadata_file, 'r') as bf:
#             base_metadata = json.load(bf)
#         with open(metadata_file, 'w') as f:
#             json.dump(base_metadata, f)
#         metadata = base_metadata
        
#     updated_metadata = localize_metadata(locale_dir, metadata)
#     # Write the updated metadata.json file to the locale's scenarios directory
#     with open(metadata_file, 'w') as f:
#         json.dump(updated_metadata, f, indent=4)