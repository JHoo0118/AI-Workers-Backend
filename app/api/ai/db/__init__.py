from .ai_db_api import router as aiSqlRouter
from .gen import *
from .gen.ai_sql_gen_api import router as aiSqlGenRouter

aiSqlRouter.include_router(aiSqlGenRouter)

__all__ = ["aiSqlRouter"]
