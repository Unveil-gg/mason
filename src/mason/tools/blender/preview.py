"""Standard Blender preview view names."""

PREVIEW_VIEWS = ("front", "side", "top", "three_quarter")
SILHOUETTE_VIEWS = (
    "silhouette_front",
    "silhouette_side",
    "silhouette_three_quarter",
)
DETAIL_VIEWS = ("detail",)
CLAY_VIEWS = ("clay_three_quarter",)
ALL_PREVIEW_FILES = (
    PREVIEW_VIEWS + SILHOUETTE_VIEWS + DETAIL_VIEWS + CLAY_VIEWS
)
BEAUTY_VIEWS = PREVIEW_VIEWS + DETAIL_VIEWS
DIAGNOSTIC_VIEWS = CLAY_VIEWS + SILHOUETTE_VIEWS
PRIMARY_VIEW = "three_quarter"
