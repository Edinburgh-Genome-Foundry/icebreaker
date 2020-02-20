from Bio import SeqIO
import os
import pandas
import json
import icebreaker

# LOAD ALL "SHARED" FOLDERS DATA ON YOUR COMPUTER

ice = icebreaker.IceClient("../api_tokens/admin.yaml")
folders = ice.get_collection_folders("SHARED")
# folders = folders[:4]  # test with a small part
local_data_folder = "local_data"
os.mkdir(local_data_folder)

for folder in folders:
    print("Processing folder", folder["folderName"])
    local_folder_path = os.path.join(local_data_folder, folder["folderName"])
    if not os.path.exists(local_folder_path):
        os.mkdir(local_folder_path)
    parts_in_folder = ice.get_folder_entries(folder_id=folder["id"])
    genbanks_path = os.path.join(local_folder_path, "records")
    if not os.path.exists(genbanks_path):
        os.mkdir(genbanks_path)
    parts_data_path = os.path.join(local_folder_path, "data")
    if not os.path.exists(parts_data_path):
        os.mkdir(parts_data_path)
    parts_infos_list = []
    for part in parts_in_folder:
        print("... entry", part["name"])
        part_infos = ice.get_part_infos(part["id"])
        parts_infos_list.append(part_infos)
        json_target = os.path.join(
            parts_data_path, "%s.json" % part_infos["id"]
        )
        with open(json_target, "w") as f:
            json.dump(part_infos, f)
        genbank_target = os.path.join(
            genbanks_path, "%s.gb" % part_infos["id"]
        )
        genbank = ice.get_sequence(part["id"])
        with open(genbank_target, "w") as f:
            f.write(genbank)
    df = pandas.DataFrame.from_records(parts_infos_list)
    spreadsheet_path = os.path.join(local_folder_path, "data.csv")
    df.to_csv(spreadsheet_path, index=False)
    print("... done with folder", folder["folderName"])

