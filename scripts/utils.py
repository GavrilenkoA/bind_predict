from functools import wraps
import pandas as pd


SEED = 42


def make_balanced_df(df, seed=SEED):
    pos_cls = df[df.label == 1]
    neg_cls = df[df.label == 0]
    if len(neg_cls) > len(pos_cls):
        neg_cls = neg_cls.sample(n=len(pos_cls), random_state=seed)
    elif len(neg_cls) < len(pos_cls):
        pos_cls = pos_cls.sample(n=len(neg_cls), random_state=seed)
    balanced_df = pd.concat([pos_cls, neg_cls])
    return balanced_df


def reduce_train(output_mmseq):
    a = output_mmseq.loc[output_mmseq["source"] == "train"]
    b = output_mmseq.loc[output_mmseq["source"] == "test"]

    exclude_train = a.merge(b,
                            on=["cluster"])["identifier_x"].drop_duplicates()

    a = a.loc[~a["identifier"].isin(exclude_train)]
    a = a.drop("source", axis=1)
    return a


def save_csv(df: pd.DataFrame, basename: str, path: str = "data/embeddings/input_csv/") -> None:
    path = path + f"{basename}.csv"
    df.to_csv(path, index=False)


def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    def valid_sequence(sequence: str) -> bool:
        valid_amino_acids = "SNYLRQDPMFCEWGTKIVAH"
        return all(char in valid_amino_acids for char in sequence)

    df = df.loc[df["sequence"].apply(valid_sequence)]
    df = df.loc[df["sequence"].apply(lambda x: 49 < len(x) < 1025)]
    df = df.drop_duplicates(subset=["sequence"])
    return df


def write_fasta(df: pd.DataFrame, name_file: str) -> None:
    def pull_data(x):
        id_ = x["identifier"]
        seq = x["sequence"]
        return id_, seq

    data = df.apply(lambda x: pull_data(x), axis=1).tolist()

    with open(f"data/fasta/{name_file}", "w") as file:
        for item in data:
            file.write(">" + f"{item[0]}")
            file.write("\n")
            file.write(f"{item[1]}")
            file.write("\n")


def collect_df(content: str) -> pd.DataFrame:
    lines = content.split("\n")
    identifiers = []
    sequences = []
    seq = ""

    for line in lines:
        if line.startswith(">"):
            head = line.split("|")[1]
            identifiers.append(head)
            if seq:
                sequences.append(seq)
                seq = ""
        else:
            seq += line.strip()

    if seq:
        sequences.append(seq)

    assert len(identifiers) == len(sequences)
    df = pd.DataFrame({"identifier": identifiers,
                       "sequence": sequences})
    return df


def convert_fasta_to_df(fasta_file: str) -> pd.DataFrame:
    with open(fasta_file) as fi:
        content = fi.read()
    df = collect_df(content)
    return df


def extract_columns(fasta_file: str, column1: str = "identifier", column2: str = "sequence") -> tuple[list]:
    df = convert_fasta_to_df(fasta_file)
    part_1 = df.loc[:, column1].to_list()
    part_2 = df.loc[:, column2].to_list()
    return part_1, part_2


def select_columns(columns):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            df = func(*args, **kwargs)
            return df.loc[:, columns]
        return wrapper
    return decorator


@select_columns(["identifier", "cluster"])
def add_clusters(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = ["repr", "identifier"]

    reprs = df["repr"].to_list()
    clusters = []
    count = 0
    name = ""
    for item in reprs:
        if item != name:
            count += 1
            name = item
        clusters.append(count)

    df["cluster"] = clusters
    return df


def exclude_common_train_seqs(train, test):
    # delete common seqs from train
    common_id = test.merge(train, on=["sequence"])["identifier_y"]
    train = train.loc[~train["identifier"].isin(common_id)]
    return train


def add_source_to_id(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame]:
    train["identifier"] = train["identifier"].apply(lambda x: x + "_train")
    test["identifier"] = test["identifier"].apply(lambda x: x + "_test")
    return train, test


def delete_source_from_id(df: pd.DataFrame) -> pd.DataFrame:
    df["source"] = df.identifier.apply(lambda x: x.split("_")[1])
    df["identifier"] = df.identifier.apply(lambda x: x.split("_")[0])
    return df


def delete_common_seqs(train: pd.DataFrame,
                       test: pd.DataFrame) -> tuple[pd.DataFrame]:

    # delete common seqs from both dataframes
    common_seqs = test.merge(train, on=["sequence"])["sequence"]

    train_sep = train.loc[~train["sequence"].isin(common_seqs)]
    test_sep = test.loc[~test["sequence"].isin(common_seqs)]

    return train_sep, test_sep


def find_common_seqs(train: pd.DataFrame, test: pd.DataFrame) -> list[str]:
    # find common seqs in test
    common_seqs = test.merge(train, on=["sequence"])["identifier_x"].to_list()
    return common_seqs


def intersect_cluster_seq(df: pd.DataFrame, source: str = "test") -> list[int]:
    id_seqs = []
    grouped = df.groupby("cluster")
    for _, group in grouped:
        if group["source"].nunique() > 1:
            id_ = group[group["source"] == source]["identifier"].to_list()
            id_seqs.extend(id_)
    return id_seqs
