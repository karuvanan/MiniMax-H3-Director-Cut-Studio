"""Run hidden H3 segments sequentially and assemble one continuous master.

This worker intentionally keeps only one ComfyUI prompt in flight while keeping
the H3 model resident across normal Segment boundaries.  It persists a resumable
manifest, can inject a preceding-segment continuity anchor into a free reference
slot, releases memory mid-job only for a real CUDA OOM, and performs one final
ComfyUI model/VRAM release after the assembled Master is complete.
"""

from __future__ import annotations

import argparse
from array import array
from copy import deepcopy
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from subprocess import SubprocessError
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid

from native_speech_guard import NativeSpeechGuard
from datetime import datetime, timezone

from comfy_submit_worker import (
    ComfyConnectionRecoveryTimeout,
    DEFAULT_OUTPUT_DOWNLOAD_RECOVERY_SECONDS,
    DEFAULT_RECONNECT_TIMEOUT_SECONDS,
    _direct_urlopen,
    _request_json,
    download_outputs,
    upload_file,
    wait_for_history,
)
from native_audio_engine import CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT
from media_engine import (
    clamp_seek_to_decode_span,
    decode_safe_video_span,
)
from workflow_engine import validate_portable_media_manifest
from character_swap_engine import (
    MOUTH_BAND_REGISTRATIONS,
    clamp_character_swap_lora_strength,
    mouth_band_registration,
    mouth_region_bbox,
)


VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
MINIMUM_FREE_DISK_BYTES = 2 * 1024**3
# Kept in step with the Studio policy: the worker only reads this as the
# fallback for a job written without an explicit ``render_policy_version``, but
# a stale copy mislabels those manifests.  Policy 59 crops the Identity Sheet
# wardrobe panel to the Shot's framing line and re-weights the panel orientation
# vote so the head keeps its pixels.
# Policy 60 moves that crop line for a close-up Shot from the chest to the hip
# (round-17 97000804 vs 97000824), which changes Picture 1 for every close-up
# candidate.
# Policy 61 is Identity Sheet engine 6 (burned-in captions, titles and social UI
# painted out of an opaque Picture's outer bands before cropping) plus the
# close-up sheet crop lock in the Character Swap prompt.  Both change the
# reference and the compiled prompt, so policy-60 manifests are stale.
# Policy 62 adds the source-costume-ownership and apparent-age clauses to the
# Character Swap prompt and compresses the never-droppable tail back under the
# proven 12 326-character submittable ceiling, and it moves the silent-mouth
# verdict onto the median across the sample timestamps with an upper-face
# relative floor plus a plate-strip ambiguity downgrade.  Prompt and QC both
# change, so policy-61 manifests are stale.
# Policy 63 regenerates every Identity Sheet: engine v7 measures the head as the
# opaque run attached to the skull axis instead of the widest row, so a waving
# cast stops handing the face panel a strip cut at the eyes, and the panel then
# grows into real artwork around the skull until it fills its cell with the face
# centred.  The submitted reference image changes, so policy-62 manifests are
# stale.
# Policy 64 follows the Studio: a medium-framed Shot may take the single-face
# Identity Sheet layout from the plate box instead of only from a suppression
# gate, so the submitted reference image can change and policy-63 manifests are
# stale.
#
# Policy 65 stamps the layout that the Studio recorded on the pass.  The Worker
# never reads those fields - it keeps submitting whatever reference the Job
# names - but a manifest built here must be gradable on its own.
#
# Policy 66 follows the Studio: a Silent Listener pass whose plate box is
# medium-shot visible (area >= 0.050, height >= 0.25) now arrives with a blurred
# head band instead of the raw V1 plate, so the submitted source video changes
# and policy-65 manifests are stale.
# Policy 67 follows the Studio again: that same pass now also softens the
# garment band under the blurred head, so the submitted source video changes
# once more and policy-66 manifests are stale.
# Policy 68 follows the Studio on both inputs at once: the identity-suppression
# plate grows a hair halo over the source actor's wig, and the composed Identity
# Sheet keeps the whole neck-down figure (sheet engine 8), so the submitted source
# video and the submitted reference image both change and policy-67 manifests are
# stale.
# Policy 69 follows the Studio once more on the same input: the garment band under
# the suppressed head grows to the actor's visible body, with protected roles cut
# out of the rectangle, so the submitted source video changes again and
# policy-68 manifests are stale.
# Policy 70 follows the Studio's new Picture 1 choice and adds the whole-body
# gate: the pass now supplies a garment-only reference and the body rectangle it
# is measured on, so a take that only replaced the head is rejected and retried
# instead of being accepted on face pixels alone.  The acceptance decision
# changes even when the input does not, so policy-69 manifests are stale.
# Policy 71 changes the submitted prompt on every suppressed plate: the hair
# ownership clause now states the crown as a fact Picture 1 can paint (bare
# scalp where Picture 1's crown is bald; headwear only where Picture 1 draws
# it) instead of only declaring who owns the region, which round 35e seed
# 923009999 showed was not enough to drop the source actor's wig.  The
# submitted prompt changes, so policy-70 manifests are stale.
# Policy 72 changes the acceptance ruler, not the input: the whole-body
# wardrobe gate now requires the upper half and the lower half of the audited
# garment rectangle to each move away from the source wardrobe, instead of
# accepting a median in which changed legwear can carry an unchanged chest.
# Seed 923010107 passed all three segments on that median while the frames kept
# the cosplayer's sleeves and vest, so policy-71 manifests are stale.
# Policy 74 rewrites the affirmative half of every Silent Listener prompt.  The
# official template says the performance "comes from the person being replaced",
# asks for a "complete visible performance", holds identity "through every
# expression" and retains the source clip's sound — three takes of policies 71
# to 73 all lip-synced with those sentences present alongside the suppression
# contract, so the pass now says body performance, drops "expression", moves the
# clothing clause to body motion, and states that the speech is off screen.  The
# submitted prompt changes, so policy-73 manifests are stale.
# Policy 75 changes what Relay is conditioned on rather than what the prompt
# says.  On a Silent Listener close-up the identity-suppressed plate now
# time-freezes the registered mouth band (``tmix=frames=7``, last stage of the
# plate graph), so the strip of pixels that carried the source lips stops
# articulating while the head still moves.  The silent mouth audit is measured
# against that plate -- ``identity_audit.plate_video_path`` -- and not only
# against raw V1, which is the clip Relay is never shown: policy-74 measured
# 0.108-0.121 on V1 while the plate sat at 0.056-0.073.  The submitted plate and
# the ruler both change, so policy-74 manifests are stale.
# Policy 76 takes the words back rather than the pixels.  Reading the prompt the
# endpoint actually received for seed 923010507, the silent prompt used the words
# speech / speaker / audible / voice / audio five times and every one of them was
# affirmative -- "the speech is off screen", "which is why <Video 1>'s audible
# speech keeps pulling the lips open", "not the audible speaker", "Every audible
# voice in this Shot ... is background sound" -- so the sentences written to
# suppress the mouth were also the only evidence in the caption that the Shot
# contains audible speech at all.  Three measurements say the take is not
# lip-syncing V1 anyway: the submitted silent plate carries no audio track, the
# take's own audio is digital silence (-91 dB, the workflow muxes the plate), and
# the mouth energy sits at 2.5-8 Hz with negative cross-correlation against V1's
# speech envelope.  The silent clauses therefore now declare an empty human vocal
# channel the way this project's verified speech-free audio passes do, instead of
# naming a speech that must stay off screen.  The submitted prompt changes, so
# policy-75 manifests are stale.
# Policy 77 stops the retry ranking from paying for an open mouth.  The p75/p76
# A/B on seed 923010507 re-ran the same three pass seeds under both wordings and
# the de-voiced caption did not quiet the mouth at all -- seg0 articulation excess
# went 0.0477 -> 0.0591 and seg2 0.0589 -> 0.0675 -- so policy 76 is a measured
# null result and the fault that is still deciding the take sits in the selector.
# Picture 1 in this project grins with its teeth showing, and the retry ranking
# decides on a colour histogram, so the take whose mouth is open widest is the one
# that most resembles the reference: seg2 chose between two takes 0.004 apart on
# target similarity whose mouth articulation differed 2x, and the widest mouth won
# both segments.  The likeness used for retry selection now also subtracts the
# articulation excess the silent mouth audit already recorded for that candidate,
# capped and weighted so a large genuine likeness gap still wins while a hairline
# gap cannot out-vote a mouth that kept moving.  Only Silent Listener and
# no-human-voice takes carry that audit, so speaker Shots rank exactly as before.
# Selection changes while the submitted prompt does not, so policy-76 manifests
# are stale.
# Policy 78 changes what goes into the conditioning node.  The single-figure
# passthrough used to be judged on layout cost alone, so the black-shirt Project's
# 252x370 Picture 1 (0.093 MP) went up raw while the Relay workflow upscaled it 4.6x
# for conditioning -- and the graded takes kept the palette but invented age and
# wardrobe, because the pixels that describe them did not exist.  A big figure only
# keeps the raw upload from 0.35 MP up; below that the composed Identity Sheet goes
# up instead, forced to the one-face + whole-figure layout the director validated
# (800x1216 = 0.973 MP).  ``reference_framing`` flips to illustrated_identity_sheet
# for those Shots, so the Relay prompt compiler appends its sheet clauses and the
# submitted prompt changes: policy-77 manifests are stale.
# Policy 80 changes which take the retry budget keeps, not what was submitted.  On
# seed 923010907 the director accepted only ``pass_01_R1_00039_`` and the worker had
# discarded it for ``00040``.  Both takes failed the wardrobe gate, so the ranking
# came down to the colour-histogram cue, and the wardrobe half of that cue is the
# median of three samples at 0.22 / 0.50 / 0.78 of the window.  Reading the frames
# showed why that is the wrong ruler: H3 puts on Picture 1's costume *late*, so the
# accepted take gained a further +0.087 of wardrobe shift after 78 % while the take
# the worker chose lost steam (+0.034).  The audit now also measures the same cue
# over 0.78 / 0.86 / 0.94 as ``wardrobe_shift_late``, and the ranking may use the
# better of the two windows.  The QC verdict and the retry trigger still read the
# original median, so a costume that only arrives in the tail still fails QC and
# still burns a retry -- it just no longer wins the tie-break.  Older manifests have
# no late field and rank exactly as before.
# Policy 81 changes the plate a Silent Listener pass is conditioned on, and
# therefore the prompt that gets submitted.  On seed 923010907 the medium-shot
# silent plate blurred everything below the head down to the bottom edge --
# 50.13 % of the frame -- so the head and the torso read as one colour blob and
# Relay had no garment geometry to map Picture 1 onto: it re-dressed the actor
# from the source cosplayer's leftover palette (invented robes, stray motifs,
# honeycomb texture, "the head changed and nothing else did").  Seed 923011007
# ran the same timeline, sheet and seed with the band off and measured the
# opposite: 5/6 wardrobe rows passed instead of 1/6, mean wardrobe shift
# +0.0972 -> +0.1658, mean target-reference similarity 0.5359 -> 0.5876, and
# Picture 1's black top, blue hem, yellow checkered socks and black sneakers all
# appeared together for the first time in a Studio render.  The same 660
# characters the band was spending are no longer billed, so the Silent Listener
# mouth clause stays inside the prompt budget again.  Manifests compiled under
# policy 80 carry the old wardrobe strategy name and plate token and are stale.
# Policy 82 is Round 49's manual-ComfyUI parity flip, kept in step with
# director_cut_studio.py.  Read back from ComfyUI /history on seeds 923011007
# and 923011008, Studio was submitting a blurred and muted plate, three
# cold-starting 4.288 s segments for one authored 12.864 s Shot, and a
# Character-Swap LoRA ladder of 1.5 -> 1.75 -> 2.0 while the published LoRA
# ceiling is 1.5.  All three now match the user's hand-built graph by default,
# and each is reversible with its own environment switch.  Policy 83 is Round 50:
# the silent mouth gate stops hard-failing a take that merely lands a little over
# its own motion limit (12 % tolerance, advisory above it), the wardrobe gate may
# now pass on a relative gain over the source region instead of only on one
# absolute shift, the age / invented-detail / silhouette clauses grew, and the RTX
# reference upscale multiplier became an explicit override.  The two gate changes
# rewrite every verdict and the prompt change rewrites every compiled prompt, so
# takes and prompts recorded under policy 82 are stale.
#
# Policy 84 is Round 51, kept in step with director_cut_studio.py.  Two changes,
# both about what the take looks like rather than how it was graded.  (1) The
# close-up sheet crop lock stopped requiring a face-dominant box: the plate is now
# measured, and when <Video 1> itself cuts the figure at its bottom edge the
# clause goes up whatever the box measures — the UI's own qualified rectangle
# shrinks a big face to 0.30x0.30 by design, and with the clause absent the
# ``full`` outfit sheet widened a half-body Shot until Picture 1's shoes appeared.
# That rewrites compiled Character Swap prompts for every Shot the probe can read,
# so cached prompts are stale.  (2) The prepare bucket is no longer chosen from
# the director's request alone: the shipped floor is 1.0 MP, so a 0.5 MP Preview
# now renders the 768 bucket (800x1216) that every accepted take used instead of
# 480 (576x864), which is the only bucket where the APPARENT AGE LOCK is obeyed.
# A different bucket is a different take size, so takes recorded under 83 are
# stale.  Both are reversible without touching code:
# ``H3_CHARACTER_SWAP_MIN_MEGAPIXELS=0`` restores the old bucket, and the crop
# lock stays quiet on its own when the probe cannot measure the plate.
# Policy 85 is Round 54, kept in step with director_cut_studio.py.  路線 1 hands
# Relay a clean, un-blurred V1, which means ``suppressed_plate`` is false and
# every hair- and costume-ownership sentence in the engine — written while the
# Studio still blurred the head — went silent.  Seed 2246500964096521702 on
# ``..._black_shirt_and_yellow_pants_4`` graded 「不接受」 for exactly that hole:
# V1's red twin-tail wig and cat ears on Picture 1's bald crown, pink cosplay
# straps left beside Picture 1's vest, and Picture 1's round glasses gone, while
# the identity audit passed because its boxes only span y 15.6-28.8%.  The new
# SOURCE LOOK BELONGS TO THE ERASED ACTOR clause states the ownership on a clean
# plate and costs 525 characters, which leaves the 路線 1 appendix inside its
# 4 200-character recording budget, so every cached Character Swap prompt is
# stale.  Round 53's apparent-age bucket floor shipped inside policy 84 and
# needs no bump of its own: it changes the
# bucket only when the clause is already in the prompt, which policy 84 prompts
# never lacked.
#
# Round 57 bumps it once more.  The policy-85 real shot (same project, master
# seed 8178175072880861825, 0.5 MP / 768 bucket) did retire the wig, the pink
# cosplay straps and the wrong wardrobe, and frames at 0.5/3/6/9/12 s show what
# is left: Picture 1's round spectacles missing in 5 of 5 frames with an orphaned
# temple on a cheek, and an older face than the sheet (stacked forehead creases,
# deepened nasolabial folds, spots and stubble dots on a flat-drawn scalp).  The
# DRAWN EYEWEAR STAYS WORN clause and the rewritten APPARENT AGE LOCK add 905
# characters to a 路線 1 appendix that measured 3 764 characters, so the clause
# set still fits its 4 200-character recording budget, and cached prompts under 86
# are stale.
#
# Round 63 bumps it a third time for the same clause family, and this time the
# evidence is in the submitted text rather than in the frames.  Read back from
# the policy-84 Job the director graded 「效果很好，唯一问题＝老人化」, the prompt
# ComfyUI actually received is 8 204 characters: the author template occupies
# 3 398 of them and carries 0 aging nouns and 0 texture nouns, while the
# 4 806-character appendix Studio added on top carries 7 of each.  The user then
# ran the same live graph by hand and got neither the aged face nor the invented
# background, which pins the drift on the appendix wording and not on the graph,
# the seed or the LoRA strength.  Round 62 rewrote the eight enumerating clauses
# into positive-only sentences, and that cost 127 characters: the appendix of
# the graded shape went 4 560 -> 4 661, far enough past its budget that the
# legacy length guard gave up a third load-bearing clause
# (``source_costume_leaves_plate``) on the silent sheet close-up.  Round 63
# removes only the duplicated restatements from those six clauses — 2 962
# characters across the eight clause sites, 133 fewer than before round 62 — so
# the graded shape now compiles at 4 545 appendix characters and the sheet
# close-up is back to paying with rank 1 and rank 2 only.  Every cached
# Character Swap prompt is stale; H3-Character-Swap-Relay-V2-api.json is
# untouched, which is what the manual comparison proved.
#
# Round 65 bumps it a fourth time, and the evidence is the take the director
# graded 「这一次最完美」: project
# ``a_cartoon_character_with_a_black_shirt_and_yellow_pants_4``, master seed
# 6401000000000000001, policy 87, 0.5 MP asked / 1.0 MP effective under the
# apparent-age floor, pass seed 6759948290807294904, one attempt.  Identity,
# wardrobe, background, plate continuity and crop all read as Picture 1, and the
# aging drift is gone.  What is left is eyewear: Picture 1 draws small rimless
# ovals, the take wears nothing for the first 2.5 s and then the erased
# performer's thick black rectangular frames from about 3 s, with one lens slid
# onto a jaw at 9 s.  ``DRAWN EYEWEAR STAYS WORN`` had bought a mandate the model
# could only honour by reaching into ``<Video 1>``, and the instruction is
# 「不要在画面强制放入眼镜」.  So the mandate becomes a three-way policy
# (``H3_CHARACTER_SWAP_EYEWEAR``; ``uncovered`` is the new default, ``worn``
# restores Round 57 verbatim, ``neutral`` says nothing) and the default branch
# ships THE FACE STAYS UNCOVERED instead, with the ownership sentence and the
# detail keep-list following the same value so the three can never disagree.  The
# graded shape's appendix goes 4 545 -> 4 532 characters, 13 shorter than the
# ``worn`` wording it replaces, with zero dropped clauses, so no gate had to be
# traded.  Cached prompts under 87 are stale; the graph json is still untouched.
#
# Round 69 changes what a cache key is allowed to mean.  The pink-dress A/B put a
# price on prompt drift: the director's accepted take came from a graph that
# appends nothing, the rejected Studio take of the same clip carried 4 050
# appended characters and every rejected frame contains an object no reference
# draws (crown, cat ears, belt, honeycomb).  So (a) the styling appendix is
# *capped* at ``CHARACTER_SWAP_LEAN_STYLING_BUDGET`` and drops weakest-evidence-
# first instead of merely recording the overflow; (b) forbidden objects are no
# longer named in the appendix, since naming is what puts them on screen;
# (c) segments shorter than one relay window merge and one V1 now renders under
# one relay seed; (d) a head-layer-only rebuild whose target-reference similarity
# falls under ``CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR`` is a *blocking*
# verdict and retries, not an advisory pass; (e) a SAM3.1 association under
# ``SAM31_MIN_MATCH_SCORE`` asks for a manual box instead of falling back to
# deltas, and every role in a Shot shares one reference framing class; (f) the
# preview canvas is quantized to ``PREVIEW_CANVAS_MULTIPLE`` so the VSR reassembly
# and the assembled mp4 agree; (g) references with alpha are flattened on white
# before they go on the wire.  Prompts, segment boundaries, QC verdicts and
# canvases compiled under 88 are all stale.  The graph json is still untouched.
#
# Round 91, kept in step with director_cut_studio.py: the reference framing can
# now be decided by cut-out evidence as well as by the BLIP caption, so a Shot
# that used to ship Picture 1 raw can compile as an Identity Sheet instead.  That
# changes the compiled prompt and the reference bytes, so prompts and takes
# cached under 89 for such a Shot are stale.  Nothing here reads the new evidence
# itself — the decision is made when the Job is compiled.
#
# Round 92, kept in step with director_cut_studio.py: the head-layer veto stopped
# averaging away the failure it exists to catch.  The Hallway Approach Project
# shipped a take where the swap collapses back to the V1 performer between 3.5 s
# and 8 s and QC called it an advisory pass, because the veto compares the
# target-reference likeness *median* of three samples against
# ``CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR``: 0.636 / 0.485 / 0.573 recorded a
# 0.573 median above the floor while the 6.98 s sample sat below it.  Replaying
# that take through ``_extract_identity_rgb_frame`` and
# ``target_reference_frame_similarity`` reproduced the recorded median exactly, so
# the measurement was right and the aggregation was wrong.  The floor now binds
# every sample, the audit publishes ``minimum_similarity`` /
# ``worst_timestamp_seconds`` / ``samples``, the verdict publishes
# ``blocking_cause``, and only the ``target_reference_temporal_collapse`` class may
# lift a lean single-take spec by one fresh seed — a seed that already produced the
# target character on both sides of the missed frame deserves the second chance,
# while the structural "the wardrobe never moved" miss keeps the round-86 no-lift
# answer.  Identity QC verdicts are stale under 90; the graph json is still
# untouched.
#
# Round 93, kept in step with director_cut_studio.py: the manifest reports the plate
# suppression instead of leaving it to the filename.  The identity audit spec gains
# ``identity_suppression_strategy`` -- ``"original"`` whenever suppression never ran
# -- together with the ``identity_suppression_geometry`` bands, ``head_band_bottom``,
# ``suppressed_frame_area`` and the crown/halo reports the prompt compiler already
# reads.  Both Hallway runs of 2026-11-07 had to be reverse-engineered from a plate
# path to find out the V1 reached Relay untouched, which is the first fact a director
# needs before grading a take that kept the source hairstyle.  The worker copies the
# audit spec through unchanged, so no worker behaviour moves and policy-91 takes stay
# valid.
#
# Round 94, kept in step with director_cut_studio.py: the close-up plate gate no
# longer trusts a caption this host cannot produce -- BLIP exits 1, so every cast
# picture reaches Studio with ``caption = ''`` and the gate silently stayed shut
# while ``H3_CHARACTER_SWAP_PLATE_SUPPRESSION=1`` was on.  Studio now also accepts the
# cut-out evidence round 91 gave the framing branch, and
# ``identity_suppression_gate`` in the audit spec names which reason applied
# (``off`` / ``caption`` / ``cutout`` / ``none``).  The worker still receives whatever
# plate Studio compiled and copies the audit spec through unchanged, so behaviour
# here does not move; only the policy number does, to keep the two caches agreeing.
#
# Round 95, kept in step with director_cut_studio.py: the compiled prompt of a
# suppressed vanilla pass changes -- the hair sentence grows 167 -> 442 characters
# and claims the hair that hangs below the identity window, which is the only
# source feature the 18:20 take left alive (mane, side length, plait and tie;
# worst sample 0.382527).  The plate is untouched and stays cache-valid, but every
# prompt and take compiled under 94 describes the narrower claim, so it is stale.
# Worker behaviour does not move.
#
# Round 96, kept in step with director_cut_studio.py: the plate gains the band under
# the blurred head whenever the project arms
# ``H3_CHARACTER_SWAP_MEDIUM_SILENT_WARDROBE_BAND_MODE`` (which Studio can now read
# from ``design_ai.env``, together with the width-share that keeps it inside the
# authored box).  A blurred torso rewrites the plate clause and the strategy suffix,
# so every prompt and take compiled under 94 is stale; nothing in the worker moves.
#
# Round 97, kept in step with director_cut_studio.py: that band measured worse on the
# takes (median similarity 0.486057 -> 0.325397 on unit 2) and is back off; the
# silent listener's identity window now has its own share knob, which moves the plate
# and nothing else -- no clause, no strategy suffix.  The plate token changes, so a
# Project that sets the knob rebuilds; worker behaviour does not move.
# Round 101, kept in step with director_cut_studio.py: the hair halo's upward reach is
# now a knob the director can arm from ``design_ai.env`` (all five shipped halo names,
# the kill switch, and a new contour-only cap), because round 100 found the shot-3 hat
# by measuring that reach and had no way to test a different value from the GUI.  The
# engine also marks which rectangles the Shot Visual Editor authored
# (``source_bbox_provenance``), and the plate shortens the reach for contour boxes
# only -- a hand box compiles exactly the band it was graded with.  Every default is the
# shipped number, so a Project that arms nothing rebuilds nothing; arming a halo knob
# changes the plate token, and the worker itself does not move.
# Round 102 prices when the association gate is allowed to fire.  The Godzilla
# Projects are the evidence: godzilla_action_figure_by_neca_5 died at 19:00 and 19:29 on
# 2026-11-08 with R3 0.36 / 0.31, and neca_6 at 21:17 with R1 0.52, every time *after*
# both independent takes and the 345-frame V1 tracking had run -- so a box that could
# never have matched was discovered 20+ minutes and one ComfyUI generation late.  The
# measurement already exists on the V1 side: queue_sam31_v1_role_masks calls the same
# match_sam31_masks_to_passes, so round 69's floor was being applied there too, just
# late.  So the V1 association now runs as a pre-flight before the first take is queued,
# and its mask bundle is handed to the composite stage instead of being re-queued -- the
# same ComfyUI work, moved earlier, and one upload and one tracking pass cheaper.  A
# weak V1 pairing aborts with the same sentinel plus a note that no take was spent,
# because a box that cannot match the source silhouette cannot match the replacement
# built on top of it either (H3 keeps the plate's blocking); the pre-flight is a
# necessary condition, and the round-69 gate on the generated take still runs after it.
# Any other pre-flight failure -- SAM unavailable, OOM, no instances -- is recorded and
# ignored, because an auxiliary cannot be allowed to kill a render that used to run.
# ``H3_CHARACTER_SWAP_SAM31_ASSOCIATION_PREFLIGHT`` picks ``on`` (default) /
# ``advisory`` (record the numbers, never abort) / ``off`` (round-97 order restored), and
# ``H3_CHARACTER_SWAP_SAM31_MIN_MATCH_SCORE`` now sets the floor itself -- default
# 0.70, clamped to [0.05, 1.0], which is the escape hatch round 69's own message asks for
# when the director would rather grade an untrusted pairing than re-draw the box.
# Round 103 stops SAM3.1 from billing a take it cannot actually grade.  neca_6 failed twice
# more on 2026-11-08 -- R1 0.48 at 23:37 even with a box whose V1 association scored
# 0.7726 with a 0.3514 margin, and R2 0.40 at 00:11 -- both times after every independent
# take had been generated, and the mask files those runs left behind say why: the generated
# take kept the replaced performer for 16 of 56 sampled frames (0 to 3.75 s of a 13.975 s
# clip) and spent the rest inside one blob whose median bbox was 0.9111 of the frame, so the
# runner-up for that role was the blob at 0.4244 and no character box could reach 0.70.  A
# measurement that stopped following a person cannot veto a composite.  So a weak pairing
# now first gets one automatic box repair from the silhouette it actually measured --
# neca_6's 0.4795 re-scored 0.7397 on the same winning instance with a 0.1038 margin, which
# is why the guards demand exactly that: the same SAM instance must still win, the margin
# over the runner-up must be at least 0.05, the box may not exceed 0.60 wide (that cap is
# what keeps the hair halo armed; the padded candidate measured 0.7058 and would have moved
# the win to the blob), and it must stay on the person -- containment 1.00 inside the
# V1-confirmed envelope, or 0.329 overlap with the authored box when no V1 evidence exists.
# If the repair is refused the Segment continues on the delta-mask compositor rather than
# failing, because that path locates a replacement by what changed between a take and its
# own source and needs no SAM identity at all.  The refusal reason and the measured envelope
# now ride inside the popup and inside every ``box_auto_repair`` record in the Manifest, and
# the round-102 pre-flight defaults to ``advisory`` -- it measures, it no longer blocks.
# ``H3_CHARACTER_SWAP_SAM31_AUTO_BOX`` picks ``on`` (default) / ``advisory`` (measure and
# record, keep the authored box) / ``off``; ``H3_CHARACTER_SWAP_SAM31_AUTO_BOX_MAX_WIDTH``
# moves the halo-width cap (default 0.60); ``H3_CHARACTER_SWAP_SAM31_WEAK_ASSOCIATION``
# picks ``continue`` (default) / ``abort`` (round-69's hard failure).
# Round 104 -- the two things that actually broke SAM3.1 on neca_6's Godzilla, and the
# two knobs that fix them, measured on that run's own mask videos:
#
#   1. ``H3_CHARACTER_SWAP_SAM31_TEXT_PROMPT``.  The tracking graph had the word
#      ``person`` written into it.  The Godzilla replacement in the right half of the
#      frame therefore produced **no instance at all**: the only human-shaped matte in
#      that pass was the other performer (white share 0.210, union x 0.02-0.69), and the
#      remaining slots were a bottom sliver, one stray top frame and one all-black slot.
#      The Project already says what the picture is -- P1's ``recognition`` reads "BLIP ·
#      Overview: godzilla action figure by neca", P2's "a gundam ..." -- so Studio now
#      copies that text onto the pass row and the phrase grows the noun itself:
#      ``person, godzilla``.  ``H3_CHARACTER_SWAP_SAM31_DETECTION_THRESHOLD`` (default
#      0.35, as before) is the other half of that experiment.
#   2. A slot whose saved video is the **frame** instead of a matte is refused before it
#      can be scored.  Instance 0 measured mid-gray share 0.440-0.558 against
#      0.000-0.007 for a real matte, and ``_mask_frame_stats`` reads any luma >= 96 as
#      filled -- so it joined the association as a body covering 0.91 of the picture in
#      every one of 56 samples and *beat* the only real body for the Godzilla role:
#      0.4517 against 0.4033, margin 0.0484.  That pairing is what the popup printed as
#      ``R2 0.40``, and compositing on it would have smeared the whole frame -- exactly
#      the round-69 failure this gate was built to stop.
#
# Refused slots are recorded, not hidden: they reach the Manifest as
# ``sam31_instance_masks_skipped`` next to the phrase and threshold that were used.
# Nothing is compiled differently: prompts, plates and QC verdicts under 99 stay valid.
#
# Round 105 -- the run that followed (neca_6, 02:08, policy 100) proved the mask work is
# finished and moved the failure somewhere else.  Pre-flight came back ``verdict: trusted``
# (R1 0.9221, R2 0.8065), the take side scored R1 0.9189 and R2 0.7228 -- the Godzilla role
# finally had an instance of its own -- with ``fallback_reason`` empty, one attempt and no
# Popup.  What failed is the replacement itself, recorded by this worker's own audit:
# ``head_layer_only`` on both passes, P1's ``target_likeness_score`` 0.019 with
# ``retention_score`` 0.754 (the source performer survived), wardrobe shifts -0.0140 and
# -0.0376 against the 0.12 floor, and ``status: complete`` beside
# ``character_swap_identity_failed: true``.  The plate had erased only the hair crown and
# the head (``suppressed_frame_area`` 0.235), and the blocking verdict's
# ``action: retry_fresh_seed`` bought nothing because the Studio compiles the audit spec at
# ``maximum_attempts: 1`` on the lean route while the escalation this worker applies for a
# structural blocking cause is also 1.  Nothing here changes for a human cast picture; the
# Studio now arms the body band, the rebuilt-figure clause and one fresh seed only when the
# bound Picture's own words name a non-human body, and records
# ``nonhuman_target_nouns`` on the pass row so a Manifest can be graded without re-measuring.
#
# Round 107 -- neca_6's 11:50 run (policy 102, one attempt) replaced both performers and moved
# the complaint to the edge: "边缘勾线出现瑕疵，合成的时候出现穿崩严重".  Measured on that run's own
# files, which a successful run deletes from disk but ComfyUI history still holds: the matte is
# registered (median best correction of the union matte against the shipped picture is
# dx +/-2 px, dy 0, dt 0 frames, so neither the 928x512-take-versus-960x512-mask letterbox nor
# the 11 extra frames the SAM mux appends shows), and the defects are in the edge treatment --
# growing the coarse hard-threshold silhouette by two pixels and feathering over the grown edge
# leaves a 1-3 px halo of plate tracing the performer, and thin limbs fall out of the matte
# entirely so the plate shows through the body.  ``H3_CHARACTER_SWAP_SAM31_EDGE_MODE`` chooses
# the edge (``classic`` keeps this worker's pre-107 chain byte for byte) and
# ``H3_CHARACTER_SWAP_SAM31_DIFF_FLOOR`` the luma difference that counts as painted.
# Round 111 -- neca_6's 20:33 take (shot 10) ran policy 106 with design_ai.env already saying
# H3_CHARACTER_SWAP_NONHUMAN_RANKING=shape, and still never tracked a roll: the Studio process had been
# open since before that edit, so its own environment still said ``first`` and the worker inherited it
# wholesale through Popen while running new code.  A job now carries the fingerprint of the knob file
# the Studio read plus exactly the pairs it installed; a worker that finds the file has changed refreshes
# those names only (a launcher override still wins) and says so in Chinese on the progress line.  The
# roll ranking also stops promoting a roll that is off-model for more of the Shot merely because its p10
# is marginally higher: the share of off-model seconds decides first, p10 breaks the tie, and the earlier
# roll is kept unless the challenger is clearly better (measured on the 20:33 rolls: 19.0 % against
# 41.4 % off-model, while p10 said the opposite -- 0.2684 against 0.3080).  A failed measurement records
# the error's message instead of only its class, and a pass that re-rolled now states out loud why its
# rolls were not compared by silhouette.
SMART_RENDER_POLICY_VERSION = 108
AUDIO_JOIN_FADE_SECONDS = 0.04
MAX_DIRECT_ASSEMBLY_SEGMENTS = 6
LOCATION_SOUND_REFERENCE_VERSION = 1


def effective_generation_timeout_seconds(job: dict) -> int:
    """Return the per-prompt ComfyUI budget a Job actually needs.

    ``generation_timeout`` bounds the wait for one submitted prompt, not one
    Relay window.  While Studio split every over-limit Shot into balanced
    one-window segments, the configured value bought exactly one window of
    work.  Round 49's manual parity submits a whole Shot once and lets the
    native Relay loop chain its windows through the 18-frame history, so the
    longest pass in the Job decides how many windows one prompt has to render:
    the 12.864 s Shot compiles to three windows and would otherwise be killed
    at 1 800 s on a render that needs roughly 5 400 s.
    """

    try:
        base = int(job.get("generation_timeout", 1800))
    except (TypeError, ValueError):
        base = 1800
    base = max(10, base)
    windows = 1
    for segment in job.get("segments") or []:
        if not isinstance(segment, dict):
            continue
        for pass_row in segment.get("character_swap_passes") or []:
            if not isinstance(pass_row, dict):
                continue
            try:
                windows = max(
                    windows, int(pass_row.get("relay_window_count", 1) or 1)
                )
            except (TypeError, ValueError):
                continue
    return min(86400, base * max(1, windows))

# Target-likeness scores that clear the hard floor but stay inside this band are
# assembled and flagged for review instead of retried.
TARGET_SIMILARITY_WARNING_BAND = 0.06
# Round 69 item 3 — QC gets a veto.  The whole-character integration audit and the
# wardrobe-shift audit are the two gates that can see *how much* of the character
# got replaced, and the director reports their failure by eye every single time
# ("only the head got swapped", "the V1 shirt is still on").  When either of them
# says head/face-layer-only and the take is also nowhere near the target P Picture,
# the low likeness is corroborating evidence rather than a colour-histogram
# artefact, so the advisory waiver is lifted and the take is retried with a fresh
# seed.  Anything else keeps the round-52 witness-only behaviour.
CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR = 0.5
# Round 92 — the veto reads every sample, not just the median.  The Hallway
# Approach Project shipped exactly the take this veto was written for and the veto
# missed it: the three target-P samples inside the audited rectangle scored
# 0.636 / 0.485 / 0.573, so the recorded median 0.573 sat above the floor while
# the 6.98 s sample — the frame where the head reverted to the V1 performer, and
# the frame the director reported by eye at 3.5-7.5 s — sat below it.  Replaying
# that take through the engine's own decoder reproduced the recorded median to
# 0.000000, so the arithmetic is the bug and not the measurement: a median of
# three tolerates precisely the one frame the eye catches.  The floor therefore
# binds on the *worst* sample as well as on the median.  The number itself is
# unchanged, because across every audited take in this workspace the
# head-layer-only class already sits at or below 0.5 (0.095 .. 0.494) and the veto
# still needs the wardrobe / whole-character witness, so a take whose body really
# moved cannot be dragged into a retry by one dim frame.
# A blocking head-layer verdict used to get the full fresh-seed budget even when
# the compiled pass spec asked for a single attempt (the lean Design audit path),
# so the director got two takes they never asked for.  Round 86 item A puts the
# escalation behind ``H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS``: with the variable
# unset the lift is one, meaning the compiled spec rules and a Preview that Studio
# compiled as ``maximum_attempts: 1`` renders exactly one take.  Setting the
# variable to 3 restores the round-69 behaviour.  The constant below stays as the
# clamp so no value can ever spend more than three seeds on one Segment.
CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS = 3
CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS_DEFAULT = 1
# Round 92: a target-reference *collapse* is the one head-layer failure a fresh
# seed can actually repair.  The Hallway take had already produced the target
# character at 3.07 s and again at 10.89 s, so the miss at 6.98 s is a sampling
# instability of this seed, not the structural "the wardrobe never moved" miss
# round 86 refused to spend seeds on.  That class therefore gets the original take
# plus one fresh seed; every other blocking verdict keeps the round-86 escalation
# of one.  ``H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS`` still rules both ways, so a
# director who wants no second chance sets it to 1 and one who wants the round-69
# budget sets it to 3.
CHARACTER_SWAP_HEAD_LAYER_COLLAPSE_MAX_ATTEMPTS = 2
CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS_ENV = "H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS"
# How much a Silent Listener whose mouth kept articulating costs the retry ranking.
# Calibrated on the seed 923010507 retry tables: seg0 let the widest-mouthed take
# win by 0.0664 of likeness (similarity plus wardrobe bonus) against a mouth that
# moved 0.0250 further past its limit, and seg2 by 0.0900 against 0.0323 -- both
# leads sit under eight times the gap, so the quieter take wins, while a take that
# is genuinely closer to Picture 1 by a wide margin still outscores it.  The cap
# bounds a pathological audit; every excess this project has measured so far sits
# below 0.07.
SILENT_ARTICULATION_PENALTY_WEIGHT = 8.0
SILENT_ARTICULATION_PENALTY_CAP = 0.35
SAM31_MULTIPLEX_CHECKPOINT = "sam3.1_multiplex_fp16.safetensors"
SAM31_COMPOSITE_MODE = "sam31_v1_plus_role_output_instance_masks_v3"
SAM31_FALLBACK_COMPOSITE_MODE = "sam31_v1_plus_role_output_masks_v3_fallback_delta"
# Round 69 item 4 — a soft association must not become the wrong person.
#
# ``match_sam31_masks_to_passes`` ranks every (Current Role box, SAM instance)
# pair and accepts the best non-conflicting pairing, so a role can pair with the
# wrong body and still clear the 0.08 discard floor.  When it does, the
# delta-mask fallback composites that wrong silhouette and the take ships with
# the wrong person swapped — the multi-character misplacement the director
# graded on the pink-dress Project, where the QC boxes agreed with each other
# and disagreed with the reference.  Below this floor the pairing is not trusted
# at all: the job stops and asks for a manual character box instead of guessing.
SAM31_MIN_MATCH_SCORE = 0.7
# The call site matches this prefix so a weak association cannot be swallowed by
# the OOM retry or the delta fallback the way an ordinary SAM failure is.
SAM31_WEAK_MATCH_SENTINEL = "SAM3.1 weak association - manual box required:"
# Round 102: the floor became a knob because the only alternative was editing source in
# front of a director who is watching a 20-minute take fail.
SAM31_MIN_MATCH_SCORE_ENV = "H3_CHARACTER_SWAP_SAM31_MIN_MATCH_SCORE"
SAM31_ASSOCIATION_PREFLIGHT_ENV = "H3_CHARACTER_SWAP_SAM31_ASSOCIATION_PREFLIGHT"
SAM31_MIN_MATCH_SCORE_MIN = 0.05
SAM31_ASSOCIATION_PREFLIGHT_MODES = ("on", "advisory", "off")


def sam31_min_match_score() -> float:
    """Association score a Current Role must reach before its pairing is trusted.

    ``SAM31_MIN_MATCH_SCORE`` is the shipped number and the default here, so a Project
    that arms nothing is judged exactly as round 69 judged it.  Round 102 makes it
    readable from ``design_ai.env`` because the gate fires after the generation has been
    paid for: neca_6 lost a take to ``R1 0.52`` and neca_5 to ``R3 0.31`` / ``R3 0.36``,
    and the director's only other lever was re-drawing a box against a ruler he could
    not see.  A lowered floor does not make the pairing correct, it makes the director
    the judge instead of the code, which is what the message itself asks for -- so the
    score and the floor both stay in the Manifest either way.

    Values outside ``[0.05, 1.0]`` are clamped and junk falls back to the shipped
    default, because a typo like ``7`` would otherwise silently trust nothing at all.
    """

    raw = os.environ.get(SAM31_MIN_MATCH_SCORE_ENV, "").strip()
    if not raw:
        return SAM31_MIN_MATCH_SCORE
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return SAM31_MIN_MATCH_SCORE
    if requested != requested:  # NaN
        return SAM31_MIN_MATCH_SCORE
    return max(SAM31_MIN_MATCH_SCORE_MIN, min(1.0, requested))


def sam31_association_preflight_mode() -> str:
    """``on`` / ``advisory`` / ``off`` for the before-generation association check.

    Round 103 moved the default from ``on`` to ``advisory``.  The pre-flight proved its
    value on godzilla_action_figure_by_neca_6 on 2026-11-08 -- it measured
    ``R1 0.7726 / margin 0.3514`` against the V1 plate *before* the first take and that
    verdict was correct -- but as a veto it is now the wrong shape, because the pairing it
    can reject after generation is rejected for a different reason (the generated masks),
    and a director who is watching a 20-minute take does not want a second gate in front
    of him.  So the pre-flight now measures and records by default and lets the
    after-generation path decide, which is what ``H3_CHARACTER_SWAP_SAM31_WEAK_ASSOCIATION``
    answers.  ``on`` restores the veto for a Project that would rather learn the number
    than spend the take; ``off`` restores the round-97 order exactly.
    """

    mode = (
        os.environ.get(SAM31_ASSOCIATION_PREFLIGHT_ENV, "").strip().casefold()
        or "advisory"
    )
    if mode not in SAM31_ASSOCIATION_PREFLIGHT_MODES:
        return "advisory"
    return mode


# Round 103: what a weak association is allowed to do.  The two Godzilla Projects of
# 2026-11-08 settled this: neca_6 failed at 23:37 with ``R1 0.48`` and at 00:11 with
# ``R2 0.40``, both times *after* every take had been generated, and the mask geometry
# read back from those failed runs shows why no character box could have passed -- SAM
# tracked the replaced performer for only 16 of the 56 sampled frames (0-3.75 s of a
# 13.975 s clip) and spent the rest of the clip inside one blob whose median bbox was
# 0.9111 of the frame.  A measurement that is not tracking a person cannot gate a
# composite, so a weak association now falls through to the H3 delta-mask compositor
# (the path that already exists for an unavailable SAM3.1) instead of failing the
# Segment.  Round 69 wrote this floor to stop a *soft* pairing compositing one person's
# replacement onto another, and the automatic box repair below keeps that protection by
# demanding the same winning instance and a real margin; ``abort`` restores round 69's
# hard failure.
SAM31_WEAK_ASSOCIATION_ACTION_ENV = "H3_CHARACTER_SWAP_SAM31_WEAK_ASSOCIATION"
SAM31_WEAK_ASSOCIATION_ACTIONS = ("continue", "abort")
SAM31_AUTO_BOX_ENV = "H3_CHARACTER_SWAP_SAM31_AUTO_BOX"
SAM31_AUTO_BOX_MODES = ("on", "advisory", "off")
SAM31_AUTO_BOX_MAX_WIDTH_ENV = "H3_CHARACTER_SWAP_SAM31_AUTO_BOX_MAX_WIDTH"
SAM31_AUTO_BOX_DEFAULT_MAX_WIDTH = 0.60
SAM31_AUTO_BOX_MIN_MARGIN = 0.05
SAM31_AUTO_BOX_NONHUMAN_MAX_WIDTH_ENV = "H3_CHARACTER_SWAP_SAM31_AUTO_BOX_MAX_WIDTH_NONHUMAN"
# Round 109: a non-human target has no hair halo to protect, and its body is routinely wider
# than a person's.  Measured on neca_6's 16:52 Preview from the run's own rescued mask files:
# Godzilla's silhouette envelope was 0.7021 wide (0.7188 when sampled at 4 fps), so with the
# person's 0.60 cap the repair ladder was *structurally* empty -- even the body's own envelope
# was rejected, which is why the association refused at 0.69 and the whole Shot shipped as a
# difference-matte fallback.  0.85 matches the area ceiling, so width alone can never veto a
# body the area guard already lets through; the same-body, margin, score and anchor-containment
# guards all still run afterwards.
SAM31_AUTO_BOX_NONHUMAN_DEFAULT_MAX_WIDTH = 0.85
SAM31_AUTO_BOX_MIN_AREA = 0.02
SAM31_AUTO_BOX_MAX_AREA = 0.85
SAM31_AUTO_BOX_MIN_ANCHOR_CONTAINMENT = 0.60
SAM31_AUTO_BOX_MIN_AUTHORED_OVERLAP = 0.30


def sam31_weak_association_action() -> str:
    """``continue`` (fall back to the delta compositor) or ``abort`` (round-69 failure)."""

    action = (
        os.environ.get(SAM31_WEAK_ASSOCIATION_ACTION_ENV, "").strip().casefold()
        or "continue"
    )
    if action not in SAM31_WEAK_ASSOCIATION_ACTIONS:
        return "continue"
    return action


def sam31_auto_box_mode() -> str:
    """Whether a weak pairing may re-fit the Role's box from the masks it measured."""

    mode = os.environ.get(SAM31_AUTO_BOX_ENV, "").strip().casefold() or "on"
    if mode not in SAM31_AUTO_BOX_MODES:
        return "on"
    return mode


def sam31_auto_box_max_width() -> float:
    """Width a repaired box may grow to before the hair halo would be switched off.

    The shipped cap is the round-68 ``max_box_width`` 0.60: on 2026-11-08 neca_6's
    repaired box measured 0.5458 wide and so kept the halo, while growing it by 0.08 on
    every side measured 0.7058 -- which not only switched the halo off but made the
    whole-frame blob the winning instance, i.e. a repair that would have started
    compositing the wrong person.
    """

    raw = os.environ.get(SAM31_AUTO_BOX_MAX_WIDTH_ENV, "").strip()
    if not raw:
        return SAM31_AUTO_BOX_DEFAULT_MAX_WIDTH
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return SAM31_AUTO_BOX_DEFAULT_MAX_WIDTH
    if requested != requested:
        return SAM31_AUTO_BOX_DEFAULT_MAX_WIDTH
    return max(0.20, min(1.0, requested))


def sam31_auto_box_max_width_nonhuman() -> float:
    """Width a repaired box may reach when the Role's target is a creature, not a person.

    ``sam31_auto_box_max_width`` exists to keep the hair halo alive on a human replacement.
    A Gundam or a Godzilla has no hair band, and its body fills more of the frame than any
    person's: on neca_6's 16:52 Preview the paired Godzilla slot measured 0.7021 wide, so the
    person's cap made every candidate -- including the envelope itself -- illegal and the run
    fell back to a difference-matte composite that double-exposed the Shot.  The default is
    therefore the area ceiling (0.85): a box that the area guard accepts can no longer be
    refused for width alone.  Set it back to ``0.60`` to restore the pre-Round-109 behaviour.
    """

    raw = os.environ.get(SAM31_AUTO_BOX_NONHUMAN_MAX_WIDTH_ENV, "").strip()
    if not raw:
        return SAM31_AUTO_BOX_NONHUMAN_DEFAULT_MAX_WIDTH
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return SAM31_AUTO_BOX_NONHUMAN_DEFAULT_MAX_WIDTH
    if requested != requested:
        return SAM31_AUTO_BOX_NONHUMAN_DEFAULT_MAX_WIDTH
    return max(0.20, min(1.0, requested))


# ---------------------------------------------------------------------------
# Round 106: SAM3.1 splits one body across several object slots the moment its appearance
# changes mid-clip, and the association below gave every Role exactly one slot.  Measured on
# neca_6's shipped 07:58 Preview by reading the mask files straight out of ComfyUI, because
# the local per-pass cache had already been cleaned
# (``testing/_dsh_verify_13/godzilla/fetch_comfyui_sam_masks_106.py``,
# ``measure_round106_coverage_metric_neca6.py``, ``sweep_round106_fragment_rule_neca6.py``):
#
#   * take R1's winning slot (object 0, score 0.8893 -- reproduced exactly offline) is a full
#     matte for 0-6.25 s and 11-14 s and an empty shell in between: per-sample filled share
#     0.0035-0.026 while its bbox still covers 0.95 of the authored box.  That is why the
#     score read 0.89 and the picture showed the source performer for six seconds;
#   * the missing seconds are sitting in the slot the association threw away: the same take's
#     object 1 carries that body from 5 s to the end (median filled share 0.4251);
#   * take R2's object 2 (0.7328) covers 5.25-12.75 s only, object 3 carries the same
#     Godzilla from 2.5-4 s, and object 0 -- which scores 0.4594 -- is the *other* body:
#     median IoU 0.318 against the Role's box, but 0.405 of its own box lies outside it;
#   * per-sample filled share separates "a matte is here" from "an empty shell" by a factor
#     of twelve on this run: the empty cluster sits at 0.0000-0.0011 and the nearest real
#     sample is at 0.0129.  The composite binarizes masks at luma 96
#     (``lut=y='if(gte(val,96),255,0)'``, line ~6998), so this is the same line of colour
#     the shipped picture already respects.
#
# The pairing decision is left exactly as rounds 69-104 shipped it.  After the winner is
# picked, the remaining slots are asked for the seconds the winner is missing, and the answer
# is added to the same pass: the compositor already ORs every mask a pass is given
# (``blend=all_mode=lighten``, line ~6990), so a fragment needs no filter change.  What no
# mask covers stays on the plate, and the Manifest now says so in seconds.
SAM31_MASK_FRAGMENT_ENV = "H3_CHARACTER_SWAP_SAM31_MASK_FRAGMENTS"
SAM31_MASK_FRAGMENT_MODES = ("on", "off")
SAM31_FRAGMENT_MIN_FILLED_SHARE = 0.010
SAM31_FRAGMENT_MIN_AREA_RATIO = 0.12
SAM31_FRAGMENT_MIN_IOU = 0.15
SAM31_FRAGMENT_MIN_MEDIAN_IOU = 0.35
SAM31_FRAGMENT_MAX_SPILL = 0.35
SAM31_FRAGMENT_MIN_SAMPLE_SHARE = 0.10
SAM31_FRAGMENT_MIN_MARGIN = 0.15
SAM31_MASK_SAMPLE_FPS = 4.0
SAM31_MASK_COVERAGE_FLOOR_ENV = "H3_CHARACTER_SWAP_SAM31_MASK_COVERAGE_FLOOR"
SAM31_DEFAULT_MASK_COVERAGE_FLOOR = 0.55


def sam31_mask_fragments_mode() -> str:
    """Whether a Role may own more than one SAM slot (round 106, default on)."""

    mode = os.environ.get(SAM31_MASK_FRAGMENT_ENV, "").strip().casefold() or "on"
    if mode not in SAM31_MASK_FRAGMENT_MODES:
        return "on"
    return mode


def sam31_min_mask_coverage_share() -> float:
    """Share of the clip a Role's matte must actually cover before it is called adequate.

    0.55 is not a guess: on the 07:58 run the single-slot coverage measured 0.655 (R1) and
    0.545 (R2) while the picture lost every second outside those ranges, and the fragments
    lift the same two Roles to 0.855 and 0.68.  The floor sits between the two so a
    fragment-starved Role is still reported, and it is advisory -- the shot keeps running,
    which is the round-103 rule.
    """

    raw = os.environ.get(SAM31_MASK_COVERAGE_FLOOR_ENV, "").strip()
    if not raw:
        return SAM31_DEFAULT_MASK_COVERAGE_FLOOR
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return SAM31_DEFAULT_MASK_COVERAGE_FLOOR
    if requested != requested:
        return SAM31_DEFAULT_MASK_COVERAGE_FLOOR
    return max(0.0, min(1.0, requested))


# ---------------------------------------------------------------------------
# Round 107: what the compositor does with the *edge* of the matte.
#
# The 11:50 Preview (policy 102) is the first shot where the replacement itself held and the
# director's complaint was about the edge, which let the two problems be told apart on that
# run's own files -- plate, both takes and every mask are still addressable in ComfyUI history
# (``testing/_dsh_verify_13/godzilla/measure_round107_registration_real_1150.py``,
# ``rim_round107_1150.py``):
#
#   * The matte is registered.  Fitting the shipped picture against the plate and the take,
#     the best correction of the union matte is a median (dx +/-2, dy 0, dt 0 frames): the
#     6-px letterbox offset between a 928x512 take and its own 960x512 mask, and the 11 extra
#     frames the SAM mux appends (345 against 334), are both real and both invisible.
#   * What is visible is the edge treatment.  ``dilation,dilation`` grows the hard, coarse
#     960x512 silhouette by two pixels and ``gblur`` then lays its soft ramp across that grown
#     boundary, so a 1-3 px strip of the plate's own rim -- carpet, wall, the other
#     performer -- survives as a halo that traces the silhouette: the 勾线.  Where the
#     silhouette is coarse the same hard threshold simply loses thin limbs (at 10.0 s the
#     Gundam's beam rifle, its sword and the spikes are not in the matte at all), so the plate
#     shows straight through the body: the 穿崩.
#
# ``soft`` feathers the union without growing it, ``soft_grow`` (the shipped default) feathers
# after a single-pixel growth, and ``soft_fill`` additionally re-adds the take's own silhouette
# -- but only inside a three-pixel halo of what SAM already found, so the fill patches
# concavities and thin limbs instead of inventing regions the colour grade difference happens to
# favour.  Measured on the 11:50 run's own files
# (``testing/_dsh_verify_13/godzilla/score_round107_variants_1150.py``): ``classic`` leaves a
# 1-3 px halo that traces the silhouette -- 96 changed background pixels per second in the
# 3-8 px ring around the performer, against 11 for ``soft`` and ``soft_grow`` -- while
# ``soft`` alone lets 2.04 % of the clearly-painted body stay plate against classic's 0.75 %,
# which is what the one-pixel growth of ``soft_grow`` buys back.  ``soft_fill`` is kept for
# the next round and is not the default: on this run its difference-based fill made the
# replacement read translucent, with the plate's performers showing through the body.
# ``classic`` is the byte-identical pre-round-107 chain.
SAM31_EDGE_MODE_ENV = "H3_CHARACTER_SWAP_SAM31_EDGE_MODE"
SAM31_EDGE_MODES = ("classic", "soft", "soft_grow", "soft_fill")
SAM31_DEFAULT_EDGE_MODE = "soft_grow"
SAM31_DIFF_FLOOR_ENV = "H3_CHARACTER_SWAP_SAM31_DIFF_FLOOR"
SAM31_DEFAULT_DIFF_FLOOR = 72
SAM31_DIFF_FLOOR_MIN = 16
SAM31_DIFF_FLOOR_MAX = 200
SAM31_EDGE_FEATHER_SIGMA = 1.2
SAM31_CLASSIC_EDGE_CHAIN = "dilation,dilation,gblur=sigma=1.4"


def sam31_edge_mode() -> str:
    """How the SAM3.1 composite treats the boundary of the matte (round 107, default soft_fill)."""

    mode = os.environ.get(SAM31_EDGE_MODE_ENV, "").strip().casefold() or SAM31_DEFAULT_EDGE_MODE
    if mode not in SAM31_EDGE_MODES:
        return SAM31_DEFAULT_EDGE_MODE
    return mode


def sam31_diff_floor() -> int:
    """Luma difference at which the take is taken to have really painted that pixel."""

    raw = os.environ.get(SAM31_DIFF_FLOOR_ENV, "").strip()
    if not raw:
        return SAM31_DEFAULT_DIFF_FLOOR
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return SAM31_DEFAULT_DIFF_FLOOR
    if requested != requested:
        return SAM31_DEFAULT_DIFF_FLOOR
    if requested >= SAM31_DIFF_FLOOR_MAX:
        return SAM31_DIFF_FLOOR_MAX
    if requested <= SAM31_DIFF_FLOOR_MIN:
        return SAM31_DIFF_FLOOR_MIN
    return max(SAM31_DIFF_FLOOR_MIN, min(SAM31_DIFF_FLOOR_MAX, int(requested)))


# Round 108 -- how much the take actually resembles the target P Picture, second by second.
#
# neca_6's 14:24 Preview (policy 103, one attempt) is the second data point on the same plate
# with byte-identical instructions -- ``prompt_chars`` 4439/4441, the same non-human cast lock,
# only the seed differs -- and the director called it 角色替换失败 while he had called the 11:50
# take good.  The auditor that is supposed to catch that scored them 0.325/0.467 against
# 0.359/0.423, i.e. it put the rejected roll *above* the accepted one (R2 0.46746 > 0.422913),
# and its blocking cause is ``head_layer_only``: a human-wardrobe predicate ("the V1 wardrobe
# still fills the body region") that fired on both roles of both takes, good and bad alike.
#
# Measuring each take against its own target P Picture cutout instead separates them cleanly,
# and it only separates them when the statistic is the one the director is actually reacting to
# -- the worst role, and the worst seconds of that role
# (``testing/_dsh_verify_13/godzilla/measure_round108_take_vs_target.py``,
# ``round108_metrics/round108_metric_rows.json``).  Inside the SAM matte the compositor was
# already using, normalized into the matte's own box and compared with the cutout's silhouette:
#
#   11:50 (accepted)  worst role R1: median 0.6378, p10 0.4232, seconds below 0.55: 17.9 %
#   14:24 (rejected)  worst role R2: median 0.5718, p10 0.3690, seconds below 0.55: 30.9 %
#
# and the series names the exact seconds: the accepted take's R1 collapses to 0.19/0.30/0.31
# across 5.0-6.5 s (the source girl's face wearing Gundam armour), while the rejected take's R2
# never rises above 0.37-0.41 and drops to 0.11/0.14 at 3.5-4.25 s (a chibi child with Godzilla
# spikes).  A whole-take median hides both, which is why no existing score ranked these runs.
#
# This round records the number rather than blocking on it, because the matte it needs only
# exists once the composite stage has asked SAM3.1 for it -- after the retry loop has already
# spent its rolls.  ``H3_CHARACTER_SWAP_SAM31_TARGET_SHAPE=block`` turns it into a verdict as
# soon as the retry loop can reach a matte; ``off`` skips the extra decode entirely.
SAM31_TARGET_SHAPE_ENV = "H3_CHARACTER_SWAP_SAM31_TARGET_SHAPE"
SAM31_TARGET_SHAPE_MODES = ("record", "block", "off")
SAM31_DEFAULT_TARGET_SHAPE_MODE = "record"
SAM31_SHAPE_IOU_FLOOR_ENV = "H3_CHARACTER_SWAP_SAM31_SHAPE_IOU_FLOOR"
SAM31_DEFAULT_SHAPE_IOU_FLOOR = 0.55
SAM31_SHAPE_IOU_FLOOR_MIN = 0.20
SAM31_SHAPE_IOU_FLOOR_MAX = 0.95
SAM31_SHAPE_WEAK_SHARE_ENV = "H3_CHARACTER_SWAP_SAM31_SHAPE_WEAK_SHARE"
SAM31_DEFAULT_SHAPE_WEAK_SHARE = 0.25
SAM31_SHAPE_WEAK_SHARE_MIN = 0.02
SAM31_SHAPE_WEAK_SHARE_MAX = 0.90
# The 11:50 take the director accepted sits at p10 0.4232, the 14:24 take he rejected at 0.3690,
# so the worst-decile floor goes between them and nowhere else.
SAM31_SHAPE_P10_FLOOR = 0.40
SAM31_SHAPE_SAMPLE_FPS = 4.0
SAM31_SHAPE_SILHOUETTE_SIZE = 128


def sam31_target_shape_mode() -> str:
    """``record`` (default), ``block`` or ``off`` for the target-shape audit."""

    raw = os.environ.get(SAM31_TARGET_SHAPE_ENV, "").strip().lower()
    return raw if raw in SAM31_TARGET_SHAPE_MODES else SAM31_DEFAULT_TARGET_SHAPE_MODE


def sam31_shape_iou_floor() -> float:
    """Per-second IoU below which a sample counts as "this is not the target character"."""

    raw = os.environ.get(SAM31_SHAPE_IOU_FLOOR_ENV, "").strip()
    if not raw:
        return SAM31_DEFAULT_SHAPE_IOU_FLOOR
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return SAM31_DEFAULT_SHAPE_IOU_FLOOR
    if requested != requested:
        return SAM31_DEFAULT_SHAPE_IOU_FLOOR
    return max(SAM31_SHAPE_IOU_FLOOR_MIN, min(SAM31_SHAPE_IOU_FLOOR_MAX, requested))


def sam31_shape_weak_share_floor() -> float:
    """How much of the clip may look wrong before the whole pass is called weak."""

    raw = os.environ.get(SAM31_SHAPE_WEAK_SHARE_ENV, "").strip()
    if not raw:
        return SAM31_DEFAULT_SHAPE_WEAK_SHARE
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return SAM31_DEFAULT_SHAPE_WEAK_SHARE
    if requested != requested:
        return SAM31_DEFAULT_SHAPE_WEAK_SHARE
    return max(SAM31_SHAPE_WEAK_SHARE_MIN, min(SAM31_SHAPE_WEAK_SHARE_MAX, requested))


def _character_swap_cutout_silhouette(reference_image: Path):
    """The target P Picture's own body, cropped to its alpha box and normalized to a square.

    Returns ``None`` when the artwork has no opaque pixels: an empty cutout cannot prove
    anything about resemblance, and a diagnostic must never fail a Segment.
    """

    from PIL import Image

    try:
        with Image.open(reference_image) as image:
            alpha = image.convert("RGBA").split()[3].point(
                lambda value: 255 if int(value) > 8 else 0
            )
    except Exception:  # noqa: BLE001 - unreadable artwork is not the take's fault
        return None
    box = alpha.getbbox()
    if not box:
        return None
    return alpha.crop(box).resize(
        (SAM31_SHAPE_SILHOUETTE_SIZE, SAM31_SHAPE_SILHOUETTE_SIZE), Image.NEAREST
    ).convert("1")


def _character_swap_decode_matte_samples(job, mask_video: Path) -> list:
    """Every ``fps=4`` frame of a saved SAM instance as a PIL image, hard-thresholded like the
    compositor thresholds it (``lut`` at luma 96)."""

    from PIL import Image

    ffprobe = job.get("ffprobe")
    ffmpeg = job.get("ffmpeg")
    geometry = _probe_video_geometry(ffprobe, mask_video)
    if geometry is None:
        return []
    width, height = geometry
    if width <= 0 or height <= 0:
        return []
    duration = _probe_duration(ffprobe, mask_video) or 0.0
    completed = subprocess.run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(mask_video),
            "-vf", f"fps={SAM31_SHAPE_SAMPLE_FPS:.6f},format=gray,"
                   f"lut=y='if(gte(val,96),255,0)'",
            "-an", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
        timeout=max(60, int(max(1.0, duration) * 10)),
    )
    if completed.returncode:
        return []
    payload = completed.stdout
    stride = width * height
    frames = len(payload) // stride
    samples = []
    for index in range(frames):
        chunk = payload[index * stride:(index + 1) * stride]
        samples.append(Image.frombytes("L", (width, height), chunk))
    return samples


def _character_swap_silhouette_from_mask(mask):
    """A matte cropped to its own bounding box and normalized into a square silhouette.

    Normalizing by the matte's own box is what makes this comparable at all: the take, its mask
    and the artwork are three different frames and sizes, and Round 107 proved the composite's
    placement offsets (median dx +/-2 px, dy 0, dt 0 frames) never reach the picture.
    """

    from PIL import Image

    box = mask.getbbox()
    if not box:
        return None
    return mask.crop(box).resize(
        (SAM31_SHAPE_SILHOUETTE_SIZE, SAM31_SHAPE_SILHOUETTE_SIZE), Image.NEAREST
    ).convert("1")


def _character_swap_silhouette_iou(first, second) -> float:
    from PIL import ImageChops

    intersection = sum(ImageChops.logical_and(first, second).getdata())
    union = sum(ImageChops.logical_or(first, second).getdata())
    if union <= 0:
        return 0.0
    return float(intersection) / float(union)


def _character_swap_take_target_shape(job, mask_videos: list, reference_image: object,
                                      clip_seconds: float = 0.0) -> dict:
    """Score a pass against its own target P Picture, second by second, from the mattes.

    The matte is the only thing this needs -- it is what SAM3.1 found in the take, and the
    compositor is already pasting through it -- so no extra decode of the take is required.
    Every failure path returns a row that says so instead of raising: an unreadable artwork or
    an empty matte must never become a new way to fail a Segment.
    """

    mode = sam31_target_shape_mode()
    if mode == "off":
        return {"target_shape_status": "off"}
    path = Path(str(reference_image or ""))
    if not path.is_file():
        return {"target_shape_status": "no_target_reference"}
    target = _character_swap_cutout_silhouette(path)
    if target is None:
        return {"target_shape_status": "empty_target_reference"}
    decoded = [row for row in (_character_swap_decode_matte_samples(job, Path(str(video)))
                               for video in (mask_videos or [])) if row]
    if not decoded:
        return {"target_shape_status": "no_masks"}
    from PIL import ImageChops

    frame_count = min(len(row) for row in decoded)
    samples: list[dict] = []
    for index in range(frame_count):
        union = decoded[0][index]
        for row in decoded[1:]:
            union = ImageChops.lighter(union, row[index])
        silhouette = _character_swap_silhouette_from_mask(union)
        if silhouette is None:
            continue
        samples.append({
            "time_seconds": round(index / SAM31_SHAPE_SAMPLE_FPS, 3),
            "iou": round(_character_swap_silhouette_iou(silhouette, target), 4),
        })
    if not samples:
        return {"target_shape_status": "empty_matte"}
    values = sorted(float(row["iou"]) for row in samples)
    median = values[len(values) // 2] if len(values) % 2 else (
        (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2.0
    )
    p10_index = max(0, min(len(values) - 1, int(round(0.10 * (len(values) - 1)))))
    p10 = values[p10_index]
    iou_floor = sam31_shape_iou_floor()
    weak_share_floor = sam31_shape_weak_share_floor()
    weak_samples = [row for row in samples if float(row["iou"]) < iou_floor]
    weak_share = round(float(len(weak_samples)) / float(len(samples)), 4)
    weak_ranges: list[list[float]] = []
    for row in weak_samples:
        moment = float(row["time_seconds"])
        if weak_ranges and moment - float(weak_ranges[-1][1]) <= (1.0 / SAM31_SHAPE_SAMPLE_FPS) + 0.01:
            weak_ranges[-1][1] = round(moment + 1.0 / SAM31_SHAPE_SAMPLE_FPS, 3)
            continue
        weak_ranges.append([moment, round(moment + 1.0 / SAM31_SHAPE_SAMPLE_FPS, 3)])
    weak = bool(weak_share > weak_share_floor or p10 < SAM31_SHAPE_P10_FLOOR)
    return {
        "target_shape_status": "measured",
        "target_shape_reference": str(path),
        "target_shape_samples": len(samples),
        "target_shape_iou_median": round(median, 4),
        "target_shape_iou_p10": round(p10, 4),
        "target_shape_iou_floor": round(iou_floor, 4),
        "target_shape_weak_share": weak_share,
        "target_shape_weak_share_floor": round(weak_share_floor, 4),
        "target_shape_p10_floor": round(SAM31_SHAPE_P10_FLOOR, 4),
        "target_shape_weak_seconds_ranges_seconds": weak_ranges,
        "target_shape_weak": weak,
        "target_shape_blocking": bool(weak and mode == "block"),
        "target_shape_clip_seconds": round(float(clip_seconds or 0.0), 3),
    }


# ---------------------------------------------------------------------------
# Round 104: what SAM3.1 is actually asked to look for, and which of its answers are
# not mattes at all.  Measured on neca_6's failed 00:11 Preview with the product's own
# decoder (``testing/_dsh_verify_13/godzilla/measure_neca6_pass2_masks.py``,
# ``check_mask_vs_frame_neca6.py``):
#
#   * the tracking workflow conditioned on the single word ``person``, and the Godzilla
#     replacement in the right half of the frame produced **no instance of its own** --
#     the only human-shaped matte in that pass was the *other* performer (white share
#     0.210, union x 0.02-0.69); the remaining slots were a bottom sliver (0.029 area),
#     one stray frame at the top, and one all-black slot;
#   * instance 0 was not a matte but **the frame itself**: mid-gray share 0.440-0.558 of
#     its luma against 0.000-0.007 for a real matte, and ``_mask_frame_stats`` reads any
#     luma >= 96 as filled, so it entered the association as "an instance whose bbox
#     covers 0.91 of the frame and that is visible in every one of 56 samples".  It then
#     *beat* the only real body for the Godzilla role: 0.4517 versus 0.4033, a margin of
#     0.0484.  That is what the popup reported as ``R2 0.40``.
#
# The Project already carries the word that says a target is not a person -- P1's
# ``recognition`` reads "BLIP · Overview: godzilla action figure by neca", P2's "a gundam
# ..." -- so Studio copies that text onto the pass row and the prompt below grows the
# noun on its own: ``person, godzilla``.
SAM31_TEXT_PROMPT_ENV = "H3_CHARACTER_SWAP_SAM31_TEXT_PROMPT"
SAM31_TEXT_PROMPT_BASE = "person"
SAM31_TEXT_PROMPT_MAX_CHARS = 160
SAM31_TARGET_RECOGNITION_KEY = "sam31_target_recognition"
SAM31_TARGET_RECOGNITION_MAX_CHARS = 4000
SAM31_DETECTION_THRESHOLD_ENV = "H3_CHARACTER_SWAP_SAM31_DETECTION_THRESHOLD"
SAM31_DETECTION_THRESHOLD_DEFAULT = 0.35
SAM31_DETECTION_THRESHOLD_MIN = 0.05
SAM31_DETECTION_THRESHOLD_MAX = 0.95
# Whole-word, body-kind only.  "figure" / "toy" / "statue" are deliberately absent: they
# appear in ordinary captions ("godzilla action figure by neca") and adding them to the
# prompt would steer SAM3.1 away from bodies it already segments correctly.
SAM31_NON_HUMAN_NOUNS = (
    "godzilla", "kong", "kaiju", "gundam", "evangelion", "mecha", "mech", "robot",
    "android", "cyborg", "monster", "creature", "beast", "alien", "dinosaur",
    "raptor", "dragon", "wyvern", "zombie", "skeleton", "ghost", "spirit",
    "werewolf", "vampire", "demon", "devil", "orc", "goblin", "troll", "giant",
    "cat", "dog", "puppy", "horse", "wolf", "fox", "panda", "tiger", "lion",
    "bear", "rabbit", "monkey", "ape", "gorilla", "elephant", "deer", "unicorn",
    "pegasus", "serpent", "snake", "crocodile", "shark",
)
SAM31_NON_HUMAN_NOUN_MAX = 4
# A real instance matte after h264 is near-binary; a photographic frame is not.  The two
# populations measured 60x apart, so the threshold sits far from both.
SAM31_FRAME_LIKE_MID_GRAY_SHARE = 0.10
SAM31_FRAME_LIKE_MID_GRAY_LOW = 96
SAM31_FRAME_LIKE_MID_GRAY_HIGH = 240
SAM31_FRAME_LIKE_SAMPLE_FPS = 1.0
SAM31_FRAME_LIKE_MAX_FRAMES = 8


# Round 110 -- how much of the Source performer the plate's identity erase actually removed.
#
# The director's question is why a take paints the original kid back after a few seconds, and
# neca_6's 18:51 run answers it with its own files.  Compared second by second *inside the V1
# performer's own SAM silhouette*: the erase left 26-41 % of R1's pixels byte-for-byte unchanged
# (35.0 % at 4.5 s -- the very seconds its take stopped being a Gundam) and 40-63 % of R2's
# (63 % at 10.75 s, the seconds its first roll lost Godzilla).  The area caps are not what is
# binding: R1's plate already erased 57.7 % of the frame (``suppressed_frame_area``), so what
# survives is where the bands were *placed*, not how large they were allowed to be.
#
# This is measured in testing/_dsh_verify_13/godzilla/measure_plate_residual_body_110.py rather than in
# the worker, and deliberately so: the byte-for-byte comparison only works between the raw relay
# and the erased plate, and the erased plate exists only on the ComfyUI box -- the worker holds
# ``identity_audit.source_video_path``, which is the relay before the erase.  A recorder there
# would have logged ``missing_inputs`` on every run, which is a knob that looks like progress and
# measures nothing.  The next round that widens a band should widen it against those numbers.
def sam31_detection_threshold() -> float:
    """How confident SAM3.1 must be before it opens an instance for a body.

    Shipped as the value the workflow has always used (0.35).  It is the knob a director
    pulls to test whether a replacement that reads as non-human -- neca_6's Godzilla --
    becomes its own instance at all; round 104's frame-like-instance filter is what makes
    lowering it safe, because a loosened detector otherwise adds more scene-wide slabs.
    """

    raw = os.environ.get(SAM31_DETECTION_THRESHOLD_ENV, "").strip()
    if not raw:
        return SAM31_DETECTION_THRESHOLD_DEFAULT
    try:
        requested = float(raw)
    except (TypeError, ValueError):
        return SAM31_DETECTION_THRESHOLD_DEFAULT
    if requested != requested:
        return SAM31_DETECTION_THRESHOLD_DEFAULT
    return max(
        SAM31_DETECTION_THRESHOLD_MIN, min(SAM31_DETECTION_THRESHOLD_MAX, requested)
    )


def _sam31_non_human_nouns(passes) -> list[str]:
    """Body-kind nouns the bound target pictures actually describe, in first-seen order."""

    if not passes:
        return []
    found: list[str] = []
    for pass_row in passes:
        if not isinstance(pass_row, dict):
            continue
        text = str(
            pass_row.get(SAM31_TARGET_RECOGNITION_KEY) or ""
        )[:SAM31_TARGET_RECOGNITION_MAX_CHARS].casefold()
        if not text.strip():
            continue
        for noun in SAM31_NON_HUMAN_NOUNS:
            if noun in found:
                continue
            if re.search(rf"\b{re.escape(noun)}\b", text):
                found.append(noun)
            if len(found) >= SAM31_NON_HUMAN_NOUN_MAX:
                return found
    return found


def _sam31_pass_is_non_human(pass_row) -> bool:
    """Whether one Character Swap pass is replacing a creature rather than a person.

    The pass row carries the nouns the bound target pictures were recognised as
    (``nonhuman_target_nouns``), which is what the geometry guards need to know: a person's
    hair halo argues for a narrow repaired box, a Godzilla's body makes that same box illegal.
    Older rows may not carry the list, so the recognition text is consulted as a fallback.
    """

    if not isinstance(pass_row, dict):
        return False
    nouns = pass_row.get("nonhuman_target_nouns")
    if isinstance(nouns, (list, tuple)) and any(str(value).strip() for value in nouns):
        return True
    return bool(_sam31_non_human_nouns([pass_row]))


def sam31_text_prompt(passes=None) -> str:
    """The phrase SAM3.1 is conditioned on -- ``person`` plus whatever the Roles really are.

    One tracking call covers every Role in the Segment, so the phrase has to name every
    body kind in it.  With the Project's own caption of P1 ("godzilla action figure by
    neca") the phrase becomes ``person, godzilla``; a director may also set the whole
    phrase by hand, in which case the measured nouns are still appended to it.
    """

    base = SAM31_TEXT_PROMPT_BASE
    override = os.environ.get(SAM31_TEXT_PROMPT_ENV, "").strip()
    if override:
        base = override[:SAM31_TEXT_PROMPT_MAX_CHARS]
    merged = base
    for noun in _sam31_non_human_nouns(passes):
        candidate = f"{merged}, {noun}"
        if len(candidate) > SAM31_TEXT_PROMPT_MAX_CHARS:
            break
        merged = candidate
    return merged


def character_swap_blocking_max_attempts(collapse: bool = False) -> int:
    """How far a blocking head-layer verdict may lift the compiled attempt spec.

    Round 86 item A.  The shipped default is one -- no lift at all -- because the
    lift was the reason a Preview that Studio compiled as a single take came back
    as three.  The veto that fired was structural (the lower half of the frame
    still wearing the V1 wardrobe, ``wardrobe_shift`` far below its floor), and a
    fresh seed cannot repair a structural miss, so the two extra takes only
    burned eight to ten minutes of GPU each.  The verdict and its numbers still
    land in the manifest either way.  ``H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS``
    is the escape hatch: ``3`` restores round-69 behaviour, and every value is
    clamped into ``[1, CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS]`` so a typo cannot
    spend an unbounded number of seeds.

    Round 92: with the variable unset, a *collapse* verdict (``collapse=True``,
    the target-reference likeness of one sampled frame falling below the floor
    while the median clears it) lifts to one fresh seed instead of none, because
    that is the failure a different seed demonstrably can repair.  An explicitly
    set variable still rules, in both directions.
    """

    raw = os.environ.get(CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS_ENV, "").strip()
    if not raw:
        if collapse:
            return max(
                1,
                min(
                    CHARACTER_SWAP_HEAD_LAYER_COLLAPSE_MAX_ATTEMPTS,
                    CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS,
                ),
            )
        return CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS_DEFAULT
    try:
        requested = int(raw)
    except ValueError:
        return CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS_DEFAULT
    return max(1, min(requested, CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS))


def character_swap_head_layer_blocking_cause(
    head_layer_only: bool,
    target_reference_audit: dict,
) -> str | None:
    """Name the witness that turns a head-layer-only rebuild into a blocking take.

    ``None`` keeps the round-52 witness-only behaviour.  Both causes need the same
    two things round 69 demanded -- a wardrobe / whole-character witness that the
    replacement stopped at the neck, and a target-P-picture measurement that was
    actually taken -- and the same ``CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR``:

    * ``"target_reference_similarity"`` -- the round-69 case: even the median of
      the samples sits below the floor.
    * ``"target_reference_temporal_collapse"`` -- round 92: the median clears the
      floor but at least one sampled frame sits below it, which is the shape of a
      take that shows the target character in some frames and the V1 performer in
      others.  It needs the per-sample minimum to have been recorded; an audit
      that only stored a median cannot assert what it never measured.
    """

    if not head_layer_only:
        return None
    if not target_reference_audit.get("available"):
        return None
    median = target_reference_audit.get("similarity")
    if median is None:
        return None
    if float(median) < CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR:
        return "target_reference_similarity"
    minimum = target_reference_audit.get("minimum_similarity")
    if minimum is None:
        return None
    if float(minimum) < CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR:
        return "target_reference_temporal_collapse"
    return None


def character_swap_head_layer_blocking(
    head_layer_only: bool,
    target_reference_audit: dict,
) -> bool:
    """Decide whether a head/face-layer-only rebuild blocks the take.

    Round 69 item 3, isolated so the veto is gradeable without two rendered
    videos and an ffmpeg harness: the two audits that can see *how much* of the
    character was replaced (whole-character integration and wardrobe shift) have
    to say "only the layer above the neck changed", and the take has to also sit
    further from Picture 1 than ``CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR`` --
    on its median sample (round 69) or on any single sample (round 92).  A missing
    or unreadable target-reference audit never blocks -- QC must not spend fresh
    seeds on a measurement it did not take -- and a take that resembles the
    reference in every sample stays the advisory witness round 52 shipped.
    """

    return bool(
        character_swap_head_layer_blocking_cause(head_layer_only, target_reference_audit)
    )


def character_swap_identity_attempt_ceiling(
    job_attempts: int,
    spec_maximum_attempts: object,
    blocking: bool,
    blocking_max_attempts: object = None,
) -> int:
    """How many times one Segment may re-roll on a failing identity audit.

    The compiled pass spec normally decides: the lean Design audit path compiles
    ``maximum_attempts: 1`` because its takes are cheap to eyeball in a Preview,
    and the full render path compiles 3 because there the re-rolls are paid for.
    A *blocking* head-layer verdict (round 69 item 3) may lift the spec, but round
    86 item A ships the lift at one, so the spec is what actually runs unless the
    director opts back in through ``character_swap_blocking_max_attempts()``.  The
    ``blocking_max_attempts`` argument lets a caller (or a test) state the lift
    explicitly instead of reading the environment.  The Job's own budget always
    remains the hard cap in both directions, and the answer never drops below the
    single attempt that produced the audit.
    """

    try:
        attempts = int(job_attempts)
    except (TypeError, ValueError):
        attempts = 1
    attempts = max(1, attempts)
    try:
        # ``or 3`` is the shipped reading: a spec that says 0 or leaves the key
        # blank has never meant "generate zero takes", it means the default.
        spec_maximum = int(spec_maximum_attempts or 3)
    except (TypeError, ValueError):
        spec_maximum = 3
    ceiling = max(1, min(attempts, spec_maximum))
    if blocking:
        escalation = (
            character_swap_blocking_max_attempts()
            if blocking_max_attempts is None
            else blocking_max_attempts
        )
        try:
            escalation = int(escalation)
        except (TypeError, ValueError):
            escalation = CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS_DEFAULT
        escalation = max(1, min(escalation, CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS))
        ceiling = max(ceiling, min(attempts, escalation))
    return ceiling


COMPLETE_LOCATION_SOUND_CONTRACT = (
    "COMPLETE LOCATION-SOUND REFERENCE CONTRACT — MANDATORY. The supplied authored "
    "speech Audio reference is one authoritative, already synchronized production "
    "recording containing the exact authored words together with continuous native "
    "ambience and physical Foley in one acoustic space. Preserve the entire reference "
    "soundtrack continuously, including its environment before, under, between and "
    "after spoken words. Never isolate the voice, denoise or gate the ambience, replace "
    "non-speech intervals with silence, duplicate dialogue, paraphrase words or invent "
    "narration. Additional visible contact sounds may be generated only when physically "
    "required by the picture and must join the same acoustic space. "
)


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def _segment_core_bounds(segment: dict) -> tuple[float, float]:
    """Return the non-overlapping timeline range represented by a segment."""
    core_start = segment.get("core_start_seconds")
    core_end = segment.get("core_end_seconds")
    start = float(segment.get("start_seconds", 0.0) if core_start is None else core_start)
    end = float(segment.get("end_seconds", start) if core_end is None else core_end)
    return start, max(start, end)


def _shot_progress_rows(job: dict, segments: list[dict]) -> list[dict]:
    """Normalize authored Shot weights and map each Shot to all of its segments."""
    raw_rows = [row for row in (job.get("progress_shots") or []) if isinstance(row, dict)]
    if not raw_rows:
        return []

    segment_ids = {
        str(segment.get("segment_id", "")): index
        for index, segment in enumerate(segments)
        if segment.get("segment_id")
    }
    normalized: list[dict] = []
    for row_index, source in enumerate(raw_rows):
        shot_id = str(
            source.get("cue_id")
            or source.get("shot_id")
            or source.get("id")
            or f"shot_{row_index + 1}"
        )
        start_value = source.get("start_seconds")
        end_value = source.get("end_seconds")
        start = float(start_value) if start_value is not None else None
        end = float(end_value) if end_value is not None else None
        duration_value = source.get("duration_seconds")
        duration = (
            max(0.0, float(duration_value))
            if duration_value is not None
            else max(0.0, float(end or 0.0) - float(start or 0.0))
        )

        required: set[int] = set()
        explicit_segment_ids = source.get("segment_ids") or []
        if isinstance(explicit_segment_ids, (list, tuple, set)):
            required.update(
                segment_ids[str(segment_id)]
                for segment_id in explicit_segment_ids
                if str(segment_id) in segment_ids
            )
        if not required:
            required.update(
                index
                for index, segment in enumerate(segments)
                if shot_id in {str(value) for value in (segment.get("shot_ids") or [])}
            )
        if not required and start is not None and end is not None:
            for index, segment in enumerate(segments):
                core_start, core_end = _segment_core_bounds(segment)
                if start < core_end - 1e-9 and end > core_start + 1e-9:
                    required.add(index)
            # A zero-duration marker belongs to the segment beginning at that
            # instant, or the final segment when it sits at the timeline end.
            if not required and abs(end - start) <= 1e-9:
                for index, segment in enumerate(segments):
                    core_start, core_end = _segment_core_bounds(segment)
                    if core_start - 1e-9 <= start < core_end - 1e-9:
                        required.add(index)
                        break
                if not required and segments:
                    _, final_end = _segment_core_bounds(segments[-1])
                    if abs(start - final_end) <= 1e-9:
                        required.add(len(segments) - 1)
        if not required and segments:
            # Keep malformed legacy metadata finishable instead of leaving a
            # Shot permanently pending.
            required.add(min(row_index, len(segments) - 1))
        normalized.append(
            {
                "shot_id": shot_id,
                "duration_seconds": duration,
                "required_segment_indexes": required,
            }
        )
    return normalized


def build_render_progress(
    job: dict,
    segments: list[dict],
    completed_indexes: set[int],
    *,
    stage: str,
    current_index: int | None = None,
) -> dict:
    """Build truthful duration-weighted progress for one smart-render event.

    Authored ``progress_shots`` are preferred when supplied by the Studio. A
    Shot spanning multiple internal segments is complete only after every one
    of those segments has completed. Older jobs fall back to non-overlapping
    segment core durations while still reporting unique Shot IDs when present.
    """
    completed_set = {
        int(index) for index in completed_indexes if 0 <= int(index) < len(segments)
    }
    shot_rows = _shot_progress_rows(job, segments)

    shot_requirements: dict[str, set[int]] = {}
    if shot_rows:
        for row in shot_rows:
            shot_requirements.setdefault(str(row["shot_id"]), set()).update(
                row["required_segment_indexes"]
            )
    else:
        for index, segment in enumerate(segments):
            ids = [str(value) for value in (segment.get("shot_ids") or []) if str(value)]
            if not ids:
                ids = [str(segment.get("segment_id") or f"segment_{index + 1}")]
            for shot_id in ids:
                shot_requirements.setdefault(shot_id, set()).add(index)

    completed_shot_ids = [
        shot_id
        for shot_id, required in shot_requirements.items()
        if required and required.issubset(completed_set)
    ]
    total_shots = len(shot_requirements)
    completed_shots = len(completed_shot_ids)

    segment_weights = [
        max(0.0, core_end - core_start)
        for core_start, core_end in (_segment_core_bounds(segment) for segment in segments)
    ]
    if shot_rows and sum(float(row["duration_seconds"]) for row in shot_rows) > 1e-9:
        total_weight = sum(float(row["duration_seconds"]) for row in shot_rows)
        completed_weight = sum(
            float(row["duration_seconds"])
            for row in shot_rows
            if row["required_segment_indexes"]
            and row["required_segment_indexes"].issubset(completed_set)
        )
        weight_source = "shots"
    else:
        total_weight = sum(segment_weights)
        completed_weight = sum(
            weight for index, weight in enumerate(segment_weights) if index in completed_set
        )
        weight_source = "segment_core"

    if total_weight <= 1e-9:
        percent_complete = 100.0 if len(completed_set) == len(segments) else 0.0
    else:
        percent_complete = min(100.0, max(0.0, completed_weight / total_weight * 100.0))
    percent_complete = round(percent_complete, 2)

    current_segment = (
        segments[current_index]
        if current_index is not None and 0 <= current_index < len(segments)
        else None
    )
    current_shot_ids: list[str] = []
    if current_segment is not None:
        current_shot_ids = [
            str(value) for value in (current_segment.get("shot_ids") or []) if str(value)
        ]
        if not current_shot_ids and shot_rows:
            current_shot_ids = [
                str(row["shot_id"])
                for row in shot_rows
                if current_index in row["required_segment_indexes"]
            ]

    return {
        "stage": str(stage),
        "current_segment_index": current_index,
        "current_segment_number": current_index + 1 if current_index is not None else None,
        "current_segment_id": (
            str(current_segment.get("segment_id", "")) if current_segment is not None else ""
        ),
        "segment_count": len(segments),
        "completed_segments": len(completed_set),
        "remaining_segments": max(0, len(segments) - len(completed_set)),
        "current_shot_ids": current_shot_ids,
        "completed_shot_ids": completed_shot_ids,
        "completed_shots": completed_shots,
        "total_shots": total_shots,
        "remaining_shots": max(0, total_shots - completed_shots),
        "weight_source": weight_source,
        "completed_weight_seconds": round(completed_weight, 6),
        "total_weight_seconds": round(total_weight, 6),
        "percent_complete": percent_complete,
        "percent_remaining": round(max(0.0, 100.0 - percent_complete), 2),
    }


def _post_json(server: str, endpoint: str, payload: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        server + endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _direct_urlopen(request, timeout) as response:
        body = response.read().decode("utf-8").strip()
    return json.loads(body) if body else {}


def release_comfy_memory(server: str, timeout: int) -> str:
    """Best-effort model/VRAM cleanup supported by current ComfyUI releases."""
    try:
        _post_json(
            server,
            "/free",
            {"unload_models": True, "free_memory": True},
            timeout,
        )
        return "ComfyUI models and VRAM released"
    except Exception as exc:  # cleanup must never discard a completed segment
        return f"ComfyUI cleanup skipped: {exc}"


def _primary_video(outputs: list[dict]) -> Path | None:
    candidates: list[tuple[int, int, Path]] = []
    for index, item in enumerate(outputs):
        local_path = Path(str(item.get("local_path", "")))
        if not local_path.is_file() or local_path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        # ComfyUI history can include the uploaded LoadVideo source alongside
        # the generated SaveVideo file. Choosing the first mp4 silently fed V1
        # back into QC and the master, while the correct generated take stayed
        # visible only in ComfyUI. Prefer real output artefacts and demote input
        # echoes regardless of their list order or generic ``kind=images``.
        artifact_type = str(item.get("type") or "").strip().casefold()
        node_id = str(item.get("node_id") or "").strip().casefold()
        priority = 0
        if artifact_type == "output":
            priority += 100
        elif artifact_type == "input":
            priority -= 100
        if "save" in node_id:
            priority += 20
        candidates.append((priority, index, local_path.resolve()))
    if candidates:
        # Later SaveVideo artefacts win only when their output priority ties.
        return max(candidates, key=lambda row: (row[0], row[1]))[2]
    return None


def _write_manifest(path: Path, payload: dict) -> None:
    payload = dict(payload)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def classify_generation_error(error: object) -> str:
    """Classify retry/failure evidence without weakening output quality."""
    text = str(error or "").casefold()
    if any(
        marker in text
        for marker in (
            "out of memory",
            "oom",
            "cuda oom",
            "allocation on device",
            "not enough memory",
            "memory allocation",
        )
    ):
        return "oom"
    if any(marker in text for marker in ("timed out", "timeout")):
        return "timeout"
    if any(
        marker in text
        for marker in (
            "connection reset",
            "connection refused",
            "connection did not recover",
            "remote end closed",
            "temporarily unavailable",
            "urlopen error",
        )
    ):
        return "transport"
    if any(
        marker in text
        for marker in ("no such file", "missing media", "produced no downloadable video")
    ):
        return "media"
    return "unknown"


def _server_lora_choices(object_info: dict) -> list[str]:
    """Read ComfyUI's concrete LoRA filenames from object_info."""

    loader = object_info.get("LoraLoaderModelOnly") or {}
    required = ((loader.get("input") or {}).get("required") or {})
    spec = required.get("lora_name") or []
    choices = spec[0] if isinstance(spec, list) and spec else []
    if not isinstance(choices, list):
        return []
    return [str(value) for value in choices if str(value).strip()]


def _character_swap_lora_for_server(
    current_name: str,
    available_names: list[str],
) -> str:
    """Prefer V1.5, otherwise resolve the template's V1 by basename."""

    def normalized(value: str) -> str:
        return (
            value.replace("\\", "/").rsplit("/", 1)[-1]
            .lower().replace("-", "_")
        )

    for name in available_names:
        token = normalized(name)
        if "character_swap" in token and ("v1.5" in token or "v1_5" in token):
            return name
    current_token = normalized(current_name)
    for name in available_names:
        if normalized(name) == current_token:
            return name
    return current_name


def prefer_server_character_swap_lora(job: dict, object_info: dict) -> list[str]:
    """Patch every Relay pass to the best Character Swap LoRA on the server."""

    choices = _server_lora_choices(object_info)
    selected: list[str] = []
    for segment in job.get("segments") or []:
        if not isinstance(segment, dict):
            continue
        for pass_row in segment.get("character_swap_passes") or []:
            if not isinstance(pass_row, dict):
                continue
            workflow = pass_row.get("workflow") or {}
            for node in workflow.values():
                if (
                    not isinstance(node, dict)
                    or node.get("class_type") != "LoraLoaderModelOnly"
                ):
                    continue
                inputs = node.setdefault("inputs", {})
                current = str(inputs.get("lora_name") or "")
                if "character_swap" not in current.lower().replace("-", "_"):
                    continue
                chosen = _character_swap_lora_for_server(current, choices)
                inputs["lora_name"] = chosen
                pass_row["character_swap_lora"] = chosen
                if chosen not in selected:
                    selected.append(chosen)
    return selected


def preflight_smart_render(job: dict) -> dict:
    """Fail before media upload if a long render cannot complete on this host."""
    segments = list(job.get("segments") or [])
    if not segments:
        raise ValueError("Smart Render requires at least one internal segment.")
    for index, segment in enumerate(segments, 1):
        duration = float(segment.get("end_seconds", 0.0)) - float(
            segment.get("start_seconds", 0.0)
        )
        if duration <= 0.0 or duration > 15.0 + 1e-6:
            raise ValueError(
                f"Segment {index} has invalid duration {duration:.3f}s; expected 0–15s."
            )

    ffmpeg = Path(str(job.get("ffmpeg", "")))
    ffprobe = Path(str(job.get("ffprobe", "")))
    if not ffmpeg.is_file() or not ffprobe.is_file():
        raise FileNotFoundError("Bundled FFmpeg or FFprobe is missing.")

    missing_media = []
    for item in job.get("media", []):
        raw_path = item.get("path", "") if isinstance(item, dict) else item
        media_path = Path(str(raw_path))
        if not media_path.is_file():
            missing_media.append(str(media_path))
    if missing_media:
        preview = "\n".join(missing_media[:8])
        raise FileNotFoundError(
            "Reference media is missing before ComfyUI upload. Re-link the "
            "Media Pool source or reopen the portable project folder:\n" + preview
        )
    final_hold_plate = str(job.get("final_hold_plate", "")).strip()
    if final_hold_plate and not Path(final_hold_plate).is_file():
        raise FileNotFoundError(
            "Immutable P1 final-hold plate is missing before render: "
            + final_hold_plate
        )

    manifest_rows = [
        item for item in (job.get("media") or []) if isinstance(item, dict)
    ]
    for segment in segments:
        continuity = segment.get("continuity") or {}
        runtime_ids = (
            {str(continuity.get("loader_node_id"))}
            if continuity.get("loader_node_id")
            else set()
        )
        validate_portable_media_manifest(
            segment.get("workflow") or {},
            manifest_rows,
            runtime_loader_node_ids=runtime_ids,
        )
        for pass_row in segment.get("character_swap_passes") or []:
            pass_runtime_ids = (
                {str(pass_row.get("runtime_source_loader_node_id"))}
                if pass_row.get("runtime_source")
                else set()
            )
            validate_portable_media_manifest(
                pass_row.get("workflow") or {},
                manifest_rows,
                runtime_loader_node_ids=pass_runtime_ids,
            )

    output_parent = Path(job["master_output"]).parent
    output_parent.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(output_parent).free
    if free_bytes < MINIMUM_FREE_DISK_BYTES:
        raise OSError(
            f"Smart Long Render needs at least 2GB free disk space; only "
            f"{free_bytes / 1024**3:.2f}GB is available."
        )

    workflows = [
        workflow
        for segment in segments
        for workflow in [
            segment.get("workflow") or {},
            *[
                row.get("workflow") or {}
                for row in segment.get("character_swap_passes") or []
                if isinstance(row, dict)
            ],
        ]
    ]
    required_classes = {
        str(node.get("class_type", ""))
        for workflow in workflows
        for node in workflow.values()
        if isinstance(node, dict) and node.get("class_type")
    }
    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    object_info = _request_json(
        urllib.request.Request(server + "/object_info", method="GET"),
        http_timeout,
    )
    selected_swap_loras = prefer_server_character_swap_lora(job, object_info)
    missing = sorted(required_classes - set(object_info))
    if missing:
        raise RuntimeError(
            "ComfyUI is missing required workflow node classes: " + ", ".join(missing)
        )
    return {
        "segment_count": len(segments),
        "node_class_count": len(required_classes),
        "free_disk_gb": round(free_bytes / 1024**3, 2),
        "character_swap_loras": selected_swap_loras,
    }


def _patch_continuity(workflow: dict, continuity: dict, uploaded_name: str) -> None:
    loader_id = str(continuity.get("loader_node_id", ""))
    h3_id = str(continuity.get("h3_node_id", ""))
    binding = str(continuity.get("binding", ""))
    connection = continuity.get("connection")
    if not loader_id or not h3_id or not binding or not isinstance(connection, list):
        return
    loader = workflow.get(loader_id)
    h3_node = workflow.get(h3_id)
    if not isinstance(loader, dict) or not isinstance(h3_node, dict):
        return
    loader_input = str(continuity.get("loader_input", "file"))
    loader.setdefault("inputs", {})[loader_input] = uploaded_name
    h3_inputs = h3_node.setdefault("inputs", {})
    occupied = h3_inputs.get(binding)
    if occupied is not None and occupied != connection:
        raise RuntimeError(
            "Continuity reference slot collision at " + binding
            + "; refusing to overwrite an active Timeline reference."
        )
    h3_inputs[binding] = connection
    # The preceding tail exists strictly as visual motion context.  Even a
    # loader capable of exposing synchronized sound must never feed old audio
    # into the next H3 segment, where it can duplicate dialogue or create an
    # audible tail.
    if bool(continuity.get("visual_only", False)):
        _canonicalize_reference_input_order(h3_node)
        return
    paired = str(continuity.get("paired_audio_binding", ""))
    paired_connection = continuity.get("paired_audio_connection")
    if paired and isinstance(paired_connection, list):
        h3_node["inputs"][paired] = paired_connection
    _canonicalize_reference_input_order(h3_node)


def _canonicalize_reference_input_order(h3_node: dict) -> None:
    """Keep Autogrow references contiguous and deterministic at runtime.

    The continuity binding was disconnected during compilation and is added
    back at runtime. Rebuilding and compacting the mapping removes any
    ambiguity between JSON insertion order, sparse physical loader slots, and
    Autogrow suffix order, so prompt ordinals always match the exact fields
    consumed by MiniMaxH3ReferenceToVideo.
    """
    inputs = h3_node.get("inputs") or {}
    prefixes = {
        "ref_images.ref_image_": 0,
        "ref_videos.ref_video_": 1,
        "ref_video_audios.ref_video_audio_": 2,
        "ref_audios.ref_audio_": 3,
    }

    ordinary = [item for item in inputs.items() if not any(item[0].startswith(p) for p in prefixes)]
    references: list[tuple[str, object]] = []
    for prefix, _group in sorted(prefixes.items(), key=lambda item: item[1]):
        rows = [item for item in inputs.items() if item[0].startswith(prefix)]
        rows.sort(
            key=lambda item: int(re.search(r"_(\d+)$", item[0]).group(1))
            if re.search(r"_(\d+)$", item[0]) else 10_000
        )
        references.extend(
            (f"{prefix}{request_index}", value)
            for request_index, (_name, value) in enumerate(rows)
        )
    h3_node["inputs"] = dict(ordinary + references)


def _h3_prompt_nodes(workflow: dict) -> tuple[dict, dict] | tuple[None, None]:
    """Return the H3 generation node and its connected text node."""

    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if "MiniMaxH3" not in str(node.get("class_type", "")):
            continue
        connection = (node.get("inputs") or {}).get("prompt")
        if not isinstance(connection, list) or not connection:
            continue
        prompt_node = workflow.get(str(connection[0]))
        if isinstance(prompt_node, dict):
            return node, prompt_node
    return None, None


def _prompt_section(prompt: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ims)^{re.escape(heading)}:\s*(.*?)(?=^[a-z_]+:\s*$|\Z)"
    )
    match = pattern.search(str(prompt or ""))
    return match.group(1).strip() if match else ""


def build_native_ambience_workflow(
    workflow: dict,
    *,
    duration_seconds: float,
    cache_token: str,
) -> dict:
    """Create a low-cost, speech-free H3 pass that generates native location sound.

    A dry TTS stem is a strong acoustic condition: real H3 tests showed that merely
    asking for ambience, or even adding a second ambience Audio reference, still lets
    the dry stem gate the location bed.  This auxiliary pass deliberately has no Audio
    reference.  Its output audio becomes part of one complete reference before the
    final H3 request.
    """

    result = deepcopy(workflow)
    h3_node, prompt_node = _h3_prompt_nodes(result)
    if h3_node is None or prompt_node is None:
        raise RuntimeError("Could not locate the MiniMax H3 prompt connection.")

    h3_inputs = h3_node.setdefault("inputs", {})
    for key in list(h3_inputs):
        if key.startswith("ref_audios.ref_audio_") or key.startswith(
            "ref_video_audios.ref_video_audio_"
        ):
            h3_inputs.pop(key, None)
    _canonicalize_reference_input_order(h3_node)

    original = str((prompt_node.get("inputs") or {}).get("value", ""))
    visual_definitions = "\n".join(
        line
        for line in _prompt_section(original, "subject_definitions").splitlines()
        if not re.match(r"\s*<Audio\s+\d+>", line, re.I)
    ).strip()
    soundscape = _prompt_section(original, "overall_soundscape")
    # The opening soundscape paragraph carries the scene acoustics. Timestamped
    # Native Audio blocks also repeat authored-speaker instructions, so they are
    # intentionally excluded from this speech-free pass.
    soundscape = re.split(r"(?im)^\[Native Audio\b", soundscape, maxsplit=1)[0].strip()
    if not soundscape:
        soundscape = (
            "Continuous room tone or outdoor atmosphere derived from the visible "
            "location, with picture-motivated movement, surface contact and object Foley."
        )
    duration = max(0.01, float(duration_seconds))
    prompt_node.setdefault("inputs", {})["value"] = (
        "subject_definitions:\n"
        + visual_definitions
        + "\n\nsummary:\nCreate a speech-free native location-sound pass for the exact "
        f"same scene and duration ({duration:.3f} seconds). All visible people remain "
        "silent with closed non-speaking mouths. Preserve the active visual references "
        "only to infer the correct physical environment and synchronized non-vocal Foley.\n\n"
        "detailed_description:\nHUMAN VOCAL CHANNEL: EMPTY. No dialogue, narration, "
        "voice-over, lyrics, singing, whisper, gasp, laugh, chant, intelligible crowd "
        "voice or spoken word in any language. Generate only real diegetic atmosphere, "
        "weather, room tone, material contact, movement and object sounds. The continuous "
        "environment bed begins on frame one, remains clearly audible through every frame "
        "and never gates or drops to digital silence. No non-diegetic music.\n\n"
        "overall_soundscape:\n"
        + soundscape
        + "\nContinuous non-vocal ambience and physically synchronized Foley only; no human voice.\n\n"
        "non_diegetic_music:\nN/A"
    )

    # Audio behavior is independent of final image resolution.  The verified 0.2 MP
    # pass is materially faster and its picture is discarded after audio extraction.
    for node in result.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or {}
        if isinstance(inputs.get("megapixels"), (int, float)):
            inputs["megapixels"] = min(0.2, float(inputs["megapixels"]))
        if isinstance(inputs.get("resize_type.scale"), (int, float)):
            inputs["resize_type.scale"] = 1.0
        if str(node.get("class_type", "")) == "SaveVideo":
            inputs["filename_prefix"] = f"video/H3_native_ambience_{cache_token}"
    return result


def patch_complete_location_reference(
    workflow: dict,
    *,
    loader_node_id: str,
    upload_name: str,
) -> None:
    """Replace the dry TTS loader with one complete on-location audio reference."""

    loader = workflow.get(str(loader_node_id))
    if not isinstance(loader, dict) or str(loader.get("class_type", "")) != "LoadAudio":
        raise RuntimeError("The authored TTS LoadAudio node is unavailable.")
    loader.setdefault("inputs", {})["audio"] = str(upload_name)
    _h3_node, prompt_node = _h3_prompt_nodes(workflow)
    if prompt_node is None:
        raise RuntimeError("Could not locate the MiniMax H3 prompt text node.")
    original = str((prompt_node.get("inputs") or {}).get("value", ""))
    if "COMPLETE LOCATION-SOUND REFERENCE CONTRACT" not in original:
        prompt_node.setdefault("inputs", {})["value"] = (
            COMPLETE_LOCATION_SOUND_CONTRACT
            + CINEMATIC_DIALOGUE_ACOUSTIC_INTEGRATION_CONTRACT
            + "\n\n"
            + original
        )


def _extract_video_audio(ffmpeg: Path, source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source), "-vn", "-ac", "2", "-ar", "32000",
            "-c:a", "pcm_s16le", str(destination),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if completed.returncode or not destination.is_file() or destination.stat().st_size <= 44:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1200:]
        raise RuntimeError("Could not extract H3 native ambience: " + detail)
    return destination


def _audio_mean_volume_db(ffmpeg: Path, source: Path) -> float:
    completed = subprocess.run(
        [
            str(ffmpeg), "-hide_banner", "-i", str(source),
            "-af", "volumedetect", "-f", "null", "NUL",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    report = completed.stderr.decode("utf-8", errors="replace")
    match = re.search(r"mean_volume:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*dB", report, re.I)
    if not match or match.group(1).casefold() == "-inf":
        return float("-inf")
    return float(match.group(1))


def _mix_complete_location_reference(
    ffmpeg: Path,
    *,
    speech: Path,
    ambience: Path,
    destination: Path,
    duration_seconds: float,
    ambience_gain: float,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.01, float(duration_seconds))
    gain = max(0.05, min(1.5, float(ambience_gain)))
    filter_graph = (
        f"[0:a]aresample=32000,apad=whole_dur={duration:.6f},"
        f"atrim=duration={duration:.6f},volume=1.0[voice];"
        f"[1:a]aresample=32000,apad=whole_dur={duration:.6f},"
        f"atrim=duration={duration:.6f},volume={gain:.4f}[amb];"
        "[voice][amb]amix=inputs=2:duration=longest:normalize=0,"
        "alimiter=limit=0.95[mix]"
    )
    completed = subprocess.run(
        [
            str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(speech), "-i", str(ambience),
            "-filter_complex", filter_graph, "-map", "[mix]", "-t", f"{duration:.6f}",
            "-ac", "2", "-ar", "32000", "-c:a", "pcm_s16le", str(destination),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if completed.returncode or not destination.is_file() or destination.stat().st_size <= 44:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1200:]
        raise RuntimeError("Could not build complete location-sound reference: " + detail)
    return destination


def _queue_auxiliary_outputs(
    job: dict,
    segment: dict,
    workflow: dict,
    destination: Path,
    *,
    client_prefix: str,
    progress_label: str,
) -> tuple[str, list[dict]]:
    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    reconnect_timeout = max(
        1, int(job.get("connection_recovery_timeout", DEFAULT_RECONNECT_TIMEOUT_SECONDS))
    )
    output_download_recovery_timeout = max(
        10,
        int(
            job.get(
                "output_download_recovery_timeout",
                DEFAULT_OUTPUT_DOWNLOAD_RECOVERY_SECONDS,
            )
        ),
    )
    payload = json.dumps(
        {"prompt": workflow, "client_id": client_prefix + uuid.uuid4().hex},
        ensure_ascii=False,
    ).encode("utf-8")
    queued = _request_json(
        urllib.request.Request(
            server + "/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        ),
        http_timeout,
    )
    prompt_id = str(queued.get("prompt_id", ""))
    if not prompt_id:
        raise RuntimeError(f"ComfyUI did not return a prompt_id for {progress_label}.")
    emit({
        "progress": (
            f"Segment {segment['index'] + 1}/{job['segment_count']} · "
            f"{progress_label} queued · {prompt_id}"
        ),
        "segment_index": segment["index"],
        "auxiliary_prompt_id": prompt_id,
    })
    _history, outputs = wait_for_history(
        server,
        prompt_id,
        poll_interval=max(0.1, float(job.get("history_poll_interval", 1.0))),
        generation_timeout=effective_generation_timeout_seconds(job),
        http_timeout=http_timeout,
        reconnect_timeout=reconnect_timeout,
        segment_id=str(segment.get("segment_id", "")) + ":" + progress_label,
    )
    downloaded = download_outputs(
        server,
        outputs,
        destination,
        http_timeout,
        reconnect_timeout=reconnect_timeout,
        prompt_id=prompt_id,
        segment_id=str(segment.get("segment_id", "")) + ":" + progress_label,
        download_recovery_timeout=output_download_recovery_timeout,
    )
    return prompt_id, downloaded


def _queue_auxiliary_workflow(
    job: dict,
    segment: dict,
    workflow: dict,
    destination: Path,
) -> Path:
    _prompt_id, downloaded = _queue_auxiliary_outputs(
        job,
        segment,
        workflow,
        destination,
        client_prefix="h3-native-ambience-",
        progress_label="native ambience pass",
    )
    video = _primary_video(downloaded)
    if video is None:
        raise RuntimeError("Native ambience pass produced no downloadable video.")
    return video


def prepare_complete_location_sound_reference(
    job: dict,
    segment: dict,
    workflow: dict,
) -> dict | None:
    """Generate/cache ambience, combine it with TTS, and patch the final H3 graph."""

    spec = dict(segment.get("location_sound_reference") or {})
    if not bool(spec.get("enabled")):
        return None
    speech = Path(str(spec.get("speech_path", "")))
    if not speech.is_file() or speech.stat().st_size <= 44:
        raise FileNotFoundError("Authored segment TTS is missing: " + str(speech))
    ambience = Path(str(spec.get("ambience_cache_path", "")))
    complete = Path(str(spec.get("complete_cache_path", "")))
    duration = max(0.01, float(spec.get("duration_seconds", 0.0)))
    token = str(spec.get("cache_token", "location"))
    ffmpeg = Path(str(job.get("ffmpeg", "")))

    ambience_valid = (
        ambience.is_file()
        and ambience.stat().st_size > 44
        and _audio_mean_volume_db(ffmpeg, ambience) > -55.0
    )
    if not ambience_valid:
        ambience.unlink(missing_ok=True)
        last_ambience_error: Exception | None = None
        for ambience_attempt in range(1, 3):
            try:
                ambience_workflow = build_native_ambience_workflow(
                    workflow, duration_seconds=duration, cache_token=token
                )
                ambience_workflow = _workflow_for_attempt(
                    ambience_workflow,
                    int(segment.get("seed", 0) or 0),
                    ambience_attempt,
                )
                auxiliary_dir = ambience.parent / (
                    ambience.stem + f"_render_{ambience_attempt}"
                )
                video = _queue_auxiliary_workflow(
                    job, segment, ambience_workflow, auxiliary_dir
                )
                _extract_video_audio(ffmpeg, video, ambience)
                mean_db = _audio_mean_volume_db(ffmpeg, ambience)
                if mean_db <= -55.0:
                    raise RuntimeError(
                        f"H3 native ambience is effectively silent ({mean_db:.1f} dB)."
                    )
                emit({
                    "progress": (
                        f"Segment {segment['index'] + 1}/{job['segment_count']} · "
                        f"native ambience cached ({mean_db:.1f} dB mean)"
                    ),
                    "segment_index": segment["index"],
                })
                last_ambience_error = None
                break
            except Exception as exc:
                last_ambience_error = exc
                ambience.unlink(missing_ok=True)
                if ambience_attempt < 2:
                    emit({
                        "progress": (
                            f"Segment {segment['index'] + 1}/{job['segment_count']} · "
                            "native ambience was unavailable or silent; retrying once"
                        ),
                        "segment_index": segment["index"],
                    })
        if last_ambience_error is not None:
            raise RuntimeError(
                "Could not create an audible native location bed after two attempts: "
                + str(last_ambience_error)
            )

    if not complete.is_file() or complete.stat().st_size <= 44:
        _mix_complete_location_reference(
            ffmpeg,
            speech=speech,
            ambience=ambience,
            destination=complete,
            duration_seconds=duration,
            ambience_gain=float(spec.get("ambience_gain", 0.55)),
        )

    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    desired_name = str(spec.get("upload_name") or complete.name)
    uploaded = upload_file(server, complete, http_timeout, desired_name)
    remote_name = str((uploaded or {}).get("name") or desired_name)
    patch_complete_location_reference(
        workflow,
        loader_node_id=str(spec.get("loader_node_id", "")),
        upload_name=remote_name,
    )
    emit({
        "progress": (
            f"Segment {segment['index'] + 1}/{job['segment_count']} · "
            "complete dialogue + location-sound reference attached"
        ),
        "segment_index": segment["index"],
    })
    return {
        "file": complete.name,
        "upload_name": remote_name,
        "result": uploaded,
        "kind": "complete_location_sound_reference",
    }


def extract_tail_frames(
    ffmpeg: Path,
    ffprobe: Path,
    source: Path,
    destination: Path,
    *,
    frame_count: int = 24,
    fps: int = 24,
) -> Path:
    """Extract exact motion-only tail frames for the next H3 segment."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame_count = max(1, int(frame_count))
    fps = max(1, int(fps))
    source_duration = _probe_duration(ffprobe, source)
    tail_seconds = frame_count / fps
    # Phone, WhatsApp and VFR plates publish a container duration that runs a
    # little past the last seekable picture.  An input seek into that tail
    # decodes zero frames and FFmpeg then fails inside its encoder setup
    # ("Conversion failed!") instead of handing back a shorter tail, which used
    # to abort the whole Smart Render step.  Take the window from the end of the
    # span that can actually be decoded, and keep an output-side seek, which
    # decodes from the beginning and still answers, as the fallback.
    try:
        safe_span = decode_safe_video_span(source, source_duration, ffprobe=ffprobe)
    except (OSError, SubprocessError, ValueError, TypeError):
        # Measuring the span is an optimisation, never a requirement: without it
        # the window stays where it always was and the output-side seek below
        # still rescues the render.  ``SubprocessError`` is imported by name
        # because tests replace this module's ``subprocess`` namespace.
        safe_span = 0.0
    window_end = min(source_duration, safe_span) if safe_span > 0.0 else source_duration
    start = max(0.0, window_end - tail_seconds)
    detail = ""
    for prefix, suffix, label in (
        (["-ss", f"{start:.6f}"], [], "input seek"),
        ([], ["-ss", f"{start:.6f}"], "output seek"),
    ):
        command = [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
            *prefix, "-i", str(source), *suffix,
            "-an", "-vf", f"fps={fps}", "-frames:v", str(frame_count),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(destination),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if not completed.returncode and destination.is_file():
            return destination.resolve()
        problem = (completed.stderr or "").strip()
        detail = f"{label} at {start:.3f}s: " + (problem[-600:] or "no frames decoded")
        destination.unlink(missing_ok=True)
    raise RuntimeError("Could not extract continuity tail: " + detail)


def _probe_duration(ffprobe: Path, source: Path) -> float:
    completed = subprocess.run(
        [
            str(ffprobe), "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode:
        raise RuntimeError("Could not probe continuity source: " + completed.stderr[-800:])
    try:
        return max(0.0, float(completed.stdout.strip()))
    except ValueError as exc:
        raise RuntimeError("Continuity source has no readable duration.") from exc


def extract_last_frame(
    ffmpeg: Path,
    ffprobe: Path,
    source: Path,
    destination: Path,
) -> Path:
    """Extract a still near the real media end without carrying prior motion."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    duration = _probe_duration(ffprobe, source)
    # H3 output durations are quantized to valid frame counts and are often
    # longer than the requested seconds. Probe the file rather than trusting
    # the requested segment duration, otherwise this would not be its tail.
    requested = max(0.0, duration - 0.08)
    # 0.08s before the published end is precisely where a phone or WhatsApp
    # plate stops answering: the seek lands behind the last seekable picture and
    # FFmpeg fails inside its encoder ("Conversion failed!") rather than
    # returning nothing.  Climb back into the decodable span first, then try the
    # end-relative and output-side forms of the seek, then the opening frame, so
    # one unreachable tail timestamp costs a slightly earlier still instead of
    # aborting motion continuity for the next H3 Segment.
    seek = clamp_seek_to_decode_span(source, requested, duration, ffprobe=ffprobe)
    attempts: list[tuple[list[str], list[str], str]] = [
        (["-ss", f"{seek:.6f}"], [], "input seek"),
    ]
    if requested > seek:
        attempts.append((["-sseof", "-0.5"], [], "end-relative seek"))
    attempts.append(([], ["-ss", f"{seek:.6f}"], "output seek"))
    if seek > 0.0:
        attempts.append(([], [], "opening frame"))
    detail = ""
    for prefix, suffix, label in attempts:
        command = [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
            *prefix, "-i", str(source), *suffix,
            "-frames:v", "1", "-q:v", "2", str(destination),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if not completed.returncode and destination.is_file():
            return destination.resolve()
        problem = (completed.stderr or "").strip()
        detail = f"{label}: " + (problem[-600:] or "no frame decoded")
        destination.unlink(missing_ok=True)
    raise RuntimeError("Could not extract continuity frame: " + detail)


def _has_audio(ffprobe: Path, source: Path) -> bool:
    completed = subprocess.run(
        [
            str(ffprobe), "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=index", "-of", "csv=p=0", str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.returncode == 0 and bool(completed.stdout.strip())


def _probe_video_geometry(ffprobe: Path, source: Path) -> tuple[int, int] | None:
    """Return the first video stream's encoded size, or None when unavailable.

    Assembly may combine H3/character-swap renders with untouched V1 relay
    windows.  Those producers do not necessarily use the same canvas size or
    sample-aspect-ratio, while FFmpeg's concat filter requires an identical
    video contract for every input.  Geometry probing is deliberately
    best-effort so command construction remains usable in dry-run tests.
    """

    try:
        completed = subprocess.run(
            [
                str(ffprobe), "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "json",
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode:
            return None
        streams = (json.loads(completed.stdout or "{}").get("streams") or [])
        if not streams:
            return None
        width = int(streams[0].get("width") or 0)
        height = int(streams[0].get("height") or 0)
        if width <= 0 or height <= 0:
            return None
        return width, height
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ):
        return None


def _identity_region_bbox(value: object) -> list[float]:
    """Return the face/upper-body part of a normalized actor rectangle.

    Relay is meant to preserve the surrounding plate, so comparing the whole
    frame would reward a failed swap.  The upper-centre portion concentrates
    the audit on identity-bearing pixels while remaining usable for cropped
    heads and half-body source performers.
    """

    try:
        left, top, right, bottom = [float(item) for item in value][:4]
    except (TypeError, ValueError, OverflowError):
        return []
    left, top = max(0.0, left), max(0.0, top)
    right, bottom = min(1.0, right), min(1.0, bottom)
    if right - left < 0.03 or bottom - top < 0.03:
        return []
    width, height = right - left, bottom - top
    return [
        left + width * 0.24,
        top + height * 0.02,
        right - width * 0.24,
        top + height * 0.46,
    ]


def _mouth_region_bbox(value: object) -> list[float]:
    """Backwards-facing alias for :func:`character_swap_engine.mouth_region_bbox`.

    Round 37i proved the audit has to be able to name the same strip of face the
    Studio's plate builder touched, so the registration moved into the shared
    engine module.  The alias stays because the probes and the existing tests
    read these names off this module.
    """

    return mouth_region_bbox(value)


def _mouth_band_registration(value: object) -> tuple[list[float], str]:
    """Alias for :func:`character_swap_engine.mouth_band_registration`."""

    return mouth_band_registration(value)


def _cavity_opening_fraction(
    frame: bytes,
    size: int,
    *,
    dark_margin: int = 42,
    row_dark_share: float = 0.34,
) -> float | None:
    """Return the height of the darkest horizontal cavity in one gray ROI.

    Round 37d closed the pixel-motion route for good: on this cartoon look the
    forehead band scored *higher* adjacent-frame change than the real mouth band
    (0.26-0.29 against 0.22-0.32), and the per-row motion profile on the result
    side was flat, with no mouth peak at all.  Relay re-draws the whole shot
    every frame, so *no* difference threshold — absolute or relative — can tell
    lip-sync from boiling.  What still separates them is shape: an articulating
    mouth grows a dark oral cavity that appears and disappears, while boiling
    only jitters texture.  The longest run of rows that are mostly darker than
    the band's own median is that cavity's height, normalized to the band.
    """

    if size < 8 or len(frame) < size * size:
        return None
    pixels = frame[: size * size]
    reference = sorted(pixels)[len(pixels) // 2]
    threshold = max(0, int(reference) - int(dark_margin))
    needed = max(2, int(size * float(row_dark_share)))
    longest = 0
    run = 0
    for row_start in range(0, len(pixels), size):
        row = pixels[row_start: row_start + size]
        dark = sum(1 for value in row if value <= threshold)
        if dark >= needed:
            run += 1
            if run > longest:
                longest = run
        else:
            run = 0
    return longest / float(size)


def _cavity_opening_profile(frames: list[bytes], size: int) -> dict:
    """Median and swing of the cavity opening across one ROI series.

    The swing is the decision.  A Silent Listener whose mouth is shut, and one
    who is drawn with a permanent grin, both have a stable cavity height: the
    first is correct, the second is a *different* failure (wrong expression)
    that must not be spent on a fresh seed by a mouth-motion gate.  Only a
    cavity that opens and closes over the clip is articulation.
    """

    readings = [
        opening
        for opening in (_cavity_opening_fraction(frame, size) for frame in frames)
        if opening is not None
    ]
    if len(readings) < 2:
        return {"available": False, "median": 0.0, "swing": 0.0, "samples": len(readings)}
    return {
        "available": True,
        "median": round(_median(readings), 6),
        "swing": round(max(readings) - min(readings), 6),
        "samples": len(readings),
    }


def _silent_mouth_geometry_settings() -> tuple[str, float, float]:
    """``(mode, swing margin, absolute swing floor)`` for the geometry gate.

    ``H3_CHARACTER_SWAP_MOUTH_GEOMETRY`` picks the regime: ``advisory`` (default)
    records the registered mouth geometry while the pixel-motion gate still
    decides, ``on`` lets the geometry decide, ``off`` skips the arithmetic and
    behaves exactly as before.  The margin and floor are exposed so a threshold
    can be re-tuned against a take without editing source; only process env is
    read, never ``design_ai.env``.

    Round 37f moved the default from ``on`` back to ``advisory`` on measurement.
    Sampled densely at 24 fps with a five-frame smoothing window — the fix for
    the boil that had made earlier probes unreadable — the cavity height of the
    policy 71/72/73 takes read 0.10-0.60 on *every* row band of the result,
    including the hair and hatband rows, and the noisiest non-mouth row was
    usually within 0.05 of the true mouth row (segment 0 of the policy 73 take:
    mouth 0.615 against noise 0.437, a ratio of 1.41 against the 1.60 margin).
    The same takes show a source plate whose cavity stays shut (0.000-0.100), so
    the geometry does measure something on the plate — it simply cannot separate
    an oral cavity from redraw boil once Relay has re-drawn the head.  Under
    ``on`` that means every articulated take passes, which silently disables the
    audit and stops spending fresh seeds.  The numbers stay in the manifest as
    evidence, and ``on`` remains available for a controlled A/B.
    """

    mode = os.environ.get(
        "H3_CHARACTER_SWAP_MOUTH_GEOMETRY", "advisory"
    ).strip().casefold() or "advisory"
    if mode not in {"on", "advisory", "off"}:
        mode = "advisory"

    def _positive(name: str, default: float) -> float:
        try:
            value = float(os.environ.get(name, "") or default)
        except (TypeError, ValueError):
            return default
        return value if value > 0.0 else default

    return (
        mode,
        _positive("H3_CHARACTER_SWAP_MOUTH_GEOMETRY_MARGIN", 1.60),
        _positive("H3_CHARACTER_SWAP_MOUTH_GEOMETRY_FLOOR", 0.020),
    )


def _silent_plate_gate_settings() -> tuple[str, float, float]:
    """``(mode, gain, floor)`` for the plate-relative silent mouth gate.

    Round 37i found the audit measuring the wrong reference.  The QC compares
    the take with ``identity_audit.source_video_path``, which is the raw V1
    clip — but Relay is never handed that clip on a suppressed close-up pass.
    It is handed the identity-suppressed plate, and on the policy-74 take that
    plate's registered mouth band moved 0.056-0.073 while V1 moved 0.108-0.121.
    Both numbers are "the source talks", and they are not the same contract:
    the model was conditioned on the quieter one.  Measuring the plate next to
    the take makes the difference visible instead of inferred, and
    ``source_speech_conflict`` names the case where the verdict came from a
    performance the model never saw.

    ``H3_CHARACTER_SWAP_SILENT_PLATE_GATE`` picks the regime: ``advisory``
    (default) records the plate-relative verdict without spending a fresh seed,
    ``on`` lets it decide, ``off`` skips the sampling entirely.  Advisory ships
    first because the plate is only measurable on a suppressed pass, and this
    round changes both the plate and the ruler in one shot: the numbers need to
    be graded on real takes before they can start costing retries.
    """

    mode = os.environ.get(
        "H3_CHARACTER_SWAP_SILENT_PLATE_GATE", "advisory"
    ).strip().casefold() or "advisory"
    if mode not in {"on", "advisory", "off"}:
        mode = "advisory"

    def _positive(name: str, default: float) -> float:
        try:
            value = float(os.environ.get(name, "") or default)
        except (TypeError, ValueError):
            return default
        return value if value > 0.0 else default

    return (
        mode,
        _positive("H3_CHARACTER_SWAP_SILENT_PLATE_MOTION_GAIN", 1.5),
        _positive("H3_CHARACTER_SWAP_SILENT_PLATE_MOTION_FLOOR", 0.012),
    )


def _silent_mouth_hard_gate_tolerance() -> float:
    """How far past its own limit a Silent Listener take may go and stay clean.

    The hard gate is right about the takes the director rejected — the S3/S5
    lip-sync failures measured 15 % and 53 % over the governing limit — and it
    is wrong about a cartoon drawn mid-laugh whose mouth band boils.  The
    1.0 MP policy-82 take (seed 923011207) recorded ``articulation_excess``
    0.0536 against a limit of 0.2256, i.e. 23.8 % over, while the frame read
    as a closed-mouth grin and the pixel-motion gate itself returned
    ``motion_violated = false``.  Spending fresh seeds on that take is what the
    tolerance below stops.

    ``H3_CHARACTER_SWAP_SILENT_HARD_GATE_TOLERANCE`` is the fraction of the
    governing limit that may be overrun before the take is called a hard
    failure.  It only ever *relaxes* the gate: an overrunning row is downgraded
    to advisory, never a clean row promoted.  One exception stays hard, because
    it is an independent confirmation rather than the same arithmetic — the
    registered mouth-cavity geometry gate.  ``0`` restores the pre-tolerance
    behaviour exactly.
    """

    try:
        value = float(
            os.environ.get(
                "H3_CHARACTER_SWAP_SILENT_HARD_GATE_TOLERANCE", ""
            )
            or 0.12
        )
    except (TypeError, ValueError):
        return 0.12
    return min(max(value, 0.0), 1.0)


def _silent_plate_verdict_scope(plate_path: object) -> str:
    """Name the reference a silent verdict was actually measured against.

    Every row said ``relative_to_suppressed_plate`` since policy 74, and since
    policy 82 the plate is usually the *clean* V1 clip rather than a blurred or
    desaturated one — the manifest for seed 923011207 says suppressed while the
    plate file it names is ``v1_relay_8df6283643bf459a39b2``.  A grader reading
    that field draws the wrong conclusion about which pixels were compared, so
    the wording now follows the plate that was actually opened.
    """

    text = str(plate_path or "").casefold()
    if "identity_suppressed" in text:
        return "relative_to_suppressed_plate"
    return "relative_to_clean_source_plate"


def _upper_face_region_bbox(value: object) -> list[float]:
    """Return the eye/brow band of one actor box as a mouth-motion reference.

    A Silent Listener is allowed to blink and to have a prop pass in front of
    the face; it is not allowed to articulate.  Sampling the band above the
    mouth gives the audit something honest to compare against: when the upper
    face is as busy as the lower face, whatever moved is the plate or a prop,
    not lip-sync.  Measured on the black-shirt S2 take, an orange juggling ball
    crossed the mouth rectangle in about a quarter of the sampled frames, and
    the absolute motion cap alone called that lip-sync.
    """

    try:
        left, top, right, bottom = [float(item) for item in value][:4]
    except (TypeError, ValueError, OverflowError):
        return []
    left, top = max(0.0, left), max(0.0, top)
    right, bottom = min(1.0, right), min(1.0, bottom)
    if right - left < 0.03 or bottom - top < 0.03:
        return []
    width, height = right - left, bottom - top
    return [
        left + width * 0.28,
        top + height * 0.02,
        right - width * 0.28,
        top + height * 0.24,
    ]


def temporal_frame_motion(frames: list[bytes]) -> float:
    """Mean normalized adjacent-frame change for an equally-sized ROI series."""

    if len(frames) < 2:
        return 0.0
    changes: list[float] = []
    for previous, current in zip(frames, frames[1:]):
        count = min(len(previous), len(current))
        if count <= 0:
            continue
        changes.append(
            sum(abs(left - right) for left, right in zip(previous[:count], current[:count]))
            / (count * 255.0)
        )
    return sum(changes) / len(changes) if changes else 0.0


def robust_temporal_frame_motion(frames: list[bytes]) -> float:
    """Median adjacent-frame change, so one transient event cannot set the tone.

    Lip-sync is motion in *most* frames.  A ball, a hand or a single cut is
    motion in a *few*, and the mean cannot tell them apart: the black-shirt S2
    Silent Listener take scored 0.253 against a 0.121 cap because the prop
    crossed the ROI six times in 24 samples, which spent three fresh seeds on a
    mouth that never moved.  The median is the articulation measure; the mean
    is still recorded next to it for review.
    """

    if len(frames) < 2:
        return 0.0
    changes: list[float] = []
    for previous, current in zip(frames, frames[1:]):
        count = min(len(previous), len(current))
        if count <= 0:
            continue
        changes.append(
            sum(abs(left - right) for left, right in zip(previous[:count], current[:count]))
            / (count * 255.0)
        )
    return _median(changes) if changes else 0.0


def _probe_frame_interval(ffprobe: Path, source: Path) -> float:
    """Seconds between decoded frames, or 0.0 when the stream cannot be read.

    Strict temporal coverage samples at ratios of the container duration.  On a
    sub-second clip the highest ratio lands after the last decodable frame, and
    ffmpeg's input seek answers ``rc=0`` with an empty pipe instead of failing,
    which aborted a whole Character Swap take (2026-10-26, seed 97000864: a
    four-frame source with stream duration 0.166667s).  The real frame interval
    is what makes a safe sampling ceiling computable.
    """

    try:
        completed = subprocess.run(
            [
                str(ffprobe), "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=avg_frame_rate",
                "-of", "default=noprint_wrappers=1:nokey=1", str(source),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode:
            return 0.0
        numerator, _, denominator = completed.stdout.strip().partition("/")
        fps = float(numerator) / float(denominator) if denominator else 0.0
        return 1.0 / fps if fps > 0.0 else 0.0
    except (OSError, TypeError, ValueError, ZeroDivisionError, subprocess.SubprocessError):
        return 0.0


def _clamped_timestamps(
    duration: float,
    ratios: tuple[float, ...],
    frame_interval: float,
) -> list[float]:
    """Map sample ratios onto timestamps that are guaranteed decodable.

    H3 takes and source plates are frequently a handful of frames long, so the
    final frame is excluded from the sampling ceiling: an input seek onto the
    exact last PTS is not reliably answered by every ffmpeg build.  When the
    frame interval cannot be probed the timestamps fall back to the raw ratios,
    which is the pre-fix behaviour.
    """

    ceiling = max(0.0, float(duration))
    if frame_interval > 0.0:
        ceiling = max(0.0, ceiling - (2.0 * float(frame_interval)))
    stamps: list[float] = []
    for ratio in ratios:
        stamps.append(max(0.0, min(float(duration) * float(ratio), ceiling)))
    return stamps


def _identity_sample_ladder(time_seconds: float) -> tuple[float, ...]:
    """Seek offsets to try for one probe frame, newest first, ``0.0`` last."""

    stamp = max(0.0, float(time_seconds))
    ladder = [stamp]
    for factor in (0.9, 0.75, 0.5):
        candidate = stamp * factor
        if candidate not in ladder:
            ladder.append(candidate)
    if stamp > 0.0:
        ladder.append(0.0)
    return tuple(ladder)


def _decode_probe_frame(
    ffmpeg: Path,
    source: Path,
    time_seconds: float,
    video_filter: str,
    pixel_format: str,
    expected_bytes: int,
) -> tuple[bytes | None, str]:
    """Decode one small probe frame: ``(bytes, "")`` or ``(None, stderr)``.

    A stamp ladder and two seek variants are attempted so a sample at or past
    the final frame, and the single-frame image case where an input-side seek
    lands past the only frame, both self-heal instead of raising in the middle
    of an audit that already paid for a full generation.
    """

    last_detail = ""
    for stamp in _identity_sample_ladder(time_seconds):
        seek = f"{stamp:.6f}"
        for command in (
            [
                str(ffmpeg), "-hide_banner", "-loglevel", "error",
                "-ss", seek, "-i", str(source),
                "-frames:v", "1", "-vf", video_filter,
                "-f", "rawvideo", "-pix_fmt", pixel_format, "pipe:1",
            ],
            # Some ffmpeg builds drop the only frame of a single-frame image
            # sequence when an input-side ``-ss`` is used because the seek
            # lands past that one frame; an output-side seek decodes it.
            [
                str(ffmpeg), "-hide_banner", "-loglevel", "error",
                "-i", str(source), "-ss", seek,
                "-frames:v", "1", "-vf", video_filter,
                "-f", "rawvideo", "-pix_fmt", pixel_format, "pipe:1",
            ],
        ):
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=90,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if not completed.returncode and len(completed.stdout) >= expected_bytes:
                return completed.stdout[:expected_bytes], ""
            detail = completed.stderr.decode("utf-8", errors="replace")[-500:]
            last_detail = (detail or f"rc={completed.returncode}").strip()
    return None, last_detail or "no frame decoded from any seek variant"


def _extract_identity_gray_frame(
    ffmpeg: Path,
    source: Path,
    time_seconds: float,
    bbox: list[float],
    *,
    size: int = 96,
) -> bytes:
    left, top, right, bottom = bbox
    width, height = right - left, bottom - top
    video_filter = (
        f"crop=iw*{width:.8f}:ih*{height:.8f}:"
        f"iw*{left:.8f}:ih*{top:.8f},"
        f"scale={size}:{size}:flags=bilinear,format=gray"
    )
    decoded, detail = _decode_probe_frame(
        ffmpeg, source, time_seconds, video_filter, "gray", size * size
    )
    if decoded is None:
        raise RuntimeError("Could not sample Character Swap identity region: " + detail)
    return decoded


def _extract_identity_rgb_frame(
    ffmpeg: Path,
    source: Path,
    time_seconds: float,
    bbox: list[float] | None = None,
    *,
    size: int = 64,
) -> bytes:
    """Decode a small colour crop for target-P-picture candidate ranking."""

    filters: list[str] = []
    if bbox:
        left, top, right, bottom = bbox
        width, height = right - left, bottom - top
        filters.append(
            f"crop=iw*{width:.8f}:ih*{height:.8f}:"
            f"iw*{left:.8f}:ih*{top:.8f}"
        )
    # Centre crop, rather than letterbox, prevents a transparent/solid Picture
    # background from overwhelming the actual character colour distribution.
    filters.extend([
        f"scale={size}:{size}:force_original_aspect_ratio=increase:flags=bilinear",
        f"crop={size}:{size}",
        "format=rgb24",
    ])
    # The shared decoder keeps the fast input-side seek first and only then
    # retries with an output-side seek, which is what makes single-frame JPG
    # references keep scoring instead of silently zeroing their audit.
    decoded, detail = _decode_probe_frame(
        ffmpeg,
        source,
        time_seconds,
        ",".join(filters),
        "rgb24",
        size * size * 3,
    )
    if decoded is None:
        raise RuntimeError("Could not sample target identity colour region: " + detail)
    return decoded


def target_reference_frame_similarity(reference: bytes, result: bytes) -> float:
    """Return a conservative 0..1 likeness cue for choosing Relay retries.

    This is deliberately not face recognition. Character Swap often maps a
    cartoon/full-body P Picture into a live plate, so a colour-distribution cue
    is more stable than raw pixel similarity. It is used only to rank completed
    retries; existing V1-retention and plate-continuity QC remain authoritative.
    """

    count = min(len(reference), len(result)) // 3
    if count <= 0:
        raise ValueError("Target-reference audit frame is empty.")
    bin_count = 16
    reference_hist = [[0] * bin_count for _ in range(3)]
    result_hist = [[0] * bin_count for _ in range(3)]
    reference_luma: list[float] = []
    result_luma: list[float] = []
    for pixel_index in range(count):
        offset = pixel_index * 3
        reference_rgb = reference[offset:offset + 3]
        result_rgb = result[offset:offset + 3]
        for channel in range(3):
            reference_hist[channel][min(bin_count - 1, reference_rgb[channel] * bin_count // 256)] += 1
            result_hist[channel][min(bin_count - 1, result_rgb[channel] * bin_count // 256)] += 1
        reference_luma.append(
            (0.2126 * reference_rgb[0] + 0.7152 * reference_rgb[1] + 0.0722 * reference_rgb[2]) / 255.0
        )
        result_luma.append(
            (0.2126 * result_rgb[0] + 0.7152 * result_rgb[1] + 0.0722 * result_rgb[2]) / 255.0
        )
    histogram_intersection = sum(
        sum(min(left, right) for left, right in zip(reference_hist[channel], result_hist[channel])) / count
        for channel in range(3)
    ) / 3.0
    reference_mean = sum(reference_luma) / count
    result_mean = sum(result_luma) / count
    reference_std = math.sqrt(sum((value - reference_mean) ** 2 for value in reference_luma) / count)
    result_std = math.sqrt(sum((value - result_mean) ** 2 for value in result_luma) / count)
    mean_similarity = max(0.0, 1.0 - abs(reference_mean - result_mean))
    contrast_similarity = max(0.0, 1.0 - abs(reference_std - result_std) * 2.0)
    return max(
        0.0,
        min(
            1.0,
            histogram_intersection * 0.78
            + mean_similarity * 0.12
            + contrast_similarity * 0.10,
        ),
    )


def _wardrobe_audit_bboxes(value: object) -> list[list[float]]:
    """Return usable body rectangles for the whole-body wardrobe gate.

    The Studio sends the same rectangle it blurred the plate on, verbatim: it is
    already torso-to-feet, so it must not go through ``_identity_region_bbox``,
    which deliberately keeps only the upper-centre 46 % of a box and would turn a
    costume back into a chest sliver.  Rectangles narrower than a shoulder or
    shorter than a torso are skipped because they would measure background and
    call it a wardrobe.
    """

    boxes: list[list[float]] = []
    for row in value or []:
        try:
            left, top, right, bottom = [float(item) for item in row][:4]
        except (TypeError, ValueError, OverflowError):
            continue
        left, top = max(0.0, left), max(0.0, top)
        right, bottom = min(1.0, right), min(1.0, bottom)
        if right - left < 0.08 or bottom - top < 0.18:
            continue
        boxes.append([left, top, right, bottom])
    return boxes[:2]


def _wardrobe_region_boxes(
    body_bbox: list[float],
) -> list[tuple[str, list[float]]]:
    """Split one garment rectangle into the regions that must each move.

    Round 36 read the frames the single-median ruler was built from and found
    the shape the director had already named: the legs had moved to Picture 1's
    yellow checkered leg warmers while the chest still wore the cosplayer's
    black vest with gold trim, and the median of those two still cleared the
    floor.  A rectangle that only changed below the waist is a head-and-legs
    swap, not a whole-body swap, so the ruler now binds on the half that did
    *not* move.  Boxes shorter than two torso heights stay whole:
    ``_wardrobe_audit_bboxes`` already refuses anything below one torso height,
    and half of such a box would measure background and report it as a costume.
    """

    left, top, right, bottom = body_bbox
    middle = top + (bottom - top) * 0.5
    if (
        bottom - top >= 0.36
        and middle - top >= 0.18
        and bottom - middle >= 0.18
    ):
        return [
            ("upper", [left, top, right, middle]),
            ("lower", [left, middle, right, bottom]),
        ]
    return [("whole", [left, top, right, bottom])]


def _wardrobe_floor_policy_settings() -> tuple[str, float, float]:
    """``(policy, relative gain, absolute sanity floor)`` for the wardrobe gate.

    The floor is an absolute similarity gain, and Picture 1 in this project is a
    dark cartoon standing in front of a dark plate.  A dark garment already sits
    close to the plate's own histogram, so the *achievable* absolute shift is
    capped: on seed 923011207 the lower region moved 0.1302 against a 0.12 floor
    and the headroom is gone — the next dark-clothing Shot misses a gate that is
    describing a swap that actually happened.

    ``H3_CHARACTER_SWAP_WARDROBE_FLOOR_POLICY=relative`` (the default) therefore
    passes a region when *either* rule holds: the absolute floor, or a gain of
    ``H3_CHARACTER_SWAP_WARDROBE_RELATIVE_GAIN`` (default 10 %) over what the
    source region already scored against Picture 1.  The relative rule is an
    OR, never an AND, so it can only ever relax the gate; ``absolute`` restores
    the pre-policy-83 behaviour exactly.  The sanity floor
    (``H3_CHARACTER_SWAP_WARDROBE_SANITY_FLOOR``, default 0.03) keeps a take
    that merely did not move from passing on a noisy 10 % blip.
    """

    policy = os.environ.get(
        "H3_CHARACTER_SWAP_WARDROBE_FLOOR_POLICY", "relative"
    ).strip().casefold() or "relative"
    if policy not in {"relative", "absolute"}:
        policy = "relative"

    def _non_negative(name: str, default: float) -> float:
        try:
            value = float(os.environ.get(name, "") or default)
        except (TypeError, ValueError):
            return default
        return value if value >= 0.0 else default

    return (
        policy,
        _non_negative("H3_CHARACTER_SWAP_WARDROBE_RELATIVE_GAIN", 0.10),
        _non_negative("H3_CHARACTER_SWAP_WARDROBE_SANITY_FLOOR", 0.03),
    )


def _wardrobe_region_passed(
    region_shift: float,
    take_median: float,
    source_median: float,
    *,
    absolute_floor: float,
    policy: str,
    relative_gain: float,
    sanity_floor: float,
) -> tuple[bool, float, bool]:
    """Return ``(passed, required_shift_relative, relative_rule_satisfied)``.

    One implementation for both the per-region rows and the Shot-level verdict,
    so a manifest can never claim a region passed on a rule the aggregate did
    not apply.  The relative requirement scales with how much the source region
    already looked like Picture 1: 10 % of an already-similar dark garment is a
    much bigger absolute ask than 10 % of a bright costume, which is exactly the
    behaviour an absolute floor cannot express.
    """

    absolute_ok = bool(
        absolute_floor > 0.0 and region_shift >= absolute_floor
    )
    required_relative = max(sanity_floor, source_median * relative_gain)
    relative_ok = bool(
        policy == "relative"
        and region_shift >= required_relative
        and take_median >= source_median * (1.0 + relative_gain)
    )
    if policy == "absolute":
        return (absolute_ok, required_relative, False)
    return (absolute_ok or relative_ok, required_relative, relative_ok)


def _candidate_target_likeness(candidate: dict) -> float:
    """Target-P likeness discounted by residual V1 identity retention.

    The target-reference metric is a colour-distribution cue, not face
    recognition: a take can resemble Picture 1's wardrobe colours while the
    head still belongs to the original actor (the S7 failure mode).  When the
    audit recorded per-role source similarity at or above the no-op threshold,
    subtract a discount that grows with how strongly the source face survived,
    so a genuinely redrawn take wins over a colour-matched face layer.
    Candidates without role data keep their raw score, preserving legacy
    behaviour for older jobs.

    A recorded wardrobe shift is added as a bonus.  When two takes both failed QC
    and both resembled Picture 1's palette, the retry budget used to pick the one
    that differed most from V1; now the one whose *body* actually moved towards
    the reference wins, which is the difference between a whole-character swap and
    a face layer.  The bonus is capped at the shift a verified whole-body swap
    measured, so it can reorder candidates without outvoting identity retention.

    Policy 80: the bonus reads the better of two windows -- the 0.22 / 0.50 / 0.78
    median that also gates QC, and a 0.78 / 0.86 / 0.94 tail -- because H3 sometimes
    finishes putting on Picture 1's costume only after the median's last sample.  On
    seed 923010907 that is what pushed the director's only accepted take into second
    place behind a take that then lost the costume.

    A Silent Listener take whose mouth kept articulating is charged back.  The
    reference picture in this project smiles with its teeth showing, and likeness
    reads a colour histogram, so an open mouth is systematically rewarded as
    "resembles Picture 1" -- measured on seed 923010507, the widest-mouthed take
    won seg0 on a 0.066 similarity lead and seg2 on a 0.004 lead while its
    articulation excess was double the loser's.  The charge uses only the
    sanctioned pixel-motion excess the silent mouth audit already recorded, which
    is zero for a compliant take, so silence earns nothing; it only stops
    non-silence from being bought with colour.
    """

    likeness = float(candidate.get("target_reference_similarity", -1.0))
    # Either window may carry the signal, so the bonus takes the best measurement
    # the audit has.  A candidate from an older manifest only has the median and
    # ranks exactly as it did under policy 79.
    measured_shifts: list[float] = []
    for key in ("wardrobe_shift", "wardrobe_shift_late"):
        value = candidate.get(key)
        if value is None:
            continue
        try:
            measured_shifts.append(float(value))
        except (TypeError, ValueError, OverflowError):
            continue
    if measured_shifts:
        likeness += min(0.35, max(measured_shifts)) * 1.5
    result = candidate.get("result") or {}
    excess = _silent_articulation_excess(result)
    if excess is not None and excess > 0.0:
        likeness -= (
            min(SILENT_ARTICULATION_PENALTY_CAP, excess)
            * SILENT_ARTICULATION_PENALTY_WEIGHT
        )
    roles = [row for row in result.get("roles") or [] if isinstance(row, dict)]
    if not roles:
        return likeness
    retention_threshold = 0.75
    retention = max(float(row.get("similarity", 0.0)) for row in roles)
    if retention < retention_threshold:
        return likeness
    return likeness - (retention - retention_threshold) * 4.0 - 0.10


def _silent_articulation_excess(result: dict) -> float | None:
    """Worst mouth articulation the silent audit measured for one take.

    ``articulation_excess`` is how far the audited mouth band moved past the limit
    this Shot is allowed, so it reads 0.0 for a take that held its mouth still and
    grows with lip-sync.  The return is ``None`` -- not ``0.0`` -- when the take was
    never audited as silent, which is every speaker Shot and every older job: those
    candidates keep the ranking they had before, and a missing measurement is never
    read as a free pass on a Shot that *was* audited.
    """

    audit = result.get("silent_mouth_audit")
    if not isinstance(audit, dict) or not audit.get("checked"):
        return None
    worst: float | None = None
    for row in audit.get("rows") or []:
        if not isinstance(row, dict):
            continue
        value = row.get("articulation_excess")
        if value is None:
            continue
        try:
            measured = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if measured != measured:  # NaN
            continue
        worst = measured if worst is None else max(worst, measured)
    return worst


# Round 108 -- which take to keep when a non-human target is swapped in.
#
# The ranking below was built for human performers: it trusts ``target_reference_similarity``
# (a colour-histogram likeness to Picture 1) and discounts a take whose identity region still
# matches V1.  On neca_6's Gundam and Godzilla it is demonstrably blind.  The 11:50 take the
# director accepted and the 14:24 take he rejected -- byte-identical instructions, different
# seeds -- were scored 0.3594/0.3250 on the roll he liked and 0.4229/**0.4675** on the roll he
# rejected: the metric puts the rejected Godzilla roll above the accepted one, so a retry loop
# driven by it throws the better take away.
#
# Until the composite-stage target-shape series (measured with the real mattes, which only exist
# after the retry loop has spent its rolls) can be brought into this decision, the honest choice
# for a non-human target was the first take.  Round 110 brings that ruler into the decision.
# neca_6's 18:51 run is the proof: R2 rolled twice, the audit kept roll 1 (likeness 0.6292 against
# 0.3577) and the Shot was rejected again.  Tracking both rolls with the Studio's own mask graph
# and grading them with the round 108 series gives roll 1 median 0.5443 / p10 0.3714 / 51.7 % of
# seconds off-model and roll 2 median 0.6305 / p10 0.5775 / 5.2 %: roll 2 passes the rule, roll 1
# does not, and the frames agree -- roll 1 loses Godzilla between 8.5 s and 10.5 s while roll 2
# carries it to the end.  ``target_reference_similarity`` measured 0.429023 against 0.429596, a
# tie inside the noise round 108 measured, so it cannot decide either.
#
# So a non-human pass now tracks every roll it generated and keeps the roll whose silhouette
# actually resembles the Picture (about 90 s of the director's own GPU per extra roll -- measured
# at 88 s end to end on this very Shot -- and only once a pass has really re-rolled).  ``first``
# is the fallback whenever a roll cannot be measured, and ``first`` in
# ``H3_CHARACTER_SWAP_NONHUMAN_RANKING`` restores round 108's keep-the-first rule; ``audit``
# restores the human ranking.
CHARACTER_SWAP_NONHUMAN_RANKING_ENV = "H3_CHARACTER_SWAP_NONHUMAN_RANKING"
CHARACTER_SWAP_NONHUMAN_RANKING_MODES = ("first", "audit", "shape")
CHARACTER_SWAP_DEFAULT_NONHUMAN_RANKING = "shape"
# A SAM slot that only saw part of the Clip is not a contestant.  The 18:51 roll 1 had a fragment
# slot scoring p10 0.5807 over 20 of 58 samples; counted as if it were the whole roll it would
# have hidden the fact that that roll's full-length slots scored 0.3143 and 0.3511.
CHARACTER_SWAP_NONHUMAN_SHAPE_MIN_SAMPLE_SHARE = 0.5
# Round 111: how much better a later roll must be before the Studio gives up the take it generated
# first.  The 20:33 rolls were 22.4 points apart on off-model seconds (19.0 % against 41.4 %) and the
# 18:51 pair 37.9 points apart (43.1 % against 5.2 %); the ruler repeats to within a point or two on
# the same roll, so 5 points absolute is far outside what measurement noise can produce and still
# small enough never to keep a roll that is visibly worse for a third of the Shot.
CHARACTER_SWAP_NONHUMAN_SHAPE_FLIP_MARGIN = 0.05


def character_swap_nonhuman_ranking_mode() -> str:
    """Which take to keep when the swap targets a non-human performer."""

    raw = os.environ.get(CHARACTER_SWAP_NONHUMAN_RANKING_ENV, "").strip().lower()
    return raw if raw in CHARACTER_SWAP_NONHUMAN_RANKING_MODES \
        else CHARACTER_SWAP_DEFAULT_NONHUMAN_RANKING


def _character_swap_candidate_shape_reading(candidate: dict) -> tuple[bool, float, float, int]:
    """Read one roll's target-shape series as ``(measured, p10, weak share, samples)``.

    The numbers ride either on the candidate itself or inside the copy of the audit it carries,
    which is where round 110's per-roll measurement puts them.  A roll that was never measured
    reads as ``(-1.0, 1.0, 0)``, so it can never outrank a roll that was.
    """

    sources: list[dict] = [candidate]
    result = candidate.get("result")
    if isinstance(result, dict):
        sources.append(result)
    for source in sources:
        raw = source.get("target_shape_iou_p10")
        if raw is None:
            continue
        try:
            p10 = float(raw)
        except (TypeError, ValueError):
            continue
        try:
            weak_share = float(source.get("target_shape_weak_share"))
        except (TypeError, ValueError):
            weak_share = 1.0
        try:
            samples = int(source.get("target_shape_samples") or 0)
        except (TypeError, ValueError):
            samples = 0
        return True, p10, weak_share, samples
    return False, -1.0, 1.0, 0


def rank_character_swap_candidates_by_target_shape(candidates: list[dict]) -> dict | None:
    """Keep the roll whose silhouette best matches the target Picture.

    Returns ``None`` when no roll carries a usable measurement, which sends the caller back to
    the keep-the-first fallback rather than to the colour histogram round 108 proved blind on
    Gundam and Godzilla figures.  A roll that passes the round 108 rule (p10 at least 0.40 with no
    more than 25 % of its seconds off-model) beats one that does not; otherwise the roll that is
    off-model for *fewer seconds* wins, with p10 only as the tiebreak, and the first roll is kept
    unless the challenger is clearly better (``CHARACTER_SWAP_NONHUMAN_SHAPE_FLIP_MARGIN``).
    """

    readings = {
        int(row.get("attempt", 0) or 0): _character_swap_candidate_shape_reading(row)
        for row in candidates
    }
    longest = max((reading[3] for reading in readings.values()), default=0)
    sample_floor = max(
        2, int(longest * CHARACTER_SWAP_NONHUMAN_SHAPE_MIN_SAMPLE_SHARE + 0.999))
    eligible = {
        attempt: reading
        for attempt, reading in readings.items()
        if reading[0] and reading[3] >= sample_floor
    }
    if not eligible:
        return None
    weak_share_floor = sam31_shape_weak_share_floor()

    def passes_rule(reading: tuple) -> bool:
        _measured, p10, weak_share, _samples = reading
        return p10 >= SAM31_SHAPE_P10_FLOOR and weak_share <= weak_share_floor

    def rank(candidate: dict) -> tuple:
        attempt = int(candidate.get("attempt", 0) or 0)
        reading = eligible.get(attempt)
        if not reading:
            return (2, 0.0, 0.0, attempt)
        _measured, p10, weak_share, _samples = reading
        # Round 111: the share of seconds off-model is the first criterion and p10 the tiebreak, not
        # the other way round as round 110 shipped.  Measured on the 20:33 take's own rolls: R1's roll
        # 1 sits at p10 0.2684 / 19.0 % off-model / median 0.7609 and its roll 2 at p10 0.3080 / 41.4 %
        # / 0.5817.  A p10-first key promotes roll 2, whose off-model seconds run through the middle of
        # the Shot (2.75-4.25 s, 4.75-6.5 s, 8-10.5 s) while roll 1's are the first and last quarter
        # second as the figure enters and leaves frame -- and the frames say exactly that: roll 1 carries
        # the Gundam through 4.5 s, roll 2 has lost it by 4.5 s.  18:51's R2 pair (p10 0.3143 / 43.1 %
        # against 0.5775 / 5.2 %) is ordered the same way by either key, so this only removes a flip.
        return (0 if passes_rule(reading) else 1, weak_share, -p10, attempt)

    best = min(candidates, key=rank)
    first = min(candidates, key=lambda row: int(row.get("attempt", 0) or 0))
    if best is not first:
        best_reading = eligible.get(int(best.get("attempt", 0) or 0))
        first_reading = eligible.get(int(first.get("attempt", 0) or 0))
        if best_reading and first_reading and not passes_rule(best_reading):
            # Both rolls are off-model somewhere; only give up the earlier take when the challenger is
            # better by a clear margin, the same discipline round 103 applies to a likeness flip.
            if (first_reading[2] - best_reading[2]) < CHARACTER_SWAP_NONHUMAN_SHAPE_FLIP_MARGIN:
                return first
    return best


def choose_character_swap_identity_candidate(
    candidates: list[dict], nonhuman_target: bool = False
) -> dict:
    """Choose a retry by target-P likeness, then by existing QC risk.

    Older jobs have no target-reference metric and retain the previous
    lowest-risk behaviour. New jobs must not pick a later take merely because
    it differs most from V1 when an earlier take actually resembles Picture 1.
    A high colour-histogram likeness alone is not enough: takes whose identity
    region still strongly matches the original V1 actor are discounted by
    _candidate_target_likeness so a drifted face layer cannot win on wardrobe
    colours alone, and a Silent Listener whose mouth kept articulating is
    discounted there too, because Picture 1's grin makes an open mouth look like
    the reference under a colour histogram.

    For a non-human target that likeness is the wrong instrument (round 108).  Round 110 replaced
    it with a measurement: the rolls are tracked and the roll whose silhouette resembles the
    target Picture wins (``rank_character_swap_candidates_by_target_shape``); when no roll could
    be measured the earliest attempt is kept.  Either way every roll's scores stay in the Manifest
    attempt table.
    """

    if not candidates:
        raise ValueError("No Character Swap identity candidates were supplied.")
    if nonhuman_target:
        nonhuman_ranking = character_swap_nonhuman_ranking_mode()
        if nonhuman_ranking == "shape":
            measured = rank_character_swap_candidates_by_target_shape(candidates)
            if measured is not None:
                return measured
            return min(candidates, key=lambda row: int(row.get("attempt", 0)))
        if nonhuman_ranking == "first":
            return min(candidates, key=lambda row: int(row.get("attempt", 0)))
    has_target_scores = any(
        row.get("target_reference_similarity") is not None for row in candidates
    )
    if has_target_scores:
        return min(
            candidates,
            key=lambda row: (
                -_candidate_target_likeness(row),
                float(row.get("score", 1.0)),
                int(row.get("attempt", 0)),
            ),
        )
    return min(
        candidates,
        key=lambda row: (float(row.get("score", 1.0)), int(row.get("attempt", 0))),
    )


def measure_character_swap_attempt_target_shapes(
    job: dict,
    segment: dict,
    candidates: list[dict],
) -> list[dict]:
    """Track every roll a non-human pass generated and grade it against the target Picture.

    The matte a roll needs for the round 108 ruler only exists after a tracking job, and until
    round 110 the Studio only ever asked for the mattes of the roll it had already chosen -- which
    is how neca_6's 18:51 run shipped the weaker of two rolls it could have measured at
    0.5443 / 0.3714 / 51.7 % against 0.6305 / 0.5775 / 5.2 %.  Every roll now gets the same mask
    graph the composite uses, and the choice is made from those numbers.

    This is deliberately not a gate: a tracking job that fails leaves that roll unmeasured, the
    ranking falls back to keeping the first roll, and the Segment still renders.  A diagnostic must
    never become a new way to fail a Shot.
    """

    if len(candidates) < 2:
        return []
    reference = ""
    audit_row: dict = {}
    for candidate in candidates:
        result = candidate.get("result")
        if isinstance(result, dict):
            audit_row = result
            reference = str(result.get("target_reference_path") or "")
            if reference:
                break
    passes = list(segment.get("character_swap_passes") or [])
    text_prompt = sam31_text_prompt(passes)
    # A human pass needs none of this: the ruler was validated on figures, and ``sam31_text_prompt``
    # always contains "person", so the prompt alone cannot tell the two cast kinds apart.  The
    # round 109 predicate reads the nouns the Studio recorded, which is the same question asked of
    # the auto-box cap.
    if not any(_sam31_pass_is_non_human(pass_row) for pass_row in passes):
        return []
    if not reference or not Path(reference).is_file() or not text_prompt:
        return []
    server = str(job.get("server") or "").rstrip("/")
    if not server:
        return []
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    ffprobe = Path(str(job["ffprobe"]))
    role_count = 1
    for pass_row in passes:
        role_count = max(role_count, len(pass_row.get("source_role_ids") or []) or 1)
    segment_token = str(segment.get("segment_id") or "segment")
    role = str(audit_row.get("source_role_id") or "role")
    try:
        pass_index = int(audit_row.get("pass_index") or 0) or 1
    except (TypeError, ValueError):
        pass_index = 1
    measurements: list[dict] = []
    clip_seconds = 0.0
    for candidate in candidates:
        attempt = int(candidate.get("attempt", 0) or 0)
        snapshot = Path(str(candidate.get("snapshot") or ""))
        if not snapshot.is_file():
            candidate["target_shape_status"] = "missing_snapshot"
            measurements.append({
                "attempt": attempt, "target_shape_status": "missing_snapshot"})
            continue
        upload_name = (
            f"h3samshape_{segment_token}_pass_{pass_index:02d}_{role}_attempt_{attempt:02d}.mp4"
        )
        try:
            uploaded = upload_file(server, snapshot, http_timeout, upload_name)
            remote_name = str((uploaded or {}).get("name") or upload_name)
            workflow, save_nodes = build_sam31_multiplex_mask_workflow(
                remote_name,
                object_count=min(12, max(4, role_count + 2)),
                output_token=(
                    f"{segment_token}_shaperank_pass_{pass_index:02d}_{role}"
                    f"_attempt_{attempt:02d}"
                ),
                text_prompt=text_prompt,
            )
            prompt_id, downloaded = _queue_auxiliary_outputs(
                job,
                segment,
                workflow,
                Path(str(segment["download_dir"]))
                / "sam31_attempt_shape_masks"
                / f"pass_{pass_index:02d}_{role}_attempt_{attempt:02d}",
                client_prefix="h3-sam31-attempt-shape-",
                progress_label=(
                    f"SAM3.1 roll-shape tracking pass {pass_index} · {role} · attempt {attempt}"
                ),
            )
            mask_rows, _skipped = _sam31_collect_instance_rows(job, downloaded, save_nodes)
            mask_videos = [
                str(row["path"])
                for row in sorted(mask_rows,
                                  key=lambda item: int(item.get("object_index") or 0))
                if Path(str(row.get("path") or "")).is_file()
            ]
            if clip_seconds <= 0.0:
                clip_seconds = float(_probe_duration(ffprobe, snapshot) or 0.0)
            reading = _character_swap_take_target_shape(
                job, mask_videos, reference, clip_seconds)
        except Exception as shape_error:  # noqa: BLE001 - a failed measurement is not a verdict
            # Round 111: the class name alone left two probe runs with "error:RuntimeError" and no way
            # to tell a wrong URL from a missing job key -- the message is what actually diagnosed it
            # (POST to /prompt/prompt, then KeyError 'segment_count').  Bounded to 160 characters
            # because this string rides along in the Manifest attempt table.
            candidate["target_shape_status"] = (
                f"error:{type(shape_error).__name__}: {str(shape_error)[:160]}"
            )
            measurements.append({
                "attempt": attempt,
                "target_shape_status": candidate["target_shape_status"],
            })
            continue
        readings = {
            key: value for key, value in reading.items()
            if str(key).startswith("target_shape")
        }
        candidate.update(readings)
        candidate["target_shape_prompt_id"] = prompt_id
        result = candidate.get("result")
        if isinstance(result, dict):
            result.update(readings)
            result["target_shape_prompt_id"] = prompt_id
        measurements.append({"attempt": attempt, "prompt_id": prompt_id, **readings})
    return measurements


# Round 86 item B — every identity-QC attempt stays on disk and in the Manifest.
#
# The retry loop already snapshotted each rejected take and then deleted the
# snapshots once it had picked a winner, so the take the director actually wanted
# vanished.  On the pink-dress Project the eye preferred attempt 1 while the
# colour histogram preferred attempt 3, and attempt 1 was only still recoverable
# from the ComfyUI server's own output folder.  Keeping the takes under
# ``<download_dir>/identity_attempts`` and naming them in the Manifest turns
# "the first one was the best" into a file copy instead of another eight to ten
# minutes of GPU.  ``H3_CHARACTER_SWAP_KEEP_ATTEMPTS=off`` restores the old
# delete-after-choice behaviour for a disk-tight machine; the Manifest table is
# written either way so the per-attempt numbers are never lost.
CHARACTER_SWAP_KEEP_ATTEMPTS_ENV = "H3_CHARACTER_SWAP_KEEP_ATTEMPTS"
CHARACTER_SWAP_ATTEMPT_DIRECTORY = "identity_attempts"


def character_swap_keep_attempts_enabled() -> bool:
    """Whether every identity-QC attempt is copied to disk instead of deleted."""

    raw = os.environ.get(CHARACTER_SWAP_KEEP_ATTEMPTS_ENV, "").strip().lower()
    if raw in {"0", "off", "false", "no", "none", "disable", "disabled"}:
        return False
    return True


def _character_swap_attempt_filename(snapshot: object, attempt: int) -> str:
    """The durable name for one kept attempt: our attempt number, their file name.

    Snapshots are named ``.identity_audit_attempt_<n>_<ComfyUI output name>``, so
    the prefix is dropped and the original output name (``pass_01_R1_00001_.mp4``)
    is kept behind our own attempt counter.  That is deliberate: the tail matches
    the file still sitting in the ComfyUI server's output folder, which is how a
    take gets cross-checked or re-downloaded without re-rendering.
    """

    name = Path(str(snapshot or "")).name
    if name.startswith(".identity_audit_attempt_"):
        trimmed = name[len(".identity_audit_attempt_"):]
        head, separator, tail = trimmed.partition("_")
        if separator and head.isdigit() and tail:
            name = tail
    return f"attempt_{int(attempt):02d}__{name or 'take.mp4'}"


def _attempt_shape_number(candidate: dict, result: dict, key: str) -> float | None:
    """One recorded target-shape number for one roll.

    Round 110 writes the measurement both onto the candidate and into the audit copy it carries,
    so either place may hold it; a roll that was never measured reads as ``None`` rather than 0.0,
    because 0.0 would look like a silhouette that scored zero.
    """

    for source in (candidate, result):
        value = (source or {}).get(key)
        if value is None:
            continue
        try:
            return round(float(value), 6)
        except (TypeError, ValueError):
            continue
    return None


def character_swap_identity_attempt_row(candidate: dict, selected_attempt: object = None) -> dict:
    """One comparable row for one retried take, shared by the log and the Manifest.

    Round 52 only ever recorded the audit that was *selected*, which is why a
    three-take retry looked like one number in the Manifest.  These rows are the
    per-attempt evidence the ranking actually consumed -- likeness to the target P
    Picture, wardrobe shift, silent-articulation excess, and the metric that
    decided -- so a disagreement with the ranking is gradeable without re-rendering.
    """

    result = candidate.get("result") or {}
    attempt = int(candidate.get("attempt", 0) or 0)
    similarity = candidate.get("target_reference_similarity")
    shift = candidate.get("wardrobe_shift")
    shift_late = candidate.get("wardrobe_shift_late")
    return {
        "attempt": attempt,
        "selected": bool(
            selected_attempt is not None and attempt == int(selected_attempt)
        ),
        "quality_risk_score": round(float(candidate.get("score", 1.0)), 6),
        "target_reference_similarity": (
            float(similarity) if similarity is not None else None
        ),
        "wardrobe_shift": float(shift) if shift is not None else None,
        "wardrobe_shift_late": float(shift_late) if shift_late is not None else None,
        "silent_articulation_excess": _silent_articulation_excess(result),
        "target_likeness_score": round(_candidate_target_likeness(candidate), 6),
        # Round 110: the ruler that now chooses a non-human roll, recorded for every roll --
        # including the rolls that could not be measured, because "no measurement" is itself the
        # record of why the choice fell back to the first roll.
        "target_shape_status": str(
            candidate.get("target_shape_status") or result.get("target_shape_status") or ""
        ),
        "target_shape_iou_median": _attempt_shape_number(
            candidate, result, "target_shape_iou_median"),
        "target_shape_iou_p10": _attempt_shape_number(
            candidate, result, "target_shape_iou_p10"),
        "target_shape_weak_share": _attempt_shape_number(
            candidate, result, "target_shape_weak_share"),
        "target_shape_samples": int(
            candidate.get("target_shape_samples") or result.get("target_shape_samples") or 0),
        "target_shape_prompt_id": str(
            candidate.get("target_shape_prompt_id")
            or result.get("target_shape_prompt_id") or ""
        ),
        "blocking": bool(result.get("blocking")),
        "head_layer_only": bool(result.get("head_layer_only")),
        "reason": str(result.get("reason", "") or ""),
        "prompt_id": str(candidate.get("prompt_id", "") or ""),
    }


def persist_character_swap_identity_attempts(
    download_dir: object,
    candidates: list[dict],
    selected_attempt: object = None,
) -> list[dict]:
    """Copy every snapshotted identity take somewhere durable and describe it.

    Returns one row per attempt with ``take_path`` set to the kept file, or an
    empty string when keeping is switched off or the copy failed.  A lost file is
    recorded as evidence with an error string rather than raised: nothing in the
    QC layer may fail a render that has already been paid for.
    """

    attempts_dir = Path(str(download_dir or "")) / CHARACTER_SWAP_ATTEMPT_DIRECTORY
    keep = character_swap_keep_attempts_enabled()
    rows: list[dict] = []
    for candidate in sorted(
        candidates, key=lambda row: int(row.get("attempt", 0) or 0)
    ):
        row = character_swap_identity_attempt_row(candidate, selected_attempt)
        snapshot = Path(str(candidate.get("snapshot", "") or ""))
        row["take_path"] = ""
        if not keep:
            rows.append(row)
            continue
        try:
            if snapshot.is_file():
                attempts_dir.mkdir(parents=True, exist_ok=True)
                destination = (
                    attempts_dir
                    / _character_swap_attempt_filename(snapshot, row["attempt"])
                )
                shutil.copy2(snapshot, destination)
                row["take_path"] = str(destination.resolve())
        except OSError as exc:
            row["take_copy_error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return rows


def identity_frame_metrics(source: bytes, result: bytes) -> dict[str, float]:
    """Measure whether an output identity region remained the V1 actor."""

    count = min(len(source), len(result))
    if count <= 1:
        raise ValueError("Identity audit frame is empty.")
    source_values = [float(value) / 255.0 for value in source[:count]]
    result_values = [float(value) / 255.0 for value in result[:count]]
    source_mean = sum(source_values) / count
    result_mean = sum(result_values) / count
    source_var = sum((value - source_mean) ** 2 for value in source_values) / count
    result_var = sum((value - result_mean) ** 2 for value in result_values) / count
    covariance = sum(
        (left - source_mean) * (right - result_mean)
        for left, right in zip(source_values, result_values)
    ) / count
    denominator = math.sqrt(max(0.0, source_var * result_var))
    correlation = covariance / denominator if denominator > 1e-12 else (
        1.0 if abs(source_mean - result_mean) <= 1e-6 else 0.0
    )
    c1, c2 = 0.01**2, 0.03**2
    similarity = (
        (2 * source_mean * result_mean + c1) * (2 * covariance + c2)
    ) / (
        (source_mean**2 + result_mean**2 + c1)
        * (source_var + result_var + c2)
    )
    mae = sum(
        abs(left - right) for left, right in zip(source_values, result_values)
    ) / count
    return {
        "correlation": max(-1.0, min(1.0, correlation)),
        "similarity": max(-1.0, min(1.0, similarity)),
        "mae": max(0.0, min(1.0, mae)),
    }


def _median(values: list[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _source_plate_regions(bboxes: list[list[float]]) -> list[list[float]]:
    """Return sizeable plate strips outside the selected actor union."""

    if not bboxes:
        return []
    left = min(float(row[0]) for row in bboxes)
    top = min(float(row[1]) for row in bboxes)
    right = max(float(row[2]) for row in bboxes)
    bottom = max(float(row[3]) for row in bboxes)
    candidates = [
        [0.0, 0.0, left, 1.0],
        [right, 0.0, 1.0, 1.0],
        [left, 0.0, right, top],
        [left, bottom, right, 1.0],
    ]
    return [
        row for row in candidates
        if row[2] - row[0] >= 0.08
        and row[3] - row[1] >= 0.08
        and (row[2] - row[0]) * (row[3] - row[1]) >= 0.035
    ]


def source_plate_drifted(rows: list[dict], spec: dict) -> bool:
    """Classify a Relay take that jumped to another V1 Shot or role.

    One region may legitimately change because hair, a hand, or the selected
    body crosses its coarse box.  Drift is therefore reported only when at
    least two outside regions exist, even the strongest anchor is lost, the
    median structure is weak, and the median pixel error is material.
    """

    if len(rows) < 2:
        return False
    similarities = [float(row.get("similarity", 0.0)) for row in rows]
    maes = [float(row.get("mae", 1.0)) for row in rows]
    return bool(
        max(similarities) < float(
            spec.get("minimum_plate_anchor_similarity", 0.50) or 0.50
        )
        and _median(similarities) < float(
            spec.get("minimum_plate_median_similarity", 0.30) or 0.30
        )
        and _median(maes) >= float(
            spec.get("minimum_plate_median_mae", 0.12) or 0.12
        )
    )


def inspect_character_swap_identity(
    ffmpeg: Path,
    ffprobe: Path,
    source: Path,
    result: Path,
    spec: dict,
) -> dict:
    """Detect a no-op identity pass by comparing only selected actor pixels.

    A near-identical region with low target likeness is ambiguous when the
    plate itself is static there (an unchanged background strip), so it no
    longer forces fresh-seed retries by itself.

    This is deliberately a conservative failure detector, not face
    recognition.  It retries only when the selected identity region remains
    simultaneously very highly correlated, structurally similar and almost
    pixel-identical to V1.
    """

    raw_bboxes = list(spec.get("source_bboxes_normalized") or [])
    raw_role_ids = [
        str(value or "").strip().upper()
        for value in (spec.get("source_role_ids") or [])
    ]
    # A role id may only be trusted against a rectangle when the two lists were
    # built together.  Otherwise every verdict stays unlabelled.
    raw_role_ids = (
        raw_role_ids
        if len(raw_role_ids) == len(raw_bboxes)
        else [""] * len(raw_bboxes)
    )
    advisory_role_ids = {
        str(value or "").strip().upper()
        for value in (spec.get("advisory_source_role_ids") or [])
        if str(value or "").strip()
    }
    # Keep the raw index alongside the usable rectangle: the erasure, mouth and
    # lower-body audits below walk the raw list, and dropping a rectangle used to
    # silently shift every later verdict onto the next actor's pixels.
    identity_regions = [
        (raw_index, region)
        for raw_index, region in enumerate(
            _identity_region_bbox(row) for row in raw_bboxes
        )
        if region
    ]
    bboxes = [region for _, region in identity_regions]
    if not bboxes:
        return {
            "passed": True,
            "available": False,
            "reason": "no reliable selected-person rectangle",
            "action": "no_retry",
        }
    if not source.is_file() or not result.is_file():
        return {
            "passed": True,
            "available": False,
            "reason": "source or result video is missing",
            "action": "no_retry",
        }
    duration = min(_probe_duration(ffprobe, source), _probe_duration(ffprobe, result))
    if duration <= 0.08:
        return {
            "passed": True,
            "available": False,
            "reason": "video duration is too short to audit",
            "action": "no_retry",
        }
    maximum_correlation = float(spec.get("maximum_source_correlation", 0.88))
    maximum_similarity = float(spec.get("maximum_source_similarity", 0.88))
    maximum_mae = float(spec.get("maximum_source_mae", 0.055))
    # Both files are sampled at identical stamps, so the frame interval is
    # taken as the coarser of the two: sampling a 24fps plate and a 30fps take
    # at stamps 0.04s apart would otherwise compare different moments.
    frame_interval = max(
        _probe_frame_interval(ffprobe, source),
        _probe_frame_interval(ffprobe, result),
    )
    timestamps = _clamped_timestamps(duration, (0.22, 0.50, 0.78), frame_interval)
    strict_temporal_coverage = bool(spec.get("strict_temporal_coverage", False))
    identity_timestamps = (
        _clamped_timestamps(duration, (0.12, 0.30, 0.50, 0.70, 0.82), frame_interval)
        if strict_temporal_coverage else timestamps
    )
    # Policy 80: the wardrobe cue sampled a second time in the last quarter of the
    # window.  The 0.78 sample is reused as the first late sample, so this costs two
    # extra decodes per region instead of three.  When the window is too short for
    # the ceiling clamp to leave distinct stamps, the list is empty and every late
    # number reports as unavailable.
    wardrobe_late_timestamps = [
        value
        for value in _clamped_timestamps(duration, (0.86, 0.94), frame_interval)
        if value not in timestamps
    ]
    role_results: list[dict] = []
    for bbox_index, (raw_bbox_index, bbox) in enumerate(identity_regions):
        samples: list[dict[str, float]] = []
        for timestamp in identity_timestamps:
            source_frame = _extract_identity_gray_frame(
                ffmpeg, source, timestamp, bbox
            )
            result_frame = _extract_identity_gray_frame(
                ffmpeg, result, timestamp, bbox
            )
            samples.append(identity_frame_metrics(source_frame, result_frame))
        # Median sampling tolerates a blink, fast occlusion or a single cut.
        medians = {
            key: sorted(sample[key] for sample in samples)[len(samples) // 2]
            for key in ("correlation", "similarity", "mae")
        }
        suspicious_samples = sum(
            1 for sample in samples
            if sample["correlation"] >= maximum_correlation
            and sample["similarity"] >= maximum_similarity
            and sample["mae"] <= maximum_mae
        )
        median_suspicious = bool(
            medians["correlation"] >= maximum_correlation
            and medians["similarity"] >= maximum_similarity
            and medians["mae"] <= maximum_mae
        )
        partial_noop = bool(
            strict_temporal_coverage
            and suspicious_samples >= 2
            and suspicious_samples >= math.ceil(len(samples) * 0.34)
        )
        suspicious = median_suspicious or partial_noop
        role_id = raw_role_ids[raw_bbox_index]
        role_results.append({
            "bbox_index": bbox_index,
            "raw_bbox_index": raw_bbox_index,
            "source_role_id": role_id,
            # An explicitly selected extra body: the director asked for it, but
            # it is not the performer the Shot is about, so a retained V1 there
            # is reported for review instead of spending another H3 generation.
            "advisory": bool(role_id) and role_id in advisory_role_ids,
            "bbox_normalized": [round(value, 6) for value in bbox],
            **{key: round(value, 6) for key, value in medians.items()},
            "source_retained_samples": suspicious_samples,
            "sample_count": len(samples),
            "partial_noop": partial_noop,
            "source_identity_retained": suspicious,
        })

    role_by_raw_index = {
        int(row["raw_bbox_index"]): row for row in role_results
    }
    plate_bboxes: list[list[float]] = []
    for raw_bbox in raw_bboxes:
        try:
            left, top, right, bottom = [float(value) for value in raw_bbox][:4]
        except (TypeError, ValueError, OverflowError):
            continue
        left, top = max(0.0, left), max(0.0, top)
        right, bottom = min(1.0, right), min(1.0, bottom)
        if right - left >= 0.03 and bottom - top >= 0.03:
            plate_bboxes.append([left, top, right, bottom])
    plate_rows: list[dict] = []
    for region_index, plate_bbox in enumerate(
        _source_plate_regions(plate_bboxes)
    ):
        samples: list[dict[str, float]] = []
        for timestamp in timestamps:
            source_frame = _extract_identity_gray_frame(
                ffmpeg, source, timestamp, plate_bbox
            )
            result_frame = _extract_identity_gray_frame(
                ffmpeg, result, timestamp, plate_bbox
            )
            samples.append(identity_frame_metrics(source_frame, result_frame))
        medians = {
            key: _median([sample[key] for sample in samples])
            for key in ("correlation", "similarity", "mae")
        }
        plate_rows.append({
            "region_index": region_index,
            "bbox_normalized": [round(value, 6) for value in plate_bbox],
            **{key: round(value, 6) for key, value in medians.items()},
        })
    # Round 52: the drift verdict is still measured and recorded, but it only
    # fails a take when the Job asked for it.  The lean routes ship
    # ``plate_audit: False`` because this coarse outside-box gate is what
    # re-rolled two 20-minute takes on the policy-84 Segment before the third
    # attempt died on an unrelated write error.
    plate_failed = bool(
        spec.get("plate_audit", True) and source_plate_drifted(plate_rows, spec)
    )
    erasure_rows: list[dict] = []
    for bbox_index, raw_bbox in enumerate(raw_bboxes):
        try:
            full_bbox = [float(value) for value in raw_bbox][:4]
        except (TypeError, ValueError, OverflowError):
            continue
        role_result = role_by_raw_index.get(bbox_index)
        if len(full_bbox) != 4 or role_result is None:
            continue
        samples: list[dict[str, float]] = []
        for timestamp in timestamps:
            source_frame = _extract_identity_gray_frame(
                ffmpeg, source, timestamp, full_bbox
            )
            result_frame = _extract_identity_gray_frame(
                ffmpeg, result, timestamp, full_bbox
            )
            samples.append(identity_frame_metrics(source_frame, result_frame))
        medians = {
            key: sorted(sample[key] for sample in samples)[len(samples) // 2]
            for key in ("correlation", "similarity", "mae")
        }
        identity_similarity = float(role_result["similarity"])
        similarity_gap = medians["similarity"] - identity_similarity
        incomplete = bool(
            not role_result["source_identity_retained"]
            and medians["correlation"] >= float(
                spec.get("minimum_erasure_correlation", 0.82) or 0.82
            )
            and medians["similarity"] >= float(
                spec.get("minimum_erasure_similarity", 0.82) or 0.82
            )
            and medians["mae"] <= float(
                spec.get("maximum_erasure_mae", 0.12) or 0.12
            )
            and similarity_gap >= float(
                spec.get("minimum_erasure_identity_gap", 0.10) or 0.10
            )
        )
        erasure_rows.append({
            "bbox_index": bbox_index,
            "bbox_normalized": [round(value, 6) for value in full_bbox],
            **{key: round(value, 6) for key, value in medians.items()},
            "identity_similarity_gap": round(similarity_gap, 6),
            "incomplete_source_actor_erasure": incomplete,
        })
    lower_body_rows: list[dict] = []
    # ``strict_temporal_coverage`` keeps its original meaning (dense face
    # sampling on a close-up).  The whole-body check now asks for the same dense
    # sampling on its own terms: the black-shirt Shot is a medium silent listener,
    # was never close-up-gated, and its head-only swap was accepted on attempt 1
    # because the lower-body loop had never been asked to run.
    if strict_temporal_coverage or bool(spec.get("whole_character_audit", False)):
        for bbox_index, raw_bbox in enumerate(raw_bboxes):
            try:
                left, top, right, bottom = [float(value) for value in raw_bbox][:4]
            except (TypeError, ValueError, OverflowError):
                continue
            if right - left < 0.03 or bottom - top < 0.08:
                continue
            height = bottom - top
            lower_bbox = [left, top + height * 0.78, right, bottom]
            samples = []
            for timestamp in timestamps:
                source_frame = _extract_identity_gray_frame(
                    ffmpeg, source, timestamp, lower_bbox
                )
                result_frame = _extract_identity_gray_frame(
                    ffmpeg, result, timestamp, lower_bbox
                )
                samples.append(identity_frame_metrics(source_frame, result_frame))
            medians = {
                key: _median([sample[key] for sample in samples])
                for key in ("correlation", "similarity", "mae")
            }
            retained = bool(
                medians["correlation"] >= 0.90
                and medians["similarity"] >= 0.90
                and medians["mae"] <= 0.06
            )
            lower_body_rows.append({
                "bbox_index": bbox_index,
                "bbox_normalized": [round(value, 6) for value in lower_bbox],
                **{key: round(value, 6) for key, value in medians.items()},
                "source_body_retained": retained,
            })
    identity_failed = any(
        row["source_identity_retained"] and not row.get("advisory")
        for row in role_results
    )
    erasure_failed = any(
        row["incomplete_source_actor_erasure"] for row in erasure_rows
    )
    lower_body_failed = any(
        row["source_body_retained"] for row in lower_body_rows
    )
    retention_score = max(
        (
            (row["correlation"] + row["similarity"]) / 2.0
            - row["mae"]
            for row in role_results
            if not row.get("advisory")
        ),
        # Nothing but an advisory bystander was inspected, so no V1 performer is
        # known to be holding its ground; rank the take on its other penalties.
        default=0.0,
    )
    performance_mode = str(spec.get("performance_mode") or "").strip().casefold()
    silent_mouth_result: dict = {}
    silent_mouth_failed = False
    if performance_mode in {"silent_listener", "no_human_voice"}:
        mouth_rows: list[dict] = []
        geometry_mode, geometry_margin, geometry_floor = (
            _silent_mouth_geometry_settings()
        )
        plate_gate_mode, plate_motion_gain, plate_motion_floor = (
            _silent_plate_gate_settings()
        )
        hard_gate_tolerance = _silent_mouth_hard_gate_tolerance()
        # The plate is a separate reference on purpose.  ``source`` stays the raw
        # V1 clip for every other gate in this audit — erasure and retention have
        # to measure the real performance — while the mouth question has to be
        # asked against what Relay was actually conditioned on.
        plate_video = Path(str(spec.get("plate_video_path") or "").strip())
        plate_available = bool(
            str(spec.get("plate_video_path") or "").strip()
        ) and plate_video.is_file()
        mouth_timestamps = _clamped_timestamps(
            duration, (0.12, 0.24, 0.36, 0.50, 0.64, 0.76, 0.88), frame_interval
        )
        for bbox_index, raw_bbox in enumerate(raw_bboxes):
            mouth_bbox, band_registration = _mouth_band_registration(raw_bbox)
            if not mouth_bbox:
                continue
            mouth_probe_size = 80
            upper_bbox = _upper_face_region_bbox(raw_bbox)
            source_frames = [
                _extract_identity_gray_frame(
                    ffmpeg, source, timestamp, mouth_bbox, size=mouth_probe_size
                )
                for timestamp in mouth_timestamps
            ]
            result_frames = [
                _extract_identity_gray_frame(
                    ffmpeg, result, timestamp, mouth_bbox, size=mouth_probe_size
                )
                for timestamp in mouth_timestamps
            ]
            # The suppressed plate, sampled at the same stamps and the same
            # registered rectangle.  A plate the Studio froze this round should
            # read close to zero here; if it does not, the freeze did not reach
            # the audited pixels and the take is not the thing being measured.
            plate_frames: list[bytes] = []
            plate_motion = 0.0
            plate_motion_mean = 0.0
            plate_measured = False
            if plate_available and plate_gate_mode != "off":
                try:
                    plate_frames = [
                        _extract_identity_gray_frame(
                            ffmpeg,
                            plate_video,
                            timestamp,
                            mouth_bbox,
                            size=mouth_probe_size,
                        )
                        for timestamp in mouth_timestamps
                    ]
                    plate_motion = robust_temporal_frame_motion(plate_frames)
                    plate_motion_mean = temporal_frame_motion(plate_frames)
                    plate_measured = True
                except (
                    OSError,
                    RuntimeError,
                    ValueError,
                    subprocess.SubprocessError,
                ):
                    plate_measured = False
            # The mean still measures "something moved a lot somewhere"; the
            # median measures "it kept moving", which is what articulation is.
            source_motion_mean = temporal_frame_motion(source_frames)
            result_motion_mean = temporal_frame_motion(result_frames)
            source_motion = robust_temporal_frame_motion(source_frames)
            result_motion = robust_temporal_frame_motion(result_frames)
            contract_maximum_motion = float(
                spec.get("maximum_silent_mouth_motion", 0.055) or 0.055
            )
            maximum_motion = max(
                contract_maximum_motion,
                source_motion * 1.5 + 0.012,
            )
            plate_relative_limit = (
                max(
                    contract_maximum_motion,
                    plate_motion * plate_motion_gain + plate_motion_floor,
                )
                if plate_measured
                else 0.0
            )
            plate_relative_violated = bool(
                plate_measured and result_motion > plate_relative_limit
            )
            # "The source talks" is only a fact about the plate the model saw.
            # When V1 articulates and the suppressed plate does not, every retry
            # the old absolute cap spent was chasing a performance Relay was never
            # conditioned on — which is how three fresh seeds in a row lost.
            source_speech_conflict = bool(
                plate_measured
                and source_motion
                > max(
                    contract_maximum_motion,
                    plate_motion * 2.0 + plate_motion_floor,
                )
            )
            # Blinking, a passing prop and handheld shake all move the head, so
            # the eye band above the mouth is the honest control region: real
            # lip-sync moves the lower face clearly more than the upper face.
            upper_motion = 0.0
            upper_frames: list[bytes] = []
            if upper_bbox:
                upper_frames = [
                    _extract_identity_gray_frame(
                        ffmpeg, result, timestamp, upper_bbox, size=mouth_probe_size
                    )
                    for timestamp in mouth_timestamps
                ]
                upper_motion = robust_temporal_frame_motion(upper_frames)
            upper_relative_limit = upper_motion * 1.25 + 0.02
            motion_violated = bool(
                result_motion > maximum_motion
                and result_motion > upper_relative_limit
            )
            # Round 37e tried to make the registered mouth cavity's *swing*
            # decide, because adjacent-frame difference could not: measured on
            # the policy 73 take, the forehead band boiled harder (median
            # 0.26-0.29) than the real mouth (0.22-0.32), so the absolute cap and
            # the upper-face relative limit were both reading redraw noise.  The
            # control band runs the identical shape algorithm, so what should be
            # left over is the oral cavity opening and closing — not boiling, not
            # a blink, not a prop, and not a reference grin held open for the
            # whole clip.  Round 37f measured that on the result side it is not:
            # sampled at 24 fps with a five-frame smoothing window the cavity read
            # 0.10-0.60 on every row band, hair and hatband included, and its
            # noisiest non-mouth row sat within 0.05 of the mouth row.  The
            # source plate reads 0.000-0.100 on the same algorithm, so the shape
            # is honest about the plate and unreadable about a head Relay has
            # re-drawn.  That is why the default is advisory again: the numbers
            # stay in the manifest, the pixel-motion gate below keeps deciding.
            mouth_profile = control_profile = source_profile = {
                "available": False, "median": 0.0, "swing": 0.0, "samples": 0,
            }
            geometry_available = False
            geometry_violated = False
            swing_limit = 0.0
            if geometry_mode != "off":
                mouth_profile = _cavity_opening_profile(
                    result_frames, mouth_probe_size
                )
                source_profile = _cavity_opening_profile(
                    source_frames, mouth_probe_size
                )
                if upper_frames:
                    control_profile = _cavity_opening_profile(
                        upper_frames, mouth_probe_size
                    )
                if mouth_profile["available"] and control_profile["available"]:
                    swing_limit = max(
                        control_profile["swing"] * geometry_margin, geometry_floor
                    )
                    geometry_available = True
                    geometry_violated = mouth_profile["swing"] > swing_limit
            if plate_gate_mode == "on" and plate_measured:
                violated = plate_relative_violated
                decision_basis = "plate_relative_pixel_motion"
                articulation_excess = max(
                    0.0, result_motion - plate_relative_limit
                )
            elif geometry_mode == "on" and geometry_available:
                violated = geometry_violated
                decision_basis = "mouth_cavity_geometry"
                articulation_excess = max(
                    0.0, mouth_profile["swing"] - swing_limit
                )
            else:
                # Three ways land here: the operator switched the gate off, the
                # mode is the default advisory, or the registered band produced
                # too few readable frames to measure a shape.  In every one of
                # them the pixel-motion rule still runs, so a QC-only change
                # cannot silently disable the audit; under advisory the geometry
                # numbers above are recorded next to the verdict for A/B later.
                violated = motion_violated
                decision_basis = "pixel_motion"
                articulation_excess = max(0.0, result_motion - maximum_motion)
            governing_limit = (
                plate_relative_limit
                if decision_basis == "plate_relative_pixel_motion"
                else swing_limit
                if decision_basis == "mouth_cavity_geometry"
                else maximum_motion
            )
            # The excess is an absolute amount, so the only way to grade it
            # across Shots is as a fraction of the limit it was measured
            # against: 0.054 over a 0.226 limit is a different claim from 0.054
            # over a 0.055 contract cap.
            overrun_ratio = (
                articulation_excess / governing_limit
                if governing_limit > 0.0
                else (1.0 if articulation_excess > 0.0 else 0.0)
            )
            # Advisory, not a spent seed: the take overran but stayed inside the
            # tolerance and nothing independent confirmed mouth movement.  The
            # arithmetic stays in the manifest either way.
            advisory_overrun = bool(
                violated
                and overrun_ratio <= hard_gate_tolerance
                and not (geometry_available and geometry_violated)
            )
            violated = bool(violated and not advisory_overrun)
            mouth_rows.append({
                "bbox_index": bbox_index,
                "bbox_normalized": [round(value, 6) for value in mouth_bbox],
                "band_registration": band_registration,
                "source_motion": round(source_motion, 6),
                "result_motion": round(result_motion, 6),
                "source_motion_mean": round(source_motion_mean, 6),
                "result_motion_mean": round(result_motion_mean, 6),
                "plate_motion": round(plate_motion, 6),
                "plate_motion_mean": round(plate_motion_mean, 6),
                "plate_measured": plate_measured,
                "plate_relative_motion_limit": round(plate_relative_limit, 6),
                "plate_relative_violated": plate_relative_violated,
                "source_speech_conflict": source_speech_conflict,
                "verdict_scope": (
                    _silent_plate_verdict_scope(plate_video)
                    if plate_measured
                    else "relative_to_raw_source"
                ),
                "upper_face_motion": round(upper_motion, 6),
                "upper_relative_motion_limit": round(upper_relative_limit, 6),
                "maximum_motion": round(maximum_motion, 6),
                "motion_violated": motion_violated,
                "mouth_opening_median": mouth_profile["median"],
                "mouth_opening_swing": mouth_profile["swing"],
                "control_opening_median": control_profile["median"],
                "control_opening_swing": control_profile["swing"],
                "source_mouth_opening_median": source_profile["median"],
                "source_mouth_opening_swing": source_profile["swing"],
                "geometry_available": geometry_available,
                "geometry_swing_limit": round(swing_limit, 6),
                "geometry_violated": geometry_violated,
                "decision_basis": decision_basis,
                "articulation_excess": round(articulation_excess, 6),
                "governing_motion_limit": round(governing_limit, 6),
                "overrun_ratio": round(overrun_ratio, 6),
                "hard_gate_tolerance": round(hard_gate_tolerance, 6),
                "advisory_overrun": advisory_overrun,
                "violated": violated,
            })
        silent_mouth_failed = any(row["violated"] for row in mouth_rows)
        silent_mouth_result = {
            "checked": bool(mouth_rows),
            "passed": not silent_mouth_failed,
            "gate": (
                "mouth_cavity_geometry_with_pixel_motion_fallback"
                if geometry_mode == "on"
                else "pixel_motion_with_cavity_geometry_recorded"
                if geometry_mode == "advisory"
                else "pixel_motion"
            ),
            "geometry_mode": geometry_mode,
            "geometry_margin": round(geometry_margin, 4),
            "geometry_floor": round(geometry_floor, 4),
            "plate_gate_mode": plate_gate_mode,
            "plate_motion_gain": round(plate_motion_gain, 4),
            "plate_motion_floor": round(plate_motion_floor, 4),
            "hard_gate_tolerance": round(hard_gate_tolerance, 6),
            "advisory_overrun_rows": sum(
                1 for mouth_row in mouth_rows if mouth_row.get("advisory_overrun")
            ),
            "hard_failed_rows": sum(
                1 for mouth_row in mouth_rows if mouth_row["violated"]
            ),
            "plate_video_path": str(plate_video) if plate_available else "",
            "plate_available": plate_available,
            "verdict_scope": (
                _silent_plate_verdict_scope(plate_video)
                if any(mouth_row["plate_measured"] for mouth_row in mouth_rows)
                else "relative_to_raw_source"
            ),
            "rows": mouth_rows,
        }
    target_reference_audit: dict = {
        "available": False,
        "similarity": None,
        "reason": "target P Picture is unavailable",
    }
    target_reference_path = Path(
        str(
            spec.get("target_reference_qc_path")
            or spec.get("target_reference_path")
            or ""
        )
    )
    if target_reference_path.is_file():
        try:
            reference_frame = _extract_identity_rgb_frame(
                ffmpeg, target_reference_path, 0.0
            )
            target_samples: list[float] = []
            target_sample_rows: list[dict] = []
            for bbox_index, bbox in enumerate(bboxes):
                for timestamp in timestamps:
                    score = target_reference_frame_similarity(
                        reference_frame,
                        _extract_identity_rgb_frame(
                            ffmpeg, result, timestamp, bbox
                        ),
                    )
                    target_samples.append(score)
                    target_sample_rows.append(
                        {
                            "bbox_index": bbox_index,
                            "timestamp_seconds": round(float(timestamp), 3),
                            "similarity": round(score, 6),
                        }
                    )
            worst_sample = (
                min(target_sample_rows, key=lambda row: row["similarity"])
                if target_sample_rows
                else None
            )
            # Round 92: the median stays exactly where the retry ranking has always
            # read it, and the worst sample joins it.  A median of three is what
            # let a take that shows the target character at 3 s and 11 s and the V1
            # performer at 7 s score 0.573 and ship; the veto needs the frame that
            # failed, and the manifest should name it.
            target_reference_audit = {
                "available": bool(target_samples),
                "similarity": (
                    round(_median(target_samples), 6)
                    if target_samples else None
                ),
                "minimum_similarity": (
                    round(min(target_samples), 6) if target_samples else None
                ),
                "worst_timestamp_seconds": (
                    worst_sample["timestamp_seconds"] if worst_sample else None
                ),
                "worst_bbox_index": (
                    worst_sample["bbox_index"] if worst_sample else None
                ),
                "sample_count": len(target_samples),
                "samples": target_sample_rows,
                "reason": "rank completed retries by resemblance to target P Picture",
            }
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            target_reference_audit = {
                "available": False,
                "similarity": None,
                "reason": f"target P Picture audit unavailable: {exc}",
            }

    # Whole-body wardrobe gate.  Thirty rounds of director grading said the same
    # thing in different words: "head OK, clothes still V1", "only the head was
    # swapped".  Nothing in QC measured that, because the face regions carry the
    # identity verdict and the whole-picture target cue is dominated by head
    # pixels.  This gate asks the one question the eye was answering: inside the
    # rectangle the plate blur covered, did the colour distribution move towards
    # Picture 1's garment strip, or is it still the source actor's outfit?  The
    # ruler is a difference, not an absolute, so a dark costume next to a dark
    # plate cannot pass by accident and a bright one cannot fail by accident.
    # Calibrated on the three accepted head-only takes of the black-shirt
    # Project: medians 0.053 / 0.089 / 0.114, best frame in the run 0.177 (a
    # partial outfit patch), against >= 0.20 for a confirmed whole-body swap.
    # Policy 72 binds that same floor on each half of the rectangle.  Seed
    # 923010107 cleared it three times over — 0.121 / 0.155 / 0.124 — and the
    # frames behind those numbers wore Picture 1's yellow checkered leg warmers
    # below the waist and the cosplayer's pink sleeves plus gold-trimmed black
    # vest above it.  A median cannot tell a costume change from a legwear
    # change, which is exactly the difference the director kept grading as
    # "only the head was swapped".
    wardrobe_audit_mode = str(spec.get("wardrobe_audit_mode") or "on").strip().lower()
    if wardrobe_audit_mode not in {"on", "advisory", "off"}:
        wardrobe_audit_mode = "on"
    wardrobe_reference_path = Path(
        str(spec.get("target_reference_wardrobe_qc_path") or "")
    )
    wardrobe_boxes = _wardrobe_audit_bboxes(spec.get("body_bboxes_normalized"))
    wardrobe_floor = float(
        spec.get("minimum_wardrobe_shift", 0.12) or 0.0
    )
    (
        wardrobe_floor_policy,
        wardrobe_relative_gain,
        wardrobe_sanity_floor,
    ) = _wardrobe_floor_policy_settings()
    # A zero floor has always meant "this Shot does not gate on wardrobe"; the
    # relative rule must not silently re-arm that disabled gate.
    wardrobe_gate_enabled = bool(wardrobe_floor > 0.0)
    wardrobe_shift: float | None = None
    wardrobe_shift_late: float | None = None
    wardrobe_failed = False
    wardrobe_binding_region = "whole"
    wardrobe_audit: dict = {
        "checked": False,
        "passed": True,
        "mode": wardrobe_audit_mode,
        "rows": [],
        "minimum_shift": round(wardrobe_floor, 6),
        "floor_policy": wardrobe_floor_policy,
        "relative_gain": round(wardrobe_relative_gain, 6),
        "sanity_floor": round(wardrobe_sanity_floor, 6),
        "reason": "no garment-only reference for this Picture",
    }
    if wardrobe_audit_mode == "off":
        wardrobe_audit["reason"] = "wardrobe audit disabled for this pass"
    elif not wardrobe_reference_path.is_file():
        wardrobe_audit["reason"] = (
            "target P Picture has no measurable garment region (portrait artwork)"
        )
    elif not wardrobe_boxes:
        wardrobe_audit["reason"] = (
            "no body region reported for this pass"
        )
    else:
        try:
            wardrobe_frame = _extract_identity_rgb_frame(
                ffmpeg, wardrobe_reference_path, 0.0
            )
            wardrobe_rows: list[dict] = []
            for bbox_index, body_bbox in enumerate(wardrobe_boxes):
                region_rows: list[dict] = []
                for region_name, region_bbox in _wardrobe_region_boxes(
                    body_bbox
                ):
                    take_scores: list[float] = []
                    source_scores: list[float] = []
                    for timestamp in timestamps:
                        take_scores.append(
                            target_reference_frame_similarity(
                                wardrobe_frame,
                                _extract_identity_rgb_frame(
                                    ffmpeg, result, timestamp, region_bbox
                                ),
                            )
                        )
                        source_scores.append(
                            target_reference_frame_similarity(
                                wardrobe_frame,
                                _extract_identity_rgb_frame(
                                    ffmpeg, source, timestamp, region_bbox
                                ),
                            )
                        )
                    take_median = _median(take_scores)
                    source_median = _median(source_scores)
                    region_shift = take_median - source_median
                    if wardrobe_gate_enabled:
                        (
                            region_passed,
                            region_required_relative,
                            region_relative_ok,
                        ) = _wardrobe_region_passed(
                            region_shift,
                            take_median,
                            source_median,
                            absolute_floor=wardrobe_floor,
                            policy=wardrobe_floor_policy,
                            relative_gain=wardrobe_relative_gain,
                            sanity_floor=wardrobe_sanity_floor,
                        )
                    else:
                        region_passed = True
                        region_required_relative = 0.0
                        region_relative_ok = False
                    # Policy 80, the same cue over the tail of the window.  The
                    # median above is what gates QC; this number is what lets the
                    # retry ranking see a costume that H3 only finishes putting on
                    # after 78 % of the clip.
                    region_shift_late: float | None = None
                    if wardrobe_late_timestamps:
                        late_take_scores = [take_scores[-1]]
                        late_source_scores = [source_scores[-1]]
                        for timestamp in wardrobe_late_timestamps:
                            late_take_scores.append(
                                target_reference_frame_similarity(
                                    wardrobe_frame,
                                    _extract_identity_rgb_frame(
                                        ffmpeg, result, timestamp, region_bbox
                                    ),
                                )
                            )
                            late_source_scores.append(
                                target_reference_frame_similarity(
                                    wardrobe_frame,
                                    _extract_identity_rgb_frame(
                                        ffmpeg, source, timestamp, region_bbox
                                    ),
                                )
                            )
                        region_shift_late = (
                            _median(late_take_scores)
                            - _median(late_source_scores)
                        )
                    region_rows.append({
                        "region": region_name,
                        "bbox_normalized": [
                            round(value, 6) for value in region_bbox
                        ],
                        "target_similarity": round(take_median, 6),
                        "source_similarity": round(source_median, 6),
                        "wardrobe_shift": round(region_shift, 6),
                        "wardrobe_shift_late": (
                            None if region_shift_late is None
                            else round(region_shift_late, 6)
                        ),
                        "sample_count": len(take_scores),
                        "source_wardrobe_retained": bool(
                            not region_passed
                        ),
                        "absolute_floor_passed": bool(
                            wardrobe_floor > 0.0
                            and region_shift >= wardrobe_floor
                        ),
                        "relative_floor_passed": bool(region_relative_ok),
                        "required_relative_shift": round(
                            region_required_relative, 6
                        ),
                        "floor_policy": wardrobe_floor_policy,
                    })
                if not region_rows:
                    continue
                # The binding region is the half that moved least.  Reporting
                # the better half is what let a legs-only swap read as a
                # finished costume change, so both the verdict and the retry
                # ranking follow the worst half.
                binding = min(
                    region_rows, key=lambda row: row["wardrobe_shift"]
                )
                if binding["source_wardrobe_retained"]:
                    wardrobe_binding_region = binding["region"]
                wardrobe_rows.append({
                    "bbox_index": bbox_index,
                    "bbox_normalized": [
                        round(value, 6) for value in body_bbox
                    ],
                    "region_split": bool(len(region_rows) > 1),
                    "binding_region": binding["region"],
                    "target_similarity": binding["target_similarity"],
                    "source_similarity": binding["source_similarity"],
                    "wardrobe_shift": binding["wardrobe_shift"],
                    # The tail measurement of the *same* region the median bound
                    # on, so the two numbers describe the same pixels and only the
                    # window differs.
                    "wardrobe_shift_late": binding.get("wardrobe_shift_late"),
                    "sample_count": min(
                        row["sample_count"] for row in region_rows
                    ),
                    "regions": region_rows,
                    "source_wardrobe_retained": bool(
                        binding["source_wardrobe_retained"]
                    ),
                })
            row_shifts = [
                row["wardrobe_shift"]
                for row in wardrobe_rows
                if row["wardrobe_shift"] is not None
            ]
            wardrobe_shift = (
                round(_median(row_shifts), 6) if row_shifts else None
            )
            late_row_shifts = [
                row["wardrobe_shift_late"]
                for row in wardrobe_rows
                if row.get("wardrobe_shift_late") is not None
            ]
            wardrobe_shift_late = (
                round(_median(late_row_shifts), 6) if late_row_shifts else None
            )
            # Shot-level verdict.  The absolute test below is the historical
            # gate and is left untouched; the relative rule can only ever
            # *relax* it, so ``policy=absolute`` (and every pre-83 manifest)
            # behaves exactly as before.  The relative pair is measured on the
            # same aggregate median the gate reads, from the binding region of
            # each body box, so the two rules describe the same pixels.
            aggregate_take_median = _median(
                [
                    row["target_similarity"]
                    for row in wardrobe_rows
                    if row.get("target_similarity") is not None
                ]
            )
            aggregate_source_median = _median(
                [
                    row["source_similarity"]
                    for row in wardrobe_rows
                    if row.get("source_similarity") is not None
                ]
            )
            absolute_floor_failed = bool(
                wardrobe_audit_mode == "on"
                and row_shifts
                and wardrobe_floor > 0.0
                and float(wardrobe_shift or 0.0) < wardrobe_floor
            )
            (
                aggregate_passed,
                aggregate_required_relative,
                aggregate_relative_ok,
            ) = _wardrobe_region_passed(
                float(wardrobe_shift or 0.0),
                aggregate_take_median,
                aggregate_source_median,
                absolute_floor=wardrobe_floor,
                policy=wardrobe_floor_policy,
                relative_gain=wardrobe_relative_gain,
                sanity_floor=wardrobe_sanity_floor,
            )
            wardrobe_failed = bool(
                absolute_floor_failed and not aggregate_relative_ok
            )
            wardrobe_audit = {
                "checked": bool(wardrobe_rows),
                "passed": not wardrobe_failed,
                "mode": wardrobe_audit_mode,
                "shift": wardrobe_shift,
                "late_shift": wardrobe_shift_late,
                "floor_policy": wardrobe_floor_policy,
                "relative_gain": round(wardrobe_relative_gain, 6),
                "sanity_floor": round(wardrobe_sanity_floor, 6),
                "required_relative_shift": round(
                    aggregate_required_relative, 6
                ),
                "binding_target_similarity": round(aggregate_take_median, 6),
                "binding_source_similarity": round(
                    aggregate_source_median, 6
                ),
                "absolute_floor_passed": bool(not absolute_floor_failed),
                "relative_floor_passed": bool(aggregate_relative_ok),
                "aggregate_rule_passed": bool(aggregate_passed),
                "late_timestamps_normalized": (
                    [0.78, 0.86, 0.94] if wardrobe_late_timestamps else []
                ),
                "binding_region": (
                    wardrobe_binding_region if wardrobe_failed else None
                ),
                "region_policy": "each_half_must_move",
                "rows": wardrobe_rows,
                "minimum_shift": round(wardrobe_floor, 6),
                "reason": (
                    "body region moved towards Picture 1's wardrobe"
                    if not wardrobe_failed else
                    (
                        f"{wardrobe_binding_region} body region moved neither "
                        f"the absolute {round(wardrobe_floor, 6)} shift nor the "
                        f"relative {round(aggregate_required_relative, 6)} "
                        "gain over the source wardrobe"
                        if wardrobe_binding_region != "whole" else
                        "body region moved neither the absolute "
                        f"{round(wardrobe_floor, 6)} shift nor the relative "
                        f"{round(aggregate_required_relative, 6)} gain over "
                        "the source wardrobe"
                    )
                ),
            }
        except (
            OSError, RuntimeError, ValueError, subprocess.SubprocessError
        ) as exc:
            wardrobe_audit = {
                "checked": False,
                "passed": True,
                "mode": wardrobe_audit_mode,
                "rows": [],
                "minimum_shift": round(wardrobe_floor, 6),
                "floor_policy": wardrobe_floor_policy,
                "relative_gain": round(wardrobe_relative_gain, 6),
                "sanity_floor": round(wardrobe_sanity_floor, 6),
                "reason": f"wardrobe audit unavailable: {exc}",
            }

    # Target-likeness gate.  The colour-distribution cue cannot see age or face
    # drift - the director rejected S7 and S10 as "became an old man" while the
    # cue still read 0.513 and 0.587 - so the floor stays low and only rejects
    # the regime the cue is trustworthy about: a take whose palette never
    # matches Picture 1 at all.  S8 was accepted on its very first attempt at
    # 0.273 and assembled as the wrong character, which is exactly that case.
    # Identity Sheet composition plus the apparent-age lock attack the age-drift
    # regime instead of forcing extra generations on a cue that cannot see it.
    target_similarity_floor = float(
        spec.get("minimum_target_reference_similarity", 0.30) or 0.0
    )
    target_similarity_failed = bool(
        target_reference_audit.get("available")
        and target_reference_audit.get("similarity") is not None
        and target_similarity_floor > 0.0
        and float(target_reference_audit["similarity"]) < target_similarity_floor
    )

    identity_ambiguity_rows: list[dict] = []
    plate_strip_ambiguous = False
    target_similarity_ambiguous = False
    if identity_failed:
        target_likeness = target_reference_audit.get("similarity")
        ambiguous_timestamps = _clamped_timestamps(
            duration, (0.12, 0.24, 0.36, 0.50, 0.64, 0.76, 0.88), frame_interval
        )
        for row in role_results:
            if not row["source_identity_retained"]:
                continue
            if row.get("advisory"):
                continue
            if (
                row["similarity"] < 0.95
                or not target_reference_audit.get("available")
                or target_likeness is None
                or float(target_likeness) >= 0.25
            ):
                continue
            # A near-identical, low-target-likeness region can be an unchanged
            # background strip rather than a retained actor: only fail when the
            # plate itself moves there (a real preserved performer would move).
            source_frames = [
                _extract_identity_gray_frame(
                    ffmpeg, source, timestamp, row["bbox_normalized"], size=80
                )
                for timestamp in ambiguous_timestamps
            ]
            plate_motion = temporal_frame_motion(source_frames)
            if plate_motion < 0.010:
                row["audit_region_ambiguous"] = True
                identity_ambiguity_rows.append({
                    "bbox_index": row["bbox_index"],
                    "bbox_normalized": row["bbox_normalized"],
                    "similarity": row["similarity"],
                    "plate_motion": round(plate_motion, 6),
                    "target_reference_similarity": target_likeness,
                })
        if identity_ambiguity_rows and all(
            bool(row.get("audit_region_ambiguous"))
            for row in role_results
            if row["source_identity_retained"] and not row.get("advisory")
        ):
            identity_failed = False
            plate_strip_ambiguous = True

    # The near-static plate strip that makes the identity cue read "V1 retained"
    # is the same strip that drags the target-likeness cue down: both samples are
    # an unchanged piece of background, not the performer.  Downgrade the hard
    # floor to a review flag in that case so the S2 wall-strip take does not burn
    # fresh-seed retries on a measurement of wallpaper.  The S8 take genuinely
    # changed identity, so no ambiguity is recorded there and it still fails hard.
    if target_similarity_failed and plate_strip_ambiguous:
        target_similarity_failed = False
        target_similarity_ambiguous = True

    # Round 69 item 3: the head-layer veto.  Computed from the two audits that
    # measure how much of the performer was replaced, corroborated by how far the
    # take sits from Picture 1.  Recorded even when the take already failed for
    # another reason, so the manifest always shows which gate decided a retry.
    # Round 92: the corroboration no longer stops at the median -- one sampled
    # frame below the floor is enough -- and the manifest records which witness
    # fired so the retry is auditable.
    head_layer_only = bool(lower_body_failed or wardrobe_failed)
    blocking_cause = character_swap_head_layer_blocking_cause(
        head_layer_only, target_reference_audit
    )
    blocking_head_layer = bool(blocking_cause)

    failed = (
        identity_failed or erasure_failed or lower_body_failed
        or silent_mouth_failed or plate_failed or target_similarity_failed
        or wardrobe_failed
    )
    mouth_penalty = max(
        (
            # Rank retries on how far the *deciding* measure overshot: under the
            # geometry gate, overshoot on the old pixel-motion number is redraw
            # boiling, and boiling that is identical in every take would make
            # the ranking meaningless.
            float(row.get("articulation_excess"))
            if row.get("articulation_excess") is not None
            else max(0.0, row["result_motion"] - row["maximum_motion"])
            for row in silent_mouth_result.get("rows") or []
        ),
        default=0.0,
    )
    erasure_penalty = max(
        (
            max(0.0, row["identity_similarity_gap"] - 0.10)
            for row in erasure_rows
            if row["incomplete_source_actor_erasure"]
        ),
        default=0.0,
    )
    plate_penalty = (
        max(
            0.0,
            float(spec.get("minimum_plate_anchor_similarity", 0.50) or 0.50)
            - max((row["similarity"] for row in plate_rows), default=0.0),
        ) * 3.0
        if plate_failed else 0.0
    )
    lower_body_penalty = max(
        (
            max(0.0, row["similarity"] - 0.90)
            + max(0.0, 0.06 - row["mae"])
            for row in lower_body_rows
            if row["source_body_retained"]
        ),
        default=0.0,
    )
    # How far the body region fell short of the wardrobe floor.  A take that got
    # part-way (0.089 of 0.12) must rank below one that barely moved (0.02), so
    # the retry budget ends on the take whose body came closest to Picture 1.
    wardrobe_penalty = (
        max(
            0.0,
            wardrobe_floor - (
                wardrobe_shift
                if wardrobe_shift is not None else 0.0
            ),
        )
        if wardrobe_failed else 0.0
    )
    quality_risk_score = (
        retention_score + mouth_penalty * 4.0
        + erasure_penalty * 2.0 + plate_penalty
        + lower_body_penalty * 3.0
        + wardrobe_penalty * 4.0
    )
    if identity_failed and silent_mouth_failed:
        reason = "selected region retains the V1 actor and the authored silent mouth is moving"
    elif identity_failed:
        reason = "selected region still matches the original V1 actor"
    elif erasure_failed and silent_mouth_failed:
        reason = "source actor remains behind the replacement and the authored silent mouth is moving"
    elif erasure_failed:
        reason = "source actor silhouette remains behind the replacement"
    elif lower_body_failed:
        reason = "replacement is only a face layer; the V1 body remains underneath"
    elif wardrobe_failed:
        stalled_region = (
            f"the {wardrobe_binding_region} half of the body region"
            if wardrobe_binding_region != "whole" else "the body region"
        )
        reason = (
            "replacement is only a head/face layer; the V1 wardrobe still fills "
            f"{stalled_region} (shift {float(wardrobe_shift or 0.0):.3f} below "
            f"floor {wardrobe_floor:.2f})"
        )
    elif plate_failed:
        reason = "output drifted away from the selected V1 Shot/plate"
    elif silent_mouth_failed:
        reason = "authored Silent Listener mouth shows excessive articulation"
    elif target_similarity_failed:
        reason = (
            "output palette never matches the target P Picture "
            f"(similarity {float(target_reference_audit['similarity']):.3f} "
            f"below floor {target_similarity_floor:.2f})"
        )
    else:
        reason = "selected identity changed and authored mouth state is stable"

    # Takes that clear the hard floor but land inside a narrow warning band stay
    # assembled and are only flagged.  The cue is a colour histogram, so
    # borderline scores are expected whenever Picture 1 is a flat-background
    # cartoon cut-out; flagging keeps the signal honest without spending another
    # H3 generation on a metric that cannot see facial identity.
    target_similarity_review = False
    if (
        not failed
        and target_reference_audit.get("available")
        and target_reference_audit.get("similarity") is not None
        and target_similarity_floor > 0.0
        and float(target_reference_audit["similarity"])
        < target_similarity_floor + TARGET_SIMILARITY_WARNING_BAND
    ):
        target_similarity_review = True

    if not failed and identity_ambiguity_rows:
        reason += " (audit region ambiguous: near-static V1-matching strip with low target likeness; kept for review)"
    if target_similarity_ambiguous:
        reason += (
            " (target P Picture floor downgraded: the audited strip is a near-static"
            " plate region, so low target likeness is flagged rather than failed)"
        )
    if target_similarity_review:
        reason += " (target P Picture similarity inside the warning band; verify before accepting)"
    if blocking_cause == "target_reference_temporal_collapse":
        # Round 92: name the frame that decided the retry, so the manifest reads
        # like what the director saw ("the swap fell out around 7 s") instead of
        # like an average that cleared the floor.
        reason += (
            " (target P Picture likeness collapses to "
            f"{float(target_reference_audit.get('minimum_similarity') or 0.0):.3f} at "
            f"{float(target_reference_audit.get('worst_timestamp_seconds') or 0.0):.2f}s, "
            f"below floor {CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR:.2f}, while the "
            f"median {float(target_reference_audit.get('similarity') or 0.0):.3f} clears it)"
        )
    return {
        "passed": not failed,
        "available": True,
        "reason": reason,
        "action": "retry_fresh_seed" if failed else "accept",
        "blocking": blocking_head_layer,
        "blocking_cause": blocking_cause,
        "head_layer_only": head_layer_only,
        "head_layer_similarity_floor": CHARACTER_SWAP_HEAD_LAYER_SIMILARITY_FLOOR,
        "retention_score": round(float(retention_score), 6),
        "quality_risk_score": round(float(quality_risk_score), 6),
        "target_reference_similarity": target_reference_audit.get("similarity"),
        "target_reference_audit": target_reference_audit,
        "wardrobe_shift": wardrobe_shift,
        # Policy 80: tail-window measurement of the same cue, kept beside the
        # median so a manifest can show which window decided a retry.
        "wardrobe_shift_late": wardrobe_shift_late,
        "wardrobe_audit": wardrobe_audit,
        "wardrobe_audit_failed": wardrobe_failed,
        "target_similarity_review": target_similarity_review,
        "target_similarity_ambiguous": target_similarity_ambiguous,
        "plate_strip_ambiguous": plate_strip_ambiguous,
        "minimum_target_reference_similarity": round(target_similarity_floor, 6),
        "target_similarity_failed": target_similarity_failed,
        "roles": role_results,
        "complete_actor_erasure_audit": {
            "passed": not erasure_failed,
            "rows": erasure_rows,
        },
        "whole_character_integration_audit": {
            "checked": bool(lower_body_rows),
            "passed": not lower_body_failed,
            "rows": lower_body_rows,
        },
        "source_plate_continuity_audit": {
            "checked": len(plate_rows) >= 2,
            "passed": not plate_failed,
            "rows": plate_rows,
        },
        "silent_mouth_audit": silent_mouth_result,
        "identity_audit_ambiguity": {
            "checked": bool(identity_ambiguity_rows),
            "rows": identity_ambiguity_rows,
        },
    }


def _assembly_canvas(ffprobe: Path, paths: list[Path]) -> tuple[int, int] | None:
    """Choose a stable concat canvas from the dominant source geometry.

    Count wins first so a single unusually large relay frame cannot upscale an
    otherwise uniform job.  Equal counts prefer the larger canvas, retaining
    the intended H3 quality in a mixed H3/V1 pair.  libx264/yuv420p requires
    even dimensions, so odd source dimensions are rounded up by one pixel.
    """

    counts: dict[tuple[int, int], int] = {}
    for path in paths:
        geometry = _probe_video_geometry(ffprobe, path)
        if geometry is not None:
            counts[geometry] = counts.get(geometry, 0) + 1
    if not counts:
        return None
    width, height = max(
        counts,
        key=lambda geometry: (
            counts[geometry], geometry[0] * geometry[1], geometry[0], geometry[1]
        ),
    )
    return width + (width % 2), height + (height % 2)


def canvas_for_megapixels(
    geometry: tuple[int, int] | None,
    megapixels: float,
) -> tuple[int, int] | None:
    """Fit a source canvas inside an exact megapixel budget without distortion."""

    if geometry is None or megapixels <= 0.0:
        return geometry
    width, height = geometry
    area_limit = max(4.0, float(megapixels) * 1_000_000.0)
    if width * height <= area_limit:
        return width + (width % 2), height + (height % 2)
    scale = math.sqrt(area_limit / float(width * height))
    fitted_width = max(2, int(math.floor(width * scale / 2.0)) * 2)
    fitted_height = max(2, int(math.floor(height * scale / 2.0)) * 2)
    while fitted_width * fitted_height > area_limit:
        if fitted_width >= fitted_height and fitted_width > 2:
            fitted_width -= 2
        elif fitted_height > 2:
            fitted_height -= 2
        else:
            break
    return fitted_width, fitted_height


PREVIEW_CANVAS_MULTIPLE = 16


def quantize_canvas_to_multiple(
    geometry: tuple[int, int] | None,
    multiple: int = PREVIEW_CANVAS_MULTIPLE,
) -> tuple[int, int] | None:
    """Snap a canvas down to a common multiple of both edges.

    ``rtx_vsr_output`` doubles whatever the Relay published, and a 2x of an
    480-bucket frame is 576x866 - even, therefore legal for libx264, and still two
    rows away from every H3 bucket frame, which is 576x864.  A Preview master built
    on the dominant geometry then inherits the enhancer's oddball canvas: the file
    the director judges is not the resolution of the take that was judged, and in a
    mixed job the untouched segments arrive pillarboxed.  Every H3 bucket edge is a
    multiple of 16, so rounding a Preview canvas down to that grid removes the
    enhancer's fingerprint and is a no-op on any take that never went through it.
    """

    if geometry is None:
        return None
    step = max(1, int(multiple))
    width, height = geometry
    return (
        max(step, (int(width) // step) * step),
        max(step, (int(height) // step) * step),
    )


def preview_canvas(job: dict, ffprobe: Path, paths: list[Path]) -> tuple[int, int] | None:
    """Return the actual Studio Preview canvas (not the Relay inference size).

    Round 69: the answer is quantised to the 16-pixel grid H3 itself publishes, so
    one RTX-enhanced Segment cannot decide the resolution of the whole assembled
    ``generated_preview.mp4``.  Production renders keep the dominant geometry as
    measured, because they never run the enhancer.
    """

    base = _assembly_canvas(ffprobe, paths)
    if str(job.get("request_kind") or "").casefold() != "preview":
        return base
    fitted = canvas_for_megapixels(
        quantize_canvas_to_multiple(base),
        float(job.get("megapixels", 0.0) or 0.0),
    )
    return quantize_canvas_to_multiple(fitted)


def _decoded_audio_envelope(
    ffmpeg: Path,
    source: Path,
    *,
    duration_seconds: float,
    sample_rate: int = 8000,
    bucket_seconds: float = 0.01,
) -> list[float]:
    """Decode a compact mono amplitude envelope for timing-only comparison."""

    completed = subprocess.run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-map", "0:a:0", "-t", f"{max(0.01, duration_seconds):.6f}",
            "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "pipe:1",
        ],
        capture_output=True,
        timeout=max(60, int(max(1.0, duration_seconds) * 4)),
    )
    if completed.returncode or not completed.stdout:
        raise RuntimeError(
            "Could not decode source-audio timing envelope: "
            + completed.stderr.decode("utf-8", errors="replace")[-600:]
        )
    samples = array("h")
    samples.frombytes(completed.stdout[: len(completed.stdout) // 2 * 2])
    if sys.byteorder != "little":
        samples.byteswap()
    bucket = max(1, round(sample_rate * bucket_seconds))
    envelope: list[float] = []
    for offset in range(0, len(samples), bucket):
        values = samples[offset : offset + bucket]
        if not values:
            break
        mean_abs = sum(abs(value) for value in values) / len(values)
        envelope.append(math.log1p(mean_abs))
    return envelope


def _pearson(values_a: list[float], values_b: list[float]) -> float:
    if len(values_a) < 8 or len(values_a) != len(values_b):
        return 0.0
    mean_a = sum(values_a) / len(values_a)
    mean_b = sum(values_b) / len(values_b)
    centered_a = [value - mean_a for value in values_a]
    centered_b = [value - mean_b for value in values_b]
    denominator = math.sqrt(
        sum(value * value for value in centered_a)
        * sum(value * value for value in centered_b)
    )
    if denominator <= 1e-12:
        return 0.0
    return sum(a * b for a, b in zip(centered_a, centered_b)) / denominator


def best_envelope_offset(
    expected: list[float],
    actual: list[float],
    *,
    bucket_seconds: float = 0.01,
    maximum_offset_seconds: float = 0.75,
) -> tuple[float, float]:
    """Return actual-vs-expected lag and correlation; never edits generated media."""

    maximum_lag = max(0, round(maximum_offset_seconds / bucket_seconds))
    best_lag = 0
    best_score = -2.0
    for lag in range(-maximum_lag, maximum_lag + 1):
        if lag >= 0:
            count = min(len(expected), len(actual) - lag)
            left = expected[:count]
            right = actual[lag : lag + count]
        else:
            count = min(len(expected) + lag, len(actual))
            left = expected[-lag : -lag + count]
            right = actual[:count]
        if count < 8:
            continue
        score = _pearson(left, right)
        if score > best_score:
            best_score = score
            best_lag = lag
    return round(best_lag * bucket_seconds, 6), round(max(-1.0, best_score), 6)


def audit_source_audio_timing(
    ffmpeg: Path,
    generated_video: Path,
    spec: dict,
) -> dict:
    """Measure temporal offset against A999 without retrying or rewriting a take."""

    if not spec.get("enabled"):
        return {"status": "not_requested"}
    expected_path = Path(str(spec.get("expected_path") or ""))
    duration = max(0.01, float(spec.get("authored_duration_seconds", 0.0) or 0.0))
    if not expected_path.is_file() or not generated_video.is_file():
        return {"status": "unavailable", "reason": "missing expected or generated media"}
    try:
        expected = _decoded_audio_envelope(
            ffmpeg, expected_path, duration_seconds=duration
        )
        actual = _decoded_audio_envelope(
            ffmpeg, generated_video, duration_seconds=duration
        )
        offset, correlation = best_envelope_offset(
            expected,
            actual,
            maximum_offset_seconds=float(
                spec.get("maximum_offset_seconds", 0.75) or 0.75
            ),
        )
        threshold = max(
            0.0, float(spec.get("warning_offset_seconds", 0.045) or 0.045)
        )
        reliable = correlation >= 0.35
        return {
            "status": (
                "warning" if reliable and abs(offset) > threshold
                else "ok" if reliable else "low_confidence"
            ),
            "offset_seconds": offset,
            "correlation": correlation,
            "authored_duration_seconds": duration,
            "padded_duration_seconds": float(
                spec.get("padded_duration_seconds", duration) or duration
            ),
            "action": "detect_only_no_regeneration",
        }
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        return {
            "status": "unavailable",
            "reason": str(exc),
            "action": "detect_only_no_regeneration",
        }


def build_assembly_command(
    ffmpeg: Path,
    ffprobe: Path,
    segments: list[dict],
    destination: Path,
    target_duration: float,
    *,
    canvas_override: tuple[int, int] | None = None,
) -> list[str]:
    """Build a trim/concat command that removes duplicated overlap frames."""
    paths = [Path(str(row["output_path"])) for row in segments]
    if not paths or not all(path.is_file() for path in paths):
        raise FileNotFoundError("One or more generated segment files are missing.")
    canvas = canvas_override or _assembly_canvas(ffprobe, paths)
    authoritative_audio_paths: list[Path | None] = []
    for row in segments:
        timing_spec = row.get("source_audio_timing_audit") or {}
        expected = Path(str(timing_spec.get("expected_path") or ""))
        authoritative_audio_paths.append(
            expected
            if timing_spec.get("enabled") and expected.is_file()
            else None
        )
    include_audio = all(
        authoritative is not None or _has_audio(ffprobe, path)
        for path, authoritative in zip(paths, authoritative_audio_paths)
    )
    command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y"]
    for path in paths:
        command.extend(["-i", str(path)])
    authoritative_input_indexes: list[int | None] = []
    for authoritative in authoritative_audio_paths:
        if authoritative is None:
            authoritative_input_indexes.append(None)
            continue
        authoritative_input_indexes.append(
            len(paths) + sum(index is not None for index in authoritative_input_indexes)
        )
        command.extend(["-i", str(authoritative)])

    filters: list[str] = []
    concat_inputs: list[str] = []
    for index, row in enumerate(segments):
        trim_strategy = str(row.get("assembly_trim_strategy", "overlap"))
        trim = (
            0.0
            if trim_strategy == "tail_padding_only"
            else max(0.0, float(row.get("overlap_before_seconds", 0.0)))
        )
        core_start = row.get("core_start_seconds")
        core_end = row.get("core_end_seconds")
        if core_start is None or core_end is None:
            core_duration = max(
                0.0,
                float(row.get("end_seconds", 0.0))
                - float(row.get("start_seconds", 0.0))
                - trim,
            )
        else:
            core_duration = max(0.0, float(core_end) - float(core_start))
        if core_duration <= 0.0:
            raise ValueError(f"Segment {index + 1} has no positive core duration.")
        trim_end = trim + core_duration
        video_filters = [
            f"[{index}:v]trim=start={trim:.6f}:end={trim_end:.6f}",
            "setpts=PTS-STARTPTS",
        ]
        if canvas is not None:
            width, height = canvas
            # Preserve the source composition.  Differently shaped relay
            # windows are fitted inside the dominant canvas and padded rather
            # than stretched or cropped.  setsar/fps/format also repair the
            # undefined SAR returned by some character-swap workflows.
            video_filters.extend(
                [
                    f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease:"
                    "force_divisible_by=2",
                    f"pad=w={width}:h={height}:x=(ow-iw)/2:y=(oh-ih)/2:color=black",
                    "setsar=1",
                    "fps=24",
                    "format=yuv420p",
                    "settb=AVTB",
                ]
            )
        filters.append(",".join(video_filters) + f"[v{index}]")
        concat_inputs.append(f"[v{index}]")
        if include_audio:
            authoritative_index = authoritative_input_indexes[index]
            audio_input_index = (
                authoritative_index if authoritative_index is not None else index
            )
            # A999 is already an exact segment-local soundtrack with silence
            # appended only after the authored core.  Never take H3's shifted
            # or time-warped return audio when this authoritative input exists.
            audio_trim = 0.0 if authoritative_index is not None else trim
            audio_filters = [
                f"[{audio_input_index}:a]atrim=start={audio_trim:.6f}:"
                f"end={audio_trim + core_duration:.6f}",
                "asetpts=PTS-STARTPTS",
            ]
            # Exact consecutive A999 windows come from one V1 master and must
            # meet sample-continuously.  Join fades would create audible dips
            # and alter the source timing envelope.
            fade = (
                0.0 if authoritative_index is not None
                else min(AUDIO_JOIN_FADE_SECONDS, core_duration / 4.0)
            )
            if index > 0 and fade > 0.0:
                audio_filters.append(f"afade=t=in:st=0:d={fade:.6f}")
            if index < len(segments) - 1 and fade > 0.0:
                audio_filters.append(
                    f"afade=t=out:st={max(0.0, core_duration - fade):.6f}:d={fade:.6f}"
                )
            filters.append(
                ",".join(audio_filters) + f"[a{index}]"
            )
            concat_inputs.append(f"[a{index}]")
    filters.append(
        "".join(concat_inputs)
        + f"concat=n={len(paths)}:v=1:a={1 if include_audio else 0}"
        + ("[vout][aout]" if include_audio else "[vout]")
    )
    command.extend(["-filter_complex", ";".join(filters), "-map", "[vout]"])
    if include_audio:
        command.extend(["-map", "[aout]"])
    command.extend(
        [
            "-t", f"{target_duration:.6f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
        ]
    )
    if include_audio:
        command.extend(["-c:a", "aac", "-b:a", "192k"])
    else:
        command.append("-an")
    command.extend(["-movflags", "+faststart", str(destination)])
    return command


def _suppress_windows_ffmpeg_error_dialogs() -> None:
    """Prevent a crashed FFmpeg child from blocking the worker behind a GUI dialog."""

    if sys.platform != "win32":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        current = int(kernel32.GetErrorMode())
        # SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
        kernel32.SetErrorMode(current | 0x0001 | 0x0002 | 0x8000)
    except (AttributeError, OSError, ValueError):
        pass


def _run_assembly_command(
    command: list[str],
    destination: Path,
    *,
    timeout: int,
    context: str,
) -> None:
    """Run one FFmpeg assembly phase and reject empty/crashed output."""

    _suppress_windows_ffmpeg_error_dialogs()
    destination.unlink(missing_ok=True)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "").strip()[-1200:]
        raise RuntimeError(
            f"FFmpeg {context} failed (exit {completed.returncode}): " + detail
        )
    if not destination.is_file() or destination.stat().st_size <= 0:
        raise RuntimeError(f"FFmpeg {context} returned no playable output file.")


def materialize_preview_proxy(job: dict, segment: dict, source: Path) -> Path:
    """Create the user-visible Motion Preview Segment after Relay inference.

    The review file is always aspect-preserved at the Job's own megapixel
    budget, so a Preview can never silently disagree with the canvas Studio
    estimated.  When Relay inference already lands at or above that budget
    (the 0.5MP inference tier used by the current Preview profile) the native
    output is returned untouched instead of being resampled downward.
    """

    if (
        str(job.get("request_kind") or "").casefold() != "preview"
        or float(job.get("megapixels", 0.0) or 0.0) > 0.25
        or not source.is_file()
    ):
        return source.resolve()
    ffmpeg = Path(job["ffmpeg"])
    ffprobe = Path(job["ffprobe"])
    geometry = _probe_video_geometry(ffprobe, source)
    canvas = canvas_for_megapixels(
        geometry, float(job.get("megapixels", 0.2) or 0.2)
    )
    if canvas is None:
        return source.resolve()
    width, height = canvas
    segment_id = re.sub(
        r"[^A-Za-z0-9_.-]+", "_", str(segment.get("segment_id") or "segment")
    )
    destination = Path(job["master_output"]).parent / (
        f"{segment_id}.preview_{width}x{height}.mp4"
    )
    source_geometry = _probe_video_geometry(ffprobe, source)
    if source_geometry == canvas and source.resolve() == destination.resolve():
        return source.resolve()
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", (
            f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease:"
            "force_divisible_by=2,"
            f"pad=w={width}:h={height}:x=(ow-iw)/2:y=(oh-ih)/2:color=black,"
            "setsar=1,fps=24,format=yuv420p"
        ),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        str(destination),
    ]
    _run_assembly_command(
        command,
        destination,
        timeout=max(300, int(_probe_duration(ffprobe, source) * 15)),
        context="Motion Preview Segment proxy",
    )
    return destination.resolve()


def _assembly_core_duration(row: dict) -> float:
    trim_strategy = str(row.get("assembly_trim_strategy", "overlap"))
    trim = (
        0.0
        if trim_strategy == "tail_padding_only"
        else max(0.0, float(row.get("overlap_before_seconds", 0.0)))
    )
    core_start = row.get("core_start_seconds")
    core_end = row.get("core_end_seconds")
    if core_start is not None and core_end is not None:
        return max(0.0, float(core_end) - float(core_start))
    return max(
        0.0,
        float(row.get("end_seconds", 0.0))
        - float(row.get("start_seconds", 0.0))
        - trim,
    )


def _concat_assembly_chunks_command(
    ffmpeg: Path,
    list_path: Path,
    destination: Path,
    target_duration: float,
) -> list[str]:
    return [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-t", f"{target_duration:.6f}",
        "-map", "0:v:0", "-map", "0:a:0?",
        "-c", "copy", "-movflags", "+faststart", str(destination),
    ]


def assemble_master(job: dict, segments: list[dict]) -> Path:
    destination = Path(job["master_output"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = Path(job["ffmpeg"])
    ffprobe = Path(job["ffprobe"])
    target_duration = float(job["target_duration_seconds"])
    paths = [Path(str(row["output_path"])) for row in segments]
    canvas = preview_canvas(job, ffprobe, paths)
    if len(segments) <= MAX_DIRECT_ASSEMBLY_SEGMENTS:
        emit({"progress": f"Assembling {len(segments)} segments into the master video…"})
        command = build_assembly_command(
            ffmpeg, ffprobe, segments, destination, target_duration,
            canvas_override=canvas,
        )
        _run_assembly_command(
            command, destination, timeout=1800, context="master assembly"
        )
        return destination.resolve()

    # Large one-shot filter graphs have crashed the Windows FFmpeg build after
    # every H3 Segment was already complete, leaving a zero-byte master and a
    # modal Application Error dialog. Normalize at most six inputs per batch,
    # then concatenate the compatible batches without re-encoding them again.
    # Preview is normalized to its real 0.2MP review canvas even when clean
    # 1.0MP production Segments are reused during a dirty repair.
    staging = destination.parent / (
        f".{destination.stem}.assembly-{uuid.uuid4().hex[:10]}"
    )
    staging.mkdir(parents=True, exist_ok=False)
    chunk_rows: list[dict] = []
    try:
        groups = [
            segments[offset : offset + MAX_DIRECT_ASSEMBLY_SEGMENTS]
            for offset in range(0, len(segments), MAX_DIRECT_ASSEMBLY_SEGMENTS)
        ]
        cursor = 0.0
        for group_index, group in enumerate(groups, start=1):
            chunk_duration = sum(_assembly_core_duration(row) for row in group)
            if chunk_duration <= 0.0:
                raise ValueError(
                    f"Assembly batch {group_index} has no positive duration."
                )
            chunk = staging / f"chunk_{group_index:03d}.mp4"
            first = (group_index - 1) * MAX_DIRECT_ASSEMBLY_SEGMENTS + 1
            last = first + len(group) - 1
            emit({
                "progress": (
                    f"Master assembly batch {group_index}/{len(groups)} · "
                    f"segments {first}–{last}"
                ),
                "assembly_progress": {
                    "stage": "normalizing",
                    "completed_batches": group_index - 1,
                    "total_batches": len(groups) + 1,
                },
            })
            command = build_assembly_command(
                ffmpeg,
                ffprobe,
                group,
                chunk,
                chunk_duration,
                canvas_override=canvas,
            )
            _run_assembly_command(
                command,
                chunk,
                timeout=1800,
                context=f"assembly batch {group_index}/{len(groups)}",
            )
            chunk_rows.append({
                "output_path": str(chunk),
                "start_seconds": cursor,
                "end_seconds": cursor + chunk_duration,
                "overlap_before_seconds": 0.0,
            })
            cursor += chunk_duration

        list_path = staging / "chunks.txt"
        list_path.write_text(
            "".join(
                f"file '{Path(str(row['output_path'])).name}'\n"
                for row in chunk_rows
            ),
            encoding="utf-8",
        )
        emit({
            "progress": f"Finalizing {len(groups)} assembly batches into the master video…",
            "assembly_progress": {
                "stage": "finalizing",
                "completed_batches": len(groups),
                "total_batches": len(groups) + 1,
            },
        })
        concat_command = _concat_assembly_chunks_command(
            ffmpeg, list_path, destination, target_duration
        )
        try:
            _run_assembly_command(
                concat_command,
                destination,
                timeout=900,
                context="final batch concat",
            )
        except RuntimeError:
            # Rare codec/time-base mismatch: only the small number of batches
            # enters a final filter graph, so the Windows 20+ input crash is
            # still avoided while retaining a deterministic recovery path.
            fallback = build_assembly_command(
                ffmpeg,
                ffprobe,
                chunk_rows,
                destination,
                target_duration,
                canvas_override=canvas,
            )
            _run_assembly_command(
                fallback,
                destination,
                timeout=1800,
                context="final normalized batch concat",
            )
        return destination.resolve()
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _workflow_for_attempt(
    workflow: dict,
    base_seed: int,
    attempt: int,
    *,
    strengthen_character_swap: bool = False,
) -> dict:
    """Return a deterministic retry workflow with optional identity escalation."""

    result = deepcopy(workflow)
    if attempt <= 1:
        return result
    digest = hashlib.sha256(
        f"native-speech-guard:{int(base_seed)}:{int(attempt)}".encode("utf-8")
    ).digest()
    retry_seed = int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)
    for node in result.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        if isinstance(inputs.get("noise_seed"), int):
            inputs["noise_seed"] = retry_seed
        elif isinstance(inputs.get("seed"), int):
            inputs["seed"] = retry_seed
        if strengthen_character_swap:
            lora_name = str(inputs.get("lora_name") or "").casefold()
            if "character_swap" in lora_name and isinstance(
                inputs.get("strength_model"), (int, float)
            ):
                # Fresh Seeds alone repeatedly returned the untouched V1 actor
                # on several close and medium Shots.  Escalate only the
                # Character-Swap LoRA—not the Turbo LoRA—across the existing
                # non-blocking retry budget.
                #
                # Round 49 caps that ladder at the published strength range.
                # ComfyUI /history for job preview_923011007_1793291943180178000
                # shows the old ladder reaching 1.75 and then 2.0, and the takes
                # it kept from those strengths are the ones graded 20 %-60 %
                # likeness: over-driven swap LoRAs invent an older face, extra
                # wrinkles and a different wardrobe instead of reproducing
                # Picture 1.  The authored graph already ships 1.5, so retries
                # now vary the seed only - which is what the manual ComfyUI
                # rerun does - and a template that shipped an out-of-range value
                # is pulled back inside the range instead of being escalated.
                inputs["strength_model"] = clamp_character_swap_lora_strength(
                    float(inputs["strength_model"])
                    + 0.25 * (attempt - 1)
                )
    return result


def speech_guard_result_score(result: dict) -> float:
    """Rank failed guarded takes so retry exhaustion keeps the least-bad take.

    The guard remains non-blocking, but returning the final random retry made a
    mildly imperfect first take regress into a take with a long invented line.
    Lower scores are better; a passing take always wins immediately.
    """

    if bool(result.get("passed", True)):
        return 0.0
    score = 0.0
    weights = {
        "unauthorized_speech_in_silence_window": 200.0,
        "materially_changed_or_unrelated_authored_line": 175.0,
        "unauthorized_extra_inside_authored_window": 125.0,
        "repeated_authored_phrase": 100.0,
    }
    violations = [row for row in (result.get("violations") or []) if isinstance(row, dict)]
    for row in violations:
        score += weights.get(str(row.get("kind", "")), 150.0)
        transcript = re.sub(r"\s+", "", str(row.get("transcript", "")))
        score += min(80.0, float(len(transcript)) * 2.0)
        score += min(30.0, max(0.0, float(row.get("voice_ratio", 0.0))) * 30.0)
    return score if violations else 1.0


def _start_relay_progress_watcher(
    server: str,
    client_id: str,
    segment: dict,
    prompt_ref: dict[str, str],
) -> tuple[threading.Event | None, threading.Thread | None]:
    """Forward exact H3 Relay window progress from ComfyUI's websocket.

    H3 Relay reports its adaptive-window progress through the ordinary ComfyUI
    progress event.  This observer is optional: a missing websocket dependency
    or an older server never blocks generation, and the normal history poll
    remains the completion authority.
    """

    window_count = max(1, int(segment.get("relay_window_count", 1) or 1))
    relay_node_id = str(segment.get("relay_node_id") or "").strip()
    relay_progress_mode = str(
        segment.get("relay_progress_mode") or "progress"
    ).strip().lower()
    status_prefix = str(segment.get("relay_status_prefix") or "").strip()
    if window_count <= 1 or not relay_node_id or not status_prefix:
        return None, None
    stop = threading.Event()
    ready = threading.Event()

    def observe() -> None:
        try:
            from websockets.sync.client import connect
        except Exception:
            ready.set()
            return
        endpoint = server.rstrip("/")
        if endpoint.startswith("https://"):
            endpoint = "wss://" + endpoint[len("https://"):]
        elif endpoint.startswith("http://"):
            endpoint = "ws://" + endpoint[len("http://"):]
        uri = endpoint + "/ws?clientId=" + client_id
        last_window = 1
        native_loop_windows = 0
        try:
            with connect(uri, open_timeout=3, close_timeout=1) as socket:
                ready.set()
                while not stop.is_set():
                    try:
                        raw = socket.recv(timeout=1.0)
                    except TimeoutError:
                        continue
                    if not isinstance(raw, str):
                        continue
                    try:
                        message = json.loads(raw)
                    except (TypeError, ValueError):
                        continue
                    event_type = str(message.get("type") or "")
                    data = message.get("data") or {}
                    if str(data.get("node") or "") != relay_node_id:
                        continue
                    expected_prompt = str(prompt_ref.get("prompt_id") or "")
                    event_prompt = str(data.get("prompt_id") or "")
                    if expected_prompt and event_prompt and event_prompt != expected_prompt:
                        continue
                    if relay_progress_mode == "executing":
                        if event_type != "executing":
                            continue
                        native_loop_windows += 1
                        window_index = min(
                            window_count, max(1, native_loop_windows)
                        )
                    else:
                        if event_type != "progress":
                            continue
                        try:
                            value = int(data.get("value", 0) or 0)
                            maximum = int(data.get("max", 0) or 0)
                        except (TypeError, ValueError, OverflowError):
                            continue
                        # Legacy H3RelayWindowedEdit exposes one absolute
                        # progress unit per adaptive window. Ignore sampler
                        # step bars whose maximum is unrelated.
                        if maximum != window_count:
                            continue
                        window_index = min(window_count, max(1, value))
                    if window_index <= last_window:
                        continue
                    last_window = window_index
                    emit({
                        "progress": (
                            f"{status_prefix} · Window {window_index}/{window_count}"
                        ),
                        "segment_index": segment.get("index", 0),
                        "character_swap_window": {
                            "index": window_index,
                            "count": window_count,
                        },
                    })
        except Exception:
            ready.set()
            return

    thread = threading.Thread(
        target=observe,
        name="h3-relay-progress",
        daemon=True,
    )
    thread.start()
    ready.wait(timeout=1.5)
    return stop, thread


def queue_segment(
    job: dict,
    segment: dict,
    workflow: dict,
    uploaded: list[dict],
    *,
    on_queued=None,
    speech_guard: NativeSpeechGuard | None = None,
) -> dict:
    server = job["server"].rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    attempts = max(1, min(5, int(job.get("segment_attempts", 3))))
    reconnect_timeout = max(
        1,
        int(job.get("connection_recovery_timeout", DEFAULT_RECONNECT_TIMEOUT_SECONDS)),
    )
    output_download_recovery_timeout = max(
        10,
        int(
            job.get(
                "output_download_recovery_timeout",
                DEFAULT_OUTPUT_DOWNLOAD_RECOVERY_SECONDS,
            )
        ),
    )
    last_error: Exception | None = None
    # Round 52: a Segment that dies after three attempts used to reach the
    # manifest as ``str(exc)`` only, which is how the policy-84 70-minute run
    # ended with ``[Errno 22] Invalid argument`` and no frame to explain it.
    # Every attempt's traceback is kept and travels with the Segment.
    attempt_tracebacks: list[str] = []
    resumed_prompt_id = str(segment.get("prompt_id", "")).strip()
    resume_status = str(segment.get("status", "")).strip().lower()
    resume_existing = bool(
        resumed_prompt_id
        and resume_status in {"queued", "monitoring", "reconnecting", "running"}
    )
    first_attempt = max(1, int(segment.get("attempts_used", 1) or 1))
    # A resumed Relay prompt may complete successfully but fail the post-pass
    # identity audit. Keep the remaining attempt range available so that case
    # can still receive a deterministic fresh seed without re-queuing the
    # already accepted prompt.
    attempt_range = range(first_attempt, attempts + 1)
    guarded_candidates: list[dict] = []
    identity_candidates: list[dict] = []
    for attempt in attempt_range:
        prompt_id = resumed_prompt_id if resume_existing else ""
        progress_stop: threading.Event | None = None
        progress_thread: threading.Thread | None = None
        attempt_workflow = _workflow_for_attempt(
            workflow,
            int(segment.get("seed", 0) or 0),
            attempt,
            strengthen_character_swap=bool(
                (segment.get("character_swap_identity_audit") or {}).get(
                    "enabled", False
                )
            ),
        )
        try:
            progress_label = str(segment.get("progress_label") or "").strip()
            if resume_existing:
                emit({
                    "progress": (
                        f"{progress_label} · resumed from server prompt · {prompt_id}"
                        if progress_label else
                        f"Segment {segment['index'] + 1}/{job['segment_count']} resumed from "
                        f"server prompt · {prompt_id}"
                    ),
                    "segment_index": segment["index"],
                    "connection_state": "reconnected",
                    "segment_status": {
                        "segment_id": segment["segment_id"],
                        "status": "running",
                        "prompt_id": prompt_id,
                    },
                })
            else:
                client_id = "h3-smart-render-" + uuid.uuid4().hex
                prompt_ref = {"prompt_id": ""}
                progress_stop, progress_thread = _start_relay_progress_watcher(
                    server,
                    client_id,
                    segment,
                    prompt_ref,
                )
                payload = json.dumps(
                    {
                        "prompt": attempt_workflow,
                        "client_id": client_id,
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                request = urllib.request.Request(
                    server + "/prompt",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                queued = _request_json(request, http_timeout)
                prompt_id = str(queued.get("prompt_id", ""))
                prompt_ref["prompt_id"] = prompt_id
                if not prompt_id:
                    raise RuntimeError("ComfyUI did not return a prompt_id.")
                if on_queued is not None:
                    on_queued(prompt_id, attempt, queued)
                emit({
                    "progress": (
                        f"{progress_label} · queued · {prompt_id}"
                        if progress_label else
                        f"Segment {segment['index'] + 1}/{job['segment_count']} queued · {prompt_id}"
                    ),
                    "segment_index": segment["index"],
                    "queued": queued,
                })
            history, outputs = wait_for_history(
                server,
                prompt_id,
                poll_interval=max(0.1, float(job.get("history_poll_interval", 1.0))),
                generation_timeout=effective_generation_timeout_seconds(job),
                http_timeout=http_timeout,
                reconnect_timeout=reconnect_timeout,
                segment_id=str(segment.get("segment_id", "")),
            )
            downloaded = download_outputs(
                server,
                outputs,
                Path(segment["download_dir"]),
                http_timeout,
                reconnect_timeout=reconnect_timeout,
                prompt_id=prompt_id,
                segment_id=str(segment.get("segment_id", "")),
                download_recovery_timeout=output_download_recovery_timeout,
            )
            video = _primary_video(downloaded)
            if video is None:
                raise RuntimeError(f"Segment {segment['index'] + 1} produced no downloadable video.")
            identity_audit_result: dict = {}
            best_identity: dict | None = None
            identity_attempt_table: list[dict] = []
            # Round 110: declared next to the table it travels with, not inside the branch that
            # fills it.  The Segment result reports it on every path, and a Shot that never
            # re-rolled has to say "nothing was measured" instead of failing on an unbound name.
            identity_shape_measurements: list[dict] = []
            identity_audit_spec = dict(
                segment.get("character_swap_identity_audit") or {}
            )
            # Round 52: under the lean routes the identity audit is a witness,
            # not a judge.  Every gate (source correlation, erasure gap, strict
            # temporal coverage, whole-character/wardrobe shift, silent mouth
            # motion, target-reference similarity) is still measured and lands
            # in the manifest, but none of them can spend another generation.
            # The director grades the take by eye; the numbers are for the next
            # diagnosis, not for an auto re-roll.
            identity_advisory = bool(identity_audit_spec.get("advisory_only"))
            if identity_audit_spec.get("enabled"):
                identity_audit_result = inspect_character_swap_identity(
                    Path(str(job["ffmpeg"])),
                    Path(str(job["ffprobe"])),
                    Path(str(identity_audit_spec.get("source_video_path") or "")),
                    video,
                    identity_audit_spec,
                )
                # Round 69 item 3: the one verdict the lean routes are not allowed
                # to waive.  ``blocking`` is only set when the whole-character
                # integration audit or the wardrobe audit says the replacement is a
                # head/face layer *and* the take sits far from the target P Picture,
                # which is the failure the director keeps reporting by eye.  Lifting
                # the waiver here (single decision point) makes the ordinary retry
                # branch below run, and the manifest's advisory-only flag honest
                # without touching it.
                if identity_advisory and bool(identity_audit_result.get("blocking")):
                    identity_advisory = False
                if identity_advisory:
                    identity_audit_result = dict(identity_audit_result)
                    identity_audit_result["advisory_only"] = True
                if identity_advisory and not bool(
                    identity_audit_result.get("passed", True)
                ):
                    emit({
                        "progress": (
                            f"{progress_label or ('Segment ' + str(segment['index'] + 1))} · "
                            f"identity QC advisory: {identity_audit_result.get('reason', 'verdict recorded')}"
                            " · take kept, no re-roll"
                        ),
                        "segment_index": segment["index"],
                        "character_swap_identity_audit": identity_audit_result,
                        "identity_audit_advisory": True,
                        "attempt": attempt,
                        "attempts": 1,
                    })
                elif not bool(identity_audit_result.get("passed", True)):
                    snapshot = Path(segment["download_dir"]) / (
                        f".identity_audit_attempt_{attempt}_{Path(video).name}"
                    )
                    shutil.copy2(video, snapshot)
                    identity_candidates.append({
                        "attempt": attempt,
                        "score": float(
                            identity_audit_result.get(
                                "quality_risk_score",
                                identity_audit_result.get("retention_score", 1.0),
                            )
                        ),
                        "target_reference_similarity": (
                            float(identity_audit_result["target_reference_similarity"])
                            if identity_audit_result.get("target_reference_similarity") is not None
                            else None
                        ),
                        "wardrobe_shift": (
                            float(identity_audit_result["wardrobe_shift"])
                            if identity_audit_result.get("wardrobe_shift") is not None
                            else None
                        ),
                        "wardrobe_shift_late": (
                            float(identity_audit_result["wardrobe_shift_late"])
                            if identity_audit_result.get("wardrobe_shift_late")
                            is not None else None
                        ),
                        "snapshot": snapshot,
                        "prompt_id": prompt_id,
                        "history_status": history.get("status", {}),
                        "result": deepcopy(identity_audit_result),
                    })
                    # Round 69 item 3: a blocking head-layer verdict ignores the
                    # lean pass spec's single-attempt ceiling so the take really
                    # does re-roll; the job's own segment budget still caps it, so
                    # the director sees one to two fresh-seed retries at most.
                    identity_attempts = character_swap_identity_attempt_ceiling(
                        attempts,
                        identity_audit_spec.get("maximum_attempts", 3),
                        bool(identity_audit_result.get("blocking")),
                        # Round 92: a target-reference collapse is the one
                        # head-layer class a fresh seed can repair -- the same take
                        # already showed the target character on both sides of the
                        # missed frame -- so it lifts a lean single-take spec by
                        # exactly one retry.  Every other blocking verdict still
                        # defers to the compiled spec (round 86) unless
                        # H3_CHARACTER_SWAP_BLOCKING_MAX_ATTEMPTS says otherwise.
                        character_swap_blocking_max_attempts(
                            str(identity_audit_result.get("blocking_cause") or "")
                            == "target_reference_temporal_collapse"
                        ),
                    )
                    if attempt < identity_attempts:
                        emit({
                            "progress": (
                                f"{progress_label or ('Segment ' + str(segment['index'] + 1))} · "
                                f"{identity_audit_result.get('reason', 'Character Swap QC failed')}; "
                                "retrying with a fresh seed · "
                                f"attempt {attempt + 1}/{identity_attempts}"
                            ),
                            "segment_index": segment["index"],
                            "character_swap_identity_audit": identity_audit_result,
                            "attempt": attempt,
                            "attempts": identity_attempts,
                        })
                        time.sleep(0.25)
                        continue
                    # Round 110: the creature question is asked with one predicate in three places
                    # -- the auto-box cap, the shape measurement below, and this choice -- because
                    # a Shot cannot be a creature to the box and a human to the roll picker.
                    nonhuman_pass = any(
                        _sam31_pass_is_non_human(pass_row)
                        for pass_row in (segment.get("character_swap_passes") or [])
                        if isinstance(pass_row, dict)
                    )
                    if (nonhuman_pass and len(identity_candidates) > 1
                            and character_swap_nonhuman_ranking_mode() == "shape"):
                        # Round 110: track every roll this pass generated and grade each one's
                        # silhouette against the target Picture before choosing.  One tracking job
                        # per extra roll costs about 90 s of the director's own GPU (measured at
                        # 88 s end to end on neca_6's 18:38 roll) and is paid only when a non-human
                        # pass really re-rolled -- the one moment where a wrong pick costs another
                        # 40-minute Preview.
                        emit({
                            "progress": (
                                f"{progress_label or ('Segment ' + str(segment['index'] + 1))} · "
                                f"Character Swap {len(identity_candidates)} 卷：先追踪每一卷的轮廓，"
                                "再按与目标图的相似程度选卷"
                            ),
                            "segment_index": segment["index"],
                        })
                        try:
                            identity_shape_measurements = (
                                measure_character_swap_attempt_target_shapes(
                                    job, segment, identity_candidates
                                )
                            )
                        except Exception as shape_error:  # noqa: BLE001
                            identity_shape_measurements = []
                            emit({
                                "progress": (
                                    "Character Swap 选卷测量失败，本轮改回保留第一卷："
                                    f"{type(shape_error).__name__}"
                                ),
                                "segment_index": segment["index"],
                            })
                    elif len(identity_candidates) > 1:
                        # Round 111: neca_6's 20:33 Manifest said policy 106 with no shape columns and
                        # no explanation anywhere, and the reason turned out to be a stale environment
                        # rather than the code.  A pass that re-rolled now always says out loud, in the
                        # progress line, why its rolls were never compared by silhouette.
                        skip_reason = (
                            "这一段没有非人目标，按人物的相似度选卷"
                            if not nonhuman_pass
                            else "选卷模式是 "
                            + str(character_swap_nonhuman_ranking_mode())
                            + "（H3_CHARACTER_SWAP_NONHUMAN_RANKING），没有按轮廓选卷"
                        )
                        emit({
                            "progress": (
                                f"{progress_label or ('Segment ' + str(segment['index'] + 1))} · "
                                f"Character Swap {len(identity_candidates)} 卷，保留第一卷：{skip_reason}"
                            ),
                            "segment_index": segment["index"],
                        })
                    best_identity = choose_character_swap_identity_candidate(
                        identity_candidates,
                        nonhuman_target=nonhuman_pass,
                    )
                    shutil.copy2(best_identity["snapshot"], video)
                    prompt_id = str(best_identity["prompt_id"])
                    identity_audit_result = dict(best_identity["result"])
                    history = {"status": dict(best_identity["history_status"])}
                    # Round 86 item B: keep every take and record what the ranking
                    # actually saw.  The director grades by eye, and on the
                    # pink-dress Project the eye and the colour histogram disagreed
                    # -- with the takes kept here, "the first one was the best" is
                    # a file copy instead of another fresh seed.
                    identity_attempt_table = persist_character_swap_identity_attempts(
                        segment["download_dir"],
                        identity_candidates,
                        best_identity["attempt"],
                    )
                    emit({
                        "progress": (
                            f"{progress_label or ('Segment ' + str(segment['index'] + 1))} · "
                            f"Character Swap QC retry budget exhausted; keeping target-best take "
                            f"{best_identity['attempt']} without stopping the Job"
                            + (
                                f" · {len(identity_attempt_table)} take(s) kept in "
                                f"{CHARACTER_SWAP_ATTEMPT_DIRECTORY}/"
                                if any(
                                    str(row.get("take_path", "")) for row in identity_attempt_table
                                )
                                else ""
                            )
                        ),
                        "segment_index": segment["index"],
                        "selected_identity_attempt": int(best_identity["attempt"]),
                        "identity_candidate_scores": identity_attempt_table,
                        "character_swap_identity_audit": identity_audit_result,
                    })
                else:
                    best_identity = None
                for candidate in identity_candidates:
                    Path(candidate["snapshot"]).unlink(missing_ok=True)
            speech_guard_result: dict = {}
            speech_guard_spec = dict(segment.get("native_speech_guard") or {})
            if speech_guard is not None and speech_guard_spec.get("enabled"):
                emit({
                    "progress": (
                        f"Segment {segment['index'] + 1}/{job['segment_count']} · "
                        "checking authored-line fidelity and unauthorized speech gaps"
                    ),
                    "segment_index": segment["index"],
                })
                speech_guard_result = speech_guard.inspect(video, speech_guard_spec)
                if not bool(speech_guard_result.get("passed", True)):
                    snapshot = Path(segment["download_dir"]) / (
                        f".speech_guard_attempt_{attempt}_{Path(video).name}"
                    )
                    shutil.copy2(video, snapshot)
                    guarded_candidates.append({
                        "attempt": attempt,
                        "score": speech_guard_result_score(speech_guard_result),
                        "snapshot": snapshot,
                        "prompt_id": prompt_id,
                        "history_status": history.get("status", {}),
                        "result": deepcopy(speech_guard_result),
                    })
                guard_retries = max(
                    0,
                    min(
                        attempts - 1,
                        int(
                            job.get(
                                "native_speech_guard_retries",
                                job.get("native_speech_guard_attempts", 2),
                            )
                        ),
                    ),
                )
                guard_attempts = 1 + guard_retries
                if not bool(speech_guard_result.get("passed", True)):
                    violation_preview = "; ".join(
                        str(row.get("transcript", ""))[:80]
                        for row in speech_guard_result.get("violations") or []
                    )
                    if attempt < guard_attempts and not resume_existing:
                        emit({
                            "progress": (
                                f"Segment {segment['index'] + 1}/{job['segment_count']} "
                                "contained repeated or unauthorized H3 speech; retrying with a fresh seed · "
                                + violation_preview
                            ),
                            "segment_index": segment["index"],
                            "native_speech_guard": speech_guard_result,
                            "attempt": attempt,
                            "attempts": guard_attempts,
                        })
                        time.sleep(0.25)
                        continue
                    emit({
                        "progress": (
                            f"Segment {segment['index'] + 1}/{job['segment_count']} "
                            "speech guard warning; retry budget exhausted, continuing without "
                            "Hard Block"
                        ),
                        "segment_index": segment["index"],
                        "native_speech_guard": speech_guard_result,
                    })
                    best = min(
                        guarded_candidates,
                        key=lambda row: (float(row["score"]), int(row["attempt"])),
                    )
                    shutil.copy2(best["snapshot"], video)
                    prompt_id = str(best["prompt_id"])
                    speech_guard_result = dict(best["result"])
                    history = {"status": dict(best["history_status"])}
                    emit({
                        "progress": (
                            f"Segment {segment['index'] + 1}/{job['segment_count']} "
                            f"kept guarded take {best['attempt']} as the least-risk result "
                            f"after {attempt} attempts"
                        ),
                        "segment_index": segment["index"],
                        "selected_guard_attempt": int(best["attempt"]),
                        "native_speech_guard": speech_guard_result,
                    })
                else:
                    best = None
                for candidate in guarded_candidates:
                    Path(candidate["snapshot"]).unlink(missing_ok=True)
            persisted_segment = {key: value for key, value in segment.items() if key != "workflow"}
            return {
                **persisted_segment,
                "status": "complete",
                "output_path": str(video),
                "prompt_id": prompt_id,
                "outputs": downloaded,
                "history_status": history.get("status", {}),
                "uploaded": uploaded,
                "error": "",
                "attempts_used": attempt,
                "selected_guard_attempt": (
                    int(best["attempt"]) if speech_guard_result and best is not None else attempt
                ),
                "failure_class": "",
                "native_speech_guard_result": speech_guard_result,
                "character_swap_identity_audit_result": identity_audit_result,
                # Round 86 item B: the per-attempt evidence behind the selection,
                # with the kept take on disk.  Empty when no identity QC retried.
                "identity_attempt_table": list(identity_attempt_table),
                # Round 110: what every roll of a non-human pass measured against the target
                # Picture before one of them was kept.  Empty for a human pass, for a pass that
                # never re-rolled, or when the tracking job could not run -- and that emptiness is
                # the record the director reads when the choice fell back to the first roll.
                "identity_shape_measurements": list(identity_shape_measurements),
                "selected_identity_attempt": (
                    int(best_identity["attempt"])
                    if identity_audit_result and best_identity is not None
                    else attempt
                ),
                # Retryable failures that were recovered from still get their
                # evidence into the manifest: attempt 1 blowing up and attempt
                # 2 succeeding is exactly the case that used to be invisible.
                "attempt_error_tracebacks": list(attempt_tracebacks),
            }
        except Exception as exc:
            last_error = exc
            failure_class = classify_generation_error(exc)
            attempt_tracebacks.append(
                f"attempt {attempt} · {type(exc).__name__}: {exc}\n"
                + "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                ).strip()
            )
            emit({
                "progress": f"Segment {segment['index'] + 1} attempt {attempt}/{attempts} failed: {exc}",
                "segment_index": segment["index"],
                "failure_class": failure_class,
                "attempt": attempt,
                "attempts": attempts,
                "error_traceback": attempt_tracebacks[-1],
            })
            # The remote server may still be rendering this accepted prompt.
            # Never submit a duplicate merely because the monitoring channel
            # exceeded its recovery window; preserve prompt_id for later resume.
            if isinstance(exc, ComfyConnectionRecoveryTimeout):
                raise
            if failure_class == "oom":
                released = release_comfy_memory(server, http_timeout)
                emit({
                    "progress": (
                        f"{released} · CUDA OOM retry"
                        if attempt < attempts
                        else f"{released} · CUDA OOM retry budget exhausted"
                    ),
                    "failure_class": failure_class,
                })
            else:
                emit({
                    "progress": (
                        f"H3 kept resident · retry class {failure_class}"
                        if attempt < attempts
                        else f"H3 kept resident · retry budget exhausted ({failure_class})"
                    ),
                    "failure_class": failure_class,
                })
            if attempt < attempts:
                # OOM often needs a little longer for ComfyUI/PyTorch to return
                # released allocations to the driver. Never lower megapixels
                # or silently change the accepted quality contract.
                time.sleep(2.0 if failure_class == "oom" else 1.0)
        finally:
            if progress_stop is not None:
                progress_stop.set()
            if progress_thread is not None:
                progress_thread.join(timeout=1.5)
            resume_existing = False
    exhausted = RuntimeError(str(last_error or "Unknown segment generation error"))
    # The message stays exactly one line so ``classify_generation_error`` keeps
    # matching on the failure itself rather than on a frame in the traceback.
    exhausted.attempt_tracebacks = list(attempt_tracebacks)
    raise exhausted


def uploaded_media_for_workflow(workflow: dict, uploaded: list[dict]) -> list[dict]:
    """Return only uploads actually referenced by this Segment workflow.

    Files may be uploaded once for the whole job, but the manifest is a
    mapping audit.  Recording the global upload union on every Segment made
    inactive Pictures appear active and concealed reference-slot leaks.
    """
    referenced: set[str] = set()
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue
        for value in inputs.values():
            if isinstance(value, str):
                referenced.add(value.replace("\\", "/").rsplit("/", 1)[-1])
    return [
        row for row in uploaded
        if str(row.get("upload_name") or row.get("file") or "")
        .replace("\\", "/").rsplit("/", 1)[-1] in referenced
    ]


def _workflow_string_input_for_class(
    workflow: dict,
    class_type: str,
    input_name: str,
) -> str:
    for node in workflow.values():
        if not isinstance(node, dict) or str(node.get("class_type") or "") != class_type:
            continue
        value = (node.get("inputs") or {}).get(input_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def build_sam31_multiplex_mask_workflow(
    source_filename: str,
    *,
    object_count: int,
    output_token: str,
    text_prompt: str | None = None,
    detection_threshold: float | None = None,
) -> tuple[dict[str, dict], dict[str, int]]:
    """Build one native ComfyUI SAM3.1 joint multi-person tracking graph.

    Round 104 gave the two conditioning values away from literals.  The phrase used to be
    the word ``person`` written into the graph, which is why neca_6's Godzilla pass came
    back with **no instance for the replacement at all** -- and the threshold was 0.35 for
    every role, human or not.
    """

    count = max(2, min(12, int(object_count)))
    phrase = str(text_prompt or sam31_text_prompt()).strip() or SAM31_TEXT_PROMPT_BASE
    threshold = (
        float(detection_threshold)
        if detection_threshold is not None
        else sam31_detection_threshold()
    )
    workflow: dict[str, dict] = {
        "1": {"class_type": "LoadVideo", "inputs": {"file": source_filename}},
        "2": {
            "class_type": "LabsH3PrepareVideo",
            "inputs": {"video": ["1", 0], "resolution": "480", "duration_seconds": 0},
        },
        "3": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": SAM31_MULTIPLEX_CHECKPOINT},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": phrase, "clip": ["3", 1]},
        },
        "5": {
            "class_type": "SAM3_VideoTrack",
            "inputs": {
                "images": ["2", 0],
                "model": ["3", 0],
                "conditioning": ["4", 0],
                "detection_threshold": threshold,
                "max_objects": count,
                # Every frame is inspected: brief appearances and hard cuts
                # must not inherit another actor's stale object matte.
                "detect_interval": 1,
            },
        },
    }
    save_nodes: dict[str, int] = {}
    safe_token = re.sub(r"[^A-Za-z0-9_.-]+", "_", output_token).strip("_")
    for object_index in range(count):
        base = 20 + object_index * 4
        track_id = str(base)
        image_id = str(base + 1)
        video_id = str(base + 2)
        save_id = str(base + 3)
        workflow[track_id] = {
            "class_type": "SAM3_TrackToMask",
            "inputs": {"track_data": ["5", 0], "object_indices": str(object_index)},
        }
        workflow[image_id] = {
            "class_type": "MaskToImage",
            "inputs": {"mask": [track_id, 0]},
        }
        workflow[video_id] = {
            "class_type": "CreateVideo",
            "inputs": {"images": [image_id, 0], "fps": 24.0},
        }
        workflow[save_id] = {
            "class_type": "SaveVideo",
            "inputs": {
                "video": [video_id, 0],
                "filename_prefix": (
                    f"h3-studio-sam31/{safe_token}_object{object_index:02d}"
                ),
                "format": "mp4",
                "codec": "h264",
            },
        }
        save_nodes[save_id] = object_index
    return workflow, save_nodes


def _normalized_bbox(values: object) -> list[float]:
    try:
        left, top, right, bottom = [float(value) for value in values][:4]
    except (TypeError, ValueError, OverflowError):
        return []
    if right <= left or bottom <= top:
        return []
    return [
        max(0.0, min(1.0, left)),
        max(0.0, min(1.0, top)),
        max(0.0, min(1.0, right)),
        max(0.0, min(1.0, bottom)),
    ]


def _bbox_iou(first: list[float], second: list[float]) -> float:
    if len(first) != 4 or len(second) != 4:
        return 0.0
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    first_area = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
    second_area = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union > 1e-9 else 0.0


def _mask_frame_stats(
    ffmpeg: Path,
    ffprobe: Path,
    mask_video: Path,
    *,
    sample_fps: float = 4.0,
) -> list[dict]:
    """Read sparse binary SAM frames and return normalized visible bboxes."""

    geometry = _probe_video_geometry(ffprobe, mask_video)
    if geometry is None:
        return []
    width, height = geometry
    completed = subprocess.run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(mask_video),
            "-vf", f"fps={sample_fps:.6f},format=gray", "-an", "-f", "rawvideo",
            "-pix_fmt", "gray", "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
        timeout=max(120, int(max(1.0, _probe_duration(ffprobe, mask_video)) * 20)),
    )
    if completed.returncode:
        return []
    frame_bytes = width * height
    if frame_bytes <= 0:
        return []
    from PIL import Image

    stats: list[dict] = []
    payload = completed.stdout
    for frame_index, offset in enumerate(range(0, len(payload) - frame_bytes + 1, frame_bytes)):
        frame = Image.frombytes("L", (width, height), payload[offset:offset + frame_bytes])
        # Round 106: the same binarize that the compositor applies to this mask
        # (``lut=y='if(gte(val,96),255,0)'``), kept so that a slot which only looks filled --
        # a bbox over 0.95 of the Role's box with 0.0035 of the pixels inside it -- can be
        # told apart from a matte.  A bbox alone cannot: that shell scores 0.89.
        binary = frame.point(lambda value: 255 if value >= 96 else 0)
        bbox = binary.getbbox()
        if not bbox:
            continue
        histogram = binary.histogram()
        left, top, right, bottom = bbox
        stats.append({
            "time_seconds": frame_index / sample_fps,
            "bbox_normalized": [
                left / width, top / height, right / width, bottom / height,
            ],
            "area": ((right - left) * (bottom - top)) / float(frame_bytes),
            "filled_share": histogram[255] / float(frame_bytes),
        })
    return stats


def _sam31_mask_frame_share(
    ffmpeg: Path,
    ffprobe: Path,
    mask_video: Path,
    *,
    sample_fps: float = SAM31_FRAME_LIKE_SAMPLE_FPS,
    max_frames: int = SAM31_FRAME_LIKE_MAX_FRAMES,
) -> float | None:
    """Median share of mid-gray luma in a saved SAM instance, or None when undecodable.

    ``_mask_frame_stats`` treats every luma >= 96 as filled and takes the outermost box:
    exactly right for a matte, exactly wrong for a photograph.  On neca_6's 00:11 Preview
    the multiplex node's first slot held the frame itself, and it walked into the
    association as a body covering 0.91 of the picture in all 56 samples -- and it *won*
    the Godzilla role from the only real matte (0.4517 against 0.4033).  A real matte,
    even soft after h264, puts almost nothing between 96 and 240 (measured 0.000-0.007);
    a frame puts nearly half of it there (0.440-0.558).

    A mask video that cannot be probed at all returns None rather than raising: an
    unfinished download or a truncated write is already handled downstream -- the slot
    simply has no samples -- and a diagnostic that reads the picture must never become a
    new way to fail a Segment.
    """

    geometry = _probe_video_geometry(ffprobe, mask_video)
    if geometry is None:
        return None
    width, height = geometry
    frame_bytes = width * height
    if frame_bytes <= 0:
        return None
    completed = subprocess.run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(mask_video),
            "-vf", f"fps={sample_fps:.6f},format=gray", "-an", "-f", "rawvideo",
            "-pix_fmt", "gray", "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
        timeout=max(60, int(max(1.0, _probe_duration(ffprobe, mask_video)) * 10)),
    )
    if completed.returncode:
        return None
    from PIL import Image

    payload = completed.stdout
    shares: list[float] = []
    for frame_index, offset in enumerate(
        range(0, len(payload) - frame_bytes + 1, frame_bytes)
    ):
        if frame_index >= max_frames:
            break
        frame = Image.frombytes(
            "L", (width, height), payload[offset:offset + frame_bytes]
        )
        histogram = frame.histogram()
        total = sum(histogram)
        if total <= 0:
            continue
        shares.append(
            sum(
                histogram[
                    SAM31_FRAME_LIKE_MID_GRAY_LOW:SAM31_FRAME_LIKE_MID_GRAY_HIGH + 1
                ]
            )
            / float(total)
        )
    if not shares:
        return None
    shares.sort()
    return shares[len(shares) // 2]


def _sam31_frame_like_mask(mid_gray_share) -> bool:
    """True when a saved "mask" is really the picture, not a binary matte."""

    try:
        share = float(mid_gray_share)
    except (TypeError, ValueError):
        return False
    return share >= SAM31_FRAME_LIKE_MID_GRAY_SHARE


def _sam31_collect_instance_rows(job, downloaded, save_nodes, *, source_pass_index=None):
    """Decode every saved SAM instance and refuse the ones that are not mattes.

    Returns ``(mask_rows, skipped)``.  A refused slot is reported rather than quietly
    dropped, because the reason -- "SAM3.1 returned the frame for this slot" -- is the
    difference between "no body was found" and "a fake body was preferred", and round 69
    made clear that compositing on a fake body puts the new person in the wrong place.
    """

    ffmpeg = Path(str(job["ffmpeg"]))
    ffprobe = Path(str(job["ffprobe"]))
    rows: list[dict] = []
    skipped: list[dict] = []
    for row in downloaded or []:
        node_id = str((row or {}).get("node_id") or "")
        if node_id not in save_nodes:
            continue
        path = Path(str((row or {}).get("local_path") or ""))
        if not path.is_file():
            continue
        share = _sam31_mask_frame_share(ffmpeg, ffprobe, path)
        if _sam31_frame_like_mask(share):
            skipped.append({
                "object_index": save_nodes[node_id],
                "path": str(path.resolve()),
                "mid_gray_share": round(float(share or 0.0), 4),
                "reason": (
                    "SAM3.1 returned the frame itself for this slot, not a matte "
                    f"(mid-gray share {float(share):.3f})"
                ),
            })
            continue
        entry: dict = {
            "object_index": save_nodes[node_id],
            "path": path.resolve(),
            "stats": _mask_frame_stats(ffmpeg, ffprobe, path),
        }
        if source_pass_index is not None:
            entry["source_pass_index"] = source_pass_index
        if share is not None:
            entry["mid_gray_share"] = round(float(share), 4)
        rows.append(entry)
    return rows, skipped


def _time_ranges_overlap(first: list[list[float]], second: list[list[float]]) -> bool:
    # No bounded range means the role may be visible throughout the Segment.
    if not first or not second:
        return True
    return any(
        float(a[0]) < float(b[1]) - 1e-6
        and float(a[1]) > float(b[0]) + 1e-6
        for a in first for b in second
        if len(a) >= 2 and len(b) >= 2
    )


def _sam_role_targets(passes: list[dict]) -> list[dict]:
    targets: list[dict] = []
    for pass_index, pass_row in enumerate(passes):
        role_ids = [
            str(value).strip().upper()
            for value in (
                pass_row.get("source_role_ids")
                or [pass_row.get("source_role_id")]
            )
            if str(value).strip()
        ]
        samples = [
            dict(value) for value in pass_row.get("composite_track_samples") or []
            if isinstance(value, dict)
            and len(_normalized_bbox(value.get("bbox_normalized") or [])) == 4
        ]
        raw_bboxes = [
            bbox for bbox in (
                _normalized_bbox(value)
                for value in pass_row.get("composite_bboxes_normalized") or []
            ) if bbox
        ]
        if not role_ids:
            role_ids = [f"PASS_{pass_index + 1}"]
        for role_offset, role_id in enumerate(role_ids):
            role_samples = [
                sample for sample in samples
                if str(sample.get("source_role_id") or "").strip().upper() == role_id
            ]
            candidates = [
                _normalized_bbox(sample.get("bbox_normalized") or [])
                for sample in role_samples
            ]
            candidates = [bbox for bbox in candidates if bbox]
            if not candidates and raw_bboxes:
                # Legacy jobs do not identify which box belongs to which role.
                candidates = [raw_bboxes[min(role_offset, len(raw_bboxes) - 1)]]
            ranges = [
                [float(sample.get("start_seconds", 0.0)),
                 float(sample.get("end_seconds", 0.0))]
                for sample in role_samples
                if float(sample.get("end_seconds", 0.0) or 0.0)
                > float(sample.get("start_seconds", 0.0) or 0.0)
            ]
            if not ranges:
                ranges = [
                    [float(value[0]), float(value[1])]
                    for value in pass_row.get("composite_time_ranges_seconds") or []
                    if isinstance(value, (list, tuple)) and len(value) >= 2
                ]
            targets.append({
                "pass_index": pass_index,
                "role_id": role_id,
                "samples": role_samples,
                "candidate_bboxes": candidates,
                "time_ranges": ranges,
            })
    return targets


def _sam_target_score(target: dict, stats: list[dict]) -> float:
    ranges = target.get("time_ranges") or []
    samples = target.get("samples") or []
    candidates = target.get("candidate_bboxes") or []
    frame_scores: list[float] = []
    for stat in stats:
        sample_time = float(stat.get("time_seconds", 0.0) or 0.0)
        if ranges and not any(
            float(value[0]) - 0.26 <= sample_time <= float(value[1]) + 0.26
            for value in ranges if len(value) >= 2
        ):
            continue
        expected = candidates
        if samples:
            nearest = min(
                samples,
                key=lambda row: abs(
                    float(row.get("time_seconds", 0.0) or 0.0) - sample_time
                ),
            )
            nearest_bbox = _normalized_bbox(nearest.get("bbox_normalized") or [])
            if nearest_bbox:
                expected = [nearest_bbox]
        actual = _normalized_bbox(stat.get("bbox_normalized") or [])
        if not actual or not expected:
            continue
        best = 0.0
        for bbox in expected:
            iou = _bbox_iou(actual, bbox)
            ax = (actual[0] + actual[2]) * 0.5
            ay = (actual[1] + actual[3]) * 0.5
            bx = (bbox[0] + bbox[2]) * 0.5
            by = (bbox[1] + bbox[3]) * 0.5
            center = max(0.0, 1.0 - math.hypot(ax - bx, ay - by) / math.sqrt(2.0))
            actual_area = max(1e-6, (actual[2] - actual[0]) * (actual[3] - actual[1]))
            bbox_area = max(1e-6, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
            area = min(actual_area, bbox_area) / max(actual_area, bbox_area)
            best = max(best, iou * 0.65 + center * 0.25 + area * 0.10)
        frame_scores.append(best)
    if not frame_scores:
        return 0.0
    frame_scores.sort(reverse=True)
    keep = frame_scores[:max(1, min(8, len(frame_scores)))]
    return sum(keep) / len(keep)


def _sam31_bbox_area(box: list[float]) -> float:
    return max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))


def _sam31_normalized_envelope(stats: list[dict]) -> list[float] | None:
    """Bounding envelope of one SAM instance's per-sample bboxes, normalized."""

    boxes = [
        box
        for box in (
            _normalized_bbox(row.get("bbox_normalized") or [])
            for row in stats or []
            if isinstance(row, dict)
        )
        if box
    ]
    if not boxes:
        return None
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def _sam31_bbox_containment(inner: list[float], outer: list[float]) -> float:
    """Share of ``inner`` that sits inside ``outer`` (0.0 - 1.0)."""

    inner_area = _sam31_bbox_area(inner)
    if inner_area <= 0.0:
        return 0.0
    width = min(float(inner[2]), float(outer[2])) - max(float(inner[0]), float(outer[0]))
    height = min(float(inner[3]), float(outer[3])) - max(float(inner[1]), float(outer[1]))
    if width <= 0.0 or height <= 0.0:
        return 0.0
    return (width * height) / inner_area


def _sam31_bbox_overlap(inner: list[float], outer: list[float]) -> float:
    """Intersection over union of two normalized boxes."""

    union = _sam31_bbox_area(inner) + _sam31_bbox_area(outer)
    width = min(float(inner[2]), float(outer[2])) - max(float(inner[0]), float(outer[0]))
    height = min(float(inner[3]), float(outer[3])) - max(float(inner[1]), float(outer[1]))
    if width <= 0.0 or height <= 0.0 or union <= 0.0:
        return 0.0
    intersection = width * height
    return intersection / max(1e-9, union - intersection)


def _sam31_role_expectation_boxes(target: dict, role_anchors: dict | None = None) -> list[list[float]]:
    """The box a Role's own matte should land on, widened by the V1-confirmed anchor.

    Round 103 hands the association an envelope per Role for exactly this purpose.  Judging a
    fragment against the hand-drawn box alone punishes a limb that leaves it: take R1's 5-14 s
    fragment measures spill 0.491 against the authored box ``[0.14,0.105,0.685,1.0]`` but 0.104
    against its union with R1's anchor ``[0.0205,0.0938,0.9084,1.0]``, while the rival body in
    take R2 stays at 0.405 either way (``sweep_round106_fragment_rule_neca6.py``).
    """

    role_id = str(target.get("role_id") or "").strip().upper()
    boxes = [_normalized_bbox(bbox) for bbox in (target.get("candidate_bboxes") or [])]
    boxes = [bbox for bbox in boxes if bbox]
    anchor = None
    if isinstance(role_anchors, dict):
        for key, value in role_anchors.items():
            if str(key).strip().upper() != role_id:
                continue
            anchor = _normalized_bbox(value or [])
            if anchor:
                break
    if not boxes:
        return [anchor] if anchor else []
    if not anchor:
        return boxes
    return [[
        min(min(bbox[0] for bbox in boxes), anchor[0]),
        min(min(bbox[1] for bbox in boxes), anchor[1]),
        max(max(bbox[2] for bbox in boxes), anchor[2]),
        max(max(bbox[3] for bbox in boxes), anchor[3]),
    ]]


def _sam31_mask_sample_step(stats: list[dict]) -> float:
    """Spacing of the mask sampler, read off the timestamps it produced."""

    times = sorted(
        {round(float(row.get("time_seconds", 0.0) or 0.0), 4) for row in stats or []}
    )
    deltas = [upper - lower for lower, upper in zip(times, times[1:]) if upper - lower > 1e-6]
    if not deltas:
        return 1.0 / SAM31_MASK_SAMPLE_FPS
    return max(0.05, min(1.0, min(deltas)))


def _sam31_time_ranges_from_samples(
    times: list[float], step: float, duration: float
) -> list[list[float]]:
    """Contiguous sample times into ``[from, to]`` ranges, clamped to the clip."""

    ranges: list[list[float]] = []
    for moment in sorted(float(value) for value in times):
        start = max(0.0, min(duration, moment))
        end = min(start + step, duration)
        if end <= start:
            continue
        if ranges and start <= ranges[-1][1] + 1e-6:
            ranges[-1][1] = max(ranges[-1][1], end)
        else:
            ranges.append([start, end])
    return [[round(start, 3), round(end, 3)] for start, end in ranges]


def _sam31_time_holes(
    ranges: list[list[float]], duration: float, min_gap: float = 0.4
) -> list[list[float]]:
    """Seconds inside the clip that no range covers -- the visible "nothing was pasted"."""

    holes: list[list[float]] = []
    cursor = 0.0
    for start, end in ranges:
        if float(start) - cursor > min_gap:
            holes.append([round(cursor, 3), round(float(start), 3)])
        cursor = max(cursor, float(end))
    if duration - cursor > min_gap:
        holes.append([round(cursor, 3), round(duration, 3)])
    return holes


def _sam31_mask_set_seconds(mask_rows: list[dict]) -> float:
    """How long this set of SAM slots says the clip is, from the samples it answered.

    Taken over every slot, not the winning one: a role whose matte stops early is exactly the
    case that must not be allowed to redefine the clip and hide its own tail.
    """

    seconds = 0.0
    for row in mask_rows or []:
        stats = row.get("stats") or []
        if not stats:
            continue
        times = [float(item.get("time_seconds", 0.0) or 0.0) for item in stats]
        seconds = max(seconds, max(times) + _sam31_mask_sample_step(stats))
    return round(seconds, 3)


def _sam31_slot_fragment_profile(
    stats: list[dict], expected_boxes: list[list[float]], duration: float | None = None
) -> dict:
    """Measure one SAM slot as a possible fragment of one Role, second by second.

    A sample counts only when all three hold: a matte is really in the frame
    (``filled_share``, the same luma-96 line the compositor binarizes with), the bbox lands
    on the Role's box, and the box is big enough to be that body.  Whether the slot belongs
    to this Role is then decided by the **median** over those samples rather than the best
    eight: the 07:58 run's rival body agrees with R2 on a handful of late frames (0.0079 at
    8 s through 0.545 at 12 s) and disagrees everywhere else, which is precisely what a
    best-of-eight score cannot see.
    """

    boxes = [bbox for bbox in expected_boxes if bbox]
    step = _sam31_mask_sample_step(stats)
    times = [float(row.get("time_seconds", 0.0) or 0.0) for row in stats or []]
    own_seconds = (max(times) + step) if times else 0.0
    # A slot that stops answering early must not shrink the clip: on this run take R2's
    # winning slot ends at 12.75 s while the clip runs to 14.5 s, and measuring the clip by
    # that slot's own tail is how the last 1.75 s of "nothing was pasted" would have gone
    # unreported.
    clip_seconds = max(own_seconds, float(duration or 0.0))
    accepted: list[float] = []
    ious: list[float] = []
    spills: list[float] = []
    for row in stats or []:
        try:
            filled = float(row.get("filled_share", 0.0) or 0.0)
        except (TypeError, ValueError):
            filled = 0.0
        if filled < SAM31_FRAGMENT_MIN_FILLED_SHARE:
            continue
        actual = _normalized_bbox(row.get("bbox_normalized") or [])
        if not actual:
            continue
        best_box: list[float] | None = None
        best_iou = 0.0
        for bbox in boxes:
            score = _sam31_bbox_overlap(actual, bbox)
            if score > best_iou:
                best_box, best_iou = bbox, score
        if not best_box or best_iou < SAM31_FRAGMENT_MIN_IOU:
            continue
        box_area = _sam31_bbox_area(best_box)
        if box_area <= 0.0:
            continue
        if _sam31_bbox_area(actual) / box_area < SAM31_FRAGMENT_MIN_AREA_RATIO:
            continue
        accepted.append(float(row.get("time_seconds", 0.0) or 0.0))
        ious.append(best_iou)
        spills.append(max(0.0, 1.0 - _sam31_bbox_containment(actual, best_box)))
    ordered = sorted(ious)
    ranges = _sam31_time_ranges_from_samples(accepted, step, clip_seconds)
    return {
        "sample_count": len(stats or []),
        "qualifying_samples": len(accepted),
        "sample_share": round(len(accepted) / float(len(stats)), 4) if stats else 0.0,
        "median_iou": round(ordered[len(ordered) // 2], 4) if ordered else 0.0,
        "mean_spill": round(sum(spills) / len(spills), 4) if spills else 1.0,
        "coverage_ranges_seconds": ranges,
        "coverage_seconds": round(sum(end - start for start, end in ranges), 3),
        "clip_seconds": round(clip_seconds, 3),
    }


def _sam31_union_coverage(
    profiles: list[dict], clip_seconds: float = 0.0
) -> tuple[float, list[list[float]]]:
    """Seconds covered by at least one slot, on the sampling grid the slots share."""

    duration = max(
        float(clip_seconds or 0.0),
        max((float(row.get("clip_seconds", 0.0) or 0.0) for row in profiles), default=0.0),
    )
    if duration <= 0.0:
        return 0.0, []
    bins = [False] * int(duration * SAM31_MASK_SAMPLE_FPS + 0.5)
    if not bins:
        return 0.0, []
    for profile in profiles:
        for raw in profile.get("coverage_ranges_seconds") or []:
            try:
                start, end = float(raw[0]), float(raw[1])
            except (TypeError, ValueError, IndexError):
                continue
            for index in range(
                int(start * SAM31_MASK_SAMPLE_FPS), int(end * SAM31_MASK_SAMPLE_FPS + 0.5)
            ):
                if 0 <= index < len(bins):
                    bins[index] = True
    covered = sum(1 for active in bins if active) / float(len(bins))
    ranges = _sam31_time_ranges_from_samples(
        [
            index / SAM31_MASK_SAMPLE_FPS
            for index, active in enumerate(bins)
            if active
        ],
        1.0 / SAM31_MASK_SAMPLE_FPS,
        duration,
    )
    return round(covered, 4), ranges


def _sam31_role_mask_fragments(
    target_index: int,
    targets: list[dict],
    valid_masks: list[dict],
    assigned: dict[int, int],
    role_anchors: dict | None,
    clip_seconds: float = 0.0,
) -> list[dict]:
    """The slots that carry seconds this Role's winning slot is missing (round 106).

    A slot is only accepted when it is predominantly this Role: median IoU against the
    Role's own expectation at least 0.35, no more than 0.35 of its box lying outside that
    expectation, and agreement on at least a tenth of its samples.  Those three bars are the
    sweep's reading of this run: they take in take R1's 5-14 s fragment (0.483 / 0.104 /
    0.379) and take R2's 2.5-4 s fragment (0.836 / 0.012 / 0.121), and they turn away the
    same take's other performer (0.318 / 0.405) and the V1 slots that belong to the other
    Role.  When another Role already owns a slot, this Role may still share it, but only on a
    clear margin -- round 69's rule, kept.
    """

    expected = _sam31_role_expectation_boxes(targets[target_index], role_anchors)
    if not expected:
        return []
    owner_of_mask = {int(mask_index): int(other) for other, mask_index in assigned.items()}
    own_mask = owner_of_mask.get(int(target_index), -1)
    found: list[dict] = []
    for mask_index, mask_row in enumerate(valid_masks):
        if mask_index == own_mask:
            continue
        stats = mask_row.get("stats") or []
        if not stats:
            continue
        profile = _sam31_slot_fragment_profile(stats, expected, clip_seconds)
        if profile["sample_share"] < SAM31_FRAGMENT_MIN_SAMPLE_SHARE:
            continue
        if profile["median_iou"] < SAM31_FRAGMENT_MIN_MEDIAN_IOU:
            continue
        if profile["mean_spill"] > SAM31_FRAGMENT_MAX_SPILL:
            continue
        rival_index = owner_of_mask.get(mask_index)
        if rival_index == int(target_index):
            continue
        if rival_index is not None:
            rival_expected = _sam31_role_expectation_boxes(targets[rival_index], role_anchors)
            if rival_expected:
                rival = _sam31_slot_fragment_profile(stats, rival_expected, clip_seconds)
                if (profile["median_iou"] - rival["median_iou"]) < SAM31_FRAGMENT_MIN_MARGIN:
                    continue
        found.append({
            "sam_mask_index": int(mask_index),
            "object_index": int(mask_row.get("object_index", -1)),
            **profile,
        })
    return found


def _sam31_auto_box_candidates(
    envelope: list[float], max_width: float
) -> list[list[float]]:
    """The repair ladder, tightest first, so the smallest honest box wins.

    Measured on neca_6's failed 23:37 run: the replaced performer's own envelope
    ``[0.1396,0.1055,0.6854,1.0]`` (width 0.5458, area 0.4883) scored 0.7397 over the
    pairing's 0.4795, while growing it by 0.08 on each side scored higher still (0.8031)
    but moved the win to the full-frame blob -- a higher number for the wrong body.  So
    the ladder stops at the first candidate that satisfies every guard, and no candidate
    may exceed ``max_width``, which is what keeps the hair halo armed.
    """

    left, top, right, bottom = (float(value) for value in envelope)
    width, height = right - left, bottom - top
    candidates: list[list[float]] = [
        [left, top, right, bottom],
    ]
    for pad in (0.06, 0.12):
        candidates.append(
            [
                max(0.0, left - pad),
                max(0.0, top - pad),
                min(1.0, right + pad),
                min(1.0, bottom + pad),
            ]
        )
    if width < min(1.0, max_width):
        candidates.append([left, top, min(1.0, left + min(1.0, max_width)), bottom])
    accepted: list[list[float]] = []
    seen: set[tuple[float, ...]] = set()
    for box in candidates:
        key = tuple(round(value, 4) for value in box)
        if key in seen:
            continue
        seen.add(key)
        box_width = box[2] - box[0]
        box_area = _sam31_bbox_area(box)
        if box_width > max_width + 1e-9:
            continue
        if not SAM31_AUTO_BOX_MIN_AREA <= box_area <= SAM31_AUTO_BOX_MAX_AREA:
            continue
        accepted.append([round(value, 4) for value in box])
    return accepted


def _sam31_repair_weak_association_boxes(
    passes: list[dict],
    targets: list[dict],
    valid_masks: list[dict],
    diagnostics: list[dict],
    floor: float,
    role_anchors: dict | None = None,
) -> list[dict]:
    """Re-fit a weak Role's box from the SAM instance it was already paired with.

    Round 103, and the guards are the whole point: the score is a comparison between a
    Role box and a candidate body, so simply drawing the box around whichever candidate
    won makes the number meaningless -- which is exactly the failure round 69 was written
    to prevent (a soft pairing composites one person's replacement onto another).  A
    repair is therefore accepted only when all of these hold, and each threshold is the
    number that decides the 2026-11-08 Godzilla runs:

    * the *same* SAM instance must still win (neca_6's padded candidate moved the win to
      a blob covering 0.9111 of the frame, and that candidate is refused here);
    * it must beat the runner-up by ``0.05`` (the accepted candidate measured 0.1038, the
      unrepaired pairing 0.0551 -- thin, which is why this is audited and recorded);
    * it must clear the floor itself, and stay within ``max_width`` so the halo survives;
    * it must stay on the person: inside a V1-confirmed envelope by 0.60 when the
      pre-flight left one (the repaired box measured 1.00 containment), or overlapping the
      authored box by 0.30 when it did not (measured 0.329).

    Roles whose geometry is per-sample (a real tracker) are skipped: one static envelope
    cannot represent a tracked path, and rewriting it would throw the tracker away.
    """

    repairs: list[dict] = []
    mode = sam31_auto_box_mode()
    if mode == "off":
        return repairs
    max_width = sam31_auto_box_max_width()
    nonhuman_max_width = sam31_auto_box_max_width_nonhuman()
    by_pass_index = {
        int(target.get("pass_index", -1)): target for target in targets
    }
    for row in diagnostics:
        measured = float(row.get("match_score") or 0.0)
        if measured >= floor:
            continue
        try:
            pass_row_for_role = passes[int(row.get("pass_index") or 1) - 1]
        except (TypeError, ValueError, IndexError, KeyError):
            pass_row_for_role = None
        role_is_non_human = _sam31_pass_is_non_human(pass_row_for_role)
        role_max_width = nonhuman_max_width if role_is_non_human else max_width
        record: dict = {
            "attempted": True,
            "accepted": False,
            "applied": False,
            "mode": mode,
            "measured_score": round(measured, 4),
            "floor": round(floor, 4),
            "max_width": round(role_max_width, 4),
            "target_is_non_human": role_is_non_human,
            "refused": "",
        }
        repairs.append(record)
        # The Manifest serializes the diagnostics rows, so the attempt belongs on the row:
        # a refusal that only lives in a return value is invisible to the director
        # grading the pairing later, which is exactly the hole the 23:37 run left behind.
        row["box_auto_repair"] = record
        pass_index = int(row.get("pass_index") or 1) - 1
        target = by_pass_index.get(pass_index)
        mask_row = next(
            (
                candidate
                for candidate in valid_masks
                if int(candidate.get("object_index", -1))
                == int(row.get("sam_object_index", -2))
            ),
            None,
        )
        if target is None or mask_row is None:
            record["refused"] = "no target or mask row for this pairing"
            continue
        if target.get("samples"):
            record["refused"] = "the Role is tracked per sample; one envelope cannot replace a path"
            continue
        envelope = _sam31_normalized_envelope(mask_row.get("stats") or [])
        if not envelope:
            record["refused"] = "the paired SAM instance has no measurable silhouette"
            continue
        record["sam_envelope_normalized"] = [round(value, 4) for value in envelope]
        record["refused"] = ""
        best_candidate_score: float | None = None

        def _refuse(text: str) -> None:
            """Keep the first guard that stopped a candidate, which is the honest reason.

            Without this, a containment refusal on the tight box gets buried under the next
            (looser) candidate's "it only scored 0.60" line and the director reading the
            popup blames the wrong thing.
            """

            if not record["refused"]:
                record["refused"] = text

        authored = [
            box for box in (target.get("candidate_bboxes") or []) if len(box) >= 4
        ]
        anchor = (role_anchors or {}).get(str(row.get("source_role_id")))
        accepted: tuple[list[float], float, float] | None = None
        for candidate in _sam31_auto_box_candidates(envelope, role_max_width):
            rebuilt = dict(target)
            rebuilt["candidate_bboxes"] = [candidate]
            rebuilt["samples"] = []
            scored = sorted(
                (
                    (
                        _sam_target_score(rebuilt, other.get("stats") or []),
                        index,
                    )
                    for index, other in enumerate(valid_masks)
                ),
                key=lambda item: -item[0],
            )
            if not scored:
                continue
            best_score, best_index = scored[0]
            runner_up = scored[1][0] if len(scored) > 1 else 0.0
            if best_candidate_score is None or best_score > best_candidate_score:
                best_candidate_score = best_score
            if (
                int(valid_masks[best_index].get("object_index", -1))
                != int(row.get("sam_object_index", -2))
            ):
                _refuse(
                    f"growing the box to {candidate} moved the win to SAM object "
                    f"{valid_masks[best_index].get('object_index')}, which is a different body"
                )
                break
            if best_score < floor:
                _refuse(
                    f"a box {(candidate[2] - candidate[0]):.2f} wide only scored "
                    f"{best_score:.4f} for the paired body"
                )
                continue
            if best_score - runner_up < SAM31_AUTO_BOX_MIN_MARGIN:
                _refuse(
                    f"margin over the runner-up is only {best_score - runner_up:.4f}"
                )
                continue
            if anchor and len(anchor) >= 4:
                containment = _sam31_bbox_containment(candidate, list(anchor))
                record["v1_anchor_containment"] = round(containment, 4)
                if containment < SAM31_AUTO_BOX_MIN_ANCHOR_CONTAINMENT:
                    _refuse(
                        f"the repaired box leaves the V1-confirmed region "
                        f"(containment {containment:.2f})"
                    )
                    continue
            elif authored:
                overlap = _sam31_bbox_overlap(candidate, [float(v) for v in authored[0][:4]])
                record["authored_box_overlap"] = round(overlap, 4)
                if overlap < SAM31_AUTO_BOX_MIN_AUTHORED_OVERLAP:
                    _refuse(
                        f"the repaired box left the authored region (overlap {overlap:.2f})"
                    )
                    continue
            accepted = (candidate, best_score, best_score - runner_up)
            break
        if best_candidate_score is not None:
            record["best_candidate_score"] = round(best_candidate_score, 4)
        if accepted is None and not record["refused"]:
            cap_note = (
                f" (the non-human cap {SAM31_AUTO_BOX_NONHUMAN_MAX_WIDTH_ENV})"
                if role_is_non_human
                else ""
            )
            record["refused"] = (
                "no candidate box fitted the size band "
                f"[{SAM31_AUTO_BOX_MIN_AREA}, {SAM31_AUTO_BOX_MAX_AREA}] within width "
                f"{role_max_width:.2f}{cap_note}"
            )
        if accepted is None:
            continue
        candidate, best_score, margin = accepted
        record.update(
            {
                "accepted": True,
                "from": [round(float(v), 4) for v in authored[0][:4]] if authored else [],
                "to": [round(float(v), 4) for v in candidate],
                "repaired_score": round(best_score, 4),
                "margin_over_runner_up": round(margin, 4),
            }
        )
        row["match_score"] = round(best_score, 4)
        record["applied"] = mode == "on"
        if mode != "on":
            continue
        try:
            pass_row = passes[pass_index]
        except (TypeError, IndexError, KeyError):
            pass_row = None
        if isinstance(pass_row, dict):
            # The compositor, the identity audit and the Manifest all read the box from
            # the pass row, so the repaired geometry is what ships and what is reported.
            pass_row["composite_bboxes_normalized"] = [list(candidate)]
            pass_row["composite_bbox_provenance"] = "sam31_auto_repaired"
    return repairs


def match_sam31_masks_to_passes(
    passes: list[dict],
    mask_rows: list[dict],
    role_anchors: dict | None = None,
) -> tuple[list[list[Path]], list[dict]]:
    """Associate anonymous SAM objects with Current Roles in space and time.

    ``role_anchors`` is the optional ``{role_id: envelope}`` map from the V1 plate that
    round 103 uses to keep an automatic box repair on the person the source evidence
    confirmed.  Without it the repair is held to the authored box instead.
    """

    targets = _sam_role_targets(passes)
    if not targets:
        raise RuntimeError("SAM3.1 has no Current Role targets to associate.")
    valid_masks = [row for row in mask_rows if row.get("stats")]
    if not valid_masks:
        raise RuntimeError("SAM3.1 found no visible person instances in this Segment.")
    ranked: list[tuple[float, int, int]] = []
    for target_index, target in enumerate(targets):
        for mask_index, mask_row in enumerate(valid_masks):
            ranked.append((
                _sam_target_score(target, mask_row.get("stats") or []),
                target_index,
                mask_index,
            ))
    ranked.sort(reverse=True)
    assigned: dict[int, int] = {}
    for score, target_index, mask_index in ranked:
        if target_index in assigned or score < 0.08:
            continue
        conflict = any(
            other_mask == mask_index
            and _time_ranges_overlap(
                targets[target_index].get("time_ranges") or [],
                targets[other_target].get("time_ranges") or [],
            )
            for other_target, other_mask in assigned.items()
        )
        if not conflict:
            assigned[target_index] = mask_index
    if len(assigned) != len(targets):
        missing = ", ".join(
            targets[index]["role_id"] for index in range(len(targets))
            if index not in assigned
        )
        raise RuntimeError(f"SAM3.1 could not associate Current Role(s): {missing}")
    by_pass: list[list[Path]] = [[] for _ in passes]
    diagnostics: list[dict] = []
    # Round 106: the winner keeps its score and its slot, and is then asked for the seconds it
    # does not actually cover.  SAM3.1 answers one body with several slots whenever the body's
    # appearance changes mid-clip; neca_6's shipped picture proved what that costs -- R1 lost
    # 6.25-11 s and R2 lost 0-5.25 s and 12.75-14 s, and the compositor pasted nothing there
    # because an empty shell of a mask has nothing to paste.
    fragments_by_target: dict[int, list[dict]] = {}
    mask_clip_seconds = _sam31_mask_set_seconds(valid_masks)
    if sam31_mask_fragments_mode() == "on":
        for target_index in assigned:
            fragments_by_target[target_index] = _sam31_role_mask_fragments(
                int(target_index), targets, valid_masks, assigned, role_anchors,
                mask_clip_seconds,
            )
    coverage_floor = sam31_min_mask_coverage_share()
    for target_index, mask_index in sorted(assigned.items()):
        target = targets[target_index]
        mask_row = valid_masks[mask_index]
        path = Path(str(mask_row["path"]))
        pass_masks = by_pass[int(target["pass_index"])]
        if path not in pass_masks:
            pass_masks.append(path)
        expected = _sam31_role_expectation_boxes(target, role_anchors)
        primary_profile = _sam31_slot_fragment_profile(
            mask_row.get("stats") or [], expected, mask_clip_seconds
        )
        fragments = fragments_by_target.get(int(target_index)) or []
        for fragment in fragments:
            fragment_row = valid_masks[int(fragment.get("sam_mask_index", -1))]
            fragment_path = Path(str(fragment_row.get("path") or ""))
            if str(fragment_path) and fragment_path not in pass_masks:
                pass_masks.append(fragment_path)
        coverage_share, coverage_ranges = _sam31_union_coverage(
            [primary_profile, *fragments], mask_clip_seconds
        )
        clip_seconds = float(mask_clip_seconds or 0.0)
        diagnostics.append({
            "source_role_id": target["role_id"],
            "pass_index": int(target["pass_index"]) + 1,
            "sam_object_index": int(mask_row["object_index"]),
            "match_score": round(
                _sam_target_score(target, mask_row.get("stats") or []), 4
            ),
            "time_ranges_seconds": target.get("time_ranges") or [],
            # What the matte really covers, in seconds: this is the line the Manifest must
            # carry, because it is the difference between "SAM3.1 is all black" and "SAM3.1
            # found the body for 6 of 14 seconds", and only one of those is the renderer's
            # fault.
            "mask_clip_seconds": round(clip_seconds, 3),
            "mask_coverage_share": coverage_share,
            "mask_coverage_seconds": round(
                sum(end - start for start, end in coverage_ranges), 3
            ),
            "mask_coverage_ranges_seconds": coverage_ranges,
            "mask_coverage_holes_seconds": _sam31_time_holes(coverage_ranges, clip_seconds),
            "mask_coverage_floor": round(coverage_floor, 4),
            "mask_coverage_low": bool(clip_seconds > 0.0 and coverage_share < coverage_floor),
            "mask_primary_coverage_share": round(
                float(primary_profile.get("coverage_seconds", 0.0) or 0.0) / clip_seconds, 4
            ) if clip_seconds > 0.0 else 0.0,
            "mask_primary_mean_spill": primary_profile["mean_spill"],
            "mask_fragment_object_indexes": [
                int(row.get("object_index", -1)) for row in fragments
            ],
            "mask_fragments": [
                {
                    "object_index": int(row.get("object_index", -1)),
                    "coverage_share": round(
                        float(row.get("coverage_seconds", 0.0) or 0.0) / clip_seconds, 4
                    ) if clip_seconds > 0.0 else 0.0,
                    "coverage_ranges_seconds": row.get("coverage_ranges_seconds") or [],
                    "median_iou": row.get("median_iou", 0.0),
                    "mean_spill": row.get("mean_spill", 1.0),
                    "sample_share": row.get("sample_share", 0.0),
                }
                for row in fragments
            ],
        })
    # Slots SAM3.1 answered with an entirely black video.  They used to be invisible in the
    # Manifest (``valid_masks`` drops them silently), which is why "the masks look all black in
    # ComfyUI" had no answer in the project: on this run three of R1's five V1 slots and two
    # of the four take slots are empty slots carrying a 0.0008 speck of white at most.
    empty_object_slots = sorted(
        {
            int(row.get("object_index", -1))
            for row in mask_rows
            if not (row.get("stats") or [])
        }
    )
    # Slots that answered with a bbox and essentially no pixels inside it.  They are what
    # "the SAM masks are all black" looks like from ComfyUI: the player shows a slot with a
    # moving box and 0.0008 of the frame filled, and neither the Manifest nor the association
    # said so, because a bbox is all ``_mask_frame_stats`` used to report.
    degenerate_object_slots = sorted(
        {
            int(row.get("object_index", -1))
            for row in mask_rows
            if (row.get("stats") or [])
            and max(
                (float(item.get("filled_share", 0.0) or 0.0) for item in row.get("stats") or []),
                default=0.0,
            ) < SAM31_FRAGMENT_MIN_FILLED_SHARE
        }
    )
    for role_row in diagnostics[:1]:
        role_row["mask_empty_object_slots"] = empty_object_slots
        role_row["mask_degenerate_object_slots"] = degenerate_object_slots
        role_row["mask_fragments_mode"] = sam31_mask_fragments_mode()
        role_row["mask_clip_seconds"] = round(float(mask_clip_seconds or 0.0), 3)
    if any(
        float(row.get("mask_coverage_share") or 0.0) < coverage_floor
        for row in diagnostics
    ):
        # Advisory by design: the shot keeps running (round 103), but the Manifest now names
        # the seconds nobody was pasted into, in the same place the pairing scores live.
        for role_row in diagnostics[:1]:
            role_row["mask_coverage_warning"] = (
                "one or more Roles have a matte covering less than "
                f"{coverage_floor:.2f} of the clip; see mask_coverage_holes_seconds"
            )
    # Round 69 item 4: every role found *a* body, but a soft score means the
    # body it found may belong to somebody else.  The manifest keeps the
    # diagnostics, so the director can see which score tripped the floor.
    # Round 102 reads the floor from the environment so the director can trade a
    # re-drawn box for a graded pairing, and prints the floor it actually used.
    # Round 103 asks the masks themselves for a better box first: neca_6's two failures
    # (R1 0.48 at 23:37, R2 0.40 at 00:11) were both cases where the pairing had found
    # the right person and the authored box was simply narrower than the generated
    # silhouette, and the repair ladder re-scored 0.4795 -> 0.7397 on the real geometry.
    floor = sam31_min_match_score()
    # The records live on the diagnostics rows (which is what the Manifest serializes), so
    # the return value is only for a caller that wants them as a list.
    _repairs = _sam31_repair_weak_association_boxes(
        passes, targets, valid_masks, diagnostics, floor, role_anchors
    )
    weak_rows = sorted(
        (
            row
            for row in diagnostics
            if float(row.get("match_score") or 0.0) < floor
        ),
        key=lambda row: float(row.get("match_score") or 0.0),
    )
    if weak_rows:
        measured = ", ".join(
            f"{row['source_role_id']} {float(row['match_score']):.2f}"
            for row in weak_rows
        )
        # A popup is the last thing the director sees, so the refusal reason and the
        # measured envelope ride along with it, not only in the Manifest.
        def _refusal(row: dict) -> str:
            record = row.get("box_auto_repair")
            if isinstance(record, dict) and record.get("refused"):
                return str(record["refused"])
            if sam31_auto_box_mode() == "off":
                return "auto-box is off"
            return "not attempted"

        evidence = "; ".join(
            f"{row['source_role_id']} auto-box: {_refusal(row)}" for row in weak_rows
        )
        raise RuntimeError(
            f"{SAM31_WEAK_MATCH_SENTINEL} Current Role(s) {measured} sat below "
            f"{floor:.2f}; draw a manual character box for this "
            "Shot instead of compositing an untrusted pairing. "
            f"Evidence: {evidence}."
        )
    if any(not values for values in by_pass):
        raise RuntimeError("SAM3.1 did not provide a mask for every Character Swap pass.")
    return by_pass, diagnostics


def queue_sam31_role_output_masks(
    job: dict,
    segment: dict,
    passes: list[dict],
    pass_outputs: list[Path],
    role_anchors: dict | None = None,
) -> tuple[list[list[Path]], list[dict], list[str]]:
    """Track the newly generated actor silhouette in every independent H3 take.

    V1 remains the spatial identity ledger only. It must never be the final
    matte because a replacement can have different hair, wardrobe, limbs and
    body proportions. Each H3 role output is therefore segmented separately;
    the V1 Current Role box merely selects the correct person inside that take.

    ``role_anchors`` (round 103) carries the per-role V1 envelopes so that a box
    re-fitted against a generated silhouette cannot walk off onto another person.
    """

    if len(passes) != len(pass_outputs):
        raise ValueError("SAM3.1 role-output tracking needs one H3 take per pass.")
    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    ffmpeg = Path(str(job["ffmpeg"]))
    ffprobe = Path(str(job["ffprobe"]))
    all_masks: list[list[Path]] = []
    all_diagnostics: list[dict] = []
    prompt_ids: list[str] = []
    segment_token = str(segment.get("segment_id") or "segment")
    for pass_index, (pass_row, role_output) in enumerate(
        zip(passes, pass_outputs)
    ):
        if not role_output.is_file():
            raise FileNotFoundError(
                f"SAM3.1 cannot inspect missing H3 role take: {role_output}"
            )
        role = str(pass_row.get("source_role_id") or f"pass{pass_index + 1}")
        upload_name = (
            f"h3sam_{segment_token}_pass_{pass_index + 1:02d}_{role}.mp4"
        )
        uploaded = upload_file(server, role_output, http_timeout, upload_name)
        remote_name = str((uploaded or {}).get("name") or upload_name)
        role_count = max(1, len(pass_row.get("source_role_ids") or []))
        workflow, save_nodes = build_sam31_multiplex_mask_workflow(
            remote_name,
            object_count=min(12, max(4, role_count + 2)),
            output_token=f"{segment_token}_generated_pass_{pass_index + 1:02d}_{role}",
            text_prompt=sam31_text_prompt(passes),
        )
        destination = (
            Path(str(segment["download_dir"]))
            / "sam31_generated_role_masks"
            / f"pass_{pass_index + 1:02d}_{role}"
        )
        prompt_id, downloaded = _queue_auxiliary_outputs(
            job,
            segment,
            workflow,
            destination,
            client_prefix="h3-sam31-role-output-",
            progress_label=(
                f"SAM3.1 generated-role mask {pass_index + 1}/{len(passes)} · {role}"
            ),
        )
        prompt_ids.append(prompt_id)
        mask_rows, skipped_instances = _sam31_collect_instance_rows(
            job, downloaded, save_nodes, source_pass_index=pass_index
        )
        pass_masks, diagnostics = match_sam31_masks_to_passes(
            [pass_row], mask_rows, role_anchors
        )
        # One place for the refusals: they describe the mask set, not a Role, and every
        # row of this call is serialized into the Manifest, so the first row carries them.
        for role_row in diagnostics[:1]:
            role_row["instance_masks_skipped"] = skipped_instances
        all_masks.append(pass_masks[0])
        all_diagnostics.extend({
            **row,
            "pass_index": pass_index + 1,
            "mask_source": "generated_role_output",
            "generated_role_output": str(role_output.resolve()),
        } for row in diagnostics)
    return all_masks, all_diagnostics, prompt_ids


def queue_sam31_v1_role_masks(
    job: dict,
    segment: dict,
    passes: list[dict],
) -> tuple[list[list[Path]], list[dict], str]:
    """Track the original V1 silhouettes that must be completely removed.

    Generated-role masks cover the replacement actor but cannot cover source
    hair, limbs or wardrobe that extend beyond that new silhouette. This
    shared V1 pass supplies the complementary half of the final union matte.
    Current Role space/time samples select only the intended V1 person, so an
    adjacent KEEP V1 actor is never unioned into the replacement layer.
    """

    if not passes:
        raise ValueError("SAM3.1 V1 tracking needs at least one role pass.")
    source = Path(str(
        ((passes[0].get("identity_audit") or {}).get("source_video_path") or "")
    ))
    if not source.is_file():
        raise FileNotFoundError(f"SAM3.1 cannot inspect missing V1 plate: {source}")
    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    ffmpeg = Path(str(job["ffmpeg"]))
    ffprobe = Path(str(job["ffprobe"]))
    segment_token = str(segment.get("segment_id") or "segment")
    upload_name = f"h3sam_{segment_token}_v1_plate.mp4"
    uploaded = upload_file(server, source, http_timeout, upload_name)
    remote_name = str((uploaded or {}).get("name") or upload_name)
    requested_roles = sum(
        max(1, len(row.get("source_role_ids") or [])) for row in passes
    )
    workflow, save_nodes = build_sam31_multiplex_mask_workflow(
        remote_name,
        object_count=min(12, max(4, requested_roles + 3)),
        output_token=f"{segment_token}_v1_source_roles",
        text_prompt=sam31_text_prompt(passes),
    )
    destination = (
        Path(str(segment["download_dir"])) / "sam31_v1_role_masks"
    )
    prompt_id, downloaded = _queue_auxiliary_outputs(
        job,
        segment,
        workflow,
        destination,
        client_prefix="h3-sam31-v1-source-",
        progress_label="SAM3.1 V1 source-silhouette masks",
    )
    mask_rows, skipped_instances = _sam31_collect_instance_rows(
        job, downloaded, save_nodes
    )
    masks, diagnostics = match_sam31_masks_to_passes(passes, mask_rows)
    # Same as the generated side: the refusals belong to the mask set, and the first
    # serialized row of this call is where the Manifest can find them.
    for role_row in diagnostics[:1]:
        role_row["instance_masks_skipped"] = skipped_instances
    return masks, [
        {
            **row,
            "mask_source": "v1_source",
            "v1_source": str(source.resolve()),
        }
        for row in diagnostics
    ], prompt_id


def sam31_v1_role_anchor_envelopes(job: dict, bundle) -> dict:
    """Per-role silhouette envelopes measured on the V1 plate, from a pre-flight bundle.

    Round 103 hands these to the after-generation association so a box re-fitted against
    a generated silhouette is held to the region the *source* evidence confirmed.  The
    bundle carries mask paths rather than stats, so the few mask videos it names are
    decoded again here -- seconds, against the 20 minutes a take costs, and only on the
    rare Segment that reaches this point.  Any trouble decoding returns what was measured
    so far, because an anchor is an extra guard, never a requirement.
    """

    anchors: dict = {}
    try:
        ffmpeg = Path(str(job["ffmpeg"]))
        ffprobe = Path(str(job["ffprobe"]))
        role_masks, role_diagnostics, _prompt_id = bundle
    except (KeyError, TypeError, ValueError):
        return anchors
    for row in role_diagnostics or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("mask_source") or "") != "v1_source":
            continue
        role_id = str(row.get("source_role_id") or "")
        if not role_id:
            continue
        try:
            paths = list(role_masks[int(row.get("pass_index", 1)) - 1])
        except (TypeError, ValueError, IndexError):
            continue
        stats: list[dict] = []
        for path in paths:
            try:
                stats.extend(_mask_frame_stats(ffmpeg, ffprobe, Path(str(path))))
            except Exception:
                continue
        envelope = _sam31_normalized_envelope(stats)
        if envelope:
            anchors[role_id] = [round(value, 4) for value in envelope]
    return anchors


def preflight_sam31_role_association(
    job: dict,
    segment: dict,
    passes: list[dict],
) -> tuple[tuple[list[list[Path]], list[dict], str] | None, dict]:
    """Run the round-69 association gate against V1 before a single take is generated.

    Round 102.  ``queue_sam31_v1_role_masks`` already judges the same pairing with the
    same floor -- it calls ``match_sam31_masks_to_passes`` -- but under policy 97 it only
    ran after every independent take had been generated and tracked, which is why a box
    that could never match cost the director the whole take: neca_5 failed at 19:00 with
    ``R3 0.36`` and at 19:29 with ``R3 0.31``, neca_6 at 21:17 with ``R1 0.52``, each one
    reported 20+ minutes after the Preview was pressed.

    This is a *necessary* condition, not a replacement for the gate on the generated
    take: H3 keeps the plate's blocking, so a role box that cannot match the source
    silhouette cannot match the replacement built on top of it either.  The generated
    silhouette is bigger and differently shaped, which can only lower the score, so a
    pairing that fails here has already failed.

    The bundle is returned so the composite stage can reuse it -- this is the same
    ComfyUI tracking job that would have run later, and reusing it saves one upload and
    one tracking pass.  Only the sentinel aborts.  Everything else the auxiliary can do
    (SAM missing, OOM, no instances found, upload refused) is recorded and ignored, and
    the composite stage re-queues V1 masks exactly as it did under policy 97, because an
    auxiliary must not be allowed to kill a render that used to run.
    """

    mode = sam31_association_preflight_mode()
    floor = sam31_min_match_score()
    record: dict = {
        "mode": mode,
        "floor": round(floor, 4),
        "before_generation": True,
        "verdict": "skipped",
        "detail": "",
        "matches": [],
        "v1_prompt_id": "",
        "reused_by_composite": False,
    }
    if mode == "off" or not passes:
        return None, record
    shot_label = str(
        next(
            (value for value in segment.get("shot_ids") or [] if str(value).strip()),
            segment.get("segment_id") or "segment",
        )
    ).strip()
    emit({
        "progress": (
            f"Segment {shot_label} · SAM3.1 association pre-flight on V1 · "
            f"{len(passes)} role layers · floor {floor:.2f}"
        ),
        "segment_index": segment.get("index", 0),
        "character_swap_association_preflight": record,
    })
    try:
        bundle = queue_sam31_v1_role_masks(job, segment, passes)
    except Exception as exc:
        record["detail"] = str(exc)
        weak = str(exc).startswith(SAM31_WEAK_MATCH_SENTINEL)
        if weak and mode == "on":
            record["verdict"] = "weak"
            raise RuntimeError(
                f"{exc} Measured on the V1 plate before generation, so no H3 take "
                f"was spent; redraw the character box or lower "
                f"{SAM31_MIN_MATCH_SCORE_ENV}."
            ) from exc
        record["verdict"] = "weak_advisory" if weak else "unavailable"
        emit({
            "progress": (
                f"Segment {shot_label} · SAM3.1 association pre-flight "
                f"{record['verdict']} · continuing · {exc}"
            ),
            "segment_index": segment.get("index", 0),
            "character_swap_association_preflight": record,
        })
        return None, record
    _masks, diagnostics, prompt_id = bundle
    record["verdict"] = "trusted"
    record["v1_prompt_id"] = str(prompt_id)
    record["reused_by_composite"] = True
    record["matches"] = [
        {
            "source_role_id": str(row.get("source_role_id") or ""),
            "sam_object_index": row.get("sam_object_index"),
            "match_score": row.get("match_score"),
        }
        for row in diagnostics
    ]
    emit({
        "progress": (
            f"Segment {shot_label} · SAM3.1 association pre-flight trusted · "
            + ", ".join(
                f"{row.get('source_role_id')} {float(row.get('match_score') or 0.0):.2f}"
                for row in diagnostics
            )
        ),
        "segment_index": segment.get("index", 0),
        "character_swap_association_preflight": record,
    })
    return bundle, record


def _character_swap_composite_bbox(pass_row: dict) -> list[float]:
    """Return one padded union box for an independently generated role pass."""

    audit = pass_row.get("identity_audit") or {}
    valid: list[list[float]] = []
    raw_bboxes = (
        pass_row.get("composite_bboxes_normalized")
        or audit.get("source_bboxes_normalized")
        or []
    )
    for raw_bbox in raw_bboxes:
        try:
            left, top, right, bottom = [float(value) for value in raw_bbox][:4]
        except (TypeError, ValueError, OverflowError):
            continue
        if right - left < 0.02 or bottom - top < 0.02:
            continue
        valid.append([
            max(0.0, left), max(0.0, top), min(1.0, right), min(1.0, bottom)
        ])
    if not valid:
        return []
    left = min(row[0] for row in valid)
    top = min(row[1] for row in valid)
    right = max(row[2] for row in valid)
    bottom = max(row[3] for row in valid)
    width, height = right - left, bottom - top
    # This is now only a permissive search region for a per-frame delta mask,
    # not the actual pasted rectangle. Expand far enough to include arms,
    # loose hair and clothing extending beyond a face/body detector box. The
    # dynamic mask below still rejects unchanged background and neighbours.
    pad_x = min(0.20, max(0.08, width * 0.65))
    pad_y = min(0.10, max(0.03, height * 0.12))
    return [
        max(0.0, left - pad_x),
        max(0.0, top - pad_y),
        min(1.0, right + pad_x),
        min(1.0, bottom + pad_y),
    ]


def _character_swap_depth_score(pass_row: dict) -> float:
    """Estimate source occlusion order: lower/background first, foreground last."""

    valid = [
        bbox for bbox in (
            _normalized_bbox(value)
            for value in pass_row.get("composite_bboxes_normalized") or []
        ) if bbox
    ]
    if not valid:
        return 0.0
    # Larger, lower bodies are normally closer to camera. This order only
    # resolves the tiny SAM feather overlap; the instance masks themselves
    # remain the primary visible-occlusion authority.
    values = []
    for left, top, right, bottom in valid:
        area = (right - left) * (bottom - top)
        values.append(area * 0.75 + bottom * 0.25)
    return max(values)


def _composite_sam31_character_swap_roles(
    job: dict,
    segment: dict,
    passes: list[dict],
    pass_outputs: list[Path],
    role_mask_videos: list[list[Path]],
    v1_role_mask_videos: list[list[Path]],
) -> Path:
    """Composite H3 takes through the union of V1 and generated silhouettes."""

    if (
        len(role_mask_videos) != len(passes)
        or len(v1_role_mask_videos) != len(passes)
        or any(not row for row in role_mask_videos)
        or any(not row for row in v1_role_mask_videos)
    ):
        raise ValueError(
            "SAM3.1 composite requires generated and V1 masks for every role pass."
        )
    source = Path(str(
        ((passes[0].get("identity_audit") or {}).get("source_video_path") or "")
    ))
    if not source.is_file() or not all(path.is_file() for path in pass_outputs):
        raise FileNotFoundError("SAM3.1 composite is missing its V1 plate or role take.")
    mask_occurrences = [
        ("generated", pass_index, mask_offset, path.resolve())
        for pass_index, values in enumerate(role_mask_videos)
        for mask_offset, path in enumerate(values)
    ] + [
        ("v1", pass_index, mask_offset, path.resolve())
        for pass_index, values in enumerate(v1_role_mask_videos)
        for mask_offset, path in enumerate(values)
    ]
    if not all(path.is_file() for _, _, _, path in mask_occurrences):
        raise FileNotFoundError("SAM3.1 composite is missing one or more instance masks.")

    ffmpeg = Path(str(job["ffmpeg"]))
    ffprobe = Path(str(job["ffprobe"]))
    geometry = _probe_video_geometry(ffprobe, source)
    if geometry is None:
        raise RuntimeError("Could not read the V1 geometry for SAM3.1 composite.")
    width, height = geometry
    width += width % 2
    height += height % 2
    duration = _probe_duration(ffprobe, source)
    if duration <= 0.0:
        raise RuntimeError("Could not read the V1 duration for SAM3.1 composite.")
    destination = Path(str(segment["download_dir"])) / (
        "character_swap_sam31_multi_role_composite.mp4"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source)
    ]
    for output in pass_outputs:
        command.extend(["-i", str(output)])
    mask_input_indexes: dict[tuple[str, int, int], int] = {}
    for mask_kind, pass_index, mask_offset, path in mask_occurrences:
        command.extend(["-i", str(path)])
        mask_input_indexes[(mask_kind, pass_index, mask_offset)] = (
            len(pass_outputs) + len(mask_input_indexes) + 1
        )

    filters = [
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,fps=24,setpts=PTS-STARTPTS,format=yuv444p[base0]"
    ]
    # Deterministic source-depth order prevents the arbitrary second H3 pass
    # from covering a nearer first role. SAM visible masks handle the actual
    # silhouettes; only their 2-3px feather overlap follows this ordering.
    ordered = sorted(
        range(len(passes)),
        key=lambda index: (_character_swap_depth_score(passes[index]), index),
    )
    current = "base0"
    emitted_labels: set[str] = set()
    for layer_number, pass_index in enumerate(ordered, start=1):
        input_index = pass_index + 1
        pass_row = passes[pass_index]
        filters.append(
            f"[{input_index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,fps=24,setpts=PTS-STARTPTS,format=rgba[role{layer_number}]"
        )
        kind_unions: dict[str, str] = {}
        if sam31_target_shape_mode() != "off":
            # Round 108: this is the only moment the take's own SAM matte, the target P Picture
            # cutout and this pass are all in one place, so the resemblance series is recorded
            # here, on the pass row the Manifest already carries.  Recorded, not enforced: the
            # retry loop that could re-roll this take ran long before SAM was asked for these
            # mattes, so ``block`` is the Manifest's verdict for the director to act on, not a
            # gate that can fail a Segment.  A diagnostic never becomes a new way to fail.
            try:
                pass_row.update(_character_swap_take_target_shape(
                    job,
                    role_mask_videos[pass_index],
                    (pass_row.get("identity_audit") or {}).get("target_reference_path"),
                    duration,
                ))
            except Exception as shape_error:  # noqa: BLE001
                pass_row["target_shape_status"] = f"error:{type(shape_error).__name__}"
        for mask_kind, role_masks in (
            ("generated", role_mask_videos[pass_index]),
            ("v1", v1_role_mask_videos[pass_index]),
        ):
            mask_labels: list[str] = []
            for mask_offset, _mask_path in enumerate(role_masks):
                mask_label = f"sam{mask_kind}{layer_number}_{mask_offset + 1}"
                filters.append(
                    f"[{mask_input_indexes[(mask_kind, pass_index, mask_offset)]}:v]"
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                    "setsar=1,fps=24,setpts=PTS-STARTPTS,format=gray,"
                    f"lut=y='if(gte(val,96),255,0)'[{mask_label}]"
                )
                mask_labels.append(mask_label)
            combined_kind = mask_labels[0]
            for mask_offset, next_label in enumerate(mask_labels[1:], start=2):
                output_label = f"sam{mask_kind}Union{layer_number}_{mask_offset}"
                filters.append(
                    f"[{combined_kind}][{next_label}]"
                    f"blend=all_mode=lighten[{output_label}]"
                )
                combined_kind = output_label
            kind_unions[mask_kind] = combined_kind
        combined = f"samV1GeneratedUnion{layer_number}"
        filters.append(
            f"[{kind_unions['v1']}][{kind_unions['generated']}]"
            f"blend=all_mode=lighten[{combined}]"
        )

        time_ranges: list[tuple[float, float]] = []
        for raw_range in pass_row.get("composite_time_ranges_seconds") or []:
            try:
                range_start, range_end = [float(value) for value in raw_range][:2]
            except (TypeError, ValueError, OverflowError):
                continue
            range_start = max(0.0, min(duration, range_start))
            range_end = max(range_start, min(duration, range_end))
            if range_end > range_start + 1e-6:
                time_ranges.append((range_start, range_end))
        mask_source = combined
        if time_ranges:
            expression = "+".join(
                f"between(t\\,{range_start:.6f}\\,{range_end:.6f})"
                for range_start, range_end in time_ranges
            )
            gate = f"samGate{layer_number}"
            gated = f"samGated{layer_number}"
            filters.extend([
                f"color=c=black:s={width}x{height}:r=24:d={duration:.6f},format=gray,"
                f"drawbox=x=0:y=0:w={width}:h={height}:color=white:t=fill:"
                f"enable='{expression}'[{gate}]",
                f"[{combined}][{gate}]blend=all_mode=multiply[{gated}]",
            ])
            mask_source = gated
        # The union covers both the old V1 body that must disappear and the
        # replacement body that may extend beyond it. ``classic`` grows that union by two
        # pixels and feathers over the grown edge; round 107 measures that as the source of
        # both complaints, so the shipped modes feather over the real edge and can re-add the
        # take's own silhouette where SAM's matte is too coarse to hold a limb.
        edge_mode = sam31_edge_mode()
        role_label = f"role{layer_number}"
        working_mask = mask_source
        if edge_mode == "classic":
            final_mask = f"samFinal{layer_number}"
            filters.append(
                f"[{mask_source}]{SAM31_CLASSIC_EDGE_CHAIN}[{final_mask}]"
            )
        else:
            if edge_mode == "soft_fill":
                plate_luma = "samPlateLuma"
                if plate_luma not in emitted_labels:
                    filters.append(
                        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                        "setsar=1,fps=24,setpts=PTS-STARTPTS,format=gray"
                        f"[{plate_luma}]"
                    )
                    emitted_labels.add(plate_luma)
                take_luma = f"samTakeLuma{layer_number}"
                role_a = f"{role_label}A"
                role_b = f"{role_label}B"
                take_diff = f"samTakeDiff{layer_number}"
                nearby = f"samNear{layer_number}"
                fill = f"samTakeFill{layer_number}"
                patched = f"samPatched{layer_number}"
                diff_floor = sam31_diff_floor()
                filters.extend([
                    f"[{role_label}]split=2[{role_a}][{role_b}]",
                    f"[{role_b}]format=gray[{take_luma}]",
                    f"[{plate_luma}][{take_luma}]blend=all_mode=difference,"
                    f"lut=y='if(gte(val,{diff_floor}),255,0)'[{take_diff}]",
                    # Only what SAM already found, plus three pixels, may be filled: the take
                    # is a different render of the same room, so its difference against the
                    # plate is not a silhouette on its own.
                    f"[{mask_source}]dilation,dilation,dilation[{nearby}]",
                    f"[{nearby}][{take_diff}]blend=all_mode=multiply[{fill}]",
                    f"[{mask_source}][{fill}]blend=all_mode=lighten[{patched}]",
                ])
                working_mask = patched
                role_label = role_a
            final_mask = f"samFinal{layer_number}"
            growth = "dilation," if edge_mode == "soft_grow" else ""
            filters.append(
                f"[{working_mask}]{growth}gblur=sigma={SAM31_EDGE_FEATHER_SIGMA}"
                f"[{final_mask}]"
            )
        masked_role = f"roleMasked{layer_number}"
        output_base = f"base{layer_number}"
        filters.extend([
            f"[{role_label}][{final_mask}]alphamerge[{masked_role}]",
            f"[{current}][{masked_role}]overlay=format=auto[{output_base}]",
        ])
        current = output_base

    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", f"[{current}]", "-map", "0:a:0?", "-t", f"{duration:.6f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(destination),
    ])
    _run_assembly_command(
        command,
        destination,
        timeout=max(900, int(duration * 45)),
        context="SAM3.1 Multiplex multi-character composite",
    )
    return destination.resolve()


def composite_independent_character_swap_roles(
    job: dict,
    segment: dict,
    passes: list[dict],
    pass_outputs: list[Path],
    role_mask_videos: list[list[Path]] | None = None,
    v1_role_mask_videos: list[list[Path]] | None = None,
) -> Path:
    """Merge independent per-role Relay results through per-frame delta masks.

    Sequential multi-character Relay passes are destructive: a later role can
    restore a previously swapped person. Each input here was generated from
    the same source plate. The selected-person rectangle is only a permissive
    search region; the actual matte follows pixels changed by that role pass and
    is active only over the role's tracked frame span. This keeps limbs outside
    the detector box while rejecting unchanged V1 actors and background.
    """

    if len(passes) != len(pass_outputs) or len(passes) < 2:
        raise ValueError("Multi-character composite requires one output per role pass.")
    if role_mask_videos is not None and v1_role_mask_videos is not None:
        return _composite_sam31_character_swap_roles(
            job,
            segment,
            passes,
            pass_outputs,
            role_mask_videos,
            v1_role_mask_videos,
        )
    source = Path(str(
        ((passes[0].get("identity_audit") or {}).get("source_video_path") or "")
    ))
    if not source.is_file() or not all(path.is_file() for path in pass_outputs):
        raise FileNotFoundError("Multi-character composite is missing its V1 plate or role take.")
    ffmpeg = Path(job["ffmpeg"])
    ffprobe = Path(job["ffprobe"])
    geometry = _probe_video_geometry(ffprobe, source)
    if geometry is None:
        raise RuntimeError("Could not read the V1 geometry for multi-character composite.")
    width, height = geometry
    width += width % 2
    height += height % 2
    duration = _probe_duration(ffprobe, source)
    if duration <= 0.0:
        raise RuntimeError("Could not read the V1 duration for multi-character composite.")
    destination = Path(str(segment["download_dir"])) / "character_swap_multi_role_composite.mp4"
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source)
    ]
    for output in pass_outputs:
        command.extend(["-i", str(output)])
    source_labels = ["base0"] + [
        f"source{index}" for index in range(1, len(pass_outputs) + 1)
    ]
    filters = [
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,fps=24,setpts=PTS-STARTPTS,format=yuv444p,"
        f"split={len(source_labels)}"
        + "".join(f"[{label}]" for label in source_labels)
    ]
    current = "base0"
    for index, (pass_row, _output) in enumerate(zip(passes, pass_outputs), start=1):
        bbox = _character_swap_composite_bbox(pass_row)
        if len(bbox) != 4:
            raise ValueError(
                "Multi-character composite needs a selected-person rectangle for every role."
            )
        left, top, right, bottom = bbox
        x = max(0, min(width - 2, round(left * width)))
        y = max(0, min(height - 2, round(top * height)))
        box_width = max(2, min(width - x, round((right - left) * width)))
        box_height = max(2, min(height - y, round((bottom - top) * height)))
        feather = max(2.0, min(10.0, min(box_width, box_height) * 0.015))
        time_ranges = []
        for raw_range in pass_row.get("composite_time_ranges_seconds") or []:
            try:
                range_start, range_end = [float(value) for value in raw_range][:2]
            except (TypeError, ValueError, OverflowError):
                continue
            range_start = max(0.0, min(duration, range_start))
            range_end = max(range_start, min(duration, range_end))
            if range_end > range_start + 1e-6:
                time_ranges.append((range_start, range_end))
        enable = ""
        if time_ranges:
            expression = "+".join(
                f"between(t\\,{range_start:.6f}\\,{range_end:.6f})"
                for range_start, range_end in time_ranges
            )
            enable = f":enable='{expression}'"
        filters.extend([
            f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,fps=24,setpts=PTS-STARTPTS,format=yuv444p,split=2"
            f"[roleColor{index}][roleDelta{index}]",
            f"[roleColor{index}]format=rgba[role{index}]",
            # Build a per-frame subject-change mask. H3 re-encodes the whole
            # frame, so low-level codec/background noise is rejected before
            # dilation closes holes inside the new body and blur feathers only
            # the real silhouette, never a rectangular slab.
            f"[source{index}][roleDelta{index}]blend=all_mode=difference,"
            "format=gray,lut=y='(val-8)*16',dilation,dilation,dilation,"
            f"gblur=sigma={feather:.3f}[delta{index}]",
            f"color=c=black:s={width}x{height}:r=24:d={duration:.6f},format=gray,"
            f"drawbox=x={x}:y={y}:w={box_width}:h={box_height}:color=white:t=fill"
            f"{enable}[roi{index}]",
            f"[delta{index}][roi{index}]blend=all_mode=multiply[mask{index}]",
            # maskedmerge applies the gray mask only to luma and leaves chroma
            # half blended on common YUV builds, producing a visible washed-out
            # rectangle. Attach the matte as a true alpha plane before overlay.
            f"[role{index}][mask{index}]alphamerge[roleMasked{index}]",
            f"[{current}][roleMasked{index}]overlay=format=auto[base{index}]",
        ])
        current = f"base{index}"
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", f"[{current}]", "-map", "0:a:0?", "-t", f"{duration:.6f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(destination),
    ])
    _run_assembly_command(
        command,
        destination,
        timeout=max(900, int(duration * 45)),
        context="independent multi-character composite",
    )
    return destination.resolve()


def queue_character_swap_passes(
    job: dict,
    segment: dict,
    uploaded: list[dict],
    *,
    on_queued=None,
) -> dict:
    """Run one Akatz Character Swap Relay pass per visible mapped role."""

    passes = [
        row for row in segment.get("character_swap_passes") or []
        if isinstance(row, dict)
    ]
    persisted = {
        key: value for key, value in segment.items()
        if key not in {"workflow", "character_swap_passes"}
    }
    persisted["character_swap_passes"] = [
        {
            key: value for key, value in row.items()
            if key != "workflow"
        }
        for row in passes
    ]
    if not passes:
        passthrough = Path(str(segment.get("passthrough_path") or ""))
        if not passthrough.is_file():
            raise FileNotFoundError(
                "Character Swap interval has no mapped role and no V1 passthrough Shot."
            )
        return {
            **persisted,
            "status": "complete",
            "output_path": str(passthrough.resolve()),
            "prompt_id": "",
            "outputs": [],
            "uploaded": [],
            "error": "",
            "attempts_used": 0,
            "failure_class": "",
        }

    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    resume_prompt_id = str(segment.get("prompt_id") or "").strip()
    resume_status = str(segment.get("status") or "").strip().lower()
    resume_active = bool(
        resume_prompt_id
        and resume_status in {"queued", "monitoring", "reconnecting", "running"}
    )
    resume_pass_index = max(
        0,
        int(segment.get("active_character_swap_pass_index", 0) or 0),
    )
    completed_pass_outputs = [
        str(path)
        for path in (segment.get("character_swap_completed_pass_outputs") or [])
        if str(path).strip()
    ]
    independent_role_mode = bool(
        len(passes) > 1
        and all(bool(row.get("independent_role_composite")) for row in passes)
        and not any(bool(row.get("runtime_source")) for row in passes)
    )
    previous_video: Path | None = None
    if resume_active and resume_pass_index > 0:
        if len(completed_pass_outputs) < resume_pass_index:
            raise RuntimeError(
                "Cannot safely resume this Character Swap pass because its preceding pass "
                "checkpoint is missing. The accepted Prompt was not re-queued."
            )
        previous_video = Path(completed_pass_outputs[resume_pass_index - 1])
        if not previous_video.is_file():
            raise FileNotFoundError(
                "Cannot safely resume this Character Swap pass because the preceding pass "
                f"output is missing: {previous_video}"
            )
    final_result: dict = {}
    identity_audit_results: list[dict] = []
    shot_label = str(
        next(
            (value for value in segment.get("shot_ids") or [] if str(value).strip()),
            segment.get("segment_id") or f"{segment.get('index', 0) + 1}",
        )
    ).strip()
    # Round 102: judge the association while the only thing at stake is one SAM
    # tracking pass, not after every independent take has been generated and
    # tracked.  A resume already has its generation in flight, so the pre-flight
    # -- and the abort it may raise -- only applies to a Segment that has not
    # started generating yet; its V1 bundle is reused by the composite stage.
    sam_preflight_v1_bundle: tuple[list[list[Path]], list[dict], str] | None = None
    sam_preflight_record: dict = {}
    sam_preflight_v1_anchors: dict = {}
    if independent_role_mode and not resume_active:
        sam_preflight_v1_bundle, sam_preflight_record = (
            preflight_sam31_role_association(job, segment, passes)
        )
        # Round 103: those same V1 masks are the anchor an automatically re-fitted box
        # must stay inside, so a repair can never walk onto the other person.
        if sam_preflight_v1_bundle is not None and sam31_auto_box_mode() != "off":
            sam_preflight_v1_anchors = sam31_v1_role_anchor_envelopes(
                job, sam_preflight_v1_bundle
            )
    for pass_index, pass_row in enumerate(passes):
        workflow = deepcopy(pass_row.get("workflow") or {})
        role = str(pass_row.get("source_role_id") or f"pass-{pass_index + 1}")
        target = str(pass_row.get("target_media_id") or "")
        relay_window_count = max(
            1, int(pass_row.get("relay_window_count", 1) or 1)
        )
        status_prefix = (
            f"Segment {shot_label} · Role {role} · "
            f"Pass {pass_index + 1}/{len(passes)}"
        )
        if resume_active and pass_index < resume_pass_index:
            previous_video = Path(completed_pass_outputs[pass_index])
            continue
        if pass_row.get("runtime_source"):
            if previous_video is None or not previous_video.is_file():
                raise RuntimeError(
                    f"Character Swap {role} requires the preceding pass output."
                )
            upload_name = (
                f"h3relay_{segment.get('segment_id', 'segment')}_"
                f"pass_{pass_index:02d}.mp4"
            )
            upload = upload_file(
                server,
                previous_video,
                http_timeout,
                upload_name,
            )
            uploaded_name = str((upload or {}).get("name") or upload_name)
            loader_id = str(pass_row.get("runtime_source_loader_node_id") or "")
            loader_input = str(
                pass_row.get("runtime_source_loader_input") or "file"
            )
            loader = workflow.get(loader_id)
            if not isinstance(loader, dict):
                raise KeyError(
                    f"Character Swap runtime source loader {loader_id} is missing."
                )
            loader.setdefault("inputs", {})[loader_input] = uploaded_name
            uploaded.append({
                "file": previous_video.name,
                "upload_name": uploaded_name,
                "result": upload,
                "runtime_character_swap_source": True,
            })
        emit({
            "progress": (
                f"{status_prefix} · Window 1/{relay_window_count}"
            ),
            "segment_index": segment["index"],
            "character_swap_pass": {
                "index": pass_index + 1,
                "count": len(passes),
                "source_role_id": role,
                "target_media_id": target,
            },
        })
        pass_segment = {
            "segment_id": (
                f"{segment.get('segment_id', 'segment')}__swap_{pass_index + 1:02d}_{role}"
            ),
            "index": segment.get("index", 0),
            "seed": int(pass_row.get("seed", segment.get("seed", 0)) or 0),
            "download_dir": str(
                Path(str(segment["download_dir"]))
                / f"character_swap_pass_{pass_index + 1:02d}_{role}"
            ),
            "native_speech_guard": {"enabled": False},
            "progress_label": (
                f"{status_prefix} · Window 1/{relay_window_count}"
            ),
            "relay_status_prefix": status_prefix,
            "relay_window_count": relay_window_count,
            "relay_node_id": str(pass_row.get("relay_node_id") or ""),
            "relay_progress_mode": str(
                pass_row.get("relay_progress_mode") or "progress"
            ),
            "character_swap_identity_audit": {
                **dict(pass_row.get("identity_audit") or {}),
                # Later serial passes must compare against the immediately
                # preceding rendered plate, not the original pre-pass V1.
                "source_video_path": str(
                    (
                        previous_video
                        if (
                            pass_row.get("runtime_source")
                            and previous_video is not None
                            and previous_video.is_file()
                        )
                        else Path(str(
                            (pass_row.get("identity_audit") or {}).get(
                                "source_video_path", ""
                            )
                        ))
                    ).resolve()
                ),
            },
        }
        if resume_active and pass_index == resume_pass_index:
            pass_segment.update(
                status="monitoring",
                prompt_id=resume_prompt_id,
                attempts_used=max(1, int(segment.get("attempts_used", 1) or 1)),
            )

        def checkpoint_character_swap_pass(
            prompt_id: str,
            attempt: int,
            queued: dict,
            *,
            _pass_index: int = pass_index,
            _role: str = role,
        ) -> None:
            # Store enough state in the outer Segment checkpoint to resume this
            # exact accepted Relay pass after a /view download interruption.
            segment["active_character_swap_pass_index"] = _pass_index
            segment["active_character_swap_source_role_id"] = _role
            segment["character_swap_completed_pass_outputs"] = list(
                completed_pass_outputs
            )
            if on_queued is not None:
                on_queued(prompt_id, attempt, queued)

        final_result = queue_segment(
            job,
            pass_segment,
            workflow,
            uploaded_media_for_workflow(workflow, uploaded),
            on_queued=checkpoint_character_swap_pass,
            speech_guard=None,
        )
        previous_video = Path(str(final_result.get("output_path") or ""))
        if not previous_video.is_file():
            raise RuntimeError(
                f"Character Swap pass {pass_index + 1} returned no video."
            )
        if len(completed_pass_outputs) <= pass_index:
            completed_pass_outputs.append(str(previous_video.resolve()))
        else:
            completed_pass_outputs[pass_index] = str(previous_video.resolve())
        identity_audit_results.append({
            "pass_index": pass_index + 1,
            "source_role_id": role,
            "target_media_id": target,
            "selected_attempt": int(
                final_result.get("selected_identity_attempt", 1) or 1
            ),
            # Round 86 item B: how many takes this Window really spent, and one
            # row per take with the numbers the ranking consumed plus the kept
            # file.  Previously only the selected audit survived, which made a
            # three-take retry look like a single measurement in the Manifest.
            "attempts_used": int(final_result.get("attempts_used", 1) or 1),
            "attempt_table": list(
                final_result.get("identity_attempt_table") or []
            ),
            **dict(
                final_result.get("character_swap_identity_audit_result") or {}
            ),
        })
        resume_active = False
        emit({
            "progress": (
                f"{status_prefix} · Window {relay_window_count}/{relay_window_count} · complete"
            ),
            "segment_index": segment["index"],
            "character_swap_pass": {
                "index": pass_index + 1,
                "count": len(passes),
                "source_role_id": role,
                "target_media_id": target,
                "window_index": relay_window_count,
                "window_count": relay_window_count,
            },
        })
    if independent_role_mode:
        role_outputs = [Path(path) for path in completed_pass_outputs[:len(passes)]]
        role_mask_videos: list[list[Path]] | None = None
        v1_role_mask_videos: list[list[Path]] | None = None
        sam_diagnostics: list[dict] = []
        sam_prompt_ids: list[str] = []
        sam_fallback_reason = ""
        emit({
            "progress": (
                f"Segment {shot_label} · SAM3.1 tracking V1 + generated silhouettes for "
                f"{len(role_outputs)} Character Swap role layers"
            ),
            "segment_index": segment["index"],
            "character_swap_composite": {
                "mode": SAM31_COMPOSITE_MODE,
                "role_count": len(role_outputs),
            },
        })
        sam_weak_action = sam31_weak_association_action()
        try:
            role_mask_videos, sam_diagnostics, sam_prompt_ids = (
                queue_sam31_role_output_masks(
                    job, segment, passes, role_outputs, sam_preflight_v1_anchors
                )
            )
            # Round 102: the pre-flight already ran this exact tracking job on this
            # plate, so the composite reuses its bundle instead of paying for a
            # second upload and a second 345-frame tracking pass.
            if sam_preflight_v1_bundle is not None:
                v1_masks, v1_diagnostics, v1_prompt_id = sam_preflight_v1_bundle
            else:
                v1_masks, v1_diagnostics, v1_prompt_id = queue_sam31_v1_role_masks(
                    job, segment, passes
                )
            v1_role_mask_videos = v1_masks
            sam_diagnostics.extend(v1_diagnostics)
            sam_prompt_ids.append(v1_prompt_id)
        except Exception as exc:
            if str(exc).startswith(SAM31_WEAK_MATCH_SENTINEL):
                # Round 103: this used to be fatal, which is how the two neca_6 takes of
                # 2026-11-08 were lost *after* both had already been generated (R1 0.48 at
                # 23:37, R2 0.40 at 00:11).  Reading the geometry back from those mask
                # videos shows why no character box could have cleared the floor: SAM
                # tracked the replaced performer for 16 of 56 sampled frames -- 0 to 3.75 s
                # of a 13.975 s clip -- and spent the rest inside one blob whose median
                # bbox was 0.9111 of the frame.  A measurement that is not following a
                # person cannot gate a composite, so the Segment now continues on the
                # delta-mask compositor, which locates a replacement by what changed
                # between a take and its own source and needs no SAM identity at all.
                # The pairing, the refusal and the measured envelopes still land in the
                # Manifest; ``H3_CHARACTER_SWAP_SAM31_WEAK_ASSOCIATION=abort`` restores
                # round 69's hard failure for a Project that wants the veto.
                if sam_weak_action == "abort":
                    raise
                sam_fallback_reason = str(exc)
            elif classify_generation_error(exc) == "oom":
                released = release_comfy_memory(server, http_timeout)
                emit({
                    "progress": (
                        f"Segment {shot_label} · SAM3.1 CUDA OOM · {released} · retrying once"
                    ),
                    "segment_index": segment["index"],
                })
                try:
                    role_mask_videos = None
                    v1_role_mask_videos = None
                    sam_diagnostics = []
                    sam_prompt_ids = []
                    role_mask_videos, sam_diagnostics, sam_prompt_ids = (
                        queue_sam31_role_output_masks(
                            job, segment, passes, role_outputs, sam_preflight_v1_anchors
                        )
                    )
                    # A bundle that already succeeded cannot be the source of this
                    # OOM, so the retry re-queues only the role-output side.
                    v1_masks, v1_diagnostics, v1_prompt_id = (
                        sam_preflight_v1_bundle
                        if sam_preflight_v1_bundle is not None
                        else queue_sam31_v1_role_masks(job, segment, passes)
                    )
                    v1_role_mask_videos = v1_masks
                    sam_diagnostics.extend(v1_diagnostics)
                    sam_prompt_ids.append(v1_prompt_id)
                except Exception as retry_exc:
                    if (
                        str(retry_exc).startswith(SAM31_WEAK_MATCH_SENTINEL)
                        and sam_weak_action == "abort"
                    ):
                        raise
                    sam_fallback_reason = str(retry_exc)
            else:
                sam_fallback_reason = str(exc)
        if sam_fallback_reason:
            emit({
                "progress": (
                    f"Segment {shot_label} · SAM3.1 instance mask unavailable; "
                    f"using H3 delta-mask fallback · {sam_fallback_reason}"
                ),
                "warning": (
                    f"Segment {shot_label} · no Character Swap mask was used: this composite is "
                    "a difference-matte fallback, so the Source performer can stay visible "
                    "behind the replacement. Lower "
                    "H3_CHARACTER_SWAP_SAM31_AUTO_BOX_MAX_WIDTH_NONHUMAN only on human shots, "
                    "or draw a manual character box."
                ),
                "segment_index": segment["index"],
                "character_swap_composite": {
                    "mode": SAM31_FALLBACK_COMPOSITE_MODE,
                    "sam31_error": sam_fallback_reason,
                    "sam31_fallback_warning": (
                        "difference-matte composite without instance masks: the Source "
                        "performer may remain visible under the replacement"
                    ),
                },
            })
        try:
            previous_video = composite_independent_character_swap_roles(
                job,
                segment,
                passes,
                role_outputs,
                role_mask_videos=role_mask_videos,
                v1_role_mask_videos=v1_role_mask_videos,
            )
        except Exception as exc:
            if role_mask_videos is None or v1_role_mask_videos is None:
                raise
            sam_fallback_reason = f"SAM3.1 compositor failed: {exc}"
            emit({
                "progress": (
                    f"Segment {shot_label} · {sam_fallback_reason} · "
                    "using H3 delta-mask fallback"
                ),
                "segment_index": segment["index"],
            })
            role_mask_videos = None
            v1_role_mask_videos = None
            previous_video = composite_independent_character_swap_roles(
                job, segment, passes, role_outputs
            )
        final_result["output_path"] = str(previous_video)
        final_result["character_swap_composite"] = {
            "mode": (
                SAM31_COMPOSITE_MODE
                if role_mask_videos is not None and v1_role_mask_videos is not None
                else SAM31_FALLBACK_COMPOSITE_MODE
            ),
            "role_count": len(role_outputs),
            "source": str(
                ((passes[0].get("identity_audit") or {}).get("source_video_path") or "")
            ),
            "role_outputs": [str(path.resolve()) for path in role_outputs],
            "sam31_checkpoint": (
                SAM31_MULTIPLEX_CHECKPOINT
                if role_mask_videos is not None and v1_role_mask_videos is not None
                else ""
            ),
            "sam31_prompt_id": sam_prompt_ids[0] if sam_prompt_ids else "",
            "sam31_prompt_ids": sam_prompt_ids,
            "sam31_mask_source": (
                "v1_plus_generated_role_outputs"
                if role_mask_videos is not None and v1_role_mask_videos is not None
                else ""
            ),
            "sam31_role_matches": sam_diagnostics,
            "sam31_mask_outputs": (
                [[str(path.resolve()) for path in values] for values in role_mask_videos]
                if role_mask_videos is not None else []
            ),
            "sam31_v1_mask_outputs": (
                [[str(path.resolve()) for path in values] for values in v1_role_mask_videos]
                if v1_role_mask_videos is not None else []
            ),
            # Round 102: what the association measured before the first take was
            # queued, and whether the composite consumed that bundle instead of
            # re-queueing the V1 tracking pass.
            "sam31_preflight": sam_preflight_record,
            "sam31_v1_masks_reused_from_preflight": bool(
                sam_preflight_v1_bundle is not None
            ),
            # Round 103: the knobs this Segment rendered under, and the V1 envelopes an
            # automatically re-fitted box was held to.  The per-role before/after boxes,
            # scores and refusal reasons ride inside each ``sam31_role_matches`` row under
            # ``box_auto_repair``, so a graded pairing can be audited without re-rendering.
            "sam31_weak_association_action": sam_weak_action,
            "sam31_auto_box_mode": sam31_auto_box_mode(),
            # Round 109: the two width caps decide whether a wide creature body can be repaired
            # at all, and a refusal that quotes only the number leaves the director guessing
            # which dial to move.  Record both, beside the mode that enabled them.
            "sam31_auto_box_max_width": round(sam31_auto_box_max_width(), 4),
            "sam31_auto_box_max_width_nonhuman": round(
                sam31_auto_box_max_width_nonhuman(), 4
            ),
            "sam31_v1_role_anchors_normalized": sam_preflight_v1_anchors,
            # Round 104: the phrase SAM3.1 was conditioned on, the confidence it was
            # asked for, and the slots that were never shown to the associator because
            # their saved video is the frame itself rather than a matte (mid-gray share
            # 0.44 against 0.00).  Each mask set carries its refusals on one row, so they
            # are collected and deduplicated here by path.
            "sam31_text_prompt": sam31_text_prompt(passes),
            "sam31_detection_threshold": sam31_detection_threshold(),
            "sam31_instance_masks_skipped": list({
                str(item.get("path") or ""): item
                for row in (sam_diagnostics or [])
                if isinstance(row, dict)
                for item in (row.get("instance_masks_skipped") or [])
                if isinstance(item, dict)
            }.values()),
            "fallback_reason": sam_fallback_reason,
        }
    # Round 52: the lean routes stamp every verdict with ``advisory_only``.
    # When all of this Segment's audits are advisory, no verdict may flip the
    # Segment to failed, because the Job already refused to spend another
    # generation on it and the director is the one who grades the take.
    identity_advisory_only = bool(identity_audit_results) and all(
        isinstance(row, dict) and bool(row.get("advisory_only"))
        for row in identity_audit_results
    )
    identity_failed = (
        not identity_advisory_only
        and any(
            bool(row.get("available", False)) and not bool(row.get("passed", True))
            for row in identity_audit_results
            if isinstance(row, dict)
        )
    )
    # A Silent Listener take whose mouth still articulates past the authored
    # motion gate is a hard failure even though the worker keeps the least-bad
    # take for review: name it so the Studio stops shipping it as clean.
    silent_mouth_hard_failed = (
        not identity_advisory_only
        and any(
            isinstance(row, dict)
            and any(
                isinstance(mrow, dict) and bool(mrow.get("violated"))
                for mrow in ((row.get("silent_mouth_audit") or {}).get("rows") or [])
            )
            for row in identity_audit_results
        )
    )
    return {
        **persisted,
        "status": "complete",
        "output_path": str(previous_video.resolve()),
        "prompt_id": str(final_result.get("prompt_id") or ""),
        "outputs": list(final_result.get("outputs") or []),
        "uploaded": list(final_result.get("uploaded") or []),
        "error": "",
        "attempts_used": int(final_result.get("attempts_used", 1) or 1),
        "failure_class": (
            "silent_mouth_excessive_articulation" if silent_mouth_hard_failed else ""
        ),
        "character_swap_identity_audits": identity_audit_results,
        "character_swap_identity_failed": identity_failed,
        "character_swap_identity_advisory_only": identity_advisory_only,
        "character_swap_composite": dict(
            final_result.get("character_swap_composite") or {}
        ),
    }


def refresh_design_env_render_knobs(job: dict) -> dict[str, str]:
    """Re-read ``design_ai.env`` when the file moved underneath the Studio that launched this job.

    Round 111: neca_6's 20:33 take is what not doing this costs.  The file already said
    ``H3_CHARACTER_SWAP_NONHUMAN_RANKING=shape``, the Manifest said policy 106, and still no roll was
    ever tracked -- the Studio had been open since before that edit, its own environment still said
    ``first``, and a spawned worker inherits that environment wholesale, new code and all.  The job
    now carries the fingerprint of the file the Studio actually read plus exactly the pairs it
    installed; when the file on disk hashes differently, only those names are refreshed, so a value the
    launcher set for the Studio stays exactly as the launcher set it -- the rule the handshake exists to
    preserve, not replace.  A worker never fails a Shot over this: an unreadable file just means the
    inherited environment stands.
    """

    provenance = job.get("design_env_knobs")
    if not isinstance(provenance, dict):
        return {}
    installed = provenance.get("installed")
    if not isinstance(installed, dict) or not installed:
        return {}
    path = str(provenance.get("path") or "").strip()
    if not path:
        return {}
    try:
        payload = Path(path).read_bytes()
    except OSError:
        return {}
    if hashlib.sha256(payload).hexdigest() == str(provenance.get("fingerprint") or ""):
        return {}
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError:
        return {}
    wanted = {str(name) for name in installed}
    from_file: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        name = name.strip()
        if name not in wanted:
            continue
        from_file[name] = value.strip().strip('"').strip("'")
    refreshed: dict[str, str] = {}
    for name in sorted(wanted):
        value = from_file.get(name)
        if value is None or os.environ.get(name) == value:
            continue
        os.environ[name] = value
        refreshed[name] = value
    if refreshed:
        job["design_env_refreshed"] = dict(refreshed)
        emit(
            {
                "progress": "design_ai.env 在本轮开始前已改动，渲染旋钮已按新值重设："
                + "、".join(f"{name}={value}" for name, value in refreshed.items())
                + "（启动器里手动设过的值不受影响）"
            }
        )
    return refreshed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job")
    args = parser.parse_args()
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    refresh_design_env_render_knobs(job)
    server = str(job["server"]).rstrip("/")
    http_timeout = max(1, int(job.get("http_timeout", 30)))
    manifest_path = Path(job["manifest_path"])
    segments = [dict(row) for row in job.get("segments", [])]
    job["segment_count"] = len(segments)
    if not segments:
        raise ValueError("The smart-render job has no segments.")

    # Round 113: the H3 phase of a take is one long GPU lease, and the status tray only honours a
    # comfy_claim.json whose ts is younger than its 120-second liveness grace.  The Studio writes that
    # claim once before generation, and active_run.json - the tray's second signal - is written only by
    # the staged driver, so on the Studio path every queue-idle stretch inside a take (the reference
    # upload, the SAM3.1 aux gap, the ffmpeg composite) released the claim and let a ~20 GB Qwen back
    # onto the VRAM this take was still using.  The worker owns the phase, so the worker renews the
    # lease for as long as it lives and stops the instant it does not.
    claim_lease = {}
    try:
        import staged_model_driver as _h3_claim_driver

        claim_lease = dict(_h3_claim_driver.start_comfy_claim_lease(note="worker-gpu-phase") or {})
    except Exception as exc:  # the tray is an optimisation, never a dependency of a take
        emit({"progress": f"GPU claim lease skipped: {exc}"})

    preflight = preflight_smart_render(job)
    completed_indexes: set[int] = set()
    emit({
        "preflight": preflight,
        "render_progress": build_render_progress(
            job, segments, completed_indexes, stage="preflight"
        ),
        "progress": (
            f"Long-render preflight passed · {preflight['segment_count']} segments · "
            f"{preflight['node_class_count']} node classes · "
            f"{preflight['free_disk_gb']:.1f}GB disk free"
        ),
    })

    uploaded: list[dict] = []
    seen_uploads: set[tuple[str, str]] = set()
    for item in job.get("media", []):
        if isinstance(item, dict):
            path = Path(str(item.get("path", "")))
            upload_name = str(item.get("upload_name") or path.name)
        else:
            path = Path(str(item))
            upload_name = path.name
        upload_key = (str(path.resolve()) if path.exists() else str(path), upload_name)
        if upload_key in seen_uploads:
            continue
        seen_uploads.add(upload_key)
        if path.is_file():
            result = upload_file(server, path, http_timeout, upload_name)
            uploaded.append({
                "file": path.name,
                "upload_name": upload_name,
                "result": result,
            })
            emit({"progress": f"Uploaded {path.name} as {upload_name}"})

    speech_guard: NativeSpeechGuard | None = None
    if any(
        bool((segment.get("native_speech_guard") or {}).get("enabled"))
        for segment in segments
    ):
        speech_guard = NativeSpeechGuard(
            str(job.get("native_speech_guard_model", "")),
            str(job.get("ffmpeg", "")),
        )
        emit({
            "progress": (
                "Native Speech Guard armed · Whisper checks only unauthorized "
                "human-vocal gaps · no Hard Block"
            )
        })

    completed: list[dict] = []
    previous_video: Path | None = None
    for index, segment in enumerate(segments):
        cached = Path(str(segment.get("output_path", "")))
        if segment.get("status") == "cached" and cached.is_file():
            cached = materialize_preview_proxy(job, segment, cached)
            segment["output_path"] = str(cached)
            completed.append({key: value for key, value in segment.items() if key != "workflow"})
            completed_indexes.add(index)
            previous_video = cached.resolve()
            emit({
                "segment_status": {
                    "segment_id": segment["segment_id"],
                    "status": "reusable",
                },
                "render_progress": build_render_progress(
                    job, segments, completed_indexes, stage="cached", current_index=index
                ),
                "progress": f"Segment {index + 1}/{len(segments)} reused from cache",
            })
            continue

        workflow = deepcopy(segment["workflow"])
        resume_existing = bool(
            str(segment.get("prompt_id", "")).strip()
            and str(segment.get("status", "")).strip().lower()
            in {"queued", "monitoring", "reconnecting", "running"}
        )
        continuity = segment.get("continuity") or {}
        if previous_video is not None and continuity and not resume_existing:
            kind = str(continuity.get("kind", "image")).lower()
            if kind == "video":
                anchor_path = Path(segment["download_dir"]) / "continuity_tail.mp4"
                extract_tail_frames(
                    Path(job["ffmpeg"]),
                    Path(job["ffprobe"]),
                    previous_video,
                    anchor_path,
                    frame_count=int(continuity.get("frame_count", 24)),
                    fps=int(continuity.get("fps", 24)),
                )
            else:
                anchor_path = Path(segment["download_dir"]) / "continuity_frame.jpg"
                extract_last_frame(
                    Path(job["ffmpeg"]),
                    Path(job["ffprobe"]),
                    previous_video,
                    anchor_path,
                )
            upload = upload_file(server, anchor_path, http_timeout)
            uploaded_name = str((upload or {}).get("name") or anchor_path.name)
            _patch_continuity(workflow, continuity, uploaded_name)
            label = "24-frame motion tail" if kind == "video" else "last-frame still"
            emit({"progress": f"Segment {index + 1}: previous {label} continuity attached"})

        # External authored TTS is intentionally dry and, in real H3 API tests,
        # suppresses native ambience even when the prompt explicitly requires it.
        # Before queuing the final Segment, create one complete production-sound
        # reference (exact TTS + H3-native speech-free ambience). A reconnecting
        # final prompt is already accepted by ComfyUI and must not be altered.
        if not resume_existing:
            location_upload = prepare_complete_location_sound_reference(
                job, segment, workflow
            )
            if location_upload is not None:
                uploaded.append(location_upload)

        emit({
            "segment_status": {
                "segment_id": segment["segment_id"],
                "status": "running",
            },
            "render_progress": build_render_progress(
                job, segments, completed_indexes, stage="running", current_index=index
            ),
            "progress": (
                f"Generating segment {index + 1}/{len(segments)} · "
                f"{segment['start_seconds']:.2f}–{segment['end_seconds']:.2f}s"
            )
        })
        try:
            def checkpoint_queued(prompt_id: str, attempt: int, queued: dict) -> None:
                pending = {
                    key: value for key, value in segment.items() if key != "workflow"
                }
                pending.update(
                    status="monitoring",
                    prompt_id=prompt_id,
                    attempts_used=attempt,
                    queued_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    error="",
                    failure_class="",
                )
                checkpoint_manifest = {
                    "format": "h3-smart-render-manifest",
                    "version": 1,
                    "render_policy_version": int(
                        job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
                    ),
                    "server": server,
                    "request_kind": job.get("request_kind", "final"),
                    "master_seed": job.get("seed"),
                    "megapixels": job.get("megapixels"),
                    "target_duration_seconds": job.get("target_duration_seconds"),
                    "timeline_start_seconds": job.get("timeline_start_seconds", 0.0),
                    "timeline_end_seconds": job.get("timeline_end_seconds"),
                    "active_prompt_id": prompt_id,
                    "segments": completed + [pending] + [
                        {key: value for key, value in row.items() if key != "workflow"}
                        for row in segments[index + 1 :]
                    ],
                }
                _write_manifest(manifest_path, checkpoint_manifest)
                emit({
                    "segment_status": {
                        "segment_id": segment["segment_id"],
                        "status": "running",
                        "prompt_id": prompt_id,
                    },
                    "partial_manifest": checkpoint_manifest,
                    "connection_state": "monitoring",
                    "progress": (
                        f"Segment {index + 1}/{len(segments)} server Job checkpointed · "
                        f"prompt_id {prompt_id}"
                    ),
                })

            if str(segment.get("character_swap_engine") or "") == "akatz-h3-relay":
                result = queue_character_swap_passes(
                    job,
                    segment,
                    uploaded,
                    on_queued=checkpoint_queued,
                )
            else:
                result = queue_segment(
                    job,
                    segment,
                    workflow,
                    uploaded_media_for_workflow(workflow, uploaded),
                    on_queued=checkpoint_queued,
                    speech_guard=speech_guard,
                )
        except Exception as exc:
            failure_class = classify_generation_error(exc)
            failed = {
                key: value for key, value in segment.items() if key != "workflow"
            }
            recovery_pending = isinstance(exc, ComfyConnectionRecoveryTimeout)
            accepted_prompt_id = (
                str(getattr(exc, "prompt_id", ""))
                or str(segment.get("prompt_id", ""))
            )
            failed.update(
                status="monitoring" if recovery_pending else "failed",
                error=str(exc),
                failure_class=failure_class,
                # Round 52: the manifest now carries the frames, not just the
                # one-line message.  A stale claim, a half-written take and a
                # genuine H3 refusal all used to look identical here.
                error_traceback="".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                ).strip(),
                attempt_error_tracebacks=list(
                    getattr(exc, "attempt_tracebacks", ()) or ()
                ),
                retry_budget=max(1, min(5, int(job.get("segment_attempts", 3)))),
            )
            if accepted_prompt_id:
                failed["prompt_id"] = accepted_prompt_id
            manifest = {
                "format": "h3-smart-render-manifest",
                "version": 1,
                "render_policy_version": int(
                    job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
                ),
                "server": server,
                "request_kind": job.get("request_kind", "final"),
                "master_seed": job.get("seed"),
                "megapixels": job.get("megapixels"),
                "target_duration_seconds": job.get("target_duration_seconds"),
                "timeline_start_seconds": job.get("timeline_start_seconds", 0.0),
                "timeline_end_seconds": job.get("timeline_end_seconds"),
                "active_prompt_id": accepted_prompt_id if recovery_pending else "",
                "segments": completed + [failed] + [
                    {key: value for key, value in row.items() if key != "workflow"}
                    for row in segments[index + 1 :]
                ],
            }
            _write_manifest(manifest_path, manifest)
            emit({
                "segment_status": {
                    "segment_id": segment["segment_id"],
                    "status": "reconnecting" if recovery_pending else "failed",
                    "error": str(exc),
                    "failure_class": failure_class,
                },
                "partial_manifest": manifest,
                "render_progress": build_render_progress(
                    job,
                    segments,
                    completed_indexes,
                    stage="reconnecting" if recovery_pending else "failed",
                    current_index=index,
                ),
                "progress": (
                    f"Segment {index + 1}/{len(segments)} saved for prompt reconnect"
                    if recovery_pending
                    else f"Segment {index + 1}/{len(segments)} failed"
                ),
            })
            raise
        timing_spec = segment.get("source_audio_timing_audit") or {}
        timing_audit = (
            audit_source_audio_timing(
                Path(job["ffmpeg"]),
                Path(str(result.get("output_path") or "")),
                timing_spec,
            )
            if timing_spec.get("enabled")
            else {"status": "not_requested"}
        )
        if timing_audit.get("status") != "not_requested":
            result["source_audio_timing_audit"] = timing_audit
            offset = float(timing_audit.get("offset_seconds", 0.0) or 0.0)
            correlation = float(timing_audit.get("correlation", 0.0) or 0.0)
            emit({
                "source_audio_timing_audit": {
                    "segment_id": segment.get("segment_id", ""),
                    **timing_audit,
                },
                "progress": (
                    f"Segment {index + 1}: A999 timing audit "
                    f"{timing_audit.get('status')} · offset {offset:+.3f}s · "
                    f"confidence {correlation:.2f} · detection only"
                ),
            })
        preview_path = materialize_preview_proxy(
            job, segment, Path(str(result.get("output_path") or ""))
        )
        if preview_path != Path(str(result.get("output_path") or "")):
            result["relay_inference_output_path"] = str(result.get("output_path") or "")
            result["output_path"] = str(preview_path)
            result["preview_proxy_megapixels"] = float(job.get("megapixels", 0.2) or 0.2)
        completed.append(result)
        completed_indexes.add(index)
        previous_video = Path(result["output_path"])
        manifest = {
            "format": "h3-smart-render-manifest",
            "version": 1,
            "render_policy_version": int(
                job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
            ),
            "server": server,
            "request_kind": job.get("request_kind", "final"),
            "master_seed": job.get("seed"),
            "megapixels": job.get("megapixels"),
            "target_duration_seconds": job.get("target_duration_seconds"),
            "timeline_start_seconds": job.get("timeline_start_seconds", 0.0),
            "timeline_end_seconds": job.get("timeline_end_seconds"),
            "segments": completed + [
                {key: value for key, value in row.items() if key != "workflow"}
                for row in segments[index + 1 :]
            ],
        }
        _write_manifest(manifest_path, manifest)
        emit({
            "segment_status": {
                "segment_id": segment["segment_id"],
                "status": "reusable",
            },
            "segment_completed": result,
            "partial_manifest": manifest,
            "render_progress": build_render_progress(
                job, segments, completed_indexes, stage="complete", current_index=index
            ),
            "progress": (
                f"Segment {index + 1}/{len(segments)} complete · "
                "H3 kept resident for the next Segment"
            ),
        })

    emit({
        "render_progress": build_render_progress(
            job, segments, completed_indexes, stage="assembling"
        ),
        "progress": f"Preparing to assemble {len(completed)} completed segments",
    })
    master = assemble_master(job, completed)
    final_release = release_comfy_memory(server, http_timeout)
    # Claim protocol: the H3 phase is over and /free ran.  Stop renewing *first* - a live lease would
    # re-arm the very file this clear deletes - then drop the claim so the status tray can auto-load
    # Qwen again (~20s after free + an idle queue).  The counters land in the manifest: a take has to
    # be able to say, in the app's own numbers, who held the GPU and for how long.
    try:
        import staged_model_driver as _h3_claim_driver

        stopped_lease = _h3_claim_driver.stop_comfy_claim_lease()
        if isinstance(stopped_lease, dict):
            claim_lease = {**claim_lease, **stopped_lease}
        claim_lease["at_release"] = _h3_claim_driver.claim_lease_state()
        _h3_claim_driver.clear_comfy_claim()
        claim_lease["after_clear"] = _h3_claim_driver.claim_lease_state()
    except Exception:
        pass
    final_manifest = {
        "format": "h3-smart-render-manifest",
        "version": 1,
        "gpu_claim_lease": dict(claim_lease),
        "render_policy_version": int(
            job.get("render_policy_version", SMART_RENDER_POLICY_VERSION)
        ),
        "server": server,
        "request_kind": job.get("request_kind", "final"),
        "master_seed": job.get("seed"),
        "megapixels": job.get("megapixels"),
        "target_duration_seconds": job.get("target_duration_seconds"),
        "timeline_start_seconds": job.get("timeline_start_seconds", 0.0),
        "timeline_end_seconds": job.get("timeline_end_seconds"),
        "master_output": str(master),
        "final_model_release": final_release,
        "segments": completed,
    }
    _write_manifest(manifest_path, final_manifest)
    # The full workflow-bearing job can be large. Keep it only for interrupted
    # recovery; a successful final manifest is the compact durable record.
    Path(args.job).unlink(missing_ok=True)
    emit({
        "smart_render": True,
        "queued": {"prompt_id": "smart-render-master"},
        "completed": True,
        "outputs": [{"kind": "videos", "local_path": str(master)}],
        "master_output": str(master),
        "manifest": final_manifest,
        "request_kind": job.get("request_kind", "final"),
        "seed": job.get("seed"),
        "megapixels": job.get("megapixels"),
        "render_progress": build_render_progress(
            job, segments, completed_indexes, stage="final"
        ),
        "progress": f"Master complete · {final_release}",
    })
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        OSError,
        ValueError,
        RuntimeError,
        TimeoutError,
        subprocess.SubprocessError,
        urllib.error.URLError,
        urllib.error.HTTPError,
    ) as exc:
        emit({"error": str(exc), "smart_render": True})
        raise SystemExit(1)
