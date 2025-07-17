from diting_inspect.services.case_service import CaseService
from diting_inspect.services.file_import_service import FileImportService
from diting_inspect.services.model_service import ModelService
from diting_inspect.services.toolconfig_service import ToolConfigService
from diting_inspect.utils import dt_persistent_path
from diting_inspect.models.case_model import InMemoryCaseRepository as CaseRepository
from diting_inspect.models.evaluation_model import (
    InMemoryEvaluationRepository as EvaluationRepository,
)
from diting_inspect.models.synthesizer_model import (
    InMemorySynthesizerRepository as SynthesizerRepository,
)
from diting_inspect.models.model_repository import (
    InMemoryModelRepository as ModelRepository,
)
from diting_inspect.models.toolconfig_repository import (
    InMemoryToolConfigRepository as ToolConfigRepository,
)
from diting_inspect.services.synthesizer_service import SynthesizerService
from diting_inspect.services.evaluation_service import EvaluationService


case_repository = CaseRepository(pickle_file=f"{dt_persistent_path}/cases.pkl")
evaluation_repository = EvaluationRepository(
    pickle_file=f"{dt_persistent_path}/evaluations.pkl"
)
synthesizer_repository = SynthesizerRepository(
    pickle_file=f"{dt_persistent_path}/synthesizers.pkl"
)
model_repository = ModelRepository(pickle_file=f"{dt_persistent_path}/models.pkl")
model_service = ModelService(model_repository)
case_service = CaseService(case_repository)
evaluation_service = EvaluationService(evaluation_repository, case_repository)
synthesizer_service = SynthesizerService(synthesizer_repository, case_repository)
file_import_service = FileImportService()
toolconfig_repository = ToolConfigRepository(
    pickle_file=f"{dt_persistent_path}/toolconfigs.pkl"
)
toolconfig_service = ToolConfigService(toolconfig_repository)
