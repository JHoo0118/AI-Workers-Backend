from .ai_code_api import router as aiCodeRouter
from .api_gen import *
from .api_gen.ai_code_api_gen_api import router as aiCodeApiGenRouter
from .code_convert import *
from .code_convert.ai_code_code_convert_api import router as aiCodeCodeConverterRouter
from .sql_entity import *
from .sql_entity.ai_sql_entity_api import router as aiCodeSqlEntityRouter
from .algorithm import *
from .algorithm.ai_code_algorithm_api import router as aiAlgorithmRouter

aiCodeRouter.include_router(aiCodeApiGenRouter)
aiCodeRouter.include_router(aiCodeCodeConverterRouter)
aiCodeRouter.include_router(aiCodeSqlEntityRouter)
aiCodeRouter.include_router(aiAlgorithmRouter)

__all__ = ["aiCodeRouter"]
