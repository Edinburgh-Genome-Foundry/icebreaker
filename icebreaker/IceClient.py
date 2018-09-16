import json

import requests
import requests_cache
import proglog

from .tools import did_you_mean, ice_genbank_to_record

class IceClient:
    """Session to easily interact with an ICE instance."""
    
    def __init__(self, root, api_token, api_token_client, cache='memory',
                 logger='bar'):
        """Initializes an instance and a connection to an ICE instance.
        
        Examples
        --------

        >>> ice = icebreaker.IceClient(root="https://ice.genomefoundry.org",
        >>>                            api_token="WHz+BC+7eFV=...",
        >>>                            api_token_client = "icebot")
        Parameters
        ----------

        root
          Web address of the ICE instance, e.g. `https:/ice.genomefoundry.org`
        
        api_token, api_token_client
          Valid ICE API token and associated client ID. See documentation if
          you are unsure how to get one.
        
        cache
          Option to cache the ICE requests, which will greatly improve the
          speed of many scripts. Set to None for no caching, "memory"
          for in-RAM caching, and either "sqlite", "mongodb", "redis" for
          persistent caching in a database.
          See https://requests-cache.readthedocs.io for more.
          Beware that caching means updates to the database may be ignored,
          use with care.
        
        logger
          Either None for no logging, 'bar' for progress bar logging (useful
          in notebooks), or a custom Proglog logging object.
        """
        self.root = root.strip('/')
        self.logger = proglog.default_bar_logger(logger)
        if cache is not None:
            self.session = requests_cache.CachedSession(backend=cache)
        else:
            self.session = requests.Session()
        self.session.headers = {
            "Accept": 'application/json',
            "Content-Type": 'application/json',
            "X-ICE-API-Token-Client": api_token_client,
            "X-ICE-API-Token": api_token, 
        }
    
    def _endpoint_to_url(self, endpoint):
        """Complete endpoint by adding domain name."""
        return self.root + '/rest/' + endpoint
    
    def request(self, method, endpoint, params=None, data=None,
                response_type='json'):
        """Make a request to the ICE server.

        This is a generic method used by all the subsequence get_ methods.

        Examples
        --------

        >>> ice = IceClient(...) 
        >>> ice.request("GET", "GET", "folders/12/entries",
                        params=dict(limit=20))

        Parameters
        ----------

        method
          One of "GET", "POST", etc. see documentation of the Request library.
        
        endpoint
          Part of the address after "http/.../rest/".
        
        params
          Parameters to add to the url.
        
        data
          Json data to add to the request
        
        response_type
          Use "json" if you expect JSON to be returned, or "file" if
          you are expecting a file.

        """
        
        url = self._endpoint_to_url(endpoint)
        response = self.session.request(method, url, params=params, data=data)
        if response.status_code == 200:
            if response_type == 'json':
                return response.json()
            if response_type == 'file':
                return response.content
        else:
            raise IOError(
                "ICE request failed with code %s (%s):\n "
                "REQUEST: %s %s\nDATA: %s "% (
                response.status_code, response.reason,
                method, url, json.dumps(data, indent=2)
            ))
    
    # PARTS
    
    def get_part_samples(self, id):
        """Return a list of samples (dicts) for the part with that id."""
        return self.request("GET", 'parts/%s/samples' % id)
    
    def get_part_sequence(self, id, format='genbank'):
        """Return genbank text for the part with that id."""
        endpoint = "file/%s/sequence/%s" % (id, format)
        return self.request("GET", endpoint, response_type='file')
        
    def get_part_record(self, id):
        """Return a biopython record for the part with that id."""
        genbank = self.get_part_sequence(id, format='genbank')
        return ice_genbank_to_record(genbank)

    def get_part_infos(self, id):
        """Return infos (name, creation date...) for the part with that id."""
        return self.request("GET", 'parts/' + id)
    
    def get_part_id(self, name, folder_id=None, collection=None,
                    use_filter=False):
        """Find the id of a part, given a name.

        This method works by pulling all data from selected folders and looking
        for the part's name. Therefore it can be very long for big folders.
        
        
        Parameters
        -----------
        
        name
          Name of the part to be IDed

        folder_id
          Folder ID (or list of) where to find the part.
          
        collection
          Collection where to find the part. Can be provided instead of
          folder_id.        
        
        use_filter
          If true, the ICE request will use filtering. This if faster for a
          one-off ID search but if you use caching and do many part IDing you
          will be better off without the filtering (your first search will be
          very long but next searches will be instantaneous)
        """
        if collection is not None:
            folder_id = tuple(sorted([
                f['id'] for f in self.get_collection_folders(collection)]))
        
        parts_names_ids = self._folder_parts_names_to_ids(
            folder_id, must_contain=name if use_filter else None)
        if name not in parts_names_ids:
            error = "No part named %s." % name
            suggestions = did_you_mean(name, parts_names_ids)
            if len(suggestions):
                error += " Suggestions: %s." % ", ".join(suggestions)
            raise IOError(error)
        id = list(set(parts_names_ids[name]))
        if len(id) > 1:
            raise IOError("Found several folders named %s, with IDs %s." %
                          (name, ", ".join([str(d) for d in id])))
        return id[0]
    
    def _folder_parts_names_to_ids(self, folder_ids, must_contain=None):
        parts_names_ids = {}
        if not isinstance(folder_ids, list):
            folder_ids = [folder_ids]
        for folder_id in folder_ids:
            entries = self.get_folder_entries(folder_id=folder_id,
                                              must_contain=must_contain)
            for entry in entries:
                name = entry["name"]
                if name not in parts_names_ids:
                    parts_names_ids[name] = []
                parts_names_ids[name].append(entry['id'])
        return parts_names_ids
    
    def search(self):
        "Not yet implemented. Ask for it !"
        pass
    
    # FOLDERS
    
    def get_folder_infos(self, id):
        """Return infos (dict) on the folder whose id is provided."""
        return self.request("GET", "folders/%s" % id)
    

    def get_folder_id(self, name, collection=None):
        folders_names_ids = self._collection_folders_names_to_ids(collection)
        if name not in folders_names_ids:
            error = "No folder named %s." % name
            suggestions = did_you_mean(name, folders_names_ids)
            if len(suggestions):
                error += " Suggestions: %s." % ", ".join(suggestions)
            raise IOError(error)
        folder_id = list(set(folders_names_ids[name]))
        if len(folder_id) > 1:
            raise IOError("Found several folders named %s, with IDs %s." %
                          (name, ", ".join([str(d) for d in folder_id])))
        return folder_id[0]
    
    def _collection_folders_names_to_ids(self, collection):
        folders_names_ids = {}
        for folder in self.get_collection_folders(collection=collection):
            name = folder["folderName"]
            if name not in folders_names_ids:
                folders_names_ids[name] = []
            folders_names_ids[name].append(folder['id'])
        return folders_names_ids
    
    def get_folder_entries(self, folder_id, must_contain=None,
                           as_iterator=False, limit=None, batch_size=10):
        """Return a list or iterator of all entries in a given ICE folder.

        Each entry is represented by a dictionnary giving its name, creation
        date, and other infos.
        
        Parameters
        ----------

        folder_id
          ID of the folder to browse.
        
        must_contain
          If provided, either the id or the name of the entry (part) must
          contain that string.
        
        limit
          If provided, only the nth first entries are considered.
        
        batch_size
          How many parts should be pulled from ICE at the same time.

        as_iterator
          If true, an iterator is returned instead of a list (useful for
          folders with many parts)
        """
        url = "folders/%s/entries" % folder_id
        def request(offset):
            return self.request(
                "GET", url,  params=dict(limit=batch_size, filter=must_contain,
                                         offset=offset))
        count = request(0)["count"]
        def generator():
            offsets = range(0, count, batch_size)
            for offset in self.logger.iter_bar(batch=offsets):
                result = request(offset)
                for entry in result["entries"]:
                    yield entry
        iterator = generator()
        if as_iterator:
            if limit is not None:
                return (entry for i, entry in zip(range(limit), iterator))
            return iterator
        else:
            if limit is not None:
                return [entry for i, entry in zip(range(limit), iterator)]
            else:
                return list(iterator)
    
    # COLLECTIONS
    
    def get_collection_folders(self, collection):
        """Return a list of folders in a given collection.
        
        Collection must be one of:
        FEATURED PERSONAL SHARED DRAFTS PENDING DELETED
        """
        if isinstance(collection, tuple):
            return sum([
                self.get_collection_folders(c)
                for c in collection
            ], [])
        return self.request("GET", "collections/%s/folders" % collection)
    
    def get_collection_entries(self, collection, ignored_folders=()):
        return sum([
            self.get_folder_entries(f)
            for f in self.get_collection_folders(collection)
            if f not in ignored_folders
        ], [])
    
    def get_collections_list(self):
        return "FEATURED PERSONAL SHARED DRAFT PENDING DELETED".split()