from .pdf_api import router as pdfRouter
from .merge.pdf_merge_api import router as pdfMergeRouter
from .convert.pdf_convert_api import router as pdfConvertRouter

pdfRouter.include_router(pdfMergeRouter)
pdfRouter.include_router(pdfConvertRouter)

__all__ = ["pdfRouter"]
