import pandas as pd
from utils import write_fasta, add_clusters, exclude_common_train_seqs, add_source_to_id, delete_source_from_id
import subprocess


def cluster_data(train: pd.DataFrame, test: pd.DataFrame, identity: float) -> pd.DataFrame:
    train, test = add_source_to_id(train, test)
    train = exclude_common_train_seqs(train, test)

    df = pd.concat([train, test])

    # Prepare fasta before clustering
    write_fasta(df, "merged.fasta")

    # Clustering
    fasta_input = "data/fasta/merged.fasta"
    output_dir = "data/clusters/merged"

    coverage = identity + 0.1

    subprocess.run(f"mmseqs easy-cluster {fasta_input} {output_dir}\
                   tmp --min-seq-id {identity} -c {coverage} --cov-mode 0",
                   shell=True)

    # Parse clusters
    output_mmseqs = pd.read_csv("data/clusters/merged_cluster.tsv",
                                sep="\t", header=None)

    output_mmseqs = add_clusters(output_mmseqs)
    assert len(output_mmseqs) == len(df), f"{len(output_mmseqs)}, {len(df)}"

    output_mmseqs = delete_source_from_id(output_mmseqs)

    return output_mmseqs
