IceBreaker
----------

..
    .. image:: https://travis-ci.org/Edinburgh-Genome-Foundry/icebreaker.svg?branch=master
        :target: https://travis-ci.org/Edinburgh-Genome-Foundry/icebreaker

    .. image:: https://coveralls.io/repos/github/Edinburgh-Genome-Foundry/icebreaker/badge.svg?branch=master
        :target: https://coveralls.io/github/Edinburgh-Genome-Foundry/icebreaker?branch=master


Icebreaker provides a Python interface for the `JBEI ICE sample manager <https://github.com/JBEI/ice>`_.

See the full API documentation `here <https://edinburgh-genome-foundry.github.io/icebreaker/>`_

Installation
-------------

Icebreaker is written for Python 3+. You can install icebreaker via PIP:

.. code::

    sudo pip install icebreaker

Alternatively, you can unzip the sources in a folder and type

.. code::

    sudo python setup.py install

Example of use
---------------

In this example we assume that we are a lab who wants to find primers from its
database to sequence a given construct. We will (1) pull all our primers from
ICE, (2) find which primers are adapted to our sequence, using the
`Primavera package <https://edinburgh-genome-foundry.github.io/Primavera/>`_, and
(3) we will ask ICE for the location of the selected primers.

Connexion to an ICE instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can connecct to your ICE instance using either an API token (see below
for how to create a token), or an email/password authentication.

.. code:: python

    import icebreaker

    # CONNECT TO ICE
    configuration = dict(
        root="https://my.ice.instance.org",
        token="WMnlYlWHz+BC+7eFV=...",
        client = "icebot"
    )
    ice = icebreaker.IceClient(configuration)

Or:

.. code:: python

    # CONNECT TO ICE
    configuration = dict(
        root="https://my.ice.instance.org",
        email="michael.swann@genomefoundry.org",
        password = "ic3ic3baby"
    )
    ice = icebreaker.IceClient(configuration)

The configuration can also be written in a yaml file so you can write
``IceClient('config.yml')`` where ``config.yml`` reads as follows:

.. code:: yaml

    root: https://my.ice.instance.org
    email: michael.swann@genomefoundry.org
    password: ic3ic3baby

Extracting all records from a folder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next we pull all primers in the database:

.. code:: python

    # FIND THE ID OF THE FOLDER WITH ALL PRIMERS
    primers_folder = ice.get_folder_id("PRIMERS", collection="SHARED")

    # GET INFOS ON ALL ENTRIES IN THE FOLDER (PRIMER NAME, ID, CREATOR...)
    primers_entries = ice.get_folder_entries(primers_folder)

    # GET A BIOPYTHON RECORD FOR EACH PRIMER
    primers_records = {primer["id"]: ice.get_record(primer["id"])
                       for primer in primers_entries}


Primer selection with Primavera
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Next provide this information to Primavera and select some primers (see the
`Primavera docs <https://edinburgh-genome-foundry.github.io/Primavera/>`_):

.. code:: python

    from primavera import PrimerSelector, Primer, load_record

    available_primers = [
        Primer(sequence=primers_records[entry['id']].seq.tostring(),
            name=entry['name'],
            metadata=dict(ice_id=entry['id']))
        for entry in primers_entries
    ]
    constructs = [load_record("RTM3_39.gb", linear=False)]
    selector = PrimerSelector(read_range=(150, 1000), tm_range=(55, 70),
                            size_range=(16, 25), coverage_resolution=10,
                            primer_reuse_bonus=200)
    selected_primers = selector.select_primers(constructs, available_primers)


Finding available samples
~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally we look for available samples for each primer:

.. code:: python

    selected_primers = set(sum(selected_primers, []))
    for primer in selected_primers:
        ice_id = primer.metadata.get("ice_id", None)
        if ice_id is not None:
            samples = ice.get_samples(ice_id)
            if len(samples) > 0:
                location = icebreaker.sample_location_string(samples[0])
                print("Primer %s is in %s." % (primer.name, location))

Result:

.. code:: bash

    Primer PRV_EMMA_IN00042 is in PRIMER_PLATE_1/E06.
    Primer PRV_EMMA_IN00043 is in PRIMER_PLATE_1/F06.
    Primer PRV_EMMA_IN00028 is in PRIMER_PLATE_1/G04.
    Primer PRV_EMMA_IN00060 is in PRIMER_PLATE_1/G08.
    Primer PRV_EMMA_IN00064 is in PRIMER_PLATE_1/C09.
    Primer PRV_EMMA_IN00038 is in PRIMER_PLATE_1/A06.
    Primer PRV_EMMA_IN00068 is in PRIMER_PLATE_1/G09.

Getting an ICE token
--------------------

There are several ways to get ICE tokens. We suggest you create one throug
the web interface as follows (see screenshot for indications):

0. Create an account with administrator rights
1. Go to the administrator panel
2. Click on "API keys"
3. Click on "create new". Note everything down !

.. image:: https://github.com/Edinburgh-Genome-Foundry/icebreaker/raw/master/docs/_static/api_key_screenshot.png
   :alt: screenshot
   :align: center

License = MIT
--------------

Icebreaker is an open-source software originally written at the Edinburgh
Genome Foundry by `Zulko <https://github.com/Zulko>`_ and `released on
Github <https://github.com/Edinburgh-Genome-Foundry/icebreaker>`_ under
the MIT licence (Copyright Edinburg Genome Foundry). Everyone is welcome to
contribute !


More biology software
-----------------------

.. image:: https://raw.githubusercontent.com/Edinburgh-Genome-Foundry/Edinburgh-Genome-Foundry.github.io/master/static/imgs/logos/egf-codon-horizontal.png
 :target: https://edinburgh-genome-foundry.github.io/

Icebreaker is part of the `EGF Codons <https://edinburgh-genome-foundry.github.io/>`_ synthetic biology software suite for DNA design, manufacturing and validation.
