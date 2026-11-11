"""Parser module for BBVA 'Anaquel con Rendimientos Históricos del Día Actual' PDF."""
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger("bbva_fondos.parser")

@dataclass
class ParsedFundRecord:
    """Represents a single parsed line/fund series from the Anaquel."""
    ticker: str
    series: str
    segment: str
    category: str
    minimo_inversion: float
    calificacion: Optional[str]
    rendimiento_diario: Optional[float]
    rendimiento_semanal: Optional[float]
    rendimiento_mes: Optional[float]
    rendimiento_anio: Optional[float]
    rendimiento_1a: Optional[float]
    rendimiento_2a: Optional[float]
    precio: float
    report_date: str  # YYYY-MM-DD

@dataclass
class ParsedAnaquelReport:
    """Complete parsed results from an Anaquel PDF document."""
    report_date: str  # YYYY-MM-DD
    total_records: int
    records: List[ParsedFundRecord] = field(default_factory=list)
    segments_found: List[str] = field(default_factory=list)
    categories_found: List[str] = field(default_factory=list)

class AnaquelParser:
    """Extracts fund performance snapshots from BBVA Anaquel PDF bytes."""

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Convert DD/MM/YYYY to YYYY-MM-DD."""
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return date_str

    @staticmethod
    def _clean_float(val_str: str) -> float:
        """Parse numerical string, handling commas, percent signs and negatives."""
        cleaned = val_str.replace("%", "").replace(",", "").strip()
        return float(cleaned)

    def parse_pdf(self, pdf_content: bytes) -> ParsedAnaquelReport:
        """Parse full PDF content into structured records using pdfplumber."""
        try:
            import pdfplumber
            return self._parse_with_pdfplumber(pdf_content)
        except Exception as e:
            logger.warning("pdfplumber parsing failed (%s), falling back to pypdf", e)
            return self._parse_with_pypdf(pdf_content)

    def _parse_with_pdfplumber(self, pdf_content: bytes) -> ParsedAnaquelReport:
        import pdfplumber

        records: List[ParsedFundRecord] = []
        segments_seen = set()
        categories_seen = set()
        detected_date: Optional[str] = None

        current_segment = "Personas Físicas"
        current_category = "Fondos de Deuda"

        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split("\n")
                for line in lines:
                    l_str = line.strip()
                    if not l_str:
                        continue

                    # Extract date
                    if not detected_date:
                        m_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", l_str)
                        if m_date:
                            detected_date = self._parse_date(m_date.group(1))

                    # Segment headers
                    if "Personas Físicas" in l_str and "Anaquel" not in l_str:
                        current_segment = "Personas Físicas"
                        segments_seen.add(current_segment)
                    elif "Personas Morales" in l_str and "Anaquel" not in l_str:
                        current_segment = "Personas Morales"
                        segments_seen.add(current_segment)
                    elif "Colaboradores BBVA" in l_str and "Anaquel" not in l_str:
                        current_segment = "Colaboradores BBVA"
                        segments_seen.add(current_segment)

                    # Category headers
                    if l_str.startswith("Fondos"):
                        current_category = l_str
                        categories_seen.add(current_category)
                        continue

                    # Fund rows
                    parts = l_str.split()
                    if len(parts) >= 9 and any("%" in p for p in parts[-7:-1]):
                        try:
                            precio = self._clean_float(parts[-1])
                            rend_2a = self._clean_float(parts[-2])
                            rend_1a = self._clean_float(parts[-3])
                            rend_anio = self._clean_float(parts[-4])
                            rend_mes = self._clean_float(parts[-5])
                            rend_sem = self._clean_float(parts[-6])
                            rend_dia = self._clean_float(parts[-7])

                            ticker = parts[0].strip().upper()
                            series = parts[1].strip().upper()
                            minimo = self._clean_float(parts[2])

                            rating_tokens = parts[3:-7]
                            calificacion = " ".join(rating_tokens).strip() if rating_tokens else None

                            report_date = detected_date or datetime.now().strftime("%Y-%m-%d")

                            rec = ParsedFundRecord(
                                ticker=ticker,
                                series=series,
                                segment=current_segment,
                                category=current_category,
                                minimo_inversion=minimo,
                                calificacion=calificacion,
                                rendimiento_diario=rend_dia,
                                rendimiento_semanal=rend_sem,
                                rendimiento_mes=rend_mes,
                                rendimiento_anio=rend_anio,
                                rendimiento_1a=rend_1a,
                                rendimiento_2a=rend_2a,
                                precio=precio,
                                report_date=report_date,
                            )
                            records.append(rec)
                            segments_seen.add(current_segment)
                            categories_seen.add(current_category)
                        except Exception:
                            continue

        final_date = detected_date or datetime.now().strftime("%Y-%m-%d")
        return ParsedAnaquelReport(
            report_date=final_date,
            total_records=len(records),
            records=records,
            segments_found=sorted(list(segments_seen)),
            categories_found=sorted(list(categories_seen)),
        )

    def _parse_with_pypdf(self, pdf_content: bytes) -> ParsedAnaquelReport:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(pdf_content))
        records: List[ParsedFundRecord] = []
        segments_seen = set()
        categories_seen = set()
        detected_date: Optional[str] = None

        current_segment = "Personas Físicas"
        current_category = "Fondos de Deuda"

        for page in reader.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                l_str = line.strip()
                if not l_str:
                    continue

                if not detected_date:
                    m_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", l_str)
                    if m_date:
                        detected_date = self._parse_date(m_date.group(1))

                if "Personas Físicas" in l_str and "Anaquel" not in l_str:
                    current_segment = "Personas Físicas"
                elif "Personas Morales" in l_str and "Anaquel" not in l_str:
                    current_segment = "Personas Morales"
                elif "Colaboradores BBVA" in l_str and "Anaquel" not in l_str:
                    current_segment = "Colaboradores BBVA"

                if l_str.startswith("Fondos"):
                    current_category = l_str
                    continue

                parts = l_str.split()
                if len(parts) >= 9 and any("%" in p for p in parts[-7:-1]):
                    try:
                        precio = self._clean_float(parts[-1])
                        rend_2a = self._clean_float(parts[-2])
                        rend_1a = self._clean_float(parts[-3])
                        rend_anio = self._clean_float(parts[-4])
                        rend_mes = self._clean_float(parts[-5])
                        rend_sem = self._clean_float(parts[-6])
                        rend_dia = self._clean_float(parts[-7])

                        ticker = parts[0].strip().upper()
                        series = parts[1].strip().upper()
                        minimo = self._clean_float(parts[2])
                        rating_tokens = parts[3:-7]
                        calificacion = " ".join(rating_tokens).strip() if rating_tokens else None

                        rec = ParsedFundRecord(
                            ticker=ticker,
                            series=series,
                            segment=current_segment,
                            category=current_category,
                            minimo_inversion=minimo,
                            calificacion=calificacion,
                            rendimiento_diario=rend_dia,
                            rendimiento_semanal=rend_sem,
                            rendimiento_mes=rend_mes,
                            rendimiento_anio=rend_anio,
                            rendimiento_1a=rend_1a,
                            rendimiento_2a=rend_2a,
                            precio=precio,
                            report_date=detected_date or datetime.now().strftime("%Y-%m-%d"),
                        )
                        records.append(rec)
                        segments_seen.add(current_segment)
                        categories_seen.add(current_category)
                    except Exception:
                        continue

        final_date = detected_date or datetime.now().strftime("%Y-%m-%d")
        return ParsedAnaquelReport(
            report_date=final_date,
            total_records=len(records),
            records=records,
            segments_found=sorted(list(segments_seen)),
            categories_found=sorted(list(categories_seen)),
        )
