"""Akatz H3 Character Swap workflow integration helpers.

The published LoRA/workflow replaces one selected source character per pass.
Studio therefore compiles one deterministic pass per mapped V1 role that is
actually visible in the current Shot. Multiple roles are generated independently
from the clean V1 plate and composited by their tracked person regions.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CHARACTER_SWAP_WORKFLOW_NAME = "H3-Character-Swap-Relay-V2-api.json"
# The swap prompt is authored by hand inside one API graph and harvested from it at
# compile time. That file used to be named separately from the graph that gets
# *submitted*, because Round 112 ships the mask graph while the accepted take's
# 4051-character prompt (appends inside its 1200-character budget) lives in this one.
#
# Round 122 (导演 11-11 的选择：完全对齐他手动成功那一枪) turns that split off.  The
# director trims clauses in the file he actually submits -- he deleted
# ``SILENT LISTENER PERFORMANCE — AUTHORITATIVE…`` and ``The source hair and headgear
# belong to the erased actor…`` from ``H3-Character-Swap-Relay-V2-API-WITHMASK.json``
# and his hand run off that file succeeded (ComfyUI history ``107a19c7…``: 46 nodes,
# prompt 2 875 characters, no clauses).  Studio still sent 4 051: the manifest records
# ``author_prompt_chars = 2895``, which is exactly the api graph's 2 876 plus the
# 19-character silent-mouth rewrite -- harvesting from the *other* file put his deleted
# words back on the wire.  So the harvest now follows ``character_swap_workflow_name``
# (line 4779): submit WITHMASK, harvest WITHMASK.  If that file is not on disk the
# harvest falls back to the api graph rather than stopping a Shot.
# One-line revert: ``H3_CHARACTER_SWAP_PROMPT_SOURCE=api`` (or any .json file name).
CHARACTER_SWAP_PROMPT_SOURCE_ENV = "H3_CHARACTER_SWAP_PROMPT_SOURCE"
CHARACTER_SWAP_PROMPT_SOURCE_FOLLOW_VALUES = frozenset({"follow", "follow_submitted", "submitted", "auto"})
CHARACTER_SWAP_PROMPT_SOURCE_DEFAULT = "follow"
CHARACTER_SWAP_PROMPT_SOURCE_NAME = CHARACTER_SWAP_WORKFLOW_NAME
LEGACY_CHARACTER_SWAP_WORKFLOW_NAME = (
    "akatz-labs-character-swap-turbo8-adaptive-window-api.json"
)
CHARACTER_SWAP_LORA_NAME = "h3_character_swap_v1.5.safetensors"
CHARACTER_SWAP_RELAY_CLASS = "H3RelayWindowPlan"
CHARACTER_SWAP_PREPARE_CLASS = "H3RelayPrepareSource"
LEGACY_CHARACTER_SWAP_RELAY_CLASS = "H3RelayWindowedEdit"
LEGACY_CHARACTER_SWAP_PREPARE_CLASS = "LabsH3PrepareVideo"

# Official Character-Swap LoRA strength ceiling.
#
# The published LoRA is trained for strength 1.0-1.5 and the author's own graph
# ships 1.5 (node ``adapter`` in H3-Character-Swap-Relay-V2-api.json).  Studio's
# retry ladder in smart_render_worker.py escalated past that on seeds
# 923011007/923011008 - the ComfyUI /history read-back for job
# preview_923011007_1793291943180178000 shows 1.5 then 1.75 then 2.0 - and the
# over-driven passes are the ones the user graded as "a different person wearing
# roughly the right clothes".  Out-of-range strength is what makes a swap LoRA
# invent an age, a face and wrinkles rather than reproduce the reference, which
# is exactly the "old man" regression reported across S3/S7/S10/S11.
#
# ``H3_CHARACTER_SWAP_LORA_MAX_STRENGTH`` may only lower the ceiling (for
# example 1.25).  Anything above 1.5, or a value that does not parse, falls back
# to the documented 1.5 so an accidental typo cannot reopen the ladder.
CHARACTER_SWAP_LORA_OFFICIAL_MAX_STRENGTH = 1.7


def _character_swap_lora_strength_ceiling() -> float:
    raw = os.environ.get("H3_CHARACTER_SWAP_LORA_MAX_STRENGTH", "").strip()
    if not raw:
        return CHARACTER_SWAP_LORA_OFFICIAL_MAX_STRENGTH
    try:
        requested = float(raw)
    except ValueError:
        return CHARACTER_SWAP_LORA_OFFICIAL_MAX_STRENGTH
    if requested <= 0.0 or requested > CHARACTER_SWAP_LORA_OFFICIAL_MAX_STRENGTH:
        return CHARACTER_SWAP_LORA_OFFICIAL_MAX_STRENGTH
    return requested


CHARACTER_SWAP_LORA_MAX_STRENGTH = _character_swap_lora_strength_ceiling()
# ``ref_image_size`` is the mode the manual graph ships: the reference is fed at
# its own size after RTX Video Super Resolution upscales it 2x at ULTRA quality
# (template node ``9``).  Studio used to inherit both purely by accident,
# because ``compile_character_swap_pass`` never touched those nodes.  They are
# now written and reported explicitly so a re-exported template cannot quietly
# drop the upscale that makes Picture 1 legible to H3.
CHARACTER_SWAP_REFERENCE_UPSCALE_CLASS = "RTXVideoSuperResolution"
CHARACTER_SWAP_REF_IMAGE_SIZE_ENV = "H3_CHARACTER_SWAP_REF_IMAGE_SIZE"
CHARACTER_SWAP_REF_IMAGE_SIZE_DEFAULT = "match"
# The upscale multiplier the RTX node runs at.  The template ships 2, which is
# what every verified take in this project used.  Raising it makes Picture 1's
# wardrobe and facial line-work legible to H3 at 1.0 MP, which is the knob the
# "the swap only changed the head" complaints come down to; 3 and 4 are the only
# other multipliers the node accepts, and anything else falls back to the
# template rather than sending a value the custom node would reject.
CHARACTER_SWAP_REF_UPSCALE_SCALE_ENV = "H3_CHARACTER_SWAP_REF_UPSCALE_SCALE"
CHARACTER_SWAP_REF_UPSCALE_SCALE_CHOICES = (2, 3, 4)
CHARACTER_SWAP_REF_UPSCALE_SCALE_KEYS = (
    "resize_type.scale",
    "scale",
    "upscale_factor",
)
# Round 59: the same node also chooses *how* it invents the pixels it adds.
# ``quality`` selects an NVIDIA SDK model and ``strength`` selects how hard it
# pushes.  The shipped template runs ULTRA at strength 1.0, which is the right
# choice for a legible source picture and a bad one for a 0.09 MP thumbnail:
# the SDK is an enhancer, so on a thumbnail it has to guess facial micro-detail
# that the reference never contained, and guessed facial detail on a cartoon
# reads as creases, stubble and an older person.  Both knobs therefore become
# explicit levers, and both stay at the template value unless the environment
# asks otherwise, so the verified baseline is what ships.
#
# The accepted spellings are the ``nvvfx.QualityLevel`` members the installed
# node publishes.  ``DENOISE_*`` and ``DEBLUR_*`` are deliberately not offered:
# that node keeps the *input* dimensions for those modes, so choosing one would
# silently undo the 2x that makes Picture 1 legible and move two variables at
# once.  BICUBIC is offered because it is the only listed mode that interpolates
# instead of enhancing, which is the honest way to test whether ULTRA was the
# thing drawing the wrinkles.
CHARACTER_SWAP_REF_UPSCALE_QUALITY_ENV = "H3_CHARACTER_SWAP_REF_UPSCALE_QUALITY"
CHARACTER_SWAP_REF_UPSCALE_QUALITY_KEYS = ("quality",)
CHARACTER_SWAP_REF_UPSCALE_QUALITY_CHOICES = (
    "BICUBIC",
    "LOW",
    "MEDIUM",
    "HIGH",
    "ULTRA",
    "HIGHBITRATE_LOW",
    "HIGHBITRATE_MEDIUM",
    "HIGHBITRATE_HIGH",
    "HIGHBITRATE_ULTRA",
    "STREAMING_MEDIUM",
    "STREAMING_ULTRA",
)
CHARACTER_SWAP_REF_UPSCALE_STRENGTH_ENV = "H3_CHARACTER_SWAP_REF_UPSCALE_STRENGTH"
CHARACTER_SWAP_REF_UPSCALE_STRENGTH_KEYS = ("strength",)
CHARACTER_SWAP_REF_UPSCALE_STRENGTH_MAX = 1.0
# Round 67: the same custom node, used on the *answer* instead of the question.
#
# The director's preview loop is a cost/legibility trade: ``PREPARE_RESOLUTION_HIGH``
# is pinned to "480" so a 0.5 MP Preview stays cheap enough to iterate on, and the
# price of that pin is a 576x864 take that the eye reads as soft.  RTX Video Super
# Resolution is not a second diffusion pass - it is the NVFX hardware enhancer the
# template already trusts on Picture 1 - so running it once on the finished frames
# makes a 480-bucket Preview judgeable at 1x without buying a second generation.
# It is therefore attached to the Preview render only, after the Relay has
# published its frames and before ``CreateVideo`` muxes them.
#
# Final Render deliberately keeps the node off: an enhancer that invents detail can
# add creases the reference never contained, and a Final take has to be graded on
# exactly what H3 produced.  Round 69 inverts the Preview default too.  The director
# graded two takes whose *backgrounds* grew a honeycomb lattice that the manual
# ComfyUI run for the same clip and seed never showed, and the enhancer was the only
# thing on the wire that could invent it; its 2x output was also 576x866 while every
# H3 bucket frame is 576x864, which made the assembled Preview a different canvas
# from the take that was judged.  The node therefore ships off and
# ``H3_CHARACTER_SWAP_PREVIEW_VSR`` is the opt-in: an affirmative word (``on``/``1``)
# turns it on at the shipped 2x, and 2/3/4 ask for a different multiplier.  Unset,
# blank and anything unparseable mean off, so a half-written variable can never put
# an enhancer back on a take that is being graded for identity.
CHARACTER_SWAP_OUTPUT_UPSCALE_CLASS = CHARACTER_SWAP_REFERENCE_UPSCALE_CLASS
CHARACTER_SWAP_OUTPUT_UPSCALE_ENV = "H3_CHARACTER_SWAP_PREVIEW_VSR"
CHARACTER_SWAP_OUTPUT_UPSCALE_DEFAULT_SCALE = 2
# The template's node ids are semantic strings (``finish``, ``video``, ``save``),
# so the inserted node gets one too instead of a number that would collide with a
# re-exported template.  The fixed id also makes re-compiling an already-compiled
# workflow idempotent rather than stacking two enhancers.
CHARACTER_SWAP_OUTPUT_UPSCALE_NODE_ID = "rtx_vsr_output"
CHARACTER_SWAP_OUTPUT_UPSCALE_ON_WORDS = ("1", "on", "true", "yes", "enable", "enabled")
CHARACTER_SWAP_OUTPUT_UPSCALE_OFF_WORDS = (
    "0",
    "off",
    "false",
    "no",
    "none",
    "disable",
    "disabled",
)
# A video file node cannot take an IMAGE.  When the saver is fed by a muxer, the
# enhancer has to go upstream of the muxer, on the image input of that muxer.
CHARACTER_SWAP_VIDEO_MUXER_CLASSES = (
    "CreateVideo",
    "CreateVideoNode",
    "VideoFromImages",
    "CreateVideoFromBatch",
)
CHARACTER_SWAP_OUTPUT_IMAGE_INPUTS = ("video", "images", "image", "frames")
# Why these three fallbacks and not something cleverer: they are the values the
# shipped template authors on node ``9`` and the defaults the installed node
# publishes, so a template that ever loses node ``9`` still compiles a Preview the
# server can validate instead of one missing required inputs.
CHARACTER_SWAP_OUTPUT_UPSCALE_RESIZE_MODE = "scale by multiplier"
CHARACTER_SWAP_OUTPUT_UPSCALE_FALLBACK_QUALITY = "ULTRA"
CHARACTER_SWAP_OUTPUT_UPSCALE_FALLBACK_STRENGTH = 1.0
CHARACTER_SWAP_OUTPUT_UPSCALE_FALLBACK_ENCODING = "8-bit RGB"
# What the stage is called in the ComfyUI graph.  Deliberately not the template
# node's own title, so the queue shows which of the two enhancers is which.
CHARACTER_SWAP_OUTPUT_UPSCALE_NODE_TITLE = "RTX Video Super Resolution - Preview Output"
# Why the enhancer is *absent*, recorded in the manifest instead of guessed by
# whoever reads the Job later.  A pass that got the node reports presence with
# ``output_upscale_enabled`` and leaves this row empty, so every value here is a
# negative answer with a named cause.
OUTPUT_UPSCALE_REASON_NOT_PREVIEW = "not_preview_request"
OUTPUT_UPSCALE_REASON_ENVIRONMENT = "environment_disabled"
OUTPUT_UPSCALE_REASON_NO_IMAGE_INPUT = "no_image_input_to_upscale"


def _character_swap_output_upscale_row_defaults() -> dict[str, Any]:
    """Every row the manifest must carry about the output enhancer.

    Studio copies these keys verbatim into the pass row and strips them again
    before hashing, so a Final Render fingerprint never moves because of a
    Preview-only node.  One dict defines both the key set and the neutral value
    each branch reports, so a row can never be added to the writer and forgotten
    by the copier.
    """

    return {
        "output_upscale_requested": False,
        "output_upscale_enabled": False,
        "output_upscale_node_id": "",
        "output_upscale_attach_node_id": "",
        "output_upscale_attach_input": "",
        "output_upscale_source_node_id": "",
        "output_upscale_scale": 0.0,
        "output_upscale_scale_source": "",
        "output_upscale_quality": "",
        "output_upscale_strength": 0.0,
        "output_upscale_image_encoding": "",
        "output_upscale_skip_reason": "",
        "output_upscale_env": "",
    }


CHARACTER_SWAP_OUTPUT_UPSCALE_ROW_DEFAULTS = (
    _character_swap_output_upscale_row_defaults()
)
CHARACTER_SWAP_OUTPUT_UPSCALE_CONTRACT_KEYS: tuple[str, ...] = tuple(
    CHARACTER_SWAP_OUTPUT_UPSCALE_ROW_DEFAULTS
)

SOURCE_REMAKE_MODE_CHARACTER_SWAP = "adaptive_character_swap"
SOURCE_REMAKE_MODE_DIRECTED_SWAP = "adaptive_character_swap_directed"
SOURCE_REMAKE_MODE_CREATIVE_H3 = "creative_h3"
SOURCE_REMAKE_MODES = {
    SOURCE_REMAKE_MODE_CHARACTER_SWAP,
    SOURCE_REMAKE_MODE_DIRECTED_SWAP,
    SOURCE_REMAKE_MODE_CREATIVE_H3,
}
SOURCE_VIDEO_CAST_REMAKE_SKILL_KEY = "source-video-cast-remake-h3"
KEEP_V1_TARGET = "KEEP_V1"

RELAY_FPS = 24
RELAY_WINDOW_FRAMES = 124
RELAY_HISTORY_FRAMES = 18
H3_FRAME_MODULUS = 17
H3_FRAME_REMAINDER = 5

# Invented-background-pattern gate.  The clause was originally written for
# face-filling close-ups (box area >= 0.45), but the honeycomb/grid artefacts
# reported in S2, S4, S6 and S8 all landed in Shots whose tracked box covers
# only ~0.10-0.12 of the frame.  A redrawn character always perturbs the plate
# behind it, so the gate now matches the smallest box the tracker actually
# produces rather than only extreme close-ups.  Re-measured against the newest
# verified run (policy 46 job records): the tail clause already fired for S3,
# S4, S6, S8, S10 and S11 on selected-box areas of 0.729-0.960 and the invented
# patterns still appeared, so the prohibition now also lives inside the
# official Subject 2 field (see _author_prompt_with_locks) where H3 reads it.
# This gate only decides whether the large-plate tail reinforcement is added:
# 0.200 keeps that reinforcement for every reported bad-background Shot
# (S4 0.800, S6 0.768, S8 0.729, S3 0.856, S10 0.950, S11 0.960, and an S2-type
# manual override box at 0.241) while S5 (0.152 / 0.177) and a distant second
# body (0.047) keep their prompt lean.
#
# Lowered to 0.060 on 2026-10-26 for the single-character project
# a_cartoon_character_with_a_black_shirt_and_yellow_pants.  Its S2 rendered the
# same invented honeycomb/lattice background with the Subject 2 scene lock
# already present, and that pass' selected R1 box measures 0.30 x 0.30 = 0.090
# of the frame: the tail reinforcement had been gated off at 0.200 even though
# the artefact landed in exactly the plate the clause is written for.  0.060
# keeps the reinforcement for every measured bad-background Shot down to that
# 0.090 box, while still excluding the 0.047 distant second body the note above
# deliberately leaves lean.
PLATE_TEXTURE_CONTRACT_MIN_BOX_AREA = 0.060

# Prompt-length guard.  The longest prompt that has ever been submitted to the
# real H3 endpoint *and* rendered successfully is 11 911 characters (seed
# 97000374, S10, policy 50 — three attempts, H3 accepted the prompt, VRAM
# released, and the render is a cartoon in P1's medium with the plate's
# composition).  The budget below is deliberately under that ceiling.  14 385
# characters has still never been submitted.  Every graded full-film take that
# lost likeness (S10 20 %, S7 40 %, S11 60 %) compiled a longer prompt than the
# takes the user graded as good, and the newest identity clauses sit at the very
# end of the prompt where dilution hurts most.  Measured directly against the
# prompts ComfyUI's /history endpoint received for the graded full film (seeds
# 97000374-97000544, archived in working/submitted_prompts_20261025), the
# pass/fail split *is* the tail drop: every take the user graded ok or 80 %
# kept both CLOSE-UP MEDIUM REINFORCEMENT and NO INVENTED TEXTURE OR PATTERN,
# while every take graded 20 %-60 % - and the S3/S6/S10 "old man plus invented
# background pattern" group - had lost exactly those two clauses to this loop.
# Length is therefore not likeness-neutral: the clauses it sacrificed were
# load-bearing.  Studio now pays for the long prompts by compressing the two
# overlapping sheet clauses (design_sheet_contract under sheet framing, and
# multi_person_subject_definitions) instead of sacrificing them, so the only
# clauses that may still be dropped are the silent-mouth reinforcements - the
# weak copies of the always-appended authoritative SILENT LISTENER contract.
# Rank 0 clauses are never dropped: they are the only copy of a rule the graph
# cannot infer from its two inputs.
#
# Recalibrated 2026-10-26 from 11 400 to 11 900.  The old number pre-dated the
# drop-rank freeze below: it was chosen when the length guard still sacrificed
# CLOSE-UP MEDIUM REINFORCEMENT and NO INVENTED TEXTURE OR PATTERN first, so a
# 11 400 prompt bought those two back.  With those clauses unfreezable the only
# rank-bearing clauses left are the two silent-mouth reinforcements, and 11 400
# forced four silent Shots (S2/S3/S6/S10, compiled 12 336-12 927 at policy 54)
# to pay 720 characters of mouth reinforcement they had been graded as needing.
# The ceiling was re-measured on 2026-10-26: seed 97000584 submitted 12 326
# characters end to end and rendered successfully (ComfyUI /history read back the
# same length, policy 55, archived in working/submitted_prompts_20261025/).  The
# older 11 911 figure (seed 97000374) is therefore a floor, not a limit, and 11 900
# was silently costing silent-mouth reinforcement again.  12 600 is the new guard:
# it keeps the plate clause that policy 56 adds, and Round 14 reads the submitted
# length back from /history so the ceiling is re-measured rather than assumed.
#
# Tightened to 12 320 on 2026-10-26, i.e. just below the 12 326 characters that
# seed 97000584 demonstrably submitted and rendered.  Six tail clauses were
# compressed in the same commit (medium reinforcement, plate texture, torso
# plate, identity sheet, age lock, wardrobe — ~410 characters per Shot) so the
# four heavy Shots (S2/S3/S6/S10) now fit under the proven ceiling (worst case
# 12 304, S6) instead of riding 190-360 characters above it.  The four silent
# Shots still give up their close-up mouth reinforcement, whose full length is
# ~12 700 — no budget at or under the measured ceiling can keep it.  Budget
# changes are only legitimate next to a measured ceiling: raising this back
# above 12 326 without a new successful submission is guessing.
CHARACTER_SWAP_PROMPT_CHAR_BUDGET = 12320

# Tail clauses Studio may drop, in the order they are sacrificed (1 = first).
# Each entry is load-bearing exactly once, so a rank only exists when another
# clause already carries the same rule:
#   1/2 close-up / medium-shot silent mouth reinforcement — redundant now that
#     the authoritative SILENT LISTENER contract carries the closed-lip wording
#     and stays last; the reinforcement was present in every take that still
#     violated, so it is the weak copy rather than the strong one.
# ``close_up_medium_reinforcement`` and ``plate_texture_contract`` used to be
# ranks 1 and 2, which meant every prompt over the budget lost them first.  The
# submitted-prompt audit above shows those two clauses are what separated a
# graded-good take from a graded-failing one, so they now carry no rank.
# ``plate_wardrobe_blurred_clause`` and ``plate_face_blurred_clause`` also have
# no rank: each is the only place that tells H3 a suppressed plate region (the
# desaturated torso colours, the blurred head band) is intentional, and ignoring
# that is how the source robe reappeared over Picture 1's shirt on S4 and how
# the original V1 face came back underneath the replacement on S7/S9.
# The medium-shot silent gate is the one exception: there the head band and the
# garment band are two stacked regions of the same unresolved window, so policy
# 67 states them once as ``plate_wardrobe_silent_clause`` instead of paying for
# both paragraphs.  Since policy 79 that merged paragraph carries the same
# never-droppable status as the two paragraphs it replaced (see below), so the
# merge hands characters back without putting the rule at risk.
#
# Rank 4/5 ordering (2026-10-26; renumbered by round 50, which added a rank 1): the S8/S9 silent sheet close-up measured
# 13 072 characters once the costume-ownership and apparent-age clauses landed,
# 752 past the submittable ceiling, so the guard had to give up two clauses and
# the crop lock was the first candidate.  The never-droppable tail was compressed
# by 301 characters, which brings the worst case back to a single rank-1 drop
# (12 245 characters, measured when the mouth reminders still held ranks 1-2; from
# round 50 the same pass gives up the silhouette reinforcement first and then the
# rank-2 reminder).  The remaining ordering question still decides grouped and
# heavier passes, and only one of the two candidates is restated elsewhere: the
# wardrobe rule also lives in the unconditional COMPLETE WARDROBE REPLACEMENT
# contract, while <Video 1>'s crop lock exists in no other clause.  The costume
# clause therefore yields before the crop lock.
CHARACTER_SWAP_TAIL_DROP_RANKS = {
    # Policy 79 (2026-10-29, seed 923010907): the silent-gate plate paragraph is
    # no longer a sacrifice, and it carries no rank.  It used to be rank 0, so
    # every Silent Listener pass on this Project gave it up: all three windows
    # compiled to 11 746 characters against the 12 320 proven ceiling, the
    # paragraph's 847 characters were the only overflow, and dropped_tail_clauses
    # read ["plate_wardrobe_silent_clause"] three times out of three.  What that
    # drop bought is now measurable and it was nothing -- the same seed still
    # lip-synced in two of three windows while carrying the mouth reinforcement
    # this clause was protecting, and the module already records seed 97000374
    # losing the reinforcement and lip-syncing anyway.  What the drop cost is the
    # regime the director keeps grading: with no sentence saying the blurred
    # plate's surviving garment colours belong to the erased actor, Relay invented
    # a different costume per window (black robe with a red sash, brown knit,
    # black robe with a blue hem) where Picture 1 shows a black top over a blue
    # hem and yellow checked shorts.  So the merged paragraph now inherits the
    # never-droppable status of the two paragraphs policy 67 merged it from, and
    # the shot-scale mouth reminder (ranks 2-3 after round 50, 772 characters) yields in its
    # place: the same pass lands at 11 821 characters, inside the ceiling.
    # 1 garment-silhouette reinforcement — round 50.  The cut/length/hem sentence is
    # the newest unverified hardening here, and the two ranks below it are verified
    # gates with named failures behind them.  Measured: a silent identity-sheet
    # close-up is 12 956 characters before any drop, the guard needs 636, and the
    # mouth reminders alone barely covered that.  The reinforcement now pays for
    # itself first (186 characters), so rank 4 and rank 5 stay on the page.
    "wardrobe_silhouette_reinforcement": 1,
    "close_up_silent_mouth": 2,
    "medium_shot_silent_mouth": 3,
    # 4 source costume ownership — an intact plate still shows the erased actor's
    # garment, and the clause below demotes that silhouette to a placement guide.
    # It yields fourth because COMPLETE WARDROBE REPLACEMENT, which is emitted for
    # every pass, already forbids any original Video 1 garment on the body.
    "source_costume_leaves_plate": 4,
    # 5 close-up sheet crop lock — the last clause Studio sacrifices.  Its rule
    # (the sheet's out-of-frame panels are identity facts, never framing facts)
    # appears nowhere else, and losing it is how S7/S9 answered by moving the
    # camera and importing the sheet's own hands, cuffs and hem.
    "close_up_sheet_crop_lock": 5,
}

# Below this frame height the identity-suppression band is treated as a head
# band, and the prompt says so.  At or above it the band reaches the shoulders
# and chest, so the plate carries no readable wardrobe at all and the prompt has
# to say that out loud (see ``plate_torso_blurred_clause``).  The Studio reports
# the real band geometry in ``pass_spec["identity_suppression_geometry"]``; this
# constant only classifies it.
PLATE_TORSO_BAND_BOTTOM = 0.45

# Silent-mouth reinforcement tiers.  Both reinforcement clauses used to demand a
# box of at least 0.12 of the frame and 0.35 tall — a medium shot by cinematography
# standards, but a small figure on these portrait plates.  The black-shirt S2
# performer covers 0.090 and is 0.30 tall with a plainly legible face, and H3
# parted its lips on every seed while the reinforcement stayed silent about it.
# Any performer large enough that the mouth is readable gets the reminder; a
# distant figure (the 0.039 crop in the existing tests) stays lean.
SILENT_REINFORCEMENT_MIN_BOX_AREA = 0.050
SILENT_REINFORCEMENT_MIN_BOX_HEIGHT = 0.25

# Studio composes a local Identity Sheet whenever Picture 1's own head covers
# less than this fraction of the V1 frame.  The project's primary cast picture
# is 209x600 and its head is ~11 % of a 460x642 source frame, which is exactly
# the regime where H3 kept the palette but invented a new face, age and
# wardrobe.  Above this fraction the raw Media Pool picture is passed through
# untouched.
IDENTITY_SHEET_MIN_HEAD_COVERAGE = 0.22

# Source-canvas escape hatch for the threshold above.  A picture whose head is
# already a large share of its *own* canvas, and whose subject fills almost all
# of it, is a full-body design sheet in miniature: re-laying it out costs head
# pixels and buys a layout the model renders as scene content.  Measured on the
# black-shirt Project (the only asset that has produced the "the character sheet
# is inside the scene" symptom): Picture 1 is 252x370 with own-canvas head share
# 0.2201 and subject fill 0.9626, was sheeted (frame head share 0.2144 ->
# 0.5259), and all three Relay windows reproduced the sheet border plus the
# headless lower panel at each window start (timeline 0.0 s, the 4.287 s segment
# boundary the director read as "the 4th second", and 8.5 s).  Every Mustache
# Project picture the director graded perfect sits below these two floors
# (measured own-canvas head share 0.0945, 0.1142 and 0.1442 with subject fill
# 0.688, 0.841 and 0.863), so the sheet path stays exactly as verified for the
# regime it was built for.
IDENTITY_SHEET_MIN_SOURCE_CANVAS_HEAD_COVERAGE = 0.18
IDENTITY_SHEET_MIN_SOURCE_SUBJECT_FILL = 0.55

# ---------------------------------------------------------------------------
# Round 52 — Character Swap routes (路線 1 / 路線 2 / legacy).
#
# The director's measurement that started this: a hand-built ComfyUI Relay graph
# that submits the LoRA author prompt plus a couple of sentences produces a
# better swap than the Studio, which submits the same author prompt plus a
# 9 065-character Studio appendix (11 941 characters total on the failed
# policy-84 job).  The appendix grew clause by clause, each one added after a
# failing take, and the module never re-measured the whole.  Round 52 therefore
# makes the appendix a *decision* instead of a default, and keeps the historical
# wording reachable behind one environment name so the 96 clause-wording tests
# stay meaningful:
#
#   route1  (default, 路線 1 「精準拆」) — official template verbatim plus the
#           clauses that each have a named, graded failure behind them.
#   manual  (路線 2) — the hand-built floor: author prompt, in-place/erasure
#           guards, one sheet-reading line and the authoritative silent block.
#           Selected from the Design page, default off.
#   legacy  — today's prompt, clause for clause, unchanged.
#   vanilla (路線 3) — the manual-ComfyUI parity floor.  Nothing is appended to
#           the author prompt that H3-Character-Swap-Relay-V2-api.json carries,
#           so the submitted text is byte-identical to the director's accepted
#           manual run (2 876 characters on the current template).  Round 69
#           added it after the pink-dress A/B: the accepted manual take and the
#           rejected Studio take of the same clip differ by the Studio appendix
#           alone, so the only way to grade "did the appendix help?" is a route
#           that has none.  A silent Shot is the one exception the director
#           asked to keep, because the author prompt is written for a subject
#           that speaks and its mouth sentence would otherwise contradict the
#           Shot's empty vocal channel.
#
# ``H3_CHARACTER_SWAP_ROUTE`` sets the default for every window; an explicit
# ``route=`` argument (Studio) wins over it, and an unrecognised value falls
# back to the default route rather than to the fat prompt, because the fat
# prompt is the regime the director is trying to leave.
#
# Round 69 item 8 moves the default from route1 to vanilla.  The director's
# grading of the pink-dress pair was unambiguous: the accepted manual takes and
# the rejected Studio take of the same clip differ by the Studio appendix alone,
# and only vanilla submits text that is byte-identical to the manual baseline
# (2 876 characters on the current template).  Route 1 stays one environment
# variable away — ``H3_CHARACTER_SWAP_ROUTE=route1`` restores the precise
# regime, including the apparent-age lock that vanilla does not carry.
CHARACTER_SWAP_ROUTE_ENV = "H3_CHARACTER_SWAP_ROUTE"
CHARACTER_SWAP_ROUTE_PRECISE = "route1"
CHARACTER_SWAP_ROUTE_MANUAL = "manual"
CHARACTER_SWAP_ROUTE_LEGACY = "legacy"
CHARACTER_SWAP_ROUTE_VANILLA = "vanilla"
CHARACTER_SWAP_ROUTE_DEFAULT = CHARACTER_SWAP_ROUTE_VANILLA
CHARACTER_SWAP_ROUTES = (
    CHARACTER_SWAP_ROUTE_PRECISE,
    CHARACTER_SWAP_ROUTE_MANUAL,
    CHARACTER_SWAP_ROUTE_VANILLA,
    CHARACTER_SWAP_ROUTE_LEGACY,
)
CHARACTER_SWAP_ROUTE_ALIASES = {
    "route1": CHARACTER_SWAP_ROUTE_PRECISE,
    "route-1": CHARACTER_SWAP_ROUTE_PRECISE,
    "1": CHARACTER_SWAP_ROUTE_PRECISE,
    "precise": CHARACTER_SWAP_ROUTE_PRECISE,
    "lean": CHARACTER_SWAP_ROUTE_PRECISE,
    "manual": CHARACTER_SWAP_ROUTE_MANUAL,
    "route2": CHARACTER_SWAP_ROUTE_MANUAL,
    "route-2": CHARACTER_SWAP_ROUTE_MANUAL,
    "2": CHARACTER_SWAP_ROUTE_MANUAL,
    "align": CHARACTER_SWAP_ROUTE_MANUAL,
    "vanilla": CHARACTER_SWAP_ROUTE_VANILLA,
    "official": CHARACTER_SWAP_ROUTE_VANILLA,
    "baseline": CHARACTER_SWAP_ROUTE_VANILLA,
    "parity": CHARACTER_SWAP_ROUTE_VANILLA,
    "route3": CHARACTER_SWAP_ROUTE_VANILLA,
    "route-3": CHARACTER_SWAP_ROUTE_VANILLA,
    "3": CHARACTER_SWAP_ROUTE_VANILLA,
    "legacy": CHARACTER_SWAP_ROUTE_LEGACY,
    "route0": CHARACTER_SWAP_ROUTE_LEGACY,
    "route-0": CHARACTER_SWAP_ROUTE_LEGACY,
    "0": CHARACTER_SWAP_ROUTE_LEGACY,
    "old": CHARACTER_SWAP_ROUTE_LEGACY,
}


def character_swap_route(value: Any = None) -> str:
    """Resolve the Character Swap prompt route.

    Precedence is explicit argument, then ``H3_CHARACTER_SWAP_ROUTE``, then
    ``CHARACTER_SWAP_ROUTE_DEFAULT`` (vanilla since round 69).  Blank and
    unknown values both resolve to that default: the fat legacy prompt must be
    asked for by name, so a typo in the environment cannot silently restore the
    9 000-character appendix that the director is measuring against.
    """

    raw = value if value is not None else os.environ.get(CHARACTER_SWAP_ROUTE_ENV, "")
    key = " ".join(str(raw or "").split()).casefold()
    if not key:
        return CHARACTER_SWAP_ROUTE_DEFAULT
    return CHARACTER_SWAP_ROUTE_ALIASES.get(key, CHARACTER_SWAP_ROUTE_DEFAULT)


# Round 65: whether the rebuilt head has to wear the reference's eyewear.
#
# The policy-87 take of the graded shot (project
# ``a_cartoon_character_with_a_black_shirt_and_yellow_pants_4``, master seed
# 6401000000000000001, pass seed 6759948290807294904, 0.5 MP prepared / 1.0 MP
# effective, one attempt) is the take the director called 「这一次最完美」:
# identity, wardrobe, background, plate continuity and crop all read as Picture 1,
# and the aging drift is gone.  Frames sampled at 0.5/1.5/3/4.5/6/7.5/9/10.5/12/12.6 s
# leave one residual, and it is the one Round 57 was written to fix.  Picture 1
# draws small rimless oval spectacles; the take wears nothing at all for the first
# two and a half seconds, then a pair of thick black rectangular frames — the
# erased performer's glasses in ``<Video 1>`` — from about 3 s, one lens slid down
# onto the jaw at 9 s, and grey-blue realistic irises where Picture 1 draws flat
# white with a round black pupil.  In other words ``DRAWN EYEWEAR STAYS WORN``
# bought a mandate the model could not honour, and an honoured-looking frame that
# came from the wrong picture.  The director's instruction is unambiguous:
# 「不要在画面强制放入眼镜」.
#
# So the mandate becomes a policy with three settings, and the default is the one
# the director asked for.  ``uncovered`` releases the requirement and paints the
# positive alternative instead: a bare face whose eyes are Picture 1's own.  Note
# that this is the one place where naming the object helps rather than hurts:
# Round 62's lesson (see ``LEAN_EYEWEAR_WORN`` below) is that naming a detail in a
# do-not-add list is how a detail you *want* disappears, so naming frame, lens, rim
# and temple in a sentence that asks for their absence works in the same direction
# the earlier take proved.  ``worn`` restores Round 57 verbatim, and ``neutral``
# says nothing about eyewear at all, which is the shape the manual ComfyUI run of
# the live graph uses.
CHARACTER_SWAP_EYEWEAR_ENV = "H3_CHARACTER_SWAP_EYEWEAR"
EYEWEAR_POLICY_UNCOVERED = "uncovered"
EYEWEAR_POLICY_WORN = "worn"
EYEWEAR_POLICY_NEUTRAL = "neutral"
CHARACTER_SWAP_EYEWEAR_POLICIES = (
    EYEWEAR_POLICY_UNCOVERED,
    EYEWEAR_POLICY_WORN,
    EYEWEAR_POLICY_NEUTRAL,
)
CHARACTER_SWAP_EYEWEAR_ALIASES = {
    "uncovered": EYEWEAR_POLICY_UNCOVERED,
    "bare": EYEWEAR_POLICY_UNCOVERED,
    "clean": EYEWEAR_POLICY_UNCOVERED,
    "off": EYEWEAR_POLICY_UNCOVERED,
    "drop": EYEWEAR_POLICY_UNCOVERED,
    "dropped": EYEWEAR_POLICY_UNCOVERED,
    "optional": EYEWEAR_POLICY_UNCOVERED,
    "no-glasses": EYEWEAR_POLICY_UNCOVERED,
    "noglasses": EYEWEAR_POLICY_UNCOVERED,
    "worn": EYEWEAR_POLICY_WORN,
    "wears": EYEWEAR_POLICY_WORN,
    "on": EYEWEAR_POLICY_WORN,
    "keep": EYEWEAR_POLICY_WORN,
    "must": EYEWEAR_POLICY_WORN,
    "round": EYEWEAR_POLICY_WORN,
    "neutral": EYEWEAR_POLICY_NEUTRAL,
    "as-is": EYEWEAR_POLICY_NEUTRAL,
    "asis": EYEWEAR_POLICY_NEUTRAL,
    "inherit": EYEWEAR_POLICY_NEUTRAL,
    "quiet": EYEWEAR_POLICY_NEUTRAL,
}


def character_swap_eyewear_policy(value: Any = None) -> str:
    """Resolve whether the rebuilt head is required to wear drawn eyewear.

    Precedence is explicit argument, then ``H3_CHARACTER_SWAP_EYEWEAR``, then
    ``uncovered``.  Blank and unknown values both resolve to ``uncovered``: the
    director grades a take with no glasses as perfect and a take with the wrong
    glasses as a defect, so forcing glasses is the riskier default and a typo in
    the environment must not restore it.
    """

    raw = (
        value
        if value is not None
        else os.environ.get(CHARACTER_SWAP_EYEWEAR_ENV, "")
    )
    key = " ".join(str(raw or "").split()).casefold()
    if not key:
        return EYEWEAR_POLICY_UNCOVERED
    return CHARACTER_SWAP_EYEWEAR_ALIASES.get(key, EYEWEAR_POLICY_UNCOVERED)


# The ownership sentence used to close with the mandate, so the fragment follows
# the same policy.  Each fragment is a continuation of "... headwear only if
# Picture 1 draws it{eyewear}.", so all three read as one grammatical sentence.
EYEWEAR_OWNERSHIP_FRAGMENTS = {
    EYEWEAR_POLICY_WORN: ", and the eyewear Picture 1 draws stays worn",
    EYEWEAR_POLICY_UNCOVERED: (
        ", and nothing the erased performer wore on the head survives"
    ),
    EYEWEAR_POLICY_NEUTRAL: "",
}


def eyewear_ownership_fragment(policy: str) -> str:
    return EYEWEAR_OWNERSHIP_FRAGMENTS.get(
        character_swap_eyewear_policy(policy), EYEWEAR_OWNERSHIP_FRAGMENTS[
            EYEWEAR_POLICY_UNCOVERED
        ]
    )


# Round 65: whether a spectacle belongs in the keep-list follows the same policy.
# This clause is a keep-list, and round 62's measurement is that naming a detail
# in a keep-list is what puts it on screen — which is exactly backwards for a Shot
# whose defect report is 「画面出现眼镜」.  So the bare list simply stops asking.
EYEWEAR_DETAIL_KEEP_LIST = (
    "every mark, garment edge, trim, collar, spectacle and facial-hair shape"
)
BARE_DETAIL_KEEP_LIST = (
    "every mark, garment edge, trim, collar and facial-hair shape"
)
DETAIL_KEEP_LISTS = {
    EYEWEAR_POLICY_WORN: EYEWEAR_DETAIL_KEEP_LIST,
    EYEWEAR_POLICY_UNCOVERED: BARE_DETAIL_KEEP_LIST,
    EYEWEAR_POLICY_NEUTRAL: BARE_DETAIL_KEEP_LIST,
}


def detail_keep_list(policy: Any = None) -> str:
    """The detail list a keep-clause should name for this eyewear policy."""

    return DETAIL_KEEP_LISTS.get(
        character_swap_eyewear_policy(policy), BARE_DETAIL_KEEP_LIST
    )


# Recording budgets for the two lean routes.  They are *measured*, not enforced:
# round 52 deletes the drop-rank clipping for the lean routes, so a clause can
# never silently disappear again.  The two numbers are the measured ceilings for
# the four worst compile shapes in ``working\r52_measure.py``; ``append_over_budget``
# in the audit says out loud when a compile exceeds them.  Measured appendix for
# route 1 is 2 989-4 590 characters (legacy on the same shapes: 4 954-8 760),
# and for the manual route 1 428-2 250.
CHARACTER_SWAP_LEAN_APPEND_BUDGET = 4200
CHARACTER_SWAP_MANUAL_APPEND_BUDGET = 2400

# Round 69: the styling appendix is now capped rather than merely recorded.
#
# The number above is the ceiling the clause set *measured*, and the manifest
# said so honestly every time -- but honesty is not a limit.  The compiled
# appendix kept growing clause by clause (3 764 in round 54, 4 560 in round 57,
# 4 050 on the rejected pink-dress take) because crossing the ceiling dropped
# nothing: round 52 deliberately removed the drop-rank clipping, and the only
# hard gate left was ``CHARACTER_SWAP_PROMPT_CHAR_BUDGET``, twelve times larger.
# The pink-dress A/B then put a price on that drift.  The director's accepted
# take of the same clip came from a graph that appends 0 characters, and the
# rejected Studio take of the same clip carried 4 050 -- 52 % of everything H3
# was told.  Every rejected take in that Project also contains an invented
# object (crown, cat ears, belt, honeycomb background) that no reference
# contains, and the engine's own canary says naming an object is what puts it
# on the page.
#
# So 1 200 characters is now the ceiling for the *styling* appendix -- the
# clauses that decide what the rebuilt character and scene look like.  Three
# kinds of text are exempt from the cap, counted in ``gate_chars`` and never
# dropped, because each one protects a fact the cap cannot buy back:
#
#   the target locator      -- without it the pass cannot tell which body in
#                              <Video 1> is the selected performer;
#   in-place + whole-body    -- the face-sticker failure the route exists to
#     erasure                  stop, graded from S1/S3/S5/S7 onward;
#   the silent contract      -- six GPU rounds (policies 52/71/72/73/95/96)
#                              proved an open mouth survives every other
#                              sentence, so a silent Shot keeps its authority
#                              whatever the styling budget decides.
#
# Styling clauses are dropped weakest-evidence-first, every drop is named in
# ``dropped_tail_clauses``, and the two halves are reported separately so a
# manifest can never read a shrunken appendix as a gate that stopped firing.
CHARACTER_SWAP_LEAN_STYLING_BUDGET = 1200
CHARACTER_SWAP_VANILLA_APPEND_BUDGET = 1200
#
# The order the styling clauses leave in.  It is ranked by what the director has
# graded most recently, not by clause size: the two live defects on the current
# Project are 「衣服完全不像参考图」 and 「角色老人化」, so the wardrobe and
# age clauses are the last two to go, and the visual-medium sentence is exempt
# from the cap entirely (see ``LEAN_MEDIUM``).  Everything above them is either
# restated by the official author template's own retention lines -- the crop
# paragraph, ``<Subject 2>``'s surrounding scene, and <Subject 1>'s wardrobe
# sentence -- or is a fix for a defect the de-nouned wording already retired.
CHARACTER_SWAP_LEAN_STYLING_DROP_ORDER = (
    "closeup_crop_lock",
    "plate_surface_provenance",
    "reference_sheet_reading",
    "no_invented_detail_list",
    "source_look_ownership",
    "eyewear_policy",
    "apparent_age_lock",
    "wardrobe_from_reference",
    # The medium sentence ships after the authored direction, so it is handled
    # as its own victim rather than as an entry in the ordered clause list.  It
    # is last: dropping it is what lets a compile whose exempt text alone
    # overflowed the budget report the overflow instead of hiding it.
    "final_medium_priority",
)

# Route 1 clause set.  Every string below replaces a named legacy clause and is
# only ever emitted under that legacy clause's own gate, so the route cannot
# invent a rule the verified prompt did not have.
LEAN_IN_PLACE = (
    "\n\nIN-PLACE REPLACEMENT — MANDATORY:\n"
    "Transform the selected performer in place at the same position, scale, "
    "frame-edge truncation and occlusion. Never add Picture 1 as a second person "
    "or duplicate its panels as extra standing bodies."
)
LEAN_ERASURE = (
    "\n\nWHOLE-BODY ERASURE — MANDATORY:\n"
    "Replace the whole visible silhouette, never a face sticker: rebuild face, "
    "hair, skin tone, neck, torso, arms and wardrobe from <Picture 1> on the "
    "selected <Video 1> body geometry, and leave no original face, hair, garment "
    "or ghost underneath. {identity_note}{hair}"
)
LEAN_IDENTITY_NOTE = (
    "<Picture 1> supplies identity only, never its room, background, static pose "
    "or props; the finished face must be recognisably the Picture 1 character, "
    "never the original <Video 1> actor."
)
LEAN_HAIR = (
    " The source hair, ears and any headgear belong to the erased actor."
)
# Round 94: the vanilla route now needs the same fact the other two routes get.
#
# 路線 3 submits the author template and nothing else, with exactly one documented
# exception (the silent mouth contract, because the template's own mouth sentence
# contradicts an empty vocal channel).  A suppressed plate is the second case the
# template cannot speak to: the Studio has taken the identity texture off the top of
# the source head, so "preserve the <Video 1> subject" points at a region that no
# longer exists -- and policy 71 already measured what H3 does with that gap.  Seed
# 923009999 (round 35e, policy 70) kept V1's wig and gilded headband in 13 of 16
# sampled frames *with* the halo band already covering the crown, because nothing
# told the renderer what a bald-crowned Picture 1 makes of that region.  With
# ``H3_CHARACTER_SWAP_PLATE_SUPPRESSION`` finally reaching the gate on a drawn
# reference, vanilla would otherwise ship the blur and stay silent about it: the
# exact configuration that failed in 35e.
#
# Round 69 priced naming the erased look -- the pink-dress A/B put objects on screen
# that no reference contains -- so this sentence keeps policy 71's positive fact and
# drops policy 68's inventory: no "wig", no "crown", no "cat ear", no "headband".
#
# Round 95: the first honest suppressed-plate Preview (policy 93, seed
# 3608049340227527602, 18:20) proved the sentence is needed but also proved it is
# too short.  The Hallway Project's Picture 1 is a bald man with three stray
# filaments and nothing else; the shipped takes now carry his scalp, his nose and
# his black-and-white vest, and the only surviving source feature is the hair that
# *hangs* -- the length down the sides at 4.23 s, the mass behind the head at
# 6.60 s, the spiked mane plus the plait and its tie at 11.21 s (the worst sample
# of the second unit, 0.382527).  Every one of those sits below or beside the
# identity window, which ends at y 0.5193 / y 0.5025, and "the top of the head"
# never claimed that territory.
#
# The alternative was the plate, and the plate was measured rather than assumed:
# ``H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE=blur`` does cover the hair
# (rebuild of both plates from this run's own compiled inputs, 18:36) but it smears
# 0.2043 -> 0.5316 and 0.1339 -> 0.5015 of the frame, and the figure-extent record
# comes back with ``protected_boxes: []`` -- the wardrobe band does not stop at a
# protected role, so the kept character's own body blurs with it.  The policy-81
# archive already refused that regime for the same reason (50.13 % against 11.4 %
# smeared, and the cartoon hands it cost).  So the words carry this round, and the
# appendix has room for them: 2895 + 602 leaves 1200 - 769 = 431 characters of the
# vanilla budget unspent.
#
# Naming stays inside the round-69 price list: the region is geometry ("the top of
# the head, the temples, the ears and the nape"), never ``crown`` or ``forehead``,
# and the fact is stated as what Picture 1 draws rather than as an object to remove.
LEAN_VANILLA_SOURCE_HAIR = (
    " The source hair and headgear belong to the erased actor, and the head gets"
    " exactly what Picture 1 draws there: bare scalp at the top of the head, the"
    " temples, the ears and the nape, and the same bare skin where the erased"
    " actor's hair used to fall behind the head, onto the shoulders and down the"
    " back. Picture 1's own hair decides that region, and nowhere else in the"
    " frame does a strand of the erased actor's hair survive as scene content."
)
# Round 54: the same ownership fact for the plate nobody blurred.
#
# ``LEAN_HAIR`` and the policy-68/71 ``source_hair_ownership_clause`` both speak
# only on a *suppressed* plate, because there the sentence is about a band edge
# the hair can hide behind.  路線 1 hands H3 a clean, un-blurred <Video 1>, so on
# the accepted take of ``a_cartoon_character_with_a_black_shirt_and_yellow_pants_4``
# (seed 2246500964096521702, policy 84, 800x1216, one attempt) none of that
# wording shipped at all — and the director's grade named exactly the three
# residuals the wording exists to prevent: V1's red twin-tail wig and cat ears
# sitting on top of Picture 1's bald crown, pink cosplay straps and ribbons left
# over on the body next to Picture 1's vest, and Picture 1's round glasses
# dropped.  The identity audit could not see any of it: its boxes cover
# y 15.6-28.8% of the frame, so hair colour and everything outside the face box
# are ungoverned, which is why the QC passed a take the director rejected.
#
# The clause states the positive fact rather than a negation, the same lesson
# policy 71 learned on the suppressed plate: "the wig leaves the frame" gave H3
# nothing to paint, while "that region gets exactly the crown Picture 1 draws"
# does.  Costume accessories are included because on this plate the leftovers
# were worn straps and ribbons, not hair only; held props stay, because the
# juggling oranges in V1 are scene action the performance needs.
#
# Round 69 removes the enumeration, not the rule.  The pink-dress A/B put a
# price on naming the erased look: the rejected takes each contain an invented
# object that no reference has, and the engine's own canary (see
# ``testing/test_character_swap_engine.py``, "a do-not-add list naming them is
# how they disappeared") says the noun is what puts the thing on the page.  The
# category word — "everything the performer wears on or above the body" — covers
# wig, ears, ribbons, straps and gloves without handing H3 a shopping list, and
# "the crown" becomes "the top of the head" for the same reason.  Held props
# still stay, because the juggling oranges in V1 are scene action.
LEAN_SOURCE_LOOK_OWNERSHIP = (
    "\n\nSOURCE LOOK BELONGS TO THE ERASED ACTOR — MANDATORY:\n"
    "Everything the selected <Video 1> performer wears on or above the body is "
    "part of the erased identity, not scene content, and leaves the frame; only "
    "what <Video 1> shows held in a hand stays. The top of the head gets exactly "
    "the head Picture 1 draws: bare scalp with a few stray strands where Picture 1 "
    "is bald, headwear only if Picture 1 draws it{eyewear}."
)
# Round 57: the one identity fact the policy-85 take still could not hold.
#
# The real-shot A/B against the rejected take (project
# ``a_cartoon_character_with_a_black_shirt_and_yellow_pants_4``, master seed
# 8178175072880861825, policy 85, 0.5 MP / 768 bucket, pass seed
# 2246500964096521702) retired all three residuals Round 54 was written for: the
# red twin-tail wig and cat ears are off Picture 1's bald crown, the pink cosplay
# straps and ribbons are gone, and the wardrobe reads as Picture 1's black-and-gold
# vest with the turquoise skirt.  Frames sampled at 0.5 s, 3 s, 6 s, 9 s and 12 s
# show two facts the take still gets wrong.  Picture 1's round spectacles are
# absent in 5 of 5 frames, with one orphaned temple line drifting on a cheek at
# 0.5 s -- the ownership sentence only says the eyewear "stays worn", which is a
# condition, not a picture of the thing.  The face also reads older than the
# sheet: three or four stacked forehead creases, deepened nasolabial folds, and
# spots and stubble dots scattered over a scalp Picture 1 draws as flat colour.
#
# So the eyewear sentence gets its own clause that enumerates the parts and the
# failure modes, and ``LEAN_AGE_LOCK`` names the invented marks it was actually
# caught adding instead of listing wrinkles in the abstract.
#
# Round 62 reverses the second half of that decision on the user's own
# counter-evidence.  Their manual ComfyUI run of the *same* live graph comes out
# with neither the aged face nor the invented background, and the official author
# prompt it uses never mentions wrinkles, creases, honeycombs or wallpaper: it
# only ever says what to draw.  The prompt Studio actually submitted for the same
# shot (job preview_1135366446077025740_1793450873363513200, 8 204 characters,
# kept in ``working/r62_submitted_prompt_pol84.txt``) splits cleanly: the 3 396
# author prompt carries zero ageing nouns and zero texture nouns, and the 4 806
# characters Studio appends carry 7 of each.  A do-not-add list still puts the
# object on the page, and this engine already learned that once -- see
# ``testing/test_character_swap_engine.py`` "a do-not-add list naming them is how
# they disappeared", which is why P1's round glasses went missing.  The clauses
# below therefore state the positive fact and its provenance instead of naming
# the artefact to avoid.
LEAN_EYEWEAR_WORN = (
    "\n\nDRAWN EYEWEAR STAYS WORN — MANDATORY:\n"
    "When Picture 1 draws eyewear, the rebuilt head wears it in every frame of the "
    "Shot: both lenses, the bridge over the nose and both temples to the ears, in "
    "Picture 1's own line weight and colour, and it stays worn through head turns, "
    "hand-to-face contact and mouth movement. No lens, rim or temple may float on a "
    "cheek, rest on a shoulder or sit behind the head. When Picture 1 draws no "
    "eyewear, none appears."
)
# Round 65, default: the face without anything resting on it, said as a picture.
#
# Same take as above, and ``DRAWN EYEWEAR STAYS WORN`` is why it failed.  The
# mandate asked for Picture 1's rimless ovals and the model delivered the erased
# performer's thick black rectangular frames from 3 s onward, with one lens on a
# jaw at 9 s — an eyewear fact it could only satisfy by reaching into
# ``<Video 1>``.  The director's grade is 「不要在画面强制放入眼镜」, so the
# requirement is released and replaced with the positive image of a bare face.
# Naming frame, lens, rim and temple works here for the reason the module's own
# canary states: naming an object steers what gets drawn, and this time the
# sentence asks for their absence rather than promising their presence.
LEAN_EYEWEAR_UNCOVERED = (
    "\n\nTHE FACE STAYS UNCOVERED — MANDATORY:\n"
    "Nothing rests on this face. The eyes are Picture 1's own eyes — same design, "
    "same colour, same drawing — and they meet the viewer directly, with no frame, "
    "no lens, no rim, no temple line and no eyewear shadow anywhere on the face or "
    "the scalp. Eyewear is an accessory this Shot does not require: the face is "
    "drawn complete without it, and nothing of the erased performer's eyewear "
    "survives."
)
LEAN_WARDROBE = (
    "\n\nWARDROBE FROM PICTURE 1 — MANDATORY:\n"
    "The body wears <Picture 1>'s wardrobe exactly as drawn: every garment layer, "
    "cut, length, hem, fit, pattern, trim, collar, accessory and colour blocking. "
    "No <Video 1> garment remains on or above the body; where Picture 1 omits a "
    "garment, continue its design in the same medium and palette instead of "
    "borrowing one from <Video 1>."
)
LEAN_NO_INVENTED = (
    "\n\nEVERY DETAIL COMES FROM PICTURE 1 — MANDATORY:\n"
    "Draw this character's details from Picture 1: {details} sits where Picture 1 "
    "puts it, in Picture 1's own line weight and colour."
)
LEAN_NO_TEXTURE = (
    "\n\nSURFACE PROVENANCE — MANDATORY:\n"
    "Every background surface keeps the colour, shading and detail <Video 1> "
    "already has at that position: each one stays the surface it is, with its "
    "geometry, lighting and depth of field."
)
LEAN_IDENTITY_SHEET = (
    "\n\nPICTURE 1 IS ONE IDENTITY SHEET — AUTHORITATIVE:\n"
    "<Picture 1> is one multi-panel sheet of a single character at another zoom "
    "of the same artwork, so its medium is identical in every panel. The head "
    "panel decides face, hair, skin tone and apparent age; the body and outfit "
    "panels decide proportions, wardrobe, colours and footwear. Never turn two "
    "panels into two people, and never bring the sheet's layout, borders or "
    "plain mat into the scene: render exactly one instance of that character "
    "inside <Video 1>'s framing."
)
LEAN_DESIGN_SHEET = (
    "\n\nDESIGN-SHEET READING — MANDATORY:\n"
    "Read <Picture 1> as a character design sheet, never as a crop, decal or face "
    "patch: rebuild one coherent head, neck, torso and wardrobe on the selected "
    "<Video 1> body geometry, whose head size, perspective, frame-edge truncation "
    "and camera distance decide the result."
)
LEAN_MINIMAL_SHEET = (
    "\n\n<Picture 1> is one identity sheet of a single character drawn at several "
    "zooms of the same artwork: read its panels as one person, and never "
    "reproduce the sheet's own layout, borders or mat inside the scene."
)
LEAN_CROP_LOCK = (
    "\n\nCROP LOCK — MANDATORY:\n"
    "Some panels of Picture 1 reach further down the figure than this Shot does; "
    "they are identity facts, never framing facts. Keep <Video 1>'s crop, shot "
    "scale and camera exactly: do not widen or tilt the shot, and do not draw "
    "hands, hems, shoes or scenery that <Video 1> never shows."
)
LEAN_AGE_LOCK = (
    "\n\nAPPARENT AGE LOCK — MANDATORY:\n"
    "Picture 1's face is flat colour fills bounded by clean lines, and the rebuilt "
    "head is that drawing reproduced: the same fills in the same places, the same "
    "line weight, the same eye design and the same hair shape. Keep Picture 1's "
    "face fullness, skin smoothness, jaw shape, hairline and the maturity it draws "
    "exactly — the person in <Video 1> lends this face its movement, never its face."
)
LEAN_MULTI_PERSON = (
    "\n\nMULTI-PERSON SUBJECT — AUTHORITATIVE:\n"
    "The person being replaced means these {n} selected performers taken "
    "together: {selector}. Each replaced body keeps its own position, scale, "
    "pose clock and occlusion order; the replaced bodies never merge into one "
    "person, exchange faces or swap positions."
)
LEAN_PROTECTED_CAST = (
    "\n\nPROTECTED CAST — MANDATORY:\n"
    "Modify only the selected performers. Every other visible person stays "
    "exactly as <Video 1> shows them — same face, hair, wardrobe, position and "
    "motion: {selectors}. Never move Picture 1's identity into a protected person."
)
LEAN_SILENT_SUMMARY = (
    "\n\nSILENT LISTENER — SUMMARY: this Shot's human vocal channel is empty and "
    "the replaced performer's lips stay closed for the whole Shot; the "
    "authoritative contract at the end decides mouth behaviour."
)
LEAN_PERFORMANCE_SILENT = (
    "\n\n<Video 1> supplies the replaced performer's position, scale, body pose, "
    "gestures, head turns, gaze, blinking, expression outside the mouth and "
    "complete action clock; it supplies no mouth articulation."
)
LEAN_SILENT_TAIL = (
    "\n\nSILENT LISTENER PERFORMANCE — AUTHORITATIVE: HUMAN VOCAL CHANNEL: EMPTY "
    "— this Shot has no dialogue, narration, voice-over, whisper, laugh, chant or "
    "spoken word in any language, on screen or off screen. The replaced performer "
    "keeps the lips naturally together and the jaw still, allowing only blinking, "
    "breathing, head turns and gaze shifts, and every listening reaction keeps "
    "the lips closed, with no open-mouth smile, laugh or jaw drop. The mouth is "
    "one of this frame's largest moving details, so keep the lips one relaxed "
    "closed curve and never borrow an open-mouth or smiling pose from Picture 1."
)
LEAN_MEDIUM = (
    "\n\nFINAL MEDIUM PRIORITY — MANDATORY:\n"
    "<Picture 1>'s own visual medium wins every conflict: a cartoon, anime, comic "
    "or cel-shaded reference keeps its line work, colour blocking and shading and "
    "never drifts photographic; a photographic reference stays photographic. Only "
    "<Video 1> supplies action, composition, camera movement, lighting, scene "
    "geometry and timing."
)
LEAN_MEDIUM_LIVE_ACTION = (
    "\n\nFINAL MEDIUM PRIORITY — MANDATORY:\n"
    "This pass adapts an illustrated design to live action: keep Picture 1's "
    "identity, apparent age, hairstyle, wardrobe and signature accessories, and "
    "render them photorealistically so they match <Video 1>'s photography."
)
# Route 2 keeps only what the hand-built graph cannot infer from its two inputs.
LEAN_MINIMAL_IN_PLACE = (
    "\n\nIN-PLACE REPLACEMENT — MANDATORY:\n"
    "Transform the selected performer in place at the same position, scale, "
    "frame-edge truncation and occlusion, and never add Picture 1 as a second "
    "person."
)
LEAN_MINIMAL_ERASURE = (
    "\n\nWHOLE-BODY ERASURE — MANDATORY:\n"
    "Replace the whole visible silhouette, never a face sticker: rebuild head and "
    "body from <Picture 1> and leave no original face, hair or garment "
    "underneath. {identity_note}"
)

# Hard floor for "the body now wears Picture 1's clothes".  The shift is
# ``similarity(take body region, P1 wardrobe) - similarity(V1 body region, P1
# wardrobe)``, sampled at the same stamps the identity audit already uses.  On
# the three accepted head-only takes of the black-shirt Project the medians are
# 0.053 / 0.089 / 0.114 and the best single frame in the whole run is 0.177 (a
# partial outfit patch), while the montage confirms all three keeps are P1's head
# on V1's cat-ear wig and pink/black cosplay body.  A genuine whole-body swap
# measured >= 0.20 on the same ruler, so 0.12 rejects every confirmed head-only
# take without touching a confirmed whole-body one.
CHARACTER_SWAP_MINIMUM_WARDROBE_SHIFT = 0.12

# Vertical registration of the mouth/jaw audit band inside an authored actor
# box, as (left inset, top fraction, right inset, bottom fraction).  The band
# used to live in ``smart_render_worker`` alone, which meant the Studio had no
# way to name the same strip of face the QC measures.  It lives here because it
# now drives two consumers: the Relay QC's mouth region and the Studio's silent
# plate mouth-band freeze (round 37j).  Prompt, plate and QC must be able to
# point at the same pixels or an audit can never be re-read against the frames
# it claims to have measured.
#
# Three regimes were measured on real plates; a single band cannot serve all of
# them, and an unregistered band audits the wrong anatomy in both directions.
MOUTH_BAND_REGISTRATIONS: dict[str, tuple[float, float, float, float]] = {
    # The selection spans nearly the whole frame, so the box is not a head crop
    # at all.  Measured on the S3/S10 portrait plate (372x536) with the authored
    # near-full-frame box (coverage 0.947): the performer's eyes sit at y
    # 0.30-0.38 of that box, so the default 0.25-0.47 band audited eyebrows,
    # blinks, hat band and burned-in title text.  Every Silent Listener close-up
    # then failed on motion that is normal for a character with nothing to say,
    # and the retry it triggered could not fix it.
    "frame_filling": (0.28, 0.42, 0.28, 0.60),
    # A short, near-square box is a head-only selection.  Measured on the
    # black-shirt S2 take (box [0.35,0.15,0.65,0.45], 0.30 x 0.30): the true
    # mouth sat at y 0.55-0.78, 0.63-0.87 and 0.68-0.92 of that box in segments
    # 0/1/2, while the default 0.25-0.47 band audited the forehead, the glasses
    # and the jewelled headband.  The audit was therefore reading redraw
    # boiling on the brow and calling it lip-sync, in both directions.
    "head_crop": (0.25, 0.52, 0.25, 0.88),
    # A tall box is a head-and-shoulders (or full-body) selection: the classic
    # lower-face band still registers.
    "lower_face": (0.28, 0.25, 0.28, 0.47),
}


def mouth_band_registration(value: object) -> tuple[list[float], str]:
    """Return ``(audit rectangle, registration name)`` for one actor box.

    Registering the band is the whole point: an unregistered band measures the
    wrong anatomy, and both the absolute cap and the upper-face control band
    inherit the mistake.  The name is recorded in the manifest so an audit can
    be re-read against the frames it actually measured -- and so the plate
    builder can freeze exactly the region the audit later reads.

    Verified arithmetic: authored box ``[0.35, 0.15, 0.65, 0.45]`` (0.30 x 0.30)
    registers as ``head_crop`` and yields ``[0.425, 0.306, 0.575, 0.414]``, which
    is the ``bbox_normalized`` recorded by the policy 74 manifest.
    """

    try:
        left, top, right, bottom = [float(item) for item in value][:4]
    except (TypeError, ValueError, OverflowError):
        return [], ""
    left, top = max(0.0, left), max(0.0, top)
    right, bottom = min(1.0, right), min(1.0, bottom)
    if right - left < 0.03 or bottom - top < 0.03:
        return [], ""
    width, height = right - left, bottom - top
    if width * height >= 0.70:
        registration = "frame_filling"
    elif height <= 0.50 and width / height >= 0.80:
        registration = "head_crop"
    else:
        registration = "lower_face"
    left_inset, top_fraction, right_inset, bottom_fraction = (
        MOUTH_BAND_REGISTRATIONS[registration]
    )
    return [
        left + width * left_inset,
        top + height * top_fraction,
        right - width * right_inset,
        top + height * bottom_fraction,
    ], registration


def mouth_region_bbox(value: object) -> list[float]:
    """Return a conservative mouth/jaw audit rectangle for one actor box.

    The Relay output is not a face-landmark product, so this deliberately uses a
    broad lower-face band.  It is used only for the authored Silent Listener
    contract: excessive temporal motion is a reason to try another seed, never a
    reason to stop the whole render.
    """

    return mouth_band_registration(value)[0]


# ``reference_framing`` value recorded when Relay receives a composed sheet.
IDENTITY_SHEET_FRAMING = "illustrated_identity_sheet"
FULL_DESIGN_FRAMING = "illustrated_full_design"


def character_swap_relay_window_count(duration_seconds: float) -> int:
    """Return the adaptive Relay window count for one H3 Shot pass."""

    requested = max(5, round(max(0.0, float(duration_seconds)) * RELAY_FPS))
    frame_count = requested + (
        H3_FRAME_REMAINDER - (requested % H3_FRAME_MODULUS)
    ) % H3_FRAME_MODULUS
    advance = max(1, RELAY_WINDOW_FRAMES - RELAY_HISTORY_FRAMES)
    if frame_count <= RELAY_WINDOW_FRAMES:
        return 1
    return 1 + max(
        0,
        (frame_count - RELAY_WINDOW_FRAMES + advance - 1) // advance,
    )


def automatic_remake_engine_for_skill(special_skill_key: object) -> str:
    """Return the recommended Remake Engine for the active Special Skill.

    The Studio uses this when a Skill is selected or an old Project has no saved
    engine choice. v0.3.8 keeps this recommendation but allows the user to
    override it from the toolbar.
    """

    normalized = str(special_skill_key or "").strip().casefold()
    if normalized == SOURCE_VIDEO_CAST_REMAKE_SKILL_KEY:
        return SOURCE_REMAKE_MODE_CHARACTER_SWAP
    return SOURCE_REMAKE_MODE_CREATIVE_H3


def load_character_swap_workflow(path: str | Path) -> dict[str, dict[str, Any]]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    if isinstance(payload.get("prompt"), dict):
        payload = payload["prompt"]
    if not isinstance(payload, dict):
        raise ValueError("Character Swap workflow is not an API-format object.")
    nodes = {
        str(node_id): deepcopy(node)
        for node_id, node in payload.items()
        if isinstance(node, dict) and isinstance(node.get("class_type"), str)
    }
    classes = {str(node.get("class_type", "")) for node in nodes.values()}
    common = {"LoadVideo", "LoadImage", "SaveVideo"}
    v2_required = {
        *common,
        CHARACTER_SWAP_PREPARE_CLASS,
        CHARACTER_SWAP_RELAY_CLASS,
        "MiniMaxH3ReferenceToVideo",
        "BasicScheduler",
        "CFGGuider",
        "StartLoop",
        "EndLoop",
        "H3RelayFinishWindows",
    }
    legacy_required = {
        *common,
        "PrimitiveStringMultiline",
        LEGACY_CHARACTER_SWAP_PREPARE_CLASS,
        LEGACY_CHARACTER_SWAP_RELAY_CLASS,
    }
    if not v2_required.issubset(classes) and not legacy_required.issubset(classes):
        missing_v2 = sorted(v2_required - classes)
        raise ValueError(
            "Character Swap API workflow is neither Relay V2 nor the supported "
            "legacy Relay workflow. Missing Relay V2 nodes: "
            + ", ".join(missing_v2)
        )
    return nodes


def character_swap_workflow_generation(
    workflow: Mapping[str, Mapping[str, Any]],
) -> str:
    """Return the supported Relay workflow generation for a loaded graph."""

    classes = {
        str(node.get("class_type", ""))
        for node in workflow.values()
        if isinstance(node, Mapping)
    }
    if {
        CHARACTER_SWAP_PREPARE_CLASS,
        CHARACTER_SWAP_RELAY_CLASS,
        "MiniMaxH3ReferenceToVideo",
        "StartLoop",
        "H3RelayFinishWindows",
    }.issubset(classes):
        return "v2"
    if {
        LEGACY_CHARACTER_SWAP_PREPARE_CLASS,
        LEGACY_CHARACTER_SWAP_RELAY_CLASS,
        "PrimitiveStringMultiline",
    }.issubset(classes):
        return "legacy"
    raise ValueError("Unsupported Character Swap Relay workflow generation.")


def node_id_for_class(
    workflow: Mapping[str, Mapping[str, Any]],
    class_type: str,
) -> str:
    matches = [
        str(node_id) for node_id, node in workflow.items()
        if str(node.get("class_type", "")) == class_type
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Character Swap workflow requires exactly one {class_type}; "
            f"found {len(matches)}."
        )
    return matches[0]


def _role_rows(analysis: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(row.get("role_id", "")).strip().upper(): row
        for row in analysis.get("principal_roles") or []
        if isinstance(row, Mapping) and str(row.get("role_id", "")).strip()
    }


def _normalized_person_bbox(value: object) -> list[float]:
    """Return a usable source-frame bbox and reject synthetic full-frame crops."""

    try:
        left, top, right, bottom = [float(item) for item in value][:4]
    except (TypeError, ValueError, OverflowError):
        return []
    left, top = max(0.0, left), max(0.0, top)
    right, bottom = min(1.0, right), min(1.0, bottom)
    if right <= left or bottom <= top:
        return []
    # Qwen, old Shot scans, and an early manual-box UI fallback could record a
    # nearly full-frame rectangle when localization failed. Passing that to
    # Relay makes it interpret the complete scene as the actor and commonly
    # pastes Picture 1 over the plate instead of replacing the performer.
    width, height = right - left, bottom - top
    if (
        (left <= 0.001 and top <= 0.001 and right >= 0.999 and bottom >= 0.999)
        or width * height >= 0.82
        or (width >= 0.94 and height >= 0.82)
    ):
        return []
    # A person box can never be an order of magnitude taller than it is wide.
    # S5 evidence: role R2 localized one brown background column (box
    # x=0.08-0.27, y=0.04-0.96, aspect 0.21) and that phantom sliver then
    # drove both the Relay selector and an identity-audit row over pixels that
    # contain no performer at all.  Every real tracked performer in this
    # project measures aspect 0.34 or wider, so rejecting below 0.30 removes
    # the background columns without touching a genuine standing figure.
    # Manual Shot Visual Editor boxes are exempt: they go through
    # :func:`_normalized_manual_person_bbox`.
    if width / max(1e-9, height) < 0.30:
        return []
    return [left, top, right, bottom]


def _normalized_manual_person_bbox(value: object) -> list[float]:
    """Return a valid user-authored box, including an intentional full frame.

    Automatic/Qwen detections still go through :func:`_normalized_person_bbox`
    because a synthetic full-frame result usually means localization failed.
    A rectangle saved by Shot Visual Editor is different: it is an explicit
    instruction and must never silently disappear merely because an actor is
    edge-cropped or fills most of a vertical source frame.
    """

    try:
        left, top, right, bottom = [float(item) for item in value][:4]
    except (TypeError, ValueError, OverflowError):
        return []
    left, top = max(0.0, left), max(0.0, top)
    right, bottom = min(1.0, right), min(1.0, bottom)
    if right <= left or bottom <= top:
        return []
    return [left, top, right, bottom]


def _bbox_containment_overlap(left: object, right: object) -> float:
    """Intersection divided by the smaller box area.

    This deliberately detects a duplicate narrow role nested inside a user's
    larger manual selection. IoU is unsuitable here: nested boxes can have a
    low IoU even when they describe the same on-screen performer.
    """

    first = _normalized_manual_person_bbox(left)
    second = _normalized_manual_person_bbox(right)
    if not first or not second:
        return 0.0
    intersection_width = max(0.0, min(first[2], second[2]) - max(first[0], second[0]))
    intersection_height = max(0.0, min(first[3], second[3]) - max(first[1], second[1]))
    intersection = intersection_width * intersection_height
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    return intersection / max(1e-9, min(first_area, second_area))


def _bbox_area(value: object) -> float:
    """Return the normalized frame coverage of a person box."""

    box = _normalized_manual_person_bbox(value)
    if not box:
        return 0.0
    return (box[2] - box[0]) * (box[3] - box[1])


def _median_role_coverage_area(role_pass_row: Mapping[str, Any]) -> float:
    """Return how much of the frame one source role really occupies.

    Per-sample boxes move with the performer, so the median is the honest
    central tendency: one occluded frame or one manual override must not decide
    whether a role is a foreground lead or a bystander.  Roles with no usable
    track fall back to their authored selection box.
    """

    areas = [
        _bbox_area(sample.get("bbox_normalized"))
        for sample in (role_pass_row.get("source_track_samples") or [])
        if isinstance(sample, Mapping)
    ]
    areas = [area for area in areas if area > 0.0]
    if not areas:
        return _bbox_area(role_pass_row.get("source_bbox_normalized"))
    areas.sort()
    middle = len(areas) // 2
    if len(areas) % 2:
        return areas[middle]
    return (areas[middle - 1] + areas[middle]) / 2.0


# Two automatic role tracks describing nearly the same rectangle are the same
# on-screen body, not two people.  0.80 containment is the same cut-off the
# duplicate-protection suppression already uses, so both halves of the engine
# agree on what a phantom duplicate is.
DUPLICATE_SOURCE_ROLE_OVERLAP_THRESHOLD = 0.80

# Background-extra demotion.  One Picture may legitimately be bound to several
# source bodies, and every bound role used to become a hard swap target with its
# own identity-audit row.  Measured on the single-character project
# a_cartoon_character_with_a_black_shirt_and_yellow_pants (all three segments,
# attempts_used=3): the principal R1 (median coverage 0.090, identity
# correlation -0.133/0.041/0.101) was swapped correctly, while a green-jacket
# photographer tracked at 0.030 under the same P1 kept 0.897/0.926/0.820 of the
# V1 actor.  That bystander is *supposed* to stay in shot, but it was listed as
# a second selected performer, so the prompt asked H3 to replace the small
# figure too, the QC scored the correct take as ``identity_failed`` and nine
# generations were burned on a pass that had already worked.
#
# A bound role is demoted to a protected <Subject 2> bystander when its median
# coverage is both absolutely small (under 0.045 — the 0.047 phantom column in
# the S5 note above is the same order) and at least
# ``BACKGROUND_EXTRA_PROMINENCE_RATIO`` times smaller than the largest role
# sharing its Picture.  Both conditions are required: two comparable leads must
# keep two real passes.
BACKGROUND_EXTRA_MAX_BOX_AREA = 0.045
BACKGROUND_EXTRA_PROMINENCE_RATIO = 2.0


# Scene and wardrobe locks injected into the official prompt structure.
# Appending prohibitions to the end of the prompt was proven ineffective on the
# newest verified video: S4, S6 and S8 were rendered with the tail clause
# "NO INVENTED TEXTURE OR PATTERN" already present and still came out with
# invented honeycomb/lattice backgrounds, and S1, S3, S4, S6 and S8 all failed
# the same way on clothing ("衣服完全不像参考图") because nothing bound the
# wardrobe to Picture 1's actual garment design.  H3 follows the official
# template fields, so both facts are stated inside the fields that own them:
# <Subject 2>'s retention line for the source scene, and <Subject 1>'s retention
# line for the wardrobe.  Anchors are matched defensively; if an edited author
# prompt no longer contains an anchor that lock is skipped instead of raising.
AUTHOR_PROMPT_SCENE_LOCK = (
    " Retain its background surfaces and props exactly as <Video 1> shows them: "
    "plain surfaces stay plain, and each one keeps the colour, shading and detail "
    "<Video 1> already has at that position."
)
# Round 50 shortened the enumeration here (was "wallpaper motif, dotted
# texture, embroidery or other ornamental pattern"), and round 62 removed the
# negation outright after the manual-ComfyUI A/B showed the named artefacts
# arriving in the frame: the surviving sentence is positive all the way down,
# and the marker phrase below is what the idempotency guard matches, so it
# stays word for word.
AUTHOR_PROMPT_WARDROBE_LOCK = (
    " For this character, clothing means the complete garment design shown in "
    "<Picture 1>: its cut, layers, colours, trim, footwear and held props. The "
    "source person's own clothing leaves the frame with their body, and no "
    "substitute outfit may be invented."
)
AUTHOR_PROMPT_SCENE_LOCK_ANCHOR = (
    "retain the surrounding scene and its changes over time."
)
AUTHOR_PROMPT_WARDROBE_LOCK_ANCHOR = (
    "visual style consistently as the character performs the source person's "
    "movements."
)
# Idempotency markers: each lock is inserted at most once per prompt.
AUTHOR_PROMPT_SCENE_LOCK_MARKER = "plain surfaces stay plain"
AUTHOR_PROMPT_WARDROBE_LOCK_MARKER = "no substitute outfit may be invented"
# The official author prompt also hands the transferred performance a positive
# mouth instruction: "...blinking, facial expressions, and visible mouth
# movements."  That is correct for a speaking Shot and wrong for every
# ``silent_listener`` Shot.  Round-10 GPU evidence (policy 52, seeds 97000444
# and 97000454) showed H3 lip-syncing both silent Shots while the authoritative
# SILENT LISTENER contract sat at the very end of the same prompt, so the
# contradiction is now removed at the source instead of being left to clause
# ordering.
# Round-37b GPU evidence (policy 72, seed 923010207) narrowed the leak further:
# keeping the words "facial expressions" in the silent rewrite still asked the
# model to match a plate whose performance is a wide laugh, so the lips opened
# anyway (true-mouth crops show real lip flapping in all three Segments).  The
# silent rewrite now limits the matched performance to the upper face only.
AUTHOR_PROMPT_MOUTH_SPEAKER_TEXT = "visible mouth movements"
AUTHOR_PROMPT_MOUTH_SILENT_ANCHOR = (
    "blinking, facial expressions, and visible mouth movements."
)
AUTHOR_PROMPT_MOUTH_SILENT_REPLACEMENT = (
    "blinking, brow and eye expression only, and a relaxed closed mouth with the "
    "jaw still."
)
# Round-37b: the reference portrait itself is the remaining trigger.  P1 in the
# black-shirt project is drawn mid-laugh with teeth and tongue showing, and both
# silent reinforcement clauses used to tell the model that Picture 1's open mouth
# was "one static expression to copy" — an instruction to copy an open mouth, in
# direct contradiction of the SILENT LISTENER contract ("no open-mouth smile,
# laugh or jaw drop").  The clause is now an explicit anti-copy instruction, and
# it is shared verbatim by the close-up and medium-shot reinforcements so the
# two can never drift apart again.
SILENT_MOUTH_REFERENCE_PORTRAIT_CLAUSE = (
    "Picture 1 may itself be drawn mid-laugh with an open mouth: copy that "
    "Picture's identity, not its mouth. Draw the same face with the lips gently "
    "together in every frame, and never let the lips open or change shape from "
    "frame to frame."
)
# Round-37f: the mouth sentence was only one of the affirmative instructions the
# official template hands a silent pass.  Reading the prompt authored inside
# H3-Character-Swap-Relay-V2-api.json directly, a silent pass still read
# (a) "<Subject 1> ... whose performance comes from the person being replaced",
# (b) "transferring their complete visible performance", (c) "identity through
# every expression", (d) "clothing move naturally with the transferred
# performance" and (e) "Retain the source clip's existing sound ...", the last
# of which hands the model a soundtrack containing speech and lets it attribute
# that speech to the visible character.  GPU evidence for the same Shot (policies
# 71-73, seeds 923010107 / 923010207 / 923010307) graded real lip flapping in
# every Segment with the authoritative SILENT LISTENER contract, both mouth
# reinforcements, the rewritten mouth sentence and the plate silent clause all
# present, so the prohibition side is saturated: the only lever left is the
# affirmative side.
#
# The five sentences are therefore rewritten in place — nothing is appended, so
# no field grows a new paragraph and the clause ordering cannot drift.  Each
# rewrite carries its own marker and is skipped when that marker is already
# present, which keeps a recompiled pass or a replayed Job idempotent.  Length
# was the binding constraint, not wording.  The heaviest silent pass this project
# compiles (SHEET_CLOSEUP_SPEC, the S8/S9-class silent identity-sheet close-up)
# is unbudgeted at 12 956 against the 12 320 proven-submittable ceiling, and the
# length guard already sacrifices exactly one clause there — the rank-1
# close-up silent reinforcement, which the guard removes for 636 characters and
# which was present in every take that still lip-synced.  Four of the five
# rewrites therefore cost 12 characters net (the "every expression" anchor
# shrinks by 15 and the "complete visible performance" anchor by 4), which keeps
# that pass at 12 318 with the same single drop instead of forcing the guard to
# eat rank 3 as well and lose SOURCE COSTUME BELONGS TO THE ERASED ACTOR.  The
# measured margin is thin, not comfortable: that drop buys 638 characters against
# a 636 shortfall, so the spec had 14 characters spare before this table and has 2
# after it — a further silent addition of three characters on the same spec makes
# the guard eat rank 3 too.  That is why this table is measured rather than
# written, and why
# test_silent_performance_rewrites_stay_inside_the_measured_length_slack rebuilds
# the same pass with the table switched off and compares, instead of pinning a
# number that would go stale.  The wording also avoids bare "performance" wherever the
# sentence is about the body.  retention_analysis' "...as the character performs
# the source person's movements." is deliberately left alone: it says movements
# rather than mouth, and the wardrobe lock is inserted immediately after it, so
# rewriting it would silently drop AUTHOR_PROMPT_WARDROBE_LOCK.
#
# Round-37n changed the fifth rewrite from "the speech is off screen" to a
# declaration that the Shot has no human voice at all.  Reading the prompt the
# endpoint actually received for seed 923010507 (working\_r37m_prompt_full.txt)
# the words speech / speaker / audible / voice / audio appear five times, and
# every one of them is *affirmative*: "the speech is off screen", "<Video 1>'s
# audible speech keeps pulling the lips open", "not the audible speaker",
# "Every audible voice in this Shot ... is background sound".  Those sentences
# were written to suppress the mouth, but they all tell the model that the Shot
# contains audible speech, which is the one thing a jointly-generating audio
# branch needs to produce lips that move.  The GPU evidence supports that
# reading rather than lip-sync: the submitted silent plate has no audio track at
# all, the take's own audio is digital silence (-91 dB) because the workflow
# muxes the plate, and the mouth energy sits at 2.5-8 Hz with negative
# cross-correlation against V1's speech envelope, so the take is not tracking
# V1's voice -- it is articulating on its own.  This project already proved the
# opposite phrasing for its audio-only passes (smart_render_worker builds
# "HUMAN VOCAL CHANNEL: EMPTY ... no human voice" and that pass comes back
# speech-free, see test_native_audio_engine's empty-vocal-channel test), so the
# silent swap prompt now says the same thing instead of naming a speech that
# must stay off screen.  Wording elsewhere keeps "human vocal channel", never
# "human voice", so the marker below stays unique.
AUTHOR_PROMPT_SILENT_PERFORMANCE_REWRITES: tuple[tuple[str, str, str], ...] = (
    (
        "and whose performance comes from the person being replaced in "
        "<Video 1>.",
        "and whose body performance comes from the person being replaced in "
        "<Video 1>.",
        "whose body performance comes",
    ),
    (
        "transferring their complete visible performance to the reference "
        "character",
        "transferring their visible body performance to the reference character",
        "their visible body performance",
    ),
    (
        "Maintain the reference character's identity through every expression "
        "and viewing angle.",
        "Maintain the reference character's identity through every viewing angle.",
        "identity through every viewing angle",
    ),
    (
        "Hair and clothing move naturally with the transferred performance.",
        "Hair and clothing move naturally with the transferred body motion.",
        "with the transferred body motion",
    ),
    (
        "Retain the source clip's existing sound without adding new dialogue "
        "or sound effects.",
        "Retain the source clip's existing ambience and sound effects; the Shot "
        "has no human voice.",
        "the Shot has no human voice",
    ),
)


def _author_prompt_with_silent_mouth(prompt: str) -> str:
    """Rewrite the author prompt's affirmative performance language for a silent pass.

    The official template is written for a Shot whose subject speaks, so beyond
    its mouth sentence it still promises a complete visible performance, every
    expression, and a soundtrack the visible character appears to own.  Anchors
    are matched defensively: an edited author prompt that no longer carries one
    is left as it is instead of raising, and every rewrite is idempotent so a
    recompiled pass or a replayed Job cannot stack the same sentence twice.
    """

    silent = prompt
    if (
        AUTHOR_PROMPT_MOUTH_SILENT_ANCHOR in silent
        and AUTHOR_PROMPT_MOUTH_SILENT_REPLACEMENT not in silent
    ):
        silent = silent.replace(
            AUTHOR_PROMPT_MOUTH_SILENT_ANCHOR,
            AUTHOR_PROMPT_MOUTH_SILENT_REPLACEMENT,
        )
    for anchor, replacement, marker in AUTHOR_PROMPT_SILENT_PERFORMANCE_REWRITES:
        if marker in silent or anchor not in silent:
            continue
        silent = silent.replace(anchor, replacement)
    return silent


def _author_prompt_with_locks(
    prompt: str, *, silent_mouth: bool = False, locks: bool = True
) -> str:
    """Insert the scene and wardrobe locks into the official prompt fields."""

    locked = (
        _author_prompt_with_silent_mouth(prompt) if silent_mouth else prompt
    )
    if not locks:
        # 路線 3 hands back the author prompt exactly as the graph carries it.
        # Both locks below are Studio sentences sitting inside the official
        # template's own fields, and the pink-dress A/B graded the accepted
        # manual take -- which has neither -- above the Studio take that had
        # both, so the parity route has to be able to switch them off as a pair
        # rather than only as part of the whole appendix.
        return locked
    for anchor, lock, marker in (
        (
            AUTHOR_PROMPT_SCENE_LOCK_ANCHOR,
            AUTHOR_PROMPT_SCENE_LOCK,
            AUTHOR_PROMPT_SCENE_LOCK_MARKER,
        ),
        (
            AUTHOR_PROMPT_WARDROBE_LOCK_ANCHOR,
            AUTHOR_PROMPT_WARDROBE_LOCK,
            AUTHOR_PROMPT_WARDROBE_LOCK_MARKER,
        ),
    ):
        if marker in locked:
            continue
        index = locked.find(anchor)
        if index < 0:
            continue
        insert_at = index + len(anchor)
        locked = locked[:insert_at] + lock + locked[insert_at:]
    return locked


def character_swap_prompt_source_name(
    workflow_name: str | None = None,
    environ: dict[str, str] | None = None,
) -> str:
    """Which authored-prompt graph to harvest the swap prompt out of.

    Default (Round 122) follows whatever ``character_swap_workflow_name`` decides to
    submit, because the director edits the prompt *in that file*: harvesting some other
    file re-inserts clauses he deleted by hand.  ``H3_CHARACTER_SWAP_PROMPT_SOURCE``
    overrides with ``api`` / a literal file name for the pre-Round-122 behaviour.  A
    hand-named or selected file that is not on disk falls back to the api graph -- a
    missing harvest source must never refuse a Shot.
    """

    source = os.environ if environ is None else environ
    requested = str(source.get(CHARACTER_SWAP_PROMPT_SOURCE_ENV, "") or "").strip()
    if requested and requested.casefold() not in CHARACTER_SWAP_PROMPT_SOURCE_FOLLOW_VALUES:
        candidate = requested
    else:
        candidate = str(workflow_name or character_swap_workflow_name(source) or "").strip()
    here = Path(__file__).resolve()
    if candidate and (here.with_name(candidate).is_file() or Path(candidate).is_file()):
        return candidate
    return CHARACTER_SWAP_WORKFLOW_NAME


def _relay_v2_author_prompt(
    *, silent_mouth: bool = False, locks: bool = True
) -> str:
    """Load the Character-Swap prompt authored in the user's V2 API graph."""

    source = Path(character_swap_prompt_source_name()).resolve()
    try:
        workflow = json.loads(source.read_text(encoding="utf-8-sig"))
        rows = [
            node for node in workflow.values()
            if isinstance(node, Mapping)
            and node.get("class_type") == "MiniMaxH3ReferenceToVideo"
        ]
        if len(rows) == 1:
            prompt = str(rows[0].get("inputs", {}).get("prompt", "")).strip()
            if prompt:
                return _author_prompt_with_locks(
                    prompt, silent_mouth=silent_mouth, locks=locks
                )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return _author_prompt_with_locks(
        "Replace the person in <Video 1> with the character shown in <Picture 1>. "
        "Picture 1 supplies appearance only. Video 1 supplies composition, camera, "
        "performance timing and the surrounding scene. Preserve the source scene and "
        "replace the complete visible source performer.",
        silent_mouth=silent_mouth,
        locks=locks,
    )


def character_swap_passes_for_window(
    analysis: Mapping[str, Any],
    bindings: Iterable[Mapping[str, Any]],
    start_seconds: float,
    end_seconds: float,
    *,
    selected_role_ids: Iterable[str] | None = None,
    source_bbox_overrides: Mapping[str, object] | None = None,
) -> list[dict[str, Any]]:
    """Return one ordered character-swap pass per visible, mapped V1 role."""

    selected_roles = {
        str(role or "").strip().upper()
        for role in (selected_role_ids or [])
        if str(role or "").strip()
    }
    bbox_overrides = {
        str(role or "").strip().upper(): _normalized_manual_person_bbox(value)
        for role, value in (source_bbox_overrides or {}).items()
        if str(role or "").strip()
    }
    bbox_overrides = {
        role: bbox for role, bbox in bbox_overrides.items() if bbox
    }

    scenes: list[Mapping[str, Any]] = []
    for scene in analysis.get("scenes") or []:
        if not isinstance(scene, Mapping):
            continue
        try:
            left = float(scene.get("start_seconds", 0.0) or 0.0)
            right = float(scene.get("end_seconds", left) or left)
        except (TypeError, ValueError, OverflowError):
            continue
        if left < end_seconds - 1e-9 and right > start_seconds + 1e-9:
            scenes.append(scene)
    scene_indexes = {
        int(scene.get("scene_index", 0) or 0) for scene in scenes
    }
    visible_roles: list[str] = []
    speaker_roles: set[str] = set()
    events_by_role: dict[str, list[str]] = {}
    for scene in scenes:
        speaker = str(scene.get("speaker_role", "") or "").strip().upper()
        if speaker:
            speaker_roles.add(speaker)
        visible_event = " ".join(str(scene.get("visible_event", "") or "").split())
        for role in scene.get("active_source_roles") or []:
            normalized = str(role or "").strip().upper()
            if not normalized:
                continue
            if normalized not in visible_roles:
                visible_roles.append(normalized)
            if visible_event:
                events_by_role.setdefault(normalized, []).append(visible_event)
    # Keep the complete cast before applying the user's SWAP subset.  The old
    # code filtered first and then called a selected actor "the only existing
    # foreground person".  In a two-person frame that instruction authorizes
    # H3 to absorb or redraw the listener and is a major source of cross-role
    # interference.
    all_visible_roles = list(visible_roles)
    if selected_roles:
        visible_roles = [role for role in visible_roles if role in selected_roles]
    sole_visible_role = len(all_visible_roles) == 1

    # Resolve the cast one Scene at a time.  A Shot-level flag — a replacement to a
    # Picture, or KEEP V1 to keep the original performer — carries the Scene indexes
    # of the Shot it was set on, so it may only speak for those Scenes.  Keeping the
    # V1 performer in one Shot never meant cancelling the replacement for the other
    # Shots that happen to share this render window, and only a flag that names no
    # Scene at all is broad enough to cover the whole window.
    role_visible_scenes: dict[str, list[int]] = {}
    for scene in scenes:
        try:
            scene_index = int(scene.get("scene_index", 0) or 0)
        except (TypeError, ValueError, OverflowError):
            scene_index = 0
        for role in scene.get("active_source_roles") or []:
            normalized = str(role or "").strip().upper()
            if not normalized:
                continue
            buckets = role_visible_scenes.setdefault(normalized, [])
            if scene_index not in buckets:
                buckets.append(scene_index)

    keep_v1_roles: set[str] = set()
    keep_v1_everywhere: set[str] = set()
    keep_v1_scenes: dict[str, set[int]] = {}
    swap_rows: dict[str, list[tuple[str, set[int]]]] = {}
    for binding in bindings:
        if not isinstance(binding, Mapping):
            continue
        role = str(binding.get("source_role_id", "") or "").strip().upper()
        target = str(binding.get("target_media_id", "") or "").strip().upper()
        indexes = {
            int(value) for value in binding.get("scene_indexes") or []
            if isinstance(value, (int, float))
        }
        keep_v1 = bool(binding.get("source_thumbnail", False)) or (
            target == KEEP_V1_TARGET
        )
        if keep_v1:
            if role in all_visible_roles and (
                not indexes or bool(indexes & scene_indexes)
            ):
                # The role keeps its V1 face somewhere inside this window, so the
                # prompt must still protect that performer even when another Scene
                # of the same window maps the role to a Picture.
                keep_v1_roles.add(role)
                if not indexes:
                    # A row that names no Scene is broad enough to speak for the
                    # whole window, so the role gets no swap pass at all.
                    keep_v1_everywhere.add(role)
                # Otherwise KEEP V1 is authoritative only for the Scenes it names.
                # It must never be materialized as a P Picture or compiled into a
                # LoRA pass in those Scenes.
                keep_v1_scenes.setdefault(role, set()).update(
                    indexes & scene_indexes
                )
            continue
        if (
            role in visible_roles
            and target.startswith("P")
            and (not indexes or bool(indexes & scene_indexes))
        ):
            swap_rows.setdefault(role, []).append(
                (target, set() if not indexes else indexes & scene_indexes)
            )

    mapped: dict[str, str] = {}
    for role, visible_scenes in role_visible_scenes.items():
        if role in keep_v1_everywhere:
            # A Scene-less KEEP V1 row covers every Scene of the window.
            continue
        rows = swap_rows.get(role) or []
        forced_v1 = keep_v1_scenes.get(role, set())
        for scene_index in visible_scenes:
            if scene_index in forced_v1:
                continue
            for target, covered_scenes in rows:
                if covered_scenes and scene_index not in covered_scenes:
                    continue
                mapped.setdefault(role, target)
                break
            if role in mapped:
                break

    roles = _role_rows(analysis)
    role_passes: list[dict[str, Any]] = []
    for role in visible_roles:
        target = mapped.get(role, "")
        if not target:
            continue
        evidence = roles.get(role, {})
        track_samples: list[dict[str, Any]] = []
        rejected_full_frame_track = False
        for track in evidence.get("shot_scan_tracks") or []:
            if not isinstance(track, Mapping):
                continue
            for sample in track.get("samples") or []:
                if not isinstance(sample, Mapping):
                    continue
                try:
                    sample_time = float(sample.get("time_seconds", 0.0) or 0.0)
                except (TypeError, ValueError, OverflowError):
                    continue
                if sample_time < start_seconds - 0.25 or sample_time > end_seconds + 0.25:
                    continue
                raw_bbox = sample.get("bbox_normalized") or []
                bbox_values = _normalized_person_bbox(raw_bbox)
                if not bbox_values:
                    try:
                        raw_values = [float(value) for value in raw_bbox][:4]
                    except (TypeError, ValueError, OverflowError):
                        raw_values = []
                    rejected_full_frame_track = rejected_full_frame_track or (
                        raw_values == [0.0, 0.0, 1.0, 1.0]
                    )
                    continue
                track_samples.append({
                    "frame_index": int(sample.get("frame_index", 0) or 0),
                    "time_seconds": sample_time,
                    "frame_span_explicit": (
                        sample.get("first_frame_index") is not None
                        and sample.get("last_frame_index") is not None
                    ),
                    "first_frame_index": int(
                        sample.get("first_frame_index", sample.get("frame_index", 0))
                        or 0
                    ),
                    "last_frame_index": int(
                        sample.get("last_frame_index", sample.get("frame_index", 0))
                        or 0
                    ),
                    "bbox_normalized": bbox_values,
                })
        track_samples.sort(key=lambda row: row["time_seconds"])
        if len(track_samples) > 6:
            positions = {
                round(index * (len(track_samples) - 1) / 5)
                for index in range(6)
            }
            track_samples = [track_samples[index] for index in sorted(positions)]
        scene_bbox: list[float] = []
        for appearance in evidence.get("appearance_evidence") or []:
            if not isinstance(appearance, Mapping):
                continue
            try:
                appearance_scene = int(appearance.get("scene_index", 0) or 0)
            except (TypeError, ValueError, OverflowError):
                continue
            if appearance_scene not in scene_indexes:
                continue
            scene_bbox = _normalized_person_bbox(
                appearance.get("thumbnail_bbox_normalized") or []
            )
            if scene_bbox:
                break
        if not scene_bbox:
            scene_bbox = _normalized_person_bbox(
                evidence.get("thumbnail_bbox_normalized") or []
            )
        source_bbox = (
            list(track_samples[0]["bbox_normalized"])
            if track_samples else ([] if sole_visible_role else scene_bbox)
        )
        identity_audit_bbox = (
            list(track_samples[0]["bbox_normalized"])
            if track_samples else list(scene_bbox)
        )
        if role in bbox_overrides:
            # Shot Visual Editor owns the explicit manual rectangle. Remove
            # older Qwen geometry from the prompt so it cannot compete with
            # the box the user deliberately placed on this Shot. Preserve the
            # frame/time spans, however: an internal hard cut may show R2 and
            # R1 consecutively rather than simultaneously, and the compositor
            # needs those spans to avoid applying both identity passes to the
            # same frame.
            source_bbox = list(bbox_overrides[role])
            identity_audit_bbox = list(bbox_overrides[role])
            track_samples = [
                {**dict(sample), "bbox_normalized": list(bbox_overrides[role])}
                for sample in track_samples
            ]
        edge_truncated = bool(rejected_full_frame_track)
        for bbox in [source_bbox, *[
            row.get("bbox_normalized") or [] for row in track_samples
        ]]:
            if len(bbox) == 4:
                edge_truncated = edge_truncated or (
                    float(bbox[0]) <= 0.015 or float(bbox[1]) <= 0.015
                    or float(bbox[2]) >= 0.985 or float(bbox[3]) >= 0.985
                )
        role_passes.append({
            "source_role_id": role,
            "target_media_id": target,
            "source_visual_identity": " ".join(
                str(evidence.get("visual_identity", "") or "").split()
            ),
            "source_wardrobe": " ".join(
                str(evidence.get("wardrobe", "") or "").split()
            ),
            "source_narrative_function": " ".join(
                str(evidence.get("narrative_function", "") or "").split()
            ),
            "source_bbox_normalized": source_bbox,
            "identity_audit_bbox_normalized": identity_audit_bbox,
            # Round 101: the identity-suppression halo has to know who drew this
            # rectangle.  A hand box is authored *below* the hair line on purpose --
            # the halo is what reaches the hair -- while an auto-contour box already
            # sits on the hair line, so the same upward reach puts a band of bare
            # background over the crown and H3 fills it with headwear (round 100's
            # pentagram cap, 8.5-12.1 s).  The plate shortens the reach for
            # ``auto_contour`` boxes only; a missing key is treated as a hand box,
            # which is the shipped behaviour, so merging and older ledgers stay put.
            "source_bbox_provenance": (
                "manual_shot_override"
                if role in bbox_overrides
                else "auto_contour"
            ),
            "source_track_samples": track_samples,
            "source_is_sole_visible_person": sole_visible_role,
            "source_edge_truncated": edge_truncated,
            "source_events": list(dict.fromkeys(events_by_role.get(role, [])))[:4],
            "scene_indexes": sorted(scene_indexes),
            "speaker": role in speaker_roles,
        })

    # A bound role is not automatically a person to replace.  When one Picture
    # is mapped onto several source bodies, every bound role used to become a
    # hard swap target: the prompt demanded that the small figure be replaced
    # too, and the identity audit scored one retained V1 bystander as a failed
    # swap even when the principal performer had already been replaced
    # correctly.  Demote the demoted-prominence extras into the protected
    # <Subject 2> cast, which is exactly the official grammar for "the other
    # people in the scene".  An explicit Shot selection is authoritative, so a
    # deliberately clicked role is kept as a pass and only made advisory for
    # the QC instead.
    demoted_background_role_ids: set[str] = set()
    advisory_extra_role_ids: list[str] = []
    demoted_background_rows: list[dict[str, Any]] = []
    if len(role_passes) > 1:
        coverage_by_role = {
            str(row["source_role_id"]): _median_role_coverage_area(row)
            for row in role_passes
        }
        rows_by_target: dict[str, list[dict[str, Any]]] = {}
        for row in role_passes:
            rows_by_target.setdefault(
                str(row["target_media_id"]), []
            ).append(row)
        kept_passes: list[dict[str, Any]] = []
        for row in role_passes:
            role_id = str(row["source_role_id"])
            area = coverage_by_role.get(role_id, 0.0)
            largest_other = max(
                (
                    coverage_by_role.get(str(other["source_role_id"]), 0.0)
                    for other in rows_by_target[str(row["target_media_id"])]
                    if other is not row
                ),
                default=0.0,
            )
            background_extra = bool(
                0.0 < area < BACKGROUND_EXTRA_MAX_BOX_AREA
                and largest_other >= area * BACKGROUND_EXTRA_PROMINENCE_RATIO
            )
            if not background_extra or bool(row.get("speaker")):
                kept_passes.append(row)
                continue
            if role_id in selected_roles:
                advisory_extra_role_ids.append(role_id)
                kept_passes.append(row)
                continue
            demoted_background_role_ids.add(role_id)
            demoted_background_rows.append({
                "source_role_id": role_id,
                "target_media_id": str(row["target_media_id"]),
                "source_visual_identity": str(
                    row.get("source_visual_identity", "") or ""
                ),
                "source_bbox_normalized": list(
                    row.get("source_bbox_normalized") or []
                ),
                "coverage_area": round(area, 6),
                "largest_same_target_coverage_area": round(largest_other, 6),
                "reason": (
                    "same Picture is already carried by a far more prominent "
                    "source performer - kept as a protected bystander"
                ),
            })
        role_passes = kept_passes
        keep_v1_roles.update(demoted_background_role_ids)

    # A single P Picture is one requested identity, even when the user assigns
    # it to several source bodies. Running a complete Relay generation once per
    # role made duplicate mappings both prohibitively slow and destructive:
    # later passes could redraw a replacement already established by an earlier
    # pass. Group those roles into one explicit multi-person identity pass.
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in role_passes:
        target = str(row["target_media_id"])
        if target not in grouped:
            grouped[target] = {
                "source_role_id": "",
                "source_role_ids": [],
                "source_roles": [],
                "merged_duplicate_source_roles": [],
                "target_media_id": target,
                "source_events": [],
                "scene_indexes": sorted(scene_indexes),
                "speaker": False,
            }
            order.append(target)
        group = grouped[target]
        role_row = {
            key: row.get(key)
            for key in (
                "source_role_id", "source_visual_identity", "source_wardrobe",
                "source_narrative_function", "source_bbox_normalized",
                "source_bbox_provenance",
                "identity_audit_bbox_normalized",
                "source_track_samples", "source_is_sole_visible_person",
                "source_edge_truncated",
            )
        }
        # One visible body must never be described as two performers.  Automatic
        # tracking regularly produces a duplicate role nested inside the
        # performer the user actually selected (S10 evidence: R1 coverage 0.947
        # and R2 coverage 0.906 are the same man under the same Picture, with
        # no explicit Shot selection).  Left unresolved, the prompt asserted
        # that "these 2 selected source performers ... never merge into one
        # person", doubled every per-role clause, pushed the prompt to 11 911
        # characters so the silent-mouth and plate-texture clauses had to be
        # deleted, and scored the same pixels twice in the QC audit.
        duplicate_index: int | None = None
        duplicate_overlap = 0.0
        for index, existing in enumerate(group["source_roles"]):
            overlap = _bbox_containment_overlap(
                existing.get("source_bbox_normalized") or [],
                role_row.get("source_bbox_normalized") or [],
            )
            if overlap >= DUPLICATE_SOURCE_ROLE_OVERLAP_THRESHOLD:
                duplicate_index = index
                duplicate_overlap = overlap
                break
        if duplicate_index is None:
            group["source_role_ids"].append(row["source_role_id"])
            group["source_roles"].append(role_row)
        else:
            existing = group["source_roles"][duplicate_index]
            kept = str(existing.get("source_role_id", ""))
            dropped = str(role_row.get("source_role_id", ""))
            if _bbox_area(role_row.get("source_bbox_normalized")) > _bbox_area(
                existing.get("source_bbox_normalized")
            ):
                group["source_roles"][duplicate_index] = role_row
                group["source_role_ids"][duplicate_index] = role_row["source_role_id"]
                kept, dropped = dropped, kept
            group["merged_duplicate_source_roles"].append({
                "source_role_id": dropped,
                "kept_source_role_id": kept,
                "duplicate_overlap": round(duplicate_overlap, 6),
                "reason": (
                    "duplicate automatic track covering the same source body - "
                    "kept the larger selection box"
                ),
            })
        group["source_events"] = list(dict.fromkeys(
            [*group["source_events"], *row.get("source_events", [])]
        ))[:6]
        group["speaker"] = bool(group["speaker"] or row.get("speaker"))
    def protected_role_row(role_id: str) -> dict[str, Any]:
        evidence = roles.get(role_id, {})
        source_bbox = list(bbox_overrides.get(role_id) or [])
        if not source_bbox:
            for track in evidence.get("shot_scan_tracks") or []:
                if not isinstance(track, Mapping):
                    continue
                for sample in track.get("samples") or []:
                    if not isinstance(sample, Mapping):
                        continue
                    try:
                        sample_time = float(sample.get("time_seconds", 0.0) or 0.0)
                    except (TypeError, ValueError, OverflowError):
                        continue
                    if (
                        sample_time >= start_seconds - 0.25
                        and sample_time <= end_seconds + 0.25
                    ):
                        source_bbox = _normalized_person_bbox(
                            sample.get("bbox_normalized") or []
                        )
                        if source_bbox:
                            break
                if source_bbox:
                    break
        if not source_bbox:
            for appearance in evidence.get("appearance_evidence") or []:
                if not isinstance(appearance, Mapping):
                    continue
                try:
                    appearance_scene = int(appearance.get("scene_index", 0) or 0)
                except (TypeError, ValueError, OverflowError):
                    continue
                if appearance_scene not in scene_indexes:
                    continue
                source_bbox = _normalized_person_bbox(
                    appearance.get("thumbnail_bbox_normalized") or []
                )
                if source_bbox:
                    break
        if not source_bbox:
            source_bbox = _normalized_person_bbox(
                evidence.get("thumbnail_bbox_normalized") or []
            )
        return {
            "source_role_id": role_id,
            "source_visual_identity": " ".join(
                str(evidence.get("visual_identity", "") or "").split()
            ),
            "source_bbox_normalized": source_bbox,
            "keep_v1": role_id in keep_v1_roles,
            "background_extra": role_id in demoted_background_role_ids,
        }

    protection_rows = {
        role_id: protected_role_row(role_id) for role_id in all_visible_roles
    }
    result = [grouped[target] for target in order]
    for row in result:
        row["source_role_id"] = "+".join(row["source_role_ids"])
        # A collapsed duplicate is not somebody to preserve: it is the same body
        # that this pass already owns.  Keeping its id in the target set stops
        # the phantom from reappearing as a "do not replace" instruction.
        target_roles = {
            *row["source_role_ids"],
            *(
                str(merged.get("source_role_id", ""))
                for merged in row.get("merged_duplicate_source_roles") or []
                if isinstance(merged, Mapping)
            ),
        }
        target_bboxes = [
            role_row.get("source_bbox_normalized") or []
            for role_row in row.get("source_roles") or []
            if isinstance(role_row, Mapping)
        ]
        protected_rows: list[dict[str, Any]] = []
        suppressed_duplicates: list[dict[str, Any]] = []
        for role_id in all_visible_roles:
            if role_id in target_roles:
                continue
            protected = protection_rows[role_id]
            protected_bbox = protected.get("source_bbox_normalized") or []
            overlap = max(
                (
                    _bbox_containment_overlap(target_bbox, protected_bbox)
                    for target_bbox in target_bboxes
                ),
                default=0.0,
            )
            # Only an explicit Shot selection authorizes duplicate suppression.
            # With no selected subset, overlapping roles may be real people and
            # retain the conservative protection behaviour.
            if selected_roles and overlap >= 0.80:
                suppressed_duplicates.append({
                    **protected,
                    "duplicate_overlap": round(overlap, 6),
                    "reason": "nested duplicate of explicitly selected source role",
                })
                continue
            protected_rows.append(protected)
        row["protected_source_roles"] = protected_rows
        row["suppressed_duplicate_source_roles"] = suppressed_duplicates
        row["demoted_background_source_roles"] = [
            dict(item) for item in demoted_background_rows
        ]
        row["qc_advisory_source_role_ids"] = list(advisory_extra_role_ids)
    # Replace non-speakers first. The final pass owns the visible speaking
    # face(s), so it receives the cleanest source-audio/mouth alignment.
    result.sort(key=lambda row: (
        bool(row.get("speaker")),
        min(visible_roles.index(role) for role in row["source_role_ids"]),
    ))
    # Name each pass's position in its own window.  Two consumers read this:
    # ``build_character_swap_prompt`` only drops the "a later pass may already
    # have replaced a protected person" sentence when the window is provably
    # one pass, which it cannot know unless the plan stamps ``pass_total``;
    # without the stamp the sentence was paid on every single-pass Shot, and
    # the two hair clauses added with policy 68 need that room.  The manifest
    # audit also gains the ordering it was previously inferring from
    # ``pass_index`` in the Studio's own loop.  Stamped after the sort so the
    # index means "order the passes actually run in".
    for pass_index, row in enumerate(result):
        row["pass_index"] = pass_index
        row["pass_total"] = len(result)
    return result


# ---------------------------------------------------------------------------
# Round 105 -- a cast Picture that is not a human being.
#
# Measured on the newest run of ``example/godzilla_action_figure_by_neca_6``
# (policy 100, manifest ``preview_411399206549878986_1794160031403257100``):
# two swap passes in one Segment, both graded by the product's own identity
# audit as ``head_layer_only: true`` / ``passed: false``.  Pass R1 -> P2 came
# back ``target_reference_similarity`` 0.346 with ``wardrobe_shift`` -0.0140
# against the 0.12 floor of ``CHARACTER_SWAP_MINIMUM_WARDROBE_SHIFT``; pass
# R2 -> P1 came back 0.404 with ``target_likeness_score`` 0.019 while
# ``retention_score`` held 0.754 -- the source performer survived -- and
# ``wardrobe_shift`` -0.0376.  The frames say the same thing: in the wide shots
# the left role became a Gundam while the right role stayed the black-haired
# boy for the whole clip, and in the close-up stretch (~3.5-7.5 s) BOTH roles
# reverted to the source characters, i.e. the take flickers between the figure
# and the human mid-clip.
#
# The reason is in the words the model was handed.  The beat-scoped cast lock
# ``design_engine.py`` authors (lines 3171-3178) says, of a kaiju figure,
# "Preserve @P1's exact recognizable face, apparent age, hair, skin tone, body
# proportions, complete wardrobe, footwear and accessories.  Never blend, swap,
# duplicate, redraw or transfer this identity."  The copy stored in the project
# is even cut mid-sentence ("... duplicate, r.").  The model obeyed it: it
# repainted a head and kept the human wardrobe, which is exactly what
# ``head_layer_only`` measures.  What a figure needs is the opposite sentence,
# so this round scans the Project's own words for the noun, deletes the human
# lock from the compiled prompt and says the figure's own material instead.
# ---------------------------------------------------------------------------

# Whole-word body-kind nouns that mean "this Picture is not a human being".
#
# ``figure`` / ``toy`` / ``statue`` / ``model`` / ``doll`` are deliberately
# absent.  They describe an *object*, and they sit inside ordinary captions of
# human cast -- the Godzilla picture's own caption is "godzilla action figure
# by neca", where "figure" carries no information a human cast picture would
# not also carry.  Counting them would arm the non-human lock on human swaps
# and take away the wardrobe sentence that verified human passes depend on.
# Same reasoning ``smart_render_worker.SAM31_NON_HUMAN_NOUNS`` already applies
# to SAM3.1's phrase.  Body-kind words only: they name what is standing in the
# frame, not how the picture was made.
CHARACTER_SWAP_NONHUMAN_NOUNS: tuple[str, ...] = (
    "godzilla", "kong", "kaiju", "gundam", "evangelion", "mecha", "mech",
    "robot", "android", "cyborg", "monster", "creature", "beast", "alien",
    "dinosaur", "raptor", "dragon", "wyvern", "zombie", "skeleton", "ghost",
    "spirit", "werewolf", "vampire", "demon", "devil", "orc", "goblin",
    "troll", "giant", "cat", "dog", "puppy", "horse", "wolf", "fox", "panda",
    "tiger", "lion", "bear", "rabbit", "monkey", "ape", "gorilla", "elephant",
    "deer", "unicorn", "pegasus", "serpent", "snake", "crocodile", "shark",
)

# Same ceiling ``director_cut_studio._sam31_target_recognition_text`` and
# ``smart_render_worker.SAM31_TARGET_RECOGNITION_MAX_CHARS`` put on the caption
# text, so the two consumers read one bounded string.
CHARACTER_SWAP_NONHUMAN_TEXT_MAX_CHARS = 4000
# Four nouns is what one Picture can be in a caption before the clause stops
# being about one body (the gundam caption repeats one noun twenty-one times).
CHARACTER_SWAP_NONHUMAN_MAX_NOUNS = 4
# The pass-spec keys this module reads, in priority order.  Studio measures the
# caption once and hands the nouns down on the pass spec
# (``director_cut_studio`` writes ``nonhuman_target`` /
# ``nonhuman_target_nouns``); the recognition-like keys are the fallback for a
# Job built by an older Studio, and the ``source_*`` fields are never read here
# because they describe the erased performer, who is a human by definition.
CHARACTER_SWAP_NONHUMAN_NOUNS_KEY = "nonhuman_target_nouns"
CHARACTER_SWAP_NONHUMAN_RECOGNITION_KEYS: tuple[str, ...] = (
    "sam31_target_recognition",
    "target_recognition",
    "reference_recognition",
    "recognition",
    "semantic_enrichment",
    "caption",
    "clip_prompt",
)

# The clause is a tail reinforcement on routes whose appendix is already
# measured against ``CHARACTER_SWAP_PROMPT_CHAR_BUDGET`` (12 320), so it pays
# for itself: 414 characters on the worst four-noun wording this module can
# emit, which is why the builder below clamps the noun list instead of letting
# the sentence grow.
CHARACTER_SWAP_NONHUMAN_CAST_LOCK_MAX_CHARS = 420
CHARACTER_SWAP_NONHUMAN_CAST_LOCK_MARKER = "nonhuman cast lock"

_NONHUMAN_NOUN_PATTERN = re.compile(
    # Whole-word only, so ``spirit`` in "high spirits" and ``giant`` in
    # "giantswarm" stay out.  Alternation order matters: ``mecha`` is listed
    # before ``mech`` so the longer noun wins at the same offset.
    r"\b(" + "|".join(CHARACTER_SWAP_NONHUMAN_NOUNS) + r")\b",
    re.IGNORECASE,
)

# The human-preservation lock, as it actually reaches a compiled prompt.  Both
# spellings of the subject reference occur in this Project (the design plan
# writes ``@P1``, the assembled brief writes ``<Picture 1>``), and the stored
# copy is cut mid-sentence, so three shapes are covered:
#   1. the full pair of sentences ``design_engine.py:3171-3178`` authors;
#   2. the "Never blend, swap, duplicate, ..." sentence complete ("... redraw
#      or transfer this identity.") or truncated ("... duplicate, r." -- the
#      exact string the project brief of this run carries);
#   3. the same lock cut off inside its own first sentence, which happens when
#      the brief is character-capped mid-word.
# ``[^.]`` can never cross a full stop, so no pattern here can eat past the
# lock into the "Do not introduce this role outside its assigned event
# interval." sentence, which stays: it is a timing rule, not a human rule.
CHARACTER_SWAP_HUMAN_CAST_LOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"Preserve\s+[^.]{0,80}?exact\s+recogni[sz]able\s+face"
        r"[^.]{0,200}?accessories\s*\.",
        re.IGNORECASE,
    ),
    re.compile(
        r"Never\s+blend\s*,\s*swap\s*,\s*duplicate\s*,?\s*[^.]{0,48}\.?",
        re.IGNORECASE,
    ),
    re.compile(
        r"Preserve\s+[^.]{0,80}?exact\s+recogni[sz]able\s+face[^.]{0,200}$",
        re.IGNORECASE,
    ),
)


def _character_swap_nonhuman_text(value: Any) -> str:
    """Join whatever caption text ``value`` carries, bounded and whitespace-clean.

    Accepts the three shapes this Project actually stores recognition in: a
    plain string, a dict with ``recognition`` / ``semantic_enrichment`` /
    ``caption``, or an asset-like object exposing the same attributes (the
    shape ``director_cut_studio._sam31_target_recognition_text`` reads).
    Anything else -- a list, an int, an object with no such attributes --
    degenerates to the empty string instead of raising, because this decides a
    prompt clause and must never take a render down.
    """

    if value is None:
        return ""
    if isinstance(value, str):
        fields: tuple[Any, ...] = (value,)
    elif isinstance(value, Mapping):
        fields = (
            value.get("recognition"),
            value.get("semantic_enrichment"),
            value.get("caption"),
        )
    else:
        fields = (
            getattr(value, "recognition", ""),
            getattr(value, "semantic_enrichment", ""),
            getattr(value, "caption", ""),
        )
    try:
        text = " ".join(
            str(field) for field in fields if field is not None and str(field).strip()
        )
    except Exception:
        # A field whose ``__str__`` raises is junk, not a fact about the cast.
        return ""
    return " ".join(text.split())[:CHARACTER_SWAP_NONHUMAN_TEXT_MAX_CHARS]


def character_swap_nonhuman_nouns(text: Any) -> list[str]:
    """Return the non-human body nouns this Picture's own words name.

    First-seen order, deduplicated, lower-cased, at most
    ``CHARACTER_SWAP_NONHUMAN_MAX_NOUNS`` entries, and ``[]`` for junk or an
    empty caption.  neca_6's two cast pictures are the whole reason this
    exists: P1's recognition reads "BLIP · Overview: godzilla action figure by
    neca" and P2's "BLIP · Overview: a gundam gundam ...", which yield
    ``["godzilla"]`` and ``["gundam"]``.
    """

    joined = _character_swap_nonhuman_text(text)
    if not joined:
        return []
    names: list[str] = []
    for match in _NONHUMAN_NOUN_PATTERN.finditer(joined):
        noun = match.group(1).casefold()
        if noun in names:
            continue
        names.append(noun)
        if len(names) >= CHARACTER_SWAP_NONHUMAN_MAX_NOUNS:
            break
    return names


def _character_swap_nonhuman_name_list(value: Any) -> list[str]:
    """Normalise a *noun list* (as opposed to caption text) into canonical nouns.

    ``nonhuman_target_nouns`` is written by Studio from this module's own scan,
    so a well-formed list round-trips.  Entries that are not nouns of the body
    (a stray sentence, an empty string, a number) are scanned rather than
    trusted, and junk drops out.
    """

    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        names: list[str] = []
        for row in value:
            for noun in character_swap_nonhuman_nouns(row):
                if noun not in names:
                    names.append(noun)
            if len(names) >= CHARACTER_SWAP_NONHUMAN_MAX_NOUNS:
                break
        return names[:CHARACTER_SWAP_NONHUMAN_MAX_NOUNS]
    return character_swap_nonhuman_nouns(value)


def character_swap_nonhuman_cast_lock_clause(nouns: list[str]) -> str:
    """The sentence that replaces the human-preservation lock, or ``""``.

    The clause has to do three jobs at once, all of them measured on the run
    quoted at the top of this section: give the figure its own material in
    place of the human's face/hair/skin/wardrobe (that is what
    ``wardrobe_shift`` -0.0140 / -0.0376 were missing), refuse the human's
    clothes and face out loud, and keep the *stability* half of the lock it
    replaces -- the 02:08 take reverted to both source characters during the
    close-up stretch at ~3.5-7.5 s, so "never flicker back" is not decoration.
    The noun list is clamped so the sentence never exceeds
    ``CHARACTER_SWAP_NONHUMAN_CAST_LOCK_MAX_CHARS``.
    """

    names = _character_swap_nonhuman_name_list(nouns)
    if not names:
        return ""
    clause = (
        "NONHUMAN CAST LOCK \u2014 AUTHORITATIVE: {names} is not human: the figure's "
        "own moulded material, silhouette, proportions and scale replace the source "
        "performer's face, hair, skin, wardrobe, footwear and accessories. Keep no "
        "human clothes, hair or skin and no human face where this figure's head "
        "belongs; hold that one figure for the whole clip, never flickering back to "
        "the source performer."
    )
    while len(names) > 1:
        candidate = clause.format(names=", ".join(names))
        if len(candidate) <= CHARACTER_SWAP_NONHUMAN_CAST_LOCK_MAX_CHARS:
            return candidate
        names.pop()
    return clause.format(names=", ".join(names))


def character_swap_nonhuman_cast_lock_rewrite(prompt: str, nouns: list[str]) -> str:
    """Replace the human cast lock with the figure lock in a compiled prompt.

    Never raises.  Removes whatever shape of the human lock is present (the
    full sentence ``design_engine.py`` authors, or the truncated copy this
    Project stores), then appends the figure clause exactly once -- including
    when nothing matched, because on route 3 the swap prompt never carried the
    human sentence in the first place and still needs the figure sentence.
    Whitespace is only tidied where a removal actually happened, so an
    untouched prompt comes back byte-identical.
    """

    try:
        text = prompt if isinstance(prompt, str) else str(prompt or "")
    except Exception:
        return ""
    try:
        clause = character_swap_nonhuman_cast_lock_clause(nouns)
    except Exception:
        return text
    if not clause:
        return text
    cleaned = text
    removed = 0
    try:
        for pattern in CHARACTER_SWAP_HUMAN_CAST_LOCK_PATTERNS:
            cleaned, hits = pattern.subn("", cleaned)
            removed += hits
    except Exception:
        return text
    if removed:
        # The removals sit between two spaces or at a paragraph head, so only
        # the seams need closing: doubled spaces, trailing spaces on a line and
        # a space after a line break.  Paragraph breaks themselves are kept.
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"[ \t]+(\n)", r"\1", cleaned)
        cleaned = re.sub(r"(\n)[ \t]+", r"\1", cleaned)
        cleaned = re.sub(r" {2,}\.", ".", cleaned)
        cleaned = cleaned.strip()
    if CHARACTER_SWAP_NONHUMAN_CAST_LOCK_MARKER in cleaned.casefold():
        # Idempotent: applying the rewrite twice must not pay for the clause
        # twice, and a prompt that already says it needs no second copy.
        return cleaned
    return f"{cleaned}\n\n{clause}" if cleaned else clause


def _character_swap_nonhuman_pass_spec_nouns(pass_spec: Any) -> list[str]:
    """The nouns this pass's replacement Picture is described by, or ``[]``."""

    if not isinstance(pass_spec, Mapping):
        return []
    names = _character_swap_nonhuman_name_list(
        pass_spec.get(CHARACTER_SWAP_NONHUMAN_NOUNS_KEY)
    )
    if names:
        return names
    parts: list[str] = []
    for key in CHARACTER_SWAP_NONHUMAN_RECOGNITION_KEYS:
        part = _character_swap_nonhuman_text(pass_spec.get(key))
        if part:
            parts.append(part)
    return character_swap_nonhuman_nouns(" ".join(parts))


def _character_swap_nonhuman_cast_lock_pass(
    pass_spec: Any,
    prompt: str,
    prompt_audit: dict[str, Any] | None,
) -> str:
    """Apply the round-105 rewrite to a finished prompt on every return path.

    Armed only by a true ``nonhuman_target`` on the pass spec plus at least one
    noun, so a human swap is never touched.  The rewrite is recorded, never
    swallowed silently: the audit dict names the nouns that fired and the net
    characters the appendix gained -- the figure clause minus whatever human
    sentence it deleted, so a route that carried no human sentence shows the
    whole clause as the cost -- and it gains those keys only on a pass that
    really rewrote, so the pinned per-route audit key sets of a human Job do not
    move.
    """

    try:
        armed = bool(
            isinstance(pass_spec, Mapping)
            and pass_spec.get("nonhuman_target", False)
        )
    except Exception:
        armed = False
    if not armed:
        return prompt
    nouns = _character_swap_nonhuman_pass_spec_nouns(pass_spec)
    if not nouns:
        return prompt
    rewritten = character_swap_nonhuman_cast_lock_rewrite(prompt, nouns)
    if prompt_audit is not None:
        try:
            prompt_audit["nonhuman_cast_lock_nouns"] = list(nouns)
            # Net growth of the appendix, so a manifest can subtract it and
            # still compare against the 12 320 / 1 200 / 2 400 / 4 200 numbers
            # every route report.
            prompt_audit["nonhuman_cast_lock_chars"] = len(rewritten) - len(prompt)
        except TypeError:
            pass
    return rewritten


def build_character_swap_prompt(
    pass_spec: Mapping[str, Any],
    *,
    directed_scene_text: str = "",
    live_action_adaptation: bool = False,
    prompt_audit: dict[str, Any] | None = None,
    route: str | None = None,
    eyewear_policy: str | None = None,
) -> str:
    role = str(pass_spec.get("source_role_id", "") or "").strip().upper()
    source_roles = [
        row for row in pass_spec.get("source_roles") or []
        if isinstance(row, Mapping)
    ]
    if not source_roles:
        source_roles = [{
            "source_role_id": role,
            "source_visual_identity": pass_spec.get("source_visual_identity", ""),
            "source_wardrobe": pass_spec.get("source_wardrobe", ""),
            "source_narrative_function": pass_spec.get("source_narrative_function", ""),
            "source_bbox_normalized": pass_spec.get("source_bbox_normalized", []),
            "source_track_samples": pass_spec.get("source_track_samples", []),
            "source_is_sole_visible_person": pass_spec.get(
                "source_is_sole_visible_person", False
            ),
            "source_edge_truncated": pass_spec.get("source_edge_truncated", False),
        }]
    events = [
        str(value).strip()
        for value in pass_spec.get("source_events") or []
        if str(value).strip()
    ]
    performance_mode = str(
        pass_spec.get("performance_mode", "") or ""
    ).strip().casefold()
    mouth_behavior = " ".join(
        str(pass_spec.get("mouth_behavior", "") or "").split()
    )
    silent_performance = performance_mode in {"silent_listener", "no_human_voice"}
    # Round 52: the route decides how much of the Studio appendix ships.  It is
    # resolved once, here, and every route branch below reads the same value.
    route = character_swap_route(route)
    # Round 65: likewise the eyewear policy, so the ownership sentence, the
    # keep-list and the dedicated clause can never disagree with each other.
    eyewear = character_swap_eyewear_policy(eyewear_policy)
    # Whether an eyewear clause actually reached the appendix, recorded in the
    # audit so ``neutral`` is distinguishable from a gate that stopped firing.
    eyewear_clause_shipped = False

    selectors: list[str] = []
    for source_role in source_roles:
        source_role_id = str(source_role.get("source_role_id", "") or "").strip().upper()
        function = " ".join(str(source_role.get("source_narrative_function", "") or "").split())
        sole_visible = bool(source_role.get("source_is_sole_visible_person", False))
        edge_truncated = bool(source_role.get("source_edge_truncated", False))
        bbox = source_role.get("source_bbox_normalized") or []
        location = ""
        if len(bbox) == 4:
            try:
                x1, y1, x2, y2 = (float(value) for value in bbox)
                location = (
                    f"source-frame box x={round(x1 * 100)}-{round(x2 * 100)}%, "
                    f"y={round(y1 * 100)}-{round(y2 * 100)}%"
                )
            except (TypeError, ValueError):
                location = ""
        track_anchors: list[str] = []
        for sample in source_role.get("source_track_samples") or []:
            if not isinstance(sample, Mapping):
                continue
            sample_bbox = sample.get("bbox_normalized") or []
            if len(sample_bbox) != 4:
                continue
            try:
                time_seconds = float(sample.get("time_seconds", 0.0) or 0.0)
                x1, y1, x2, y2 = (float(value) for value in sample_bbox)
            except (TypeError, ValueError, OverflowError):
                continue
            track_anchors.append(
                f"{time_seconds:.3f}s box x={round(x1 * 100)}-{round(x2 * 100)}%, "
                f"y={round(y1 * 100)}-{round(y2 * 100)}%"
            )
        tracking = (
            "tracked anchors " + " | ".join(track_anchors[:6])
            if track_anchors else ""
        )
        source_position = (
            "the only existing physical foreground performer in Video 1"
            if sole_visible else ""
        )
        crop_state = (
            "intentionally cropped by the source frame edge"
            if edge_truncated else ""
        )
        description = ", ".join(part for part in (
            # Source appearance and wardrobe identify the actor we are trying
            # to erase. Repeating them in the positive target sentence teaches
            # Relay to preserve the V1 face/clothes and can completely overpower
            # Picture 1. Locate the body only by role, function and geometry.
            source_position, function, crop_state,
            location, tracking,
        ) if part)
        selectors.append(f"{source_role_id}: {description}" if description else source_role_id)
    selector = "; ".join(selectors) or f"the source performer tracked as {role}"
    # Qwen's original V1 event may say that this actor is speaking. A later
    # Shot Visual Editor override is authoritative, so never leak that stale
    # evidence back into a Silent Listener Relay prompt.
    event_selector = "" if silent_performance else " ".join(events[:2])
    directed = " ".join(str(directed_scene_text or "").split())
    # Close-up face anchoring: when the selected performer's head is a strong
    # identity cue in this Shot, H3 over-conditions on the source plate's face
    # texture and keeps the original actor's face and hair while swapping only
    # the wardrobe.  Two geometry regimes are covered, mirroring the
    # identity-suppression blur gate in director_cut_studio: a face-filling
    # close-up box (wide and tall) or a tall narrow standing person whose head
    # sits at the top of a frame-height box.
    _anchor_role_boxes: list[tuple[float, float]] = []
    for source_role in source_roles:
        bbox = source_role.get("source_bbox_normalized") or []
        if len(bbox) != 4:
            continue
        try:
            x1, y1, x2, y2 = (float(value) for value in bbox)
        except (TypeError, ValueError):
            continue
        _anchor_role_boxes.append((max(0.0, x2 - x1), max(0.0, y2 - y1)))
    close_up_event_text = " ".join(events).casefold()
    face_dominant_closeup = bool(
        any(width >= 0.55 and height >= 0.65 for width, height in _anchor_role_boxes)
        or any(height >= 0.75 and width <= 0.45 for width, height in _anchor_role_boxes)
    )
    close_up_face_anchor = (
        "\n\nCLOSE-UP FACE ANCHORING — MANDATORY:\n"
        "The selected performer's face is a strong identity cue in this Shot. "
        "Rebuild that face entirely from Picture 1's design sheet: same facial "
        "structure, skin tone, eyes, nose, mouth, moustache or beard design, "
        "hairstyle and hair colour as Picture 1. The source plate supplies only "
        "head position, pose, motion, framing, lighting direction and camera "
        "distance; its own face, skin texture, hairstyle and hair colour belong "
        "to the original actor being erased, not to facts to preserve. Never "
        "blend the two faces into a third person, and never keep the source "
        "actor's hair or face under Picture 1's design."
    ) if (
        "close-up" in close_up_event_text
        or "close up" in close_up_event_text
        or face_dominant_closeup
    ) else ""
    # Close-up medium reinforcement: in face-filling Shots H3 drifts toward a
    # photographic rendering even when Picture 1 is an illustrated design, so
    # the generic FINAL MEDIUM PRIORITY sentence alone does not hold.  The
    # clause fires only for non-live-action passes where the close-up anchor
    # already identifies the face as a strong identity cue; live-action
    # adaptation keeps its own explicit medium contract instead.
    close_up_medium_reinforcement = (
        "\n\nCLOSE-UP MEDIUM REINFORCEMENT — AUTHORITATIVE:\n"
        "Because the selected performer fills most of this frame, do not let any "
        "part of them drift toward a photographic or live-action rendering. "
        "Rebuild the entire visible character — head, neck, torso, arms and "
        "hands — in exactly Picture 1's own visual medium: keep its line work, "
        "shading style, colour blocking, eye design and facial-hair design from "
        "the design sheet at the same rendering fidelity: its skin is unbroken flat "
        "colour bounded by clean lines, and the rebuilt skin is drawn the same way."
    ) if (face_dominant_closeup and not live_action_adaptation) else ""
    # Plate/texture preservation: when a large part of the frame is re-synthesised
    # (dominant close-ups), H3 invents repeating decorative patterns that exist
    # neither in Video 1 nor in Picture 1.  Fire only where a sizeable plate is
    # actually visible and being redrawn; small-box Shots keep their prompt lean.
    # Round 62: the clause no longer names the patterns.  The manual run that
    # never mentions them never grows them either, and the black-shirt S2 take
    # grew its lattice with this clause already on the page, so naming them was
    # paying rent for nothing.
    _plate_box_areas = [width * height for width, height in _anchor_role_boxes]
    plate_texture_contract = (
        "\n\nSURFACE PROVENANCE — MANDATORY:\n"
        "Every surface in this Shot keeps the colour, shading and detail that "
        "<Video 1> already has at that position, including the walls, fabric and "
        "props around the character. Where <Video 1> shows a plain wall or an "
        "unbroken floor, the result shows that same surface with its real geometry, "
        "lighting and depth of field."
    ) if any(area >= PLATE_TEXTURE_CONTRACT_MIN_BOX_AREA for area in _plate_box_areas) else ""
    # Extreme close-up silent mouth: the generic Silent Listener contract is not
    # enough when the mouth is one of the largest moving details in frame — H3
    # parts the lips anyway.  Reinforce it
    # for face-filling Shots so the closed-lip direction lands at prompt tail,
    # directly ahead of the final Silent Listener contract re-append.
    close_up_silent_mouth = (
        "\n\nEXTREME CLOSE-UP SILENT MOUTH — SHOT-SCALE REMINDER:\n"
        "In this Shot the selected performer's mouth is one of the largest moving "
        "details in the entire frame, so the Shot's empty human vocal channel is "
        "the only reason it may stay still. Keep the replaced lips visibly closed for the whole "
        "Shot and the mouth line a single relaxed closed curve; the authoritative "
        "SILENT LISTENER contract below is the deciding word. "
        + SILENT_MOUTH_REFERENCE_PORTRAIT_CLAUSE
    ) if (silent_performance and face_dominant_closeup) else ""
    # Medium-shot silent mouth: S2-type Shots — the character's face and mouth are
    # clearly visible but the box is not a face-filling close-up, so only the
    # generic Silent Listener contract applies.  preview_980000001 showed that is
    # not enough: H3 still parts the lips
    # (result_motion 0.191 > max).  Reinforce at prompt tail exactly like the
    # extreme close-up clause; the gate excludes face-filling boxes, so the two
    # clauses never fire for the same pass.
    _medium_shot_visible = any(
        width * height >= SILENT_REINFORCEMENT_MIN_BOX_AREA
        and height >= SILENT_REINFORCEMENT_MIN_BOX_HEIGHT
        for width, height in _anchor_role_boxes
    )
    medium_shot_silent_mouth = (
        "\n\nMEDIUM-SHOT SILENT MOUTH REINFORCEMENT — SHOT-SCALE REMINDER:\n"
        "In this Shot the selected performer is a Silent Listener whose face and "
        "mouth are clearly visible, so the Shot's empty human vocal channel is the "
        "only reason the mouth may stay still. Keep the replaced lips visibly closed for the whole Shot "
        "and the mouth line a single relaxed closed curve; the authoritative "
        "SILENT LISTENER contract below is the deciding word. "
        + SILENT_MOUTH_REFERENCE_PORTRAIT_CLAUSE
    ) if (
        silent_performance and not face_dominant_closeup and _medium_shot_visible
    ) else ""
    # Plate clauses must describe the plate the model actually receives.  The
    # Studio now reports the real suppression geometry in the pass spec, because
    # guessing from the strategy name silently lost the clause exactly where it
    # mattered most: round 13 seeds 97000554/97000564/97000574 (S3/S10/S6) blurred
    # 62 % of a near-full-frame box — head, neck, shoulders and chest — and carried
    # no plate clause whatsoever, since the clause used to fire only for the
    # medium-silent strategy name.  H3 was handed an unexplained smudge over the
    # whole upper body and reconstructed an age (grey-haired "old man", 20-60 %
    # likeness) and a costume (gold medallions, fantasy robe) from its colour
    # distribution.  Head-only plates (the medium-silent band, and the multi-role
    # head-band variant) keep the short face wording; a band that reaches the
    # torso gets the wording below, which is also the only place that settles what
    # the unreadable chest means for the wardrobe.
    _suppression_strategy = str(pass_spec.get("identity_suppression_strategy") or "")
    _suppression_geometry = pass_spec.get("identity_suppression_geometry")
    if not isinstance(_suppression_geometry, Mapping):
        _suppression_geometry = {}
    _suppression_bands = [
        band
        for band in (_suppression_geometry.get("bands") or [])
        if isinstance(band, Mapping)
    ]
    _head_band_bottom = 0.0
    for _band in _suppression_bands:
        if str(_band.get("kind") or "") != "head":
            continue
        try:
            _band_bottom = float(_band.get("top") or 0.0) + float(
                _band.get("height") or 0.0
            )
        except (TypeError, ValueError):
            continue
        _head_band_bottom = max(_head_band_bottom, _band_bottom)
    suppressed_plate = bool(_suppression_bands) or (
        "_identity_suppressed" in _suppression_strategy
    )
    # Who owns the hair.  The Studio's suppression band is a rectangle around the
    # selected face, and on a cosplayer the hair sits outside that rectangle: the
    # black-shirt plate carries a pink twin-tail wig with cat ears spanning
    # x 0.15-0.85 / y 0.03-0.75 while the saved R1 box (0.35,0.15,0.65,0.45) stops
    # under it.  Seed 3395346299780713753 graded exactly that split — the head came
    # out as Picture 1, the wig stayed in every frame, because nothing had told H3
    # the wig belonged to the erased actor rather than to the scene.  Policy 68
    # widens the band over that hair (``_hair_halo_band_box``) and pays for the
    # same fact in words.  The clause only speaks on a suppressed plate: an intact
    # plate has no band whose edge the hair can hide behind, and this can keep the
    # wording off the un-gated Shot classes that measured 12 245 characters with
    # one rank-1 drop and no room to spare.
    # Policy 71 adds the half that was missing.  Policy 68's wording said the wig
    # "leaves the frame" and Picture 1 "decides that region", which is a transfer
    # of ownership without a stated fact to render: seed 923009999 (round 35e,
    # policy 70) still carried V1's cat-ear wig and gilded headband in 13 of 16
    # sampled frames even though the halo band covered the crown, because H3 was
    # never told what a bald-crowned Picture 1 makes of that region.  The sentence
    # below states the positive fact instead — bare scalp where Picture 1 shows
    # bare scalp, and headwear only where Picture 1 itself draws it — so the
    # renderer has something to paint rather than something to negate.
    source_hair_ownership_clause = (
        " The source actor's wig, hair extensions, hairpiece, animal ears and "
        "headgear are part of the erased identity, not scene content: they leave "
        "the frame, and Picture 1's own hair decides that region. That region "
        "gets exactly the crown Picture 1 shows: where Picture 1's crown is bald "
        "or holds only a few stray strands, it is bare scalp, and no wig volume, "
        "animal-ear silhouette, headband, hair tie or extension may survive there. "
        "Headwear appears only where Picture 1 itself draws it."
    ) if suppressed_plate else ""
    if not _head_band_bottom:
        # Jobs built before policy 56 carry no geometry.  Only the single-role
        # dominant gate ever blurred past the head there, so classify from the
        # strategy name and keep every other variant on the head wording.
        _head_band_bottom = (
            0.62
            if (
                "dominant_closeup" in _suppression_strategy
                and "head_band" not in _suppression_strategy
            )
            else 0.0
        )
    _torso_band_blurred = _head_band_bottom >= PLATE_TORSO_BAND_BOTTOM
    # The plate mask decides how the suppressed window ends at its border.  A
    # feathered alpha window (policy 58) has no hard rectangle to describe, and
    # naming one anyway teaches the model an artefact it cannot see; the mode
    # must come from the geometry the Studio actually baked into the plate.
    plate_edge_wording = (
        "its soft feathered window is a tool artefact rather than scene "
        "content"
        if str(_suppression_geometry.get("mask_mode") or "").strip().lower()
        == "feather"
        else "its hard rectangular edges are a tool artefact rather than scene "
        "content"
    )
    plate_face_blurred_clause = (
        "\n\nSOURCE PLATE FACE BLURRED — AUTHORITATIVE:\n"
        "The selected performer's head region in <Video 1> is intentionally "
        "blurred to hide the original actor's identity. Do not restore, "
        "sharpen or guess that blurred face from memory; it belongs to the "
        "erased original actor and must never reappear as a sharper face "
        "underneath Picture 1. Use only its silhouette for head position, "
        "pose and motion, and rebuild the entire visible head and face from "
        "Picture 1's design sheet."
    ) if (suppressed_plate and not _torso_band_blurred) else ""
    plate_torso_blurred_clause = (
        "\n\nSOURCE PLATE HEAD AND TORSO BLURRED — AUTHORITATIVE:\n"
        "The selected performer in <Video 1> is blurred from the crown into the "
        "chest: hair, face, neck, collar and torso are one unresolved smudge, and "
        + plate_edge_wording
        + ". Read that smudge for placement only — position, scale, pose, "
        "motion, drape and lighting. It decides nothing about identity: never "
        "infer apparent age, face, skin texture, hair colour or hairline from the "
        "colours inside the blur. Where the plate is soft, Picture 1 decides the "
        "whole wardrobe — collar type, sleeve length, layering, closures, trims, "
        "colours and pattern. The colour mass inside the band is the source "
        "actor's costume, not a fact to preserve: rebuild no cross-collar wrap, "
        "diagonal sash, wide belt or robe hem out of that colour mass."
    ) if (
        suppressed_plate
        and _torso_band_blurred
        and "wardrobe" not in _suppression_strategy
    ) else ""
    # Same mechanism for the wardrobe band the Studio may suppress under the
    # head region (S4 evidence: a blurred garment keeps its shape and average
    # colour, so the source robe sash reappeared over Picture 1's shirt on two
    # different seeds).  The clause only fires when that band really exists, and
    # it must describe the plate the model actually sees: the desaturating mode
    # hands over a grey template, while the chroma-preserving blur keeps the
    # source garment's colours but resolves none of its seams.  Seed 97000334
    # showed the grey wording is counterproductive when the chroma survives, so
    # the two modes get separate clauses keyed by the plate's own strategy name.
    plate_wardrobe_blurred_clause = ""
    if "wardrobe_blur_suppressed" in _suppression_strategy:
        plate_wardrobe_blurred_clause = (
            "\n\nSOURCE PLATE WARDROBE BLURRED — AUTHORITATIVE:\n"
            "The selected performer's torso region in <Video 1> is deliberately "
            "softened: its average colours stay readable while every collar line, "
            "seam, layer edge and drape line is unresolved. Read that surviving "
            "colour as Picture 1's palette under this lighting, never as the "
            "source actor's outfit. Because the plate decides nothing about "
            "construction, rebuild collar type, sleeve length, layering, closures "
            "and trims from Picture 1's body and outfit panels: wherever the plate "
            "is soft, Picture 1 decides. Do not reconstruct the original actor's "
            "cross-collar wrap, diagonal sash, wide belt, sleeveless vest or robe "
            "hem out of a blurred smudge, and draw no seam, trim or ornament "
            "Picture 1 does not show: when Picture 1 shows a collared or checked "
            "shirt, the replaced body wears exactly that shirt and nothing over "
            "it."
        )
    elif "wardrobe_suppressed" in _suppression_strategy:
        plate_wardrobe_blurred_clause = (
            "\n\nSOURCE PLATE WARDROBE SUPPRESSED — AUTHORITATIVE:\n"
            "The selected performer's torso region in <Video 1> has been drained "
            "of colour on purpose: it is a neutral grey fabric template whose "
            "weave, seams, folds and silhouette stay legible while every "
            "original hue is unreadable. Treat it as a placement guide, never as "
            "a garment to copy. Take from that region only the body's pose, "
            "motion, drape and where fabric edges fall; take the garment type, "
            "every colour, every pattern design and every trim from Picture 1's "
            "body and outfit panels. Do not re-colour it from the original "
            "actor's outfit and do not invent an ornamented robe, medallion "
            "motif, lattice embroidery, diagonal sash or wide belt that Picture 1 "
            "does not show: when Picture 1 shows a collared or checked shirt, the "
            "replaced body wears exactly that shirt and nothing over it."
        )
    # One band, one description.  A medium-shot silent listener is blurred in two
    # stacked regions - head band over garment band - but for the model it is a
    # single unresolved window from crown to hips, and the two clauses above each
    # spend a paragraph on it.  Measured on the black-shirt project with the
    # policy 67 probe: the garment paragraph alone costs 855 characters, which
    # pushed the compiled prompt from 11 901 to 12 758 and made the length guard
    # delete the MEDIUM-SHOT SILENT MOUTH reinforcement - the clause the director
    # keeps grading as "the character still lip-syncs" (S2/S5 round 22, seeds
    # 923000127 and 923000227).  Saying it once keeps every rule - read the band
    # for placement only, recover no age or face from its colours, Picture 1
    # decides wherever the plate is soft, invent no garment from the colour mass -
    # and gives the budget back to both silent mouth clauses.
    plate_wardrobe_silent_clause = ""
    if plate_wardrobe_blurred_clause and (
        "medium_silent" in _suppression_strategy
        and "dominant" not in _suppression_strategy
    ):
        # The wording still has to match the plate that was actually baked: the
        # chroma-preserving blur keeps the garment colours while resolving none
        # of its seams, the desaturating mode hands over a grey template (S4
        # seeds 97000324 and 97000334 showed the grey sentence is wrong for the
        # blurred plate).  Every character here is measured against the 12 320
        # ceiling: the unbudgeted pass measured 12 419 with the first draft, so
        # the wording is compressed to 847 characters, which lands the pass at
        # 12 288 and keeps both silent mouth reinforcements.
        _silent_band_colour_wording = (
            "below the shoulders it is a neutral grey template"
            if "wardrobe_suppressed" in _suppression_strategy
            else "its colours survive while no collar line, seam or drape resolves"
        )
        # How deep the soft window really goes is the Studio's answer, not this
        # module's: policy 69 grows the garment band to the bottom of the frame on
        # a standing figure, and a sentence that still said "hips" would understate
        # the region the model can see going soft.  Both spellings are the same
        # length, so the 12 320-character budget measured for this wording does
        # not move.
        _silent_band_reach = (
            "crown to feet"
            if _suppression_geometry.get("wardrobe_reaches_bottom")
            else "crown to hips"
        )
        plate_wardrobe_silent_clause = (
            "\n\nSOURCE PLATE HEAD AND WARDROBE BLURRED — AUTHORITATIVE:\n"
            "The selected performer in <Video 1> is one unresolved band from "
            + _silent_band_reach
            + ": hair, face and whole garment "
            + _silent_band_colour_wording + ", with " + plate_edge_wording + ". "
            "Read it for placement only: position, scale, pose, motion, drape, "
            "lighting. It decides no identity fact — never infer apparent age, "
            "face, skin, hair colour or hairline from its colours, and never "
            "restore the erased actor's sharper face from memory. Wherever the "
            "plate is soft, Picture 1 decides the head and the entire wardrobe: "
            "collar type, sleeve length, layering, closures, trims, colours, "
            "pattern. The surviving colour is the erased actor's costume, not a "
            "fact to keep: draw no vest, sash, belt, hem or ornament Picture 1 "
            "does not show."
        )
        # The merged wording replaces both single-region paragraphs, so the plate
        # is still described exactly once.
        plate_wardrobe_blurred_clause = ""
        plate_face_blurred_clause = ""
    # Costume ownership on an untouched plate.  The two clauses above only speak
    # when the Studio blurred or desaturated the torso, and on this project the
    # plate usually arrives intact — which is exactly the regime the director
    # graded as "the clothes look nothing like the reference" (S4/S6/S8) and
    # "the character became an old man" (S3/S7/S10/S11).  With a legible source
    # garment in place, H3 keeps the silhouette it can see and only re-tints it,
    # so the prompt has to say whose costume it is.  The official grammar already
    # calls the source person's appearance replaceable; this settles the one
    # region where the plate was still voting.
    source_costume_leaves_clause = (
        "\n\nSOURCE COSTUME BELONGS TO THE ERASED ACTOR — AUTHORITATIVE:\n"
        "The garment <Video 1> still shows inside the selected performer's region "
        "is the original actor's costume, not a wardrobe cue: the body that wore "
        "it is being replaced, so its silhouette carries no design authority. "
        "Never trace the source cross-collar wrap, diagonal sash, ribbons, wide "
        "belt, hem line or ornament Picture 1 does not show, and keep one wardrobe "
        "from the first frame to the last instead of alternating between two "
        "outfits across a cut inside this Shot."
    ) if (
        not live_action_adaptation
        and not suppressed_plate
        and any(height >= 0.25 for _width, height in _anchor_role_boxes)
    ) else ""
    # Identity-sheet grammar.  Studio composes a multi-panel sheet locally
    # whenever Picture 1's head is too small in the V1 frame to bind, so H3 must
    # be told that the one Picture it sees is several zooms of the same person
    # and that the sheet's own layout is not scene content.  Panels are crops of
    # the same artwork, which is also what keeps a cartoon a cartoon.
    reference_framing = str(pass_spec.get("reference_framing") or "").strip()
    identity_sheet_contract = (
        "\n\nPICTURE 1 IS ONE IDENTITY SHEET — AUTHORITATIVE:\n"
        "<Picture 1> is a multi-panel identity sheet of a single character, not a "
        "photograph of a room and not several people. Every panel is the same "
        "character at a different zoom, cut from the same artwork, so the visual "
        "medium is identical in all of them. The enlarged head panel is the sole "
        "authority for facial structure, eyes, eyebrows, nose, mouth, moustache or "
        "beard design, skin tone, hairstyle, hair colour and apparent age; the "
        "body and outfit panels are the sole authority for body proportions, the "
        "complete wardrobe, its colours, footwear and held props. Read those "
        "panels as one person: never turn two panels into two people, never put "
        "one panel's head on another panel's body, and never average the panels "
        "with the Video 1 actor. The sheet's presentation is packaging, not scene "
        "content: do not reproduce its split-panel layout, borders, gutters, plain "
        "mat or cut-out silhouette edges. Render exactly one instance of that "
        "character inside <Video 1>'s pose, framing, lighting, background and "
        "camera distance: the scene must not gain a second, smaller or partial "
        "copy of Picture 1."
    ) if reference_framing == IDENTITY_SHEET_FRAMING else ""
    # Apparent-age lock.  Every small-head pass in the last verified video aged
    # the cartoon design (S3, S5, S7, S10, S11 — 20 % to 80 % likeness, the user
    # grading four of them as failing).  Colour and silhouette survived; age did
    # not, so the age contract has to be stated separately from the identity one.
    apparent_age_lock = (
        "\n\nAPPARENT AGE LOCK — MANDATORY:\n"
        "Picture 1 is what the replaced character looks like, and its face is flat "
        "colour fills bounded by clean lines. The rebuilt head reproduces that "
        "drawing one for one: the same colour fills, the same lines, the same line "
        "weight, the same eye design, the same hair shape, and the same face "
        "fullness, skin smoothness, jaw shape, hairline and build. Keep the "
        "maturity Picture 1 draws, and let the person in <Video 1> lend this face "
        "its movement and timing only, never its face."
    ) if not live_action_adaptation else ""
    # Close-up sheet crop lock.  Round 18/19 S7 and S9: in a face-filling Shot
    # the sheet's lower panels show more of the figure than <Video 1> frames, and
    # Relay answered by moving the camera — importing the sheet's own hands,
    # sleeve cuffs and robe hem, and lifting source furniture that the Shot keeps
    # low.  The crop grammar that magnifies a small head is the same grammar that
    # can widen a shot, so the out-of-frame panels have to be demoted explicitly
    # to identity facts rather than framing facts.
    # Round 51 widened the trigger.  The black-shirt director reported the take
    # as "V1 frames a half-body, the result is P1's whole body": the plate cuts
    # the actor at the bottom edge, and the shipped ``full`` outfit sheet — the
    # strongest "this whole figure belongs in frame" cue Relay gets — answered by
    # widening the shot until the shoes appeared.  That Shot is not a close-up, so
    # the face-dominance test never fired even though the manual qualified
    # rectangle had already shrunk the box to 0.30x0.30 by design.  The plate
    # itself is now measured (``character_identity_sheet.
    # measure_source_figure_reveal``): if the figure inside the role box is cut by
    # the bottom edge of <Video 1>, the crop lock goes up regardless of face size.
    # Cost is stated in the round note: on a Silent Listener pass this shape pays
    # with ``medium_shot_silent_mouth`` if it runs out of budget.
    close_up_sheet_crop_lock = (
        "\n\nCLOSE-UP SHEET CROP LOCK — MANDATORY:\n"
        "This Shot crops the figure while some panels of Picture 1 "
        "reach further down the figure than this Shot does. Those panels supply "
        "identity facts only — face, hair, wardrobe design, colours, materials. "
        "They never move the camera: keep <Video 1>'s crop, shot scale and "
        "framing exactly, and do not widen the shot, tilt it lower or settle the "
        "character lower just to reveal body parts <Video 1> never shows. Do not "
        "draw hands, fists, sleeves, hems, trousers, shoes or furniture that "
        "appear in Picture 1's panels but not inside <Video 1>'s frame, and do "
        "not raise, shrink or rearrange source furniture to make room for them. "
        "Render only the part of the sheet's figure that already lies inside "
        "<Video 1>'s existing framing. <Video 1> itself cuts the figure at its "
        "bottom edge."
    ) if (
        (
            face_dominant_closeup
            or bool(pass_spec.get("source_figure_reaches_frame_bottom", False))
        )
        and reference_framing == IDENTITY_SHEET_FRAMING
    ) else ""
    protected_rows = [
        row for row in pass_spec.get("protected_source_roles") or []
        if isinstance(row, Mapping)
    ]
    protected_selectors: list[str] = []
    for protected in protected_rows:
        protected_role = str(
            protected.get("source_role_id", "") or ""
        ).strip().upper()
        protected_identity = " ".join(
            str(protected.get("source_visual_identity", "") or "").split()
        )
        keep_v1 = bool(protected.get("keep_v1", False))
        protected_bbox = protected.get("source_bbox_normalized") or []
        protected_location = ""
        if len(protected_bbox) == 4:
            try:
                x1, y1, x2, y2 = (float(value) for value in protected_bbox)
                protected_location = (
                    f"protected box x={round(x1 * 100)}-{round(x2 * 100)}%, "
                    f"y={round(y1 * 100)}-{round(y2 * 100)}%"
                )
            except (TypeError, ValueError, OverflowError):
                protected_location = ""
        protected_description = ", ".join(
            value for value in (
                "KEEP V1 — preserve the original source actor exactly" if keep_v1 else "",
                protected_identity,
                protected_location,
            ) if value
        )
        protected_selectors.append(
            f"{protected_role}: {protected_description}"
            if protected_description else protected_role
        )
    protected_contract = ""
    if protected_selectors:
        # The contract used to be one fixed paragraph.  Its last two sentences
        # cost 326 characters, and each one describes a situation that is absent
        # more often than not:
        #   * the overlap sentence describes boxes that do not overlap on this
        #     pass (round 28 S1: R1 x 35-65 %, y 15-45 % against R2 x 15-30 %,
        #     y 25-45 % — two different columns, yet the clause told H3 that a
        #     contour boundary inside the selected box was the seam between two
        #     people);
        #   * the "a later pass may already have replaced" sentence describes a
        #     *later* pass, and a single-pass window has none.
        # The budget is 12 320 characters and this pass measured 12 288, so
        # those two sentences are the cheapest real money available for the hair
        # and wardrobe contracts that were missing.  They still ship whenever the
        # geometry or the pass list says they apply.
        isolation = [
            "This pass may modify only the selected source performer(s) named "
            "above.",
            "Every other visible person is a protected non-target and must "
            "remain pixel-position, face, body, wardrobe, pose, expression and "
            "identity stable through this pass: "
            + "; ".join(protected_selectors) + ".",
            "Do not transfer Picture 1 identity, face, hair, clothing or colour "
            "into a protected person.",
            "Do not merge adjacent bodies, exchange faces, duplicate the target, "
            "or use a protected person's mouth or head as the replacement "
            "destination.",
        ]
        target_boxes = [
            list(source.get("source_bbox_normalized") or [])
            for source in source_roles
        ]
        protected_boxes = [
            list(row.get("source_bbox_normalized") or [])
            for row in protected_rows
        ]
        if any(
            _bbox_containment_overlap(target_box, protected_box) > 0.0
            for target_box in target_boxes
            for protected_box in protected_boxes
        ):
            isolation.append(
                "When target and protected boxes overlap, follow the selected "
                "performer's original body contour inside the selected target "
                "box; preserve the person outside that contour."
            )
        # A missing pass count reads as "there may be another pass", which is the
        # conservative side: the sentence is only dropped when the window is
        # provably one pass.
        try:
            pass_total = int(pass_spec.get("pass_total", 2) or 2)
        except (TypeError, ValueError):
            pass_total = 2
        if pass_total > 1:
            isolation.append(
                "A later character-swap pass may already have replaced a "
                "protected person, so preserve the current input pixels rather "
                "than restoring the original V1 actor."
            )
        protected_contract = (
            "\n\nMULTI-PERSON IDENTITY ISOLATION — MANDATORY:\n"
            + " ".join(isolation)
        )
    # Keep the author workflow's explicit Subject contract.  A previous compact
    # rewrite let H3 keep the V1 face while importing Picture 1's room, which is
    # exactly the inverse of a character swap.  The separation below makes the
    # identity-only and source-world responsibilities unambiguous.
    if len(source_roles) > 1:
        target_clause = (
            f"Replace each of these {len(source_roles)} distinct selected source "
            f"performers in <Video 1> with the same character from <Picture 1>: "
            f"{selector}. Keep them as separate bodies in their original screen positions."
        )
    else:
        sole_visible = bool(source_roles[0].get(
            "source_is_sole_visible_person", False
        ))
        target_clause = (
            "Replace only this selected source performer in <Video 1> with the "
            f"character shown in <Picture 1>: {selector}."
        )
        if sole_visible:
            target_clause += (
                " The target is the only existing foreground person in the source "
                "frame, including when only half of that person is visible."
            )
    if event_selector:
        target_clause += " Target-performance evidence: " + event_selector

    if silent_performance:
        speech_contract = (
            "\n\nSILENT LISTENER PERFORMANCE — AUTHORITATIVE: HUMAN VOCAL CHANNEL: "
            "EMPTY — this Shot has no dialogue, narration, voice-over, whisper, "
            "laugh, chant or spoken word in any language, on screen or off screen. "
            "The selected replacement performer keeps the lips naturally "
            "together and the jaw still; allow only blinking, breathing, head turns and "
            "gaze shifts. Every silent listening reaction must keep the lips closed — no "
            "open-mouth smile, laugh or jaw drop. Nothing may drive the replaced "
            "mouth: the only sound this Shot holds is non-vocal ambience, weather, "
            "room tone and material contact. Picture 1 supplies "
            "identity but never supplies an open-mouth pose, smile, visible teeth, tongue "
            "or speaking expression. Even if Picture 1 is smiling or has an open mouth, "
            "reconstruct that same identity with relaxed closed lips for the whole Shot."
        )
        if mouth_behavior:
            speech_contract += " Authored mouth direction: " + mouth_behavior
        # The body slot carries a one-line pointer only.  The authoritative
        # full contract is re-appended as the last words of the prompt (see the
        # tail below), and that placement is what the tests assert.  Emitting
        # the whole contract twice was pure bloat: S2/S3/S6/S10 each carried
        # ~1 230 duplicated characters, which is how a silent Shot reached
        # 14 385 characters against an 11 454-character proven ceiling.
        #
        # The voice-ownership wording moved *into* the authoritative block above on
        # 2026-10-26 because the authoritative block is the one copy that can never
        # be dropped, while a reinforcement can.  The archived read-backs show the
        # reinforcement was never decisive either way: seed 97000374 (S10) lost it to
        # the length guard and lip-synced, and seed 97000454 (S3) carried the full
        # 720-character reinforcement and lip-synced just the same.  What actually
        # stopped the mouth was the plate head-blur plus the closed-lip substitution
        # in the official author prompt, both of which are unfreezable.  Each
        # reinforcement is therefore now a shot-scale reminder (720 → ~380 characters)
        # instead of a second copy of the contract.
        speech_contract_body = (
            "\n\nSILENT LISTENER — SUMMARY: this Shot's human vocal channel is "
            "empty and the selected replacement performer's lips stay closed "
            "for the whole Shot; the authoritative contract at the end of this "
            "prompt decides mouth behaviour."
        )
        source_performance_contract = (
            "<Video 1> supplies the selected performer's position, scale, body pose, "
            "gestures, head turns, gaze, blinking, expression outside the mouth, and "
            "complete action clock. It must not supply mouth articulation for the "
            "selected performer."
        )
        retention_performance = (
            "preserve composition, camera, body motion, silent facial reaction, action "
            "timing, duration and non-vocal ambience; replace only the selected identity and keep "
            "the selected mouth silent"
        )
    else:
        speech_contract = ""
        speech_contract_body = ""
        source_performance_contract = (
            "<Video 1> supplies the selected performer's position, scale, body pose, "
            "gestures, head turns, gaze, blinking, expression, visible mouth timing and "
            "complete action clock. It does not supply the selected performer's identity "
            "after replacement."
        )
        retention_performance = (
            "preserve composition, camera, motion, expressions, mouth timing, action "
            "timing, duration and soundtrack; replace only the selected identity"
        )
    performance_override = (
        source_performance_contract + "\n<Video 1>: " + retention_performance + "."
        if silent_performance else ""
    )

    # The full-design-sheet contract is medium-neutral: it stops Relay from
    # pasting Picture 1 as a crop, decal or face patch whether or not an
    # illustrated cast is being adapted to live action.  Both branches keep
    # it so the two concerns never get mixed again.
    design_sheet_contract_full = (
        "\n\nFULL DESIGN-SHEET INTERPRETATION — MANDATORY:\n"
        "Treat the complete Picture 1 person as a character design sheet, never "
        "as a crop, decal, face patch or ready-made foreground layer. Rebuild "
        "one coherent head, neck, shoulders, torso, wardrobe and any visible "
        "limbs on the original Video 1 body geometry. The head size, shoulder "
        "width, perspective, frame-edge truncation and camera distance come "
        "only from the selected Video 1 performer. Never enlarge Picture 1's "
        "face to fill the selected rectangle, never paste its original flat "
        "pixels, and never leave the source actor's hair, collar, robe or body "
        "underneath it."
    )
    # When Studio sends a composed Identity Sheet, the identity-sheet grammar
    # clause above already owns "read the panels together, never paste them into
    # the frame", so the full restatement here is the second copy of the same
    # instruction.  Measured 2026-10-25: the two sheet clauses together cost
    # 2 137 characters and pushed the S3/S6/S10 passes to 12 586-12 756, well
    # past the longest prompt this endpoint is known to accept (11 911), which
    # is what forced the drop loop to sacrifice the load-bearing medium and
    # plate-texture clauses.  Under sheet framing the clause therefore collapses
    # to a pointer that keeps its marker and the anti-paste rule; every other
    # reference framing (raw Media Pool picture, full design sheet) still gets
    # the full wording, because there the anti-paste rule has no other copy.
    design_sheet_contract_sheet_lean = (
        "\n\nFULL DESIGN-SHEET INTERPRETATION — MANDATORY:\n"
        "Treat the complete Picture 1 person as a character design sheet, never "
        "as a crop, decal, face patch or ready-made foreground layer: rebuild one "
        "coherent head, neck, torso and wardrobe on the selected Video 1 body "
        "geometry, whose head size, perspective, frame-edge truncation and "
        "camera distance decide the result."
    )
    design_sheet_contract = (
        design_sheet_contract_sheet_lean
        if reference_framing == IDENTITY_SHEET_FRAMING
        else design_sheet_contract_full
    )
    if live_action_adaptation:
        medium_contract = (
            "\n\nILLUSTRATED-CAST TO LIVE-ACTION CONTRACT:\n"
"<Picture 1> may be a cartoon, anime, comic, cel-shaded or otherwise illustrated design. Preserve its semantic identity cues—apparent age, moustache or facial-hair design, hairstyle silhouette and colour, facial proportions, wardrobe design, colour blocking and signature accessories—but do not preserve its drawing medium as pixels. Reconstruct Subject 1 as a physically plausible live-action human photographed in the same production as <Video 1>. Use realistic anatomy and head-to-body scale, dimensional skin, individual hair, real cloth weave, natural pores, subsurface skin colour, scene-matched highlights and shadows, lens softness, depth of field, motion blur and film grain. Match Video 1 exposure, white balance, shadow direction, edge softness and occlusion. No pasted cartoon head, sticker edge, black ink outline, flat cel shading, paper cutout, oversized head, illustrated hands or mixed 2D/photographic surfaces. The result must remain recognisable as the Picture 1 character's live-action film interpretation."

            + design_sheet_contract
        )
    else:
        medium_contract = design_sheet_contract

    # Multi-person subject redefinition: the official template's Subject 1 is
    # singular ("the person being replaced"), which H3 reconciles poorly when
    # one P Picture replaces several V1 bodies (S7/S10/S11 evidence — loose
    # photorealistic drift with both plate faces fully blurred).  For a grouped
    # pass, redefine the singular definition as all selected performers taken
    # together and bind every body to its own position and pose clock.
    # The wording is deliberately terse: a grouped pass already carries the two
    # plate-suppression clauses plus the sheet grammar, and seed 97000374 (S10
    # R1+R2) proved a 11 911-character grouped prompt still submits while the
    # 11 589-character pre-drop build of the same pass needed 189 characters cut
    # to fit the budget without losing a load-bearing clause.
    multi_person_subject_definitions = ""
    if len(source_roles) > 1:
        multi_person_subject_definitions = f"""

MULTI-PERSON SUBJECT DEFINITIONS — AUTHORITATIVE:
The singular "person being replaced" above means these {len(source_roles)} selected source performers taken together: {selector}. <Subject 1> is one replacement character from <Picture 1> that replaces each of those bodies, one at a time, at that person's exact position, scale and frame-edge truncation. Each replaced body keeps its own pose clock, occlusion order and scene interactions; the replaced bodies never merge into one person, exchange faces or swap positions, and no other visible person becomes Subject 1.
"""
    # Complete-wardrobe replacement: the official template mentions clothing once
    # and H3 settles for a "similar concept" outfit (S4/S6/S8 evidence — invented
    # patterns, trims and garments that Picture 1 never shows).  Bind every
    # visible garment layer to the design sheet's wardrobe.
    # Round 50: this clause used to end with the garment-silhouette sentence.  It
    # is an *unranked* (never-droppable) clause, so every character we spent there
    # came out of the ranked clauses further down the tail.  The silhouette
    # sentence now lives on its own in ``wardrobe_silhouette_reinforcement`` below,
    # which the length guard can sacrifice first; the rest of this clause keeps its
    # full round-49 wording because nothing in it is negotiable.
    complete_wardrobe_contract = (
        "\n\nCOMPLETE WARDROBE REPLACEMENT — MANDATORY:\n"
        "Replace the selected performer's entire visible wardrobe with Picture 1's "
        "wardrobe exactly as drawn in its design sheet: every garment layer, shape, "
        "pattern, trim, collar, fastener, accessory and colour blocking comes from "
        "Picture 1. No original Video 1 garment remains underneath or on top of it — "
        "no original robe hem, sleeve, collar, sash, belt, fabric edge or under-layer "
        "visible anywhere on the body. Where Picture 1 does not fully show a garment, "
        "continue that same design coherently in the same medium and palette; never "
        "borrow missing garments from Video 1."
    )
    # Round 50 (garment-silhouette reinforcement, deliberately its own droppable
    # clause at rank 1): the cut/length/hem complaint is the newest unverified
    # hardening in this module, and measured closes show what paying for it inside
    # a never-droppable clause costs.  A Silent Listener identity-sheet close-up
    # compiles to 12 956 characters before any drop against the 12 320 proven
    # ceiling, so the tail has to give 636; the old rank 1-2 mouth reminders buy
    # back 638 between them, which left two characters of slack.  Adding 243
    # characters to an unranked clause on that same spec therefore pushed the guard
    # into rank 3 and sacrificed ``source_costume_leaves_plate`` -- the clause that
    # stops S4's "the source actor's own robe came back onto P1's shirt".  Trading
    # a verified gate for an unverified reinforcement is the wrong direction, so
    # the reinforcement now pays for itself: it is dropped before the mouth
    # reminders, and both verified gates survive the same close-up.
    wardrobe_silhouette_reinforcement = (
        "\n\nGARMENT SILHOUETTE — MANDATORY:\n"
        "Match Picture 1's garment silhouette and drape exactly: the cut, length, "
        "fit and hem line of every garment, never a similar concept in a different "
        "cut."
    )
    # No-invented-details binding: H3 adds goatees, medallions and embroidery that
    # exist neither in Picture 1 nor in Video 1 (S7 evidence).  The background-only
    # texture contract is not enough; bind the character's own details too.
    no_invented_details_contract = (
        "\n\nEVERY DETAIL COMES FROM PICTURE 1 — MANDATORY:\n"
        "Every visible detail of the replacement is drawn from Picture 1's design "
        "sheet: each mark, garment edge, trim, collar, spectacle and facial-hair "
        "shape sits where Picture 1 puts it, with Picture 1's own line weight and "
        "colour. What Picture 1 draws stays drawn — the moustache, round glasses, "
        "hat and collar dots belong to the character — and an ambiguous detail "
        "keeps Picture 1's own rendering."
    )

    # The LoRA author prompt in the V2 API is the proven conditioning baseline.
    # Studio previously replaced it with a much longer bespoke prompt which
    # repeated the V1 actor's hair and wardrobe as positive facts. On the real
    # S3 clip that caused a near-total no-op. Keep the API prompt verbatim and
    # append only controls that the graph cannot infer from its two inputs.
    # ``Preserve Video 1 visible mouth timing`` is a positive lip-sync fact. For a
    # speaking Shot it is exactly right; emitted unconditionally it also told every
    # ``silent_listener`` pass to animate the mouth, and round-10 (seeds 97000444 /
    # 97000454) proved H3 obeys it even when the SILENT LISTENER contract is the
    # last thing in the prompt. The sentence therefore follows the performance mode.
    mouth_clock_clause = (
        "Preserve Video 1 action clock; the selected mouth follows the silent "
        "performance contract below."
        if silent_performance
        else "Preserve Video 1 visible mouth timing and action clock."
    )
    if route == CHARACTER_SWAP_ROUTE_VANILLA:
        # 路線 3: the manual-ComfyUI parity floor.  Round 69 measured the two
        # takes of the same clip -- the director's accepted manual graph and the
        # rejected Studio compile -- and the only difference in what H3 was told
        # is the appendix: 2 876 characters against 7 394, with 4 050 of Studio
        # clauses sitting under a prompt the official template already completes.
        # Every field the appendix restates (crop, wardrobe, background, medium)
        # is already a retention line of the author prompt, and the noun-bearing
        # clauses are the ones that put invented objects on screen.  This route
        # therefore submits the author prompt and nothing else, so a GPU take is
        # a clean measurement of the graph rather than of clause accumulation.
        #
        # Two facts survive by exception.  A silent Shot keeps the authoritative
        # mouth contract, because the template was written for a subject that
        # speaks and its ``visible mouth movements`` sentence would otherwise
        # contradict an empty vocal channel; and the route still reports the same
        # audit keys, so a manifest can never read a 0-character appendix as a
        # gate that stopped firing.
        # Round 122: 默认连这三处例外都不加（``H3_CHARACTER_SWAP_PROMPT_APPENDIX``）。
        # 静音改写也一起关掉：它会把他模板里那句 ``visible mouth movements`` 就地换掉，
        # 而他手跑那一枪用的就是原句。开关开回来，下面这段就是 Round 117 之前的原样。
        appendix = character_swap_prompt_appendix_enabled()
        prompt = _relay_v2_author_prompt(
            silent_mouth=silent_performance and appendix, locks=False
        )
        appendix_start = len(prompt)
        if appendix:
            if silent_performance:
                prompt += LEAN_SILENT_TAIL
                if mouth_behavior:
                    prompt += " Authored mouth direction: " + mouth_behavior
            if suppressed_plate:
                # The second exception, for the same reason as the first: the template
                # describes a picture that is no longer the one Relay received.  See
                # ``LEAN_VANILLA_SOURCE_HAIR``.
                prompt += LEAN_VANILLA_SOURCE_HAIR
            # Round 105: the figure sentence, on the parity route too.  Nothing here
            # matched to delete -- 路線 3 ships no authored direction, so the design
            # lock never entered this prompt -- and that is exactly why the clause is
            # still appended: neca_6 rendered on this route (manifest
            # preview_411399206549878986_1794160031403257100) and H3 was never once
            # told that a kaiju figure has no human wardrobe to keep.  Placed before
            # the length audit below so the recorded char counts describe the prompt
            # that is actually sent.
            prompt = _character_swap_nonhuman_cast_lock_pass(
                pass_spec, prompt, prompt_audit
            )
        append_chars = len(prompt) - appendix_start
        if prompt_audit is not None:
            prompt_audit.update({
                "route": route,
                "char_budget": CHARACTER_SWAP_PROMPT_CHAR_BUDGET,
                "eyewear_policy": eyewear,
                "eyewear_clause_shipped": False,
                "prompt_chars": len(prompt),
                "gate_chars": append_chars,
                "tail_chars": 0,
                "dropped_tail_clauses": [],
                "over_budget": len(prompt) > CHARACTER_SWAP_PROMPT_CHAR_BUDGET,
                "append_chars": append_chars,
                "append_budget": CHARACTER_SWAP_VANILLA_APPEND_BUDGET,
                "append_over_budget": (
                    append_chars > CHARACTER_SWAP_VANILLA_APPEND_BUDGET
                ),
                "author_prompt_chars": appendix_start,
                # Round 122: a 0-character appendix must never read as a gate that
                # stopped firing by accident -- these two rows say which file the words
                # came from and that the appendix switch is what made it zero.
                "prompt_appendix": appendix,
                "prompt_source": character_swap_prompt_source_name(),
            })
        return prompt
    if route != CHARACTER_SWAP_ROUTE_LEGACY:
        # 路線 1 / 路線 2.  The same gates decide which clauses exist, so a lean
        # route can never be asked about a situation the verified prompt did not
        # describe; only the wording and the number of clauses change.
        sheet_active = reference_framing == IDENTITY_SHEET_FRAMING
        lean_identity_note = LEAN_IDENTITY_NOTE + " " + mouth_clock_clause
        # Every clause is registered as ``(name, text, exempt)`` in shipping
        # order.  A name is unique per compile, which is what lets the cap below
        # name its victims instead of losing them silently, and ``exempt`` marks
        # the three kinds of text ``CHARACTER_SWAP_LEAN_STYLING_BUDGET`` says may
        # never be traded away: the target locator, the in-place/whole-body
        # erasure pair, and the silent contract.  The visual-medium declaration
        # is exempt for the same reason -- it is the one sentence standing
        # between a cartoon reference and a photographic take, and round 62's
        # manual A/B graded the ageing/texture clauses, never this one.  It is
        # nevertheless registered as the last victim below (``final_medium_priority``
        # sits past the end of the drop order), so a compile whose exempt text
        # alone overflowed the budget can still be reported honestly instead of
        # shipping a knowingly over-budget appendix.
        clauses: list[tuple[str, str, bool]] = [
            (
                "target_locator",
                "\n\nSTUDIO TARGET LOCATOR — AUTHORITATIVE:\n" + target_clause,
                True,
            ),
        ]
        if route == CHARACTER_SWAP_ROUTE_PRECISE:
            if len(source_roles) > 1:
                clauses.append(
                    (
                        "multi_person_cast",
                        LEAN_MULTI_PERSON.format(
                            n=len(source_roles), selector=selector
                        ),
                        True,
                    )
                )
            clauses.append(("in_place_replacement", LEAN_IN_PLACE, True))
            clauses.append(
                (
                    "whole_body_erasure",
                    LEAN_ERASURE.format(
                        identity_note=lean_identity_note,
                        hair=LEAN_HAIR if suppressed_plate else "",
                    ),
                    True,
                )
            )
            clauses.append(
                ("wardrobe_from_reference", LEAN_WARDROBE, False)
            )
            clauses.append(
                (
                    "no_invented_detail_list",
                    LEAN_NO_INVENTED.format(details=detail_keep_list(eyewear)),
                    False,
                )
            )
            if protected_selectors:
                clauses.append(
                    (
                        "protected_cast",
                        LEAN_PROTECTED_CAST.format(
                            selectors="; ".join(protected_selectors)
                        ),
                        True,
                    )
                )
            if silent_performance:
                clauses.append(("silent_summary", LEAN_SILENT_SUMMARY, True))
                clauses.append(
                    ("silent_performance_grounding", LEAN_PERFORMANCE_SILENT, True)
                )
            clauses.append(
                (
                    "reference_sheet_reading",
                    LEAN_IDENTITY_SHEET if sheet_active else LEAN_DESIGN_SHEET,
                    False,
                )
            )
            if (
                face_dominant_closeup
                or bool(pass_spec.get("source_figure_reaches_frame_bottom", False))
            ) and sheet_active:
                clauses.append(("closeup_crop_lock", LEAN_CROP_LOCK, False))
            if not live_action_adaptation:
                clauses.append(("apparent_age_lock", LEAN_AGE_LOCK, False))
            if any(
                area >= PLATE_TEXTURE_CONTRACT_MIN_BOX_AREA
                for area in _plate_box_areas
            ):
                clauses.append(
                    ("plate_surface_provenance", LEAN_NO_TEXTURE, False)
                )
            # A clean plate has no band to hide the source look behind, so the
            # ownership sentence has to be said out loud.  On a suppressed plate
            # ``LEAN_HAIR`` and the blurred-band clauses already own this ground,
            # and a live-action adaptation deliberately keeps the source's head.
            if not suppressed_plate and not live_action_adaptation:
                clauses.append(
                    (
                        "source_look_ownership",
                        LEAN_SOURCE_LOOK_OWNERSHIP.format(
                            eyewear=eyewear_ownership_fragment(eyewear)
                        ),
                        False,
                    )
                )
                # Same ground, same plate: the eyewear fact only has to be said
                # when nobody blurred the face band away, and a live-action
                # adaptation is deliberately keeping the source head anyway.
                # Round 65 says which of the two it is; ``neutral`` deliberately
                # says nothing, which is the shape of the manual ComfyUI run.
                if eyewear == EYEWEAR_POLICY_WORN:
                    clauses.append(
                        ("eyewear_policy", LEAN_EYEWEAR_WORN, False)
                    )
                    eyewear_clause_shipped = True
                elif eyewear == EYEWEAR_POLICY_UNCOVERED:
                    clauses.append(
                        ("eyewear_policy", LEAN_EYEWEAR_UNCOVERED, False)
                    )
                    eyewear_clause_shipped = True
        else:
            # 路線 2: the hand-built floor.  One medium sentence, one sheet line
            # when a sheet is actually on the wire, and the in-place/erasure
            # guards that stop the face-sticker failure the director grades.
            clauses.append(
                ("in_place_replacement", LEAN_MINIMAL_IN_PLACE, True)
            )
            clauses.append(
                (
                    "whole_body_erasure",
                    LEAN_MINIMAL_ERASURE.format(identity_note=lean_identity_note),
                    True,
                )
            )
            if sheet_active:
                clauses.append(
                    ("reference_sheet_reading", LEAN_MINIMAL_SHEET, False)
                )
        # 路線 2's measured styling half (one sheet line plus the medium
        # sentence) cannot reach the cap, so the ranking below can only ever
        # fire on a 路線 1 compile with most gates on at once.
        medium_clause = (
            LEAN_MEDIUM_LIVE_ACTION if live_action_adaptation else LEAN_MEDIUM
        )
        clause_text = {name: text for name, text, _exempt in clauses}
        clause_text["final_medium_priority"] = medium_clause
        drop_rank = {
            name: index
            for index, name in enumerate(CHARACTER_SWAP_LEAN_STYLING_DROP_ORDER)
        }
        styling_chars = sum(
            len(text) for name, text, exempt in clauses if not exempt
        ) + len(medium_clause)
        dropped: list[str] = []
        while styling_chars > CHARACTER_SWAP_LEAN_STYLING_BUDGET:
            candidates = [
                name
                for name, _text, exempt in clauses
                if not exempt and _text and name not in dropped
            ]
            if medium_clause and "final_medium_priority" not in dropped:
                candidates.append("final_medium_priority")
            if not candidates:
                break
            victim = min(candidates, key=lambda name: drop_rank[name])
            dropped.append(victim)
            styling_chars -= len(clause_text[victim])
        prompt = _relay_v2_author_prompt(silent_mouth=silent_performance)
        appendix_start = len(prompt)
        prompt += "".join(
            text
            for name, text, _exempt in clauses
            if text and name not in dropped
        )
        if directed:
            prompt += (
                " After the identity swap, apply only this authored direction without "
                "changing the performance clock or protected cast: " + directed
            )
        if "final_medium_priority" not in dropped:
            prompt += medium_clause
        if silent_performance:
            # Last words, exactly as in the legacy route: the silent-mouth tests
            # assert with ``rfind`` that nothing may follow this block.
            prompt += LEAN_SILENT_TAIL
            if mouth_behavior:
                prompt += " Authored mouth direction: " + mouth_behavior
        # Round 105: same rewrite, same place -- after every appendix and lock is
        # assembled, before ``append_chars`` / ``prompt_chars`` are recorded.  On a
        # non-human cast the figure clause takes the last word even behind a silent
        # contract: the measured failure was a flicker back to the human at ~3.5-7.5
        # s, and a mouth rule cannot fix a body the model was told to keep dressed.
        prompt = _character_swap_nonhuman_cast_lock_pass(
            pass_spec, prompt, prompt_audit
        )
        append_chars = len(prompt) - appendix_start
        # ``styling_chars`` is the surviving capped half, medium included when it
        # shipped; whatever is left of the appendix is exempt text.
        gate_chars = append_chars - styling_chars
        append_budget = (
            CHARACTER_SWAP_LEAN_APPEND_BUDGET
            if route == CHARACTER_SWAP_ROUTE_PRECISE
            else CHARACTER_SWAP_MANUAL_APPEND_BUDGET
        )
        if prompt_audit is not None:
            prompt_audit.update({
                "route": route,
                # Round 65: what the appendix was told to do about eyewear, and
                # whether it said anything.  ``neutral`` ships no clause, and the
                # manifest has to be able to tell that apart from a gate that
                # quietly stopped firing.
                "char_budget": CHARACTER_SWAP_PROMPT_CHAR_BUDGET,
                "eyewear_policy": eyewear,
                # Round 69: the cap can drop a clause whose gate fired, and a
                # manifest that says the face sentence shipped while the text
                # never reached H3 is the same lie the uncapped appendix used to
                # tell.  "Shipped" means on the wire, so a dropped clause reads
                # as not shipped and ``dropped_tail_clauses`` says why.
                "eyewear_clause_shipped": bool(
                    eyewear_clause_shipped
                    and "eyewear_policy" not in dropped
                ),
                "prompt_chars": len(prompt),
                # The cap is honest: the halves are reported separately so a
                # shrunken appendix can never be read as a gate that stopped
                # firing, and every sacrificed clause is named in the order it
                # would have shipped.
                "gate_chars": gate_chars,
                "tail_chars": styling_chars,
                "styling_budget": CHARACTER_SWAP_LEAN_STYLING_BUDGET,
                "dropped_tail_clauses": sorted(
                    dropped, key=lambda name: drop_rank[name]
                ),
                "over_budget": len(prompt) > CHARACTER_SWAP_PROMPT_CHAR_BUDGET,
                "append_chars": append_chars,
                "append_budget": append_budget,
                "append_over_budget": append_chars > append_budget,
                "author_prompt_chars": appendix_start,
            })
        return prompt
    author_prompt = _relay_v2_author_prompt(silent_mouth=silent_performance)
    appendix_start = len(author_prompt)
    prompt = author_prompt
    prompt += f"""

STUDIO TARGET LOCATOR — AUTHORITATIVE:
{target_clause}
{multi_person_subject_definitions}

IN-PLACE REPLACEMENT — MANDATORY:
Transform the selected performer in place. Never add Picture 1 as a second person or duplicate its panels into extra standing bodies. Preserve exact frame-edge truncation, scale and occlusion.

COMPLETE SOURCE-ACTOR ERASURE — MANDATORY:
Replace the whole visible silhouette, not a face sticker. Leave no original actor, ghost or duplicate underneath; the selected box must contain exactly one coherent Subject 1 head and body.{source_hair_ownership_clause}
{complete_wardrobe_contract}
{no_invented_details_contract}

<Picture 1> supplies identity only. Never import Picture 1's room or background. The final face must be recognisably the Picture 1 character, never the original Video 1 actor. {mouth_clock_clause}
Do not replace, blend, merge, duplicate or restyle any non-target person.
{protected_contract}
{speech_contract_body}
{performance_override}
{medium_contract}
"""
    if directed:
        prompt += (
            " After the identity swap, apply only this authored direction without changing "
            "the performance clock or protected cast: " + directed
        )
    if live_action_adaptation:
        prompt += (
            " FINAL MEDIUM PRIORITY: whenever another instruction says preserve the Picture "
            "exactly, preserve its character identity and signature design only; the visible "
            "rendering medium must remain physically realistic live-action cinema."
        )
    else:
        # Medium preservation is the default contract: whatever visual medium a
        # P Picture uses (cartoon, anime, comic, cel-shaded or photographic)
        # stays that same medium; only Video 1 supplies action and scene.
        prompt += (
            " FINAL MEDIUM PRIORITY: whenever another instruction says preserve the Picture "
            "exactly, preserve its own visual medium as well — an illustrated, cartoon, "
            "anime or comic reference stays in that same illustrated style with its line "
            "work, colour blocking and shading intact; a photographic reference stays "
            "photographic. Only <Video 1> supplies action, composition, camera movement, "
            "lighting direction, scene geometry and timing."
        )
    # Tail clauses keep their historical emission order — every reinforcement
    # must stay before the final authoritative contract, which is what the
    # silent-mouth tests assert with ``rfind``.  The same list is what the
    # length guard can sacrifice: ``CHARACTER_SWAP_TAIL_DROP_RANKS`` gives the
    # order in which restatements are dropped once the compiled prompt passes
    # the proven submittable ceiling, and a clause without a rank is never
    # dropped.  Within one rank the clause emitted last is dropped first so the
    # strongest early-tail positions survive.
    tail_clauses = (
        ("close_up_face_anchor", close_up_face_anchor),
        ("close_up_medium_reinforcement", close_up_medium_reinforcement),
        ("identity_sheet_contract", identity_sheet_contract),
        ("close_up_sheet_crop_lock", close_up_sheet_crop_lock),
        ("apparent_age_lock", apparent_age_lock),
        ("plate_texture_contract", plate_texture_contract),
        ("close_up_silent_mouth", close_up_silent_mouth),
        ("medium_shot_silent_mouth", medium_shot_silent_mouth),
        ("plate_face_blurred_clause", plate_face_blurred_clause),
        ("plate_torso_blurred_clause", plate_torso_blurred_clause),
        ("plate_wardrobe_blurred_clause", plate_wardrobe_blurred_clause),
        ("plate_wardrobe_silent_clause", plate_wardrobe_silent_clause),
        ("wardrobe_silhouette_reinforcement", wardrobe_silhouette_reinforcement),
        ("source_costume_leaves_plate", source_costume_leaves_clause),
    )
    clause_text = dict(tail_clauses)
    emission_order = [name for name, _text in tail_clauses]
    kept = {name for name, text in tail_clauses if text}
    silent_tail_length = len(speech_contract) if silent_performance else 0
    total_chars = (
        len(prompt)
        + sum(len(clause_text[name]) for name in kept)
        + silent_tail_length
    )
    dropped: list[str] = []
    while total_chars > CHARACTER_SWAP_PROMPT_CHAR_BUDGET:
        candidates = [
            name for name in kept
            if name in CHARACTER_SWAP_TAIL_DROP_RANKS
        ]
        if not candidates:
            break
        victim = min(
            candidates,
            key=lambda name: (
                CHARACTER_SWAP_TAIL_DROP_RANKS[name],
                -emission_order.index(name),
            ),
        )
        kept.remove(victim)
        dropped.append(victim)
        total_chars -= len(clause_text[victim])
    for name, text in tail_clauses:
        if name in kept:
            prompt += text
    if silent_performance:
        # Keep this last so an authored directed-scene note cannot accidentally
        # re-enable an obsolete Qwen speaker/mouth instruction.
        prompt += speech_contract
    # Round 105: the legacy route is the only one that has always carried the
    # authored design direction, so this is where the human lock is really found
    # and deleted -- "Preserve @P1's exact recognizable face, ... footwear and
    # accessories. Never blend, swap, duplicate, redraw or transfer this
    # identity." (design_engine.py:3171-3178).  Again before the audit, so
    # ``prompt_chars`` and ``append_chars`` describe the sent prompt.
    prompt = _character_swap_nonhuman_cast_lock_pass(
        pass_spec, prompt, prompt_audit
    )
    if prompt_audit is not None:
        prompt_audit.update({
            "route": route,
            "char_budget": CHARACTER_SWAP_PROMPT_CHAR_BUDGET,
            "prompt_chars": len(prompt),
            "dropped_tail_clauses": [
                name for name in emission_order if name in dropped
            ],
            "over_budget": len(prompt) > CHARACTER_SWAP_PROMPT_CHAR_BUDGET,
            "append_chars": len(prompt) - appendix_start,
            "append_budget": CHARACTER_SWAP_PROMPT_CHAR_BUDGET,
            "append_over_budget": False,
            "author_prompt_chars": appendix_start,
        })
    return prompt


def character_swap_ref_upscale_scale_override() -> int | None:
    """Return the reference-upscale multiplier forced by the environment.

    ``H3_CHARACTER_SWAP_REF_UPSCALE_SCALE`` accepts 2, 3 or 4, the multipliers
    ``RTXVideoSuperResolution`` publishes.  Unset, blank, malformed or out of
    range returns ``None`` = "keep the shipped template value", which is what
    every verified take in this project used.  A typo degrades to the verified
    baseline instead of submitting a multiplier the custom node would reject.
    """

    raw = os.environ.get(CHARACTER_SWAP_REF_UPSCALE_SCALE_ENV, "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value in CHARACTER_SWAP_REF_UPSCALE_SCALE_CHOICES else None


def character_swap_ref_upscale_quality_override() -> str | None:
    """Return the RTX Video Super Resolution SDK mode forced by the environment.

    ``H3_CHARACTER_SWAP_REF_UPSCALE_QUALITY`` accepts the scale-preserving
    ``nvvfx.QualityLevel`` members the installed node publishes.  Comparison is
    case- and whitespace-tolerant; anything else -- including the ``DENOISE_*``
    and ``DEBLUR_*`` modes that keep the input dimensions -- returns ``None``,
    which means "keep the shipped template mode".
    """

    raw = os.environ.get(CHARACTER_SWAP_REF_UPSCALE_QUALITY_ENV, "").strip()
    if not raw:
        return None
    normalised = raw.upper().replace("-", "_").replace(" ", "_")
    return normalised if normalised in CHARACTER_SWAP_REF_UPSCALE_QUALITY_CHOICES else None


def character_swap_ref_upscale_strength_override() -> float | None:
    """Return the RTX Video Super Resolution strength forced by the environment.

    The node publishes ``strength`` as a 0.0-1.0 float.  Values outside that
    range, NaN and malformed text all return ``None`` = "keep the template
    value", so a typo cannot hand ComfyUI a number the custom node rejects.
    """

    raw = os.environ.get(CHARACTER_SWAP_REF_UPSCALE_STRENGTH_ENV, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value or value < 0.0 or value > CHARACTER_SWAP_REF_UPSCALE_STRENGTH_MAX:
        return None
    return round(value, 3)


def character_swap_output_upscale_switch() -> str:
    """Return the raw Preview output enhancer switch, normalised.

    ``"on"`` (an affirmative word), ``"off"`` or ``"scale"`` (a bare multiplier).
    A bare multiplier is an affirmative too: ``H3_CHARACTER_SWAP_PREVIEW_VSR=4``
    says both "enhance" and "by four", and reading it as only one of the two is how
    a knob ends up half-honoured.

    Round 69: the default flipped to ``"off"``, so unset, blank, an unparseable
    value and an unsupported multiplier all mean "do not touch the finished frames".
    The enhancer costs resolution parity as well as detail, and a Preview is graded
    on what H3 produced; silence has to mean the untouched take.
    """

    raw = os.environ.get(CHARACTER_SWAP_OUTPUT_UPSCALE_ENV, "").strip().lower()
    if not raw or raw in CHARACTER_SWAP_OUTPUT_UPSCALE_OFF_WORDS:
        return "off"
    if raw in CHARACTER_SWAP_OUTPUT_UPSCALE_ON_WORDS:
        return "on"
    try:
        value = int(raw)
    except (TypeError, ValueError):
        # An unparseable value is not a request for an enhancer, so it must not
        # receive one.  Only an affirmative word buys the shipped 2x.
        return "off"
    # 2/3/4 are the multipliers the installed node publishes; anything else is a
    # number the node would reject, so it buys nothing rather than half a pass.
    return "scale" if value in CHARACTER_SWAP_REF_UPSCALE_SCALE_CHOICES else "off"


def character_swap_output_upscale_requested() -> bool:
    """Return whether the environment still allows the Preview output enhancer."""

    return character_swap_output_upscale_switch() != "off"


def character_swap_output_upscale_scale_override() -> int | None:
    """Return the multiplier the environment asked for, if it named one.

    Only 2, 3 and 4 are offered because those are the multipliers the installed
    node publishes.  ``None`` means "no opinion" - unset, blank, an affirmative
    word, an off word, or an unusable number - and the caller then uses the
    shipped 2x rather than the number it was handed.
    """

    raw = os.environ.get(CHARACTER_SWAP_OUTPUT_UPSCALE_ENV, "").strip().lower()
    if (
        not raw
        or raw in CHARACTER_SWAP_OUTPUT_UPSCALE_ON_WORDS
        or raw in CHARACTER_SWAP_OUTPUT_UPSCALE_OFF_WORDS
    ):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value in CHARACTER_SWAP_REF_UPSCALE_SCALE_CHOICES else None


def _character_swap_enhancer_settings(workflow: Mapping[str, Any], *, exclude_node_id: str) -> dict:
    """Return the scalar enhancer settings the template already authored.

    The Preview enhancer is a second instance of the node the template already
    runs on Picture 1, so it inherits that node's authored ``quality``,
    ``strength`` and ``image_encoding`` instead of guessing them.  Links are
    dropped: this helper copies settings, and the caller supplies the image the
    enhancer has to eat.
    """

    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type", "")) != CHARACTER_SWAP_OUTPUT_UPSCALE_CLASS:
            continue
        if str(node_id) == str(exclude_node_id):
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, Mapping):
            continue
        return {
            str(key): deepcopy(value)
            for key, value in inputs.items()
            if not isinstance(value, (list, tuple))
        }
    return {}


def _character_swap_follow_enhancer_link(
    workflow: Mapping[str, Any],
    link: list,
) -> list:
    """Step back through an enhancer that is already on the wire.

    Re-feeding a compiled graph - a saved Job opened again, or the same workflow
    recompiled in place - arrives with the output stage already spliced into the
    link.  Eating its own output would be a cycle the server can execute but
    nobody can read, and stacking a second 2x on top of the first would quietly
    turn 480 into 1920.  Following the stage's own input instead puts the fresh
    node back on the original frames, which is the same graph the first compile
    produced.
    """

    enhancer_id = CHARACTER_SWAP_OUTPUT_UPSCALE_NODE_ID
    resolved = [link[0], link[1]]
    while str(resolved[0]) == enhancer_id:
        stage = workflow.get(enhancer_id)
        upstream = (
            stage.get("inputs", {}).get("images")
            if isinstance(stage, dict) and isinstance(stage.get("inputs"), Mapping)
            else None
        )
        if not isinstance(upstream, (list, tuple)) or len(upstream) != 2:
            break
        resolved = [upstream[0], upstream[1]]
    return resolved


def _character_swap_output_upscale_target(
    workflow: Mapping[str, Any],
    save_node_id: str,
) -> tuple[str, str, list] | None:
    """Return ``(node_to_attach, input_name, image_link)`` for the enhancer.

    A ``SaveVideo`` consumes a VIDEO, not an IMAGE, so on the shipped graph the
    enhancer has to sit upstream of ``CreateVideo`` rather than in front of the
    saver.  Walking the link rather than hard-coding ``video`` also keeps a
    re-exported template - or the legacy all-in-one Relay graph, whose saver is
    fed differently - compiling against the graph it actually got.  ``None`` means
    this graph has no image stream to enhance, which is a reason to skip and say
    so, never a reason to ship a node ComfyUI cannot validate.
    """

    saver = workflow.get(str(save_node_id))
    if not isinstance(saver, dict):
        return None
    saver_inputs = saver.get("inputs")
    if not isinstance(saver_inputs, Mapping):
        return None
    ordered = [
        name
        for name in CHARACTER_SWAP_OUTPUT_IMAGE_INPUTS
        if name in saver_inputs
    ]
    ordered += [name for name in saver_inputs if name not in ordered]
    image_link: list | None = None
    saver_input_name = ""
    for name in ordered:
        value = saver_inputs.get(name)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            image_link = [value[0], value[1]]
            saver_input_name = str(name)
            break
    if image_link is None:
        return None
    producer_id = str(image_link[0])
    producer = workflow.get(producer_id)
    if (
        isinstance(producer, dict)
        and str(producer.get("class_type", "")) in CHARACTER_SWAP_VIDEO_MUXER_CLASSES
    ):
        producer_inputs = producer.get("inputs")
        if isinstance(producer_inputs, Mapping):
            frames = producer_inputs.get("images")
            if isinstance(frames, (list, tuple)) and len(frames) == 2:
                return (
                    producer_id,
                    "images",
                    _character_swap_follow_enhancer_link(
                        workflow, [frames[0], frames[1]]
                    ),
                )
    return (
        str(save_node_id),
        saver_input_name,
        _character_swap_follow_enhancer_link(workflow, image_link),
    )


def insert_character_swap_output_upscale(
    workflow: dict[str, Any],
    *,
    save_node_id: str,
    scale: int = CHARACTER_SWAP_OUTPUT_UPSCALE_DEFAULT_SCALE,
) -> dict[str, Any]:
    """Insert the RTX VSR stage between the Relay's frames and the video mux.

    The enhancer is spliced into one existing link and nothing else moves: the
    saver keeps its ``filename_prefix``, ``CreateVideo`` keeps its ``fps`` and its
    audio, and the worker still harvests output from the same ``SaveVideo`` node.
    Re-compiling an already-compiled workflow reuses the node instead of stacking a
    second 2x on top of the first.
    """

    target = _character_swap_output_upscale_target(workflow, save_node_id)
    if target is None:
        return {}
    attach_id, input_name, source_link = target
    node_id = CHARACTER_SWAP_OUTPUT_UPSCALE_NODE_ID
    authored = _character_swap_enhancer_settings(
        workflow, exclude_node_id=node_id
    )
    existing = workflow.get(node_id)
    reused = bool(
        isinstance(existing, dict)
        and str(existing.get("class_type", ""))
        == CHARACTER_SWAP_OUTPUT_UPSCALE_CLASS
    )
    if not reused:
        existing = {"class_type": CHARACTER_SWAP_OUTPUT_UPSCALE_CLASS, "inputs": {}}
        workflow[node_id] = existing
    # The shipped template labels every node, and a queue whose last stage is
    # anonymous is a queue the director cannot read.  Titled separately from
    # node 9 on purpose: two identical titles in one graph is how a reference
    # enhancer gets mistaken for the output enhancer.
    existing.setdefault("_meta", {})["title"] = (
        CHARACTER_SWAP_OUTPUT_UPSCALE_NODE_TITLE
    )
    inputs = existing.setdefault("inputs", {})
    scale_key = next(
        (key for key in CHARACTER_SWAP_REF_UPSCALE_SCALE_KEYS if key in inputs),
        "",
    )
    if not scale_key:
        scale_key = next(
            (
                key
                for key in CHARACTER_SWAP_REF_UPSCALE_SCALE_KEYS
                if key in authored
            ),
            CHARACTER_SWAP_REF_UPSCALE_SCALE_KEYS[0],
        )
    for key, value in authored.items():
        if str(key) == scale_key or str(key) == "images":
            continue
        # The mode is forced to a multiplier below, so the other branch's
        # dimension inputs are dead weight the node was not asked for.
        if str(key).startswith("resize_type."):
            continue
        inputs.setdefault(str(key), value)
    inputs["resize_type"] = CHARACTER_SWAP_OUTPUT_UPSCALE_RESIZE_MODE
    inputs[scale_key] = int(scale)
    inputs.setdefault("quality", CHARACTER_SWAP_OUTPUT_UPSCALE_FALLBACK_QUALITY)
    inputs.setdefault(
        "strength", CHARACTER_SWAP_OUTPUT_UPSCALE_FALLBACK_STRENGTH
    )
    inputs.setdefault(
        "image_encoding", CHARACTER_SWAP_OUTPUT_UPSCALE_FALLBACK_ENCODING
    )
    inputs["images"] = [source_link[0], source_link[1]]
    workflow[attach_id].setdefault("inputs", {})[input_name] = [node_id, 0]
    try:
        strength = float(inputs.get("strength", 0.0))
    except (TypeError, ValueError):
        strength = 0.0
    return {
        "node_id": node_id,
        "attach_node_id": attach_id,
        "attach_input": input_name,
        "source_node_id": str(source_link[0]),
        "source_output_index": int(source_link[1]),
        "scale": int(scale),
        "quality": str(inputs.get("quality", "")),
        "strength": strength,
        "image_encoding": str(inputs.get("image_encoding", "")),
        "reused_template_enhancer_settings": bool(authored),
        "reused_existing_node": reused,
    }


def character_swap_output_upscale_contract_rows(
    workflow: dict[str, Any],
    *,
    save_node_id: str,
    requested: bool,
) -> dict[str, Any]:
    """Apply the Preview enhancer and return the rows that report it.

    Only ``requested`` comes from the caller, because only the caller knows
    whether this is a Preview.  The environment switch and the multiplier are read
    here so the Job, the manifest and the graph are produced by one decision
    instead of three that can disagree.  Every branch returns the full row set:
    a director who turned the feature off still has to be able to read *that* from
    the manifest rather than infer it from an absent key.
    """

    raw_env = os.environ.get(CHARACTER_SWAP_OUTPUT_UPSCALE_ENV, "").strip()
    rows: dict[str, Any] = dict(CHARACTER_SWAP_OUTPUT_UPSCALE_ROW_DEFAULTS)
    rows["output_upscale_requested"] = bool(requested)
    rows["output_upscale_env"] = raw_env
    if not requested:
        # Final Render is graded on what H3 produced.  An enhancer that invents
        # detail is allowed to change a verdict, so it never touches the take that
        # gets approved.
        rows["output_upscale_skip_reason"] = OUTPUT_UPSCALE_REASON_NOT_PREVIEW
        return rows
    if not character_swap_output_upscale_requested():
        rows["output_upscale_skip_reason"] = OUTPUT_UPSCALE_REASON_ENVIRONMENT
        return rows
    scale_override = character_swap_output_upscale_scale_override()
    scale = int(
        CHARACTER_SWAP_OUTPUT_UPSCALE_DEFAULT_SCALE
        if scale_override is None
        else scale_override
    )
    inserted = insert_character_swap_output_upscale(
        workflow, save_node_id=save_node_id, scale=scale
    )
    if not inserted:
        rows["output_upscale_skip_reason"] = OUTPUT_UPSCALE_REASON_NO_IMAGE_INPUT
        return rows
    rows.update(
        {
            "output_upscale_enabled": True,
            "output_upscale_node_id": inserted["node_id"],
            "output_upscale_attach_node_id": inserted["attach_node_id"],
            "output_upscale_attach_input": inserted["attach_input"],
            "output_upscale_source_node_id": inserted["source_node_id"],
            "output_upscale_scale": float(inserted["scale"]),
            "output_upscale_scale_source": (
                "environment" if scale_override is not None else "shipped_default"
            ),
            "output_upscale_quality": inserted["quality"],
            "output_upscale_strength": inserted["strength"],
            "output_upscale_image_encoding": inserted["image_encoding"],
        }
    )
    return rows


def clamp_character_swap_lora_strength(value: Any) -> float:
    """Return ``value`` inside the published Character-Swap LoRA range.

    Anything the LoRA was not trained for is clipped to the ceiling instead of
    being forwarded to ComfyUI, and a non-numeric value degrades to the ceiling
    rather than to an unbounded strength.
    """

    ceiling = CHARACTER_SWAP_LORA_MAX_STRENGTH
    try:
        strength = float(value)
    except (TypeError, ValueError):
        return ceiling
    if strength != strength:  # NaN
        return ceiling
    return round(min(max(0.0, strength), ceiling), 3)


# Round 117 (2026-11-11, the director's own instruction: 别搞自己的实验，按照原本 h3 的提示词跑, and
# read it from the two sources he named).  The published API prompt of akatz-ai/MiniMax-H3-Character-
# Swap-LoRA (examples/H3-Character-Swap-Relay-V2.api.json, node ``reference_conditioning``) hands the
# reference conditioning ONE sentence, and examples/README.md states the rest of the recipe in one line:
# "Keep eight steps, normal scheduler, er_sde, CFG 1 and both LoRA strengths at 1."  Our submitted
# graph (read back from his ComfyUI history for the 06:32 take, nodes 89d80ec3 / 55d2785c) instead
# carried Studio's multi-paragraph ``subject_definitions`` prompt and ``strength_model = 1.5`` on
# h3_character_swap_v1.5.safetensors, while every other published number in that graph already matched
# (steps 8 / normal / er_sde / CFG 1 / shift 12.0+3.0 / SAM 0.35+0.5 / max_objects 1 / detect_interval
# 1 / expansion 64 / window 124 / history 18).  The model card is equally direct: "Download V1.5 -
# recommended, strength 1.0".
# 退回两条各一行：H3_CHARACTER_SWAP_PROMPT_RECIPE=on（换成官方那一句）、
# H3_CHARACTER_SWAP_LORA_STRENGTH=official（换成官方 1.0）。两条默认都是**他自己图里的数**，因为
# 2×2 四格真跑（R2 同一镜头、同一遮罩修正，testing/_sheet/116/round117_prompt_vs_strength.png）说得很清楚：
#   115 长提示词 + 1.5 → 937.2/766.8s，t=0.5s 与 3.5s 右边都是整只 godzilla（唯一成功的一格）
#   G1  官方一句 + 1.5 → 937.2s，右边是没画开的原人物剪影，godzilla 没了
#   G2  长提示词 + 1.0 → 596.8s，同样只剩黑影
#   117 官方一句 + 1.0 → 681.8s，也没有 godzilla
# 也就是说这一镜需要他那一枪的替换力度；官方那两处一起或分别软下来都画不出角色。默认照赢的那格走，
# 开关留着，谁想复核一行的事。
CHARACTER_SWAP_RECIPE_PROMPT_ENV = "H3_CHARACTER_SWAP_PROMPT_RECIPE"
CHARACTER_SWAP_RECIPE_PROMPT = (
    "Replace the selected person with the reference character. "
    "Preserve source performance, scene and audio timing."
)
CHARACTER_SWAP_OFFICIAL_PROMPT_ON_VALUES = frozenset(
    {"1", "on", "true", "yes", "official", "api", "published"}
)
CHARACTER_SWAP_LORA_STRENGTH_ENV = "H3_CHARACTER_SWAP_LORA_STRENGTH"
# The card's number for the recommended V1.5 adapter, and the README's "both LoRA strengths at 1".
CHARACTER_SWAP_RECIPE_LORA_STRENGTH = 1.0
CHARACTER_SWAP_LORA_STRENGTH_OFFICIAL_VALUES = frozenset(
    {"official", "published", "card", "readme", "api", "1.0", "1"}
)
# Round 122（导演 11-11 点名）：路线 3 也不许再往他写的提示词后面加字。
#
# 他在自己提交的 WITHMASK 里删掉了两段文字，Studio 又把它们加回来：路线 3 只剩三处例外
# ——静音尾 ``LEAN_SILENT_TAIL``（:3507）、``Authored mouth direction``（:3509）、
# 头发归属句 ``LEAN_VANILLA_SOURCE_HAIR``（:3514）——外加非人类锁（:3523），还有
# ``_relay_v2_author_prompt(silent_mouth=True)`` 会把他那句 ``visible mouth movements``
# 就地改成静音说法（实测 +19 字）。他手跑那一枪 2875 字一个字没动、结果是他要的，
# 所以默认关掉整套追加；要复核开 ``H3_CHARACTER_SWAP_PROMPT_APPENDIX=on`` 一行的事。
# 写坏了也倒回默认（不加字），因为方向是"少给他不想要的字"。
CHARACTER_SWAP_PROMPT_APPENDIX_ENV = "H3_CHARACTER_SWAP_PROMPT_APPENDIX"
CHARACTER_SWAP_PROMPT_APPENDIX_ON_VALUES = frozenset(
    {"1", "on", "true", "yes", "clauses", "appendix", "legacy", "round117"}
)


def character_swap_prompt_appendix_enabled(
    environ: dict[str, str] | None = None,
) -> bool:
    """Whether any clause may be appended to the harvested author prompt (default no).

    Round 122: the director's own hand run ships his template text untouched and won,
    so the shipped default submits what he wrote — the silent tail, the mouth
    direction, the hair-ownership sentence, the nonhuman cast lock and the in-place
    silent-mouth rewrite all go quiet.  Only the explicit on-values above put them back.
    """

    source = os.environ if environ is None else environ
    return (
        str(source.get(CHARACTER_SWAP_PROMPT_APPENDIX_ENV, "")).strip().lower()
        in CHARACTER_SWAP_PROMPT_APPENDIX_ON_VALUES
    )


def character_swap_official_prompt_recipe_enabled(
    environ: dict[str, str] | None = None,
) -> bool:
    """Whether the swap conditioning carries the published one-sentence prompt (default no).

    Default off on measured evidence: the official wording paints less than the Studio's own prompt on
    this two-character fisheye shot (see the block above), so the shipped default keeps the wording
    that produced the only cell where the creature was painted.
    """

    source = os.environ if environ is None else environ
    return (
        str(source.get(CHARACTER_SWAP_RECIPE_PROMPT_ENV, "")).strip().lower()
        in CHARACTER_SWAP_OFFICIAL_PROMPT_ON_VALUES
    )


def character_swap_lora_recipe_strength(
    template_strength: Any = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """The adapter strength this graph should ship with, and where that number came from.

    Empty knob keeps his graph's own number (the winning cell of the 2×2); ``official`` / ``1.0``
    switches to the published figure; any other numeric value still passes through
    :func:`clamp_character_swap_lora_strength`, so the published ceiling stays the ceiling.
    """

    source = os.environ if environ is None else environ
    raw = str(source.get(CHARACTER_SWAP_LORA_STRENGTH_ENV, "")).strip().lower()
    if not raw or raw in {"template", "graph", "keep", "as_is", "as-is", "author"}:
        return {
            "strength": clamp_character_swap_lora_strength(template_strength),
            "source": "导演图里的数（2×2 量出来只有这一格画出了角色）",
        }
    if raw in CHARACTER_SWAP_LORA_STRENGTH_OFFICIAL_VALUES:
        return {
            "strength": clamp_character_swap_lora_strength(CHARACTER_SWAP_RECIPE_LORA_STRENGTH),
            "source": "官方说明与 README 的数（strength 1.0）",
        }
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        requested = clamp_character_swap_lora_strength(template_strength)
        return {
            "strength": requested,
            "source": "导演旋钮写坏了，退回导演图里的数",
        }
    return {
        "strength": clamp_character_swap_lora_strength(requested),
        "source": "导演旋钮 H3_CHARACTER_SWAP_LORA_STRENGTH",
    }


# ``resolution`` on the prepare node is a bucket, not a size: the node publishes
# 480 and 768 and H3 renders the take at the bucket's own aspect-matched size
# (576x864 and 800x1216 on this plate).  Age drift turned out to be a resolution
# problem before it was a prompt problem.  Every 0.5 MP Preview in the newest
# video — S3, S5, S7, S10, S11 — came back as "the cartoon medium is right, the
# head is nothing like the reference, the person became an old man", while the one
# take the director accepted (preview_923011207, policy 82 at 1.0 MP, 800x1216)
# passed on its first attempt with the same prompt shape.  The APPARENT AGE LOCK
# is only obeyed at 768, so paying for the small bucket silently deletes it.
#
# ``H3_CHARACTER_SWAP_MIN_MEGAPIXELS`` raises the floor, and round 52 ships it at
# ``0.0``: what Preview asks for is what Preview pays for.  The 1.0 floor was
# added to stop small-bucket age drift, but it also silently re-rated every 0.5 MP
# Preview into a 1.0 MP render, and on the failed policy-84 job that re-rate is one
# of the reasons a 12.86 s Shot cost the director roughly 70 minutes (two
# QC-triggered re-fires at about 22 minutes each plus a third attempt).  The age
# drift it was fighting is now fought by ``APPARENT AGE LOCK``, which 路線 1 ships
# on every non-live-action pass, and the knob still works: ``=1.0`` puts the round-51
# behaviour back verbatim.  Anything above 4.0 or anything that does not parse
# falls back to the shipped default so a typo cannot ask the node for a bucket it
# does not publish.
CHARACTER_SWAP_MIN_MEGAPIXELS_ENV = "H3_CHARACTER_SWAP_MIN_MEGAPIXELS"
# Round 52: the floor is off by default.  A Preview that asks for 0.5 MP now gets
# the 480 bucket, and the manifest's ``effective_megapixels`` still records the
# bucket that actually went up the wire, so a cost can never be paid twice without
# appearing in the contract.
CHARACTER_SWAP_MIN_MEGAPIXELS_DEFAULT = 0.0
CHARACTER_SWAP_MIN_MEGAPIXELS_MAX = 4.0
# Round 122（导演 11-11 选"改回 768"）：两个桶都上 768。
#
# 两条实测都指向同一格：他手动成功那一枪（ComfyUI history ``107a19c7…``）他自己在
# ``H3RelayPrepareSource.inputs.resolution`` 里填的是 ``"768"``；Studio 的 h3_project_333
# 走的是 ``"480"``，同一张图、同一套 LoRA、同一个 expansion 128，被他判失败。
# 官方 README 的配方也是 768p。Round 53 早就量过一次：480 桶会把参考角色画老画糊
# （576x864 那格"人变老头"），800x1216 那格才是他收的版本。
# 他 P1 那张 670x1920 的头只占 7.7%，480 桶本来就不够脸。
# 代价他一小时前就认了：Preview 慢大约一倍。回退一行：两个常量都写回 "480"。
PREPARE_RESOLUTION_HIGH = "768"
PREPARE_RESOLUTION_LOW = "768"
PREPARE_HIGH_MEGAPIXELS = 0.75
# Round 53 brings the floor back, but only where it demonstrably buys something.
#
# The director's own footage supplies a clean A/B: two takes of the same identity
# sheet (preset 8, 800x1216, source_fingerprint a7d8b999cf3e69a3), the same 307
# frames, the same clause set, one attempt each and no QC re-fire.  The take that
# came back "the person became an old man" prepared at the 480 bucket and rendered
# 576x864; the take the director accepted prepared at 768 and rendered 800x1216.
# ``APPARENT AGE LOCK — MANDATORY`` was present in both prompts, so the clause was
# delivered in both and the bucket is the only surviving discriminator.  That also
# rules out the tempting conditional fix - "only raise the bucket on a
# face-filling Shot": the aged take is a *medium* Shot (design_plan medium x9,
# no close-up, ``face_dominant_closeup`` false), so a close-up-anchored rule
# would never have fired on the one Shot that needs it.
#
# The bucket is therefore tied to the single fact that predicts the drift: whether
# this pass is carrying an apparent-age promise at all.  A pass whose compiled
# prompt contains the age lock pays for the 768 bucket; a live-action adaptation,
# which deliberately ships no age lock, keeps what it asked for.  An explicit
# ``H3_CHARACTER_SWAP_MIN_MEGAPIXELS`` - including ``0`` - always wins, so the
# escape hatch round 52 documented still means exactly what it says and round 52's
# objection (a silent re-rate that helped make one 12.86 s Shot cost ~70 minutes)
# cannot come back without naming itself in the contract.
APPARENT_AGE_LOCK_PROMPT_MARKER = "APPARENT AGE LOCK"
# 1.0 rather than the bare 0.75 that would also select 768: the bucket, and
# therefore the wall clock, is identical either way, and the number recorded in
# the manifest should read like the take it is being compared against
# (preview_923011207 recorded effective 1.0 MP at 800x1216).
APPARENT_AGE_LOCK_MIN_MEGAPIXELS = 0.5
# ``megapixel_floor_reason`` names the rule that produced ``megapixel_floor`` and
# ``megapixel_floor_applied`` says whether that number actually raised this
# pass's render.  They are kept apart on purpose: a director who sets the escape
# hatch to ``0`` has to be able to prove from the manifest that the knob was in
# play even on the passes where the knob did not move the number.
MEGAPIXEL_FLOOR_REASON_ENVIRONMENT = "environment"
MEGAPIXEL_FLOOR_REASON_AGE_LOCK = "apparent_age_lock"
MEGAPIXEL_FLOOR_REASON_SHIPPED_DEFAULT = "shipped_default"


def character_swap_megapixels_floor() -> float:
    """Return the megapixel floor forced by the environment.

    Unset or blank is the shipped 0.0, which means "no floor" and reproduces the
    policy-83 timing behaviour.  ``1.0`` restores round 51's forced high bucket;
    malformed and out-of-range values degrade to the shipped default rather
    than to whatever a typo said.  That includes ``nan``, which parses cleanly
    and would otherwise survive the range tests below: a NaN floor makes
    ``max(requested, floor)`` return the requested value and
    ``nan >= PREPARE_HIGH_MEGAPIXELS`` false, so the floor the operator asked
    for would quietly vanish and the Shot would land back on the bucket that
    ages the character.
    """

    raw = os.environ.get(CHARACTER_SWAP_MIN_MEGAPIXELS_ENV, "").strip()
    if not raw:
        return CHARACTER_SWAP_MIN_MEGAPIXELS_DEFAULT
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return CHARACTER_SWAP_MIN_MEGAPIXELS_DEFAULT
    if requested != requested:  # NaN parses; it must not win
        return CHARACTER_SWAP_MIN_MEGAPIXELS_DEFAULT
    if requested < 0.0 or requested > CHARACTER_SWAP_MIN_MEGAPIXELS_MAX:
        return CHARACTER_SWAP_MIN_MEGAPIXELS_DEFAULT
    return requested


def character_swap_megapixels_floor_override() -> float | None:
    """Return the megapixel floor the operator explicitly asked for, if any.

    ``None`` means "the environment said nothing usable": unset, blank,
    unparseable, NaN, or outside 0-4.  ``character_swap_megapixels_floor``
    collapses that case onto the shipped default, and the collapse has to stay
    visible here: the automatic age-lock floor added in round 53 must fire when
    the operator abstained and must not fire when the operator explicitly said
    ``0``.  Both readings return ``0.0`` from ``floor()``, so only this function
    can tell them apart.
    """

    raw = os.environ.get(CHARACTER_SWAP_MIN_MEGAPIXELS_ENV, "").strip()
    if not raw:
        return None
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return None
    if requested != requested:  # NaN parses; it must not win
        return None
    if requested < 0.0 or requested > CHARACTER_SWAP_MIN_MEGAPIXELS_MAX:
        return None
    return requested


def character_swap_apparent_age_lock_in_prompt(prompt: Any) -> bool:
    """Return whether a compiled prompt actually carries the apparent-age lock.

    The test is on the compiled text rather than on the Shot's flags, because the
    promise that has to be paid for is the promise that reached H3.  Both spellings
    of the clause - 路線 1's lean ``LEAN_AGE_LOCK`` and the full
    ``apparent_age_lock`` reinforcement - open with the same heading, and neither
    one carries a tail-drop rank, so if the marker is absent the pass genuinely
    made no age promise (a live-action adaptation) rather than having it trimmed.
    """

    return APPARENT_AGE_LOCK_PROMPT_MARKER in str(prompt or "")


def character_swap_megapixel_decision(
    value: Any, *, apparent_age_lock: bool = False
) -> dict[str, Any]:
    """Return the megapixels Relay should prepare at and the rule that chose them.

    Precedence, strongest first: an explicit environment override (``0``
    included); then the automatic floor for a pass that carries the apparent-age
    lock; then the shipped default.  The request itself is never lowered - a 2.0
    MP request stays 2.0 MP whatever the floor says.  The reason string is not
    decoration: ``effective_megapixels`` alone cannot tell a director whether the
    render they are paying for came from their own number, a knob, or Studio
    refusing to age the character on a cheap bucket.
    """

    override = character_swap_megapixels_floor_override()
    if override is not None:
        floor = override
        floor_reason = MEGAPIXEL_FLOOR_REASON_ENVIRONMENT
    elif apparent_age_lock:
        floor = APPARENT_AGE_LOCK_MIN_MEGAPIXELS
        floor_reason = MEGAPIXEL_FLOOR_REASON_AGE_LOCK
    else:
        floor = CHARACTER_SWAP_MIN_MEGAPIXELS_DEFAULT
        floor_reason = MEGAPIXEL_FLOOR_REASON_SHIPPED_DEFAULT
    floor = float(floor)
    try:
        requested = float(value)
    except (TypeError, ValueError):
        requested = float("nan")
    if requested != requested:  # NaN or a non-numeric request
        # Falling back to the floor rather than to the small bucket is the
        # round-51 rule and it survives: the small bucket is what ages the
        # reference, so an unreadable request must not buy it.
        return {
            "requested_megapixels": None,
            "megapixel_floor": floor,
            "effective_megapixels": floor,
            "megapixel_floor_reason": floor_reason,
            # Nothing was raised above a usable request, so nothing was
            # "applied".  The row that says what happened is the null
            # ``requested_megapixels``, which is why this stays False.
            "megapixel_floor_applied": False,
        }
    effective = max(requested, floor)
    return {
        "requested_megapixels": requested,
        "megapixel_floor": floor,
        "effective_megapixels": effective,
        "megapixel_floor_reason": floor_reason,
        "megapixel_floor_applied": effective > requested,
    }


def character_swap_effective_megapixels(
    value: Any, *, apparent_age_lock: bool = False
) -> float:
    """Return the megapixels Relay should actually prepare at.

    The requested value survives whenever it is already at or above the floor;
    below it the floor wins.  A non-numeric request degrades to the floor, never
    to the small bucket, because the small bucket is the thing that ages the
    reference character.

    ``apparent_age_lock`` is keyword-only and defaults to ``False`` so every
    caller written before round 53 keeps the round-52 world unchanged: the
    automatic floor only exists for the caller that can prove the pass promised
    an apparent age, which is the workflow compiler.
    """

    return float(
        character_swap_megapixel_decision(
            value, apparent_age_lock=apparent_age_lock
        )["effective_megapixels"]
    )


def character_swap_prepare_resolution(megapixels: float) -> str:
    """Map megapixels onto the prepare node's published bucket."""

    return (
        PREPARE_RESOLUTION_HIGH
        if float(megapixels) >= PREPARE_HIGH_MEGAPIXELS
        else PREPARE_RESOLUTION_LOW
    )


# ---------------------------------------------------------------------------
# Round 112 - SAM 3 的遮罩进图，而不是事后拿 ffmpeg 贴边
#
# 导演要的做法是「各自生成角色替换 → SAM3 沟边 → 合成」。节点包里官方的
# Character Swap 配方就是这么做的：SAM3_Detect / SAM3_VideoTrack /
# SAM3_TrackToMask 先框出要被替换的那个人，H3RelayExpandMask 外扩 64 px，
# H3RelayWindowInputs 把这个遮罩发成一个窗口的 edit_mask，
# H3RelayApplyEditMask 再把它变成 H3 自己的 noise_mask——擦与画都发生在同一次
# 扩散里，源的其余像素由 H3 原样保留。这条链在包外没有第二个实现：
# h3_relay/toolkit.py 的 H3RelayApplyEditMask 明确把 latent 的视频张量换成编码
# 后的源张量，并写 {"noise_mask": [video_mask, ones]}。
#
# 导演 11-10 凌晨新存的 H3-Character-Swap-Relay-V2-API-WITHMASK.json 才是这张图的正确
# 版本：46 个节点，他那台 ComfyUI 上 0 缺类、0 必填输入缺口，window.mask 已经接在
# expand_mask.0 上。旧那张 -api-mask.json（11-01 存的）恰恰漏了这根线——它的
# edit_mask.mask 虽然连着 window.1，可 H3RelayWindowInputs 自己的 mask 是空的，遮罩
# 一路传空，而 H3RelayApplyEditMask 的 mask 是 required，节点要到执行时才炸，所以那条
# 路从来没出过画面，CHANGELOG 里也就没有它一行。逐节点比对正在跑的图：新图只多了 11
# 个遮罩节点，只把 guide / sample / sampling_memory 的 latent 改走 edit_mask——底模
# (minimax_h3_ref2va_int8_convrot)、Turbo (minimax_h3_turbo_v4_step600_ema, 1.0)、
# swap LoRA (h3_character_swap_v1.5, 1.5)、两个 VAE、采样器、P 图路径一个字都没改，
# 这才是「只加 SAM3 沟边、别的都不动」。character_swap_model_identity_drift 会把这类
# 漂移原样写进 manifest 当警告，但绝不改写导演画的图。
#
# 引擎只做核对与补线（缺才接，已有的线不覆盖），并按 env 把包里推荐的阈值写进图
# （默认就是 example workflow 的 0.35 / 0.50 / 64 px / max_objects 1）。max_objects
# 永远是 1：包里所有 swap 图都钉死 1，官方配方再叠一层 H3RelaySelectMask(largest)，
# 单人一次是它的硬合同，所以「两个角色一次换完」不在这轮的范围里。
# 退回：H3_CHARACTER_SWAP_WORKFLOW_NAME=plain（回到正在跑的这张，逐字节不变）。
# ---------------------------------------------------------------------------
CHARACTER_SWAP_WORKFLOW_NAME_ENV = "H3_CHARACTER_SWAP_WORKFLOW_NAME"
CHARACTER_SWAP_MASK_WORKFLOW_NAME = "H3-Character-Swap-Relay-V2-API-WITHMASK.json"
CHARACTER_SWAP_PLAIN_WORKFLOW_ALIASES = {
    "plain", "maskless", "off", "none", "legacy",
    CHARACTER_SWAP_WORKFLOW_NAME,
}
SAM_MASK_SUBJECT_ENV = "H3_CHARACTER_SWAP_SAM_MASK_SUBJECT"
SAM_MASK_SUBJECT_DEFAULT = "person"
SAM_MASK_DETECT_THRESHOLD_ENV = "H3_CHARACTER_SWAP_SAM_MASK_DETECT_THRESHOLD"
SAM_MASK_DETECT_THRESHOLD_DEFAULT = 0.35
SAM_MASK_TRACK_THRESHOLD_ENV = "H3_CHARACTER_SWAP_SAM_MASK_TRACK_THRESHOLD"
SAM_MASK_TRACK_THRESHOLD_DEFAULT = 0.50
SAM_MASK_EXPANSION_PX_ENV = "H3_CHARACTER_SWAP_SAM_MASK_EXPANSION_PX"
# Round 118 (2026-11-11, godzilla Shot, my own ComfyUI submits at 127.0.0.1:8189): the author's graph has
# no plate erasure — ``window.0`` goes straight into ``VAEEncode`` and ``H3RelayApplyEditMask`` decides
# where the model may paint — so an edit mask that misses the body leaves the model nowhere to draw it.
# Measured for free (no diffusion, testing/_dsh_verify_13/godzilla/mask_expansion_118.py: prune to the
# ancestors of ``expand_mask``, sink it through ``MaskToImage``/``SaveImage``, then measure coverage of
# each role box the Studio already knows, 44 sampled frames per case):
#   expansion   R2 盖住本角色   R2 平均   R2 串对面   R1 盖住本角色   R1 平均   R1 串对面
#      64 (官方)   31/44        0.5252     0.1995        22/44        0.4824     0.3590
#      96            42/44        0.6315     0.2590        29/44        0.5505     0.4149
#     128            44/44        0.7285     0.3233        33/44        0.6208     0.4713
#     160            44/44        0.8184     0.3924        38/44        0.6916     0.5283
# 128 is the first value where the right-hand figure is covered in every sampled frame, and 160 starts
# eating the neighbouring box.  Paid confirmation on the same shot with the director's own prompt and
# strength (testing/_dsh_verify_13/godzilla/selfrun_118.py, testing/_sheet/116/round118_expansion_128.png,
# R1 772.2 s / R2 1022.2 s): the right role now shows a whole godzilla at t=0.5 s, 3.5 s *and* the 7.0 s
# close-up (the official 64 left an unpainted face there), and the left role shows a complete RX-78 —
# the first pass of eleven that ever painted the mech.  ``H3_CHARACTER_SWAP_SAM_MASK_EXPANSION_PX=64``
# restores the published figure on any one Shot.
SAM_MASK_EXPANSION_PX_DEFAULT = 128
SAM_MASK_MAX_OBJECTS = 1
# Round 114 (2026-11-10, measured by testing/_dsh_verify_13/godzilla/subject_text_probe_113e.py on
# the godzilla Shot, free SAM-only submits, no diffusion): the in-graph mask chain conditioned on
# ``person`` returns exactly ONE object from a two-figure frame, so both role passes receive the same
# mask - the left figure - and the figure that was supposed to be replaced is never masked at all
# (frame 84: R1 covered 0.5244, R2 covered 0.0000).  Handing the detector the same union phrase the
# composite already tracks with returns THREE objects on that frame, and only ``rightmost`` /
# ``index 1`` reaches the right figure at all.  So the mask's subject text names every body kind in
# the Shot and the selector - not the detector - chooses which one this pass repaints.
SAM_MASK_AUTOSELECT_ENV = "H3_CHARACTER_SWAP_SAM_MASK_AUTOSELECT"
SAM_MASK_UNION_SUBJECT_BASE = "person"
# The composite caps its tracking phrase at 160 characters (smart_render_worker
# SAM31_TEXT_PROMPT_MAX_CHARS); the mask phrase carries the same bodies, so it carries the same cap.
SAM_MASK_UNION_SUBJECT_MAX_CHARS = 160
SAM_MASK_SIDE_MARGIN = 0.05
# The plate geometry the Studio already computed for this pass describes where this role is: every
# erase band is [left, top, width, height] and protected_boxes are the OTHER roles' boxes (the
# Round 10x guard never blurs inside them).  Those are the app's own numbers, from the same run, so
# they decide which object the mask follows instead of a field the director may never have touched.
SAM_MASK_GEOMETRY_KEYS = ("hair_extent", "figure_extent")
SAM_MASK_SELECTABLE = ("largest", "leftmost", "rightmost", "index")
# Round 116 (2026-11-11, the same Shot, four real swap passes I rendered myself on ComfyUI
# 127.0.0.1:8189 and compared frame by frame in testing/_sheet/115/round115_r1_four_way.png): what the
# plate erases and what the SAM mask selects are two different shapes, and every mismatch shows up in the
# picture.  Erasing nothing keeps the source person - no gundam appears at all (run 115c, 1118.2 s).
# Erasing only the head/hair bands paints only a head layer (run 115b, 1007.8 s - the audit's own words:
# "replacement is only a head/face layer; the V1 wardrobe still fills the upper…").  Erasing a whole
# rectangle wider than the mask leaves the part of that rectangle the mask never covered blurred grey
# forever (run 115d, 837.5 s: a flat grey block, nothing painted into it).  So more erasing is not the
# answer; the mask is the one shape both sides can agree on, and the director's own instruction is to
# 沟边 with SAM.  The plate is therefore erased IN THE GRAPH from that mask: blur the window frames, and
# keep the original sharp frames wherever the mask is not.  A wrong band then costs nothing, and the
# erase always follows the same edge the repaint follows.
# 退回：H3_CHARACTER_SWAP_IN_GRAPH_PLATE=off（只用 Studio 压片带的那张图，逐字节不变）。默认就是 off：
# 这一上午又跑了四枪把它否掉（testing/_sheet/116/round116_verdict.png 与 round116b_verdict.png）——
#   压片带 + 图内压片（R1-E 973.2s / R2-E 671.6s）：左边第一次出现 gundam，右边整只 godzilla 还在，
#     但 t=3.5s 右边退化成金发怪物，比只改遮罩那一版（R2-B）差；
#   未压片原片 + 图内压片（R1-F 1152.2s / R2-F 847.0s）：灰糊问题彻底没了（这是它对的部分），
#     可右边又变回黑影没有 godzilla，左边画出来的是人形不是 gundam。
# 也就是说「遮罩内糊」并不能替模型决定要画什么，九枪里唯一稳定变好的仍是遮罩那一半（Round 114/115）。
# 所以这个开关留在实验位，等他看过对照表再定；要开就 H3_CHARACTER_SWAP_IN_GRAPH_PLATE=on。
IN_GRAPH_PLATE_ENV = "H3_CHARACTER_SWAP_IN_GRAPH_PLATE"
IN_GRAPH_PLATE_ON_VALUES = frozenset({"1", "on", "true", "yes", "mask", "in_graph"})
IN_GRAPH_PLATE_BLUR_RADIUS_ENV = "H3_CHARACTER_SWAP_IN_GRAPH_PLATE_BLUR_RADIUS"
IN_GRAPH_PLATE_SIGMA_ENV = "H3_CHARACTER_SWAP_IN_GRAPH_PLATE_SIGMA"
# ImageBlur on this build takes (image, blur_radius INT, sigma FLOAT) - verified through
# /object_info.  The Studio's own head band settled on a boxblur radius around 18 for a head-sized crop,
# so 24 px at the prepared resolution is the same strength by another name.
IN_GRAPH_PLATE_BLUR_RADIUS_DEFAULT = 24
IN_GRAPH_PLATE_SIGMA_DEFAULT = 1.0
IN_GRAPH_PLATE_BLUR_RADIUS_MAX = 96
IN_GRAPH_PLATE_SIGMA_MAX = 8.0


def character_swap_in_graph_plate_parameters(
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Whether the plate is erased by the in-graph mask, and how hard that blur is."""

    source = os.environ if environ is None else environ
    # Default off: the frames decided it (see the block above).  Anything that is not an explicit "on"
    # word leaves the director's band plate exactly as his accepted takes rendered it.
    enabled = (
        str(source.get(IN_GRAPH_PLATE_ENV, "")).strip().lower() in IN_GRAPH_PLATE_ON_VALUES
    )
    radius_raw = str(source.get(IN_GRAPH_PLATE_BLUR_RADIUS_ENV, "")).strip()
    try:
        blur_radius = int(radius_raw) if radius_raw else IN_GRAPH_PLATE_BLUR_RADIUS_DEFAULT
    except (TypeError, ValueError):
        blur_radius = IN_GRAPH_PLATE_BLUR_RADIUS_DEFAULT
    if not 1 <= blur_radius <= IN_GRAPH_PLATE_BLUR_RADIUS_MAX:
        blur_radius = IN_GRAPH_PLATE_BLUR_RADIUS_DEFAULT
    sigma_raw = str(source.get(IN_GRAPH_PLATE_SIGMA_ENV, "")).strip()
    try:
        sigma = float(sigma_raw) if sigma_raw else IN_GRAPH_PLATE_SIGMA_DEFAULT
    except (TypeError, ValueError):
        sigma = IN_GRAPH_PLATE_SIGMA_DEFAULT
    if not 0.05 <= sigma <= IN_GRAPH_PLATE_SIGMA_MAX:
        sigma = IN_GRAPH_PLATE_SIGMA_DEFAULT
    return {"enabled": enabled, "blur_radius": int(blur_radius), "sigma": float(sigma)}


def _bounded_float_setting(name: str, default: float, environ: dict) -> float:
    """Read a 0-1-ish float knob, falling back to the shipped default on junk."""

    raw = str(environ.get(name, "")).strip()
    if not raw:
        return float(default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return float(default)
    if not (0.01 <= value <= 1.0):
        return float(default)
    return value


def character_swap_sam_mask_parameters(
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """The in-graph SAM parameters: the package's own example values unless moved."""

    source = os.environ if environ is None else environ
    subject = str(source.get(SAM_MASK_SUBJECT_ENV, "")).strip() or SAM_MASK_SUBJECT_DEFAULT
    expansion_raw = str(source.get(SAM_MASK_EXPANSION_PX_ENV, "")).strip()
    try:
        expansion_px = int(expansion_raw) if expansion_raw else SAM_MASK_EXPANSION_PX_DEFAULT
    except (TypeError, ValueError):
        expansion_px = SAM_MASK_EXPANSION_PX_DEFAULT
    if not (0 <= expansion_px <= 256):
        # H3RelayExpandMask publishes 0-256 px at the prepared resolution.
        expansion_px = SAM_MASK_EXPANSION_PX_DEFAULT
    return {
        "subject": subject[:120],
        "detect_threshold": _bounded_float_setting(
            SAM_MASK_DETECT_THRESHOLD_ENV, SAM_MASK_DETECT_THRESHOLD_DEFAULT, source
        ),
        "track_threshold": _bounded_float_setting(
            SAM_MASK_TRACK_THRESHOLD_ENV, SAM_MASK_TRACK_THRESHOLD_DEFAULT, source
        ),
        "expansion_px": int(expansion_px),
        "max_objects": SAM_MASK_MAX_OBJECTS,
    }


def character_swap_workflow_name(environ: dict[str, str] | None = None) -> str:
    """Which swap template to compile. The SAM-mask one ships on; ``plain`` reverts.

    The mask template is only selected when it is actually on disk: a Studio whose
    template folder lost that file must keep rendering with the graph it always used
    rather than refuse every Shot.
    """

    source = os.environ if environ is None else environ
    requested = str(source.get(CHARACTER_SWAP_WORKFLOW_NAME_ENV, "")).strip()
    if requested.lower() in CHARACTER_SWAP_PLAIN_WORKFLOW_ALIASES:
        return CHARACTER_SWAP_WORKFLOW_NAME
    if requested:
        return requested
    return CHARACTER_SWAP_MASK_WORKFLOW_NAME


def character_swap_workflow_path(
    project_root: str | Path,
    environ: dict[str, str] | None = None,
) -> Path:
    """Resolve the chosen template inside the project, falling back to the plain graph."""

    root = Path(project_root)
    name = character_swap_workflow_name(environ)
    candidate = root / name
    if candidate.is_file():
        return candidate
    # A hand-named file can differ from the constant by letter case alone - the plain graph
    # on this disk is really ``H3-Character-Swap-Relay-V2-API.json`` while the constant is
    # lowercase ``api``.  Windows opens it either way, but a case-sensitive mount would
    # silently downgrade every Shot to the maskless graph, which is the failure this round
    # exists to remove.  Match case-insensitively before falling back.
    folded = name.casefold()
    for sibling in sorted(root.glob("*.json")):
        if sibling.name.casefold() == folded:
            return sibling
    return root / CHARACTER_SWAP_WORKFLOW_NAME


def _character_swap_node_id_by_class(
    workflow: Mapping[str, Mapping[str, Any]], class_name: str
) -> str:
    for node_id, node in workflow.items():
        if isinstance(node, dict) and str(node.get("class_type", "")) == class_name:
            return str(node_id)
    return ""


def _character_swap_sam_subject_node(
    workflow: Mapping[str, Mapping[str, Any]]
) -> str:
    """The CLIPTextEncode whose clip comes from the SAM checkpoint, i.e. the subject box."""

    checkpoint_ids = {
        str(node_id)
        for node_id, node in workflow.items()
        if isinstance(node, dict)
        and str(node.get("class_type", "")) == "CheckpointLoaderSimple"
    }
    if not checkpoint_ids:
        return ""
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type", "")) != "CLIPTextEncode":
            continue
        clip = (node.get("inputs") or {}).get("clip")
        if isinstance(clip, list) and clip and str(clip[0]) in checkpoint_ids:
            return str(node_id)
    return ""


CHARACTER_SWAP_MODEL_IDENTITY_CLASSES = (
    "UNETLoader",
    "VAELoader",
    "LoraLoaderModelOnly",
    "LoraLoader",
    "KSamplerSelect",
    "BasicScheduler",
    "MiniMaxH3SigmaShift",
    "ModelAttentionBackend",
    "SolAttnMiniMaxH3Patcher",
)
CHARACTER_SWAP_TURBO_LORA_MARKER = "turbo"


def _character_swap_lora_nodes_by_marker(
    workflow: Mapping[str, Mapping[str, Any]], marker: str
) -> list[str]:
    rows = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type", "")) not in {"LoraLoaderModelOnly", "LoraLoader"}:
            continue
        name = str((node.get("inputs") or {}).get("lora_name", "")).casefold()
        if marker in name:
            rows.append(str(node_id))
    return rows


def _character_swap_identity_signature(workflow) -> dict[str, list[dict[str, Any]]]:
    """The constants that decide which model is actually on the wire, grouped by class.

    Links are left out because a hand-saved graph renames nodes freely, and node
    ``prompt`` / ``*-preview`` fields are left out because they are neither model nor
    submitted behaviour.  Rows are sorted per class so two graphs stay comparable even
    when the author numbered their two ``VAELoader`` nodes the other way round.
    """

    rows: dict[str, list[dict[str, Any]]] = {}
    for node in (workflow or {}).values():
        if not isinstance(node, dict):
            continue
        class_name = str(node.get("class_type", ""))
        if class_name not in CHARACTER_SWAP_MODEL_IDENTITY_CLASSES:
            continue
        constants: dict[str, Any] = {}
        for key, value in (node.get("inputs") or {}).items():
            if isinstance(value, list) or key == "prompt" or key.endswith("-preview"):
                continue
            constants[key] = value
        rows.setdefault(class_name, []).append(constants)
    for bucket in rows.values():
        bucket.sort(key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
    return rows


def _character_swap_reference_source(workflow) -> str:
    """Which class of node Picture 1 actually arrives at the reference slot through."""

    graph = workflow or {}
    for node in graph.values():
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type", "")) != "MiniMaxH3ReferenceToVideo":
            continue
        link = (node.get("inputs") or {}).get("ref_images.ref_image_0")
        if isinstance(link, list) and link:
            source = graph.get(str(link[0]))
            if isinstance(source, dict):
                return str(source.get("class_type", ""))
            return str(link[0])
    return ""


def character_swap_model_identity_drift(
    workflow: Mapping[str, Any],
    base_template: Mapping[str, Mapping[str, Any]] | None,
) -> list[str]:
    """Name every model-side difference between two graphs, changing neither one.

    The shape of an accepted take depends on the base model, the Turbo LoRA and the swap
    adapter's strength; a graph saved by hand can drift on all three without anyone
    touching a mask.  The old ``-api-mask.json`` is the proof - its ``UNETLoader`` was a
    community fine-tune (``Minimax-h3_Singularity_x_10Eros-Max_PRISM_int8``), its Turbo
    was a different file at strength 0.8, and it put a 2x RTX upscale in front of
    Picture 1 where every recent manifest records ``reference_upscale_node_id: ""``.

    This does **not** rewrite anything.  The mask graph is the director's own file, so a
    silent overwrite of his model choice would be worse than the drift; the rows land in
    the manifest as a warning that says "look at the template", and
    ``H3-Character-Swap-Relay-V2-API-WITHMASK.json`` currently produces no rows at all,
    which is the offline proof that the only real change is the SAM 3 edit mask.
    """

    if not isinstance(base_template, Mapping) or not base_template:
        return []
    left = _character_swap_identity_signature(base_template)
    right = _character_swap_identity_signature(workflow)
    drift: list[str] = []
    for class_name in sorted(set(left) | set(right)):
        mine_rows = right.get(class_name) or []
        for index, base_row in enumerate(left.get(class_name, ())):
            if index >= len(mine_rows):
                drift.append(f"{class_name} #{index + 1}: 新图里没有对应的节点")
                continue
            mine = mine_rows[index]
            for key in sorted(set(base_row) | set(mine)):
                if base_row.get(key) != mine.get(key):
                    drift.append(
                        f"{class_name} #{index + 1}.{key}: "
                        f"{base_row.get(key)!r} -> {mine.get(key)!r}"
                    )
    base_source = _character_swap_reference_source(base_template)
    mine_source = _character_swap_reference_source(workflow)
    if base_source and mine_source and base_source != mine_source:
        drift.append(f"Picture 1 进参考槽的来源: {base_source} -> {mine_source}")
    return drift


def character_swap_sam_mask_union_subject(
    target_nouns: Iterable[str] | None = None,
    environ: dict[str, str] | None = None,
) -> str:
    """The words the in-graph detector is conditioned on: every body kind in the Shot.

    ``H3_CHARACTER_SWAP_SAM_MASK_SUBJECT`` stays the base it always was (``person``); the Shot's own
    measured target nouns are appended, which is exactly how the composite's tracking phrase is
    built (``smart_render_worker.sam31_text_prompt`` -> ``person, gundam, godzilla``).  The word list
    is what makes the detector return one object per figure - with the bare ``person`` it returns one
    object for the whole frame and every pass then repaints the same person.
    """

    source = os.environ if environ is None else environ
    merged = str(source.get(SAM_MASK_SUBJECT_ENV, "")).strip() or SAM_MASK_UNION_SUBJECT_BASE
    seen = {token for token in merged.replace(",", " ").lower().split() if token}
    for noun in target_nouns or []:
        token = " ".join(str(noun).strip().lower().split())
        if not token or token in seen:
            continue
        candidate = f"{merged}, {token}"
        if len(candidate) > SAM_MASK_UNION_SUBJECT_MAX_CHARS:
            break
        seen.add(token)
        merged = candidate
    return merged[:SAM_MASK_UNION_SUBJECT_MAX_CHARS]


def character_swap_sam_mask_selection(
    source_role_id: str = "",
    role_boxes: Mapping[str, Sequence[Any]] | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Which object the mask chain follows for THIS pass, decided from the app's own role boxes.

    The relay node offers ``largest | leftmost | rightmost | index``; the engine used to hard-write
    ``largest`` + index 0, which hands every pass in a multi-role Shot the biggest figure.  With one
    figure per side the honest choice is the side this pass is about: left of the other roles means
    ``leftmost``, right means ``rightmost``.  Anything unclear - one role, no box, boxes stacked on
    top of each other - keeps ``largest``, which is what has been rendering.
    """

    source = os.environ if environ is None else environ
    autoselect = str(source.get(SAM_MASK_AUTOSELECT_ENV, "")).strip().lower() not in {
        "0", "off", "false", "no", "legacy", "largest",
    }
    boxes: dict[str, list[float]] = {}
    for role, box in (role_boxes or {}).items():
        key = str(role).strip().upper()
        if not key or not isinstance(box, (list, tuple)) or len(box) != 4:
            continue
        try:
            left, top, right, bottom = (float(value) for value in box)
        except (TypeError, ValueError):
            continue
        if right > left and bottom > top:
            boxes[key] = [left, top, right, bottom]
    role = str(source_role_id or "").strip().upper()
    others = {key: box for key, box in boxes.items() if key != role}
    if not autoselect:
        return {"selection": "largest", "index": 0, "autoselect": False,
                "reason": f"{SAM_MASK_AUTOSELECT_ENV} 关掉：沿用 largest"}
    if not boxes or role not in boxes or not others:
        return {"selection": "largest", "index": 0, "autoselect": True,
                "reason": "镜头里只认得出这一个角色（或这个角色没有框）：沿用 largest"}
    own = (boxes[role][0] + boxes[role][2]) / 2.0
    rival = sum((box[0] + box[2]) / 2.0 for box in others.values()) / float(len(others))
    if own < rival - SAM_MASK_SIDE_MARGIN:
        return {"selection": "leftmost", "index": 0, "autoselect": True,
                "reason": f"本角色中心 {own:.3f} 在其余角色 {rival:.3f} 左侧"}
    if own > rival + SAM_MASK_SIDE_MARGIN:
        return {"selection": "rightmost", "index": 0, "autoselect": True,
                "reason": f"本角色中心 {own:.3f} 在其余角色 {rival:.3f} 右侧"}
    return {"selection": "largest", "index": 0, "autoselect": True,
            "reason": f"本角色 {own:.3f} 与其余角色 {rival:.3f} 几乎同侧：沿用 largest"}


def _sam_mask_normalized_box(value: Any) -> list[float]:
    """One plate rectangle as ``[left, top, right, bottom]``; the plate writes it as x/y/w/h."""

    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return []
    try:
        left, top, third, fourth = (float(item) for item in value)
    except (TypeError, ValueError):
        return []
    right, bottom = left + third, top + fourth
    if right > 1.0 + 1e-6 or bottom > 1.0 + 1e-6:
        # A manual override arrives as an absolute box already.
        right, bottom = third, fourth
    if not (0.0 <= left <= 1.0 and 0.0 <= top <= 1.0):
        return []
    if right > left and bottom > top:
        return [max(0.0, left), max(0.0, top), min(1.0, right), min(1.0, bottom)]
    return []


def _sam_mask_union_box(boxes: Sequence[Sequence[Any]]) -> list[float]:
    rows = [box for box in (_sam_mask_normalized_box(item) for item in boxes) if box]
    if not rows:
        return []
    box = [
        min(row[0] for row in rows),
        min(row[1] for row in rows),
        max(row[2] for row in rows),
        max(row[3] for row in rows),
    ]
    return box if box[2] > box[0] and box[3] > box[1] else []


def character_swap_sam_mask_boxes_from_geometry(
    geometry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """This pass's own erased rectangle, and the other roles' rectangles, from its plate geometry.

    Measured on the failed 06:32 neca_6 take
    (``example/godzilla_action_figure_by_neca_6/project/render_jobs/preview_8053966229313392623_
    1794348343547891800.manifest.json``): pass R1 carries ``pieces [[0.0, 0.069445, 0.606356,
    0.343548]]`` / ``face_band [0.0, 0.412993, 0.606356, 0.474424]`` with ``protected_boxes
    [[0.606356, 0.264815, 1.0, 1.0]]``, and pass R2 carries the mirror image - so one pass already
    knows both sides of the frame, in the app's own coordinates, without waiting for any other pass.
    """

    own: list[list[float]] = []
    others: list[list[float]] = []
    if isinstance(geometry, Mapping):
        for key in SAM_MASK_GEOMETRY_KEYS:
            block = geometry.get(key)
            applied = block.get("applied") if isinstance(block, Mapping) else None
            for row in applied or []:
                if not isinstance(row, Mapping):
                    continue
                for piece in [row.get("band"), row.get("face_band"),
                              *(row.get("pieces") or [])]:
                    box = _sam_mask_normalized_box(piece)
                    if box:
                        own.append(box)
                for piece in list(row.get("protected_boxes") or []):
                    box = _sam_mask_normalized_box(piece)
                    if box:
                        others.append(box)
    return {"own": _sam_mask_union_box(own), "others": _sam_mask_union_box(others)}


def character_swap_sam_mask_selection_from_geometry(
    *,
    source_role_id: str = "",
    geometry: Mapping[str, Any] | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Same left/right decision, taken from the plate this very pass is about to render."""

    boxes = character_swap_sam_mask_boxes_from_geometry(geometry)
    own = boxes.get("own") or []
    other = boxes.get("others") or []
    selection = character_swap_sam_mask_selection(
        "SELF", {"SELF": own, "OTHER": other} if own and other else {}, environ=environ
    )
    reason = str(selection.get("reason") or "")
    if own and other:
        reason = f"{reason}（取自本遍压片几何，对面那位来自 protected_boxes）"
    elif not selection.get("autoselect"):
        reason = f"{reason}（压片几何未被查看）"
    else:
        reason = f"{reason}（本遍压片几何给不出对面那位）"
    return {
        "selection": str(selection.get("selection") or "largest"),
        "index": int(selection.get("index") or 0),
        "autoselect": bool(selection.get("autoselect")),
        "reason": reason,
        "own_box": own,
        "other_box": other,
        "source_role_id": str(source_role_id or "").strip().upper(),
    }


def character_swap_sam_mask_recipe(
    *,
    source_role_id: str = "",
    role_boxes: Mapping[str, Sequence[Any]] | None = None,
    geometry: Mapping[str, Any] | None = None,
    target_nouns: Iterable[str] | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One call from the Studio: the words and the selector for this pass's in-graph SAM mask.

    The side comes from the director's own per-role boxes when he drew them; when that field is
    empty - which is what the neca_6 project recorded on 11-11 06:32 - it falls back to the plate
    geometry this pass built for itself, which already knows both figures.
    """

    boxes = {
        str(role).strip().upper(): box
        for role, box in (role_boxes or {}).items()
        if _sam_mask_normalized_box(box)
    }
    if boxes:
        selection = character_swap_sam_mask_selection(
            source_role_id=source_role_id, role_boxes=role_boxes, environ=environ
        )
        selection["box_source"] = "导演的角色框（source_role_bbox_overrides）"
    else:
        selection = character_swap_sam_mask_selection_from_geometry(
            source_role_id=source_role_id, geometry=geometry, environ=environ
        )
        selection["box_source"] = "本遍压片几何（identity_suppression_geometry + protected_boxes）"
    autoselect = bool(selection.get("autoselect"))
    return {
        "subject_text": (
            character_swap_sam_mask_union_subject(target_nouns, environ=environ)
            if autoselect else ""
        ),
        "selection": str(selection.get("selection") or "largest"),
        "index": int(selection.get("index") or 0),
        "autoselect": autoselect,
        "reason": str(selection.get("reason") or ""),
        "box_source": str(selection.get("box_source") or ""),
        "own_box": list(selection.get("own_box") or []),
        "other_box": list(selection.get("other_box") or []),
    }


def apply_character_swap_sam_mask_graph(
    workflow: dict[str, Any],
    *,
    parameters: Mapping[str, Any] | None = None,
    subject_text: str = "",
    selection: str = "",
    selection_index: int = 0,
    plate_parameters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Connect and parameterise the in-graph SAM 3 edit mask; never fail a Shot.

    A graph without ``H3RelayExpandMask`` is the plain template: this returns
    ``{"in_graph_sam_mask": False}`` and does not touch a single byte, so reverting
    the template really is a no-op rather than a rewrite.

    ``subject_text`` and ``selection`` come from :func:`character_swap_sam_mask_recipe` and say,
    per pass, which body kinds to look for and which of them this pass repaints.  Left empty they
    fall back to the knobs, which is the behaviour every take up to Round 113 rendered with.
    """

    expand_id = _character_swap_node_id_by_class(workflow, "H3RelayExpandMask")
    if not expand_id:
        return {"in_graph_sam_mask": False, "sam_mask_reason": "模板里没有 SAM 遮罩链"}
    settings = dict(parameters or character_swap_sam_mask_parameters())
    window_id = _character_swap_node_id_by_class(workflow, "H3RelayWindowInputs")
    edit_mask_id = _character_swap_node_id_by_class(workflow, "H3RelayApplyEditMask")
    detect_id = _character_swap_node_id_by_class(workflow, "SAM3_Detect")
    track_id = _character_swap_node_id_by_class(workflow, "SAM3_VideoTrack")
    to_mask_id = _character_swap_node_id_by_class(workflow, "SAM3_TrackToMask")
    select_id = _character_swap_node_id_by_class(workflow, "H3RelaySelectMask")
    subject_id = _character_swap_sam_subject_node(workflow)

    reason = ""
    link_source = ""
    if not window_id or not edit_mask_id:
        reason = "缺 H3RelayWindowInputs 或 H3RelayApplyEditMask"
    else:
        window_inputs = workflow[window_id].setdefault("inputs", {})
        if not isinstance(window_inputs, dict):
            reason = "H3RelayWindowInputs 的 inputs 不是字典"
        else:
            link = window_inputs.get("mask")
            already = isinstance(link, list) and link and str(link[0]) == expand_id
            if not already:
                # The 11-01 saved template left this empty, which is why that graph
                # never produced a frame; the director's own WITHMASK export already
                # carries window.mask <- expand_mask.0, and that link is never
                # overwritten here - only a missing one is filled.
                window_inputs["mask"] = [expand_id, 0]
                link_source = "引擎按节点包配方补接"
            else:
                link_source = "导演自己图里已接好"

    if detect_id:
        workflow[detect_id].setdefault("inputs", {})["threshold"] = float(
            settings["detect_threshold"]
        )
    if track_id:
        track_inputs = workflow[track_id].setdefault("inputs", {})
        track_inputs["detection_threshold"] = float(settings["track_threshold"])
        track_inputs["max_objects"] = int(settings["max_objects"])
    workflow[expand_id].setdefault("inputs", {})["expansion_px"] = int(
        settings["expansion_px"]
    )
    mask_words = str(subject_text or "").strip()[:SAM_MASK_UNION_SUBJECT_MAX_CHARS]
    written_subject = mask_words or str(settings["subject"])
    if subject_id:
        workflow[subject_id].setdefault("inputs", {})["text"] = written_subject
    mask_selection = str(selection or "").strip().lower()
    if mask_selection not in SAM_MASK_SELECTABLE:
        mask_selection = "largest"
    mask_index = int(selection_index or 0) if mask_selection == "index" else 0
    if select_id:
        workflow[select_id].setdefault("inputs", {}).update(
            {"selection": mask_selection, "index": mask_index}
        )

    plate_rows = character_swap_apply_in_graph_plate_graph(
        workflow, window_id=window_id, parameters=plate_parameters
    )

    repaired = bool(
        window_id and isinstance((workflow[window_id].get("inputs") or {}).get("mask"), list)
    )
    return {
        "in_graph_sam_mask": True,
        "sam_mask_link_repaired": bool(repaired),
        "sam_mask_link_source": link_source,
        "sam_mask_reason": reason,
        "sam_mask_window_node_id": window_id,
        "sam_mask_expand_node_id": expand_id,
        "sam_mask_edit_node_id": edit_mask_id,
        "sam_mask_detect_node_id": detect_id,
        "sam_mask_track_node_id": track_id,
        "sam_mask_to_mask_node_id": to_mask_id,
        "sam_mask_select_node_id": select_id,
        "sam_mask_subject_node_id": subject_id,
        "sam_mask_subject": written_subject,
        "sam_mask_subject_source": "镜头内全体名词" if mask_words else "导演旋钮",
        "sam_mask_selection": mask_selection,
        "sam_mask_selection_index": mask_index,
        "sam_mask_detect_threshold": float(settings["detect_threshold"]),
        "sam_mask_track_threshold": float(settings["track_threshold"]),
        "sam_mask_expansion_px": int(settings["expansion_px"]),
        "sam_mask_max_objects": int(settings["max_objects"]),
        **plate_rows,
    }


def character_swap_apply_in_graph_plate_graph(
    workflow: dict[str, Any],
    *,
    window_id: str = "",
    parameters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Erase the plate along the SAM mask itself: blurred inside it, untouched outside it.

    Four passes of the same Shot, rendered by hand on the director's ComfyUI and measured in
    ``testing/_sheet/115/round115_r1_four_way.png``, show that the erase and the mask must be the same
    shape: with no erase the source identity survives, with a head-sized erase only a head layer appears,
    and with a rectangle wider than the mask the uncovered part of that rectangle stays a grey blur
    forever.  ``H3RelayWindowInputs`` publishes the windowed frames on pin 0 and the windowed mask on
    pin 1 - the exact pair ``H3RelayApplyEditMask`` already repaints with - so those two pins are what
    the plate is rebuilt from, and the only wire that moves is ``VAEEncode.pixels``.

    Never raises: a Shot that cannot be rewired keeps the Studio's band plate and says why.
    """

    rows = {
        "in_graph_plate": False,
        "in_graph_plate_reason": "",
        "in_graph_plate_blur_node_id": "",
        "in_graph_plate_composite_node_id": "",
        "in_graph_plate_encode_node_id": "",
    }
    settings = dict(parameters or character_swap_in_graph_plate_parameters())
    rows["in_graph_plate_blur_radius"] = int(settings["blur_radius"])
    rows["in_graph_plate_sigma"] = float(settings["sigma"])
    if not settings["enabled"]:
        rows["in_graph_plate_reason"] = "导演旋钮关掉了图内压片（沿用 Studio 的压片带）"
        return rows
    if not window_id or not isinstance(workflow.get(window_id), dict):
        rows["in_graph_plate_reason"] = "缺 H3RelayWindowInputs，压片带原样交给模型"
        return rows
    encode_id = ""
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or str(node.get("class_type")) != "VAEEncode":
            continue
        link = (node.get("inputs") or {}).get("pixels")
        if isinstance(link, list) and link and str(link[0]) == str(window_id):
            encode_id = str(node_id)
            break
    if not encode_id:
        rows["in_graph_plate_reason"] = "VAEEncode 的 pixels 不是从 H3RelayWindowInputs 来的"
        return rows
    suffix = 0
    while True:
        blur_id = "plate_blur" if not suffix else f"plate_blur_{suffix}"
        composite_id = "plate_masked" if not suffix else f"plate_masked_{suffix}"
        if blur_id not in workflow and composite_id not in workflow:
            break
        suffix += 1
    workflow[blur_id] = {
        "class_type": "ImageBlur",
        "_meta": {"title": "Plate blur inside the SAM mask"},
        "inputs": {
            "image": [window_id, 0],
            "blur_radius": int(settings["blur_radius"]),
            "sigma": float(settings["sigma"]),
        },
    }
    workflow[composite_id] = {
        "class_type": "ImageCompositeMasked",
        "_meta": {"title": "Plate: sharp outside the SAM mask"},
        "inputs": {
            "destination": [window_id, 0],
            "source": [blur_id, 0],
            "x": 0,
            "y": 0,
            "resize_source": False,
            "mask": [window_id, 1],
        },
    }
    workflow[encode_id].setdefault("inputs", {})["pixels"] = [composite_id, 0]
    rows.update(
        {
            "in_graph_plate": True,
            "in_graph_plate_reason": "遮罩内糊、遮罩外留原片；只挪了一根 VAEEncode.pixels 的线",
            "in_graph_plate_blur_node_id": blur_id,
            "in_graph_plate_composite_node_id": composite_id,
            "in_graph_plate_encode_node_id": encode_id,
        }
    )
    return rows


def compile_character_swap_pass(
    template: Mapping[str, Mapping[str, Any]],
    *,
    source_filename: str,
    reference_filename: str,
    prompt: str,
    seed: int,
    megapixels: float,
    output_prefix: str,
    runtime_source: bool = False,
    output_upscale: bool = False,
    model_identity_template: Mapping[str, Mapping[str, Any]] | None = None,
    sam_mask_subject_text: str = "",
    sam_mask_selection: str = "",
    sam_mask_selection_index: int = 0,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Patch one API-format Relay workflow for one character pass.

    Relay V2 expands the old all-in-one node into a native ComfyUI loop.  Keep
    legacy compilation available for old saved jobs, while every newly compiled
    Studio job uses ``H3-Character-Swap-Relay-V2-api.json``.

    ``output_upscale`` is the Preview-only request for RTX Video Super
    Resolution on the *generated* clip.  Preview costs its money at 480 and buys
    back legibility on the way out; Final Render leaves the flag off and keeps
    the template's own pixels, byte for byte.
    """

    workflow = deepcopy(dict(template))
    generation = character_swap_workflow_generation(workflow)
    video_id = node_id_for_class(workflow, "LoadVideo")
    image_id = node_id_for_class(workflow, "LoadImage")
    save_id = node_id_for_class(workflow, "SaveVideo")

    workflow[video_id].setdefault("inputs", {})["file"] = (
        "__H3_RELAY_PREVIOUS_PASS__.mp4" if runtime_source else source_filename
    )
    workflow[image_id].setdefault("inputs", {})["image"] = reference_filename
    # Round 51: the caller's megapixels is a request, not a decision.  Preview
    # asks for 0.5 and every such take in the newest video aged the character, so
    # the floor below lifts it onto the bucket the accepted 1.0 MP takes used.
    # ``H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0`` puts the old behaviour back
    # verbatim; ``effective_megapixels`` is reported in the pass contract so a
    # manifest can never again hide which bucket actually went up the wire.
    # Round 53 re-opens that floor on evidence rather than on a global default:
    # the same sheet, the same frames and the same clauses aged the character at
    # the 480 bucket and satisfied the director at 768, so the bucket now follows
    # the one thing that predicts the drift - whether this compiled prompt
    # carries the apparent-age lock.  The request and the reason both stay in the
    # contract, so the extra cost is never paid silently.
    age_lock_in_prompt = character_swap_apparent_age_lock_in_prompt(prompt)
    megapixel_decision = character_swap_megapixel_decision(
        megapixels, apparent_age_lock=age_lock_in_prompt
    )
    effective_megapixels = float(megapixel_decision["effective_megapixels"])
    # What the reference conditioning will actually be told, and where that text came from.  The
    # v2 branch may replace it with the author's published sentence; the v1 branch keeps Studio's.
    written_prompt = prompt
    swap_prompt_source = "Studio 编译提示词"
    if not character_swap_official_prompt_recipe_enabled():
        # Round 122: contract 要能说清这几个字到底是谁写的。之前只写"Studio 编译提示词"，
        # 于是导演在自己提交的文件里删掉的条款被另一个文件收割回来加上去，contract 也看不出来。
        harvested_name = character_swap_prompt_source_name()
        swap_prompt_source = "Studio 编译提示词" + (
            f"（收割自 {harvested_name} + Studio 条款）"
            if character_swap_prompt_appendix_enabled()
            else f"（收割自 {harvested_name}，未追加条款）"
        )
    if generation == "v2":
        prompt_id = node_id_for_class(workflow, "MiniMaxH3ReferenceToVideo")
        prepare_id = node_id_for_class(workflow, CHARACTER_SWAP_PREPARE_CLASS)
        plan_id = node_id_for_class(workflow, CHARACTER_SWAP_RELAY_CLASS)
        schedule_id = node_id_for_class(workflow, "BasicScheduler")
        guider_id = node_id_for_class(workflow, "CFGGuider")
        # The native loop emits an ``executing`` event every time one Relay
        # window is appended.  Studio uses that node as the exact window
        # progress clock instead of waiting for the old monolithic progress bar.
        progress_id = node_id_for_class(workflow, "H3RelayAppendWindow")
        progress_mode = "executing"

        # Round 117: what goes to the reference node is the author's own sentence, not Studio's essay
        # (see CHARACTER_SWAP_RECIPE_PROMPT).  The apparent-age lock above is still read from the
        # Studio's prompt, so the resolution bucket this Shot earns does not move with the wording -
        # only the text the model actually sees changes, which is what the director asked for.
        if character_swap_official_prompt_recipe_enabled():
            written_prompt = CHARACTER_SWAP_RECIPE_PROMPT
            swap_prompt_source = "官方 api.json 原句（akatz-ai/MiniMax-H3-Character-Swap-LoRA）"
        workflow[prompt_id].setdefault("inputs", {})["prompt"] = written_prompt
        prepare = workflow[prepare_id].setdefault("inputs", {})
        prepare["resolution"] = character_swap_prepare_resolution(
            effective_megapixels
        )
        prepare["duration_seconds"] = 0
        prepare.setdefault("missing_audio", "silence")
        plan = workflow[plan_id].setdefault("inputs", {})
        plan.update({
            "window_frames": str(RELAY_WINDOW_FRAMES),
            "history_frames": str(RELAY_HISTORY_FRAMES),
            "seed": int(seed),
            "schedule": "adaptive",
            "seed_mode": "fixed",
            # Never reuse per-window overrides exported from another Project.
            "seed_overrides": "{}",
        })
        schedule = workflow[schedule_id].setdefault("inputs", {})
        schedule.update({"steps": 8, "denoise": 1})
        # Preserve V2's authored scheduler (currently ``normal``); it is part
        # of the supplied graph rather than an old Studio default.
        schedule.setdefault("scheduler", "normal")
        workflow[guider_id].setdefault("inputs", {})["cfg"] = 1
        relay_id = plan_id
    else:
        prompt_id = node_id_for_class(workflow, "PrimitiveStringMultiline")
        prepare_id = node_id_for_class(
            workflow, LEGACY_CHARACTER_SWAP_PREPARE_CLASS
        )
        relay_id = node_id_for_class(
            workflow, LEGACY_CHARACTER_SWAP_RELAY_CLASS
        )
        progress_id = relay_id
        progress_mode = "progress"
        workflow[prompt_id].setdefault("inputs", {})["value"] = prompt
        prepare = workflow[prepare_id].setdefault("inputs", {})
        prepare["resolution"] = character_swap_prepare_resolution(
            effective_megapixels
        )
        prepare["duration_seconds"] = 0
        relay = workflow[relay_id].setdefault("inputs", {})
        relay.update({
            "window_frames": str(RELAY_WINDOW_FRAMES),
            "history_frames": str(RELAY_HISTORY_FRAMES),
            "seed": int(seed),
            "steps": 8,
            "cfg": 1,
            "scheduler": "simple",
            "denoise": 1,
            "window_controls": "{}",
        })
    # Round 112: if this graph carries the SAM 3 edit-mask chain, connect it and set
    # the package's own thresholds before anything else touches the nodes.  The plain
    # template has no H3RelayExpandMask, so this is a verified no-op there and the
    # revert is the template switch, not a code change.
    sam_mask_rows = apply_character_swap_sam_mask_graph(
        workflow,
        subject_text=str(sam_mask_subject_text or ""),
        selection=str(sam_mask_selection or ""),
        selection_index=int(sam_mask_selection_index or 0),
    )
    # Round 112: a hand-saved graph can drift on things that are not the mask at all -
    # the old -api-mask file carried a community fine-tune, a different Turbo LoRA at
    # 0.8 and an RTX enhancer in front of Picture 1.  The director's WITHMASK graph was
    # measured against the graph that rendered the accepted takes and drifts on nothing,
    # so this only records the comparison.  It deliberately does not rewrite his graph:
    # an unexpected line in the manifest means "look at the template", not "the Studio
    # quietly changed my model".
    model_identity_drift_rows = character_swap_model_identity_drift(
        workflow, model_identity_template
    )
    # Round 49 manual parity, written explicitly rather than inherited.  Three
    # of these settings used to reach ComfyUI only because this compiler never
    # touched them, so any re-export of the template could have changed them
    # without a word in the Job or the manifest.
    #
    #   * the Character-Swap LoRA strength is clamped to the published 1.0-1.5
    #     range (the Turbo LoRA is deliberately untouched - 0.8 is its authored
    #     value and it is a different adapter);
    #   * ``ref_image_size`` is set to the graph's own mode instead of left to
    #     whatever a re-export wrote;
    #   * the RTX Video Super Resolution node that 2x-upscales Picture 1 is
    #     reported in the contract, so a silently missing upscale is visible in
    #     the manifest rather than looking like "Studio never upscales the
    #     reference".
    swap_lora_strengths: list[float] = []
    swap_lora_strength_source = "图里没有 character_swap 适配器"
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type", "")) not in {
            "LoraLoaderModelOnly",
            "LoraLoader",
        }:
            continue
        inputs = node.setdefault("inputs", {})
        if not isinstance(inputs, dict):
            continue
        if "character_swap" not in str(inputs.get("lora_name", "")).casefold():
            continue
        if "strength_model" in inputs:
            # Round 117: the card and the README both say strength 1 for this adapter, so the
            # published number wins over whatever a re-export baked into the template; the clamp still
            # applies, and one knob line hands the graph's own number back.
            recipe = character_swap_lora_recipe_strength(inputs.get("strength_model"))
            inputs["strength_model"] = float(recipe["strength"])
            swap_lora_strength_source = str(recipe["source"])
            swap_lora_strengths.append(float(inputs["strength_model"]))
    ref_image_size = (
        os.environ.get(CHARACTER_SWAP_REF_IMAGE_SIZE_ENV, "").strip()
        or CHARACTER_SWAP_REF_IMAGE_SIZE_DEFAULT
    )
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs")
        if isinstance(inputs, dict) and "ref_image_size" in inputs:
            inputs["ref_image_size"] = ref_image_size
    upscale_node_id = ""
    upscale_scale = 0.0
    upscale_scale_source = "template"
    upscale_scale_override = character_swap_ref_upscale_scale_override()
    upscale_quality = ""
    upscale_quality_source = "template"
    upscale_quality_override = character_swap_ref_upscale_quality_override()
    upscale_strength = 0.0
    upscale_strength_source = "template"
    upscale_strength_override = character_swap_ref_upscale_strength_override()
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") != CHARACTER_SWAP_REFERENCE_UPSCALE_CLASS:
            continue
        upscale_node_id = str(node_id)
        inputs = node.get("inputs") or {}
        if isinstance(inputs, dict):
            scale_key = ""
            for key in CHARACTER_SWAP_REF_UPSCALE_SCALE_KEYS:
                value = inputs.get(key)
                if isinstance(value, (int, float)):
                    scale_key = key
                    upscale_scale = float(value)
                    break
            if not scale_key and "resize_type" in inputs:
                # The node names its multiplier input ``resize_type.scale``
                # alongside the mode string; a template that only shipped the
                # mode still has to receive the multiplier.
                scale_key = CHARACTER_SWAP_REF_UPSCALE_SCALE_KEYS[0]
            if upscale_scale_override is not None and scale_key:
                inputs[scale_key] = int(upscale_scale_override)
                upscale_scale = float(upscale_scale_override)
                upscale_scale_source = "environment"
            quality_key = next(
                (
                    key
                    for key in CHARACTER_SWAP_REF_UPSCALE_QUALITY_KEYS
                    if isinstance(inputs.get(key), str)
                ),
                "",
            )
            if quality_key:
                upscale_quality = str(inputs[quality_key])
            if upscale_quality_override and quality_key:
                inputs[quality_key] = upscale_quality_override
                upscale_quality = upscale_quality_override
                upscale_quality_source = "environment"
            strength_key = next(
                (
                    key
                    for key in CHARACTER_SWAP_REF_UPSCALE_STRENGTH_KEYS
                    if isinstance(inputs.get(key), (int, float))
                ),
                "",
            )
            if strength_key:
                try:
                    upscale_strength = float(inputs[strength_key])
                except (TypeError, ValueError):
                    upscale_strength = 0.0
            if upscale_strength_override is not None and strength_key:
                inputs[strength_key] = upscale_strength_override
                upscale_strength = upscale_strength_override
                upscale_strength_source = "environment"
        break
    # Round 67: the enhancer above sharpened the *reference*; this one sharpens
    # the *answer*.  Preview pays for generation at the 480 bucket and buys its
    # legibility back with RTX Video Super Resolution on the finished clip, so
    # the director reads a face without paying for a 1.0 MP take.  The insert
    # runs after the reference loop above (which stops at the template's own
    # node) so the two RTX nodes never fight over one link, and the returned
    # ``reference_upscale_node_id`` still names the authored node.
    output_upscale_rows = character_swap_output_upscale_contract_rows(
        workflow,
        save_node_id=save_id,
        requested=bool(output_upscale),
    )
    workflow[save_id].setdefault("inputs", {})["filename_prefix"] = output_prefix
    workflow_contract: dict[str, Any] = {
        "workflow_generation": generation,
        "source_loader_node_id": video_id,
        "source_loader_input": "file",
        "reference_loader_node_id": image_id,
        "reference_loader_input": "image",
        "relay_node_id": progress_id,
        "relay_progress_mode": progress_mode,
        "relay_plan_node_id": relay_id,
        "prompt_node_id": prompt_id,
        "swap_lora_max_strength": (
            max(swap_lora_strengths) if swap_lora_strengths else 0.0
        ),
        "swap_lora_ceiling": CHARACTER_SWAP_LORA_MAX_STRENGTH,
        # Round 117: the manifest has to say which prompt the model was actually handed and which
        # strength the adapter got, because those two were the only published numbers our graph
        # disagreed with.  Studio's own text stays in the record even when it is not the one submitted.
        "swap_prompt": written_prompt,
        "swap_prompt_source": swap_prompt_source,
        "swap_prompt_official": written_prompt == CHARACTER_SWAP_RECIPE_PROMPT,
        "swap_prompt_studio": prompt,
        "swap_lora_strength_source": swap_lora_strength_source,
        "reference_upscale_node_id": upscale_node_id,
        "reference_upscale_scale": upscale_scale,
        "reference_upscale_scale_source": upscale_scale_source,
        "reference_upscale_scale_override": upscale_scale_override,
        # Round 59: how much of the reference the enhancer is allowed to invent.
        # ``scale`` says how many pixels appeared; ``quality`` and ``strength``
        # say whether they were interpolated or guessed by a model, which is the
        # difference between "the reference was soft" and "the reference grew
        # wrinkles it never had".
        "reference_upscale_quality": upscale_quality,
        "reference_upscale_quality_source": upscale_quality_source,
        "reference_upscale_quality_override": upscale_quality_override,
        "reference_upscale_strength": upscale_strength,
        "reference_upscale_strength_source": upscale_strength_source,
        "reference_upscale_strength_override": upscale_strength_override,
        "reference_image_size": ref_image_size,
        # Round 51: which prepare bucket actually went up the wire, and the two
        # numbers that decided it.  A manifest that only carries the caller's
        # request cannot show that a 0.5 MP Preview silently rendered 800x1216,
        # which is the difference between "the age lock was ignored" and "the age
        # lock was never on the bucket that obeys it".
        "relay_prepare_node_id": prepare_id,
        "relay_prepare_resolution": str(prepare.get("resolution", "")),
        "requested_megapixels": float(megapixels),
        "effective_megapixels": float(effective_megapixels),
        # Which rule produced the number that chose the bucket: the director's
        # own request, an environment knob, the automatic age-lock floor, or the
        # shipped default.  ``effective_megapixels`` on its own cannot distinguish
        # "Preview asked for 1.0" from "Studio refused to age the character on a
        # 0.5 MP bucket", and that difference is the whole 70-minute question.
        "megapixel_floor": float(megapixel_decision["megapixel_floor"]),
        "megapixel_floor_reason": str(
            megapixel_decision["megapixel_floor_reason"]
        ),
        "megapixel_floor_applied": bool(
            megapixel_decision["megapixel_floor_applied"]
        ),
        "apparent_age_lock_in_prompt": age_lock_in_prompt,
    }
    # Round 112: which SAM mask chain actually went up the wire, including whether
    # Studio had to repair the saved template's unconnected H3RelayWindowInputs.mask
    # (a required input of H3RelayApplyEditMask).  Without these rows a manifest
    # cannot tell "SAM 3 edged the swap" from "ffmpeg pasted an edge on afterwards".
    workflow_contract.update(sam_mask_rows)
    # Round 112: the model-side comparison against the graph that rendered the accepted
    # output.  Empty list means the only real difference between the two graphs is the
    # SAM 3 edit mask, which is exactly what this round is betting the Preview on.
    workflow_contract["model_identity_drift"] = model_identity_drift_rows
    workflow_contract.update(output_upscale_rows)
    return workflow, workflow_contract

