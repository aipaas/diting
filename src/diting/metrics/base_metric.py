from abc import ABC, abstractmethod
import typing as t
import time
from dataclasses import dataclass

from diting.cases.llm_case import LLMCase, LLMCaseParams
from diting.utilities.slug import camel_to_snake
from diting.utilities.print import get_bolded_text, get_colored_text, print_text


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
        self, test_case: LLMCase, *args: t.Tuple[t.Any], **kwargs: t.Dict[str, t.Any]
    ) -> MetricValue:
        """Compute metric value for a test case.

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
            If _compute method is not implemented in subclass.

        Notes
        -----
        1. Validates test case against required parameters
        2. Executes pre-computation callbacks
        3. Executes computation
        4. Executes post-computation callbacks
        """
        _assert_testcase_validity(self.name, test_case, self._required_params)
        debug = kwargs.get("debug", False)
        try:
            if debug:
                print(
                    f"Starting {get_colored_text(self.name, color='green')} evaluation algorithm"
                )
                required_params_info = ", ".join(
                    [
                        get_colored_text(p.name, color="green")
                        for p in self._required_params
                    ]
                )
                print(
                    f"Algorithm requires the following parameters: {required_params_info}"
                )
                print(get_bolded_text("Test Case Information:"))
                print(get_colored_text(str(test_case), "blue"))
            start_time: float = time.perf_counter()
            metric_value = await self._compute(test_case, *args, **kwargs)
            end_time: float = time.perf_counter()
            duration = int((end_time - start_time) * 1000)
            if debug:
                print(
                    get_bolded_text(
                        f"Computation Complete! Total time taken: {duration} ms"
                    )
                )
                print(get_bolded_text("Metric Value:"))
                print(get_colored_text(str(metric_value), color="green"))
            return metric_value
        except Exception as err:
            if debug:
                print_text("Error occurred during computation:", color="red")
                print_text(str(err), color="red")
            raise
        finally:
            if debug:
                print(get_bolded_text("Evaluation finished."))

    @abstractmethod
    async def _compute(
        self, test_case: LLMCase, *args: t.Tuple[t.Any], **kwargs: t.Dict[str, t.Any]
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
    missing_params = []
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
