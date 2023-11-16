import esm
import torch
import biotite

if __name__ == "__main__":
    model = esm.pretrained.esmfold_v1()
    print("Finished downloading model.")
    model = model.eval().cuda()

    # Optionally, uncomment to set a chunk size for axial attention. This can help reduce memory.
    # Lower sizes will have lower memory requirements at the cost of increased speed.
    # model.set_chunk_size(128)

    sequence = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"
    # Multimer prediction can be done with chains separated by ':'

    with torch.no_grad():
        print("Running inference.")
        output = model.infer_pdb(sequence)

    with open("result.pdb", "w") as f:
        f.write(output)

    import biotite.structure.io as bsio

    struct = bsio.load_structure("result.pdb", extra_fields=["b_factor"])
    print(struct.b_factor.mean())
    # remove the pdb file
    os.remove("result.pdb")
