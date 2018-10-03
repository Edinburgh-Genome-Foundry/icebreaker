import json
import yaml
from io import StringIO

import requests
import requests_cache
import proglog

from Bio import SeqIO


from .tools import did_you_mean, ice_genbank_to_record

class IceClient:
    """Session to easily interact with an ICE instance."""
    
    def __init__(self, config, cache=None, logger='bar'):
        """Initializes an instance and a connection to an ICE instance.
        
        Examples
        --------

        >>> config = dict(root="https://ice.genomefoundry.org",
        >>>               token="WHz+BC+7eFV=...",
        >>>               client="icebot")
        >>> ice = icebreaker.IceClient(config)
        >>> # Alternative config via a yaml file:
        >>> ice = icebreaker.IceClient(config="config.yaml")

        Parameters
        ----------

        config
          Authentication configuration of the ICE instance. Should be either
          a dictionnary or a yaml file representing a dictionnary
          (cf. documentation). The dictionnary should be of the form
          ``{root: email: password:}`` where root is the root address of your
          online ICE instance, or ``{root: token: client:}`` to authenticate
          with a client name and API token (a.k.a API key).
        
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
        if isinstance(config, str):
            with open(config, "r") as f:
                config = next(yaml.load_all(f.read()))
        self.root = config["root"].strip('/')
        self.logger = proglog.default_bar_logger(logger)
        self.logger.ignore_bars_under = 2
        if cache is not None:
            self.session = requests_cache.CachedSession(backend=cache)
        else:
            self.session = requests.Session()
        self.session.headers = headers = {}
        self.session_infos = {}
        if "session_id" in config:
            headers['X-ICE-Authentication-SessionId'] = config['session_id']
            self.session_infos.update(config.get('session_infos', {}))
        if "client" in config:
            self.set_api_token(config["client"], config["token"])
        elif "password" in config:
            self.get_new_session_id(config["email"], config["password"])
    
    def _endpoint_to_url(self, endpoint):
        """Complete endpoint by adding domain name."""
        return self.root + '/rest/' + endpoint
    
    def set_api_token(self, client, token):
        """Set a new API token (and erase any previous token / session ID)
        
        Examples
        --------

        >>> ice_client.set_api_token('icebot', 'werouh4E4boubSFSDF=')
        """
        self.session.headers.update({
            "X-ICE-API-Token-Client": client,
            "X-ICE-API-Token": token 
        })
        self.session.headers.pop('X-ICE-Authentication-SessionId', None)
        self.session_infos = {'api_token': token, 'api_client': client}

    
    def get_new_session_id(self, email, password):
        """Authenticate and receive a new session ID.

        This is automatically called in IceClient if the config contains an
        email and password.
        """
        data = dict(email=email, password=password)
        response = self.request('POST', 'accesstokens', data=data)
        session_id = response['sessionId']
        self.session.headers['X-ICE-Authentication-SessionId'] = session_id
        self.session.headers.pop("X-ICE-API-Token-Client", None)
        self.session.headers.pop("X-ICE-API-Token", None)
        self.session_infos = response

    def request(self, method, endpoint, params=None, data=None,
                files=None, response_type='json'):
        """Make a request to the ICE server.

        This is a generic method used by all the subsequent methods, and wraps
        the ``requests.request`` method

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
          Parameters to add to the url, as a dict (the ones after "?=")
        
        data
          Json data to add to the request
        
        files
          A dict of the form ``{fileId: (filename, content, mimetype)}``
          where fileId is the variable name expected by the ICE API,
          content is a string or bytes, mymetype a string like
          ````

        
        response_type
          Use "json" if you expect JSON to be returned, or "file" if
          you are expecting a file.

        """
        
        url = self._endpoint_to_url(endpoint)
        if files is None:
            headers = {
              "Accept": 'application/json',
              "Content-Type": 'application/json;charset=UTF-8' 
            }
            headers.update(self.session.headers)
            
            response = self.session.request(method, url, params=params,
                                            headers=headers,
                                            data=json.dumps(data))
        else:
            response =  self.session.request(method, url, data=data,
                                             files=files)

        if response.status_code == 200:
            if response_type == 'json':
                return response.json()
            if response_type == 'file':
                return response.content
            if response_type == 'raw':
                return response
            return response
        else:
            raise IOError(
                "ICE request failed with code %s (%s):\n "
                "REQUEST: %s %s\nDATA: %s "% (
                response.status_code, response.reason,
                method, url, json.dumps(data, indent=2)
            ))
    
    # PARTS
    
    def get_part_samples(self, id):
        """Return a list of samples (dicts) for the entity with that id."""
        return self.request("GET", 'parts/%s/samples' % id)
    
    def get_sequence(self, id, format='genbank'):
        """Return genbank text for the entity with that id."""
        endpoint = "file/%s/sequence/%s" % (id, format)
        return self.request("GET", endpoint, response_type='file')
        
    def get_record(self, id):
        """Return a biopython record for the entity with that id."""
        genbank = self.get_sequence(id, format='genbank')
        return ice_genbank_to_record(genbank)

    def get_part_infos(self, id):
        """Return infos (name, creation date...) for the part with that id."""
        return self.request("GET", 'parts/%s' % id)
    
    def _folder_parts_names_to_ids(self, folder_ids, must_contain=None):
        parts_names_ids = {}
        if not isinstance(folder_ids, (list, tuple)):
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
    
    def search(self, query, limit=None, batch_size=50, as_iterator=False,
               min_score=0, entry_types=(),
               sort_field="RELEVANCE"):
        """Return an iterator or list over text search results.

        Parameters
        ----------

        query
          Text to query
        
        limit
          limit on the number of entries to fetch
        
        batch_size
          How many entries to get at the same time at each connexion with ICE
          ideal may be 50
        
        as_iterator
          If True an iterator is returned, if False a list is returned.
        
        min_score
          Minimal score accepted. The search will be stopped at the first
          occurence of a score below that limit if sort_field is "RELEVANCE".
        
        
        Returns
        -------
        entries_iterator
          An iterator over the successive entries found by the search.
        """
        def request(offset):
            if limit is not None:
                retrieve_count = min(batch_size, limit - offset + 1)
            else:
                retrieve_count = batch_size
            data = dict(
                entryTypes=list(entry_types),
                parameters=dict(start=offset,
                                retrieveCount= retrieve_count,
                                sortField=sort_field),
                blastQuery={}, queryString=query,webSearch=False
            )
            return self.request("POST", "search",
                                data=data)
        count = request(0)["resultCount"]
        if limit:
            count = min(count, limit)
        def generator():
            offsets = range(0, count, batch_size)
            for offset in self.logger.iter_bar(batch=offsets):
                result = request(offset)
                for entry in result["results"]:
                    if float(entry["score"]) < min_score:
                        return
                    yield entry['entryInfo']
                
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
    
    def find_entry_by_name(self, name, limit=10, min_score=0,
                             entry_types=('PART', 'PLASMID')):
        """Find an entry (id and other infos) via a name search.
        
        Note that because of possible weirdness in ICE searches, it is not
        guaranteed to work.

        Parameters
        ----------
        name
          Name of the entry to retrieve

        limit
          Limitation on the number of entries to consider in the search.
          Ideally, get just 1 result (top result) would be sufficient, but
          you never know, some parts with slightly different names could
          rank higher.
        
        entry_types
          List of acceptable entry types. The less there is, the faster the
          search.
        
        Returns
        -------
          entry_info, None
            In case of success. ``entry_info`` is a dict with part ID, owner,
            etc.
        
          None, ("Multiple matches", [entries_ids...])
            In case several ICE entries have that exact name
        
          None, ("No match", ["suggestion1", "suggestion2" ...])
            Where the suggestions are entry names in ICE very similar to the
            required name.
        """
        results = self.search(name, limit=limit, min_score=min_score,
                              entry_types=entry_types)
        good_names = [r for r in results if r["name"] == name]
        if len(good_names) > 1:
            return None, ("Multiple matches", [r["id"] for r in r])
        elif len(good_names) == 0:
            suggestions = did_you_mean(
                name, [r["name"] for r in results], min_score=80)
            return None, ('No match', suggestions)
        return good_names[0], None
    
    def get_folder_entries(self, folder_id, must_contain=None,
                           as_iterator=False, limit=None, batch_size=15):
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
    


    def change_user_password(self, new_password, user_id='session_user'):
        """Change the password of a user (current session user by default)"""
        if  user_id == 'session_user':
            user_id = self.get_session_user_id()
        return self.request("PUT", "users/%s/password" % user_id,
                            data={'password': new_password})
    
    def get_part_permissions(self, id):
        """Get a list of all permissions attached to a part"""
        return self.request("GET", "parts/%s/permissions" % id)
    
    def delete_part_permission(self, part_id, permission_id):
        """Delete a permission for a given part."""
        url = "parts/%s/permissions/%s" % (part_id, permission_id)
        return self.request("DELETE", url, response_type='raw')
    
    def get_session_user_id(self):
        """Return the ICE id of the user of the current session."""
        if 'id' not in self.session_infos:
            raise ValueError("get_session_user_id only works")
        return self.session_infos['id']
    
    def restrict_part_to_user(self, part_id, user_id='current_user'):
        """Remove all permissions that are not from the given user."""
        if user_id == 'current_user':
            user_id = self.get_session_user_id()
        for permission in self.get_part_permissions(part_id):
            is_group = 'account' not in permission
            if is_group or (permission['account']['id'] != user_id):
                 self.delete_part_permission(part_id, permission['id'])
    
    def create_part(self, name, description="A part.", pi="unknown",
                    parameters=(), **attributes):
        """Create a new part.

        Parameters
        ----------

        name
          Name of the new part
        

        """
        parameters = [{"key": "", "value": value,  "name": name}
                        for name, value in parameters]
        data = dict(name=name, shortDescription=description, type="PART",
                    principalInvestigator=pi,
                    parameters=parameters, **attributes)
        return self.request("POST", 'parts', data=data)
    
    def create_folder(self, name):
        """Create a folder with the given name."""
        return self.request("POST", 'folders', data=dict(folderName=name))
    
    def create_folder_permission(self, folder_id, group_id=None, user_id=None,
                                 can_write=False):
        """Add a new permission for the given folder.
        
        Parameters
        ----------

        folder_id
          ID of the folder getting the permission

        user_id, group_id
          Provide either one to identify who gets the permission
        
        can_write
          Allows users to both add files to the folder and overwrite data
          from files in the folder (!! use with care).
        """
        data = dict(
            article="GROUP" if group_id is not None else "ACCOUNT",
            typeId=folder_id,
            articleId=group_id if group_id is not None else user_id,
            type="WRITE_FOLDER" if can_write else "READ_FOLDER"
        )
        return self.request("POST", 'folders/%s/permissions' % folder_id,
                            data=data)

    def delete_folder_permission(self, folder_id, permission_id):
        """Remove a permission attached to a given folder."""
        url = "folders/%s/permissions/%s" % (folder_id, permission_id)
        return self.request("DELETE", url, response_type='raw')
    
    def add_to_folder(self, entries_ids=(), folders=(), folders_ids=(),
                      remote_entries=()):
        """Add a list of entries to a list of folders.
        
        Parameters
        ----------

        entries_ids
          List of entry IDS

        folders
          List of full folder infos. (NOT folder ids). I guess this is to allow
          folders on remote ICE instances. Confusing, but you can use
          ``folders_ids`` instead.
        
        folder_ids
          List of folder IDs that can be provided instead of the ``folders``
          infos list.
        """
        if folders_ids is not None:
            folders = [self.get_folder_infos(fid) for fid in folders_ids]
        data = dict(
            destination=list(folders),
            entries=list(entries_ids),
            remoteEntries=list(remote_entries),
            all=False,
            selectionType='COLLECTION'
        )
        return self.request("PUT", "folders/entries", data=data,
                            response_type='raw')

    def remove_from_folder(self, entries_ids, folder_id):
        """Dissociate a list of entries from a folder."""
        url = "folders/%s/entries?move=false" % folder_id
        data = dict(entries=entries_ids, folderId=folder_id)
        return self.request("POST", url, data=data, response_type='raw')
    
    def attach_record_to_part(self, ice_record_id=None, ice_part_id=None,
                              record=None, record_text=None,
                              filename ='auto', record_format='genbank'):
        """Attach a BioPython record or raw text record to a part
        
        Parameters
        ----------
        ice_record_id
          A uuid (like aw3de45-sfjn389-lng563d...) that identifies the record
          attachment of the part in ICE. It is generally the field "recordId"
          when you retrieve a part's infos in ICE. If you have no clue, leave
          this to None and provide a ``ice_part_id`` instead.

        ice_part_id
          The id of an ICE entry that can be provided instead of the
          ``ice_record_id``.

        record
          A Biopython record
        
        record_text
          Raw text from a FASTA/Genbank record.
        
        filename
          If set to "auto", will be "record_id.gb" for genbank format.
        
        record_format
          When providing a fasta format in record_text, set this to "fasta".
        """
        typedata = {
            'fasta': {
                'extension': 'fa',
                'mimetype': 'application/biosequence.fasta'
            },
            'genbank': {
                'extension': 'gb',
                'mimetype': 'application/biosequence.genbank'
            },
        }[record_format]
        
        if ice_record_id is None:
            ice_record_id = self.get_part_infos(ice_part_id)['recordId']

        if record is not None:
            stringio = StringIO()
            SeqIO.write(record, stringio, "genbank")
            record_text = stringio.getvalue()
            if filename == 'auto':
                filename = record.id + '.' + typedata['extension']
        if filename == 'auto':
            filename = 'uploaded_with_icebreaker.' + typedata['extension']

        return self.request(
            "POST", "file/sequence",
            data={'entryType': 'PART', 'entryRecordId': ice_record_id},
            files={'file': (filename, record_text, typedata['mimetype'])},
            response_type='raw'
        )

    def delete_part_record(self, part_id):
        """Remove the record attached to a part."""
        return self.request("DELETE", "parts/%s/sequence" % part_id,
                            response_type="raw")
    
    def get_user_groups(self, user_id="session_id"):
        """List all groups a user (this user by default) is part of."""
        if user_id == "session_id":
            user_id =  self.get_session_user_id()
        return self.request("GET", "users/%s/groups" % user_id)

    def trash_parts(self, part_ids, visible='OK'):
        """Place the list of IDed parts in the trash."""
        return self.request('POST', 'parts/trash',
                            data=[dict(id=part_id, visible=visible)
                                  for part_id in part_ids],
                            response_type="raw")
    
    def find_parts_by_custom_field_value(self, parameter, value):
        """Find all parts whose (extra) field "parameter" is set to "value" """
        results = []
        for entry in self.search(value):
            parameters = self.get_part_custom_fields_list(entry["id"])
            for param in parameters:
                if (param["name"] == parameter) and (param["value"] == value):
                    entry['parameters'] = parameters
                    results.append(entry)
                    break
        return results
    
    def get_collections_list(self):
        """Return a list ['FEATURED', 'SHARED', etc.]"""
        return "FEATURED PERSONAL SHARED DRAFT PENDING DELETED".split()
    
    def rebuild_search_indexes(self):
        """Rebuild the search indexes.

        An OK response does not mean that it is finished, just that the
        rebuild was scheduled.
        """
        return self.request("PUT", "search/indexes/lucene",
                            response_type="raw")
    
    def get_part_custom_fields_list(self, part_id):
        """Return a list of all custom fields for a given part.
        
        Returns a list of the form ``[{name: 'field1', value: 321}, ...]``
        """
        return self.request('GET', "custom-fields?partId=%s" % part_id)
    
    def get_part_custom_field(self, part_id, field_name):
        """Return the value for a part's custom field.
        
        The value will be a list if the part has several values attached to
        that field name.
        """
        fields_list =  self.get_part_custom_fields_list(part_id)
        results = []
        for field in fields_list:
            if field["name"] == field_name:
                results.append(field["value"])
        if len(results) == 0:
            msg = 'Part %s has no custom field "%s".' % (part_id, field_name)
            raise IOError(msg)
        elif len(results) == 1:
            return results[0]
        else:
            return results
    
    def set_part_custom_field(self, part_id, field_name, value):
        data = dict(name=field_name, value=value, partId=part_id, edit=True,
                    nameInvalid=False, valueInvalid=False)
        return self.request("POST", "custom-fields", data=data)
    
    def delete_custom_field(self, custom_field_id):
        return self.request("DELETE", "custom-fields/%s" % custom_field_id,
                            response_type='raw')
    
    # Legacy and super-experimental stuff

    def __get_part_id(self, name, folder_id=None, collection=None,
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
    
    def __get_collection_entries(self, collection, ignored_folders=()):
        """Return all entries in a given collection"""
        return sum([
            self.get_folder_entries(f)
            for f in self.get_collection_folders(collection)
            if f not in ignored_folders
        ], [])
