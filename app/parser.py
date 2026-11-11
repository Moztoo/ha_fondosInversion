"""Parser module for BBVA 'Anaquel con Rendimientos Históricos del Día Actual' PDF."""
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import pypdf

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
        """Parse full PDF content into structured records."""
        stream = io.BytesIO(pdf_content)
        reader = pypdf.PdfReader(stream)

        records: List[ParsedFundRecord] = []
        segments_seen = set()
        categories_seen = set()
        detected_date: Optional[str] = None

        current_segment = "Personas Físicas"
        current_category = "Fondos de Inversión"

        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            lines = text.split("\n")

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                # 1. Detect report date
                if not detected_date:
                    # Look for date pattern DD/MM/YYYY
                    m_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", line_str)
                    if m_date:
                        raw_date = m_date.group(1)
                        detected_date = self._parse_date(raw_date)
                        logger.info("Found report date in PDF: %s (page %d)", detected_date, page_idx + 1)

                # 2. Detect segment headers
                if "Personas Físicas" in line_str and "Anaquel" not in line_str:
                    current_segment = "Personas Físicas"
                    segments_seen.add(current_segment)
                elif "Personas Morales" in line_str and "Anaquel" not in line_str:
                    current_segment = "Personas Morales"
                    segments_seen.add(current_segment)
                elif "Colaboradores BBVA" in line_str and "Anaquel" not in line_str:
                    current_segment = "Colaboradores BBVA"
                    segments_seen.add(current_segment)

                # 3. Detect category headers
                if line_str.startswith("Fondos de") or line_str.startswith("Fondos Ciclos"):
                    current_category = line_str
                    categories_seen.add(current_category)
                    continue

                # 4. Check for table rows
                # Expected row layout:
                # [Ticker] [Serie] [Mínimo] [Optional: Calificación] [%Diario] [%Semanal] [%Mes] [%Año] [%1A] [%2A] [Precio]
                parts = line_str.split()
                if len(parts) >= 9:
                    # Verify if trailing parts contain percentage signs
                    trailing_candidates = parts[-7:-1]
                    if any("%" in p for p in trailing_candidates):
                        try:
                            precio = self._clean_float(parts[-1])
                            rend_2a = self._clean_float(parts[-2])
                            rend_1a = self._clean_float(parts[-3])
                            rend_anio = self._clean_float(parts[-4])
                            rend_mes = self._clean_float(parts[-5])
                            rend_sem = self._clean_float(parts[-6])
                            rend_dia = self._clean_float(parts[-7])

                            ticker = parts[0].strip()
                            series = parts[1].strip()
                            minimo = self._clean_float(parts[2])

                            # Calificación is any tokens between minimo and rend_dia
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

                        except Exception as e:
                            logger.debug("Skipping unparseable line: %s (%s)", line_str, e)

        final_date = detected_date or datetime.now().strftime("%Y-%m-%d")
        logger.info(
            "Parsed PDF successfully: %d records found for date %s",
            len(records),
            final_date,
        )

        return ParsedAnaquelReport(
            report_date=final_date,
            total_records=len(records),
            records=records,
            segments_found=sorted(list(segments_seen)),
            categories_found=sorted(list(categories_seen)),
        )
