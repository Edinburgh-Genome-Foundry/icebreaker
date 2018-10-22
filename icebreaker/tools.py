from io import StringIO
from Bio import SeqIO
from fuzzywuzzy import process
import re

def did_you_mean(name, other_names, limit=5, min_score=50):
    results = process.extract(name, list(other_names), limit=limit)
    return [e for (e, score) in results if score >= min_score]

def ice_genbank_to_record(genbank_txt):
    def remove_spaces_in_first_line(line):
        elements = line[12:].split("  ")
        elements[0] = elements[0].replace(' ', '_')
        return line[:12] + "  ".join(elements)
    if hasattr(genbank_txt, 'decode'):
        genbank_txt = genbank_txt.decode()
    lines = genbank_txt.splitlines()
    lines[0] = remove_spaces_in_first_line(lines[0])
    lines[0] += max(0, 80 - len(lines[0])) * ' '
    genbank_txt = '\n'.join(lines)
    return SeqIO.read(StringIO(genbank_txt), format='genbank')

def load_record(filename, name="unnamed", fmt='auto'):
    """Load a FASTA/Genbank/... record"""
    if fmt is not 'auto':
        record = SeqIO.read(filename, fmt)
    elif filename.lower().endswith(("gb", "gbk")):
        record = SeqIO.read(filename, "genbank")
    elif filename.lower().endswith(('fa', 'fasta')):
        record = SeqIO.read(filename, "fasta")
    else:
        raise ValueError('Unknown format for file: %s' % filename)
    if name != "unnamed":
        record.id = name
        record.name = name.replace(" ", "_")[:20]
    return record

def sanitize_well_name(well_name):
    matches = re.match("([A-Z]*)(\d+)", well_name)
    if matches is None:
        raise ValueError("%s is not a valid well name." % well_name)
    letter, number = matches.groups()
    return letter + "%02d" % int(number)
