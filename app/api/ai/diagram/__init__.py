from .ai_diagram_api import router as aiDiagramRouter
from .erd import *
from .erd.ai_diagram_erd_api import router as aiErdRouter
from .seq_diagram import *
from .seq_diagram.ai_diagram_seq_diagram_api import router as aiDiagramSeqDiagramRouter

aiDiagramRouter.include_router(aiErdRouter)
aiDiagramRouter.include_router(aiDiagramSeqDiagramRouter)

__all__ = ["aiDiagramRouter"]
