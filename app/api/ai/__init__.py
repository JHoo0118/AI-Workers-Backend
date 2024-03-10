from .ai_api import *
from .ai_api import router as aiRouter
from .docs import *
from .docs.ai_docs_api import router as aiDocsRouter
from .diagram import *
from .diagram.ai_diagram_api import router as aiDiagramRouter
from .code import *
from .code.ai_code_api import router as aiCodeRouter
from .db import *
from .db.ai_db_api import router as aiDbSqlRouter

aiRouter.include_router(aiDocsRouter)
aiRouter.include_router(aiDiagramRouter)
aiRouter.include_router(aiCodeRouter)
aiRouter.include_router(aiDbSqlRouter)

__all__ = ["aiRouter"]
