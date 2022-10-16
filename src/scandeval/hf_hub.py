"""Functions related to fetching data from the Hugging Face Hub."""

import logging
from collections import defaultdict
from copy import deepcopy
from typing import Dict, List, Optional, Sequence, Union

from huggingface_hub import HfApi, ModelFilter
from requests.exceptions import RequestException

from scandeval.utils import internet_connection_available

from .config import BenchmarkConfig, Language, ModelConfig
from .exceptions import HuggingFaceHubDown, InvalidBenchmark, NoInternetConnection
from .languages import DA, NB, NN, NO, SV, get_all_languages

logger = logging.getLogger(__name__)


# TODO: Cache this
def get_model_config(model_id: str, benchmark_config: BenchmarkConfig) -> ModelConfig:
    """Fetches configuration for a model from the Hugging Face Hub.

    Args:
        model_id (str):
            The full Hugging Face Hub ID of the model.
        benchmark_config (BenchmarkConfig):
            The configuration of the benchmark.

    Returns:
        ModelConfig:
            The model configuration.

    Raises:
        RuntimeError:
            If the extracted framework is not recognized.
    """
    # If the model ID specifies a random ID, then return a hardcoded metadata
    # dictionary
    if model_id.startswith("random"):
        model_config = ModelConfig(
            model_id=model_id,
            framework="pytorch",
            task="fill-mask",
            languages=list(),
            revision="main",
        )
        return model_config

    # Extract the revision from the model ID, if it is specified
    if "@" in model_id:
        model_id_without_revision, revision = model_id.split("@", 1)
    else:
        model_id_without_revision = model_id
        revision = "main"

    # Extract the author and model name from the model ID
    author: Optional[str]
    if "/" in model_id_without_revision:
        author, model_name = model_id_without_revision.split("/")
    else:
        author = None
        model_name = model_id_without_revision

    # Attempt to fetch model data from the Hugging Face Hub
    try:

        # Define the API object
        api = HfApi()

        # Fetch the model metadata
        models = api.list_models(
            filter=ModelFilter(author=author, model_name=model_name),
            use_auth_token=benchmark_config.use_auth_token,
        )

        # Filter the models to only keep the one with the specified model ID
        models = [
            model for model in models if model.modelId == model_id_without_revision
        ]

        # Check that the model exists. If it does not then raise an error
        if len(models) == 0:
            raise InvalidBenchmark(
                f"The model {model_id} does not exist on the Hugging Face Hub."
            )

        # Fetch the model tags
        tags = models[0].tags

        # Extract the framework, which defaults to PyTorch
        framework = "pytorch"
        if "pytorch" in tags:
            pass
        elif "jax" in tags:
            framework = "jax"
        elif "spacy" in tags:
            raise InvalidBenchmark("SpaCy models are not supported.")
        elif "tf" in tags or "tensorflow" in tags or "keras" in tags:
            raise InvalidBenchmark("TensorFlow/Keras models are not supported.")

        # Extract the model task, which defaults to 'fill-mask'
        model_task: Optional[str] = models[0].pipeline_tag
        if model_task is None:
            model_task = "fill-mask"

        # Get list of all language codes
        language_mapping = get_all_languages()
        language_codes = list(language_mapping.keys())

        # Construct the model config
        model_config = ModelConfig(
            model_id=models[0].modelId,
            framework=framework,
            task=model_task,
            languages=[language_mapping[tag] for tag in tags if tag in language_codes],
            revision=revision,
        )

    # If fetching from the Hugging Face Hub failed then throw a reasonable exception
    except RequestException:
        if internet_connection_available():
            raise HuggingFaceHubDown()
        else:
            raise NoInternetConnection()

    # Return the model config
    return model_config


# TODO: Cache this
def get_model_lists(
    languages: Optional[Sequence[Language]],
    use_auth_token: Union[bool, str],
) -> Dict[str, Sequence[str]]:
    """Fetches up-to-date model lists.

    Args:
        languages (None or sequence of Language objects):
            The language codes of the language to consider. If None then the models
            will not be filtered on language.
        use_auth_token (bool or str):
            The authentication token for the Hugging Face Hub. If a boolean value is
            specified then the token will be fetched from the Hugging Face CLI, where
            the user has logged in through `huggingface-cli login`. If a string is
            specified then it will be used as the token. Defaults to False.

    Returns:
        dict:
            The keys are filterings of the list, which includes all language codes,
            including 'multilingual', as well as 'all'. The values are lists
            of model IDs.
    """
    # Get list of all languages
    all_languages = list(get_all_languages().values())

    # If no languages are specified, then include all languages
    language_list = all_languages if languages is None else languages

    # Form string of languages
    if len(language_list) == 1:
        language_string = f"the language {language_list[0].name}"
    else:
        language_list = sorted(language_list, key=lambda x: x.name)
        if {lang.code for lang in language_list} == {
            lang.code for lang in all_languages
        }:
            language_string = "all languages"
        else:
            language_string = (
                f"the languages {', '.join(l.name for l in language_list[:-1])} "
                f"and {language_list[-1].name}"
            )

    # Log fetching message
    logger.info(
        f"Fetching list of models for {language_string} from the Hugging Face Hub."
    )

    # Initialise the API
    api = HfApi()

    # Initialise model lists
    model_lists = defaultdict(list)

    # Do not iterate over all the languages if we are not filtering on language
    language_itr: Sequence[Optional[Language]]
    if {lang.code for lang in language_list} == {lang.code for lang in all_languages}:
        language_itr = [None]
    else:
        language_itr = deepcopy(language_list)

    for language in language_itr:

        # Fetch the model list
        models = api.list_models(
            filter=ModelFilter(language=language),
            use_auth_token=use_auth_token,
        )

        # Filter the models to only keep the ones with the specified language
        models = [
            model
            for model in models
            if (language is None or language.code in model.tags)
        ]

        # Extract the model IDs
        model_ids = [model.id for model in models]

        # Store the model IDs
        model_lists["all"].extend(model_ids)
        if language is not None:
            model_lists[language.code].extend(model_ids)

    # Add multilingual models manually
    multi_models = [
        "xlm-roberta-large",
        "Peltarion/xlm-roberta-longformer-base-4096",
        "microsoft/xlm-align-base",
        "microsoft/infoxlm-base",
        "microsoft/infoxlm-large",
        "bert-base-multilingual-cased",
        "bert-base-multilingual-uncased",
        "distilbert-base-multilingual-cased",
        "cardiffnlp/twitter-xlm-roberta-base",
    ]
    model_lists["multilingual"] = multi_models
    model_lists["all"].extend(multi_models)

    # Add random models
    random_models = [
        "random-xlmr-base-sequence-clf",
        "random-xlmr-base-token-clf",
        "random-electra-small-sequence-clf",
        "random-electra-small-token-clf",
    ]
    model_lists["random"].extend(random_models)
    model_lists["all"].extend(random_models)

    # Add some multilingual Danish models manually that have not marked 'da' as their
    # language
    if DA in language_itr:
        multi_da_models: List[str] = [
            "Geotrend/bert-base-en-da-cased",
            "Geotrend/bert-base-25lang-cased",
            "Geotrend/bert-base-en-fr-de-no-da-cased",
            "Geotrend/distilbert-base-en-da-cased",
            "Geotrend/distilbert-base-25lang-cased",
            "Geotrend/distilbert-base-en-fr-de-no-da-cased",
        ]
        model_lists["da"].extend(multi_da_models)
        model_lists["all"].extend(multi_da_models)

    # Add some multilingual Swedish models manually that have not marked 'sv' as their
    # language
    if SV in language_itr:
        multi_sv_models: List[str] = []
        model_lists["sv"].extend(multi_sv_models)
        model_lists["all"].extend(multi_sv_models)

    # Add some multilingual Norwegian models manually that have not marked 'no', 'nb'
    # or 'nn' as their language
    if any(lang in language_itr for lang in [NO, NB, NN]):
        multi_no_models: List[str] = [
            "Geotrend/bert-base-en-no-cased",
            "Geotrend/bert-base-25lang-cased",
            "Geotrend/bert-base-en-fr-de-no-da-cased",
            "Geotrend/distilbert-base-en-no-cased",
            "Geotrend/distilbert-base-25lang-cased",
            "Geotrend/distilbert-base-en-fr-de-no-da-cased",
        ]
        model_lists["no"].extend(multi_no_models)
        model_lists["all"].extend(multi_no_models)

    # Remove duplicates from the lists
    for lang, model_list in model_lists.items():
        model_lists[lang] = list(set(model_list))

    return dict(model_lists)
