---
name: comic-talk-show-h3
description: |
  Turn one loaded P1 group image into a duration-aware ensemble comedy in which every complete foreground person is detected dynamically, assigned a stable left-to-right speaker identity, given one main comic beat, and preserved in P1's original visual medium. Use for one-person monologues, two-person banter or larger group talk shows without fixing the cast count in advance.
---

# Comic Talk Show H3

Apply this Special Skill together with the bound Default H3 Prompt Writing Skill. `@P1` is required and is the authoritative group-cast, composition, wardrobe, location and source-medium plate.

## Inspect P1 Before Writing

Build a cast ledger from the current P1 visual evidence before planning any Shot or line. Count only complete, clearly visible foreground people intended as the principal group. Ignore cropped edge fragments, background passers-by, portraits, reflections, statues, mannequins and duplicated depictions. Never assume five people.

Assign stable speaker IDs from left to right in the opening P1 composition:

- leftmost complete principal person is `S1`;
- next complete principal person is `S2`;
- continue as `S3`, `S4` and onward until every complete principal person has exactly one ID.

For every ID record the P1-established screen position, recognizable face, apparent age, hairstyle, body proportions, complete clothing, footwear and accessories. Preserve this ledger through every Shot. Speaker numbering never changes when the camera pans, reframes or cuts closer. Do not remap IDs by gender.

If P1 evidence is too weak to distinguish a fact, preserve the supplied pixels neutrally; never invent a replacement cast. BLIP and AI Enrich are descriptive evidence only and never outrank P1.

## Lock the Source Medium

Match P1's actual visual medium exactly. A photograph stays photographic, a 2D comic stays in the same line art and colouring language, a 3D render stays 3D, and an illustration stays illustrated. “Natural acting” describes performance only; it never authorizes photoreal conversion, cartoon conversion or visual-style replacement.

Preserve P1's original location, palette, lighting logic, object layout and group identity unless the user explicitly requests a new location. Do not redesign the people into generic young actors.

## Reference Policy

Register P1 in `existing_media_uses` as a `whole_design` `h3_reference` covering the complete actual Timeline. Every Segment must retain P1.

Do not create free text-to-image actor, portrait, pose or group references. Set image `media_requests` to empty for the ordinary P1 talk-show setup. Never create P2-P9 strangers to illustrate individual speakers. Camera reframing, facial performance and body reactions are executed by H3 from P1 plus Shot prose.

If the user explicitly requests a new environment, an environment-only request may be considered only when it contains no principal or substitute person and cannot compete with P1. Otherwise preserve P1's background.

## Adapt to Any Cast Count

Use the detected complete-person count, not a fixed template count:

- one person: direct-to-camera comic monologue;
- two people: setup, rebuttal and reversal;
- three people: setup, escalation and payoff;
- four or more people: one main beat per person plus silent group reactions and a final ensemble payoff.

Create one opening group Shot, one readable main speaker beat for every detected cast member, and one final group payoff Shot. Combine only when the requested duration is too short, but every principal person must still receive one clearly attributable spoken beat unless the user requests otherwise.

Budget the spoken copy before fixing boundaries. Use the user's explicit duration as the target. First shorten generated dialogue and remove repeated setup; do not silently extend a 45-second request merely to preserve verbose AI-written lines. Reserve at least 15 percent of the Timeline for reaction pauses, ambience, camera movement and the final payoff. Extend only when the user supplied exact verbatim lines that cannot fit naturally.

## Bind Speech to Faces

Every final line must be an independent editable `text_layers` item. Use the dynamic `S1...SN` cast ledger for `speaker`, set `explicit_user_requested=true`, and keep the words out of Shot prose.

End each generated Dialogue Text Layer when its estimated spoken copy finishes; never stretch a short line across the complete camera Shot. The released Shot tail is reserved for closed-mouth reaction, ambience and picture-synchronous Foley. Do not write `speaks`, `says`, `after the line`, `before the next line` or equivalent speech-state prose into a Shot interval that has no overlapping Dialogue Text Layer.

Each principal speaker receives a separate Dialogue Text Layer and stable Speaker ID. During a non-overlapping line, only the assigned P1 cast member moves lips and jaw; every other visible cast member keeps a non-speaking mouth and reacts silently through eyes, brows, head turns, posture, restrained laughter or gestures. Voice-over causes no visible lip motion.

Set every Dialogue or Voice-over Text Layer's structured `voice_gender` to `male`, `female` or `auto`. Use `male` or `female` only from the actual assigned P1 person's visible identity or an explicit user instruction; use `auto` when the evidence is ambiguous. Gender belongs to the voice event, never to the `S1...SN` number, and the selected value must reach native H3 and external TTS unchanged.

Give every authored Dialogue or Voice-over event its own visible Timeline track (`D1`, `D2`, `D3`... or the corresponding voice-over lanes), even when the same person speaks again later. A track is an ownership and editing lane, not a mixed-audio stem. Do not reuse one lane for consecutive lines merely because they do not overlap.

For ordinary turn-taking, `overlap_policy=auto` behaves sequentially and reserves at least 1.0 second after the preceding spoken line for a closed-mouth release, listener reaction, ambience and non-vocal Foley before the next line may begin. Only an explicitly authored interruption, chorus or simultaneous response may use `overlap`; it must remain on a different track and must never be inferred from tightly packed timings.

At the exact end of every Dialogue Text Layer, the active speaker immediately returns to a closed or neutral non-speaking mouth. Until the next authored Text Layer begins, every principal remains vocally silent: no ad-lib, repeated punchline, translation, early answer, vocal laugh, filler syllable, whisper or background conversation. Environment ambience and non-vocal Foley continue normally.

Use `overlap_policy=auto` by default. Use `overlap` only for an authored interruption, chorus or simultaneous response and route overlapping lines onto separate tracks. Never merge several people into one Speaker merely because they share a group image.

Voice character follows the P1 person and authored delivery. Do not force odd-number speakers to be female or even-number speakers to be male.

## Comedy and Camera Grammar

Keep humour friendly, personality-led and causally staged: visual setup, one person's line or action, listener reaction, then payoff. Avoid cruelty, humiliation and unrelated slapstick unless requested.

Start near P1's original group composition. Use pans, short lateral moves, reframes and modest push-ins to identify the active speaker while keeping at least one listener reaction visible when practical. Do not replace a cast member when moving to a close shot. Return to a readable group composition for the final payoff.

Use one main camera movement per Shot. Preserve screen order, eyelines, seating or standing relationships, handed objects and background geometry. The last 0.5 to 1.0 seconds is a stable Final Hold with no new line or action.

## Native Audio

Generate exact authored dialogue as native on-location sound with the distance, screen position and acoustics of the visible P1 scene. Maintain continuous environment ambience and picture-synchronous Foley under speech. Non-diegetic music may duck; ambience and Foley may not disappear. Do not improvise extra words.

## Validate Before Apply

- P1 exists and covers the complete actual duration.
- The cast count comes from complete P1 principals and is not hard-coded.
- The cast ledger is stable left to right and every speaking ID maps to exactly one P1 person.
- Every principal receives one attributable main beat.
- Every Dialogue line exists exactly once as an editable Text Layer.
- Every speech Text Layer has an explicit `voice_gender`; it agrees with its assigned P1 person and never comes from odd/even Speaker numbering.
- Every spoken event has its own visible Timeline track, and sequential turns retain a 1.0-second non-vocal release gap.
- Only the assigned speaker lip-syncs outside an authored overlap.
- No generated Picture introduces or substitutes a person.
- P1's visual medium, faces, clothing, palette and location remain authoritative.
- Shots cover the actual duration without gaps or overlaps.
- The final ensemble payoff resolves before a stable Final Hold.
