from Bio import SeqIO
import os
import pandas
import json
import icebreaker

new_ice = icebreaker.IceClient("../api_tokens/local_update.yaml")
new_ice_folders = new_ice.get_collection_folders("PERSONAL")
root_data_folder = "local_data"
collection_folders = os.listdir(root_data_folder)

for folder in collection_folders:
    print("Processing folder", folder)
    if folder not in new_ice_folders:
        folder_infos = new_ice.create_folder(folder)
        new_ice_folders.append(folder)
        folder_id = folder_infos["id"]
    else:
        folder_id = new_ice.get_folder_id(folder)

    data_folder = os.path.join(root_data_folder, folder, "data")
    genbank_folder = os.path.join(root_data_folder, folder, "records")
    parts_ids = []
    for data_file in os.listdir(data_folder):
        part_id = ".".join(data_file.split(".")[:-1])
        print("... entry", part_id)
        data_file_path = os.path.join(
            root_data_folder, folder, "data", data_file
        )
        with open(data_file_path, "r") as f:
            part_infos = json.load(f)
        genbank_file_path = os.path.join(
            root_data_folder, folder, "records", part_id + ".gb"
        )
        with open(genbank_file_path, "r") as f:
            record_text = f.read()
        if part_infos["type"] == "PLASMID":
            part_infos = new_ice.create_plasmid(
                name=part_infos["name"],
                description=part_infos["shortDescription"],
                markers=part_infos["selectionMarkers"],
                pi=part_infos["principalInvestigator"],
            )
        else:
            part_infos = new_ice.create_part(
                name=part_infos["name"],
                description=part_infos["shortDescription"],
                pi=part_infos["principalInvestigator"],
            )
        parts_ids.append(part_infos["id"])
        new_ice.attach_record_to_part(
            ice_part_id=part_infos["id"], record_text=record_text
        )
        new_ice.add_to_folder(parts_ids, folders_ids=[folder_id])
