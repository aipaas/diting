"""Tests for synthesis module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from diting_core.cases.llm_case import LLMCase
from diting_web.workers.synthesis import SynthesisRunner


class TestCreateSynthesizer:
    """Tests for SynthesisRunner.create_synthesizer."""

    @patch("diting_web.utils.model_helpers.create_llm_from_config")
    def test_create_synthesizer_qa(self, mock_create_llm):
        """Test creating QA synthesizer."""
        # Arrange
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        llm_config = {"model_name": "gpt-4"}

        # Act
        synthesizer = SynthesisRunner.create_synthesizer(
            synthesizer_type="qa",
            llm_config=llm_config,
        )

        # Assert
        assert synthesizer is not None
        assert synthesizer.__class__.__name__ == "QASynthesizer"
        mock_create_llm.assert_called_once_with(llm_config)

    @patch("diting_web.utils.model_helpers.create_llm_from_config")
    def test_create_synthesizer_qa_synthesizer_alias(self, mock_create_llm):
        """Test creating synthesizer with 'qa_synthesizer' alias."""
        # Arrange
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        # Act
        synthesizer = SynthesisRunner.create_synthesizer(
            synthesizer_type="qa_synthesizer",
            llm_config={"model_name": "gpt-4"},
        )

        # Assert
        assert synthesizer is not None
        assert synthesizer.__class__.__name__ == "QASynthesizer"

    def test_create_synthesizer_unknown_raises_error(self):
        """Test that unknown synthesizer type raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown synthesizer"):
            SynthesisRunner.create_synthesizer(
                synthesizer_type="unknown_type",
                llm_config={"model_name": "gpt-4"},
            )

    @patch("diting_web.utils.model_helpers.create_llm_from_config")
    def test_create_synthesizer_with_params(self, mock_create_llm):
        """Test creating synthesizer with additional parameters."""
        # Arrange
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        synthesizer_params = {
            "max_generation_per_context": 5,
            "quality_threshold": 0.8,
        }

        # Act
        synthesizer = SynthesisRunner.create_synthesizer(
            synthesizer_type="qa",
            llm_config={"model_name": "gpt-4"},
            synthesizer_params=synthesizer_params,
        )

        # Assert
        assert synthesizer.max_generation_per_context == 5
        assert synthesizer.quality_threshold == 0.8

    @patch("diting_web.utils.model_helpers.create_llm_from_config")
    def test_create_synthesizer_handles_llm_creation_error(self, mock_create_llm):
        """Test that LLM creation errors are propagated."""
        # Arrange
        mock_create_llm.side_effect = Exception("LLM creation failed")

        # Act & Assert
        with pytest.raises(Exception, match="LLM creation failed"):
            SynthesisRunner.create_synthesizer(
                synthesizer_type="qa",
                llm_config={"model_name": "invalid"},
            )


class TestRunSynthesis:
    """Tests for SynthesisRunner.run_synthesis."""

    @pytest.mark.asyncio
    @patch("diting_web.workers.synthesis.SynthesisRunner.create_synthesizer")
    async def test_run_synthesis_success(self, mock_create_synthesizer, mock_corpus_data):
        """Test successful synthesis run."""
        # Arrange
        mock_synthesizer = MagicMock()
        
        # Create mock LLMCase results
        mock_results = [
            LLMCase(
                user_input="What is Python?",
                expected_output="Python is a programming language.",
                context=mock_corpus_data["context"],
                metadata={"score": 0.9, "synthesizer": "qa_synthesizer"},
            ),
            LLMCase(
                user_input="Who created Python?",
                expected_output="Guido van Rossum created Python.",
                context=mock_corpus_data["context"],
                metadata={"score": 0.85, "synthesizer": "qa_synthesizer"},
            ),
        ]
        
        # Mock apply method to return results
        mock_synthesizer.apply = AsyncMock(side_effect=mock_results)
        mock_create_synthesizer.return_value = mock_synthesizer

        llm_config = {"model_name": "gpt-4"}
        num_generations = 2

        # Act
        results = await SynthesisRunner.run_synthesis(
            synthesizer_type="qa",
            corpus_data=mock_corpus_data,
            llm_config=llm_config,
            num_generations=num_generations,
        )

        # Assert
        assert len(results) == 2
        assert results[0]["question"] == "What is Python?"
        assert results[0]["answer"] == "Python is a programming language."
        assert results[0]["context"] == mock_corpus_data["context"]
        assert results[0]["metadata"]["score"] == 0.9
        
        assert results[1]["question"] == "Who created Python?"
        assert mock_synthesizer.apply.call_count == 2

    @pytest.mark.asyncio
    @patch("diting_web.workers.synthesis.SynthesisRunner.create_synthesizer")
    async def test_run_synthesis_single_generation(
        self, mock_create_synthesizer, mock_corpus_data
    ):
        """Test synthesis with single generation."""
        # Arrange
        mock_synthesizer = MagicMock()
        mock_result = LLMCase(
            user_input="Test question?",
            expected_output="Test answer.",
            context=mock_corpus_data["context"],
        )
        mock_synthesizer.apply = AsyncMock(return_value=mock_result)
        mock_create_synthesizer.return_value = mock_synthesizer

        # Act
        results = await SynthesisRunner.run_synthesis(
            synthesizer_type="qa",
            corpus_data=mock_corpus_data,
            llm_config={"model_name": "gpt-4"},
            num_generations=1,
        )

        # Assert
        assert len(results) == 1
        assert results[0]["question"] == "Test question?"

    @pytest.mark.asyncio
    @patch("diting_web.workers.synthesis.SynthesisRunner.create_synthesizer")
    async def test_run_synthesis_handles_partial_failure(
        self, mock_create_synthesizer, mock_corpus_data
    ):
        """Test that synthesis continues even if some generations fail."""
        # Arrange
        mock_synthesizer = MagicMock()
        
        # First call succeeds, second fails, third succeeds
        mock_results = [
            LLMCase(user_input="Q1", expected_output="A1", context=[]),
            Exception("Generation failed"),
            LLMCase(user_input="Q3", expected_output="A3", context=[]),
        ]
        
        mock_synthesizer.apply = AsyncMock(side_effect=mock_results)
        mock_create_synthesizer.return_value = mock_synthesizer

        # Act
        results = await SynthesisRunner.run_synthesis(
            synthesizer_type="qa",
            corpus_data=mock_corpus_data,
            llm_config={"model_name": "gpt-4"},
            num_generations=3,
        )

        # Assert
        # Should have 2 results (1st and 3rd succeeded)
        assert len(results) == 2
        assert results[0]["question"] == "Q1"
        assert results[1]["question"] == "Q3"

    @pytest.mark.asyncio
    @patch("diting_web.workers.synthesis.SynthesisRunner.create_synthesizer")
    async def test_run_synthesis_creates_corpus(
        self, mock_create_synthesizer, mock_corpus_data
    ):
        """Test that BaseCorpus is created from corpus_data."""
        # Arrange
        mock_synthesizer = MagicMock()
        mock_result = LLMCase(
            user_input="Q", expected_output="A", context=mock_corpus_data["context"]
        )
        mock_synthesizer.apply = AsyncMock(return_value=mock_result)
        mock_create_synthesizer.return_value = mock_synthesizer

        # Act
        await SynthesisRunner.run_synthesis(
            synthesizer_type="qa",
            corpus_data=mock_corpus_data,
            llm_config={"model_name": "gpt-4"},
            num_generations=1,
        )

        # Assert
        # Check that apply was called with a BaseCorpus
        call_args = mock_synthesizer.apply.call_args
        corpus = call_args[1]["corpus"]
        assert corpus.context == mock_corpus_data["context"]

    @pytest.mark.asyncio
    @patch("diting_web.workers.synthesis.SynthesisRunner.create_synthesizer")
    async def test_run_synthesis_with_synthesizer_params(
        self, mock_create_synthesizer, mock_corpus_data
    ):
        """Test synthesis with additional synthesizer parameters."""
        # Arrange
        mock_synthesizer = MagicMock()
        mock_result = LLMCase(user_input="Q", expected_output="A", context=[])
        mock_synthesizer.apply = AsyncMock(return_value=mock_result)
        mock_create_synthesizer.return_value = mock_synthesizer

        synthesizer_params = {"quality_threshold": 0.9}

        # Act
        await SynthesisRunner.run_synthesis(
            synthesizer_type="qa",
            corpus_data=mock_corpus_data,
            llm_config={"model_name": "gpt-4"},
            synthesizer_params=synthesizer_params,
            num_generations=1,
        )

        # Assert
        mock_create_synthesizer.assert_called_once()
        call_kwargs = mock_create_synthesizer.call_args[1]
        assert call_kwargs["synthesizer_params"] == synthesizer_params



