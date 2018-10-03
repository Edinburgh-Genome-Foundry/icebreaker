import pandas
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