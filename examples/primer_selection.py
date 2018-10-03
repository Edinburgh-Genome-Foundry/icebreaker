from icebreaker import IceClient, sample_location_string
from primavera import PrimerSelector, Primer, load_record
import proglog
proglog.notebook()

# CONNECT TO ICE

ice = icebreaker.IceClient(
    root="https://ice.genomefoundry.org",
    api_token="BJJG11ZnwS7Glw3WMnlYlWHz+BC+7eFV=",
    api_token_client = "icebot"
)

# GET ALL PRIMERS

primers_folder = ice.get_folder_id("PRIMERS", collection="SHARED")
available_primers = [
    Primer(sequence=ice.get_record(entry["id"]).seq.tostring(),
           name=entry["name"],
           metadata=dict(ice_id=entry['id']))
    for entry in ice.get_folder_entries(primers_folder)
]
constructs = [load_record("./RTM3_39.gb", linear=False)]

# SELECT THE BEST PRIMERS

selector = PrimerSelector(read_range=(150, 1000), tm_range=(55, 70),
                          size_range=(16, 25), coverage_resolution=10,
                          primer_reuse_bonus=200)
selected_primers = selector.select_primers(constructs, available_primers)

# FIND THE LOCATION OF THE SELECTED PRIMERS

for primer in set(sum(selected_primers, [])):
    ice_id = primer.metadata.get("ice_id", None)
    primer.metadata["location"] = None
    if ice_id is not None:
        samples = ice.get_samples(ice_id)
        location = ", ".join([sample_location_string(s) for s in samples])
        primer.metadata["location"] = location or "unknown"

# PLOT THE COVERAGE AND WRITE THE PRIMERS IN A SPREADSHEET

selector.plot_coverage(constructs, selected_primers, 'coverage.pdf')
selector.write_primers_table(selected_primers, 'selected_primers.csv')