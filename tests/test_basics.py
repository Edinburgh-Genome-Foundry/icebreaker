import os
import time
import icebreaker
from icebreaker.tools import load_record


conf_folder = os.path.join('tests', 'configs')

def test_auth():
    ice = icebreaker.IceClient(os.path.join(conf_folder, 'john_doe_token.yml'))
    assert (len(ice.get_collection_folders('PERSONAL')) >  0)
    ice = icebreaker.IceClient(os.path.join(conf_folder, 'john_doe_auth.yml'))
    assert ice.session_infos['description'] == 'I am John'

def test_search_methods():
    ice = icebreaker.IceClient(os.path.join(conf_folder, 'john_doe_auth.yml'))
    test1_part, errors = ice.find_entry_by_name("Test1")
    assert (errors is None)
    assert test1_part["id"] == 1

def test_folder_methods():
    ice = icebreaker.IceClient(os.path.join(conf_folder, 'john_doe_token.yml'))
    folders = ice.get_collection_folders('PERSONAL')
    assert (len(folders) == 1) and (folders[0]['folderName'] == 'test_folder')

def test_file_attachments():
    ice = icebreaker.IceClient(os.path.join(conf_folder, 'john_doe_auth.yml'))
    record  = load_record(os.path.join('tests', 'data', 'example_record.gb'))
    part_id = 1
    try:
        ice.delete_part_record(part_id)
    except:
        pass
    ice.attach_record_to_part(ice_part_id=part_id, record=record)
    new_record = ice.get_record(part_id)
    assert len(new_record) == 150
    ice.delete_part_record(part_id)

def test_part_parameter_values():
    ice = icebreaker.IceClient(os.path.join(conf_folder, 'john_doe_auth.yml'))
    part_id = 1
    ice.set_part_custom_field(part_id, "TEST_PARAM", "TEST_VALUE")
    assert ice.get_part_custom_field(part_id, "TEST_PARAM") == "TEST_VALUE"
    parts = ice.find_parts_by_custom_field_value("TEST_PARAM", "TEST_VALUE")
    assert len(parts) == 1
    fields = ice.get_part_custom_fields_list(part_id)
    assert len(fields) == 1
    for field in fields:
        response = ice.delete_custom_field(field['id'])
        assert response.ok