"""Functions related to the loading of models."""

from typing import Type

from transformers import PreTrainedModel, PreTrainedTokenizer

from .config import BenchmarkConfig, DatasetConfig, ModelConfig
from .model_setups import (
    FreshModelSetup,
    HFModelSetup,
    LocalModelSetup,
    ModelSetup,
    OpenAIModelSetup,
)


def load_model(
    model_config: ModelConfig,
    dataset_config: DatasetConfig,
    benchmark_config: BenchmarkConfig,
) -> tuple[PreTrainedTokenizer, PreTrainedModel]:
    """Load a model.

    Args:
        model_config (ModelConfig):
            The model configuration.
        dataset_config (DatasetConfig):
            The dataset configuration.
        benchmark_config (BenchmarkConfig):
            The benchmark configuration.

    Returns:
        pair of (tokenizer, model):
            The tokenizer and model.
    """
    model_type_to_model_setup_mapping: dict[str, Type[ModelSetup]] = dict(
        fresh=FreshModelSetup,
        hf=HFModelSetup,
        local=LocalModelSetup,
        openai=OpenAIModelSetup,
    )
    setup_class = model_type_to_model_setup_mapping[model_config.model_type]
    setup = setup_class(benchmark_config=benchmark_config)
    return setup.load_model(model_config=model_config, dataset_config=dataset_config)
