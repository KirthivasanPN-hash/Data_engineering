import csv

from models.site import Site

def is_duplicate(site_name: str, seen_values: set) -> bool:
    return site_name in seen_values

def is_complete_site(site: dict, required_keys: list) -> bool:
    return all(key in site for key in required_keys)

def save_keys_to_csv(valid_infos: list, filename: str) -> None:
    if not valid_infos: 
        print("No data to save")
        return
    
    fieldnames = Site.model_fields.keys()
    
    with open(filename, mode='w', newline= "", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(valid_infos)
    print(f"Saved {len(valid_infos)} sites to '{filename}'.")

    