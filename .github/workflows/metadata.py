import os
import json
import yaml

def process_directory(directory):
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        
        if os.path.isdir(path):
            # If it's a directory, process it recursively
            process_directory(path)
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
                            item['sourceUrl'] = item['sourceUrl'].replace('/scenarios/', f'/localized/{locale}/scenarios/')
                            item['documentationUrl'] = item['documentationUrl'].replace('learn.microsoft.com/azure', f'learn.microsoft.com/{locale}/azure')
    
# Base directory for localized content
base_dir = 'localized'

# Iterate over each locale directory
for locale in sorted(os.listdir(base_dir)):
    locale_dir = os.path.join(base_dir, locale, 'scenarios')
    # Load the base metadata.json file
    with open('scenarios/metadata.json', 'r') as f:
        metadata = json.load(f)
    
    process_directory(locale_dir)
    # Write the updated metadata.json file to the locale's scenarios directory
    with open(os.path.join(locale_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=4)