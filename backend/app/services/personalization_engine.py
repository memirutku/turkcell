"""Multi-factor personalization engine for tariff and package recommendations."""

import logging
from datetime import date
from decimal import Decimal

from app.models.personalization_schemas import (
    CustomerProfile,
    PersonalizedPackageRecommendation,
    PersonalizedPackageResult,
    PersonalizedRecommendation,
    PersonalizedRecommendationResult,
)
from app.services.churn_risk_service import ChurnRiskService
from app.services.market_data_service import MarketDataService
from app.services.mock_bss import MockBSSService
from app.services.usage_pattern_service import UsagePatternService

logger = logging.getLogger(__name__)

# Composite score weights
WEIGHTS = {
    "usage_fit": 0.30,
    "demographic_fit": 0.20,
    "behavioral_fit": 0.20,
    "market_competitiveness": 0.15,
    "retention_value": 0.15,
}

# Segment-tariff affinity rules
SEGMENT_AFFINITY = {
    "genc": {
        "preferred_features": ["sosyal_medya", "yuksek_data"],
        "price_sensitivity": "yuksek",
        "data_weight": 0.7,
        "voice_weight": 0.1,
    },
    "profesyonel": {
        "preferred_features": ["yurt_disi", "yuksek_data", "yuksek_dakika"],
        "price_sensitivity": "dusuk",
        "data_weight": 0.5,
        "voice_weight": 0.3,
    },
    "aile": {
        "preferred_features": ["dengeli", "ekonomik"],
        "price_sensitivity": "orta",
        "data_weight": 0.4,
        "voice_weight": 0.3,
    },
    "emekli": {
        "preferred_features": ["ekonomik", "kolay_kullanim"],
        "price_sensitivity": "yuksek",
        "data_weight": 0.3,
        "voice_weight": 0.5,
    },
    "ogrenci": {
        "preferred_features": ["sosyal_medya", "ekonomik"],
        "price_sensitivity": "cok_yuksek",
        "data_weight": 0.7,
        "voice_weight": 0.1,
    },
}

# Segment-based conversation style directives
SEGMENT_CONVERSATION_STYLE = {
    "genc": (
        "Genç ve enerjik bir üslup kullan. 'Sen' dili ile hitap et. "
        "Kısa ve hızlı yanıtlar ver. Güncel ve samimi bir dil kullan. "
        "Örnek: 'Hemen halledelim!', 'Şurada bir bakayım senin için.'"
    ),
    "profesyonel": (
        "Profesyonel ve resmi bir üslup kullan. 'Siz' dili ile hitap et. "
        "Detaylı ve çözüm odaklı yanıtlar ver. İş dili kullan, jargondan kaçın. "
        "Örnek: 'Size en uygun çözümü hemen sunayım.', 'Detayları inceledim.'"
    ),
    "aile": (
        "Sıcak, güven verici ve sabırlı bir üslup kullan. 'Siz' dili ile hitap et. "
        "Pratik ve anlaşılır öneriler sun. Aile bütçesini göz önünde bulundur. "
        "Örnek: 'Merak etmeyin, birlikte çözümü bulalım.', 'Aileniz için en uygunu...'"
    ),
    "emekli": (
        "Çok açık, sade ve sabırlı bir üslup kullan. 'Siz' dili ile hitap et. "
        "Kısa cümleler kur, teknik terimlerden kaçın. Adım adım açıkla. "
        "Gerekirse aynı bilgiyi farklı şekilde tekrarla. "
        "Örnek: 'Adım adım anlatayım.', 'Yani kısaca şöyle...'"
    ),
    "ogrenci": (
        "Samimi ve enerjik bir üslup kullan. 'Sen' dili ile hitap et. "
        "Bütçe bilincini göz önünde bulundur. Kısa ve pratik yanıtlar ver. "
        "Örnek: 'En uygun fiyatlı seçeneğe bakalım!', 'Öğrenci dostu paketlerimiz var.'"
    ),
    "kurumsal": (
        "Çok resmi ve profesyonel bir üslup kullan. 'Siz' dili ile hitap et. "
        "Verimlilik ve çözüm odaklı ol. Kurumsal ihtiyaçlara öncelik ver. "
        "Örnek: 'Kurumunuz için en verimli çözümü sunayım.'"
    ),
    "default": "Samimi, empatik ve profesyonel bir ton kullan.",
}


def get_conversation_style(segment: str | None = None, contract_type: str = "bireysel") -> str:
    """Return conversation style directive based on customer segment."""
    if contract_type == "kurumsal":
        return SEGMENT_CONVERSATION_STYLE["kurumsal"]
    return SEGMENT_CONVERSATION_STYLE.get(
        segment or "default", SEGMENT_CONVERSATION_STYLE["default"]
    )


class PersonalizationEngine:
    """Orchestrates sub-services for multi-factor personalized recommendations."""

    def __init__(self, mock_bss: MockBSSService):
        self._mock_bss = mock_bss
        self._usage_pattern = UsagePatternService(mock_bss)
        self._churn_risk = ChurnRiskService(mock_bss)
        self._market_data = MarketDataService(mock_bss)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_personalized_tariff_recommendations(
        self, customer_id: str, top_n: int = 3
    ) -> PersonalizedRecommendationResult | None:
        """Full multi-factor tariff recommendation."""
        customer = self._mock_bss.get_customer(customer_id)
        if not customer:
            return None

        profile = self._build_profile(customer_id)
        if not profile:
            return None

        current_tariff = self._mock_bss.get_tariff(customer.tariff_id)
        if not current_tariff:
            return None

        # Calculate current effective cost
        bills = self._mock_bss.get_customer_bills(customer_id)
        avg_total = (
            sum(float(b.total_amount_tl) for b in bills) / len(bills) if bills else 0
        )

        usage = self._mock_bss.get_customer_usage(customer_id)
        retention_value = self._churn_risk.calc_retention_value(customer_id)
        churn_profile = self._churn_risk.get_risk_profile(customer_id)

        recommendations: list[PersonalizedRecommendation] = []
        for tariff in self._mock_bss.get_tariffs():
            if not tariff.is_active or tariff.id == current_tariff.id:
                continue

            # Only recommend upgrades (higher data quota)
            if tariff.data_gb <= current_tariff.data_gb:
                continue

            usage_fit = self._calc_usage_fit(usage, tariff)
            demographic_fit = self._calc_demographic_fit(profile.segment, tariff)
            behavioral_fit = self._usage_pattern.calc_behavioral_fit(
                customer_id, tariff.data_gb, tariff.features
            )
            market_score = self._market_data.calc_market_score(tariff.id)

            overall = (
                usage_fit * WEIGHTS["usage_fit"]
                + demographic_fit * WEIGHTS["demographic_fit"]
                + behavioral_fit * WEIGHTS["behavioral_fit"]
                + market_score * WEIGHTS["market_competitiveness"]
                + retention_value * WEIGHTS["retention_value"]
            )

            # Estimate savings
            tariff_base = float(tariff.monthly_price_tl)
            data_overage_cost = max(0, (usage.data_used_gb if usage else 0) - tariff.data_gb) * 25
            estimated_cost = (tariff_base + data_overage_cost) * 1.35  # KDV+OIV
            savings = avg_total - estimated_cost

            reasons = self._build_reasons(
                profile, tariff, usage_fit, demographic_fit, behavioral_fit, market_score, savings
            )
            tags = self._build_tags(profile, tariff)

            recommendations.append(
                PersonalizedRecommendation(
                    tariff_id=tariff.id,
                    tariff_name=tariff.name,
                    monthly_price_tl=tariff.monthly_price_tl,
                    estimated_savings_tl=Decimal(str(round(savings, 2))),
                    usage_fit_score=round(usage_fit, 2),
                    demographic_fit_score=round(demographic_fit, 2),
                    behavioral_fit_score=round(behavioral_fit, 2),
                    market_competitiveness_score=round(market_score, 2),
                    retention_value_score=round(retention_value, 2),
                    overall_score=round(overall, 3),
                    reasons=reasons,
                    personalization_tags=tags,
                )
            )

        recommendations.sort(key=lambda r: r.overall_score, reverse=True)

        retention_note = None
        if churn_profile and churn_profile.churn_probability >= 0.5:
            retention_note = (
                f"Dikkat: Bu musteri {churn_profile.churn_risk_level} kayip riskinde "
                f"(olasilik: %{churn_profile.churn_probability * 100:.0f}). "
                f"Ozel teklif sunulmasi onerilir."
            )

        return PersonalizedRecommendationResult(
            customer_id=customer_id,
            profile_summary=profile,
            current_tariff_name=current_tariff.name,
            current_monthly_cost_tl=Decimal(str(round(avg_total, 2))),
            recommendations=recommendations[:top_n],
            retention_note=retention_note,
        )

    def get_personalized_package_recommendations(
        self, customer_id: str, top_n: int = 3
    ) -> PersonalizedPackageResult | None:
        """Personalized package recommendations based on usage patterns and profile."""
        customer = self._mock_bss.get_customer(customer_id)
        if not customer:
            return None

        profile = self._build_profile(customer_id)
        pattern = self._usage_pattern.get_usage_pattern(customer_id)
        usage = self._mock_bss.get_customer_usage(customer_id)

        segment = profile.segment if profile else "profesyonel"
        affinity = SEGMENT_AFFINITY.get(segment, SEGMENT_AFFINITY["profesyonel"])
        top_cats = pattern.top_app_categories if pattern else []

        recommendations: list[PersonalizedPackageRecommendation] = []
        for pkg in self._mock_bss.get_packages():
            if not pkg.is_active:
                continue

            reason, tags = self._match_package(pkg, segment, affinity, top_cats, usage)
            if reason:
                recommendations.append(
                    PersonalizedPackageRecommendation(
                        package_id=pkg.id,
                        package_name=pkg.name,
                        price_tl=pkg.price_tl,
                        category=pkg.category,
                        reason=reason,
                        personalization_tags=tags,
                    )
                )

        return PersonalizedPackageResult(
            customer_id=customer_id,
            recommendations=recommendations[:top_n],
        )

    def get_customer_profile(self, customer_id: str) -> CustomerProfile | None:
        """Build a CustomerProfile for external consumption."""
        return self._build_profile(customer_id)

    # ------------------------------------------------------------------
    # Internal scoring
    # ------------------------------------------------------------------

    def _build_profile(self, customer_id: str) -> CustomerProfile | None:
        customer = self._mock_bss.get_customer(customer_id)
        if not customer:
            return None

        today = date.today()
        age = 30  # default
        if customer.birth_date:
            age = (
                today.year
                - customer.birth_date.year
                - (
                    (today.month, today.day)
                    < (customer.birth_date.month, customer.birth_date.day)
                )
            )

        tenure = (today.year - customer.registration_date.year) * 12 + (
            today.month - customer.registration_date.month
        )

        return CustomerProfile(
            customer_id=customer_id,
            name=customer.name,
            age=age,
            occupation=customer.occupation or "bilinmiyor",
            segment=customer.segment or "profesyonel",
            city=customer.address_city,
            tenure_months=tenure,
            contract_type=customer.contract_type,
        )

    @staticmethod
    def _calc_usage_fit(usage, tariff) -> float:
        """Score how well tariff covers actual usage needs (0.0-1.0)."""
        if not usage:
            return 0.5

        data_ratio = tariff.data_gb / max(usage.data_used_gb, 0.1)
        voice_ratio = tariff.voice_minutes / max(usage.voice_used_minutes, 1)
        sms_ratio = tariff.sms_count / max(usage.sms_used, 1)

        # Ideal ratio is 1.0-1.5x (covers need with some headroom)
        def ratio_score(r: float) -> float:
            if r < 1.0:
                return r * 0.7  # penalty for not covering need
            elif r <= 1.5:
                return 1.0  # sweet spot
            elif r <= 2.5:
                return 1.0 - (r - 1.5) * 0.3  # mild penalty for over-provisioning
            return 0.4  # heavy over-provisioning

        return (
            ratio_score(data_ratio) * 0.5
            + ratio_score(voice_ratio) * 0.3
            + ratio_score(sms_ratio) * 0.2
        )

    @staticmethod
    def _calc_demographic_fit(segment: str, tariff) -> float:
        """Score demographic fit based on segment-tariff affinity (0.0-1.0)."""
        affinity = SEGMENT_AFFINITY.get(segment, SEGMENT_AFFINITY["profesyonel"])
        score = 0.5  # baseline

        # Feature match
        tariff_features_lower = " ".join(tariff.features).lower()
        for pref in affinity["preferred_features"]:
            if pref == "sosyal_medya" and "sosyal medya" in tariff_features_lower:
                score += 0.15
            elif pref == "yuksek_data" and tariff.data_gb >= 15:
                score += 0.1
            elif pref == "yuksek_dakika" and tariff.voice_minutes >= 1500:
                score += 0.1
            elif pref == "ekonomik" and float(tariff.monthly_price_tl) <= 150:
                score += 0.15
            elif pref == "yurt_disi" and "yurt disi" in tariff_features_lower:
                score += 0.15
            elif pref == "dengeli":
                score += 0.05  # most tariffs are somewhat balanced

        # Price sensitivity penalty
        price = float(tariff.monthly_price_tl)
        sensitivity = affinity["price_sensitivity"]
        if sensitivity == "cok_yuksek" and price > 150:
            score -= 0.2
        elif sensitivity == "yuksek" and price > 200:
            score -= 0.15
        elif sensitivity == "dusuk" and price > 300:
            score -= 0.05  # minimal penalty for professionals

        return max(0.0, min(1.0, score))

    @staticmethod
    def _build_reasons(
        profile, tariff, usage_fit, demographic_fit, behavioral_fit, market_score, savings
    ) -> list[str]:
        """Generate Turkish explanation strings for the recommendation."""
        reasons = []
        if usage_fit >= 0.7:
            reasons.append("Mevcut kullaniminiza cok uygun bir tarife")
        elif usage_fit < 0.4:
            reasons.append("Kullaniminiz icin kapasitesi yetersiz olabilir")

        if demographic_fit >= 0.7:
            reasons.append(f"{profile.segment.capitalize()} profilinize uygun")

        if behavioral_fit >= 0.7:
            reasons.append("Kullanim kalibinizla uyumlu (zaman dagilimi ve uygulama tercihleri)")

        if market_score >= 0.6:
            reasons.append("Piyasaya kiyasla rekabetci fiyat")
        elif market_score < 0.4:
            reasons.append("Rakiplere kiyasla daha pahali")

        if savings > 0:
            reasons.append(f"Tahmini aylik {savings:.0f} TL tasarruf")
        elif savings < -50:
            reasons.append(f"Mevcut maliyetinize gore aylik {abs(savings):.0f} TL daha pahali")

        return reasons if reasons else ["Genel değerlendirme"]

    @staticmethod
    def _build_tags(profile, tariff) -> list[str]:
        tags = [f"{profile.segment}_segment"]
        if tariff.data_gb >= 15:
            tags.append("yuksek_data")
        if float(tariff.monthly_price_tl) <= 130:
            tags.append("ekonomik")
        features_lower = " ".join(tariff.features).lower()
        if "sosyal medya" in features_lower:
            tags.append("sosyal_medya_dahil")
        if "yurt disi" in features_lower:
            tags.append("yurt_disi_dahil")
        return tags

    @staticmethod
    def _match_package(pkg, segment, affinity, top_cats, usage) -> tuple[str | None, list[str]]:
        """Determine if a package is a good match, return reason + tags."""
        tags: list[str] = [f"{segment}_segment"]

        # Data packages for users with overage
        if pkg.category == "ek_data" and usage and usage.data_overage_gb > 0:
            return (
                f"Veri asiminiz {usage.data_overage_gb} GB. Bu paketle asim ucretinden kurtulabilirsiniz.",
                tags + ["asim_cozumu"],
            )

        # Social media package for young/student users
        if pkg.category == "sosyal_medya" and "sosyal_medya" in top_cats:
            return (
                "Sosyal medya en cok kullandiginiz kategori. Bu paketle sosyal medya kotanizdan yemez.",
                tags + ["sosyal_medya_agirlikli"],
            )

        # Entertainment for family segment
        if pkg.category == "eglence" and segment == "aile":
            return (
                "Aile profiliniz icin TV+ ve Fizy erisimi uygun bir secim.",
                tags + ["aile_eglence"],
            )

        # International for professionals
        if pkg.category == "yurt_disi" and segment == "profesyonel":
            return (
                "Profesyonel profiliniz icin yurt disi veri ve arama paketi onerilir.",
                tags + ["is_seyahati"],
            )

        # Data package for high usage (near limit)
        if pkg.category == "ek_data" and usage and usage.data_limit_gb > 0:
            if usage.data_used_gb / usage.data_limit_gb >= 0.8:
                return (
                    f"Veri kullaniminiz limitinizin %{usage.data_used_gb / usage.data_limit_gb * 100:.0f}'ine ulasti. "
                    f"Ek veri paketi asimi onleyebilir.",
                    tags + ["limit_yakin"],
                )

        return None, tags
