"""Model setup for fresh models."""

import re
import warnings
from json import JSONDecodeError

from transformers import (
    AutoConfig,
    AutoTokenizer,
    ElectraForQuestionAnswering,
    ElectraForSequenceClassification,
    ElectraForTokenClassification,
    PretrainedConfig,
    PreTrainedModel,
    PreTrainedTokenizer,
    XLMRobertaForQuestionAnswering,
    XLMRobertaForSequenceClassification,
    XLMRobertaForTokenClassification,
)

from ..config import BenchmarkConfig, DatasetConfig, ModelConfig
from ..enums import Framework, ModelType
from ..exceptions import InvalidBenchmark
from ..utils import block_terminal_output
from .base import GenerativeModel, Tokenizer
from .utils import align_model_and_tokenizer, setup_model_for_question_answering

FRESH_MODELS: list[str] = [
    "electra-small",
    "xlm-roberta-base",
]


class FreshModelSetup:
    """Model setup for fresh models.

    Args:
        benchmark_config (BenchmarkConfig):
            The benchmark configuration.

    Attributes:
        benchmark_config (BenchmarkConfig):
            The benchmark configuration.
    """

    def __init__(
        self,
        benchmark_config: BenchmarkConfig,
    ) -> None:
        self.benchmark_config = benchmark_config

    @staticmethod
    def _strip_model_id(model_id: str) -> str:
        return re.sub("(^.*::|@.*$|^fresh-)", "", model_id)

    def model_exists(self, model_id: str) -> bool:
        """Check if a model ID denotes a fresh model.

        Args:
            model_id (str):
                The model ID.

        Returns:
            bool:
                Whether the model exists as a fresh model.
        """
        return self._strip_model_id(model_id=model_id) in FRESH_MODELS

    def get_model_config(self, model_id: str) -> ModelConfig:
        """Fetches configuration for a fresh model.

        Args:
            model_id (str):
                The model ID.

        Returns:
            ModelConfig:
                The model configuration.
        """
        return ModelConfig(
            model_id=self._strip_model_id(model_id=model_id),
            framework=Framework.PYTORCH,
            task="fill-mask",
            languages=list(),
            revision="main",
            model_type=ModelType.FRESH,
        )

    def load_model(
        self, model_config: ModelConfig, dataset_config: DatasetConfig
    ) -> tuple[Tokenizer, PreTrainedModel | GenerativeModel]:
        """Load a fresh model.

        Args:
            model_config (ModelConfig):
                The model configuration.

        Returns:
            pair of (tokenizer, model):
                The tokenizer and model.
        """

        config: PretrainedConfig
        block_terminal_output()

        model_id = model_config.model_id
        supertask = dataset_config.task.supertask

        if model_config.model_id == "xlm-roberta-base":
            if supertask == "sequence-classification":
                model_cls = XLMRobertaForSequenceClassification
            elif supertask == "token-classification":
                model_cls = XLMRobertaForTokenClassification
            elif supertask == "question-answering":
                model_cls = XLMRobertaForQuestionAnswering
            else:
                raise InvalidBenchmark(
                    f"Supertask {supertask} is not supported for model {model_id}"
                )

        elif model_id == "electra-small":
            model_id = "google/electra-small-discriminator"
            if supertask == "sequence-classification":
                model_cls = ElectraForSequenceClassification
            elif supertask == "token-classification":
                model_cls = ElectraForTokenClassification
            elif supertask == "question-answering":
                model_cls = ElectraForQuestionAnswering
            else:
                raise InvalidBenchmark(
                    f"Supertask {supertask} is not supported for model {model_id}"
                )

        else:
            raise InvalidBenchmark(
                f"Model {model_id} is not supported as a fresh class."
            )

        config = AutoConfig.from_pretrained(
            model_id,
            use_auth_token=self.benchmark_config.use_auth_token,
            num_labels=dataset_config.num_labels,
            id2label=dataset_config.id2label,
            label2id=dataset_config.label2id,
            cache_dir=self.benchmark_config.cache_dir,
        )
        model = model_cls(config)

        # Set up the model for question answering
        if supertask == "question-answering":
            model = setup_model_for_question_answering(model=model)

        # Load the tokenizer. If the model is a subclass of a RoBERTa model then we
        # have to add a prefix space to the tokens, by the way the model is constructed
        prefix_models = ["Roberta", "GPT", "Deberta"]
        prefix = any(model_type in type(model).__name__ for model_type in prefix_models)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            try:
                tokenizer: PreTrainedTokenizer = AutoTokenizer.from_pretrained(
                    model_id,
                    revision=model_config.revision,
                    use_auth_token=self.benchmark_config.use_auth_token,
                    add_prefix_space=prefix,
                    cache_dir=self.benchmark_config.cache_dir,
                    use_fast=True,
                    verbose=False,
                )
            except (JSONDecodeError, OSError):
                raise InvalidBenchmark(
                    f"Could not load tokenizer for model {model_id!r}."
                )

        # Align the model and the tokenizer
        model, tokenizer = align_model_and_tokenizer(
            model=model,
            tokenizer=tokenizer,
            raise_errors=self.benchmark_config.raise_errors,
        )

        return tokenizer, model