import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass

from diting_core.callbacks.manager import new_group
from diting_core.cases.llm_case import LLMCase, LLMCaseParams
from diting_core.utilities.slug import camel_to_snake


@dataclass
class MetricValue:
    score: t.Optional[float] = None
    reason: t.Optional[str] = None
    run_logs: t.Optional[t.Dict[str, t.Any]] = None

    def __str__(self):
        return (
            f"MetricValue(score={self.score}, "
            f"reason={self.reason}, "
            f"run_logs={self.run_logs})"
        )


class BaseMetric(ABC):
    # run config
    include_reason: bool = False
    _required_params: t.List[LLMCaseParams] = []

    async def compute(
        self,
        test_case: LLMCase,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> MetricValue:
        """Compute metric value for a test case.

        Parameters
        ----------
        test_case : LLMCase
            The test case to evaluate.
        *args : t.Tuple[t.Any]
            Additional positional arguments.
        **kwargs : t.Dict[str, t.Any]
            verbose : bool
                Whether to enable verbose mode. Defaults to False.
            callbacks : Callbacks
                The callback register to the evaluation
            Other Additional keyword arguments.

        Returns
        -------
        MetricValue
            Container with score, reason, and run logs.

        Raises
        ------
        NotImplementedError
            If _compute method is not implemented in subclass.

        Notes
        -----
        1. Validates test case against required parameters
        2. Executes pre-computation callbacks
        3. Executes computation
        4. Executes post-computation callbacks
        """
        from diting_core.callbacks.base import ChainType

        run_manager, grp_cb = await new_group(
            name=self.name,
            inputs={"test_case": test_case},
            callbacks=kwargs.get("callbacks"),
            verbose=kwargs.get("verbose", False),
            chain_type=ChainType.METRIC,
            required_params=self._required_params,
        )
        try:
            _assert_testcase_validity(self.name, test_case, self._required_params)
            metric_value = await self._compute(
                test_case, callbacks=grp_cb, *args, **kwargs
            )
        except Exception as e:
            await run_manager.on_chain_error(e)
            raise e

        await run_manager.on_chain_end({"metric_value": metric_value})
        return metric_value

    @abstractmethod
    async def _compute(
        self,
        test_case: LLMCase,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> MetricValue:
        """Abstract method to perform actual metric computation.

        Parameters
        ----------
        test_case : LLMCase
            The test case to evaluate.
        *args : t.Tuple[t.Any]
            Additional positional arguments.
        **kwargs : t.Dict[str, t.Any]
            Additional keyword arguments.

        Returns
        -------
        MetricValue
            Container with score, reason, and run logs.

        Raises
        ------
        NotImplementedError
            If not implemented in subclass.
        """

        raise NotImplementedError

    @property
    def name(self) -> str:
        return camel_to_snake(self.__class__.__name__)


def _assert_testcase_validity(
    metric_name: str,
    test_case: LLMCase,
    required_params: t.Optional[t.List[LLMCaseParams]],
) -> None:
    """
    Validate the test case to ensure required parameters are not None.

    Parameters
    ----------
    metric_name : str
        The name of the metric being validated, used for error message context.
    test_case : LLMCase
        The test case object to check, which should contain the required parameters as attributes.
    required_params : Optional[List[LLMCaseParams]]
        A list of required parameters (each with a `value` attribute) that must exist and be non-None in the test case.

    Raises
    ------
    ValueError
        If any required parameter is None, a ValueError is raised with a message listing the missing parameters.

    Notes
    -----
    This function checks the presence of required parameters in the test case using `getattr(test_case, param.value)`.
    If `required_params` is None, the validation is skipped.
    The error message is automatically formatted based on the number of missing parameters.
    """
    if required_params is None:
        return
    missing_params: list[str] = []
    for param in required_params:
        if getattr(test_case, param.value) is None:
            missing_params.append(f"'{param.value}'")

    if missing_params:
        if len(missing_params) == 1:
            missing_params_str = missing_params[0]
        elif len(missing_params) == 2:
            missing_params_str = " and ".join(missing_params)
        else:
            missing_params_str = (
                ", ".join(missing_params[:-1]) + ", and " + missing_params[-1]
            )

        error_str = (
            f"{missing_params_str} cannot be None for the '{metric_name}' metric"
        )
        raise ValueError(error_str)
