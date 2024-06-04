from .pdf_api import router as pdfRouter
from .merge.pdf_merge_api import router as pdfMergeRouter
from .convert.pdf_convert_api import router as pdfConvertRouter
from .split.pdf_split_api import router as pdfSplitRouter

pdfRouter.include_router(pdfMergeRouter)
pdfRouter.include_router(pdfConvertRouter)
pdfRouter.include_router(pdfSplitRouter)

__all__ = ["pdfRouter"]
