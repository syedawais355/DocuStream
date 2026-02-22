import subprocess
import shutil
from pathlib import Path
from exceptions import ConversionError
from config import get_settings
from logger import get_logger

logger = get_logger()

try:
    import winreg
except ImportError:
    winreg = None


def _find_soffice_path() -> Path | None:
    settings = get_settings()
    
    if settings.soffice_path:
        path = Path(settings.soffice_path)
        if path.exists():
            return path
        raise ConversionError(
            f"SOFFICE_PATH configured in .env but not found: {settings.soffice_path}"
        )
    
    soffice_name = "soffice.exe" if shutil.os.name == "nt" else "soffice"
    
    path = shutil.which(soffice_name)
    if path:
        return Path(path)
    
    if shutil.os.name == "nt":
        try:
            hklm = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
            key = winreg.OpenKey(hklm, r"SOFTWARE\LibreOffice\UNO\InstallPath")
            install_path, _ = winreg.QueryValueEx(key, None)
            winreg.CloseKey(key)
            soffice_path = Path(install_path) / "soffice.exe"
            if soffice_path.exists():
                return soffice_path
        except (OSError, TypeError):
            pass
        
        glob_results = list(Path("C:\\Program Files").glob("LibreOffice*/program/soffice.exe"))
        if glob_results:
            return glob_results[0]
        
        glob_results = list(Path("C:\\Program Files (x86)").glob("LibreOffice*/program/soffice.exe"))
        if glob_results:
            return glob_results[0]
    
    return None


def convert_docx_to_pdf(input_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{input_path.stem}.pdf"
    
    soffice_path = _find_soffice_path()
    if not soffice_path:
        raise ConversionError(
            "LibreOffice not found. Install LibreOffice or set SOFFICE_PATH in .env. "
            "On Windows, run: Get-ChildItem -Path 'C:\\' -Filter 'soffice.exe' "
            "-Recurse -ErrorAction SilentlyContinue"
        )
    
    try:
        subprocess.run(
            [
                str(soffice_path),
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(input_path),
            ],
            check=True,
            timeout=120,
            capture_output=True,
        )
    except subprocess.TimeoutExpired as e:
        logger.warning(f"DOCX to PDF timeout: {input_path.name}")
        raise ConversionError(f"DOCX to PDF conversion timed out (120s): {input_path.name}") from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        logger.warning(f"DOCX to PDF failed: {stderr}")
        raise ConversionError(
            f"DOCX to PDF conversion failed: {stderr}"
        ) from e
    except FileNotFoundError as e:
        logger.error(f"LibreOffice executable not found: {soffice_path}")
        raise ConversionError(f"LibreOffice executable not found: {soffice_path}") from e
    
    if not output_file.exists():
        logger.error(f"Output file not created: {output_file}")
        raise ConversionError(f"Output file not created: {output_file}")
    
    return output_file


def convert_pdf_to_docx(input_path: Path, output_dir: Path) -> Path:
    from pdf2docx import Converter
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{input_path.stem}.docx"
    
    try:
        converter = Converter(str(input_path))
        converter.convert(str(output_file))
        converter.close()
    except Exception as e:
        logger.warning(f"PDF to DOCX failed: {str(e)}")
        raise ConversionError(f"PDF to DOCX conversion failed: {str(e)}") from e
    
    if not output_file.exists():
        logger.error(f"PDF to DOCX output file not created: {output_file}")
        raise ConversionError(f"Output file not created: {output_file}")
    
    return output_file
