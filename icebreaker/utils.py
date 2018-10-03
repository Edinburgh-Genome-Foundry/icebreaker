from collections import OrderedDict

def parse_sample_location(sample_data):
    if 'location' in sample_data:
        sample_data = sample_data["location"]
    result = OrderedDict([(sample_data["type"],
                           sample_data.get("display", ""))])
    while "child" in sample_data:
        sample_data = sample_data["child"]
        result[sample_data["type"]] = sample_data.get("display", "")
    return result

def sample_location_string(sample_data, stop_at="WELL"):
    result = []
    for container, label in parse_sample_location(sample_data).items():
        result.append(label)
        if container == stop_at:
            break
    return "/".join(result)