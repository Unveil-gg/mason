"""Art direction, construction plans, and visual evaluation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mason.core.decompose import Decomposition
from mason.core.form_plan import GeometricPlan, QualityStage
from mason.core.ref_analysis import ReferenceAnalysis
from mason.core.workflow import WorkflowKind


class UsageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    importance: Literal[
        "background_prop", "standard_prop", "focal_prop", "hero",
    ] = "standard_prop"
    viewing_distance: Literal["far", "medium", "close"] = "medium"


class ReferenceImage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    purpose: Literal[
        "silhouette",
        "proportion",
        "shape_language",
        "material",
        "color",
        "style",
        "detail",
        "composition",
        "component",
        "correction",
    ]
    view: str | None = None
    component: str | None = None


class ArtStyleNotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    realism: float = Field(default=0.35, ge=0, le=1)
    stylization: float = Field(default=0.65, ge=0, le=1)
    shape_language: list[str] = Field(default_factory=list)


class FormLists(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)
    tertiary: list[str] = Field(default_factory=list)


class MaterialIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str
    palette: str | None = None


class GameplayRead(BaseModel):
    """How the asset must read in-game."""

    model_config = ConfigDict(extra="forbid")

    camera: str = ""
    on_screen_size: str = ""
    must_read: list[str] = Field(default_factory=list)


class ArtDirection(BaseModel):
    """Optional brief an external agent fills before generation."""

    model_config = ConfigDict(extra="forbid")

    subject: str = ""
    style: ArtStyleNotes = Field(default_factory=ArtStyleNotes)
    usage: UsageSpec = Field(default_factory=UsageSpec)
    silhouette: str = ""
    forms: FormLists = Field(default_factory=FormLists)
    materials: list[MaterialIntent] = Field(default_factory=list)
    detail_density: Literal["low", "medium", "high"] = "medium"
    references: list[ReferenceImage] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    focal_point: str = ""
    value_hierarchy: str = ""
    asymmetry: str = "none"
    gameplay: GameplayRead = Field(default_factory=GameplayRead)
    recognition_details: list[str] = Field(default_factory=list)


class PlanForm(BaseModel):
    """One intended form. Not compiled into geometry."""

    model_config = ConfigDict(extra="forbid")

    type: str
    purpose: str = ""
    count: int | None = Field(default=None, ge=1)
    notes: str | None = None


class PlanTechnique(BaseModel):
    """Chosen modeling technique. Intent only, not compiled."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "lathe", "box", "curve", "outline", "skin",
        "modular", "remesh", "refine", "sculpt", "fit",
    ]
    purpose: str = ""
    applies_to: str = ""


class ConstructionPlan(BaseModel):
    """Intent for primary / secondary / tertiary construction."""

    model_config = ConfigDict(extra="forbid")

    techniques: list[PlanTechnique] = Field(default_factory=list)
    primary_forms: list[PlanForm] = Field(default_factory=list)
    secondary_forms: list[PlanForm] = Field(default_factory=list)
    tertiary_details: list[PlanForm] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    keep_parts: list[str] = Field(default_factory=list)
    rebuild_parts: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ShapeLanguageNotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str = ""
    secondary: str = ""
    edges: str = ""


class ProportionNotes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height_width_ratio: float | None = None
    exaggerated_features: list[str] = Field(default_factory=list)


class PaletteDistribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominant: str = ""
    secondary: str = ""
    accent: str = ""


class SourceSize(BaseModel):
    """Pixel dimensions of a reference image."""

    model_config = ConfigDict(extra="forbid")

    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ImageRegion(BaseModel):
    """One measured color region in a reference image."""

    model_config = ConfigDict(extra="forbid")

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    hex: str = ""
    palette: str | None = None


class ArtAnalysis(BaseModel):
    """Optional notes an agent produces from reference images. Also
    the target for measured fields written by `mason ingest`."""

    model_config = ConfigDict(extra="forbid")

    shape_language: ShapeLanguageNotes = Field(
        default_factory=ShapeLanguageNotes,
    )
    proportions: ProportionNotes = Field(default_factory=ProportionNotes)
    detail_density: Literal["low", "medium", "high"] = "medium"
    style: ArtStyleNotes = Field(default_factory=ArtStyleNotes)
    materials: list[str] = Field(default_factory=list)
    wear: float = Field(default=0.0, ge=0, le=1)
    palette_distribution: PaletteDistribution = Field(
        default_factory=PaletteDistribution,
    )
    source_size: SourceSize | None = None
    regions: list[ImageRegion] = Field(default_factory=list)


class ImageBBox(BaseModel):
    """Pixel bounding box of the detected subject."""

    model_config = ConfigDict(extra="forbid")

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class PaletteHexes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominant: str = ""
    secondary: str = ""
    accent: str = ""


class PaletteKeys(BaseModel):
    """Nearest style palette key per palette slot, filled only when
    `mason ingest` is given `--style`. Never invents new hex."""

    model_config = ConfigDict(extra="forbid")

    dominant: str | None = None
    secondary: str | None = None
    accent: str | None = None


class ImageAnalysis(BaseModel):
    """Measured facts from `mason ingest`'s CV pass: silhouette
    ratio, palette, color regions, contour, and edge character. A
    structured document, not a mesh or layer compiler."""

    model_config = ConfigDict(extra="forbid")

    source: str
    source_size: SourceSize
    bbox: ImageBBox
    height_width_ratio: float
    palette: PaletteHexes = Field(default_factory=PaletteHexes)
    palette_keys: PaletteKeys = Field(default_factory=PaletteKeys)
    regions: list[ImageRegion] = Field(default_factory=list)
    contour: list[tuple[float, float]] = Field(default_factory=list)
    edges: Literal["hard", "soft"] = "soft"


class EvalScores(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_visual_quality: int | None = Field(
        default=None, ge=1, le=10,
    )
    detail_density: int | None = Field(default=None, ge=1, le=10)
    silhouette: int | None = Field(default=None, ge=1, le=10)
    proportions: int | None = Field(default=None, ge=1, le=10)
    secondary_forms: int | None = Field(default=None, ge=1, le=10)
    tertiary_detail: int | None = Field(default=None, ge=1, le=10)
    materials: int | None = Field(default=None, ge=1, le=10)
    visual_hierarchy: int | None = Field(default=None, ge=1, le=10)
    style_consistency: int | None = Field(default=None, ge=1, le=10)
    game_readability: int | None = Field(default=None, ge=1, le=10)
    layering: int | None = Field(default=None, ge=1, le=10)
    background_read: int | None = Field(default=None, ge=1, le=10)
    contact_read: int | None = Field(default=None, ge=1, le=10)
    continuity: int | None = Field(default=None, ge=1, le=10)
    form_conviction: int | None = Field(default=None, ge=1, le=10)
    target_identity: int | None = Field(default=None, ge=1, le=10)
    primary_silhouette: int | None = Field(default=None, ge=1, le=10)
    major_masses: int | None = Field(default=None, ge=1, le=10)
    style_match: int | None = Field(default=None, ge=1, le=10)
    multi_view_coherence: int | None = Field(default=None, ge=1, le=10)
    technical_quality: int | None = Field(default=None, ge=1, le=10)
    wearable_fit: int | None = Field(default=None, ge=1, le=10)
    anatomy_follow: int | None = Field(default=None, ge=1, le=10)
    boxiness: int | None = Field(default=None, ge=1, le=10)
    deformation: int | None = Field(default=None, ge=1, le=10)


class EvalIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    severity: Literal["low", "medium", "high"]
    description: str
    suggested_change: str = ""


class EvalDiscrepancy(BaseModel):
    """Ranked geometric error. Fix critical before major/minor."""

    model_config = ConfigDict(extra="forbid")

    rank: Literal["critical", "major", "minor"]
    category: str
    description: str
    geometric_intent: str = ""
    suggested_action: str = ""
    landmark: str | None = None


class ViewScore(BaseModel):
    """Per-view critic score used to block cross-view regression."""

    model_config = ConfigDict(extra="forbid")

    view: str
    score: int = Field(ge=1, le=10)
    notes: str = ""


class CompareToBest(BaseModel):
    """Candidate versus current_best. Required for a promote."""

    model_config = ConfigDict(extra="forbid")

    best_iteration: int | None = None
    improves: list[str] = Field(default_factory=list)
    worsens: list[str] = Field(default_factory=list)
    verdict: Literal["accept", "reject", "try_again"] | None = None
    reason: str = ""


class CorrectionTarget(BaseModel):
    """One named part, param, or landmark the next edit may change."""

    model_config = ConfigDict(extra="forbid")

    part: str | None = None
    param: str | None = None
    landmark: str | None = None


class VisualEvaluation(BaseModel):
    """Critic scores written by mason evaluate, not by the build."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    scores: EvalScores = Field(default_factory=EvalScores)
    issues: list[EvalIssue] = Field(default_factory=list)
    discrepancies: list[EvalDiscrepancy] = Field(default_factory=list)
    mode: Literal["beauty", "silhouette"] = "beauty"
    represents_object: bool | None = None
    represents_style: bool | None = None
    stage: QualityStage | None = None
    actions_taken: list[str] = Field(default_factory=list)
    acceptance_reason: str = ""
    view_scores: list[ViewScore] = Field(default_factory=list)
    compare: CompareToBest | None = None
    candidate: str | None = None
    critic: Literal["art", "technical"] = "art"
    ship: bool = False
    iteration: int | None = None
    created_at: str = ""
    primary_failure: str = ""
    correction_targets: list[CorrectionTarget] = Field(
        default_factory=list,
    )
    approved: list[str] = Field(default_factory=list)
    visual_reasoning: bool = False


class ArtFields(BaseModel):
    """Shared optional art-loop fields on every AssetSpec type."""

    workflow: WorkflowKind | None = None
    art_direction: ArtDirection | None = None
    construction_plan: ConstructionPlan | None = None
    geometric_plan: GeometricPlan | None = None
    art_analysis: ArtAnalysis | None = None
    reference_analysis: ReferenceAnalysis | None = None
    decomposition: Decomposition | None = None
    depends_on: list[str] = Field(default_factory=list)
