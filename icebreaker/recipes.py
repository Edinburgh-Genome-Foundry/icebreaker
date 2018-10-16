import pandas
import flametree
from .utils import sample_location_string

def find_parts_locations_by_name(ice_client, part_names):
    rows = []
    for p in ice_client.logger.iter_bar(part=part_names):
        part_infos, error = ice_client.search_part_by_name(p)
        if error:
            rows.append([
                p, "%s. Did you mean %s" % (error[0], ", ".join(error[1]))])
        else:
            samples = ice_client.get_part_samples(part_infos["id"])
            if len(samples) == 0:
                rows.append([p, "In ICE but no samples"])
            else:
                for sample in samples:
                    location = sample_location_string(
                        sample["location"], stop_at="TUBE")
                    location = location.replace("\n", " ").replace("\r", " ")
                    rows.append([p, location])
    return pandas.DataFrame(rows, columns=["part", "location"])

def download_folder_data(ice_client, folder_id=None, folder_name=None,
                         collection="SHARED",
                         columns='default', spreadsheet_file=None,
                         genbanks_dir=None, logger='bar'):
    logger = default_bar_logger(logger)
    if folder_id is None:
        folder_id = ice_client.get_folder_id(folder_name, collection)
    entries = ice_client.get_folder_entries(folder_id)
    
    if spreadsheet_file is not None:
        for entry in logger.iter_bar(entry=entries):
            data = ice_client.get_part_infos(entry['id'])
            entry.update(data)
        
        if columns == 'default':
            columns = ('name', 'alias', 'basePairCount', 'selectionMarkers',
                       'hasSample', 'principalInvestigator',
                       'shortDescription')
        df = pandas.DataFrame(entries, columns=columns)
        df.to_excel(spreadsheet_file, index=False)
    
    if genbanks_dir is not None:
        genbanks_root = flametree.file_tree(genbanks_dir)
        for e in logger.iter_bar(entry_record=entries):
            seq = ice_client.get_sequence(e['id'])
            genbanks_root._file('%s.gb' % e['name']).write(seq)
        genbanks_root._close()