"""Create the NoSammendrag-mini summarisation dataset."""

import pandas as pd
from datasets import Dataset, DatasetDict, Split, load_dataset
from huggingface_hub import HfApi
from requests import HTTPError
from scripts.constants import MAX_NUM_CHARS_IN_ARTICLE, MIN_NUM_CHARS_IN_ARTICLE


def main():
    """Create the NoSammendrag-mini summarisation dataset and upload to HF Hub."""
    dataset_id = "norkart/no-sammendrag"

    dataset = load_dataset(dataset_id, split="train", token=True)
    assert isinstance(dataset, Dataset)

    dataset = dataset.rename_columns(
        column_mapping=dict(document="text", summary="target_text")
    )

    df = dataset.to_pandas()
    assert isinstance(df, pd.DataFrame)

    # Only work with samples where the text is not very large or small
    lengths = df.text.str.len()
    lower_bound = MIN_NUM_CHARS_IN_ARTICLE
    upper_bound = MAX_NUM_CHARS_IN_ARTICLE
    df = df[lengths.between(lower_bound, upper_bound)]

    # Create validation split
    val_size = 256
    val_df = df.sample(n=val_size, random_state=4242)

    # Create test split
    test_size = 2048
    filtered_df = df[~df.index.isin(val_df.index)]
    test_df = filtered_df.sample(n=test_size, random_state=4242)

    # Create train split
    train_size = 1024
    filtered_df = filtered_df[~filtered_df.index.isin(test_df.index)]
    train_df = filtered_df.sample(n=train_size, random_state=4242)

    val_df = val_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)
    train_df = train_df.reset_index(drop=True)

    # Collect datasets in a dataset dictionary
    dataset = DatasetDict(
        train=Dataset.from_pandas(train_df, split=Split.TRAIN),
        val=Dataset.from_pandas(val_df, split=Split.VALIDATION),
        test=Dataset.from_pandas(test_df, split=Split.TEST),
    )

    # Create dataset ID
    mini_dataset_id = "ScandEval/no-sammendrag-mini"

    # Remove the dataset from Hugging Face Hub if it already exists
    try:
        api: HfApi = HfApi()
        api.delete_repo(mini_dataset_id, repo_type="dataset")
    except HTTPError:
        pass

    # Push the dataset to the Hugging Face Hub
    dataset.push_to_hub(mini_dataset_id)


if __name__ == "__main__":
    main()