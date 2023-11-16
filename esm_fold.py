import csv
import io
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Annotated, List, Optional

import esm
from esm.data import read_fasta
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from ray import serve
from pydantic import BaseModel, Field
import tempfile
from starlette.responses import StreamingResponse

from timeit import default_timer as timer

from esm_code.fold import create_batched_sequence_datasest


app = FastAPI()


class SequenceInput(BaseModel):
    """
    A sequence input to the model.
    """

    name: Optional[str] = Field(
        None,
        description="Name for the sequence. If not provided, the sequence will be named the first 20 letters of the sequence.",
    )
    sequence: str = Field(description="The protein sequence to fold.")


class FoldOutput(BaseModel):
    """
    A folded sequence output from the model.
    """

    name: str = Field(description="Name of the sequence.")
    sequence: str = Field(description="The protein sequence.")
    pdb_string: str = Field(
        description="The pdb string of the folded sequence. Save this string to a .pdf file."
    )
    mean_plddt: float = Field(description="The mean pLDDT of the folded sequence.")
    ptm: float = Field(description="The pTM of the folded sequence.")


class InferenceParams(BaseModel):
    """
    These params be used to manage memory usage during inference.
    """
    num_recycles: Optional[int] = Field(4,
            description="Number of recycles to run. Defaults to number "
                        "used in training (4)."
        )
    max_tokens_per_batch: Optional[int] = Field(1024,
            description="Maximum number of tokens per gpu "
                        "forward-pass. This will group shorter "
                        "sequences together for batched prediction. "
                        "Lowering this can help with out of memory "
                        "issues, if these occur on short sequences. "
                        "Default: 1024.",
        )
    chunk_size: Optional[int] = Field(
        None,
        description="Chunks axial attention computation to reduce memory usage from O(L^2) to O(L). Equivalent to running a for loop over chunks of each dimension. Lower values will result in lower memory usage at the cost of speed. Recommended values: 128, 64, 32. Default: None.",
    )


def save_upload_file_tmp(upload_file: UploadFile) -> Path:
    try:
        suffix = Path(upload_file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            tmp_path = Path(tmp.name)
    finally:
        upload_file.file.close()
    return tmp_path


@serve.deployment(route_prefix="/", ray_actor_options={"num_cpus": 7, "num_gpus": 1})
@serve.ingress(app)
class MyFastAPIDeployment:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.log(logging.INFO, "Loading model...")
        self.model = esm.pretrained.esmfold_v1()
        self.logger.log(logging.INFO, "Model loaded.")
        self.model = self.model.eval().cuda()
        self.logger.log(logging.INFO, "Model set to eval and cuda.")

    # @app.post("/set_model_inference_hyperparams")
    # async def set_model_inference_hyperparams(
    #     self, params: ModelInferenceHyperparameters
    # ):
    #     """
    #     Set the model inference hyperparameters. This can be used to manage memory usage during inference.
    #     Returns a dictionary with the previous and current values of the chunk_size parameter.
    #     """
    #     self.model.set_chunk_size(params.chunk_size)
    #     return {
    #         "prev_params": {"chunk_size": self.model.trunk.chunk_size},
    #         "curr_params": {"chunk_size": params.chunk_size},
    #     }

    @app.post(
        "/fold_sequences",
    )
    async def fold_sequences(
        self,
        seqs: Annotated[
            List[SequenceInput],
            Body(
                description="A list of sequences to fold.",
                examples=[{
                    "Jessica": {"value": [
                        {
                            "name": "seq1",
                            "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                        },
                        {
                            "name": "seq2",
                            "sequence": "KALTARQQEVFDLIRDHISQTGMPPTRAEIAQRLGFRSPNAAEEHLKALARKGVIEIVSGASRGIRLLQEE",
                        },
                    ]},
                    "Tom": {"value": [
                        {
                            "name": "seq4",
                            "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                        },
                        {
                            "name": "seq3",
                            "sequence": "KALTARQQEVFDLIRDHISQTGMPPTRAEIAQRLGFRSPNAAEEHLKALARKGVIEIVSGASRGIRLLQEE",
                        },
                    ]},
                }],
            ),
        ],
        inference_params: Optional[InferenceParams] = InferenceParams(),
    ) -> List[FoldOutput]:
        """
        Fold a list of sequences.
        """
        try:
            # set the inference hyperparameters
            self.model.set_chunk_size(inference_params.chunk_size)

            for seq_input in seqs:
                if not seq_input.name:
                    seq_input.name = seq_input.sequence[:20]

            # convert to a list of tuples
            seqs = [(seq_input.name, seq_input.sequence) for seq_input in seqs]

            batched_sequences = create_batched_sequence_datasest(
                seqs, inference_params.max_tokens_per_batch
            )

            num_completed = 0
            num_sequences = len(seqs)
            outputs = []
            for headers, sequences in batched_sequences:
                start = timer()
                try:
                    output = self.model.infer(sequences, num_recycles=inference_params.num_recycles)
                except RuntimeError as e:
                    if e.args[0].startswith("CUDA out of memory"):
                        if len(sequences) > 1:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Failed (CUDA out of memory) to predict batch of size {len(sequences)}. "
                                "Try lowering the max_tokens_per_batch parameter.",
                            )
                        else:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Failed (CUDA out of memory) on sequence {headers[0]} of length {len(sequences[0])}. "
                                f"Try lowering the max_tokens_per_batch parameter, or setting the chunk size with the"
                                f"`set_model_inference_hyperparameters` endpoint.",
                            )
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Exception {e} occurred while predicting sequence {headers[0]} of length {len(sequences[0])}: {e}.",
                        )

                output = {key: value.cpu() for key, value in output.items()}
                pdbs = self.model.output_to_pdb(output)
                tottime = timer() - start
                time_string = f"{tottime / len(headers):0.1f}s"
                if len(sequences) > 1:
                    time_string = (
                        time_string + f" (amortized, batch size {len(sequences)})"
                    )

                for header, seq, pdb_string, mean_plddt, ptm in zip(
                    headers, sequences, pdbs, output["mean_plddt"], output["ptm"]
                ):
                    res = FoldOutput(
                        name=header,
                        sequence=seq,
                        pdb_string=pdb_string,
                        mean_plddt=mean_plddt,
                        ptm=ptm,
                    )
                    outputs.append(res)
                    num_completed += 1
                    self.logger.info(
                        f"Predicted structure for {header} with length {len(seq)}, pLDDT {mean_plddt:0.1f}, "
                        f"pTM {ptm:0.3f} in {time_string}. "
                        f"{num_completed} / {num_sequences} completed."
                    )

            return outputs
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to fold sequences: {e}"
            )
        finally:
            # reset the inference hyperparameters
            self.model.set_chunk_size(None)

    @app.post("/fold_sequence")
    async def fold_sequence(
        self,
        sequence: Annotated[str, Body(description="The sequence to fold.")],
        name: Annotated[
            Optional[str],
            Body(
                description="Name of the sequence. If not provided, the sequence will be named the first 20 letters of the sequence."
            ),
        ] = None,
        inference_params: Optional[InferenceParams] = InferenceParams(),
    ) -> FoldOutput:
        """
        Fold a sequence.
        """
        if not name:
            name = sequence[:20]
        return (
            await self.fold_sequences(
                [SequenceInput(name=name, sequence=sequence)], inference_params
            )
        )[0]

    @app.post("/fold_fasta")
    async def fold_fasta(
        self,
        fasta: Annotated[
            UploadFile, File(description="A fasta file containing sequences to fold.")
        ],
        inference_params: Optional[InferenceParams] = InferenceParams(),
    ) -> List[FoldOutput]:
        """
        Fold sequences from a fasta file. Use the `fold_fasta/zipped` endpoint if you'd like a zip with pdb files for each sequence.
        """
        try:
            tmp_path = save_upload_file_tmp(fasta)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to save fasta: {e}")

        try:
            all_sequences = sorted(
                read_fasta(tmp_path), key=lambda header_seq: len(header_seq[1])
            )
            seqs = [
                SequenceInput(name=header, sequence=seq)
                for header, seq in all_sequences
            ]
            return await self.fold_sequences(seqs, inference_params)

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to fold fasta: {e}")
        finally:
            tmp_path.unlink()

    @app.post("/fold_fasta/zipped")
    async def fold_fasta_zipped(
        self,
        fasta: Annotated[
            UploadFile, File(description="A fasta file containing sequences to fold.")
        ],
        inference_params: Optional[InferenceParams] = InferenceParams(),
    ) -> StreamingResponse:
        """
        Fold sequences from a fasta file and download the results as a zip file. Use the `fold_fasta` endpoint if you'd
        like to return the results as a list.
        Returns a zip file containing the pdb files and a csv file with the confidence metrics for each sequence.
        """
        try:
            results = await self.fold_fasta(fasta, inference_params)

            in_memory_zip = io.BytesIO()
            with zipfile.ZipFile(in_memory_zip, "w") as zf:
                # Create the CSV in-memory
                csv_data = io.StringIO()
                csv_writer = csv.writer(csv_data)
                csv_writer.writerow(["Name", "Sequence", "mean_plddt", "ptm"])

                for result in results:
                    pdb_filename = f"{result.name}.pdb"
                    zf.writestr(pdb_filename, result.pdb_string)
                    csv_writer.writerow(
                        [result.name, result.sequence, result.mean_plddt, result.ptm]
                    )

                # Save the CSV to the zip
                csv_data.seek(0)
                zf.writestr("confidence_metrics.csv", csv_data.getvalue())

            in_memory_zip.seek(0)
            return StreamingResponse(
                in_memory_zip,
                media_type="application/zip",
                headers={"Content-Disposition": "attachment; filename=output.zip"},
            )

        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to fold fasta zipped: {e}"
            )


deployment = MyFastAPIDeployment.bind()
