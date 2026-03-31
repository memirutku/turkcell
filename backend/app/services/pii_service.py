"""PII Masking Service for KVKK compliance.

Wraps Presidio AnalyzerEngine + AnonymizerEngine with custom Turkish
recognizers. Detects and masks PII (TC Kimlik, phone, IBAN, email, names)
before user messages reach the LLM.
"""

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import EmailRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from app.recognizers import TcKimlikRecognizer, TurkishIbanRecognizer, TurkishPhoneRecognizer


class PIIMaskingService:
    """Detect and mask PII in Turkish text using Presidio.

    Replaces:
    - Person names -> [ISIM]
    - TC Kimlik No -> [TC_KIMLIK]
    - Turkish phone numbers -> [TELEFON]
    - Turkish IBAN -> [IBAN]
    - Email addresses -> [EMAIL]
    - Other PII -> [PII]
    """

    def __init__(self):
        # Configure NLP engine with multilingual spaCy model
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "tr", "model_name": "xx_ent_wiki_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()

        # Create registry with only custom Turkish recognizers
        # Do NOT call registry.load_predefined_recognizers() to avoid
        # English false positives (per research recommendation)
        registry = RecognizerRegistry(supported_languages=["tr"])
        registry.add_recognizer(TcKimlikRecognizer())
        registry.add_recognizer(TurkishPhoneRecognizer())
        registry.add_recognizer(TurkishIbanRecognizer())
        registry.add_recognizer(
            EmailRecognizer(
                supported_language="tr",
                context=["email", "e-posta", "eposta", "mail"],
            )
        )

        self._analyzer = AnalyzerEngine(
            registry=registry,
            nlp_engine=nlp_engine,
            supported_languages=["tr"],
        )
        self._anonymizer = AnonymizerEngine()

        # Per-entity replacement operators
        self._operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[ISIM]"}),
            "TC_KIMLIK_NO": OperatorConfig("replace", {"new_value": "[TC_KIMLIK]"}),
            "TR_PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[TELEFON]"}),
            "TR_IBAN": OperatorConfig("replace", {"new_value": "[IBAN]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            "DEFAULT": OperatorConfig("replace", {"new_value": "[PII]"}),
        }

    def mask(self, text: str) -> str:
        """Detect and mask PII in Turkish text.

        Args:
            text: Raw text that may contain PII.

        Returns:
            Text with PII replaced by type-specific placeholders.
        """
        results = self._analyzer.analyze(text=text, language="tr")
        anonymized = self._anonymizer.anonymize(
            text=text, analyzer_results=results, operators=self._operators
        )
        return anonymized.text
