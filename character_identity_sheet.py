"""Deterministic local Identity Sheet composition for MiniMax H3 Character Swap.

H3 reads a Character Swap reference as a single picture.  The verified failure
mode in this project was never "the wrong person was pasted"; it was that the
P Picture was far too small for the reference encoder to bind the *face* and the
*wardrobe* (the project's primary cast picture is 209x600, so its head is only
~125 pixels).  H3 therefore kept the palette and silhouette but invented a new
face, an older apparent age and different clothing.

The referenced community workflow
`ComfyUI-H3-Character-Sheets` (Jalen-Brunson) solves the same problem for
*generated* sheets: one Subject, several Pictures with declared roles, and one
multi-panel output layout where enlarged heads sit above body/outfit panels.
This module reproduces that panel grammar **locally with PIL** -- no GPU, no
model and no extra ComfyUI node pack -- so an illustrated cast picture can be
magnified into an identity sheet before it is ever uploaded to Relay.

Panels are crops of the *same* artwork, so the reference can never invent a new
medium: a cartoon stays a cartoon.  Layout indices 0-7 mirror the upstream
presets so a sheet authored here can also be re-generated on the H3 still
workflow with the same semantics.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import subprocess
from dataclasses import asdict, dataclass, replace
from itertools import chain
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageStat

# Bump whenever the crop grammar or resampling changes so cached sheets are
# rebuilt instead of silently reused with a different meaning.
# v4: the head panel is a skull, not a bust (skull-width ceiling on head height),
# which is what finally magnifies the face instead of re-showing the chest.
# v5: two changes, both driven by round-15 S3/S10 (grey hair, wrinkles) and
# round-15 S2 (a second correctly-dressed figure standing in the Shot).  The
# layout vote now follows the face instead of averaging it with the wardrobe
# panel, and the outfit panel can be cut to what the Shot actually frames.
# v6: opaque artwork whose outer bands carry burned-in captions, a show title
# or social-UI chrome is de-contaminated *before* it is ever cropped, so no
# panel can publish that dirt as an identity fact (round 19 S1: the P5 Picture
# is a screen-grab and both of its panels kept the burned-in title).
# v7: the head is walked row by row along the opaque run that stays attached
# to the skull axis.  Whole-row measurement let a raised arm widen rows that
# are still head, so the shoulder line read 65 rows early and the "enlarged
# head panel" was a bald forehead above the eyes -- no eyes, nose, moustache
# or chin, which is why H3 repainted the face older every single time.
# v8: the framed-wardrobe views gain ``full``, which keeps the whole neck-down
# figure (blue tunic hem, yellow checked trousers, shoes) inside the outfit
# panel instead of stopping at the hem.  Round 28 measured the black-shirt P1
# artwork (252x370): the shipped ``medium`` share 0.62 cuts the crop at
# [0,153,250,288], which is *above* the trousers -- every row below y=296, the
# yellow checks and the shoes, had zero authority, and the user graded the
# result as "衣服完全不像参考图".  At the same OUTFIT_VIEW_OUTFIT_AREA the head
# panel is byte-for-byte the same size as the take the user graded "头部效果
# 完美" (coverage 0.5259), so the fix only adds authority.
IDENTITY_SHEET_ENGINE_VERSION = 8
IDENTITY_SHEET_SIDECAR_SUFFIX = ".identity_sheet.json"
DEFAULT_MAX_MEGAPIXELS = 1.0

# How much of the neck-down artwork a Shot that never reaches the feet should
# be shown.  Round-15 S2: the sheet carried the full figure -- legs, shoes --
# and Relay painted it as an extra standing person beside the subject, because
# a whole figure is the strongest possible cue that a whole figure belongs in
# the frame.  The upstream prompt says the opposite ("show only the portions of
# the replacement character that belong within that framing"), so the panel is
# now cut at the framing line and keeps authority only over what is visible.
# ``full`` is the share for a Shot that does reach the hips and below: it keeps
# the entire neck-down figure, so nothing the Shot frames is left without a
# reference (round 28: the 0.62 cut stopped above the yellow checked trousers
# and the shoes never had any authority at all).
OUTFIT_VIEW_SHARES: dict[str, float] = {
    "close_up": 0.34,
    "medium": 0.62,
    "full": 1.0,
}
OUTFIT_VIEW_TAGS: dict[str, str] = {
    "close_up": "uchest",
    "medium": "uhip",
    "full": "fullfig",
}
# Canvas area a *cropped* wardrobe panel still needs.  The designed share (0.56
# in the single-face layout) buys the whole neck-down figure; once the panel
# only carries the chest, that area is worth more to the face.  Round-15
# measured the exchange rate for the 209x600 P1 artwork: the head reached 20.9 %
# of Picture 1 at its designed 0.44 share and 34.2 % once it owned 0.56.
# ``full`` deliberately repeats ``medium``'s 0.44: round 28 probed the whole
# curve (0.44 / 0.48 / 0.52 / 0.56) on the project's own P1 artwork and 0.44
# leaves the head panel exactly where the user graded it "完美" (coverage
# 0.5259) while the wardrobe crop grows from 250x135 to 250x217.
OUTFIT_VIEW_OUTFIT_AREA: dict[str, float] = {
    "close_up": 0.36,
    "medium": 0.44,
    "full": 0.44,
}

# How much a non-primary panel may tip the grid-orientation vote.  The head is
# the surface the user grades, so the wardrobe may only break a near-tie: at the
# old 0.2 the 209x600 P1 artwork was split into columns and its head fell to
# 15.3 % of Picture 1 (stacking kept it at 21 %+), and Relay repainted the
# missing face detail as grey hair and forehead wrinkles (round-15 S3/S10).
ORIENT_SECONDARY_PANEL_WEIGHT = 0.05

# H3 picture-role vocabulary (upstream `H3RefSlots` semantics).  A local sheet
# is one Picture, so the role recorded per panel documents which surface each
# panel is authoritative for.
ROLE_FACE_PRIMARY = "face (primary)"
ROLE_BODY = "body"
ROLE_OUTFIT = "outfit"
ROLE_APPEARANCE = "appearance"
ROLE_CHARACTER_SHEET = "character sheet"

# Round 69 item 7 — which *view of the body* a panel is authoritative for.
# These are not the ``outfit_view`` framing values (close_up / medium / full),
# which say how far *down* a wardrobe panel is cut; a view says which *side* of
# the character it shows.  Presets 0-8 carry no view tag and compose exactly as
# they always did, so nothing about an existing sheet changes.  Preset 9 tags its
# panels, and a tagged panel is filled from a real picture for that view when the
# director has supplied one and from the front artwork (mirrored, for the rear)
# when they have not.  The sidecar records which of the two happened, which is
# the whole point: a mirrored silhouette has stabilised contour for years and it
# has never once told H3 what the back of this character's head looks like.
VIEW_FRONT = "front"
VIEW_REAR = "rear"
VIEW_SIDE = "side"
PANEL_VIEWS = (VIEW_FRONT, VIEW_REAR, VIEW_SIDE)
# What ``PanelRecord.view_source`` says about where a panel's pixels came from.
VIEW_SOURCE_REFERENCE = "reference picture"
VIEW_SOURCE_FRONT = "front artwork"
VIEW_SOURCE_MIRRORED_FRONT = "mirrored front artwork"

# Relay normalises the reference into the V1 frame, so an extreme sheet canvas
# would fight the video geometry; clamp instead.
MIN_CANVAS_ASPECT = 0.40
MAX_CANVAS_ASPECT = 2.50
# A panel smaller than this never conditions anything; it only dilutes the
# panels that do, so it is dropped and its quota is redistributed.
MIN_USEFUL_PANEL_SHARE = 0.055
# A cast picture lifted out of a video frame usually carries solid colour bars.
# Solid rows/columns are trimmed from the outside before the border colour is
# sampled, but never this much of one axis.
UNIFORM_BAND_TOLERANCE = 15.0
UNIFORM_BAND_MAX_FRACTION = 0.12
# A real head band is roughly square-tall.  Anything flatter than this is a
# hair-only sliver produced by a segmentation that never found a shoulder line.
MAX_HEAD_BOX_ASPECT = 2.6
MIN_HEAD_BOX_ASPECT = 0.30
# A skull is never much taller than it is wide once its widest row (hair, hat
# brim or ears) is known.  Measured on the project's own casts: P1 skull 99 px
# wide -> chin at 145 px (1.46x), P3 skull 98 px -> chin at 134 px (1.37x).
# Anything taller than that below the crown is chest, not head.
MAX_HEAD_HEIGHT_TO_SKULL_WIDTH = 1.45
SKULL_WIDTH_SAMPLE_SHARE = 0.55
# --- head-run geometry (engine v7) ------------------------------------------
# The head is measured as the opaque run that stays attached to the skull axis,
# never as the whole row: a cartoon cast that waves one arm keeps a second run
# at head height, and that run used to set both the shoulder line and the width
# of the face panel (round 21 black-shirt P1: the panel was cut at the eyes).
CROWN_SEED_SHARE = 0.10
HEAD_RUN_BRIDGE_SHARE = 0.12
HEAD_RUN_MAX_AXIS_SHIFT = 1.10
HEAD_SEARCH_SHARE = 0.62
HEAD_RUN_SHOULDER_VS_SKULL = 1.05
HEAD_RUN_SHOULDER_VS_NECK = 1.35
HEAD_RUN_NECK_CONFIRM_SHARE = 0.92
MERGED_TORSO_RUN_SHARE = 1.30
HEAD_HEIGHT_MIN_SKULL_SHARE = 1.10
_OPAQUE_RUN_PATTERN = re.compile(rb"[\x80-\xff]+")

# --- face-panel cell fill ----------------------------------------------------
# The correct head box is narrow (a cartoon skull is taller than it is wide),
# while the head cell is usually wide.  Contain-fitting the bare crop therefore
# letterboxes the face *inside its own cell* and the face never reaches the
# pixel budget H3 conditions on (round 21: coverage fell 0.304 -> 0.194).  The
# crop is grown with real artwork around the skull -- mostly downward, so the
# panel carries neck, shoulders and the collar it must repaint -- never by
# upscaling and never past this factor.
HEAD_PANEL_MAX_GROW = 1.45
HEAD_PANEL_DOWNWARD_GROW_SHARE = 0.75
# Growing the face box sideways splits it as evenly as the frame allows, because
# a face that lands off the middle of its panel reads as a crop of somebody
# else's torso.  Engine v7 already kept the waving cast's second run (x 204-250)
# out of the head box, and the 1.45x cap is what stops that sleeve from walking
# back in through the panel edge; the column coverage table only decides which
# side of an odd leftover column carries artwork.

# --- burned-in overlay suppression ------------------------------------------
# A cast picture pulled off a social post carries white subtitles, a burned-in
# show title and a like/comment row, and every Identity Sheet panel is a crop of
# that same artwork -- so the sheet republishes the chrome as character design.
# Round-19 S1 used the P5 screen-grab: both panels still carried the title and
# the UI column, and the take was graded "wrong person" because the painted face
# matched the *screenshot's* scowling hat-wearer rather than the intended cast.
# The pass below is deliberately not a generic inpainter.  It trusts only
# near-white pixels, only inside the outer bands where captions actually live,
# and only for *interior* runs: text sits inside a background, while a
# legitimate white garment or a paper sheet runs to the artwork's own edge.
# These values were converged on the project's own dirty cast picture (P5,
# 1.3 % of pixels repaired) against clean ones (P6, 0.12 %).
OVERLAY_WHITE_MIN = 240
OVERLAY_RUN_MIN_PX = 2
OVERLAY_RUN_MAX_FRACTION = 0.30
OVERLAY_BAND_ROWS = {"top": 0.20, "bottom": 0.13}
OVERLAY_BAND_COLUMNS = {"left": 0.10, "right": 0.16}
OVERLAY_ROUNDS = 2
OVERLAY_HALO_DILATIONS = (9, 5)
OVERLAY_BLEND_BLUR_RADIUS = 3.0
# Past this fraction of the picture the caption hypothesis is wrong: the artwork
# really is white paper, so leave the source alone.
OVERLAY_MAX_REPAIRED_FRACTION = 0.08


# --- source figure-reveal probe ---------------------------------------------
# A half-body source Shot and a whole-body source Shot need opposite answers from
# the Identity Sheet, and until now nothing could tell them apart.  The shipped
# ``full`` outfit view puts the whole figure -- trousers, shoes -- inside Picture
# 1, which is the single strongest cue that a whole figure belongs in the frame
# (round 28 measured that on this Project's own artwork), and the close-up sheet
# crop lock that is supposed to cancel it only fires for a *face-filling* box.
# The black-shirt Project's round-51 take is neither: <Video 1> frames the
# performer knees-up and cuts him at the bottom edge, the auto role rectangle is
# 0.30 x 0.30 so it is not face-dominant, and the take answered by widening the
# shot downward until the whole cartoon figure -- shoes included -- sat inside
# the frame ("V1 的人物是半身，但是创作出來的卻是 P1 的全身").
#
# The probe below answers the question directly from pixels of the plate Relay
# was handed: does the moving subject reach the bottom edge of the frame, or is
# static background visible below it?  Background is the per-pixel temporal
# median, so a camera-static Shot needs no segmentation at all, and the subject
# band is deliberately the narrow middle of the tracked role box rather than a
# padded box: measured on this Project's own 426x642 source clip, a box padded
# 20 % sideways lets moving bystanders qualify on 92-99 % of rows and fakes a
# figure running off the bottom, while the central 40 % of the box's own width
# does not.
FIGURE_REVEAL_PROBE_WIDTH = 96
FIGURE_REVEAL_SAMPLE_COUNT = 6
# Symmetric inset as a fraction of the role box's own width, so 0.30 leaves the
# central 40 % of it.
FIGURE_REVEAL_BAND_INSET = 0.30
FIGURE_REVEAL_MIN_BAND_PIXELS = 8
FIGURE_REVEAL_MIN_ROW_SHARE = 0.30
FIGURE_REVEAL_MIN_ROW_PIXELS = 3
FIGURE_REVEAL_DIFF_THRESHOLD = 30
# How close to the last decoded row subject evidence has to be before the figure
# counts as cut off.  A normalized share was the first attempt and it is the wrong
# unit: measured on this Project's own plate the true positive lands on the last
# row (1.000) while a real negative -- the same plate shrunk into a taller frame
# with static black below it -- still reaches 0.984 of its height because codec
# noise moves a few pixels inside pure black.  A share of 0.985 therefore passed
# that negative by one third of a row.  Rows are geometry, shares are not, and one
# row of tolerance is what separates the two measurements above.
FIGURE_REVEAL_BOTTOM_TOLERANCE_ROWS = 1
FIGURE_REVEAL_MIN_FRAMES = 2
# Past this share of qualifying rows the whole frame is moving -- a handheld
# plate, heavy grain, or a band padded so wide that bystanders join in -- and
# "the subject's lowest row" stops meaning anything.  The wide 20 %-padded band
# measured 0.92-0.99 on this Project's own source clip, which is how it produced
# a confident false "the figure runs off the bottom"; the narrow central band
# measures 0.31-0.56 on the same clip.  A Shot in this regime is reported as not
# measurable rather than guessed at.
FIGURE_REVEAL_GLOBAL_MOTION_SHARE = 0.90
# How many sampled frames have to show subject evidence at the bottom edge before
# it counts.  One frame is too few; requiring all of them is too many, because a
# performer who stands still for part of the Shot leaves the moving evidence to
# the frames where he does not -- which is exactly what the 426x642 plate shows
# (two of six sampled frames reach the last row, the median lands at 0.944).
FIGURE_REVEAL_MIN_BOTTOM_FRAMES = 2


@dataclass(frozen=True)
class SheetPanel:
    """One panel of a composed sheet."""

    slot: str            # head | body | outfit | detail | full
    col: int
    row: int
    col_span: int = 1
    row_span: int = 1
    mirror: bool = False
    role: str = ""
    # Which side of the character this panel shows ("" = unspecified, i.e. the
    # legacy presets, which are all composed from one front artwork).
    view: str = ""
    # Designed share of the canvas this panel should own.  0 means "take the
    # share implied by the remaining panels".  Area -- not cell shape -- is the
    # quantity that decides how much reference detail the H3 encoder can bind,
    # because Relay normalises the sheet into the V1 frame before encoding.
    area_weight: float = 0.0


@dataclass(frozen=True)
class SheetPreset:
    """One sheet layout; index matches the upstream 0-7 CHOOSE SHEET control."""

    index: int
    label: str
    aspect: tuple[int, int]
    grid: tuple[int, int]
    panels: tuple[SheetPanel, ...]
    description: str
    synthetic_rear: bool = False
    # Designed area share per panel, in panel order.  Empty means even shares.
    panel_weights: tuple[float, ...] = ()


SHEET_PRESETS: dict[int, SheetPreset] = {
    preset.index: preset
    for preset in (
        SheetPreset(
            0,
            "Head + full body (identity first)",
            (3, 4),
            (2, 1),
            (
                SheetPanel("head", 0, 0, role=ROLE_FACE_PRIMARY),
                SheetPanel("body", 1, 0, role=ROLE_BODY),
            ),
            # declared with two columns; ``_arrangement`` stacks them when the
            # canvas is portrait, which is where a side-by-side head is starved
            # of width and stays ~13 % of the reference.
            "Enlarged head beside the complete figure. Recommended for "
            "Character Swap: the face gets maximum reference area while the "
            "body panel still supplies proportions and wardrobe.",
            panel_weights=(0.46, 0.54),
        ),
        SheetPreset(
            1,
            "Head above full body",
            (3, 4),
            (1, 2),
            (
                SheetPanel("head", 0, 0, role=ROLE_FACE_PRIMARY),
                SheetPanel("body", 0, 1, role=ROLE_BODY),
            ),
            "Upstream sheet index 0/3 grammar: head row above the figure. "
            "Keeps the full body at native aspect on a portrait canvas.",
            panel_weights=(0.42, 0.58),
        ),
        SheetPreset(
            2,
            "Head + body + outfit",
            (4, 3),
            (2, 2),
            (
                SheetPanel("head", 0, 0, row_span=2, role=ROLE_FACE_PRIMARY),
                SheetPanel("body", 1, 0, role=ROLE_BODY),
                SheetPanel("outfit", 1, 1, role=ROLE_OUTFIT),
            ),
            "Adds a dedicated wardrobe panel, which is the panel that fixes "
            "'clothing does not match the reference' drift.",
            panel_weights=(0.44, 0.30, 0.26),
        ),
        SheetPreset(
            3,
            "Head / mirrored head / body",
            (3, 2),
            (3, 1),
            (
                SheetPanel("head", 0, 0, role=ROLE_FACE_PRIMARY),
                SheetPanel("head", 1, 0, mirror=True, role="face"),
                SheetPanel("body", 2, 0, role=ROLE_BODY),
            ),
            "Turnaround-style row. The mirrored head is a synthetic opposite "
            "three-quarter read of the same artwork, not a new angle.",
            panel_weights=(0.40, 0.28, 0.32),
        ),
        SheetPreset(
            4,
            "Head only (maximum magnification)",
            (1, 1),
            (1, 1),
            (SheetPanel("head", 0, 0, role=ROLE_FACE_PRIMARY),),
            "Single face plate. Use when identity drift, not wardrobe, is the "
            "failure; pair it with a second body Picture in Relay.",
            panel_weights=(1.0,),
        ),
        SheetPreset(
            5,
            "Body + outfit (wardrobe first)",
            (3, 4),
            (2, 1),
            (
                SheetPanel("body", 0, 0, role=ROLE_BODY),
                SheetPanel("outfit", 1, 0, role=ROLE_OUTFIT),
            ),
            "Wardrobe-led sheet for Shots where the head is not the failing "
            "surface but the costume keeps drifting.",
            panel_weights=(0.55, 0.45),
        ),
        SheetPreset(
            6,
            "Detail grid (2x2)",
            (1, 1),
            (2, 2),
            (
                SheetPanel("head", 0, 0, role=ROLE_FACE_PRIMARY),
                SheetPanel("body", 1, 0, role=ROLE_BODY),
                SheetPanel("head", 0, 1, mirror=True, role="face"),
                SheetPanel("outfit", 1, 1, role=ROLE_OUTFIT),
            ),
            "Four even panels for pictures whose design detail is spread over "
            "face, costume and props.",
            panel_weights=(0.34, 0.24, 0.18, 0.24),
        ),
        SheetPreset(
            7,
            "Head + front body + rear body",
            (4, 3),
            (3, 1),
            (
                SheetPanel("head", 0, 0, role=ROLE_FACE_PRIMARY),
                SheetPanel("body", 1, 0, role=ROLE_BODY),
                SheetPanel("body", 2, 0, mirror=True, role=ROLE_BODY),
            ),
            "Upstream preset 7 grammar. The rear panel is a mirrored read of "
            "the same artwork: it stabilises silhouette continuity, it does "
            "not invent unseen back-of-head detail.",
            synthetic_rear=True,
            panel_weights=(0.40, 0.32, 0.28),
        ),
        # Not an upstream layout: added for this project's close-up failures.
        # Round-14 S2 evidence - a sheet whose body panel shows the whole
        # figure puts a *second* face next to the head panel, and a close-up
        # V1 frame has no room for two faces, so Relay cloned the character
        # (one oversized face plus one correctly dressed small figure).  The
        # ``outfit`` slot is the same artwork from the neck down, so this
        # layout keeps wardrobe authority while the sheet carries exactly one
        # face.  Engine version stays 4: no existing panel crop changed, and
        # the new index writes its own ``identitysheet08`` filename.
        SheetPreset(
            8,
            "Head + neck-down figure (single face)",
            (3, 4),
            (2, 1),
            (
                SheetPanel("head", 0, 0, role=ROLE_FACE_PRIMARY),
                SheetPanel("outfit", 1, 0, role=ROLE_OUTFIT),
            ),
            "One face only. The second panel is the same artwork from the neck "
            "down, so a close-up Shot cannot read two competing faces and "
            "clone the character while the wardrobe still has an authority "
            "panel.",
            panel_weights=(0.44, 0.56),
        ),
        # Round 69 item 7: the turnaround the director asked for.  Preset 7 fakes
        # its rear panel by mirroring the front artwork, which is why a take can
        # match the sheet in profile and still invent the back of the head.  This
        # layout tags every body panel with the view it is meant to show, so a
        # real rear or side picture the director adds next to the P Picture is
        # used for that panel and nothing else is invented.  Panels without a real
        # view fall back to the front artwork (mirrored for the rear) and the
        # sidecar says so.
        SheetPreset(
            9,
            "Head + front / rear / side figure (real views)",
            (4, 3),
            (4, 1),
            (
                SheetPanel("head", 0, 0, role=ROLE_FACE_PRIMARY, view=VIEW_FRONT),
                SheetPanel("body", 1, 0, role=ROLE_BODY, view=VIEW_FRONT),
                SheetPanel("body", 2, 0, role=ROLE_BODY, view=VIEW_REAR),
                SheetPanel("body", 3, 0, role=ROLE_BODY, view=VIEW_SIDE),
            ),
            "Turnaround sheet for Character Swap: the rear and side panels are "
            "filled from real rear / side artwork when the Media Pool has it, so "
            "the back of the head and the profile stop being invented. Without "
            "those pictures the layout still composes, and the sidecar names "
            "which panels stayed synthetic.",
            panel_weights=(0.31, 0.27, 0.21, 0.21),
        ),
    )
}
DEFAULT_SHEET_PRESET = 0


@dataclass
class PanelRecord:
    slot: str
    role: str
    rect: list[int]
    mirrored: bool
    source_crop: list[int]
    # Fraction of the finished canvas actually covered by artwork (not padding).
    coverage: float = 0.0
    # Round 69 item 7: which body view the panel carries and where its pixels
    # actually came from, so a sidecar can never present a synthetic read as an
    # unseen angle.  Defaults keep sidecars written before this field loadable.
    view: str = ""
    view_source: str = ""


@dataclass
class IdentitySheetResult:
    ok: bool
    reason: str = ""
    sheet_path: str = ""
    head_path: str = ""
    body_path: str = ""
    preset: int = DEFAULT_SHEET_PRESET
    preset_label: str = ""
    # Framing the wardrobe panel was cut to ("" = the whole neck-down figure).
    outfit_view: str = ""
    width: int = 0
    height: int = 0
    source_path: str = ""
    source_fingerprint: str = ""
    engine_version: int = IDENTITY_SHEET_ENGINE_VERSION
    canvas_aspect: float = 0.0
    head_coverage: float = 0.0
    # Round 59: how much *real* face the reference ever had.  ``head_coverage``
    # says how big the head panel is on the finished sheet, which is a layout
    # fact; this number says how many source pixels are behind it, which is the
    # fact that decides whether H3 can draw the face at all.  A 0.53 head panel
    # grown from a 178x152 crop is 4.3x invented, and that invention is what the
    # "the cartoon became an old man" reports keep landing on.
    source_head_crop_megapixels: float = 0.0
    source_megapixels: float = 0.0
    dropped_slots: list[str] = None  # type: ignore[assignment]
    panels: list[PanelRecord] = None  # type: ignore[assignment]
    notes: list[str] = None  # type: ignore[assignment]
    # Round 69 item 7: fingerprint of every real rear / side picture this sheet
    # was composed from.  It is part of the cache key, so dropping a new rear
    # drawing into the Media Pool recomposes the sheet instead of quietly reusing
    # a stale one -- and it stays empty for presets 0-8, whose sidecars keep
    # validating exactly as they did before.
    view_fingerprints: dict = None  # type: ignore[assignment]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["panels"] = [
            panel if isinstance(panel, dict) else asdict(panel)
            for panel in (self.panels or [])
        ]
        return payload


def source_head_crop_megapixels(panels) -> float:
    """Return the megapixels of real artwork behind the head panel.

    Read from the recorded ``source_crop`` box in the *source* picture, so a
    sheet that was magnified four times still reports the detail it actually
    had.  Sidecars written before this field existed answer from their panel
    rows, which is why the cached path recomputes rather than trusting the
    stored number.
    """

    for panel in panels or []:
        if isinstance(panel, dict):
            slot = str(panel.get("slot") or "")
            mirrored = bool(panel.get("mirrored"))
            crop = panel.get("source_crop")
        else:
            slot = str(getattr(panel, "slot", "") or "")
            mirrored = bool(getattr(panel, "mirrored", False))
            crop = getattr(panel, "source_crop", None)
        if slot != "head" or mirrored or not isinstance(crop, (list, tuple)):
            continue
        if len(crop) < 4:
            continue
        try:
            left, top, right, bottom = (float(value) for value in crop[:4])
        except (TypeError, ValueError):
            continue
        width = max(0.0, right - left)
        height = max(0.0, bottom - top)
        return round((width * height) / 1_000_000.0, 5)
    return 0.0


def _failure(reason: str, source: Path | None = None) -> IdentitySheetResult:
    return IdentitySheetResult(ok=False, reason=reason, source_path=str(source or ""))


def source_fingerprint(path: Path) -> str:
    """Cheap immutable identity for a Media Pool picture."""

    try:
        stat = path.stat()
    except OSError:
        return ""
    return hashlib.sha1(
        f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
    ).hexdigest()[:16]


def _segment_mask(image: Image.Image) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Return a binary artwork mask plus its subject bounding box.

    Transparent cut-outs use real alpha.  Opaque artwork is segmented against
    its own border colour, which is what an illustrated cast picture normally
    provides (flat paper background).
    """

    rgba = image.convert("RGBA")
    width, height = rgba.size
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] < 250:
        mask = alpha.point(lambda value: 255 if value > 8 else 0)
    else:
        rgb = rgba.convert("RGB")
        band_left, band_top, band_right, band_bottom = _trim_uniform_bands(rgb)
        artwork = rgb.crop((band_left, band_top, band_right, band_bottom))
        artwork_width = max(1, band_right - band_left)
        artwork_height = max(1, band_bottom - band_top)
        border = (
            ImageOps.crop(
                artwork, max(1, min(artwork_width, artwork_height) // 64)
            )
            .resize((1, 1), Image.Resampling.BOX)
            .convert("RGB")
            .getpixel((0, 0))
        )
        flat = Image.new("RGB", artwork.size, border)
        delta = ImageChops.difference(artwork, flat).convert("L")
        artwork_mask = delta.point(lambda value: 255 if value > 26 else 0)
        # A photograph has no flat background, so its difference map saturates
        # into a noisy full-frame mask.  Treat that case as "no segmentation":
        # the full frame is safer than a crop of an arbitrary high-contrast
        # region, and every downstream panel still receives the whole artwork.
        box = artwork_mask.getbbox() or (0, 0, artwork_width, artwork_height)
        coverage = (box[2] - box[0]) * (box[3] - box[1]) / float(
            max(1, artwork_width * artwork_height)
        )
        density = sum(
            1
            for value in artwork_mask.resize(
                (64, 64), Image.Resampling.BOX
            ).getdata()
            if value > 96
        ) / 4096.0
        mask = Image.new("L", (width, height), 0)
        filled = (
            Image.new("L", artwork.size, 255)
            if coverage > 0.94 and density > 0.55
            else artwork_mask
        )
        mask.paste(filled, (band_left, band_top))
    box = mask.getbbox() or (0, 0, width, height)
    return mask, (int(box[0]), int(box[1]), int(box[2]), int(box[3]))


def _trim_uniform_bands(rgb: Image.Image) -> tuple[int, int, int, int]:
    """Return the artwork frame with solid letterbox/pillarbox bars removed.

    The border colour that the segmentation is measured against used to be the
    mean of the frame edge.  A picture exported from a video frame carries
    plain colour bars, so on those pictures the border colour became the *bar*
    colour, the flat paper background then scored as artwork, the mask
    saturated to the whole frame, and the enlarged head panel collapsed onto a
    hair-only strip with no eyes, nose or mouth in it.  Trimming whole
    single-colour rows and columns from the outside keeps the paper — and
    therefore the head band — measurable.
    """

    width, height = rgb.size
    if width < 16 or height < 16:
        return (0, 0, width, height)

    def row_spread(row: int) -> float:
        return float(sum(ImageStat.Stat(rgb.crop((0, row, width, row + 1))).stddev))

    def column_spread(column: int) -> float:
        return float(sum(ImageStat.Stat(rgb.crop((column, 0, column + 1, height))).stddev))

    limit_v = max(1, int(height * UNIFORM_BAND_MAX_FRACTION))
    limit_h = max(1, int(width * UNIFORM_BAND_MAX_FRACTION))
    top = 0
    while top < limit_v and row_spread(top) <= UNIFORM_BAND_TOLERANCE:
        top += 1
    bottom = height
    while (
        height - bottom < limit_v
        and bottom > top + 1
        and row_spread(bottom - 1) <= UNIFORM_BAND_TOLERANCE
    ):
        bottom -= 1
    left = 0
    while left < limit_h and column_spread(left) <= UNIFORM_BAND_TOLERANCE:
        left += 1
    right = width
    while (
        width - right < limit_h
        and right > left + 1
        and column_spread(right - 1) <= UNIFORM_BAND_TOLERANCE
    ):
        right -= 1
    return (left, top, right, bottom)


def _row_profile(mask: Image.Image) -> list[int]:
    """Mean mask coverage per row, as one downsampled column of values."""

    width, height = mask.size
    if width <= 0 or height <= 0:
        return []
    return [int(value) for value in mask.resize((1, height), Image.Resampling.BOX).getdata()]


def _widest_row(mask: Image.Image, first_row: int, last_row: int) -> int:
    """Widest opaque run (in pixels) between ``first_row`` and ``last_row``."""

    widest = 0
    start = max(0, int(first_row))
    stop = min(mask.height, max(start + 1, int(last_row)))
    for row in range(start, stop):
        band = mask.crop((0, row, mask.width, row + 1)).getbbox()
        if band is None:
            continue
        widest = max(widest, band[2] - band[0])
    return widest


def _head_run_walk(
    mask: Image.Image,
    subject: tuple[int, int, int, int],
    search_stop: int,
) -> tuple[int, list[tuple[int, int, int]]]:
    """Follow the opaque run that stays attached to the skull, one row at a time.

    ``estimate_head_box`` used to measure the *whole* row, so anything that left
    the silhouette at head height -- a raised arm, a hand on the hip, a caption
    column -- widened rows that are still head.  Both the shoulder line and the
    horizontal extent of the face panel were then set by that dirt.  On the
    project's own black-shirt cast (a 252x370 waving uncle) the arm kept a
    second run from row 76 down: the "shoulder line" read at row 75, the skull
    clamp measured a chest-contaminated 84 px, and the enlarged panel that the
    prompt calls the sole authority for facial structure was cut at the eyes --
    a bald forehead, two eyebrows and the tops of some glasses.  No eyes, no
    nose, no moustache, no chin, so H3 painted those features itself.  That is
    the "character turned into an old man" and "the clothes are nothing like
    the reference" report, and the wardrobe panel inherited the same error
    because it starts at ``head_bottom``.

    Walking only the run contiguous with the skull axis ignores the arm.
    Returns ``(row, left, right)`` with ``right`` exclusive, ascending by row,
    for every row where the head run could be followed, together with the seed
    row -- the widest head run in the crown band, which is where the landmark
    measurement has to start because everything above it is the crown tapering
    to its tip rather than a neck.
    """

    left, top, right, bottom = (int(value) for value in subject)
    x_start = max(0, left - 2)
    x_stop = min(mask.width, right + 2)
    stop = max(top + 1, min(int(search_stop), bottom))
    if x_stop - x_start < 2 or stop - top < 2:
        return -1, []

    # An "L" mask is one byte per pixel, so one row is one contiguous slice and
    # its opaque runs are found in C rather than in a per-pixel Python loop.
    data = mask.tobytes() if mask.mode == "L" else mask.convert("L").tobytes()
    stride = mask.width
    runs_by_row: dict[int, list[tuple[int, int]]] = {}
    for row in range(top, stop):
        offset = row * stride + x_start
        line = data[offset : offset + (x_stop - x_start)]
        found = [
            (match.start() + x_start, match.end() + x_start)
            for match in _OPAQUE_RUN_PATTERN.finditer(line)
        ]
        if found:
            runs_by_row[row] = found
    if not runs_by_row:
        return -1, []

    # The crown band holds the widest run of the head itself, which is the axis
    # everything below is measured against.
    seed_row, seed_run = -1, None
    probe_rows = max(4, int(max(1, bottom - top) * CROWN_SEED_SHARE))
    for row in range(top, min(stop, top + probe_rows)):
        for run in runs_by_row.get(row, ()):
            if seed_run is None or run[1] - run[0] > seed_run[1] - seed_run[0]:
                seed_row, seed_run = row, run
    if seed_run is None:
        return -1, []

    def _follow(rows: range, previous: tuple[int, int]) -> list[tuple[int, int, int]]:
        walked: list[tuple[int, int, int]] = []
        for row in rows:
            candidates = runs_by_row.get(row)
            if not candidates:
                continue
            bridge = max(2, int((previous[1] - previous[0]) * HEAD_RUN_BRIDGE_SHARE))
            best: tuple[int, int] | None = None
            best_overlap = 0
            for run in candidates:
                overlap = min(previous[1] + bridge, run[1]) - max(
                    previous[0] - bridge, run[0]
                )
                if overlap > best_overlap:
                    best, best_overlap = run, overlap
            if best is None:
                # A line-art gap or a hairline split: stay on the axis instead of
                # adopting whatever happens to sit nearby.
                centre = (previous[0] + previous[1]) // 2
                nearest = min(
                    candidates,
                    key=lambda run: abs((run[0] + run[1]) // 2 - centre),
                )
                if abs((nearest[0] + nearest[1]) // 2 - centre) > int(
                    max(4, (previous[1] - previous[0]) * HEAD_RUN_MAX_AXIS_SHIFT)
                ):
                    continue
                best = nearest
            previous = best
            walked.append((row, previous[0], previous[1]))
        return walked

    upward = _follow(range(seed_row - 1, top - 1, -1), seed_run)
    walked = list(reversed(upward))
    walked.append((seed_row, seed_run[0], seed_run[1]))
    walked.extend(_follow(range(seed_row + 1, stop), seed_run))
    return seed_row, walked


def _head_run_landmarks(
    walked: list[tuple[int, int, int]],
    seed_row: int = -1,
) -> tuple[int, int, int]:
    """Return ``(peak_row, peak_width, shoulder_row)`` for one head walk.

    The head run can never be wider than its own widest row -- hair, hat brim
    and ears all belong to the head -- so the row where that run grows past the
    peak *and* past the narrowest row since (the neck) is the row where it
    merged with the body.  The skull measurement is frozen the moment that
    narrowing appears: without the freeze a torso wider than the head simply
    reads as "the head got wider again", the merge row is swallowed as a new
    peak and no shoulder line ever appears -- which is exactly how a 101 px hat
    over a 61 px face ended with the 161 px shoulder patch called the skull.
    Requiring a real neck first is also what keeps a raised arm, which merges
    with the torso at waist height, from posing as a shoulder line.
    ``shoulder_row`` is -1 when the silhouette never does that, which is the
    close-up headshot regime where only skull proportions are left.
    """

    # The scan starts at the seed, never at the top of the walk.  Rows above the
    # seed are the crown narrowing toward its tip, and on a bald skull or a
    # pointed hat that taper is steeper and longer than a real neck pinch: on the
    # project's own black-shirt cast it froze the skull at 33 px on row 18 and
    # called row 23 the shoulder line, so the panel that the prompt treats as the
    # sole authority for facial structure was a stamp on the forehead -- which is
    # how "the character turned into an old man" survived every re-render.
    start = 0
    if seed_row >= 0:
        for index, (row, _left, _right) in enumerate(walked):
            if row >= seed_row:
                start = index
                break
    peak_row, peak_left, peak_right = walked[start]
    peak_width = max(1, peak_right - peak_left)
    neck_width = peak_width
    skull_locked = False
    shoulder_row = -1
    for row, run_left, run_right in walked[start + 1 :]:
        width = max(1, run_right - run_left)
        if not skull_locked:
            # Still inside the crown: growth is hair/ears widening the skull, and
            # only a narrowing back below the widest row closes the measurement.
            if width > peak_width:
                peak_row, peak_width = row, width
                neck_width = width
                continue
            if width <= peak_width * HEAD_RUN_NECK_CONFIRM_SHARE:
                skull_locked = True
                neck_width = width
            continue
        if (
            width >= peak_width * HEAD_RUN_SHOULDER_VS_SKULL
            and width >= neck_width * HEAD_RUN_SHOULDER_VS_NECK
        ):
            shoulder_row = row
            break
        neck_width = min(neck_width, width)
    return peak_row, peak_width, shoulder_row


def estimate_head_box(
    mask: Image.Image,
    subject: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Locate the head band inside a standing figure's bounding box.

    Cartoon casts are drawn head-heavy, so the classic "top 20%" heuristic is
    only the fallback.  The primary signal is the skull's own walk: the widest
    head row gives the width, the row where that run merges with the body gives
    the chin, and the head rows themselves give the horizontal extent.  Engine
    v7 measures all three on the head's own run, so a limb or a caption column
    can no longer widen a row that is still face and cut the panel at the eyes.
    """

    left, top, right, bottom = subject
    subject_height = max(1, bottom - top)
    head_bottom = top + int(subject_height * 0.24)
    band_left, band_right = left, right
    seed_row, walked = _head_run_walk(
        mask,
        subject,
        min(bottom, top + int(subject_height * HEAD_SEARCH_SHARE)),
    )
    if walked:
        _, peak_width, shoulder_row = _head_run_landmarks(walked, seed_row)
        if peak_width >= max(2, (right - left) - 2) and shoulder_row < 0:
            # The walk found no silhouette at all: an opaque picture with no flat
            # background segments into a mask that fills the frame (the mustache
            # project's P4/P5 portraits), so every row is one run as wide as the
            # canvas, no shoulder can ever appear, and the only honest reading is
            # "this picture is the head".  Engine v6 answered that case with
            # figure proportions; without this guard the same picture reports a
            # 1069 px skull, a 666 px head and a face panel that is the frame.
            head_height = max(1, min(int(subject_height * 0.34), bottom - top))
            head_width = max(1, min(right - left, int(head_height * 1.15)))
            centre_x = (left + right) // 2
            return (
                max(0, centre_x - head_width // 2),
                top,
                min(mask.width, centre_x - head_width // 2 + head_width),
                min(bottom, top + head_height),
            )
        if shoulder_row >= 0:
            # The run merged with the torso on ``shoulder_row``, so the row
            # above it is still chin.
            head_bottom = shoulder_row - 1
        else:
            # No body signal at all: a close-up picture.  The skull's own aspect
            # is the only geometry left, still capped by the old proportion so a
            # hair-only sliver cannot claim the whole figure.
            head_bottom = top + min(
                int(subject_height * 0.42),
                int(peak_width * MAX_HEAD_HEIGHT_TO_SKULL_WIDTH),
            )
        # A face is taller than the skull is wide, and it is never much taller
        # than one skull-width plus the hair.  Floor first, then ceiling, so the
        # ceiling always wins when both bite.
        head_bottom = max(head_bottom, top + int(peak_width * HEAD_HEIGHT_MIN_SKULL_SHARE))
        head_bottom = min(
            head_bottom,
            top + int(peak_width * MAX_HEAD_HEIGHT_TO_SKULL_WIDTH),
            top + int(subject_height * 0.42),
            bottom - 1,
        )
        head_bottom = max(top + 1, head_bottom)
        band_values: list[int] = []
        for row, run_left, run_right in walked:
            if row > head_bottom:
                break
            if run_right - run_left > peak_width * MERGED_TORSO_RUN_SHARE:
                # The row had already merged with the torso: its width is the
                # wardrobe, not the head, and must not widen the face panel.
                continue
            band_values.append(run_left)
            band_values.append(run_right)
        if len(band_values) >= 2:
            band_left, band_right = min(band_values), max(band_values)
        else:
            merged_band = mask.crop((0, top, mask.width, head_bottom)).getbbox()
            band_left, band_right = (
                (left, right)
                if merged_band is None
                else (merged_band[0], merged_band[2])
            )
    band_left = max(0, min(band_left, right))
    band_right = max(band_left + 1, min(band_right, mask.width))
    pad_x = max(1, int((band_right - band_left) * 0.06))
    pad_y = max(1, int((head_bottom - top) * 0.08))
    head_box = (
        max(0, band_left - pad_x),
        max(0, top - pad_y),
        min(mask.width, band_right + pad_x),
        min(bottom, head_bottom + pad_y),
    )
    head_width = max(1, head_box[2] - head_box[0])
    head_height = max(1, head_box[3] - head_box[1])
    aspect = head_width / float(head_height)
    if aspect > MAX_HEAD_BOX_ASPECT or aspect < MIN_HEAD_BOX_ASPECT:
        # The band is a strip, not a face: the mask carried no shoulder signal,
        # so the percentage fallback landed on hair alone.  Rebuild from figure
        # proportions, centred on the body, so the panel still owns a complete
        # face.  A hair-only strip is what made H3 invent moustaches and ages
        # that the design sheet never showed.
        head_height = max(
            int(subject_height * 0.26),
            min(int(subject_height * 0.40), int(subject_height * 0.34)),
        )
        head_height = max(1, min(head_height, bottom - top))
        head_width = max(1, min(right - left, int(head_height * 1.15)))
        centre_x = (left + right) // 2
        head_box = (
            max(0, centre_x - head_width // 2),
            top,
            min(mask.width, centre_x - head_width // 2 + head_width),
            min(bottom, top + head_height),
        )
    return head_box

def measure_head_coverage(
    source: Path | str,
    frame_width: int,
    frame_height: int,
) -> float | None:
    """Return how much of one source frame the picture's own head can fill.

    The artwork is fit inside the frame the same way Relay receives it (contain,
    never stretch), so the value is the fraction of the V1 plate that a take can
    inherit for the face.  ``None`` means the picture cannot be measured, which
    callers must treat as "leave the original picture alone" rather than zero.
    """

    try:
        frame_width = int(frame_width)
        frame_height = int(frame_height)
        if frame_width <= 0 or frame_height <= 0:
            return None
        with Image.open(str(source)) as image:
            image.load()
            if image.width < 8 or image.height < 8:
                return None
            mask, subject = _segment_mask(image)
            head = estimate_head_box(mask, subject)
            scale = min(
                frame_width / float(image.width),
                frame_height / float(image.height),
            )
    except (OSError, ValueError, ZeroDivisionError, MemoryError):
        return None
    head_width = max(0, head[2] - head[0])
    head_height = max(0, head[3] - head[1])
    if head_width <= 0 or head_height <= 0:
        return None
    return (
        head_width * head_height * scale * scale
        / float(frame_width * frame_height)
    )


def measure_reference_head_metrics(source: Path | str) -> dict | None:
    """Measure a picture's head and subject on the picture's *own* canvas.

    ``measure_head_coverage`` answers "how much of the V1 frame can this
    artwork's face fill", which is the question that decides whether a sheet is
    needed at all.  It cannot answer the next question, which is whether the
    artwork was *already* drawn big enough that a sheet would cost more than it
    buys.  A full-body cut-out whose head is a fifth of its own canvas and whose
    subject fills almost the whole canvas loses head pixels when it is re-laid
    out into panels, and it gains a layout the model keeps reproducing as scene
    content: the black-shirt Project's 252x370 Picture 1 measures 0.2201 head
    share and 0.9626 subject fill on its own canvas, was sent through the
    two-panel sheet (head share 0.5259 of the frame), and every Relay window
    start then rendered the sheet's own border and headless lower panel inside
    the scene.  These two numbers are what separates that asset from the
    Mustache Project's pictures (0.094-0.144 own-canvas head share), whose sheet
    the director graded as perfect.

    Returns ``None`` when the artwork cannot be segmented, which every caller
    must treat as "leave the original picture alone" rather than zero.
    """

    try:
        with Image.open(str(source)) as image:
            image.load()
            if image.width < 8 or image.height < 8:
                return None
            mask, subject = _segment_mask(image)
            head = estimate_head_box(mask, subject)
            canvas_width, canvas_height = image.width, image.height
    except (OSError, ValueError, ZeroDivisionError, MemoryError):
        return None
    head_area = max(0, head[2] - head[0]) * max(0, head[3] - head[1])
    subject_area = max(0, subject[2] - subject[0]) * max(
        0, subject[3] - subject[1]
    )
    canvas_area = float(max(1, canvas_width * canvas_height))
    if head_area <= 0 or subject_area <= 0:
        return None
    return {
        "head_canvas_coverage": head_area / canvas_area,
        "subject_fill_share": subject_area / canvas_area,
        "head_box": [int(value) for value in head],
        "subject_box": [int(value) for value in subject],
        "canvas": [int(canvas_width), int(canvas_height)],
    }


# A cast design sheet is drawn as a cut-out: the artist erases the background so
# the figure can be dropped into any plate.  A photograph or a scene plate carries
# an alpha band only as a container accident and leaves it fully opaque.  Measured
# across this workspace's example Projects, every Picture used as a Character Swap
# reference is 46-68 % transparent and every photographic asset is 0.0 % -- the
# one clean separator, because flat-colour statistics do not separate the two (the
# Pink Dress cartoon's top-3 colour share 0.2388 sits inside the photographic
# range 0.135-0.76).  The thresholds below only have to keep that separation while
# tolerating a picture that keeps a thin transparent margin.
ALPHA_CUTOUT_MIN_DIMENSION = 16
ALPHA_CUTOUT_TRANSPARENT_THRESHOLD = 16
ALPHA_CUTOUT_MIN_TRANSPARENT_SHARE = 0.02
ALPHA_CUTOUT_BORDER_RING_SHARE = 0.02
ALPHA_CUTOUT_MIN_BORDER_TRANSPARENT_SHARE = 0.50
# A cut-out is only useful as appearance reference when it still carries a figure.
# The two shares above say "the canvas was erased"; this one says "something was
# drawn on it".  Without it, a fully erased canvas -- the residue of a failed
# import -- reads as design artwork and the sheet would magnify nothing.
ALPHA_CUTOUT_MIN_OPAQUE_SHARE = 0.02


def is_alpha_cutout(source: Path | str) -> bool:
    """Return whether the picture is a background-free cut-out.

    Cheap and deterministic: it reads the alpha histogram, never the pixels one by
    one, so it can run inside Job compilation.  A picture counts as a cut-out when
    it has a real alpha band, at least ``ALPHA_CUTOUT_MIN_TRANSPARENT_SHARE`` of its
    canvas is transparent, and a thin ring along its outer edge is at least half
    transparent -- the ring is what stops a photograph with one clipped corner from
    reading as artwork.

    ``False`` is returned for anything that cannot be probed (no alpha, unreadable,
    degenerate), which callers must treat as "no image-side evidence" rather than
    as proof of a photograph.

    Only modes that carry a real alpha band qualify, so a palette PNG whose
    ``transparency`` metadata never became an ``A`` band also answers ``False``;
    every design sheet produced in this pipeline is RGBA, which is acceptable.
    """

    try:
        with Image.open(str(source)) as image:
            image.load()
            if (
                image.width < ALPHA_CUTOUT_MIN_DIMENSION
                or image.height < ALPHA_CUTOUT_MIN_DIMENSION
            ):
                return False
            if "A" not in image.getbands():
                return False
            alpha = image.getchannel("A")
            histogram = alpha.histogram()
            # The crop geometry is needed after the context manager closes, so the
            # canvas size is captured while the image is still open.
            image_width, image_height = image.width, image.height
    except (OSError, ValueError, IndexError, KeyError, MemoryError):
        return False

    def _transparent_share(values: list[int]) -> float | None:
        total = float(sum(values))
        if total <= 0.0:
            return None
        return sum(values[: ALPHA_CUTOUT_TRANSPARENT_THRESHOLD + 1]) / total

    def _opaque_share(values: list[int]) -> float | None:
        total = float(sum(values))
        if total <= 0.0:
            return None
        return sum(values[ALPHA_CUTOUT_TRANSPARENT_THRESHOLD + 1:]) / total

    whole = _transparent_share(list(histogram))
    if whole is None or whole < ALPHA_CUTOUT_MIN_TRANSPARENT_SHARE:
        return False
    drawn = _opaque_share(list(histogram))
    if drawn is None or drawn < ALPHA_CUTOUT_MIN_OPAQUE_SHARE:
        return False

    ring_thickness = max(
        1,
        int(
            round(
                min(image_width, image_height) * ALPHA_CUTOUT_BORDER_RING_SHARE
            )
        ),
    )
    try:
        strips = [
            (0, 0, image_width, ring_thickness),
            (0, image_height - ring_thickness, image_width, image_height),
            (0, 0, ring_thickness, image_height),
            (image_width - ring_thickness, 0, image_width, image_height),
        ]
        ring_values = [0] * 256
        for strip in strips:
            for index, count in enumerate(alpha.crop(strip).histogram()):
                ring_values[index] += count
    except (OSError, ValueError, IndexError, KeyError, MemoryError):
        return False
    border = _transparent_share(ring_values)
    if border is None:
        return False
    return border >= ALPHA_CUTOUT_MIN_BORDER_TRANSPARENT_SHARE


def _figure_reveal_stats(band_frames: list[list[list[int]]]) -> dict:
    """Return the lowest moving row inside one vertical band of frames.

    ``band_frames`` is ``[frame][row][column]`` gray values, all frames the same
    shape.  Background is reconstructed per pixel as the temporal median, which
    makes a camera-static Shot trivial: whatever never moves is not the subject,
    whatever moves on enough rows to be a body column is.  A row counts as
    subject-bearing when at least ``max(FIGURE_REVEAL_MIN_ROW_PIXELS,
    FIGURE_REVEAL_MIN_ROW_SHARE * band width)`` pixels deviate from that median
    by more than ``FIGURE_REVEAL_DIFF_THRESHOLD``, and the answer is the lowest
    such row per frame, medianaed across frames so one flapping bystander in one
    sampled frame cannot drag it to the floor.

    Two depths come back rather than one, because they answer different questions
    and the plate the black-shirt Project shipped proves why: the *median* depth
    is the stable reading a grader can compare across takes, while the *deepest*
    depth is the evidence that the figure is cut at all.  A cosplayer framed
    knees-up stands with still legs and a moving upper body, so only two of the
    six sampled frames put moving pixels in the last row (median 0.944 of the
    frame, deepest 1.000) -- a median-only rule would have called that half-body
    shot "not cut" and the crop lock would have stayed silent exactly as it did
    before this probe existed.

    Pure Python over plain lists so the gate can be unit-tested without ffmpeg or
    a video file.
    """

    frame_count = len(band_frames)
    row_count = len(band_frames[0]) if frame_count else 0
    band_width = len(band_frames[0][0]) if frame_count and row_count else 0
    if frame_count < FIGURE_REVEAL_MIN_FRAMES or row_count <= 0 or band_width <= 0:
        return {
            "bottom_row": -1,
            "deepest_row": -1,
            "bottom_rows": [],
            "qualifying_row_share": [],
            "row_threshold": 0.0,
            "band_width": band_width,
        }
    background = [
        [
            int(statistics.median(
                band_frames[frame][row][column] for frame in range(frame_count)
            ))
            for column in range(band_width)
        ]
        for row in range(row_count)
    ]
    row_threshold = max(
        float(FIGURE_REVEAL_MIN_ROW_PIXELS),
        FIGURE_REVEAL_MIN_ROW_SHARE * float(band_width),
    )
    bottoms: list[int] = []
    shares: list[float] = []
    for frame in range(frame_count):
        lowest = -1
        qualifying = 0
        for row in range(row_count):
            moved = 0
            for column in range(band_width):
                if (
                    abs(band_frames[frame][row][column] - background[row][column])
                    > FIGURE_REVEAL_DIFF_THRESHOLD
                ):
                    moved += 1
            if moved >= row_threshold:
                qualifying += 1
                lowest = row
        bottoms.append(lowest)
        shares.append(round(qualifying / float(row_count), 6))
    scored = [row for row in bottoms if row >= 0]
    return {
        "bottom_row": (
            int(statistics.median(scored)) if scored else -1
        ),
        "deepest_row": max(scored) if scored else -1,
        "bottom_rows": [int(row) for row in bottoms],
        "qualifying_row_share": shares,
        "row_threshold": row_threshold,
        "band_width": band_width,
    }


def measure_source_figure_reveal(
    ffmpeg: Path | str | None,
    video_path: Path | str,
    role_box: list[float] | tuple[float, float, float, float] | None,
    *,
    frame_width: int,
    frame_height: int,
    sample_count: int = FIGURE_REVEAL_SAMPLE_COUNT,
) -> dict | None:
    """Return how far down the frame the tracked figure actually reaches.

    ``role_box`` is the tracked performer's normalized ``[x1, y1, x2, y2]``; only
    its middle is read, because that is where a torso is guaranteed to be and the
    frame's own rows decide whether anything below it is background.  The clip is
    decoded whole to ``FIGURE_REVEAL_PROBE_WIDTH`` in gray (the same cheap route
    the worker uses for SAM mask statistics), sampled evenly, and the moving
    subject's lowest row is measured inside that narrow band.

    ``reaches_frame_bottom`` is the answer the crop lock needs: ``True`` when the
    figure is cut off by the frame, ``False`` when the frame shows the figure's
    end with background under it.  ``None`` means "not measurable" -- no ffmpeg,
    no subject evidence, a box too narrow to read -- and a ``global_motion``
    status reports the same way, because a plate whose whole frame moves has no
    readable background at all.  Every caller must treat all of those exactly like
    ``False``, which is today's shipped behaviour.
    """

    try:
        ffmpeg_path = Path(ffmpeg) if ffmpeg else None
        clip = Path(video_path)
        frame_width = int(frame_width)
        frame_height = int(frame_height)
        left, top, right, bottom = [float(value) for value in (role_box or [])]
        if (
            ffmpeg_path is None
            or not clip.is_file()
            or frame_width <= 0
            or frame_height <= 0
        ):
            return None
    except (TypeError, ValueError, OSError):
        return None
    if len(list(role_box or [])) != 4 or right <= left or bottom <= top:
        return None

    probe_width = max(8, int(FIGURE_REVEAL_PROBE_WIDTH))
    probe_height = max(
        8, (int(round(probe_width * frame_height / float(frame_width))) // 2) * 2
    )
    try:
        completed = subprocess.run(
            [
                str(ffmpeg_path), "-hide_banner", "-loglevel", "error",
                "-i", str(clip),
                "-vf",
                f"scale={probe_width}:{probe_height},format=gray",
                "-an", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode:
        return None

    from PIL import Image

    frame_bytes = probe_width * probe_height
    payload = completed.stdout
    if frame_bytes <= 0 or len(payload) < frame_bytes:
        return None
    decoded: list[Image.Image] = []
    for offset in range(0, len(payload) - frame_bytes + 1, frame_bytes):
        try:
            decoded.append(
                Image.frombytes(
                    "L", (probe_width, probe_height), payload[offset:offset + frame_bytes]
                )
            )
        except ValueError:
            break
    frame_total = len(decoded)
    if frame_total < FIGURE_REVEAL_MIN_FRAMES:
        return {"status": "insufficient_frames", "sample_count": frame_total}

    # Sample evenly across the whole Shot rather than trusting one moment: a
    # performer who steps back mid-Shot is still framed by the same crop.
    wanted = max(FIGURE_REVEAL_MIN_FRAMES, min(int(sample_count), FIGURE_REVEAL_SAMPLE_COUNT * 4))
    wanted = min(wanted, frame_total)
    if frame_total <= wanted:
        picks = list(range(frame_total))
    else:
        picks = sorted(
            {min(frame_total - 1, max(0, round(index * (frame_total - 1) / float(wanted - 1))))
             for index in range(wanted)}
        )

    box_width = right - left
    inset = max(0.0, min(0.45, float(FIGURE_REVEAL_BAND_INSET)))
    band_left = left + box_width * inset
    band_right = right - box_width * inset
    band_x1 = max(0, int(math.floor(band_left * probe_width)))
    band_x2 = min(probe_width, int(math.ceil(band_right * probe_width)))
    if band_x2 - band_x1 < FIGURE_REVEAL_MIN_BAND_PIXELS:
        # A box this narrow cannot carry a 30 %-of-rows rule; widen the band to
        # the smallest readable slice centred on it instead of reading noise.
        centre = (left + right) / 2.0 * probe_width
        band_x1 = max(0, int(math.floor(centre - FIGURE_REVEAL_MIN_BAND_PIXELS / 2.0)))
        band_x2 = min(probe_width, band_x1 + FIGURE_REVEAL_MIN_BAND_PIXELS)
        band_x1 = max(0, band_x2 - FIGURE_REVEAL_MIN_BAND_PIXELS)
    if band_x2 - band_x1 <= 0:
        return None

    band_frames: list[list[list[int]]] = []
    for index in picks:
        frame = decoded[index]
        if frame.mode != "L":
            frame = frame.convert("L")
        band = frame.crop((band_x1, 0, band_x2, probe_height))
        band_frames.append(
            [
                list(band.getdata())[row * (band_x2 - band_x1):(row + 1) * (band_x2 - band_x1)]
                for row in range(probe_height)
            ]
        )
    stats = _figure_reveal_stats(band_frames)
    observed = {
        "sample_count": len(picks),
        "probe_size": [probe_width, probe_height],
        "band_pixels": [band_x1, band_x2],
        "qualifying_row_share": stats["qualifying_row_share"],
    }
    if stats["deepest_row"] < 0:
        return {"status": "no_subject_motion", **observed}
    row_shares = sorted(stats["qualifying_row_share"])
    median_row_share = statistics.median(row_shares)
    observed["median_row_share"] = round(float(median_row_share), 6)
    if median_row_share >= FIGURE_REVEAL_GLOBAL_MOTION_SHARE:
        return {"status": "global_motion", **observed}
    deepest_normalized = (stats["deepest_row"] + 1) / float(probe_height)
    median_normalized = (stats["bottom_row"] + 1) / float(probe_height)
    # Row semantics, not a fraction: a 0.985 share on a 144-row probe rounds to
    # "the figure touches the bottom edge" even when the last visible row sits a
    # third of a row above it, which is exactly what the shrunk-box negative
    # control measured.  Ask for the last row itself, plus a tolerance.
    bottom_row_floor = probe_height - 1 - FIGURE_REVEAL_BOTTOM_TOLERANCE_ROWS
    bottom_frames = sum(
        1 for row in stats["bottom_rows"] if row >= bottom_row_floor
    )
    return {
        "status": "measured",
        "figure_bottom_normalized": round(deepest_normalized, 6),
        "figure_bottom_median_normalized": round(median_normalized, 6),
        "reaches_frame_bottom": bool(
            stats["deepest_row"] >= bottom_row_floor
            and bottom_frames >= min(FIGURE_REVEAL_MIN_BOTTOM_FRAMES, len(picks))
        ),
        "bottom_evidence_frames": int(bottom_frames),
        **observed,
        "figure_bottom_rows": stats["bottom_rows"],
    }


def compose_wardrobe_signature(
    source: Path | str,
    destination: Path | str,
) -> dict | None:
    """Flatten the artwork's garment-only region into one small QC reference.

    Whole-body replacement has never had a hard gate.  Every identity gate in
    Relay QC looks at the face region, so a take that swaps only the head and
    leaves the source actor's cosplay on the body scores as a pass (rounds
    25/30/32/33 all graded "head OK, clothes still V1"), and the colour cue used
    for target likeness is measured against the *whole* picture, where the head
    occupies a fifth of the pixels and the surviving source wardrobe barely
    moves the histogram.  The fix needs a second reference: the artwork below
    its own head box, i.e. tunic, shorts, leg-warmers and shoes and nothing
    else.

    The region is flattened onto the picture's own canvas colour rather than
    saved with alpha, because the QC decoder reads ``rgb24`` and would otherwise
    score the transparent area as black.  Returns ``None`` when the artwork has
    no measurable body region (a head-and-shoulders portrait, an unsegmentable
    photograph), which callers must treat as "no wardrobe gate for this Shot".
    """

    source = Path(source)
    try:
        with Image.open(str(source)) as image:
            image.load()
            canvas_width, canvas_height = image.width, image.height
            if canvas_width < 16 or canvas_height < 16:
                return None
            mask, subject = _segment_mask(image)
            head = estimate_head_box(mask, subject)
            canvas = neutral_canvas_color(image)
            rgba = image.convert("RGBA")
    except (OSError, ValueError, ZeroDivisionError, MemoryError):
        return None
    left = max(0, int(subject[0]))
    right = min(canvas_width, int(subject[2]))
    # +2 px keeps the chin/jaw row out of the garment crop without cutting the
    # collar: the head box bottom is a mask row, not a clothing edge.
    top = min(canvas_height - 2, int(head[3]) + 2)
    bottom = min(canvas_height, int(subject[3]))
    width, height = right - left, bottom - top
    if (
        width < max(8, int(canvas_width * 0.08))
        or height < max(8, int(canvas_height * 0.08))
    ):
        return None
    fingerprint = source_fingerprint(source)
    try:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        output = destination / (
            f"{source.stem}_wardrobe_{fingerprint[:12]}_v1.png"
        )
    except OSError:
        return None
    reason = "composed"
    if output.is_file() and output.stat().st_size > 0:
        # The fingerprint embeds path, size and mtime, so an existing file with
        # this name is already the render of this exact artwork.
        reason = "cached"
    else:
        try:
            crop = rgba.crop((left, top, right, bottom))
            flat = Image.new("RGBA", crop.size, canvas + (255,))
            flat.alpha_composite(crop)
            flat.convert("RGB").save(str(output), format="PNG")
        except (OSError, ValueError, MemoryError):
            return None
    return {
        "path": output,
        "bbox_normalized": [
            round(left / float(canvas_width), 6),
            round(top / float(canvas_height), 6),
            round(right / float(canvas_width), 6),
            round(bottom / float(canvas_height), 6),
        ],
        "head_box": [int(value) for value in head],
        "subject_box": [int(value) for value in subject],
        "canvas": [int(canvas_width), int(canvas_height)],
        "reason": reason,
    }


def neutral_canvas_color(image: Image.Image) -> tuple[int, int, int]:
    """Pick a canvas colour that matches the artwork's own paper background."""

    rgba = image.convert("RGBA")
    if rgba.getchannel("A").getextrema()[0] < 250:
        return (246, 246, 246)
    return _border_colour(rgba.convert("RGB"))


def _border_colour(rgb: Image.Image) -> tuple[int, int, int]:
    """Average colour of the outermost pixel ring -- the artwork's own paper.

    The padding colour used to be blended with an autocontrasted mean of the
    *whole* picture, which turned a white paper cast into a grey-beige mat.
    Relay then reads that mat as part of the reference, so the sheets picked up
    a colour the artwork never had.  Sampling the border ring and returning it
    verbatim keeps white artwork white and dark artwork dark.
    """

    width, height = rgb.size
    band = max(1, min(width, height) // 32)
    pieces = (
        rgb.crop((0, 0, width, band)),
        rgb.crop((0, max(0, height - band), width, height)),
        rgb.crop((0, 0, band, height)),
        rgb.crop((max(0, width - band), 0, width, height)),
    )
    totals = [0, 0, 0]
    weight = 0
    for piece in pieces:
        if piece.width < 1 or piece.height < 1:
            continue
        pixel = piece.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
        mass = piece.width * piece.height
        for channel in range(3):
            totals[channel] += int(pixel[channel]) * mass
        weight += mass
    if not weight:
        return (255, 255, 255)
    return tuple(int(round(value / weight)) for value in totals)  # type: ignore[return-value]


def _slot_crop(
    slot: str,
    source: Image.Image,
    subject: tuple[int, int, int, int],
    head: tuple[int, int, int, int],
    outfit_view: str | None = None,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    left, top, right, bottom = subject
    head_left, head_top, head_right, head_bottom = head
    if slot == "head":
        box = head
    elif slot == "outfit":
        neck = head_bottom
        box = (left, neck, right, bottom)
        if box[3] - box[1] < 8:
            box = (left, top, right, bottom)
        elif outfit_view in OUTFIT_VIEW_SHARES:
            # Framing-aware wardrobe: a close-up Shot never sees the shoes, so
            # the shoes must not be in the reference either.
            share = float(OUTFIT_VIEW_SHARES[outfit_view])
            visible = neck + int(round(share * max(0, bottom - neck)))
            if visible - neck >= 8:
                box = (left, neck, right, visible)
    elif slot == "detail":
        neck = head_bottom
        mid_y = (head_bottom + bottom) // 2
        half = max(8, min((right - left), (bottom - neck if bottom > neck else bottom - top)) // 2)
        box = (
            max(left, (left + right) // 2 - half),
            max(top, mid_y - half),
            min(right, (left + right) // 2 + half),
            min(bottom, mid_y + half),
        )
    else:  # body / full
        box = (0, 0, source.width, source.height) if slot == "full" else subject
    box = (
        max(0, int(box[0])),
        max(0, int(box[1])),
        min(source.width, int(box[2])),
        min(source.height, int(box[3])),
    )
    if box[2] - box[0] < 4 or box[3] - box[1] < 4:
        box = (0, 0, source.width, source.height)
    crop = source.crop(box)
    if box[2] - box[0] < 4 or box[3] - box[1] < 4:
        crop = source
    return crop, box


def _column_artwork_scores(
    mask: Image.Image,
    box: tuple[int, int, int, int],
) -> list[float]:
    """Mean opaque coverage of every column inside ``box``, left to right.

    One averaged row is the whole cost table, so it is computed in C:
    ``reduce`` takes reduction *factors*, so collapsing the rows onto one line is
    ``reduce((1, height))`` -- one value per column.
    """

    left = max(0, int(box[0]))
    top = max(0, int(box[1]))
    right = min(mask.width, int(box[2]))
    bottom = min(mask.height, int(box[3]))
    if right - left < 2 or bottom - top < 2:
        return []
    strip = mask.convert("L").crop((left, top, right, bottom))
    try:
        reduced = strip.reduce((1, strip.height))
    except (OSError, ValueError):  # pragma: no cover - imaging guard
        return []
    return [float(value) for value in reduced.getdata()]


def _balanced_growth_split(
    mask: Image.Image,
    span: tuple[int, int, int, int],
    left: int,
    right: int,
    extra: int,
) -> int:
    """Split ``extra`` outward columns so the face stays centred in its panel.

    ``span`` is the growth window as a ``(left, top, right, bottom)`` box; only
    its horizontal edges matter here, and its full box goes to the coverage
    table below.

    Returns how many of those columns come off the left.  Centring is the
    property that makes the panel read as a face, so the balanced split is the
    default and the frame only overrides it when one side has run out of room.
    An odd ``extra`` leaves two equally balanced splits; the column coverage
    table breaks that tie towards the side that carries the character, because
    artwork the Shot can repaint is worth more to the panel than blank paper.
    """

    span_left, span_right = int(span[0]), int(span[2])
    room_left = max(0, left - span_left)
    room_right = max(0, span_right - right)
    half = max(0, extra // 2)
    splits = [half] if extra % 2 == 0 else [extra - half, half]
    feasible = [
        take_left
        for take_left in splits
        if take_left <= room_left and (extra - take_left) <= room_right
    ]
    if not feasible:
        return min(extra, room_left)
    if len(feasible) == 1:
        return feasible[0]
    scores = _column_artwork_scores(mask, span)
    if not scores:
        return feasible[0]
    index_left = left - span_left
    index_right = right - span_left

    def _artwork_gained(take_left: int) -> float:
        take_right = extra - take_left
        return float(
            sum(scores[index_left - take_left : index_left])
            + sum(scores[index_right : index_right + take_right])
        )

    return max(feasible, key=_artwork_gained)


def _grow_head_crop_to_cell(
    box: tuple[int, int, int, int],
    cell: tuple[int, int, int, int],
    source: Image.Image,
    subject: tuple[int, int, int, int],
    mask: Image.Image | None = None,
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Extend the head crop with real artwork until it can fill its cell.

    ``_fit_into_cell`` never distorts, so a narrow skull crop loses its cell's
    horizontal slack and the face then shrinks twice -- once into the panel and
    again when Relay normalises the sheet into the V1 frame.  Growing the box
    over the surrounding artwork recovers that slack honestly: every extra pixel
    comes out of the cast picture, so the panel gains the neck, shoulders and
    collar the Shot has to repaint instead of empty canvas.

    Growth stays inside the segmented subject so the panel never gains a border
    of invented background, and the chin row is never moved, because everything
    below it is wardrobe rather than headroom.

    Sideways growth is split as evenly as the frame allows so the face stays in
    the middle of its panel; the frame only overrides that balance when one
    side has run out of room.  An odd leftover column then goes to the side
    that carries artwork, because a limb that engine v7 deliberately kept out
    of the head run is worth less to Relay than the blank paper beside it.
    """

    left, top, right, bottom = (int(value) for value in box)
    bounds = (
        max(0, min(int(subject[0]), left)),
        max(0, min(int(subject[1]), top)),
        min(source.width, max(int(subject[2]), right)),
        min(source.height, max(int(subject[3]), bottom)),
    )
    # Downward growth stops at the figure's own feet, but sideways growth may
    # cross the paper around it: the sheet canvas is that same neutral colour,
    # so padding left of a cut-out is not invented background -- it is the
    # cheapest thing the panel can swallow.  Clamping sideways growth to the
    # subject bbox instead pushed the whole face panel off centre, because the
    # waving cast is the only reason the right side looked expensive.
    x_bounds = (0, source.width)
    width = max(1, right - left)
    height = max(1, bottom - top)
    cell_w = max(1, int(cell[2]) - int(cell[0]))
    cell_h = max(1, int(cell[3]) - int(cell[1]))
    cell_aspect = float(cell_w) / float(max(1, cell_h))
    crop_aspect = float(width) / float(height)
    if crop_aspect < cell_aspect:
        target_w = min(
            int(round(width * HEAD_PANEL_MAX_GROW)),
            int(round(height * cell_aspect)),
            x_bounds[1] - x_bounds[0],
        )
        extra = min(target_w - width, (left - x_bounds[0]) + (x_bounds[1] - right))
        if extra > 0:
            take_left = (
                extra // 2
                if mask is None
                else _balanced_growth_split(
                    mask, (x_bounds[0], top, x_bounds[1], bottom), left, right, extra
                )
            )
            left -= take_left
            right += extra - take_left
    elif crop_aspect > cell_aspect:
        target_h = min(
            int(round(height * HEAD_PANEL_MAX_GROW)),
            int(round(width / max(cell_aspect, 1e-06))),
            bounds[3] - bounds[1],
        )
        if target_h > height:
            below = int(round((target_h - height) * HEAD_PANEL_DOWNWARD_GROW_SHARE))
            new_bottom = min(bounds[3], bottom + below)
            new_top = max(bounds[1], top - max(0, target_h - (new_bottom - top)))
            new_bottom = min(bounds[3], new_top + target_h)
            top, bottom = new_top, new_bottom
    grown = (
        max(0, left),
        max(0, top),
        min(source.width, right),
        min(source.height, bottom),
    )
    return source.crop(grown), grown


def _fit_into_cell(
    crop: Image.Image,
    cell: tuple[int, int, int, int],
    *,
    sharpen: bool,
) -> tuple[Image.Image, tuple[int, int]]:
    """Contain-fit ``crop`` inside ``cell`` without distortion; return offsets."""

    cell_left, cell_top, cell_right, cell_bottom = cell
    cell_w = max(1, cell_right - cell_left)
    cell_h = max(1, cell_bottom - cell_top)
    crop_w, crop_h = crop.size
    scale = min(cell_w / float(crop_w), cell_h / float(crop_h))
    target_w = max(1, int(round(crop_w * scale)))
    target_h = max(1, int(round(crop_h * scale)))
    resample = Image.Resampling.LANCZOS
    if scale > 1.0:
        resized = crop.resize((target_w, target_h), resample)
        if sharpen and scale >= 1.5:
            resized = resized.filter(
                ImageFilter.UnsharpMask(
                    radius=min(3.2, max(1.4, 0.34 * scale)),
                    percent=120,
                    threshold=3,
                )
            )
    else:
        resized = crop.resize((target_w, target_h), resample)
    offset_x = cell_left + (cell_w - target_w) // 2
    offset_y = cell_top + (cell_h - target_h) // 2
    return resized, (offset_x, offset_y)


def suppress_burned_in_overlays(
    image: Image.Image,
) -> tuple[Image.Image, dict[str, object]]:
    """Paint out burned-in white captions, titles and UI in the outer bands.

    Character Swap reads Picture 1 as the sole authority for the character's
    design, and an Identity Sheet panel is a crop of that same picture, so a
    caption or a like/comment row baked into the artwork is read as *design* and
    then republished in every panel.  Returns ``(image, stats)`` and never
    raises: a sheet must still be produced when the pass declines to act.

    The source comes back untouched, with a ``skipped_reason``, when the artwork
    is transparent (a cut-out cast has no background to caption over), when no
    interior near-white band exists, or when the repair would have exceeded
    ``OVERLAY_MAX_REPAIRED_FRACTION`` of the picture.
    """

    stats: dict[str, object] = {
        "applied": False,
        "pixels": 0,
        "fraction": 0.0,
        "skipped_reason": "",
    }
    rgba = image.convert("RGBA")
    if rgba.getchannel("A").getextrema()[0] < 250:
        stats["skipped_reason"] = "source artwork is a transparent cut-out"
        return image, stats
    work = rgba.convert("RGB")
    width, height = work.size
    pixels = work.load()
    mask = Image.new("L", (width, height), 0)
    mask_pixels = mask.load()

    def near_white() -> Image.Image:
        # Three channels must *all* be near-white.  A single bright channel is
        # saturated colour (a red hat top, a blue shirt), not text.
        channels = [
            work.getchannel(name).point(
                lambda value, floor=OVERLAY_WHITE_MIN: 255 if value >= floor else 0
            )
            for name in ("R", "G", "B")
        ]
        return ImageChops.multiply(
            ImageChops.multiply(channels[0], channels[1]), channels[2]
        )

    def median_of(values: list[int]) -> int:
        if not values:
            return 0
        ordered = sorted(values)
        return ordered[len(ordered) // 2]

    def interior_runs(line: bytes, axis_length: int) -> list[tuple[int, int]]:
        found: list[tuple[int, int]] = []
        start = None
        for index, value in enumerate(line):
            if value and start is None:
                start = index
            elif not value and start is not None:
                found.append((start, index))
                start = None
        if start is not None:
            found.append((start, len(line)))
        return [
            (start, stop)
            for start, stop in found
            if OVERLAY_RUN_MIN_PX
            <= stop - start
            <= OVERLAY_RUN_MAX_FRACTION * axis_length
            and start > 0
            and stop < len(line)
        ]

    def fill_rows(white_rows: list[bytes], lo: int, hi: int) -> int:
        changed = 0
        for y in range(lo, hi):
            line = white_rows[y]
            for start, stop in interior_runs(line, width):
                colour = tuple(
                    median_of(
                        [
                            pixels[x, y][channel]
                            for x in chain(range(start), range(stop, width))
                            if not line[x]
                        ]
                    )
                    for channel in range(3)
                )
                for x in range(start, stop):
                    if mask_pixels[x, y] == 0:
                        changed += 1
                    mask_pixels[x, y] = 255
                    pixels[x, y] = colour
        return changed

    def fill_columns(white: Image.Image, lo: int, hi: int) -> int:
        changed = 0
        for x in range(lo, hi):
            line = white.crop((x, 0, x + 1, height)).tobytes()
            for start, stop in interior_runs(line, height):
                colour = tuple(
                    median_of(
                        [
                            pixels[x, y][channel]
                            for y in chain(range(start), range(stop, height))
                            if not line[y]
                        ]
                    )
                    for channel in range(3)
                )
                for y in range(start, stop):
                    if mask_pixels[x, y] == 0:
                        changed += 1
                    mask_pixels[x, y] = 255
                    pixels[x, y] = colour
        return changed

    def dilate_halo_and_refill(round_index: int) -> None:
        # The median fill leaves a bright fringe wherever an anti-aliased glyph
        # edge was left outside the run.  Growing the mask swallows that halo,
        # and the grown region is re-filled from the row's own unmasked pixels.
        nonlocal mask, mask_pixels
        radius = OVERLAY_HALO_DILATIONS[
            min(round_index, len(OVERLAY_HALO_DILATIONS) - 1)
        ]
        mask = mask.filter(ImageFilter.MaxFilter(radius))
        mask_pixels = mask.load()
        for lo, hi in row_bands:
            for y in range(lo, hi):
                line = mask.crop((0, y, width, y + 1)).tobytes()
                if not any(line):
                    continue
                colour = tuple(
                    median_of(
                        [
                            pixels[x, y][channel]
                            for x in range(width)
                            if not line[x]
                        ]
                    )
                    for channel in range(3)
                )
                for x in range(width):
                    if line[x]:
                        pixels[x, y] = colour

    row_bands = (
        (0, int(height * OVERLAY_BAND_ROWS["top"])),
        (height - int(height * OVERLAY_BAND_ROWS["bottom"]), height),
    )
    column_bands = (
        (0, int(width * OVERLAY_BAND_COLUMNS["left"])),
        (width - int(width * OVERLAY_BAND_COLUMNS["right"]), width),
    )
    repaired = 0
    for round_index in range(OVERLAY_ROUNDS):
        # Round 2 re-samples: the first pass fills a run with its row median,
        # which makes the glyph's own brighter anti-aliasing the next run.
        white = near_white()
        white_rows = [
            white.crop((0, y, width, y + 1)).tobytes() for y in range(height)
        ]
        for lo, hi in row_bands:
            repaired += fill_rows(white_rows, lo, hi)
        for lo, hi in column_bands:
            repaired += fill_columns(white, lo, hi)
        if repaired > OVERLAY_MAX_REPAIRED_FRACTION * width * height:
            stats["skipped_reason"] = (
                f"overlay hypothesis rejected: {repaired / float(width * height):.1%} "
                "of the picture is near-white, so the artwork itself is white"
            )
            return image, stats
        if repaired:
            dilate_halo_and_refill(round_index)
    if not repaired:
        stats["skipped_reason"] = "no interior near-white overlay band detected"
        return image, stats
    # The filled runs are flat medians, which reads as a smudge at the seams.
    # Blurring only the masked region keeps the character's own edges sharp.
    blended = Image.composite(
        work.filter(ImageFilter.GaussianBlur(radius=OVERLAY_BLEND_BLUR_RADIUS)),
        work,
        mask,
    )
    blended.putalpha(rgba.getchannel("A"))
    stats["applied"] = True
    stats["pixels"] = int(repaired)
    stats["fraction"] = round(repaired / float(width * height), 6)
    return blended, stats


def _view_artwork(
    path: Path,
) -> tuple[Image.Image, Image.Image, tuple[int, int, int, int], tuple[int, int, int, int]] | None:
    """Segment one supplied rear / side picture the way the front is segmented.

    Returns ``None`` rather than raising: a picture that will not decode or that
    has no segmentable figure must degrade to the front artwork, never take the
    whole sheet down with it.
    """

    try:
        with Image.open(path) as handle:
            image = handle.convert("RGBA")
        if image.width < 32 or image.height < 32:
            return None
        image, _overlay_stats = suppress_burned_in_overlays(image)
        mask, subject = _segment_mask(image)
        subject = (
            max(0, int(subject[0])),
            max(0, int(subject[1])),
            min(image.width, int(subject[2])),
            min(image.height, int(subject[3])),
        )
        if subject[2] - subject[0] < 16 or subject[3] - subject[1] < 16:
            return None
        head = estimate_head_box(mask, subject)
    except Exception:  # pragma: no cover - defensive imaging guard
        return None
    return image, mask, subject, head


def collect_view_sources(
    preset: int,
    view_sources: dict | None,
) -> dict[str, Path]:
    """Keep only the view pictures the selected layout can actually use.

    Round 69 item 7.  A rear drawing is not a global reference upgrade: preset 0
    has no rear panel, so passing one there must not change anything.  The layout
    decides which views it tags, and only those tags read the mapping.
    """

    layout = SHEET_PRESETS.get(int(preset)) or SHEET_PRESETS[DEFAULT_SHEET_PRESET]
    wanted = {
        str(getattr(panel, "view", "") or "").strip().lower()
        for panel in layout.panels
    } - {""}
    collected: dict[str, Path] = {}
    if not wanted or not view_sources:
        return collected
    for key, value in dict(view_sources).items():
        name = str(key or "").strip().lower()
        if name not in wanted or not value:
            continue
        candidate = Path(str(value))
        if candidate.is_file():
            collected[name] = candidate
    return collected


def compose_identity_sheet(
    source: Path | str,
    output_dir: Path | str,
    *,
    preset: int = DEFAULT_SHEET_PRESET,
    max_megapixels: float = DEFAULT_MAX_MEGAPIXELS,
    force: bool = False,
    target_aspect: tuple[int, int] | float | None = None,
    outfit_view: str | None = None,
    view_sources: dict | None = None,
) -> IdentitySheetResult:
    """Compose one deterministic identity sheet from one P Picture.

    Returns a result object rather than raising: Character Swap must keep
    working with the raw picture whenever composition is unavailable.

    ``target_aspect`` is the V1 frame geometry (width, height).  When it is
    supplied the canvas matches the source Shot, which is the aspect Relay will
    normalise the reference to; otherwise the preset's upstream aspect is used.

    ``outfit_view`` ("close_up" / "medium" / "full") states how far down the
    figure the wardrobe panel keeps authority: ``close_up`` and ``medium`` cut
    it at the line the Shot actually frames, and ``full`` keeps the complete
    neck-down figure while still trading canvas from the wardrobe to the face.
    An unknown or empty view keeps the panel uncut *and* un-re-weighted.

    ``view_sources`` ("rear" / "side" -> picture path) supplies real artwork for
    the body views a layout tags (round 69 item 7, preset 9).  Views the layout
    does not tag are ignored, an unreadable picture falls back to the front
    artwork, and either fallback is recorded in the sidecar rather than being
    presented as an angle the artwork never showed.
    """

    source = Path(str(source))
    output_dir = Path(str(output_dir))
    preset_index = int(preset)
    if preset_index not in SHEET_PRESETS:
        preset_index = DEFAULT_SHEET_PRESET
    layout = SHEET_PRESETS[preset_index]
    # Relay feeds the reference through ``MiniMaxH3ReferenceToVideo`` with
    # ``ref_image_size = match``, i.e. it normalises the sheet into the V1 frame
    # before the VAE sees it.  Composing at the V1 aspect therefore keeps every
    # panel at full scale; composing at the upstream 3:4/21:9 aspects would let
    # that normalisation shrink the face a second time.
    canvas_aspect = _canvas_ratio(target_aspect, layout)
    if not source.is_file():
        return _failure("source picture is missing", source)
    fingerprint = source_fingerprint(source)
    if not fingerprint:
        return _failure("source picture cannot be stat-ed", source)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return _failure(f"cannot create identity sheet folder: {error}", source)

    stem = "".join(
        character if character.isalnum() or character in "._-" else "_"
        for character in source.stem
    )[:64] or "reference"
    # The aspect is part of the cache key: a portrait V1 sheet and a landscape
    # V1 sheet for the same picture are different references, not one of them.
    aspect_tag = f"a{int(round(canvas_aspect * 100)):04d}"
    view = str(outfit_view or "").strip().lower()
    if view not in OUTFIT_VIEW_SHARES:
        view = ""
    # Same story for the framing: a chest-only wardrobe panel and a whole-figure
    # wardrobe panel are two different references for one picture.
    view_tag = f"_{OUTFIT_VIEW_TAGS[view]}" if view else ""
    # A cropped wardrobe panel also stops deserving its designed slice of the
    # canvas, so the layout is re-weighted before anything is scored or placed.
    layout = _view_adjusted_layout(layout, view)
    # Round 69 item 7: which real view artwork this sheet is allowed to read.
    view_paths = collect_view_sources(preset_index, view_sources)
    view_fingerprints = {
        name: (source_fingerprint(path) or "unreadable")
        for name, path in sorted(view_paths.items())
    }
    # The view artwork is part of the reference's identity, so it belongs in the
    # file name as well as the cache key: a new rear drawing has to produce a new
    # sheet path, or a finished Segment would keep serving the take it rendered
    # from the previous one.
    views_tag = "".join(
        f"_{name[:2]}{view_fingerprints[name][:6]}"
        for name in sorted(view_fingerprints)
    )
    sheet_path = output_dir / f"{stem}_identitysheet{preset_index:02d}{view_tag}{views_tag}_{aspect_tag}_v{IDENTITY_SHEET_ENGINE_VERSION}.png"
    head_path = output_dir / f"{stem}_identitysheet{preset_index:02d}{view_tag}{views_tag}_{aspect_tag}_head_v{IDENTITY_SHEET_ENGINE_VERSION}.png"
    body_path = output_dir / f"{stem}_identitysheet{preset_index:02d}{view_tag}{views_tag}_{aspect_tag}_body_v{IDENTITY_SHEET_ENGINE_VERSION}.png"
    sidecar = output_dir / f"{sheet_path.name}{IDENTITY_SHEET_SIDECAR_SUFFIX}"

    def _cached() -> IdentitySheetResult | None:
        if force or not (sheet_path.is_file() and sidecar.is_file()):
            return None
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("source_fingerprint") != fingerprint:
            return None
        if int(payload.get("engine_version") or 0) != IDENTITY_SHEET_ENGINE_VERSION:
            return None
        # ``or -1`` here looked like a missing-field default, but 0 is a real
        # preset (``DEFAULT_SHEET_PRESET``), so every default-layout sheet read as
        # a preset mismatch and was recomposed from scratch on every job.  An
        # absent or non-integer field still fails closed.
        if not isinstance(payload.get("preset"), int) or payload["preset"] != preset_index:
            return None
        if str(payload.get("outfit_view") or "") != view:
            return None
        if abs(float(payload.get("canvas_aspect") or 0.0) - canvas_aspect) > 0.01:
            return None
        # Empty on both sides for presets 0-8, which is why their sheets keep
        # hitting the cache; a real rear / side picture that changed forces a
        # recomposition.
        if dict(payload.get("view_fingerprints") or {}) != view_fingerprints:
            return None
        if not (
            Path(str(payload.get("sheet_path") or "")).is_file()
            and Path(str(payload.get("head_path") or "")).is_file()
        ):
            return None
        panels = [
            PanelRecord(**row) for row in payload.get("panels") or [] if isinstance(row, dict)
        ]
        return IdentitySheetResult(
            ok=True,
            reason="cached",
            sheet_path=str(payload["sheet_path"]),
            head_path=str(payload["head_path"]),
            body_path=str(payload.get("body_path") or ""),
            preset=preset_index,
            preset_label=layout.label,
            outfit_view=view,
            width=int(payload.get("width") or 0),
            height=int(payload.get("height") or 0),
            source_path=str(source.resolve()),
            source_fingerprint=fingerprint,
            canvas_aspect=float(payload.get("canvas_aspect") or canvas_aspect),
            head_coverage=float(payload.get("head_coverage") or 0.0),
            source_head_crop_megapixels=float(
                payload.get("source_head_crop_megapixels")
                or source_head_crop_megapixels(panels)
            ),
            source_megapixels=float(payload.get("source_megapixels") or 0.0),
            dropped_slots=[str(value) for value in payload.get("dropped_slots") or []],
            panels=panels,
            notes=list(payload.get("notes") or []),
            view_fingerprints=dict(view_fingerprints),
        )

    cached = _cached()
    if cached is not None:
        return cached

    try:
        with Image.open(source) as handle:
            image = handle.convert("RGBA")
    except (OSError, ValueError) as error:
        return _failure(f"cannot decode source picture: {error}", source)
    if image.width < 32 or image.height < 32:
        return _failure("source picture is too small for an identity sheet", source)

    # Crop grammar magnifies whatever the artwork actually shows, so dirt in the
    # artwork becomes identity facts in the sheet.  De-contaminate before the
    # segmentation and the crops see anything.
    try:
        image, overlay_stats = suppress_burned_in_overlays(image)
    except Exception as error:  # pragma: no cover - defensive imaging guard
        overlay_stats = {
            "applied": False,
            "pixels": 0,
            "fraction": 0.0,
            "skipped_reason": f"suppression could not run: {error}",
        }

    try:
        mask, subject = _segment_mask(image)
    except Exception as error:  # pragma: no cover - defensive imaging guard
        return _failure(f"cannot segment source picture: {error}", source)
    subject = (
        max(0, subject[0]),
        max(0, subject[1]),
        min(image.width, subject[2]),
        min(image.height, subject[3]),
    )
    if subject[2] - subject[0] < 16 or subject[3] - subject[1] < 16:
        return _failure("segmented subject is too small for an identity sheet", source)
    head = estimate_head_box(mask, subject)

    # Round 69 item 7: the real view artwork, if the director supplied any.  A
    # view that was supplied but will not segment behaves exactly like a view
    # that was never supplied, and says so in the notes.
    view_artworks = {
        name: _view_artwork(path) for name, path in sorted(view_paths.items())
    }
    unusable_views = sorted(
        name for name, artwork in view_artworks.items() if artwork is None
    )
    usable_views = {
        name: artwork
        for name, artwork in view_artworks.items()
        if artwork is not None
    }
    # Which artwork each panel is cut from.  Untagged panels -- every panel of
    # presets 0-8 -- take the front picture, so their crops, their placement and
    # their sidecar rows are unchanged.
    artworks: dict[int, tuple[Image.Image, Image.Image, tuple[int, int, int, int], tuple[int, int, int, int], str]] = {}
    for panel_index, panel in enumerate(layout.panels):
        wanted = str(getattr(panel, "view", "") or "").strip().lower()
        artwork = usable_views.get(wanted) if wanted and wanted != VIEW_FRONT else None
        if artwork is not None:
            artworks[panel_index] = artwork + (VIEW_SOURCE_REFERENCE,)
        else:
            artworks[panel_index] = (image, mask, subject, head, "")

    canvas_w, canvas_h = _canvas_size(canvas_aspect, max_megapixels)
    background = neutral_canvas_color(image)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), background + (255,))
    draw = ImageDraw.Draw(canvas)
    gutter = max(4, int(min(canvas_w, canvas_h) * 0.012))
    crops: dict[int, tuple[Image.Image, tuple[int, int, int, int]]] = {
        index: _slot_crop(
            panel.slot,
            artworks[index][0],
            artworks[index][2],
            artworks[index][3],
            view or None,
        )
        for index, panel in enumerate(layout.panels)
    }
    # The crop aspects are known before the grid is chosen, which is what lets
    # ``_arrangement`` measure both orientations instead of guessing from the
    # declared row/column counts.
    crop_aspects = {
        index: float(crop.width) / float(max(1, crop.height))
        for index, (crop, _box) in crops.items()
    }
    grid, placements = _arrangement(
        layout,
        canvas_w / float(max(1, canvas_h)),
        crop_aspects,
    )
    canvas_area = float(max(1, canvas_w * canvas_h))
    keep: dict[int, bool] = {index: True for index, *_ in placements}
    dropped: list[str] = []
    rects: dict[int, tuple[int, int, int, int]] = {}
    for _attempt in range(3):
        shares = _area_shares(layout, placements, keep)
        rects = _cell_rects(placements, shares, grid, (canvas_w, canvas_h), gutter)
        fills: dict[int, float] = {}
        for index, rect in rects.items():
            crop_source, _box = crops[index]
            cell_w = max(1, rect[2] - rect[0])
            cell_h = max(1, rect[3] - rect[1])
            scale = min(cell_w / float(crop_source.width), cell_h / float(crop_source.height))
            fills[index] = (
                crop_source.width * scale * crop_source.height * scale
            ) / canvas_area
        survivors = [index for index in keep if keep[index]]
        victims = sorted(
            (
                index for index in rects
                if fills[index] < MIN_USEFUL_PANEL_SHARE
                and layout.panels[index].slot != "head"
                and len(survivors) > 1
            ),
            key=lambda index: fills[index],
        )
        if not victims:
            break
        victim = victims[0]
        keep[victim] = False
        dropped.append(layout.panels[victim].slot)
    panels: list[PanelRecord] = []
    notes: list[str] = []
    head_saved = False
    body_saved = False
    head_coverage = 0.0
    divider = tuple(max(0, value - 28) for value in background) + (255,)
    for index, cell in sorted(rects.items()):
        panel = layout.panels[index]
        art_image, art_mask, art_subject, art_head, art_kind = artworks[index]
        wanted_view = str(getattr(panel, "view", "") or "").strip().lower()
        mirrored = bool(panel.mirror) or (
            wanted_view == VIEW_REAR and art_kind != VIEW_SOURCE_REFERENCE
        )
        crop, box = crops[index]
        if panel.slot == "head":
            crop, box = _grow_head_crop_to_cell(
                box, cell, art_image, art_subject, art_mask
            )
        del art_head
        if mirrored:
            crop = ImageOps.mirror(crop)
        fitted, offset = _fit_into_cell(crop, cell, sharpen=not mirrored)
        canvas.paste(fitted, offset, fitted)
        draw.rectangle(cell, outline=divider, width=1)
        panels.append(
            PanelRecord(
                slot=panel.slot,
                role=panel.role or panel.slot,
                rect=[int(value) for value in cell],
                mirrored=mirrored,
                source_crop=[int(value) for value in box],
                coverage=round(
                    (fitted.width * fitted.height) / canvas_area, 4
                ),
                view=str(getattr(panel, "view", "") or ""),
                view_source=(
                    f"{VIEW_SOURCE_REFERENCE} {view_paths[wanted_view].name}"
                    if wanted_view and art_kind == VIEW_SOURCE_REFERENCE
                    else VIEW_SOURCE_MIRRORED_FRONT
                    if wanted_view and mirrored
                    else VIEW_SOURCE_FRONT
                    if wanted_view
                    else ""
                ),
            )
        )
        if panel.slot == "head" and not mirrored:
            head_coverage = round((fitted.width * fitted.height) / canvas_area, 4)
        if panel.slot == "head" and not head_saved and not mirrored:
            raw_crop = crop
            saved_head, saved_offset = _fit_into_cell(
                raw_crop,
                (
                    0,
                    0,
                    max(1, head[2] - head[0]) * 3,
                    max(1, head[3] - head[1]) * 3,
                ),
                sharpen=True,
            )
            del saved_offset
            saved_head.convert("RGB").save(head_path, format="PNG")
            head_saved = True
        if panel.slot == "body" and not body_saved and not mirrored:
            crops[index][0].convert("RGBA").resize(
                (
                    max(1, int(subject[2] - subject[0])),
                    max(1, int(subject[3] - subject[1])),
                ),
                Image.Resampling.LANCZOS,
            ).save(body_path, format="PNG")
            body_saved = True
    if not head_saved:
        head_crop, _ = _slot_crop("head", image, subject, head)
        head_crop.save(head_path, format="PNG")
    if not body_saved:
        body_crop, _ = _slot_crop("body", image, subject, head)
        body_crop.save(body_path, format="PNG")
    if layout.synthetic_rear:
        notes.append(
            "rear panel is a mirrored read of the same artwork, not a new angle"
        )
    if any(panel.mirror for panel in layout.panels):
        notes.append("mirrored panels are synthetic opposite reads")
    # Round 69 item 7: say which views came from real artwork and which did not,
    # so a rear panel can never again be mistaken for a genuine new angle.
    real_view_rows = sorted(
        {
            record.view_source
            for record in panels
            if record.view_source.startswith(VIEW_SOURCE_REFERENCE)
        }
    )
    if real_view_rows:
        notes.append("real view artwork used: " + "; ".join(real_view_rows))
    invented_view_rows = sorted(
        {
            f"{record.view} = {record.view_source}"
            for record in panels
            if record.view
            and record.view_source
            and not record.view_source.startswith(VIEW_SOURCE_REFERENCE)
        }
    )
    if invented_view_rows:
        notes.append(
            "view panel recomputed from the front picture (no artwork given): "
            + "; ".join(invented_view_rows)
        )
    if unusable_views:
        notes.append(
            "view artwork given but unusable (no subject found): "
            + ", ".join(unusable_views)
        )
    notes.append(f"source head region normalized to {list(head)}")
    if view:
        share = float(OUTFIT_VIEW_SHARES[view])
        notes.append(
            (
                "wardrobe panel keeps the whole neck-down figure: "
                if share >= 1.0
                else "wardrobe panel cut to the visible framing: "
            )
            + f"{view} ({share:.2f} of the neck-down figure)"
        )
    if dropped:
        notes.append(
            "dropped panel(s) too small to condition anything: "
            + ", ".join(sorted(set(dropped)))
        )
    if overlay_stats.get("applied"):
        notes.append(
            "burned-in white caption/title/UI painted out of the outer bands: "
            f"{int(overlay_stats['pixels'])} px = "
            f"{float(overlay_stats['fraction']) * 100.0:.2f}% of the source picture"
        )
    elif overlay_stats.get("skipped_reason"):
        notes.append(f"overlay suppression: {overlay_stats['skipped_reason']}")
    notes.append(f"canvas aspect {canvas_w}x{canvas_h} = {canvas_w / float(max(1, canvas_h)):.3f}")

    # Round 59: the number the age-drift reports actually hinge on.  ``head_coverage``
    # can be 0.53 on a sheet grown from a social-media thumbnail, and the sheet
    # still has no face to read.  Recording the crop's real megapixels next to
    # the coverage is what makes "the layout lever is exhausted" visible instead
    # of arguable.
    head_detail_mp = source_head_crop_megapixels(panels)
    source_mp = round(
        (image.width * image.height) / 1_000_000.0, 5
    )
    notes.append(
        "reference detail: head panel carries "
        f"{head_detail_mp:.5f} MP of real artwork; source picture "
        f"{image.width}x{image.height} = {source_mp:.5f} MP"
    )

    canvas.convert("RGB").save(sheet_path, format="PNG")
    result = IdentitySheetResult(
        ok=True,
        reason="composed",
        sheet_path=str(sheet_path.resolve()),
        head_path=str(head_path.resolve()),
        body_path=str(body_path.resolve()),
        preset=preset_index,
        preset_label=layout.label,
        outfit_view=view,
        width=canvas_w,
        height=canvas_h,
        source_path=str(source.resolve()),
        source_fingerprint=fingerprint,
        canvas_aspect=round(canvas_aspect, 4),
        head_coverage=round(head_coverage, 4),
        source_head_crop_megapixels=head_detail_mp,
        source_megapixels=source_mp,
        dropped_slots=sorted(set(dropped)),
        panels=panels,
        notes=notes,
        view_fingerprints=dict(view_fingerprints),
    )
    try:
        sidecar.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=True), encoding="utf-8"
        )
    except OSError:
        pass
    return result


def _canvas_size(aspect: tuple[int, int], max_megapixels: float) -> tuple[int, int]:
    """Fit one aspect ratio inside a megapixel budget, aligned to 32 pixels.

    Both edges are floored to a 32-pixel multiple of the exact solution, which
    can only ever land below the budget -- so the aspect survives.  Iteratively
    shaving the longer edge instead (the previous behaviour) walked a portrait
    canvas back to a square and silently undid the whole point of matching the
    V1 geometry.
    """

    if isinstance(aspect, (tuple, list)) and len(aspect) == 2:
        ratio = float(aspect[0]) / float(max(1, int(aspect[1])))
    else:
        ratio = float(aspect)
    ratio = max(MIN_CANVAS_ASPECT, min(MAX_CANVAS_ASPECT, ratio))
    budget = max(0.12, float(max_megapixels)) * 1_000_000.0
    width = max(32, int(((budget * ratio) ** 0.5) // 32) * 32)
    height = max(32, int(((budget / ratio) ** 0.5) // 32) * 32)
    while width * height > budget:
        if width > 32:
            width -= 32
        elif height > 32:
            height -= 32
        else:
            break
    return width, height


def _canvas_ratio(
    target_aspect: tuple[int, int] | float | None,
    layout: SheetPreset,
) -> float:
    """Resolve the sheet canvas aspect from the source Shot geometry.

    ``target_aspect`` wins whenever it is usable, because Relay normalises the
    reference into the V1 frame; the preset's upstream aspect is only a
    fallback for sheets authored without a Shot.  Anything unusable (zero,
    negative, NaN, a string, a short tuple) degrades to the fallback rather
    than raising, so Character Swap never dies on bad media metadata.
    """

    ratio: float | None = None
    if isinstance(target_aspect, (tuple, list)) and len(target_aspect) >= 2:
        try:
            height = float(target_aspect[1])
            width = float(target_aspect[0])
            if height > 0.0:
                ratio = width / height
        except (TypeError, ValueError):
            ratio = None
    elif isinstance(target_aspect, (int, float)) and not isinstance(target_aspect, bool):
        ratio = float(target_aspect)
    if ratio is None or not math.isfinite(ratio) or ratio <= 0.0:
        ratio = float(layout.aspect[0]) / float(max(1, int(layout.aspect[1])))
    return max(MIN_CANVAS_ASPECT, min(MAX_CANVAS_ASPECT, float(ratio)))


def _arrangement(
    layout: SheetPreset,
    canvas_aspect: float,
    crop_aspects: dict[int, float] | None = None,
) -> tuple[tuple[int, int], list[tuple[int, int, int, int, int]]]:
    """Choose the panel arrangement for one canvas aspect.

    ``SHEET_PRESETS`` declare the upstream grid, but a grid only conditions what
    it can draw.  In a portrait V1 frame a head drawn *beside* the figure is
    starved of width and ends up near 13 % of the reference -- the exact
    geometry that let H3 keep inventing faces.  When the declared grid fights
    the canvas aspect the grid is transposed, so identity-first sheets put the
    head band across the full canvas width and wardrobe sheets keep the figure
    at full height.

    The direction is chosen by measuring both orientations: for every panel the
    artwork area is its designed quota multiplied by how well its crop aspect
    matches the cell aspect it would actually get.  The orientation that gives
    the primary identity panel more real artwork wins, so a 2x2 wardrobe grid
    still becomes a head band on top when the canvas is portrait, which the old
    "transpose only when cols != rows" rule could not express.
    """

    cols, rows = max(1, int(layout.grid[0])), max(1, int(layout.grid[1]))
    candidates = (
        (False, (cols, rows)),
        (True, (rows, cols)),
    )
    primary = _primary_panel_index(layout)
    best: tuple[float, tuple[int, int], list[tuple[int, int, int, int, int]]] | None = None
    for transpose, (grid_cols, grid_rows) in candidates:
        placements = _placements(layout, (grid_cols, grid_rows), transpose)
        score = _orientation_score(
            layout,
            placements,
            (grid_cols, grid_rows),
            canvas_aspect,
            crop_aspects,
            primary,
        )
        if best is None or score > best[0] + 1e-6:
            best = (score, (grid_cols, grid_rows), placements)
    if best is None:  # pragma: no cover - two candidates always exist
        grid = (cols, rows)
        return grid, _placements(layout, grid, False)
    return best[1], best[2]


def _placements(
    layout: SheetPreset,
    grid: tuple[int, int],
    transpose: bool,
) -> list[tuple[int, int, int, int, int]]:
    """Project declared panel coordinates onto one candidate grid."""

    cols, rows = max(1, int(grid[0])), max(1, int(grid[1]))
    placements: list[tuple[int, int, int, int, int]] = []
    for index, panel in enumerate(layout.panels):
        col, row, span_cols, span_rows = (
            panel.col, panel.row, max(1, panel.col_span), max(1, panel.row_span)
        )
        if transpose:
            col, row = row, col
            span_cols, span_rows = span_rows, span_cols
        col = min(max(0, col), cols - 1)
        row = min(max(0, row), rows - 1)
        span_cols = max(1, min(span_cols, cols - col))
        span_rows = max(1, min(span_rows, rows - row))
        placements.append((index, col, row, span_cols, span_rows))
    return placements


def _primary_panel_index(layout: SheetPreset) -> int:
    """The panel an identity sheet is really for: the real (un-mirrored) head."""

    for index, panel in enumerate(layout.panels):
        if panel.slot == "head" and not panel.mirror:
            return index
    weights = layout.panel_weights or ()
    if weights:
        return max(range(len(layout.panels)), key=lambda i: float(weights[min(i, len(weights) - 1)]))
    return 0


def _orientation_score(
    layout: SheetPreset,
    placements: list[tuple[int, int, int, int, int]],
    grid: tuple[int, int],
    canvas_aspect: float,
    crop_aspects: dict[int, float] | None,
    primary: int,
) -> float:
    """Real artwork area a grid orientation would deliver (primary weighted).

    Contain-fitting artwork of aspect ``a`` into a cell of aspect ``A`` covers
    ``min(a/A, A/a)`` of that cell, so the score needs no imaging and no pixels:
    it is exact for the geometry that actually reaches the reference encoder.

    The face is what the user judges, so the vote is identity-first: the
    wardrobe panel only breaks a near-tie.  Round-15 proved the old 0.2 weight
    was too loud -- for the 209x600 P1 artwork it put the head in a narrow
    column at 15.3 % canvas coverage when the same sheet stacked to 21 %+, and
    the missing face detail is exactly what Relay filled in with grey hair and
    forehead wrinkles.
    """

    keep = {index: True for index, *_ in placements}
    shares = _area_shares(layout, placements, keep)
    col_w, row_h = _solve_band_sizes(placements, shares, grid)
    primary_fill = 0.0
    others = 0.0
    for index, col, row, span_cols, span_rows in placements:
        quota = shares.get(index, 0.0)
        if quota <= 0.0:
            continue
        width = sum(col_w[c] for c in range(col, min(len(col_w), col + span_cols)))
        height = sum(row_h[r] for r in range(row, min(len(row_h), row + span_rows)))
        if width <= 1e-9 or height <= 1e-9:
            continue
        cell_aspect = (width * canvas_aspect) / height
        crop_aspect = 1.0
        if crop_aspects:
            candidate = float(crop_aspects.get(index, 1.0) or 1.0)
            if candidate > 1e-6:
                crop_aspect = candidate
        mismatch = min(
            crop_aspect / cell_aspect, cell_aspect / crop_aspect
        )
        fill = quota * mismatch
        if index == primary:
            primary_fill = fill
        else:
            others += fill
    return primary_fill + ORIENT_SECONDARY_PANEL_WEIGHT * others


def _area_shares(
    layout: SheetPreset,
    placements: list[tuple[int, int, int, int, int]],
    keep: dict[int, bool],
) -> dict[int, float]:
    """Normalised canvas-area quota for every surviving panel."""

    raw: dict[int, float] = {}
    for index, *_ in placements:
        if not keep.get(index, True):
            continue
        weight = 0.0
        if index < len(layout.panel_weights):
            weight = float(layout.panel_weights[index])
        if weight <= 0.0:
            weight = float(getattr(layout.panels[index], "area_weight", 0.0))
        raw[index] = weight if weight > 0.0 else 1.0
    total = sum(raw.values()) or 1.0
    return {index: value / total for index, value in raw.items()}


def _view_adjusted_layout(layout: SheetPreset, view: str) -> SheetPreset:
    """Re-weight the layout when the wardrobe panel has been cut to the Shot.

    ``OUTFIT_VIEW_OUTFIT_AREA`` states the canvas a *chest-height* wardrobe
    panel still needs.  A ``body`` panel is never re-weighted: it still shows the
    whole figure, so it still needs its designed area.  Freed area goes to the
    face panels, which is the surface the user grades — round-15 P1 measured
    20.9 % head coverage at the designed share and 34.2 % once the face panel
    owned the difference.

    The ``full`` view re-weights too even though its panel is uncut, because the
    panel is still cropped from the neck down: it carries no face, so its taller
    artwork does not need more canvas than the chest panel had.  Its 0.44 target
    is ``medium``'s value verbatim, which round 28 verified keeps head coverage
    at 0.5259 — byte-identical to the take the user graded "头部效果完美" — while
    the wardrobe crop grows from the tunic hem to the shoes.
    """

    if view not in OUTFIT_VIEW_OUTFIT_AREA:
        return layout
    weights: list[float] = []
    for index, panel in enumerate(layout.panels):
        weight = 0.0
        if index < len(layout.panel_weights):
            weight = float(layout.panel_weights[index])
        if weight <= 0.0:
            weight = float(panel.area_weight or 0.0)
        weights.append(weight if weight > 0.0 else 1.0)
    slots = [str(panel.slot or "").strip().lower() for panel in layout.panels]
    wardrobe = [i for i, slot in enumerate(slots) if slot == "outfit"]
    faces = [i for i, slot in enumerate(slots) if slot == "head"]
    if not wardrobe or not faces:
        return layout
    total = sum(weights)
    wardrobe_total = sum(weights[i] for i in wardrobe)
    face_total = sum(weights[i] for i in faces)
    target = float(OUTFIT_VIEW_OUTFIT_AREA[view]) * total
    freed = wardrobe_total - target
    if freed <= 1e-9 or face_total <= 1e-9:
        return layout
    scale = max(0.0, target) / wardrobe_total
    adjusted = list(weights)
    for index in wardrobe:
        adjusted[index] = weights[index] * scale
    for index in faces:
        adjusted[index] = weights[index] + freed * (weights[index] / face_total)
    adjusted = [round(max(0.0, value), 9) for value in adjusted]
    if sum(adjusted) <= 1e-9:
        return layout
    return replace(layout, panel_weights=tuple(adjusted))


def _solve_band_sizes(
    placements: list[tuple[int, int, int, int, int]],
    shares: dict[int, float],
    grid: tuple[int, int],
) -> tuple[list[float], list[float]]:
    """Solve normalised column widths / row heights for the designed quotas.

    Panel areas are products of band widths and heights, so the quotas form a
    small linear system.  Gauss-Seidel relaxation converges in a handful of
    passes for these 1x2 / 2x1 / 2x2 / 3x1 grids and leaves every band as close
    to its designed share as the grid allows.
    """

    cols, rows = max(1, grid[0]), max(1, grid[1])
    col_w = [1.0 / cols] * cols
    row_h = [1.0 / rows] * rows
    active = [row for row in placements if shares.get(row[0], 0.0) > 0.0]
    if not active:
        return col_w, row_h
    for _ in range(80):
        acc = [[0.0, 0] for _ in range(cols)]
        for index, col, row, span_cols, span_rows in active:
            height = sum(row_h[r] for r in range(row, min(rows, row + span_rows)))
            if height <= 1e-9:
                continue
            per = (shares[index] / height) / span_cols
            for band in range(col, min(cols, col + span_cols)):
                acc[band][0] += per
                acc[band][1] += 1
        col_w = [
            max(1e-4, (value / count) if count else width)
            for (value, count), width in zip(acc, col_w)
        ]
        total = sum(col_w) or 1.0
        col_w = [width / total for width in col_w]
        acc = [[0.0, 0] for _ in range(rows)]
        for index, col, row, span_cols, span_rows in active:
            width = sum(col_w[c] for c in range(col, min(cols, col + span_cols)))
            if width <= 1e-9:
                continue
            per = (shares[index] / width) / span_rows
            for band in range(row, min(rows, row + span_rows)):
                acc[band][0] += per
                acc[band][1] += 1
        row_h = [
            max(1e-4, (value / count) if count else height)
            for (value, count), height in zip(acc, row_h)
        ]
        total = sum(row_h) or 1.0
        row_h = [height / total for height in row_h]
    return col_w, row_h


def _cell_rects(
    placements: list[tuple[int, int, int, int, int]],
    shares: dict[int, float],
    grid: tuple[int, int],
    canvas_size: tuple[int, int],
    gutter: int,
) -> dict[int, tuple[int, int, int, int]]:
    """Map every surviving panel (including spans) to its canvas rectangle."""

    width, height = canvas_size
    cols, rows = max(1, grid[0]), max(1, grid[1])
    col_w, row_h = _solve_band_sizes(placements, shares, grid)
    pad = gutter
    usable_w = max(1, width - 2 * pad)
    usable_h = max(1, height - 2 * pad)
    col_edges = [0.0]
    for value in col_w:
        col_edges.append(col_edges[-1] + value)
    row_edges = [0.0]
    for value in row_h:
        row_edges.append(row_edges[-1] + value)
    inner = max(2, int(gutter * 0.45))
    rects: dict[int, tuple[int, int, int, int]] = {}
    for index, col, row, span_cols, span_rows in placements:
        if not shares.get(index, 0.0):
            continue
        left = int(pad + col_edges[col] * usable_w) + inner
        top = int(pad + row_edges[row] * usable_h) + inner
        right = int(pad + col_edges[min(cols, col + span_cols)] * usable_w) - inner
        bottom = int(pad + row_edges[min(rows, row + span_rows)] * usable_h) - inner
        rects[index] = (
            max(0, left),
            max(0, top),
            max(left + 8, right),
            max(top + 8, bottom),
        )
    return rects


def sheet_preset_labels() -> list[tuple[int, str]]:
    return [(index, f"{index} - {preset.label}") for index, preset in sorted(SHEET_PRESETS.items())]


def sheet_preset_panel_roles(preset: int) -> list[str]:
    layout = SHEET_PRESETS.get(int(preset)) or SHEET_PRESETS[DEFAULT_SHEET_PRESET]
    return [
        f"{panel.slot} = {panel.role or panel.slot}"
        + (" (mirrored)" if panel.mirror else "")
        + (f" [{panel.view} view]" if getattr(panel, "view", "") else "")
        for panel in layout.panels
    ]


def resolve_identity_sheet(
    source: Path | str,
    output_dir: Path | str,
    *,
    preset: int = DEFAULT_SHEET_PRESET,
    max_megapixels: float = DEFAULT_MAX_MEGAPIXELS,
    force: bool = False,
    target_aspect: tuple[int, int] | float | None = None,
    outfit_view: str | None = None,
    view_sources: dict | None = None,
) -> IdentitySheetResult:
    """Never-throwing wrapper used by Character Swap job compilation."""

    try:
        return compose_identity_sheet(
            source,
            output_dir,
            preset=preset,
            max_megapixels=max_megapixels,
            force=force,
            target_aspect=target_aspect,
            outfit_view=outfit_view,
            view_sources=view_sources,
        )
    except Exception as error:  # pragma: no cover - imaging backend guard
        return _failure(f"identity sheet composition failed: {error}", Path(str(source)))
