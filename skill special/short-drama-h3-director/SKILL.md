---
name: short-drama-h3-director
description: |
  Develop short-form and vertical drama episodes for MiniMax H3 with executable conflict, character causality, exact authored dialogue, planted reversals, episode hooks, timed Shot Blocks, reference-media planning and production-ready Director Design JSON. Use for urban drama, suspense, romance, family conflict, social-topic monologues and episodic shorts that must become an editable H3 Timeline.
---

# Short Drama H3 Director

Apply this Special Skill together with the bound Default H3 prompt-writing skill. Shape the drama and its production plan; let the Default Skill preserve the official MiniMax H3 Ref2VA structure and reference syntax.

## Define One Executable Production Unit

Treat one Studio project as one episode or one explicitly bounded production unit. Preserve the requested duration, aspect ratio, language, genre, audience, platform, locations, cast, budget, references and delivery form.

For a multi-episode request, establish the series premise and episode progression only as concise context, then fully execute the episode named by the user. Do not compress several complete episodes into one short Timeline unless explicitly requested.

Build a compact dramatic brief containing:

- genre and audience promise;
- protagonist's immediate visible objective;
- resistance, risk and cost of failure;
- relationship pressure or concealed information;
- opening hook, escalation, reversal, emotional landing and episode hook;
- production limits and exact deliverables.

Ask only for a missing fact that would materially change the story. Make and label reasonable assumptions for everything else.

## Build Causal Drama

Every scene and Shot must change at least one of: information, relationship, objective, risk or emotion. Avoid scenes that merely restate the premise.

Use this causal chain:

1. A visible trigger changes the present situation.
2. A character pursues an immediate objective.
3. Another person, object, rule, deadline or hidden fact creates resistance.
4. The character makes a choice that produces a visible consequence.
5. The consequence forces the next Shot rather than resetting the scene.

Plant evidence before a reversal. A twist must become more convincing when the audience looks back at earlier Shots. Do not introduce an unprepared stranger, object, power or confession solely to manufacture surprise.

End an episode with a new question, irreversible cost, changed relationship or immediate threat. A hook must advance the story; it is not an arbitrary interruption.

## Lock Character and Relationship Continuity

Before writing Shots, freeze:

- exact character identities, appearance, wardrobe and visible props;
- each character's knowledge, current objective and emotional pressure;
- relationship status at the beginning and end of every scene;
- who owns, sees, hears, gives, receives or hides each story-critical object;
- location geography and the visible travel path between spaces.

Do not change motivation between Shots without a visible event, discovery, threat or choice. Express internal change through behavior, reaction, avoidance, hesitation, gaze, distance, object handling or speech—not explanatory narration alone.

## Preserve Authored Speech Verbatim

When the user provides Dialogue, Voice-over, Lyrics or On-screen Text, preserve every word, language and time range exactly. Never paraphrase, summarize, duplicate, translate, omit or move authored words to another speaker.

Put speech and visible copy in `text_layers`, never bury the only copy inside `subject_action`, `creative_brief` or a Shot prompt.

- `dialogue`: on-screen character speech; assign S1 to a female speaker and S2 to a male speaker unless explicitly assigned.
- `voice_over`: narrator or internal voice that does not require visible lip sync.
- `lyrics`: authored sung words.
- `on_screen_text`: text that must be visible in the image.

Set `explicit_user_requested=true` for authored content. Preserve the intended language, delivery and lip-sync choice. Make dialogue playable: each line pursues, tests, evades, pressures, reveals or reacts. Avoid long background exposition when action or subtext can carry the information.

If exact speech does not fit its authored time range, retain the words and request faster natural delivery or a wider time range; never solve timing by deleting words.

## Convert the Script Into Director Design JSON

Return one schema-valid Director Design JSON object, not screenplay Markdown. Use exact chronological, non-overlapping Shot ranges on the 0.5-second grid and cover the full requested duration.

For every Shot provide:

- `framing`: a readable composition suited to the dramatic information;
- `camera_angle`: the power or emotional relationship of the moment;
- `camera_movement`: one primary move, or a stable camera when performance is more important;
- `subject_action`: the must-complete visible causal action;
- `environment_response`: only contact- or event-driven reactions that prove causality;
- `continuity_state`: incoming and outgoing pose, gaze, prop ownership, screen direction, emotion and unresolved action;
- `optional_flourish`: expendable atmosphere or secondary behavior;
- `additional_direction`: performance, subtext, pacing and reference-use details.

Budget no more than three must-complete physical beats, two required consequences and two optional flourishes per five seconds. Split overloaded drama into shorter consecutive Shots when time permits; otherwise preserve trigger, decisive choice, consequence and outgoing state before decoration.

Use reaction Shots only when the reaction changes meaning or decision. Do not repeat the same crying, staring, walking, phone-reading or confrontation action in several Shots without new information.

## Plan Visual Language

For vertical 9:16 drama, keep the critical face, hand, phone message, evidence or relationship axis legible in one vertical composition. Avoid wide staging that makes the story clue unreadable.

Use camera grammar to support drama:

- stable or restrained movement for performance and subtext;
- push-in for realization, pressure or an irreversible decision;
- pull-back for isolation, exposure or changed geography;
- controlled handheld movement for immediate danger or instability;
- insert or macro framing only for story-critical evidence;
- motivated cutaways that reveal information, not decorative coverage.

Maintain screen direction, eyelines, prop position and room geography across cuts. Do not use a transition to hide a continuity error.

## Plan Reference Media

Audit selected Media Pool evidence before requesting new material. Reuse matching sources through `existing_media_uses` with stable `@P`, `@V` and `@A` IDs. Never invent an empty ID or replace a supplied reference that already satisfies the need.

Use `media_requests` only for missing identity, wardrobe, location, evidence-object, emotional-state or boundary-composition references that materially reduce ambiguity. Do not create one image per Shot automatically.

Every generated image must be a complete standalone prompt showing exactly one frozen instant in the real story environment. Preserve exact character/prop ownership and avoid neutral studio backgrounds for time-scoped action or boundary references.

## Design Dialogue, Ambience and Music

Dialogue must sound captured in the visible location: natural breath, conversational pauses, camera-distance perspective, subtle environmental bleed and space-appropriate reflections. Do not request a dry announcer voice for on-screen drama.

Plan three diegetic layers when relevant:

1. continuous location ambience;
2. exact-frame Foley and one-shot effects caused by visible contact;
3. foreground speech.

Plan non-diegetic music as a separate dramatic layer. Duck it under speech, let it rise in gaps and transitions, and use it to support pressure or release without replacing performance.

## Transition and Final Hold

Use direct cuts for most dramatic exchanges. Use match action, sound bridges, occlusion or motivated inserts only when they preserve direction or carry information across a boundary.

Create a Final Hold marker before the final frame. Resolve the last outgoing state and episode hook without introducing a new multi-beat action. Preserve readable face, evidence, threat or changed relationship through the hold.

## Validate Before Delivery

- Exact duration is covered with no Shot gap or overlap.
- Every scene changes information, relationship, objective, risk or emotion.
- Every reversal has an earlier visible or audible clue.
- Character knowledge, motivation, wardrobe, props and geography remain continuous.
- Authored `text_layers` are verbatim, timed once and assigned to the correct speaker.
- Media Pool sources are reused before new references are requested.
- Shot action budgets are executable and Final Hold introduces no new action.
- Constraints state that identity, continuity and core actions outrank optional flourish.
- Output is valid Studio Design JSON ready for the bound Default H3 Skill.

