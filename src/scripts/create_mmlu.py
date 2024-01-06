"""Create the MMLU-mini datasets and upload them to the HF Hub."""

import pandas as pd
from datasets import Dataset, DatasetDict, Split, load_dataset
from huggingface_hub import HfApi
from requests import HTTPError
from sklearn.model_selection import train_test_split


def main() -> None:
    """Create the MMLU-mini datasets and upload them to the HF Hub."""
    # Define the base download URL
    repo_id = "alexandrainst/m_mmlu"

    # Create a mapping with the word "Choices" in different languages
    choices_mapping = dict(
        da="Svarmuligheder",
        sv="Svarsalternativ",
        de="Antwortmöglichkeiten",
        nl="Antwoordopties",
    )

    for language in ["da", "sv", "de", "nl"]:
        # Download the dataset
        dataset = load_dataset(path=repo_id, name=language, token=True)
        assert isinstance(dataset, DatasetDict)

        # Convert the dataset to a dataframe
        train_df = dataset["train"].to_pandas()
        val_df = dataset["val"].to_pandas()
        test_df = dataset["test"].to_pandas()
        assert isinstance(train_df, pd.DataFrame)
        assert isinstance(val_df, pd.DataFrame)
        assert isinstance(test_df, pd.DataFrame)

        # Concatenate the splits
        df = pd.concat([train_df, val_df, test_df], ignore_index=True)

        # Rename the columns
        df.rename(columns=dict(answer="label"), inplace=True)

        # Extract the category as a column
        df["category"] = df["id"].str.split("/").str[0]

        # Make a `text` column with all the options in it
        df["text"] = [
            row.instruction.replace("\n", " ").strip() + "\n"
            f"{choices_mapping[language]}:\n"
            f"a. " + row.option_a.replace("\n", " ").strip() + "\n"
            "b. " + row.option_b.replace("\n", " ").strip() + "\n"
            "c. " + row.option_c.replace("\n", " ").strip() + "\n"
            "d. " + row.option_d.replace("\n", " ").strip()
            for _, row in df.iterrows()
        ]

        # Only keep the `text`, `label` and `category` columns
        df = df[["text", "label", "category"]]

        # Remove duplicates
        df.drop_duplicates(inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Create validation split
        val_size = 256
        traintest_arr, val_arr = train_test_split(
            df, test_size=val_size, random_state=4242, stratify=df.category
        )
        traintest_df = pd.DataFrame(traintest_arr, columns=df.columns)
        val_df = pd.DataFrame(val_arr, columns=df.columns)

        # Create test split
        test_size = 2048
        train_arr, test_arr = train_test_split(
            traintest_df,
            test_size=test_size,
            random_state=4242,
            stratify=traintest_df.category,
        )
        train_df = pd.DataFrame(train_arr, columns=df.columns)
        test_df = pd.DataFrame(test_arr, columns=df.columns)

        # Create train split
        train_size = 1024
        train_df = train_df.sample(train_size, random_state=4242)

        # Reset the index
        train_df = train_df.reset_index(drop=True)
        val_df = val_df.reset_index(drop=True)
        test_df = test_df.reset_index(drop=True)

        # Collect datasets in a dataset dictionary
        dataset = DatasetDict(
            train=Dataset.from_pandas(train_df, split=Split.TRAIN),
            val=Dataset.from_pandas(val_df, split=Split.VALIDATION),
            test=Dataset.from_pandas(test_df, split=Split.TEST),
        )

        # Create dataset ID
        dataset_id = f"ScandEval/mmlu-{language}-mini"

        # Remove the dataset from Hugging Face Hub if it already exists
        try:
            api = HfApi()
            api.delete_repo(dataset_id, repo_type="dataset")
        except HTTPError:
            pass

        # Push the dataset to the Hugging Face Hub
        dataset.push_to_hub(dataset_id)


if __name__ == "__main__":
    main()
