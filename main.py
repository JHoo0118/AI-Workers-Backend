import uvicorn
import ssl
from dependencies import download_pandoc

ssl._create_default_https_context = ssl._create_unverified_context


host = "127.0.0.1"
port = 8000
app_name = "app.main:app"


if __name__ == "__main__":
    download_pandoc()
    uvicorn.run(
        app_name,
        host=host,
        port=port,
        reload=True,
        timeout_keep_alive=60 * 3,
    )
