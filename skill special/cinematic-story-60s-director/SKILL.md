---
name: cinematic-story-60s-director
description: |
  Adapt long prose, background material or a rough story into an approximately 60-second cinematic MiniMax H3 short with visual-first storytelling, generated Mandarin dialogue and voice-over, editable independent speech layers, reference-first character continuity, speech-safe timing and a memorable ending. Use when the user wants to paste story material instead of authoring every Shot and line manually.
---

# Cinematic Story 60s Director

Apply this Special Skill together with the bound Default H3 Prompt Writing Skill. Treat the user's story as adaptation source material unless the user separately labels words as exact authored Dialogue, Voice-over, Lyrics or On-screen Text.

## Adapt Before Structuring

Read the whole source before planning Shots. Extract the central character objective, relationship, conflict, concealed information, escalation, climax and final reversal or memorable landing. Do not mechanically divide paragraphs into equal visual blocks and do not narrate every fact.

Prefer visible decisions, behavior, evidence, reaction and environment change over explanation. Compress background history, repeated claims, secondary branches and decorative information before reducing the central causal chain. The result must be understandable without trying to preserve every source sentence.

## Plan the Duration

Use 60.00 seconds as the initial target and normally create eight to twelve chronological, non-overlapping Shots on the 0.5-second grid. Cover the complete actual Timeline from 0.00 seconds with no gap.

Budget generated speech before finalizing Shot boundaries. First shorten exposition and rewrite generated lines into concise natural Mandarin. If further compression would make delivery unnatural, remove the core conflict or break the final reversal, Studio may extend the Timeline modestly. When it does, extend the owning Shot and every affected downstream Shot, Text Layer, cue and range together. Never create a speech-only tail with no Shot coverage.

Reserve visible time for silent reaction, action, ambience, Foley and the final image. Do not fill the entire film with continuous narration. The final 0.5 to 1.0 seconds must be a stable Final Hold with no new action or new speech.

## Build Cinematic Causality

Create a fast opening question or disturbance, causal escalation through the middle, a decisive choice or discovery near the climax, and a reversal, hook or strong emotional image at the end. Every Shot must change information, objective, risk, relationship, location or physical state.

For every Shot provide one primary camera movement, a must-complete subject action, a contact- or event-driven environment response, incoming continuity, outgoing continuity, and optional flourish. Allow at most three must-complete physical actions per five seconds. Do not use walking, staring, montage or decorative coverage as substitutes for story progress.

Maintain identity, age, face, hairstyle, wardrobe, props, geography, time, weather, lighting, screen direction, knowledge and emotional state across Shots. A change requires an authored visible cause and must persist afterward.

## Respect Reference Authority

Explicitly referenced Media Pool sources are the highest visual evidence. Preserve the facts actually established by requested `@P`, `@V` and `@A` sources and design only what those sources do not define. A loaded but unreferenced source is available evidence, not an automatic character binding. Never invent a Media Pool ID.

If references do not define a required person, wardrobe, location or prop, design the missing fact from the current story. Reuse suitable sources through `existing_media_uses` before creating `media_requests`. Do not generate one image per Shot automatically; request only the minimum identity, location, prop-state or difficult boundary references required for stable execution.

## Generate and Lock Speech

Generate concise, conversational Mandarin Dialogue and Mandarin Voice-over appropriate to character identity and visible emotion. Decide whether information belongs in action, Dialogue or Voice-over; never let Voice-over repeat what the image already proves.

Every final spoken line must be its own editable `text_layers` item with role, speaker, language, delivery, start, end, Shot binding and `overlap_policy`. Keep spoken words exclusively in Text Layers, never inside Shot prompts. Because the user requested generated speech, set `explicit_user_requested=true` after the Design model has chosen the final wording; from that point forward, preserve it verbatim through Timeline, Prompt and generation.

Use `auto` by default. Use `overlap` only for narratively intentional simultaneous speech and route the lines to different same-role lanes. Use `sequential` when the later line must wait. Never merge, reorder, duplicate, translate, omit or invent speech after final Text Layers are established. A real overlap group must remain inside one H3 Segment rather than being cut at a speaker change.

## Direct Picture and Sound

Use photoreal live-action cinematography unless the user explicitly requests another visual form. Choose framing, lens distance and camera motion for story meaning, not constant spectacle. Keep anatomy, performance, exposure, depth of field and environmental behavior physically believable. Avoid cartoon rendering, visible AI artifacts, unexplained extra principal characters, identity drift, costume resets and unsupported modern objects.

Dialogue and Voice-over must sound appropriate to the visible or intended acoustic space. Maintain continuous diegetic ambience, synchronize Foley to visible contact and duck non-diegetic music under speech. Follow the current Studio MUSIC mode. Do not add unauthorized voices.

Follow the current SUB setting. When subtitles are off, Dialogue and Voice-over may not appear as burned-in text. Design Requirement instructions, Shot labels, prompts, logos, watermarks and UI text must never become visible scenery. Story-essential visible text must be a separate editable `on_screen_text` layer.

## Deliver Director Design JSON

Return one schema-valid Studio Director Design JSON object covering the complete actual duration. Do not return screenplay Markdown or several disconnected JSON objects.

Before delivery verify:

- the core story is understandable and the ending pays off an earlier setup;
- Shots cover the actual duration with no gap or overlap;
- every generated spoken line exists exactly once in an editable Text Layer;
- overlapping lines use independent tracks and an explicit policy;
- speech timing cannot create a Shot-less Segment;
- explicit references outrank generated appearance and location choices;
- each Shot has one primary camera movement and an executable action budget;
- optional flourish yields before identity, causality, speech or continuity;
- the Final Hold begins no new action, speech or unexplained visual element.
