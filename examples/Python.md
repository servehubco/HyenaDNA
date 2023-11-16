
# Fold a sequence

```python
import servehub
res = servehub.run(
    "{{ deployment }}",
    "fold_sequence",
    sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
    num_recycles=4,
)
print(res)
# {
#     "name": "MKTVRQERLKSIVRILERSKE", # name defaults to first 20 characters of sequence if not provided
#     "sequence": "KALTARQQEVFDLIRDHISQTGMPPTRAEIAQRLGFRSPNAAEEHLKALARKGVIEIVSGASRGIRLLQEE",
#     "pdb_string": "...",
#     "mean_plddt": 88.27366638183594,
#     "ptm": 0.8401376008987427,
# }
```

# Fold a list of sequences

```python
import servehub
res = servehub.run(
    "{{ deployment }}",
    "fold_sequences",
    seqs=[
        {
            "name": "seq1",
            "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
        },
        {
            "name": "seq2",
            "sequence": "KALTARQQEVFDLIRDHISQTGMPPTRAEIAQRLGFRSPNAAEEHLKALARKGVIEIVSGASRGIRLLQEE",
        },
    ],
    num_recycles=4,
    max_tokens_per_batch=1024,
)
print(res)
# [
#     {
#         "name": "seq1",
#         "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
#         "pdb_string": "...",
#         "mean_plddt": 88.27366638183594,
#         "ptm": 0.8401376008987427,
#     },
#     {
#         "name": "seq2",
#         "sequence": "KALTARQQEVFDLIRDHISQTGMPPTRAEIAQRLGFRSPNAAEEHLKALARKGVIEIVSGASRGIRLLQEE",
#         "pdb_string": "...",
#         "mean_plddt": 82.7134780883789,
#         "ptm": 0.8045980930328369,
#     },
# ]
```

# Fold sequences in a fasta file

```python
from pathlib import Path
import servehub

# Get the directory of the script
script_dir = Path(__file__).parent

# Construct the full path to the file
filename = Path(script_dir / "data/example.fasta")

with open(filename, "rb") as f:
    res = servehub.run(
        "{{ deployment }}",
        "fold_fasta",
        files={"fasta": f},
        num_recycles=4,
        max_tokens_per_batch=1024,
    )
print(res)
# [
#     {
#         "name": "seq1",
#         "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
#         "pdb_string": "...",
#         "mean_plddt": 88.27366638183594,
#         "ptm": 0.8401376008987427,
#     },
#     {
#         "name": "seq2",
#         "sequence": "KALTARQQEVFDLIRDHISQTGMPPTRAEIAQRLGFRSPNAAEEHLKALARKGVIEIVSGASRGIRLLQEE",
#         "pdb_string": "...",
#         "mean_plddt": 82.7134780883789,
#         "ptm": 0.8045980930328369,
#     },
# ]
```

# Fold sequences in a fasta file and return a zip file of the results

The zip file will contain a csv file with rows corresponding to the confidence metrics (`ptm` and `mean_plddt`) for each sequence, and a pdb file for each sequence.

```python
from pathlib import Path
import servehub

# Get the directory of the script
script_dir = Path(__file__).parent

# Construct the full path to the file
filename = Path(script_dir / "data/example.fasta")

output_path = Path(script_dir / "output/example.zip")

with open(filename, "rb") as f:
    res = servehub.run(
        "{{ deployment }}",
        "fold_fasta/zipped",
        files={"fasta": f},
        num_recycles=4,
        max_tokens_per_batch=1024,
    )

    with open(output_path, "wb") as f_out:
        # Process the response as a stream to avoid loading the entire file into memory if it is large
        for chunk in res.iter_content(chunk_size=8192):
            f_out.write(chunk)

    # Close the response object
    res.close()
```
